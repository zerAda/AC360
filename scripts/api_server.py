from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
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
import urllib.parse
from collections import defaultdict
from planner_integration import create_planner_task
from generate_fiche_rdv import generate_fiche_rdv
from auth import verify_azure_ad_token
from safe_logger import log_security, redact, redact_mapping
from feature_flags import is_allowed, blocked_message, hash_id
from usage_tracker import track
from graph_obo import acquire_obo_graph_token_retrying, obo_configured
from audit_trail import emit_document_access
from telemetry import setup_telemetry


def _redacted_detail(generic: str, *sensitive: object) -> str:
    """Construit un message d'erreur client neutralisé : un texte générique suivi
    d'une portion redactée (via la SEULE surface auditée ``safe_logger.redact``)
    de toute valeur dynamique (exception, valeur utilisateur). Aucune PII / aucun
    secret ne fuit dans le corps de réponse (Pitfall 5)."""
    if not sensitive:
        return generic
    safe = redact(" ".join(str(s) for s in sensitive if s is not None))
    return f"{generic} ({safe})" if safe else generic


def _truthy(val) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "on", "enabled")


_DOCID_FORBIDDEN = re.compile(r"[/\\\s;'\"<>`]|\.\.|\x00")
_DOCID_MAX_LEN = 512
# Plancher de longueur (R1) : un drive-item-id SharePoint est un jeton opaque
# long (~34 caractères). Un id trop court ne peut jamais résoudre ; on le rejette
# AVANT de consommer un quota ou de démarrer une orchestration Durable vouée à
# l'échec. Plancher fixé au minimum déjà couvert par le contrat de validation
# (test_hostile_review : id valides >= 10), donc compatible et conservateur.
_DOCID_MIN_LEN = 10


def _validate_sharepoint_doc_id(document_id: str) -> str:
    if not document_id or not isinstance(document_id, str):
        raise HTTPException(status_code=400, detail="document_id manquant.")
    if len(document_id) > _DOCID_MAX_LEN:
        raise HTTPException(status_code=400, detail="document_id invalide (trop long).")
    if len(document_id) < _DOCID_MIN_LEN:
        raise HTTPException(status_code=400, detail="document_id invalide (trop court).")
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


@app.on_event("startup")
async def startup_event():
    # Câble l'exportateur Azure Monitor UNE SEULE FOIS au démarrage, avant de
    # servir le trafic (OBS-01). setup_telemetry est gate-inerte hors prod
    # (early-return quand le gate AppInsights est fermé) ; on l'enveloppe malgré
    # tout dans try/except pour qu'une misconfig ne lève JAMAIS dans le démarrage.
    try:
        setup_telemetry()
    except Exception:  # pragma: no cover - filet défensif au démarrage
        pass


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()


class AppInsightsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        if os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY"):
            # Les dimensions traversent la frontière vers App Insights : on route
            # toutes les valeurs par la seule surface de redaction auditée avant
            # émission (aucune PII / aucun secret ne fuit — AUD-06).
            log_security("INFO", "AppInsights_Telemetry", redact_mapping({
                "method": request.method,
                "url": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(process_time * 1000, 2)
            }))

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
# CB-04 : garde anti-réentrance pour la purge — au plus UNE tâche concurrente.
_cleanup_task: Optional[asyncio.Task] = None


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


def _maybe_spawn_cleanup() -> None:
    """CB-04 : lance la purge UNE seule fois tant qu'une instance tourne. Sans cette
    garde, chaque requête au-dessus du seuil lançait une coroutine fire-and-forget
    supplémentaire (réécritures concurrentes du store, lost-update sur les compteurs,
    tâches non tracées). La référence est conservée pour éviter un GC prématuré."""
    global _cleanup_task
    if len(_rate_limit_store) > 1000 and (_cleanup_task is None or _cleanup_task.done()):
        _cleanup_task = asyncio.create_task(cleanup_rate_limits())


async def _check_rate_limit(upn: str) -> None:
    now = time.time()
    _maybe_spawn_cleanup()

    _rate_limit_store[upn] = [t for t in _rate_limit_store[upn] if now - t < _RATE_LIMIT_WINDOW]

    if len(_rate_limit_store[upn]) >= _RATE_LIMIT_MAX:
        log_security("WARNING", f"Rate limit dépassé pour {upn}")
        raise HTTPException(
            status_code=429,
            detail=(f"Quota dépassé : maximum {_RATE_LIMIT_MAX} audits par heure.")
        )
    _rate_limit_store[upn].append(now)


# Quota distinct (plus généreux) pour la résolution documentaire : une recherche
# ne doit pas consommer le quota d'audits.
_RESOLVE_RATE_MAX = 60


async def _check_resolve_rate_limit(upn: str) -> None:
    # Même garde de débordement que `_check_rate_limit` : le chemin résolution
    # écrit des clés `resolve:{upn}` dans le MÊME store partagé. Sans ce garde,
    # un déploiement dominé par la recherche accumule des clés jamais purgées
    # (croissance non bornée clé par identité). cleanup_rate_limits() purge les
    # listes vides quel que soit leur préfixe.
    _maybe_spawn_cleanup()
    key = f"resolve:{upn}"
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < _RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[key]) >= _RESOLVE_RATE_MAX:
        log_security("WARNING", f"Rate limit recherche dépassé pour {upn}")
        raise HTTPException(
            status_code=429,
            detail=f"Quota dépassé : maximum {_RESOLVE_RATE_MAX} recherches par heure.")
    _rate_limit_store[key].append(now)


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


class DocumentResolveRequest(BaseModel):
    query: str
    choice: Optional[int] = None


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


def _assert_durable_owner(data, oid):
    """Gate IDOR AUTORITAIRE (AUD-03) : compare le ``owner_hash`` persisté dans
    l'entrée d'orchestration Durable (stockage partagé, robuste au scale-out et au
    redémarrage) à ``hash_id(oid)`` de l'appelant — la map mémoire ``_assert_audit_owner``
    n'est qu'un fast-path/cache. Hard-fail en 403 sur NON-CORRESPONDANCE (la menace
    IDOR réelle : un autre oid lisant le job d'autrui).

    FAIL-CLOSED (WR-01) : depuis le cutover oid (clean-cutover, app jamais
    déployée), TOUT nouveau job porte un ``owner_hash``. Un job dans un état
    TERMINAL (``Completed`` / ``Failed`` / ``Terminated``) dont l'``owner_hash``
    est absent ne peut donc plus être un job légitime en attente de surface :
    c'est soit un job legacy (inexistant en clean-cutover) soit une réponse de
    statut dégradée. On refuse alors (403) plutôt que d'accorder l'accès — le
    gate « autoritaire » est ainsi réellement fail-closed. La fenêtre transitoire
    PRÉ-input (états non terminaux : ``Pending`` / ``Running``, ou job introuvable
    sans état) reste tolérée pour ne pas casser les shapes de statut qui ne
    portent légitimement jamais d'``owner_hash``."""
    import json as _json
    inp = data.get("input")
    if isinstance(inp, str):
        try:
            inp = _json.loads(inp)
        except (ValueError, TypeError):
            inp = None
    owner_hash = inp.get("owner_hash") if isinstance(inp, dict) else None
    runtime_status = data.get("runtimeStatus")
    if owner_hash:
        if owner_hash != hash_id(oid):
            log_security("WARNING",
                         "Accès refusé au statut d'audit (owner_hash Durable ne correspond pas)",
                         {"oid_hash": hash_id(oid)})
            raise HTTPException(status_code=403, detail="Accès refusé à ce job d'audit.")
        return
    # owner_hash absent : on ne tolère que la fenêtre transitoire pré-input
    # (états non terminaux). Sur un état terminal, refus fail-closed.
    if runtime_status in ("Completed", "Failed", "Terminated"):
        log_security("WARNING",
                     "Statut terminal sans owner_hash Durable — refus fail-closed (WR-01)",
                     {"oid_hash": hash_id(oid)})
        raise HTTPException(status_code=403, detail="Accès refusé à ce job d'audit.")


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


async def _assert_user_can_access_document(graph_token: str, document_id: str) -> None:
    """Échec rapide : vérifie AVEC le token délégué de l'utilisateur qu'il a accès
    au document SharePoint, avant de déclencher l'orchestration. Best-effort — un
    drive non configuré ou une erreur transitoire ne bloque pas (le téléchargement
    as-user côté Function reste le contrôle faisant autorité)."""
    drive_id = os.environ.get("SHAREPOINT_DRIVE_ID")
    if not drive_id or not graph_token:
        return
    try:
        resp = await http_client.get(
            f"{GRAPH_BASE}/drives/{drive_id}/items/{document_id}",
            params={"$select": "id"},
            headers={"Authorization": f"Bearer {graph_token}"},
            timeout=10.0,
        )
    except Exception as e:
        log_security("WARNING", f"Pré-vérification d'accès indisponible: {e}")
        return
    if resp.status_code in (403, 404):
        log_security("WARNING", "Accès SharePoint refusé (pré-vérification as-user)",
                     {"status": resp.status_code})
        raise HTTPException(status_code=resp.status_code,
                            detail="Accès refusé à ce document ou document introuvable.")


def _shape_status_response(job_id, data):
    """Met à plat la réponse Durable en un contrat de présentation stable : le
    verdict et les champs remontent au premier niveau (évite un JSON doublement
    imbriqué et un rendu fragile côté Copilot). `result` reste pour rétro-compat.
    Tolérant : accepte une sortie plate ou imbriquée (output.result)."""
    runtime_status = data.get("runtimeStatus")
    completed = runtime_status == "Completed"
    output = data.get("output") if completed else None
    output = output if isinstance(output, dict) else {}
    audit = output.get("result")
    audit = audit if isinstance(audit, dict) else output
    return {
        "job_id": job_id,
        "status": runtime_status,
        "audit_status": output.get("status"),
        "verdict": audit.get("verdict"),
        "client_document": audit.get("client_document"),
        "reference_fabric": audit.get("meilleur_match_fabric"),
        "score_nom": audit.get("score_correspondance_nom"),
        "fields": audit.get("fields"),
        "fic_available": bool(output.get("fic_path")),
        "error": output.get("error"),
        "result": output if completed else None,
    }


@app.post("/api/audit")
async def trigger_audit(
    request: AuditRequest,
    req: Request,
    oid: str = Depends(verify_azure_ad_token)
):
    # La dépendance verify_azure_ad_token retourne l'Entra Object ID immuable
    # (Plan 01-02) : `oid` est la SEULE clé d'appartenance/de quota. L'upn mutable
    # n'est jamais utilisé comme clé (cause racine de l'IDOR par réutilisation
    # d'upn — AUD-02/03). Le nom de paramètre porte explicitement `oid`.
    # CB-02 : valider AVANT de consommer le quota — une entrée invalide (format,
    # longueur, caractères interdits) ne doit jamais décompter un des 10 audits/h.
    _validate_sharepoint_doc_id(request.document_id)
    await _check_rate_limit(oid)

    _user_hash = hash_id(oid)
    _allowed, _reason = is_allowed("audit", user_id_hash=_user_hash)
    if not _allowed:
        track("audit_documentaire_started", status="blocked",
              user_id=oid, action_name="trigger_audit", error_code=_reason)
        raise HTTPException(status_code=403, detail=blocked_message(_reason))
    track("audit_documentaire_started", status="ok",
          user_id=oid, action_name="trigger_audit")

    # AUD-07 : piste d'audit d'accès document émise au point d'accès portant l'oid
    # (seul site qui le détient — l'entrée Durable ne porte que l'owner_hash à sens
    # unique). Seam gaté/inerte sans APPINSIGHTS ; 4 champs verrouillés, sans PII brute.
    emit_document_access(oid=oid, document_id=request.document_id)

    log_security("INFO", "Envoi de la requête d'audit à l'Azure Function",
                 {"document_id": request.document_id, "oid_hash": _user_hash})

    auth_headers = {}
    if req and req.headers.get("Authorization"):
        auth_headers["Authorization"] = req.headers["Authorization"]

    # On-Behalf-Of : échange le token utilisateur contre un token Graph délégué.
    # Le téléchargement SharePoint s'effectuera AVEC les permissions de
    # l'utilisateur (superposition RBAC). Sans OBO, l'accès reste applicatif côté
    # Function : AC360_REQUIRE_OBO=true ferme alors la porte (prod stricte).
    raw_auth = req.headers.get("Authorization", "") if req else ""
    graph_token = None
    if obo_configured():
        try:
            # Wrapper avec backoff borné, réessais sur erreurs transitoires (AUD-05).
            graph_token = await run_in_threadpool(acquire_obo_graph_token_retrying, raw_auth)
            auth_headers["X-MS-Graph-Token"] = graph_token
        except Exception as e:
            # Épuisement des réessais = indisponibilité transitoire -> 503 (retriable),
            # pas 502 (qui suggèrerait à tort un upstream défaillant). Détail redacté.
            log_security("ERROR", f"OBO exchange failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=_redacted_detail(
                    "Échec de l'autorisation déléguée (OBO) — réessayez.", e))
    elif _truthy(os.environ.get("AC360_REQUIRE_OBO")):
        log_security("ERROR", "OBO requis (AC360_REQUIRE_OBO) mais non configuré")
        raise HTTPException(status_code=503,
                            detail="Autorisation déléguée requise mais non configurée.")

    # Échec rapide au bord : si l'utilisateur n'a pas accès au document, on refuse
    # AVANT de démarrer l'orchestration (le contrôle as-user côté Function reste
    # le garant final).
    if graph_token:
        try:
            await _assert_user_can_access_document(graph_token, request.document_id)
        except HTTPException:
            track("audit_documentaire_started", status="blocked", user_id=oid,
                  action_name="trigger_audit", error_code="sharepoint_denied")
            raise

    try:
        func_url = f"{AZURE_FUNCTION_URL}/audit"
        if AZURE_FUNCTION_KEY:
            func_url += f"?code={AZURE_FUNCTION_KEY}"

        resp = await http_client.post(
            func_url,
            json={"document_id": request.document_id,
                  "client_context": request.client_context,
                  # Appartenance persistée DANS l'entrée d'orchestration Durable
                  # (stockage partagé) -> contrôle IDOR robuste au redémarrage et
                  # au scale-out, contrairement à la map mémoire (fast-path seul).
                  "owner_hash": hash_id(oid)},
            headers=auth_headers,
            timeout=30.0
        )
        # Refus Graph propagé : l'utilisateur n'a pas accès au document (403) ou
        # il est introuvable (404) — on ne masque pas en 502.
        if resp.status_code in (403, 404):
            track("audit_documentaire_started", status="blocked",
                  user_id=oid, action_name="trigger_audit", error_code="sharepoint_denied")
            raise HTTPException(status_code=resp.status_code,
                                detail="Accès refusé à ce document ou document introuvable.")
        resp.raise_for_status()
        az_data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        log_security("ERROR", f"Failed to start Azure Function: {e}")
        raise HTTPException(status_code=502, detail="Erreur de communication avec le moteur d'audit Azure.")

    # Fast-path mémoire (cache) : le contrôle Durable autoritaire reste _assert_durable_owner.
    _record_audit_owner(az_data.get("id"), oid)

    # SÉCURITÉ : on n'expose JAMAIS le `statusQueryGetUri` Durable — il porte une
    # clé SAS `?code=` qui permettrait à quiconque lit le transcript/trace de
    # poller (ou rejouer) le job d'un autre utilisateur, hors de tout contrôle
    # IDOR. Le client poll l'endpoint passerelle gété `/api/audit/{job_id}/status`
    # (server-side, _assert_durable_owner) avec SON propre jeton. Chemin relatif,
    # aucun secret ne quitte la passerelle.
    _job_id = az_data.get("id")
    return {
        "status": "accepted",
        "job_id": _job_id,
        "status_url": f"/api/audit/{_job_id}/status",
        "requested_by": oid
    }


# Extensions auditables (alignées sur l'allowlist de téléchargement Function).
_AUDITABLE_EXT = (".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".tif")
_RESOLVE_QUERY_MIN, _RESOLVE_QUERY_MAX = 2, 200


def _validate_resolve_query(query: str) -> str:
    q = (query or "").strip()
    if not (_RESOLVE_QUERY_MIN <= len(q) <= _RESOLVE_QUERY_MAX):
        raise HTTPException(status_code=400,
                            detail="Recherche invalide (2 à 200 caractères).")
    if re.search(r"[\x00-\x1f\x7f]", q):
        raise HTTPException(status_code=400,
                            detail="Recherche invalide (caractères interdits).")
    return q


@app.post("/api/documents/resolve")
async def resolve_document(
    request: DocumentResolveRequest,
    req: Request,
    user_upn: str = Depends(verify_azure_ad_token)
):
    """Résout un document auditable depuis une recherche en langage naturel
    (« contrat GEREP ») via Graph **au nom de l'utilisateur** (OBO) : seuls les
    documents auxquels IL a accès remontent. Évite d'exiger un drive-item-id."""
    await _check_resolve_rate_limit(user_upn)
    q = _validate_resolve_query(request.query)

    drive_id = os.environ.get("SHAREPOINT_DRIVE_ID")
    if not drive_id:
        raise HTTPException(status_code=503,
                            detail="Recherche documentaire non configurée (SHAREPOINT_DRIVE_ID).")
    if not obo_configured():
        raise HTTPException(status_code=503,
                            detail="Recherche au nom de l'utilisateur non configurée (OBO).")

    raw_auth = req.headers.get("Authorization", "") if req else ""
    try:
        # Wrapper avec backoff borné, réessais sur erreurs transitoires (AUD-05).
        graph_token = await run_in_threadpool(acquire_obo_graph_token_retrying, raw_auth)
    except Exception as e:
        # Épuisement = indisponibilité transitoire -> 503 (retriable), pas 502.
        # Détail dynamique via le canal `data` redacté (message statique).
        log_security("ERROR", "OBO exchange failed (resolve)", {"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail=_redacted_detail("Échec de l'autorisation déléguée (OBO).", e))

    # Littéral OData : quote simple doublée, puis URL-encode du segment.
    safe_q = urllib.parse.quote(q.replace("'", "''"), safe="")
    try:
        resp = await http_client.get(
            f"{GRAPH_BASE}/drives/{drive_id}/root/search(q='{safe_q}')",
            params={"$select": "id,name,lastModifiedDateTime,parentReference", "$top": "25"},
            headers={"Authorization": f"Bearer {graph_token}"},
            timeout=15.0,
        )
    except Exception as e:
        log_security("ERROR", "Graph search error", {"error": str(e)})
        raise HTTPException(status_code=502, detail="Recherche SharePoint indisponible.")
    if resp.status_code == 403:
        log_security("WARNING", "Recherche SharePoint refusée (as-user)")
        raise HTTPException(status_code=403, detail="Accès SharePoint refusé.")
    if resp.status_code >= 400:
        log_security("ERROR", f"Graph search HTTP {resp.status_code}")
        raise HTTPException(status_code=502, detail="Recherche SharePoint indisponible.")

    docs = []
    for it in (resp.json() or {}).get("value", []) or []:
        name = str(it.get("name") or "")
        if os.path.splitext(name)[1].lower() not in _AUDITABLE_EXT:
            continue
        folder = str(((it.get("parentReference") or {}).get("path") or ""))
        folder = folder.split("root:", 1)[-1].lstrip("/") or "racine"
        docs.append({
            "id": it.get("id"),
            "name": name,
            "modified": str(it.get("lastModifiedDateTime") or "")[:10],
            "folder": folder,
        })
    # CB-01 : clé secondaire stable (`id`) — la date `modified` est tronquée au jour,
    # donc les documents du même jour s'égalisent ; sans départage déterministe,
    # l'ordre dépend du retour Graph (non garanti identique d'un appel à l'autre) et
    # un `choice` positionnel pouvait résoudre un AUTRE document que celui affiché.
    docs.sort(key=lambda d: (d["modified"], str(d["id"])), reverse=True)
    docs = docs[:5]
    count = len(docs)

    track("backend_action_called", user_id=user_upn, action_name="resolve_document")

    if count == 0:
        return {"count": 0}
    if request.choice is not None:
        if not (1 <= int(request.choice) <= count):
            raise HTTPException(status_code=400, detail=f"Choix invalide (1 à {count}).")
        chosen = docs[int(request.choice) - 1]
        return {"count": count, "single": True,
                "document_id": chosen["id"], "document_name": chosen["name"]}
    if count == 1:
        return {"count": 1, "single": True,
                "document_id": docs[0]["id"], "document_name": docs[0]["name"]}
    display = "\n".join(
        f"{i + 1}. **{d['name']}** — {d['folder']} (modifié {d['modified']})"
        for i, d in enumerate(docs))
    return {"count": count, "single": False, "display": display}


@app.post("/api/planner/task")
async def api_create_planner_task(
    request: PlannerTaskRequest,
    req: Request,
    user_upn: str = Depends(verify_azure_ad_token)
):
    try:
        # Le jeton entrant a pour audience la PASSERELLE ; Graph le rejetterait.
        # On échange via On-Behalf-Of pour un jeton Graph délégué (permission
        # déléguée Tasks.ReadWrite consentie), au nom de l'utilisateur.
        raw_auth = req.headers.get("Authorization", "") if req else ""
        if not obo_configured():
            raise HTTPException(
                status_code=503,
                detail="Planner indisponible : autorisation déléguée (OBO) non configurée.")
        # Wrapper avec backoff borné, réessais sur erreurs transitoires (AUD-05) :
        # l'épuisement transitoire est mappé en 503 (retriable), pas 502/500.
        try:
            token = await run_in_threadpool(acquire_obo_graph_token_retrying, raw_auth)
        except Exception as e:
            log_security("ERROR", "OBO exchange failed (planner)", {"error": str(e)})
            raise HTTPException(
                status_code=503,
                detail=_redacted_detail("Échec de l'autorisation déléguée (OBO).", e))
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
        # Corps Graph dynamique via le canal `data` redacté (message statique) :
        # un corps d'erreur arbitraire peut porter des identifiants hors des
        # motifs connus du message — `redact_mapping` neutralise ses valeurs.
        log_security("ERROR", "Graph API Error", {"body": e.response.text})
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
        # I/O fichier synchrone déportée en threadpool. L'identité de l'auteur est
        # passée EXPLICITEMENT (pas via os.environ : sinon course inter-requêtes).
        file_path = await run_in_threadpool(
            generate_fiche_rdv,
            request.client_name,
            request.summary,
            request.alert_points,
            job_id,
            user_upn,
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


@app.get("/ready")
async def readiness(oid: str = Depends(verify_azure_ad_token)):
    """Sonde de disponibilité Entra-gatée (OBS-03).

    Distincte de ``/health`` (liveness anonyme 200, cible du test de
    disponibilité Standard). ``/ready`` exige un jeton Entra valide (401 sinon),
    et NE retourne QUE des booléens coarse + une chaîne de statut coarse :
    aucune valeur de secret, aucune chaîne d'exception ne fuit dans le corps
    (même posture que ``_redacted_detail`` — T-03-04). 200 quand toutes les
    dépendances sont résolues, 503 (status "degraded") sinon.
    """
    checks: dict[str, bool] = {}
    # 1) Référence Key Vault résolue ? Le secret OBO ne doit PLUS être le
    #    littéral @Microsoft.KeyVault(...) au runtime.
    obo = os.environ.get("OBO_CLIENT_SECRET", "")
    checks["keyvault_ref"] = bool(obo) and not obo.startswith("@Microsoft.KeyVault")
    # 2) Accessibilité aval — booléen coarse uniquement, aucune PII, aucun secret.
    checks["function_host"] = bool(os.environ.get("AZURE_FUNCTION_URL"))
    ready = all(checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "degraded", "checks": checks},
    )


@app.get("/api/audit/{job_id}/status")
async def get_job_status(
    job_id: str,
    oid: str = Depends(verify_azure_ad_token)
):
    # Fast-path mémoire (cache, par-processus) ; le contrôle Durable autoritaire
    # (_assert_durable_owner, robuste au scale-out) tranche AVANT toute donnée.
    _assert_audit_owner(job_id, oid)

    try:
        auth_param = f"&code={AZURE_DURABLE_KEY}" if AZURE_DURABLE_KEY else ""
        task_hub = os.environ.get("TASK_HUB_NAME")
        if not task_hub:
            log_security("ERROR", "TASK_HUB_NAME non configuré — statut d'audit indisponible")
            raise HTTPException(status_code=500, detail="Configuration du moteur d'audit incomplète.")

        safe_job_id = urllib.parse.quote(job_id)

        resp = await http_client.get(
            f"{AZURE_FUNCTION_HOST}/runtime/webhooks/durabletask/instances/{safe_job_id}"
            f"?taskHub={task_hub}&connection=Storage&showInput=true{auth_param}",
            timeout=5.0
        )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Job introuvable.")
        resp.raise_for_status()
        data = resp.json()
        # Gate IDOR AUTORITAIRE (robuste cross-instance/scale-out) — en plus du
        # fast-path mémoire ci-dessus. Compare hash_id(oid) à l'owner_hash Durable.
        _assert_durable_owner(data, oid)
        return _shape_status_response(job_id, data)
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
