from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import subprocess
import os
import uuid
import time
import json
import httpx

# PyJWT avec algorithmes RS256
import jwt
from jwt.algorithms import RSAAlgorithm

# Neutralisation des messages avant journalisation (anti fuite d'info / log-injection)
from safe_logger import redact

app = FastAPI(
    title="AC360 Audit Engine API",
    description="API Enterprise Grade pour déclencher le pipeline Python depuis Copilot Studio",
    version="2.0.0"
)

security = HTTPBearer()

# ---------------------------------------------------------------------------
# Configuration Microsoft Entra ID (Azure AD)
# ---------------------------------------------------------------------------
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")

# Fail-fast : on refuse de démarrer si les variables critiques sont absentes
if not TENANT_ID:
    raise EnvironmentError(
        "ConfigurationError : La variable d'environnement TENANT_ID est obligatoire. "
        "Définissez-la avant de lancer l'application."
    )
if not CLIENT_ID:
    raise EnvironmentError(
        "ConfigurationError : La variable d'environnement CLIENT_ID est obligatoire. "
        "Définissez-la avant de lancer l'application."
    )

JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ISSUER   = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"

# Cache JWKS en mémoire (rafraîchi à chaque redémarrage)
_JWKS_CACHE: Optional[dict] = None

# Extensions de documents autorisées (whitelist)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt"}

# Dossier sécurisé de travail (isolation par job_id)
JOBS_BASE_DIR = os.path.abspath(os.getenv("JOBS_BASE_DIR", "jobs"))


def _fetch_jwks() -> dict:
    """Télécharge et met en cache les clés JWKS depuis Microsoft Entra ID."""
    global _JWKS_CACHE
    if _JWKS_CACHE is not None:
        return _JWKS_CACHE
    try:
        response = httpx.get(JWKS_URL, timeout=10.0)
        response.raise_for_status()
        _JWKS_CACHE = response.json()
        return _JWKS_CACHE
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Impossible de télécharger les clés JWKS depuis Microsoft Entra ID : {exc}"
        )


def _get_public_key(kid: str):
    """Retrouve la clé publique RSA correspondant au kid du token JWT."""
    jwks = _fetch_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(key_data))
    # Si la clé n'est pas dans le cache, on force un rafraîchissement
    global _JWKS_CACHE
    _JWKS_CACHE = None
    jwks = _fetch_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(key_data))
    raise HTTPException(status_code=401, detail="Clé publique introuvable pour ce token JWT (kid inconnu).")


def verify_azure_ad_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Vérifie cryptographiquement le JWT émis par Microsoft Entra ID via JWKS RS256.
    - Télécharge les clés depuis : https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys
    - Vérifie : issuer, audience, signature RS256, expiration (exp), nbf
    """
    token = credentials.credentials

    # 1. Décode l'en-tête sans vérification pour obtenir le kid
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError as exc:
        raise HTTPException(status_code=401, detail=f"Token JWT malformé : {exc}")

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token JWT invalide : champ 'kid' manquant dans l'en-tête.")

    alg = unverified_header.get("alg", "RS256")
    if alg != "RS256":
        raise HTTPException(status_code=401, detail=f"Algorithme JWT non autorisé : {alg}. Seul RS256 est accepté.")

    # 2. Récupère la clé publique correspondante
    public_key = _get_public_key(kid)

    # 3. Vérifie signature, issuer, audience, exp, nbf
    try:
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER,
            options={
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
            }
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token JWT expiré.")
    except jwt.ImmatureSignatureError:
        raise HTTPException(status_code=401, detail="Token JWT pas encore valide (nbf).")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Token JWT : issuer invalide.")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Token JWT : audience invalide.")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Token JWT invalide : {exc}")

    # 4. Extraction de l'identité
    upn = claims.get("upn") or claims.get("preferred_username")
    if not upn:
        raise HTTPException(status_code=401, detail="Le token ne contient pas d'identité (UPN/preferred_username).")

    print(f"[SECURITY] Token RS256 valide pour : {upn}")
    return upn


def _validate_document_id(document_id: str) -> str:
    """
    Valide un document_id (pas un chemin direct).
    Règles :
    - Doit être un UUID v4 valide
    - L'extension réelle est résolue via un registre interne (whitelist)
    Retourne le chemin sécurisé ou lève une HTTPException.
    """
    try:
        parsed = uuid.UUID(document_id, version=4)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="document_id invalide : doit être un UUID v4."
        )
    # Résolution du chemin à partir du registre de jobs
    doc_registry_path = os.path.join(JOBS_BASE_DIR, str(parsed), "metadata.json")
    if not os.path.exists(doc_registry_path):
        raise HTTPException(status_code=404, detail=f"Document introuvable pour l'ID : {document_id}")

    with open(doc_registry_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    file_path = meta.get("file_path", "")
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension de fichier non autorisée : {ext}. Extensions acceptées : {ALLOWED_EXTENSIONS}"
        )
    return file_path


# Schéma de requête — on passe un document_id (UUID), jamais un chemin direct
class AuditRequest(BaseModel):
    document_id: str          # UUID v4 référençant un document pré-uploadé
    client_context: Optional[str] = None


def run_audit_pipeline(job_id: str, doc_path: str, user_principal_name: str):
    """
    Exécute le pipeline d'audit réel en arrière-plan via subprocess.
    Les fichiers temporaires sont isolés dans /jobs/{job_id}/.
    """
    job_dir = os.path.join(JOBS_BASE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        from db_manager import log_audit_action
        log_audit_action(doc_path, "START_AUDIT", "IN_PROGRESS", f"Triggered by {user_principal_name} | job={job_id}")

        pipeline_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "run_audit_pipeline.ps1"
        )

        process = subprocess.run(
            [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-File", pipeline_script,
                "-DocumentPath", doc_path,
                "-Upn", user_principal_name,
                "-JobDir", job_dir
            ],
            capture_output=True,
            text=True
        )

        if process.returncode == 0:
            log_audit_action(doc_path, "END_AUDIT", "SUCCESS", f"Pipeline terminé. job={job_id}")
            print(f"[API_WORKER] Audit terminé — job={job_id} — doc={doc_path}")
        else:
            # Le stderr brut du pipeline peut contenir des chemins, des traces
            # Python ou du contenu de document (OCR/FIC), voire des secrets. On
            # le neutralise (masquage secrets/PII, contrôles, troncature) avant
            # de le persister en base (audit_logs.details) ou de l'afficher.
            safe_stderr = redact(process.stderr)
            log_audit_action(doc_path, "END_AUDIT", "FAILED", f"Erreur Pipeline: {safe_stderr}")
            print(f"[API_WORKER_ERROR] Code {process.returncode}: {safe_stderr}")
    except Exception as exc:
        print(f"[API_WORKER_ERROR] Exception fatale — job={job_id} : {exc}")


@app.post("/api/audit")
async def trigger_audit(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    user_upn: str = Depends(verify_azure_ad_token)
):
    """
    Déclenche un audit AC360 sur un document identifié par son UUID.
    L'authentification est vérifiée cryptographiquement via JWKS RS256.
    Aucun chemin Windows direct n'est accepté en entrée.
    """
    # Résolution sécurisée du chemin via le registre de documents
    doc_path = _validate_document_id(request.document_id)

    # Génération d'un job_id UUID v4 unique (isolation des fichiers temporaires)
    job_id = str(uuid.uuid4())

    # Lancement de la tâche lourde en arrière-plan
    background_tasks.add_task(run_audit_pipeline, job_id, doc_path, user_upn)

    return {
        "status": "accepted",
        "message": "L'audit a été lancé. Vous serez notifié via Teams à la fin du traitement.",
        "job_id": job_id,
        "document_id": request.document_id,
        "requested_by": user_upn
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0", "security": "EntraID_JWKS_RS256"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
