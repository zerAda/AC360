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
from dataclasses import replace

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
    """Télécharge le document depuis SharePoint via Microsoft Graph.

    Prérequis (variables d'app) :
      * SHAREPOINT_DRIVE_ID : drive SharePoint contenant les dossiers clients ;
      * un accès Entra ID (Managed Identity recommandée) avec scope Graph
        `Files.Read.All` ou `Sites.Selected`.
    `document_id` est l'item id Graph. Le binaire est écrit dans JOBS_BASE_DIR.
    """
    from sharepoint import download_document
    from azure.identity import DefaultAzureCredential

    drive_id = os.environ.get("SHAREPOINT_DRIVE_ID")
    if not drive_id:
        raise RuntimeError("SHAREPOINT_DRIVE_ID manquant (configuration requise).")

    credential = DefaultAzureCredential()
    token = credential.get_token("https://graph.microsoft.com/.default").token

    dest_dir = os.path.join(os.environ.get("JOBS_BASE_DIR", "jobs"), str(document_id))
    return download_document(
        item_id=document_id,
        drive_id=drive_id,
        dest_dir=dest_dir,
        access_token=token,
    )


def _download_as_user(document_id: str, graph_token: str) -> str:
    """Télécharge le document AVEC le token Graph délégué de l'utilisateur (OBO).

    Graph applique les permissions SharePoint de l'utilisateur : pas d'accès ->
    HTTPStatusError 403/404 (propagé tel quel par `http_start`).
    """
    from sharepoint import download_document

    drive_id = os.environ.get("SHAREPOINT_DRIVE_ID")
    if not drive_id:
        raise RuntimeError("SHAREPOINT_DRIVE_ID manquant (configuration requise).")
    dest_dir = os.path.join(os.environ.get("JOBS_BASE_DIR", "jobs"), str(document_id))
    return download_document(
        item_id=document_id,
        drive_id=drive_id,
        dest_dir=dest_dir,
        access_token=graph_token,
    )


def _graph_error_status(exc: Exception) -> int:
    """Mappe une erreur de téléchargement Graph vers un statut HTTP à renvoyer :
    403/404 (refus/introuvable côté utilisateur) propagés, sinon 502."""
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None)
    return code if code in (403, 404) else 502


def _ocr(path: str) -> dict:
    from process_document_ocr import extract_document_azure
    return extract_document_azure(path)


def _fetch_reference(identity):
    """Référence client depuis Microsoft Fabric (OneLake Delta, pur Python — pas
    d'ODBC). Rapprochement par SIRET exact (prioritaire) puis nom. ``identity`` =
    {"nom_client", "siret"}. Retourne le dict de référence, ou None si absent."""
    from fabric_onelake import fetch_client_reference
    identity = identity or {}
    return fetch_client_reference(
        client_name=identity.get("nom_client"),
        siret=identity.get("siret"),
    )


def _build_garanties(audit_result: dict) -> dict:
    """Adapte le résultat d'audit typé -> dict {garantie: valeur} pour la FIC."""
    garanties = {}
    for field in audit_result.get("fields", []):
        champ = field.get("champ")
        valeur = field.get("valeur_reference") or field.get("valeur_document")
        if champ and valeur is not None:
            garanties[champ] = valeur
    return garanties


def _date_effet(audit_result: dict):
    for field in audit_result.get("fields", []):
        if field.get("champ") == "date_effet":
            return field.get("valeur_reference") or field.get("valeur_document")
    return None


def _make_fic(client_name, audit_result):
    # Génère un brouillon de FIC pour revue humaine (verdict ECART/INCERTAIN).
    from generate_fic_draft import generate_fic_document
    out_dir = os.environ.get("JOBS_BASE_DIR", "jobs")
    os.makedirs(out_dir, exist_ok=True)
    safe = "".join(c for c in (client_name or "client") if c.isalnum() or c == " ").strip().replace(" ", "_")
    out_path = os.path.join(out_dir, f"FIC_Brouillon_{safe or 'client'}.docx")
    generate_fic_document(
        client_name,
        _date_effet(audit_result),
        _build_garanties(audit_result),
        out_path,
    )
    return out_path


_DEPS = AuditDeps(
    download=_download,
    ocr=_ocr,
    fetch_reference=_fetch_reference,
    make_fic=_make_fic,
)


# ---------------------------------------------------------------------------
# Logique testable (sans le SDK Durable). Les triggers ci-dessous délèguent ici.
# ---------------------------------------------------------------------------
def _activity_logger():
    return lambda lvl, msg: logging.log(getattr(logging, lvl, logging.INFO), msg)


def _run_activity(payload: dict) -> dict:
    """Corps de l'activité Durable : exécute l'orchestration pure avec _DEPS.
    Testable sans le runtime Azure. Si `document_path` est fourni (document déjà
    téléchargé AU NOM de l'utilisateur via OBO côté http_start), on court-circuite
    le téléchargement applicatif — aucun token n'est persisté dans l'état Durable."""
    payload = payload or {}
    deps = _DEPS
    pre_path = payload.get("document_path")
    if pre_path:
        deps = replace(_DEPS, download=lambda _id, _p=pre_path: _p)
    return run_audit(
        payload.get("document_id"),
        payload.get("client_context"),
        deps,
        logger=_activity_logger(),
    )


def _audit_orchestration(context):
    """Générateur d'orchestration : appelle l'activité d'audit. Testable avec un
    contexte factice exposant get_input() et call_activity()."""
    payload = context.get_input() or {}
    result = yield context.call_activity(
        "activity_run_audit",
        {"document_id": payload.get("document_id"),
         "client_context": payload.get("client_context"),
         "document_path": payload.get("document_path")},
    )
    return result


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

        # OBO : si la passerelle a fourni un token Graph délégué, on télécharge le
        # document AU NOM de l'utilisateur (Graph applique sa RBAC SharePoint).
        # Pas d'accès -> 403/404 propagés, l'orchestration ne démarre pas. Seul un
        # chemin local (pas de token) entre ensuite dans l'état Durable.
        body = dict(body or {})
        graph_token = req.headers.get("X-MS-Graph-Token")
        if graph_token:
            try:
                body["document_path"] = _download_as_user(document_id, graph_token)
            except Exception as exc:  # noqa: BLE001
                status = _graph_error_status(exc)
                logging.warning("Téléchargement SharePoint (OBO) refusé/échoué (%s)", status)
                return func.HttpResponse(
                    "Accès refusé à ce document ou document introuvable.",
                    status_code=status)

        instance_id = await client.start_new("audit_orchestrator", None, body)
        logging.info("Orchestration audit démarrée: %s", instance_id)
        # Renvoie {id, statusQueryGetUri, ...} — contrat attendu par api_server.
        return client.create_check_status_response(req, instance_id)

    @app.orchestration_trigger(context_name="context")
    def audit_orchestrator(context):
        result = yield from _audit_orchestration(context)
        return result

    @app.activity_trigger(input_name="payload")
    def activity_run_audit(payload: dict) -> dict:
        return _run_activity(payload)
