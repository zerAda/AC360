"""function_app.py — Backend AC360 (Azure Durable Functions, modèle Python v2).

Passerelle d'orchestration appelée par `scripts/api_server.py` (`/api/audit`).
Démarre une orchestration durable document -> OCR -> Fabric -> comparaison -> FIC.

⚠️ Ce module n'est chargé QUE par le runtime Azure Functions. Les imports `azure.*`
sont protégés pour ne jamais casser la collection pytest ni un import accidentel
hors runtime. La logique métier testée vit dans `shared/audit_pipeline.py`.

À VALIDER AU DÉPLOIEMENT : nécessite la ressource OCR Document Intelligence
provisionnée, l'accès Fabric (Entra ID) et un compte de stockage pour Durable.
Voir README.md.
"""
from __future__ import annotations

import logging
import os
import sys

_HERE = os.path.dirname(__file__)
for _p in (os.path.join(_HERE, "shared"), os.path.abspath(os.path.join(_HERE, "..", "scripts"))):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import azure.functions as func
    import azure.durable_functions as df
    _DURABLE_AVAILABLE = True
except Exception:  # pragma: no cover - dépend du runtime
    func = None
    df = None
    _DURABLE_AVAILABLE = False

from audit_pipeline import AuditDeps, run_audit  # noqa: E402


# ---------------------------------------------------------------------------
# Implémentations réelles des I/O (exécutées côté activités Durable uniquement)
# ---------------------------------------------------------------------------
def _download(document_id: str) -> str:
    """Télécharge le document depuis SharePoint via Graph API.

    À IMPLÉMENTER au branchement réel (Graph /drives/{id}/items/{document_id}).
    Laissé explicite pour ne rien simuler.
    """
    raise NotImplementedError(
        "Téléchargement SharePoint non branché — fournir l'implémentation Graph API."
    )


def _ocr(path: str) -> dict:
    from process_document_ocr import extract_document_azure
    return extract_document_azure(path)


def _fetch_reference(client_name):
    from audit_fabric_comparison import fetch_artus_data
    df_ref = fetch_artus_data(client_name)
    if df_ref is None or getattr(df_ref, "empty", True):
        return None
    row = df_ref.iloc[0].to_dict()
    return {
        "client_id": row.get("client_id"),
        "nom_client": row.get("nom_client"),
        "plafond_hospitalisation": row.get("plafond_hospitalisation"),
        "date_effet": str(row.get("date_effet")) if row.get("date_effet") is not None else None,
    }


def _make_fic(client_name, audit_result):
    # Génère un brouillon de FIC pour revue humaine (verdict ECART/INCERTAIN).
    from generate_fic_draft import generate_fic_document
    out_dir = os.environ.get("JOBS_BASE_DIR", "jobs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"FIC_{(client_name or 'client').replace(' ', '_')}.docx")
    generate_fic_document(client_name, None, audit_result, out_path)
    return out_path


_DEPS = AuditDeps(
    download=_download,
    ocr=_ocr,
    fetch_reference=_fetch_reference,
    make_fic=_make_fic,
)


# ---------------------------------------------------------------------------
# Enregistrement Durable Functions (uniquement si le SDK est disponible)
# ---------------------------------------------------------------------------
if _DURABLE_AVAILABLE:
    app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)

    @app.route(route="audit")
    @app.durable_client_input(client_name="client")
    async def http_start(req: "func.HttpRequest", client) -> "func.HttpResponse":
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse("Corps JSON invalide.", status_code=400)
        document_id = (body or {}).get("document_id")
        if not document_id:
            return func.HttpResponse("document_id manquant.", status_code=400)
        instance_id = await client.start_new("audit_orchestrator", None, body)
        logging.info("Orchestration audit démarrée: %s", instance_id)
        # Renvoie {id, statusQueryGetUri, ...} — contrat attendu par api_server.
        return client.create_check_status_response(req, instance_id)

    @app.orchestration_trigger(context_name="context")
    def audit_orchestrator(context):
        payload = context.get_input() or {}
        document_id = payload.get("document_id")
        client_context = payload.get("client_context")
        result = yield context.call_activity(
            "activity_run_audit", {"document_id": document_id, "client_context": client_context}
        )
        return result

    @app.activity_trigger(input_name="payload")
    def activity_run_audit(payload: dict) -> dict:
        out = run_audit(
            payload.get("document_id"),
            payload.get("client_context"),
            _DEPS,
            logger=lambda lvl, msg: logging.log(getattr(logging, lvl, logging.INFO), msg),
        )
        return out
