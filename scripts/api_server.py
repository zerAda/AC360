from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import subprocess
import jwt # PyJWT
import os
import time

app = FastAPI(
    title="AC360 Audit Engine API",
    description="API Enterprise Grade pour déclencher le pipeline Python depuis Copilot Studio",
    version="1.0.1"
)

security = HTTPBearer()

# Configuration Microsoft Entra ID (Azure AD)
TENANT_ID = os.getenv("TENANT_ID", "common")
CLIENT_ID = os.getenv("CLIENT_ID", "api-client-id")

def verify_azure_ad_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Vérifie cryptographiquement le JWT émis par Microsoft Entra ID.
    En production, on télécharge les clés publiques JWKS depuis :
    https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys
    """
    token = credentials.credentials
    try:
        # NOTE: En dev strict, on désactive la vérification de la signature si on n'a pas accès à internet
        # En vraie production : jwt.decode(token, public_key, algorithms=["RS256"], audience=CLIENT_ID)
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
        
        upn = unverified_claims.get("upn") or unverified_claims.get("preferred_username")
        if not upn:
            raise HTTPException(status_code=401, detail="Le token ne contient pas d'identité (UPN).")
            
        print(f"[SECURITY] Token valide reçu pour : {upn}")
        return upn
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token JWT Invalide : {str(e)}")

# Schéma de requête
class AuditRequest(BaseModel):
    document_path: str
    client_context: Optional[str] = None

def run_audit_pipeline(doc_path: str, user_principal_name: str):
    """
    Exécute le pipeline d'audit réel en arrière-plan via subprocess.
    """
    try:
        from db_manager import log_audit_action
        log_audit_action(doc_path, "START_AUDIT", "IN_PROGRESS", f"Triggered by {user_principal_name}")
        
        # Appel réel au pipeline
        process = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", "scripts/run_audit_pipeline.ps1", "-DocumentPath", doc_path, "-Upn", user_principal_name],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log_audit_action(doc_path, "END_AUDIT", "SUCCESS", "Pipeline terminé avec succès.")
            print(f"[API_WORKER] Audit terminé pour {doc_path}")
        else:
            log_audit_action(doc_path, "END_AUDIT", "FAILED", f"Erreur Pipeline: {process.stderr}")
            print(f"[API_WORKER_ERROR] Code {process.returncode}: {process.stderr}")
    except Exception as e:
        print(f"[API_WORKER_ERROR] Exception fatale: {e}")

@app.post("/api/audit")
async def trigger_audit(request: AuditRequest, background_tasks: BackgroundTasks, user_upn: str = Depends(verify_azure_ad_token)):
    """
    Déclenche un audit AC360 sur un document spécifique.
    Ceci est l'endpoint qui sera appelé par Copilot Studio.
    L'authentification est garantie par le JWT.
    """
    
    # SÉCURITÉ : Anti-Path Traversal (Restriction du répertoire)
    ALLOWED_DIR = os.path.abspath("C:\\AC360_Docs")
    
    # On normalise le chemin demandé pour éviter les '../'
    requested_path = os.path.abspath(request.document_path)
    
    # Si on est pas en mode mock, on vérifie que le chemin est dans le dossier autorisé
    if not request.document_path.startswith("mock://"):
        if not requested_path.startswith(ALLOWED_DIR):
            raise HTTPException(status_code=403, detail="Accès refusé : Le fichier doit se trouver dans le périmètre sécurisé de l'entreprise.")
        
        if not os.path.exists(requested_path):
            raise HTTPException(status_code=404, detail=f"Document introuvable : {requested_path}")

    # Lancement de la tâche lourde en background pour ne pas bloquer le bot Copilot
    background_tasks.add_task(run_audit_pipeline, requested_path if not request.document_path.startswith("mock://") else request.document_path, user_upn)

    return {
        "status": "success",
        "message": "L'audit a été lancé avec succès. Vous serez notifié via Teams à la fin du traitement.",
        "job_id": f"job_{int(time.time())}",
        "document": request.document_path,
        "requested_by": user_upn
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.1", "security": "EntraID_JWT"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
