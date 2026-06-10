from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional
import os
import re
import uuid
import time
import httpx
import asyncio
from collections import defaultdict
from planner_integration import create_planner_task
from generate_fiche_rdv import generate_fiche_rdv
from auth import verify_azure_ad_token
from safe_logger import log_security
from feature_flags import is_allowed, blocked_message, hash_id
from usage_tracker import track
from graph_obo import acquire_obo_graph_token, obo_configured


def _truthy(val) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "on", "enabled")


_DOCID_FORBIDDEN = re.compile(r"[/\\\s;'\"<>`]|\.\.|\x00")
_DOCID_MAX_LEN = 512


def _validate_sharepoint_doc_id(document_id: str) -> str:
    if not document_id or not isinstance(document_id, str):
        raise HTTPException(status_code=400, detail="document_id manquant.")
    if len(document_id) > _DOCID_MAX_LEN:
        raise HTTPException(status_code=400, detail="document_id invalide (trop long).")
    if _DOCID_FORBIDDEN.search(document_id):
        raise HTTPException(status_code=400, detail="document_id invalide (caractères interdits).")
    return document_id


_PLANNER_PLACEHOLDER_PLAN = {"", "DEFAULT_PLAN"}
_PLANNER_PLACEHOLDER_BUCKET = {"", "DEFAULT_BUCKET"}
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _resolve_planner_params(plan_id, bucket_id, due_date):
    plan = plan_id if plan_id not in _PLANNER_PLACEHOLDER_PLAN \
        else os.environ.get("PLANNER_DEFAULT_PLAN_ID", "")
    bucket = bucket_id if bucket_id not in _PLANNER_PLACEHOLDER_BUCKET \
        else os.environ.get("PLANNER_DEFAULT_BUCKET_ID", "")
    due = due_date
    if due_date and _DATE_ONLY_RE.match(str(due_date).strip()):
        due = str(due_date).strip() + "T00:00:00Z"
    return plan, bucket, due


app = FastAPI(
    title="AC360 Audit Engine API",
    description="API Enterprise Grade - Passerelle vers Azure Durable Functions",
    version="3.0.0"
)

AZURE_FUNCTION_URL = os.environ.get("AZURE_FUNCTION_URL", "http://localhost:7071/api")
AZURE_FUNCTION_KEY = os.environ.get("AZURE_FUNCTION_KEY", "")
AZURE_FUNCTION_HOST = AZURE_FUNCTION_URL.rstrip("/")
if AZURE_FUNCTION_HOST.endswith("/api"):
    AZURE_FUNCTION_HOST = AZURE_FUNCTION_HOST[: -len("/api")]
AZURE_DURABLE_KEY = os.environ.get("AZURE_DURABLE_KEY", "") or AZURE_FUNCTION_KEY
http_client = httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=50, max_connections=200))


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()


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
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(AppInsightsMiddleware)

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
        await asyncio.sleep(0)
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


def _validate_document_id(document_id: str) -> str:
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

    try:
        if os.path.commonpath([resolved, base]) != base:
            raise HTTPException(status_code=400, detail="Identifiant invalide.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant invalide.")

    if not os.path.isdir(resolved):
        raise HTTPException(status_code=404, detail="Ressource introuvable.")

    return normalized


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


_AUDIT_OWNER_MAX = 5000
_audit_job_owners: dict = {}


def _record_audit_owner(job_id, user_upn):
    if not job_id:
        return
    if len(_audit_job_owners) >= _AUDIT_OWNER_MAX:
        _audit_job_owners.clear()
    _audit_job_owners[job_id] = user_upn


def _assert_audit_owner(job_id, user_upn):
    owner = _audit_job_owners.get(job_id)
    if owner is not None and owner != user_upn:
        log_security("WARNING",
                     "Accès refusé au statut d'un audit appartenant à un autre utilisateur",
                     {"user": user_upn})
        raise HTTPException(status_code=403, detail="Accès refusé à ce job d'audit.")


@app.post("/api/audit")
async def trigger_audit(
    request: AuditRequest,
    req: Request,
    user_upn: str = Depends(verify_azure_ad_token)
):
    await _check_rate_limit(user_upn)
    _validate_sharepoint_doc_id(request.document_id)

    _user_hash = hash_id(user_upn)
    _allowed, _reason = is_allowed("audit", user_id_hash=_user_hash)
    if not _allowed:
        track("audit_documentaire_started", status="blocked",
              user_id=user_upn, action_name="trigger_audit", error_code=_reason)
        raise HTTPException(status_code=403, detail=blocked_message(_reason))
    track("audit_documentaire_started", status="ok",
          user_id=user_upn, action_name="trigger_audit")

    log_security("INFO", "Envoi de la requête d'audit à l'Azure Function",
                 {"document_id": request.document_id, "user": user_upn})

    auth_headers = {}
    if req and req.headers.get("Authorization"):
        auth_headers["Authorization"] = req.headers["Authorization"]

    # On-Behalf-Of : échange le token utilisateur contre un token Graph délégué.
    # Le téléchargement SharePoint s'effectuera AVEC les permissions de
    # l'utilisateur (superposition RBAC). Sans OBO, l'accès reste applicatif côté
    # Function : AC360_REQUIRE_OBO=true ferme alors la porte (prod stricte).
    raw_auth = req.headers.get("Authorization", "") if req else ""
    if obo_configured():
        try:
            graph_token = await run_in_threadpool(acquire_obo_graph_token, raw_auth)
            auth_headers["X-MS-Graph-Token"] = graph_token
        except Exception as e:
            log_security("ERROR", f"OBO exchange failed: {e}")
            raise HTTPException(status_code=502, detail="Échec de l'autorisation déléguée (OBO).")
    elif _truthy(os.environ.get("AC360_REQUIRE_OBO")):
        log_security("ERROR", "OBO requis (AC360_REQUIRE_OBO) mais non configuré")
        raise HTTPException(status_code=503,
                            detail="Autorisation déléguée requise mais non configurée.")

    try:
        func_url = f"{AZURE_FUNCTION_URL}/audit"
        if AZURE_FUNCTION_KEY:
            func_url += f"?code={AZURE_FUNCTION_KEY}"

        resp = await http_client.post(
            func_url,
            json={"document_id": request.document_id, "client_context": request.client_context},
            headers=auth_headers,
            timeout=30.0
        )
        # Refus Graph propagé : l'utilisateur n'a pas accès au document (403) ou
        # il est introuvable (404) — on ne masque pas en 502.
        if resp.status_code in (403, 404):
            track("audit_documentaire_started", status="blocked",
                  user_id=user_upn, action_name="trigger_audit", error_code="sharepoint_denied")
            raise HTTPException(status_code=resp.status_code,
                                detail="Accès refusé à ce document ou document introuvable.")
        resp.raise_for_status()
        az_data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        log_security("ERROR", f"Failed to start Azure Function: {e}")
        raise HTTPException(status_code=502, detail="Erreur de communication avec le moteur d'audit Azure.")

    _record_audit_owner(az_data.get("id"), user_upn)

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
        plan_id, bucket_id, due_date = _resolve_planner_params(
            request.plan_id, request.bucket_id, request.due_date)
        if not plan_id or not bucket_id:
            raise HTTPException(
                status_code=400,
                detail="Plan/bucket Planner non configuré "
                       "(définir PLANNER_DEFAULT_PLAN_ID / PLANNER_DEFAULT_BUCKET_ID).")
        log_security("INFO", f"Création tâche Planner pour {user_upn}: {request.title}")
        result = await create_planner_task(token, plan_id, bucket_id, request.title, due_date)
        return {"status": "success", "task_title": request.title,
                "due_date": due_date, "planner_task_id": result.get("id")}
    except HTTPException:
        raise
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
    if ".." in filename or "/" in filename or "\\" in filename:
        log_security("WARNING", f"Tentative de Path Traversal : {filename} par {user_upn}")
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    job_id = _validate_document_id(job_id)

    from config import load_config
    config = load_config()
    file_path = os.path.join(config.jobs_base_dir, job_id, filename)

    if not os.path.exists(file_path):
        log_security("WARNING", f"Fichier non trouvé : {file_path}")
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    import json
    meta_path = os.path.join(config.jobs_base_dir, job_id, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            if meta.get("user_upn") != user_upn:
                log_security("WARNING", f"Tentative IDOR par {user_upn} sur la job_id {job_id}")
                raise HTTPException(status_code=403, detail="Accès refusé.")
    else:
        log_security("WARNING", f"Fichier meta.json manquant pour le job {job_id}")
        raise HTTPException(status_code=403, detail="Propriétaire non vérifiable.")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/health")
def health_check():
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
    _assert_audit_owner(job_id, user_upn)

    try:
        auth_param = f"&code={AZURE_DURABLE_KEY}" if AZURE_DURABLE_KEY else ""
        task_hub = os.environ.get("TASK_HUB_NAME")
        if not task_hub:
            log_security("ERROR", "TASK_HUB_NAME non configuré — statut d'audit indisponible")
            raise HTTPException(status_code=500, detail="Configuration du moteur d'audit incomplète.")

        import urllib.parse
        safe_job_id = urllib.parse.quote(job_id)

        resp = await http_client.get(
            f"{AZURE_FUNCTION_HOST}/runtime/webhooks/durabletask/instances/{safe_job_id}"
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
        raise
    except httpx.HTTPStatusError as e:
        log_security("ERROR", f"Azure Function HTTP error: {e}")
        raise HTTPException(status_code=502, detail="Erreur lors de la récupération du statut.")
    except Exception as e:
        log_security("ERROR", f"Azure Function communication error: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne de statut.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)  # nosec B104
