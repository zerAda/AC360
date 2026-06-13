"""audit_trail.py — Seam d'émission de la piste d'audit d'accès document (AUD-07).

Émet un événement d'accès document portant EXACTEMENT les quatre champs
verrouillés ``{user_id_hash, document_id, ts_utc, verdict}`` — aucun champ libre
en plus, aucune PII brute. Conformément à la Baseline Sécurité (cf.
docs/security/SECURITY_BASELINE.md), ``user_id_hash`` est le SHA-256 sans sel de
l'``oid`` Entra (réutilise ``feature_flags.hash_id``) : l'identifiant brut ne
traverse JAMAIS la frontière vers le puits de télémétrie.

Design (Open Q2 — RESEARCH §AUD-07) : ce module est le SEAM d'émission
uniquement. Aucun exportateur Azure Monitor n'est attaché ici et aucune nouvelle
dépendance pip (``azure-monitor-opentelemetry``) n'est ajoutée dans cette phase
d'audit — l'exportateur réel (``configure_azure_monitor``) atterrit en Phase 3
(OBS-01) sans toucher les sites d'appel. L'émission est donc :

- INERTE tant que le gate d'environnement AppInsights existant n'est pas posé
  (``APPINSIGHTS_INSTRUMENTATIONKEY`` ou ``APPLICATIONINSIGHTS_CONNECTION_STRING``,
  même garde qu'à api_server.py:84) ;
- routée à travers l'unique surface de redaction auditée
  (``safe_logger.redact_mapping``) avant émission — aucun regex de redaction
  n'est réintroduit ici.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from feature_flags import hash_id
from safe_logger import log_security, redact_mapping

__all__ = ["emit_document_access"]

# Nom canonique de l'événement custom (forme RESEARCH §AUD-07 — exploitée par
# l'exportateur Phase 3 via la dimension microsoft.custom_event.name).
_EVENT_NAME = "ac360_document_access"

# Gate d'environnement AppInsights — même garde que api_server.py:84. L'une ou
# l'autre variable suffit à activer l'émission.
_APPINSIGHTS_ENV_VARS = (
    "APPINSIGHTS_INSTRUMENTATIONKEY",
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
)


def _appinsights_gate_open() -> bool:
    """Vrai si le gate AppInsights est posé (au moins une variable non vide)."""
    return any(
        (os.environ.get(name) or "").strip() for name in _APPINSIGHTS_ENV_VARS
    )


def emit_document_access(
    *,
    oid: str,
    document_id: str,
    verdict: Optional[str] = None,
) -> None:
    """Émet l'événement d'accès document AUD-07 (seam, gaté, redaction-routé).

    Construit le dict de dimensions verrouillé à EXACTEMENT quatre clés
    ``{user_id_hash, document_id, ts_utc, verdict}``, calcule ``user_id_hash``
    via ``hash_id(oid)`` (SHA-256 sans sel — l'oid brut n'apparaît dans aucune
    dimension), horodate en ISO-8601 UTC, puis route toutes les valeurs à travers
    ``safe_logger.redact_mapping`` avant émission.

    L'émission est INERTE tant que le gate AppInsights n'est pas posé : aucun
    appel au puits n'est effectué (seam sans exportateur — Phase 3 OBS-01).

    Args:
        oid: Identifiant d'objet Entra de l'utilisateur (jamais émis en clair).
        document_id: Identifiant du document accédé.
        verdict: Verdict d'audit éventuel ; absent -> chaîne vide (jamais
            dimension manquante).
    """
    if not _appinsights_gate_open():
        return

    dimensions: Dict[str, Any] = {
        "user_id_hash": hash_id(oid),
        "document_id": document_id,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict or "",
    }

    # Redaction des VALEURS via l'unique surface auditée (aucun regex local).
    safe_dimensions = redact_mapping(dimensions)

    log_security("INFO", _EVENT_NAME, safe_dimensions)
