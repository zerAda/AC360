"""audit_pipeline.py — Orchestration PURE de l'audit AC360.

Cœur métier du backend Durable Functions, écrit comme une fonction pure à
dépendances injectées : AUCUN appel réseau, AUCUNE lecture de données ici. Toutes
les I/O (téléchargement SharePoint, OCR Azure, requête Fabric, génération FIC)
sont fournies via l'objet ``AuditDeps``. Cela rend l'orchestration entièrement
testable en CI avec des fakes, sans runtime Durable ni accès cloud.

Le wrapper Durable Functions (``azure_functions/function_app.py``) ne fait que
brancher les vraies implémentations sur ces points d'injection.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Masque les affectations de type SECRET/KEY/TOKEN=... même non quotées, en
# complément de safe_logger.redact (défense en profondeur sur les messages
# d'exception qui pourraient embarquer une valeur sensible).
_SENSITIVE_ASSIGN = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PWD|CREDENTIAL)[A-Z0-9_]*)\s*[=:]\s*\S+"
)

# fabric_audit_engine vit dans scripts/. En test, conftest l'ajoute au path ;
# en déploiement, on l'ajoute défensivement.
_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if os.path.isdir(_SCRIPTS) and _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from fabric_audit_engine import audit as _default_compare  # noqa: E402
from fabric_audit_engine import extract_canonical_fields  # noqa: E402


def _safe_error(exc: Exception) -> str:
    """Message d'erreur neutralisé (jamais de secret/PII). Utilise safe_logger si
    disponible, sinon borne et masque a minima."""
    raw = f"{type(exc).__name__}: {exc}"
    raw = _SENSITIVE_ASSIGN.sub(r"\1=[MASQUÉ]", raw)
    try:
        from safe_logger import redact
        return redact(raw)
    except Exception:
        return raw[:300]


@dataclass
class AuditDeps:
    """Points d'injection des I/O. Chaque champ est un callable.

    - download(document_id) -> chemin local du document
    - ocr(path) -> dict OCR brut (schemas/ocr_result.schema.json)
    - fetch_reference(client_name) -> dict de référence Fabric, ou None si absent
    - make_fic(client_name, audit_result) -> chemin FIC, ou None (optionnel)
    - compare(audit_input) -> audit_result (défaut : fabric_audit_engine.audit)
    """
    download: Callable[[str], str]
    ocr: Callable[[str], Dict[str, Any]]
    fetch_reference: Callable[[Optional[str]], Optional[Dict[str, Any]]]
    make_fic: Optional[Callable[[Optional[str], Dict[str, Any]], Optional[str]]] = None
    compare: Callable[[Dict[str, Any]], Dict[str, Any]] = _default_compare


# Verdicts déclenchant la génération d'un brouillon de FIC pour revue humaine.
_FIC_VERDICTS = {"ECART", "INCERTAIN"}


def run_audit(
    document_id: str,
    client_context: Optional[str],
    deps: AuditDeps,
    *,
    logger: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """Orchestration pure document -> OCR -> Fabric -> comparaison -> (FIC).

    Retourne un dict :
      {
        "status": "Completed" | "Failed",
        "document_id": str,
        "stages": [ {name, ok, detail?} ... ],
        "result": <audit_result> | None,
        "fic_path": str | None,
        "error": str | None,   # neutralisé
      }
    Ne lève jamais : toute exception est capturée et neutralisée.
    """
    stages: List[Dict[str, Any]] = []

    def _log(level: str, msg: str) -> None:
        if logger:
            logger(level, msg)

    def _stage(name: str, ok: bool, detail: str = "") -> None:
        stages.append({"name": name, "ok": ok, "detail": detail})

    out: Dict[str, Any] = {
        "status": "Failed",
        "document_id": document_id,
        "stages": stages,
        "result": None,
        "fic_path": None,
        "error": None,
    }

    if not document_id:
        out["error"] = "document_id manquant"
        _stage("validate", False, "document_id manquant")
        return out
    _stage("validate", True)

    try:
        path = deps.download(document_id)
        _stage("download", True)

        ocr_result = deps.ocr(path)
        _stage("ocr", True)

        canonical = extract_canonical_fields(ocr_result)
        client_name = canonical.get("nom_client") or client_context
        _stage("extract", True, f"client={'<set>' if client_name else '<none>'}")

        reference = deps.fetch_reference(client_name)
        if not reference:
            result = {
                "client_document": client_name,
                "meilleur_match_fabric": None,
                "score_correspondance_nom": 0.0,
                "motif_operation": canonical.get("motif_operation") or "NON_DETERMINE",
                "motif_source": "ocr" if canonical.get("motif_operation") else "absent",
                "verdict": "CLIENT_NON_TROUVE",
                "fields": [],
            }
            _stage("fetch_reference", True, "client absent de Fabric")
            out.update(status="Completed", result=result)
            _log("WARNING", "Audit terminé : client non trouvé dans Fabric")
            return out
        _stage("fetch_reference", True)

        audit_input = {"document": canonical, "reference": reference}
        result = deps.compare(audit_input)
        _stage("compare", True, f"verdict={result.get('verdict')}")

        fic_path = None
        if deps.make_fic and result.get("verdict") in _FIC_VERDICTS:
            fic_path = deps.make_fic(client_name, result)
            _stage("make_fic", True, "FIC générée pour revue humaine")

        out.update(status="Completed", result=result, fic_path=fic_path)
        _log("INFO", f"Audit terminé : {result.get('verdict')}")
        return out

    except Exception as exc:  # noqa: BLE001 - on neutralise et on remonte proprement
        safe = _safe_error(exc)
        _stage("error", False, safe)
        out["error"] = safe
        _log("ERROR", f"Échec pipeline audit : {safe}")
        return out
