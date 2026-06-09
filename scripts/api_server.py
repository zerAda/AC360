from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import time
import httpx
import asyncio
from collections import defaultdict
from planner_integration import create_planner_task
from generate_fiche_rdv import generate_fiche_rdv
from auth import verify_azure_ad_token
from safe_logger import log_security

app = FastAPI(
    title="AC360 Audit Engine API",
    description="API Enterprise Grade - Passerelle vers Azure Durable Functions",
    version="3.0.0"
)

# Configuration de l'Azure Function Backend
AZURE_FUNCTION_URL = os.environ.get("AZURE_FUNCTION_URL", "http://localhost:7071/api")
AZURE_FUNCTION_KEY = os.environ.get("AZURE_FUNCTION_KEY", "")

# Global HTTP Client pour éviter le Socket Exhaustion
http_client = httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=50, max_connections=200))


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

# ---------------------------------------------------------------------------
# Middleware Application Insights (Monitoring Enterprise)
# ---------------------------------------------------------------------------


class AppInsightsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        if os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY"):
            log_security("INFO", "AppInsights_Telemetry", {
                "method": request.method,
                "url": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(process_time * 1000, 2)
            })

        response.headers["X-Process-Time"] = str(round(process_time, 4))
        # En-têtes de sécurité standard (défense en profondeur API).
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(AppInsightsMiddleware)

# ---------------------------------------------------------------------------
# Rate-limiting
# ---------------------------------------------------------------------------
_RATE_LIMIT_MAX = 10
_RATE_LIMIT_WINDOW = 3600  # secondes
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


async def cleanup_rate_limits():
    now = time.time()
    keys_to_delete = []
    for k, timestamps in list(_rate_limit_store.items()):
        valid_ts = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if not valid_ts:
            keys_to_delete.append(k)
        else:
            _rate_limit_store[k] = valid_ts
        await asyncio.sleep(0)  # Ne pas bloquer l'Event Loop
    for k in keys_to_delete:
        _rate_limit_store.pop(k, None)


async def _check_rate_limit(upn: str) -> None:
    now = time.time()
    if len(_rate_limit_store) > 1000:
        asyncio.create_task(cleanup_rate_limits())

    _rate_limit_store[upn] = [t for t in _rate_limit_store[upn] if now - t < _RATE_LIMIT_WINDOW]

    if len(_rate_limit_store[upn]) >= _RATE_LIMIT_MAX:
        log_security("WARNING", f"Rate limit dépassé pour {upn}")
        raise HTTPException(
            status_code=429,
            detail=(f"Quota dépassé : maximum {_RATE_LIMIT_MAX} audits par heure.")
        )
    _rate_limit_store[upn].append(now)

# ---------------------------------------------------------------------------
# Validation des identifiants (anti path-traversal + anti accès arbitraire)
# ---------------------------------------------------------------------------


def _validate_document_id(document_id: str) -> str:
    """Valide qu'un identifiant est un UUID canonique ET qu'il correspond à une
    ressource connue (répertoire de job sous ``jobs_base_dir``).

    Double objectif de sécurité :
      * empêcher le path traversal sur un segment d'URL (``..``, chemins absolus,
        séparateurs) en exigeant un UUID strict ;
      * empêcher l'énumération/accès à des ressources arbitraires en vérifiant
        l'existence du répertoire de job.

    Lève ``HTTPException`` 400 (format invalide) ou 404 (ressource inconnue).
    Retourne l'UUID normalisé en cas de succès.
    """
    try:
        normalized = str(uuid.UUID(str(document_id)))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Identifiant invalide : un UUID canonique est attendu.",
        )

    from config import load_config
    config = load_config()
    base = os.path.abspath(config.jobs_base_dir)
    resolved = os.path.abspath(os.path.join(base, normalized))

    # Défense en profondeur : le chemin résolu doit rester confiné sous la base.
    try:
        if os.path.commonpath([resolved, base]) != base:
            raise HTTPException(status_code=400, detail="Identifiant invalide.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant invalide.")

    if not os.path.isdir(resolved):
        raise HTTPException(status_code=404, detail="Ressource introuvable.")

    return normalized


# Schémas de requête
class AuditRequest(BaseModel):
    document_id: str
    client_context: Optional[str] = None


class PlannerTaskRequest(BaseModel):
    title: str
    due_date: str
    plan_id: str
    bucket_id: str


class FicheRDVRequest(BaseModel):
    client_name: str
    summary: str
    alert_points: str


@app.post("/api/audit")
async def trigger_audit(
    request: AuditRequest,
    req: Request,
    user_upn: str = Depends(verify_azure_ad_token)
):
    await _check_rate_limit(user_upn)

    if not request.document_id:
        raise HTTPException(status_code=400, detail="document_id manquant.")

    # [PATCH HATER OPTION A] Plus de fausse validation locale.
    # On transmet l'ID du document à l'Azure Durable Function qui s'occupera
    # de le télécharger depuis SharePoint via Graph API en tâche de fond.

    log_security("INFO", "Envoi de la requête d'audit à l'Azure Function",
                 {"document_id": request.document_id, "user": user_upn})

    try:
        # Forward auth if available, append key to URL if present
        auth_headers = {}
        if req and req.headers.get("Authorization"):
            auth_headers["Authorization"] = req.headers["Authorization"]

        func_url = f"{AZURE_FUNCTION_URL}/audit"
        if AZURE_FUNCTION_KEY:
            func_url += f"?code={AZURE_FUNCTION_KEY}"

        resp = await http_client.post(
            func_url,
            json={"document_id": request.document_id, "client_context": request.client_context},
            headers=auth_headers,
            timeout=10.0
        )
        resp.raise_for_status()
        az_data = resp.json()
    except Exception as e:
        log_security("ERROR", f"Failed to start Azure Function: {e}")
        raise HTTPException(status_code=502, detail="Erreur de communication avec le moteur d'audit Azure.")

    return {
        "status": "accepted",
        "job_id": az_data.get("id"),
        "statusQueryGetUri": az_data.get("statusQueryGetUri"),
        "requested_by": user_upn
    }


@app.post("/api/planner/task")
async def api_create_planner_task(
    request: PlannerTaskRequest,
    req: Request,
    user_upn: str = Depends(verify_azure_ad_token)
):
    try:
        token = req.headers.get("Authorization", "").replace("Bearer ", "")
        log_security("INFO", f"Création tâche Planner pour {user_upn}: {request.title}")
        result = await create_planner_task(token, request.plan_id, request.bucket_id, request.title, request.due_date)
        return {"status": "success", "task_title": request.title,
                "due_date": request.due_date, "planner_task_id": result.get("id")}
    except httpx.HTTPStatusError as e:
        log_security("ERROR", f"Graph API Error: {e.response.text}")
        raise HTTPException(status_code=502, detail="Erreur Microsoft Graph.")
    except Exception as e:
        log_security("ERROR", "Planner error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création de la tâche.")


@app.post("/api/generate-fiche-rdv")
async def api_generate_fiche_rdv(
    request: FicheRDVRequest,
    user_upn: str = Depends(verify_azure_ad_token)
):
    job_id = str(uuid.uuid4())
    log_security("INFO", f"Génération fiche RDV demandée par {user_upn} pour {request.client_name}")
    try:
        # Prevent event loop blocking by offloading the synchronous file I/O to a threadpool
        import os
        os.environ["CURRENT_USER_UPN"] = user_upn
        file_path = await run_in_threadpool(
            generate_fiche_rdv,
            request.client_name,
            request.summary,
            request.alert_points,
            job_id
        )
        return {
            "status": "success",
            "job_id": job_id,
            "download_url": f"/api/download/{job_id}/{os.path.basename(file_path)}"
        }
    except Exception as e:
        log_security("ERROR", "Fiche RDV generation error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la fiche.")


@app.get("/api/download/{job_id}/{filename}")
async def download_fiche_rdv(
    job_id: str,
    filename: str,
    user_upn: str = Depends(verify_azure_ad_token)
):
    """
    [PATCH HATER] L'endpoint fantôme est réparé.
    Le fichier Word généré peut enfin être téléchargé en toute sécurité.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        log_security("WARNING", f"Tentative de Path Traversal : {filename} par {user_upn}")
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    # [SECURITY] Le segment job_id doit être un UUID connu : empêche le path
    # traversal sur le job_id lui-même (ex: job_id="..") et l'accès arbitraire.
    job_id = _validate_document_id(job_id)

    from config import load_config
    config = load_config()
    file_path = os.path.join(config.jobs_base_dir, job_id, filename)

    if not os.path.exists(file_path):
        log_security("WARNING", f"Fichier non trouvé : {file_path}")
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    # [PATCH IDOR] Verify the authenticated user owns this file
    import json
    meta_path = os.path.join(config.jobs_base_dir, job_id, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            if meta.get("user_upn") != user_upn:
                log_security("WARNING", f"Tentative IDOR par {user_upn} sur la job_id {job_id}")
                raise HTTPException(status_code=403, detail="Accès refusé.")
    else:
        # Legacy behavior: if no meta.json, restrict just in case or allow if strictly needed.
        # Strict by default:
        log_security("WARNING", f"Fichier meta.json manquant pour le job {job_id}")
        raise HTTPException(status_code=403, detail="Propriétaire non vérifiable.")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/health")
def health_check():
    """Health-check allégé depuis la purge de Celery."""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "auth": "entra-id-jwt",
        "orchestration": "azure-durable-functions"
    }


@app.get("/api/audit/{job_id}/status")
async def get_job_status(
    job_id: str,
    user_upn: str = Depends(verify_azure_ad_token)
):
    """
    Interroge le statut d'une orchestration d'audit sur Azure Durable Functions.
    Le bot Copilot interroge cet endpoint pour connaître l'avancement de l'audit.
    """
    try:
        # Appel à l'API standard des instances Durable Functions :
        # GET /runtime/webhooks/durabletask/instances/{instanceId}
        # Le task hub DOIT être configuré explicitement (pas de valeur de test
        # par défaut) afin de ne jamais interroger un hub de test en production.
        auth_param = f"&code={AZURE_FUNCTION_KEY}" if AZURE_FUNCTION_KEY else ""
        task_hub = os.environ.get("TASK_HUB_NAME")
        if not task_hub:
            log_security("ERROR", "TASK_HUB_NAME non configuré — statut d'audit indisponible")
            raise HTTPException(status_code=500, detail="Configuration du moteur d'audit incomplète.")

        import urllib.parse
        safe_job_id = urllib.parse.quote(job_id)

        resp = await http_client.get(
            f"{AZURE_FUNCTION_URL}/runtime/webhooks/durabletask/instances/{safe_job_id}"
            f"?taskHub={task_hub}&connection=Storage{auth_param}",
            timeout=5.0
        )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Job introuvable.")
        resp.raise_for_status()
        data = resp.json()

        return {
            "job_id": job_id,
            "status": data.get("runtimeStatus"),
            "result": data.get("output") if data.get("runtimeStatus") == "Completed" else None
        }
    except HTTPException:
        # Laisse passer nos réponses HTTP volontaires (404 job introuvable,
        # 500 configuration) sans les ré-emballer en 500 générique.
        raise
    except httpx.HTTPStatusError as e:
        log_security("ERROR", f"Azure Function HTTP error: {e}")
        raise HTTPException(status_code=502, detail="Erreur lors de la récupération du statut.")
    except Exception as e:
        log_security("ERROR", f"Azure Function communication error: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne de statut.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
