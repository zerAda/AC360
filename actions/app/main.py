"""onix-actions — Couche applicative d'onix (audit / génération / tâches /
notification / usage / coût / administration).

Microservice FastAPI interne (réseau onix-net, AUCUN port hôte), appelé par
l'assistant Onyx via Actions OpenAPI. 100 % local : aucun Azure / M365 / cloud.

Tous les endpoints (hors /health) sont :
  * authentifiés par clé API (header X-API-Key) ;
  * gatés par l'état d'administration (kill-switch global + flag par fonction +
    blocage utilisateur) — un flag coupé renvoie 403.

Ce module porte la LOGIQUE d'AC360 (moteur d'audit, génération .docx, trackers,
contrôles admin) en la généricisant intégralement.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from . import admin_state, cost_tracker, docgen, notify as notify_mod
from . import ocr as ocr_mod
from . import tasks as tasks_mod
from . import usage_tracker
from .audit_engine import audit as run_audit
from .audit_engine import extract_canonical_fields
from .security import require_admin, require_api_key, validate_upload

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    admin_state.init_db()
    usage_tracker.init_db()
    tasks_mod.init_db()
    yield


app = FastAPI(
    title="onix-actions",
    version="1.0.0",
    description="Couche applicative locale d'onix : audit, génération, tâches, "
    "notification, usage, coût, administration. 100 % local, sans cloud.",
    lifespan=_lifespan,
)


# ---------------------------------------------------------------------------
# Gating commun
# ---------------------------------------------------------------------------
def _gate(feature: str, caller_id: Optional[str] = None) -> None:
    """Lève 403 si la fonction est coupée (global / feature / utilisateur)."""
    user_hash = admin_state.hash_id(caller_id) if caller_id else None
    allowed, reason = admin_state.is_allowed(feature, user_id_hash=user_hash)
    if not allowed:
        raise HTTPException(status_code=403, detail=admin_state.blocked_message(reason))


def _select_reference_record(records: list, client_key: Optional[str]) -> dict:
    """Choisit l'enregistrement de référence parmi une liste : filtré par
    `client_key` (sur le nom du client) si fourni, sinon le premier."""
    if not records:
        raise HTTPException(status_code=404, detail="Référence vide.")
    if client_key:
        from .audit_engine import normalize_name

        target = normalize_name(client_key)
        for rec in records:
            if isinstance(rec, dict) and normalize_name(rec.get("nom_client")) == target:
                return rec
        raise HTTPException(status_code=404, detail="Client introuvable dans la référence.")
    first = records[0]
    if not isinstance(first, dict):
        raise HTTPException(status_code=400, detail="Référence : objet attendu.")
    return first


def _load_reference(
    reference: Optional[Any],
    reference_path: Optional[str],
    client_key: Optional[str],
) -> dict:
    """Résout l'enregistrement de référence : inline (dict OU liste) prioritaire,
    sinon fichier monté (JSON/CSV). Dans les deux cas, une liste est filtrée par
    `client_key` sur le nom du client (à défaut, le premier enregistrement)."""
    if reference is not None:
        # Inline : accepte un objet unique ou une liste d'objets (comme un
        # fichier .json), et applique la même résolution par client_key.
        records = reference if isinstance(reference, list) else [reference]
        return _select_reference_record(records, client_key)
    if not reference_path:
        raise HTTPException(
            status_code=400,
            detail="Aucune référence fournie (champ 'reference' ou 'reference_path').",
        )
    safe = os.path.abspath(reference_path)
    allowed_root = os.path.abspath(os.environ.get("ONIX_REFERENCE_DIR", "/data/reference"))
    if not (safe == allowed_root or safe.startswith(allowed_root + os.sep)):
        raise HTTPException(status_code=400, detail="Chemin de référence hors périmètre.")
    if not os.path.isfile(safe):
        raise HTTPException(status_code=404, detail="Fichier de référence introuvable.")
    try:
        if safe.lower().endswith(".json"):
            with open(safe, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = data if isinstance(data, list) else [data]
        elif safe.lower().endswith(".csv"):
            import csv

            with open(safe, "r", encoding="utf-8") as f:
                records = list(csv.DictReader(f))
        else:
            raise HTTPException(status_code=400, detail="Référence : .json ou .csv attendu.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Référence illisible.")

    return _select_reference_record(records, client_key)


# ---------------------------------------------------------------------------
# Modèles I/O
# ---------------------------------------------------------------------------
class AuditDocument(BaseModel):
    nom_client: Optional[str] = None
    plafond_hospitalisation: Optional[Any] = None
    date_effet: Optional[str] = None
    numero_contrat: Optional[str] = None
    motif_operation: Optional[str] = None


class AuditRequest(BaseModel):
    # Soit un document déjà extrait (champs canoniques), soit un texte brut.
    document: Optional[Dict[str, Any]] = None
    text: Optional[str] = Field(default=None, description="Texte brut à extraire.")
    reference: Optional[Dict[str, Any]] = None
    reference_path: Optional[str] = None
    client_key: Optional[str] = Field(
        default=None, description="Nom de client pour filtrer une référence multi-lignes."
    )
    use_llm: bool = Field(default=False, description="Extraction des champs via Ollama.")
    caller_id: Optional[str] = Field(default=None, description="Identifiant appelant (hashé).")


class FicheRequest(BaseModel):
    client_name: str
    summary: str = ""
    alert_points: str = ""
    extra_sections: Optional[Dict[str, str]] = None
    caller_id: Optional[str] = None


class TaskRequest(BaseModel):
    title: str
    due_date: Optional[str] = None
    client_id: Optional[str] = None
    notes: Optional[str] = None
    webhook_url: Optional[str] = None
    caller_id: Optional[str] = None


class NotifyRequest(BaseModel):
    provider: str = "webhook"
    message: str
    subject: Optional[str] = None
    url: Optional[str] = None
    to: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    caller_id: Optional[str] = None


class UsageRequest(BaseModel):
    event_type: str
    status: str = "ok"
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    action_name: Optional[str] = None
    document_count: int = 0
    page_count: int = 0
    estimated_tokens_input: int = 0
    estimated_tokens_output: int = 0
    estimated_cost_eur: float = 0.0


class CostEstimateRequest(BaseModel):
    cost_center: str
    quantity: float
    unit: str = "request"
    client_id: Optional[str] = None
    use_case: Optional[str] = None


class AdminControlRequest(BaseModel):
    admin_id: str = "admin"
    action: str
    scope: str = "global"
    target_id: Optional[str] = None
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# 8. Santé
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "onix-actions",
        "version": app.version,
        "ocr": ocr_mod.ocr_capabilities(),
        "global_enabled": admin_state.is_global_enabled(),
    }


# ---------------------------------------------------------------------------
# 1. Audit documentaire
# ---------------------------------------------------------------------------
def _resolve_document_fields(
    document: Optional[dict], text: Optional[str], use_llm: bool
) -> Dict[str, Any]:
    """Construit les champs canoniques du document à partir d'un dict déjà
    extrait, ou d'un texte brut (LLM si demandé, sinon heuristique OCR-like)."""
    if document:
        return document
    if not text:
        raise HTTPException(status_code=400, detail="Fournir 'document' ou 'text'.")
    if use_llm:
        _gate("llm")
        try:
            from .llm import extract_fields_llm

            fields = extract_fields_llm(text)
            usage_tracker.track("backend_action_called", action_name="llm_extract")
            if fields:
                return fields
        except Exception:
            # Repli silencieux sur l'heuristique : « en mieux » mais jamais bloquant.
            pass
    # Heuristique locale : libellés "clé: valeur" -> champs canoniques.
    pseudo_ocr = {"fields": ocr_mod._kv_pairs_from_text(text), "tables": []}
    return extract_canonical_fields(pseudo_ocr)


@app.post("/audit")
def audit_endpoint(req: AuditRequest, _: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("audit", req.caller_id)
    usage_tracker.track(
        "audit_documentaire_started", user_id=req.caller_id, action_name="audit"
    )
    document = _resolve_document_fields(req.document, req.text, req.use_llm)
    reference = _load_reference(req.reference, req.reference_path, req.client_key)
    result = run_audit({"document": document, "reference": reference})
    usage_tracker.track(
        "audit_documentaire_completed",
        user_id=req.caller_id,
        client_id=result.get("client_document"),
        action_name="audit",
        document_count=1,
    )
    return result


@app.post("/audit/file")
async def audit_file_endpoint(
    file: UploadFile = File(...),
    reference: Optional[str] = Form(default=None),
    reference_path: Optional[str] = Form(default=None),
    client_key: Optional[str] = Form(default=None),
    use_llm: bool = Form(default=False),
    caller_id: Optional[str] = Form(default=None),
    _: str = Depends(require_api_key),
) -> Dict[str, Any]:
    """Audit à partir d'un FICHIER (PDF/image) : OCR local -> extraction ->
    comparaison. Dégrade proprement si l'OCR est indisponible."""
    _gate("audit", caller_id)
    _gate("ocr", caller_id)
    data = await file.read()
    validate_upload(file.filename or "", len(data))

    usage_tracker.track("ocr_started", user_id=caller_id, action_name="audit_file")
    ocr_out = ocr_mod.extract(data, file.filename or "document")
    mode = ocr_out["metadata"]["extraction_mode"]
    if mode == "unavailable":
        usage_tracker.track("ocr_failed", status="error", user_id=caller_id,
                            error_code="ocr_unavailable")
        if not use_llm:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Extraction OCR indisponible",
                    "reason": ocr_out["metadata"].get("reason"),
                    "hint": "Activez l'OCR (tesseract/poppler) ou fournissez un texte/JSON déjà extrait.",
                },
            )
    usage_tracker.track("ocr_completed", user_id=caller_id,
                        page_count=ocr_out["metadata"].get("pages", 0))

    # Champs : LLM sur le texte si demandé, sinon extraction canonique OCR.
    if use_llm and ocr_out.get("text"):
        document = _resolve_document_fields(None, ocr_out["text"], True)
    else:
        document = extract_canonical_fields(ocr_out)

    if reference:
        try:
            ref_inline = json.loads(reference)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Champ 'reference' invalide : JSON attendu (objet ou liste d'objets).",
            )
    else:
        ref_inline = None
    reference_record = _load_reference(ref_inline, reference_path, client_key)
    result = run_audit({"document": document, "reference": reference_record})
    result["_ocr_mode"] = mode
    usage_tracker.track("audit_documentaire_completed", user_id=caller_id,
                        client_id=result.get("client_document"), document_count=1)
    return result


# ---------------------------------------------------------------------------
# 2. Génération de fiche .docx + téléchargement
# ---------------------------------------------------------------------------
@app.post("/generate/fiche")
def generate_fiche_endpoint(req: FicheRequest, _: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("generate", req.caller_id)
    try:
        out = docgen.generate_fiche(
            req.client_name, req.summary, req.alert_points,
            extra_sections=req.extra_sections,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    usage_tracker.track("fiche_generated", user_id=req.caller_id,
                        client_id=req.client_name, action_name="generate_fiche")
    return {
        "status": "success",
        "job_id": out["job_id"],
        "filename": out["filename"],
        "download_url": f"/download/{out['job_id']}",
    }


@app.get("/download/{job_id}")
def download_endpoint(job_id: str, _: str = Depends(require_api_key)) -> FileResponse:
    _gate("generate")
    base = os.path.join(docgen.jobs_dir(), os.path.basename(job_id))
    if not os.path.isdir(base):
        raise HTTPException(status_code=404, detail="Job introuvable.")
    docx_files = [f for f in os.listdir(base) if f.lower().endswith(".docx")]
    if not docx_files:
        raise HTTPException(status_code=404, detail="Aucun fichier pour ce job.")
    try:
        path = docgen.resolve_download(job_id, docx_files[0])
    except (PermissionError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return FileResponse(
        path=path,
        filename=docx_files[0],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ---------------------------------------------------------------------------
# 3. Tâches / relances locales
# ---------------------------------------------------------------------------
@app.post("/tasks")
def create_task_endpoint(req: TaskRequest, _: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("tasks", req.caller_id)
    try:
        record = tasks_mod.create_task(
            title=req.title, due_date=req.due_date, client_id=req.client_id,
            owner=req.caller_id, notes=req.notes, webhook_url=req.webhook_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Push optionnel vers un système externe.
    if req.webhook_url:
        res = notify_mod.send_webhook(
            f"Nouvelle tâche: {req.title}" + (f" (échéance {req.due_date})" if req.due_date else ""),
            url=req.webhook_url,
        )
        tasks_mod.update_webhook_status(record["task_id"], res.get("status", "unknown"))
        record["webhook_status"] = res.get("status")
    usage_tracker.track("task_created", user_id=req.caller_id, action_name="create_task")
    record.pop("webhook_url", None)
    return record


@app.get("/tasks")
def list_tasks_endpoint(
    status: Optional[str] = None, _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    _gate("tasks")
    try:
        items = tasks_mod.list_tasks(status=status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"count": len(items), "tasks": items}


# ---------------------------------------------------------------------------
# 4. Notification
# ---------------------------------------------------------------------------
@app.post("/notify")
def notify_endpoint(req: NotifyRequest, _: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("notify", req.caller_id)
    result = notify_mod.notify(
        provider=req.provider, message=req.message, subject=req.subject,
        url=req.url, to=req.to, extra=req.extra,
    )
    usage_tracker.track(
        "notification_sent",
        status="ok" if result.get("status") in ("sent", "skipped") else "error",
        user_id=req.caller_id, action_name=f"notify_{req.provider}",
    )
    return result


# ---------------------------------------------------------------------------
# 5. Usage
# ---------------------------------------------------------------------------
@app.post("/usage")
def usage_endpoint(req: UsageRequest, _: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("usage")
    try:
        event = usage_tracker.track(
            req.event_type, status=req.status, user_id=req.user_id,
            client_id=req.client_id, action_name=req.action_name,
            document_count=req.document_count, page_count=req.page_count,
            estimated_tokens_input=req.estimated_tokens_input,
            estimated_tokens_output=req.estimated_tokens_output,
            estimated_cost_eur=req.estimated_cost_eur,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"recorded": True, "event_id": event["event_id"]}


@app.get("/usage/summary")
def usage_summary_endpoint(_: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("usage")
    return usage_tracker.summary()


# ---------------------------------------------------------------------------
# 6. Coût (FinOps)
# ---------------------------------------------------------------------------
@app.get("/cost")
def cost_endpoint(_: str = Depends(require_api_key)) -> Dict[str, Any]:
    _gate("cost")
    spent = usage_tracker.summary().get("estimated_cost_eur", 0.0)
    return {
        "rate_card": cost_tracker.load_rate_card(),
        "spent_eur": spent,
        "budget": cost_tracker.check_budget(spent),
    }


@app.post("/cost/estimate")
def cost_estimate_endpoint(
    req: CostEstimateRequest, _: str = Depends(require_api_key)
) -> Dict[str, Any]:
    _gate("cost")
    try:
        est = cost_tracker.estimate_cost(
            req.cost_center, req.quantity, unit=req.unit,
            client_id=req.client_id, use_case=req.use_case,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    usage_tracker.track("cost_estimated", estimated_cost_eur=est["estimated_cost_eur"])
    return est


# ---------------------------------------------------------------------------
# 7. Administration (kill-switch / flags / blocage)
# ---------------------------------------------------------------------------
@app.post("/admin/control")
def admin_control_endpoint(
    req: AdminControlRequest, _: str = Depends(require_admin)
) -> Dict[str, Any]:
    record = admin_state.apply_control(
        admin_id=req.admin_id, action=req.action, scope=req.scope,
        target_id=req.target_id, reason=req.reason,
    )
    if record["result"] == "noop":
        return JSONResponse(status_code=400, content=record)
    return record


@app.get("/admin/state")
def admin_state_endpoint(_: str = Depends(require_admin)) -> Dict[str, Any]:
    return admin_state.current_state()
