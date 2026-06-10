"""
usage_tracker.py — Traçage d'usage AC360 (P0-08).

Objectif : suivi fin de la consommation par commercial / équipe / client / cas
d'usage, SANS limiter par défaut et SANS exposer de donnée personnelle.

Garanties :
  - Identifiants (utilisateur, commercial, client) → hash SHA-256 (jamais en clair).
  - Tokens marqués ESTIMATED : Copilot Studio n'expose pas les tokens réels ;
    le nom des champs (`estimated_tokens_*`) l'indique explicitement.
  - Événements conformes à schemas/usage_event.schema.json.
  - Émission « best-effort » : le traçage ne doit JAMAIS casser le métier
    (une erreur d'émission est avalée et journalisée safe).

Le sink est configurable (fichier JSONL via AC360_USAGE_SINK) ; à défaut,
l'événement est journalisé via safe_logger. En production réelle, brancher ce
sink sur Application Insights / Log Analytics (cf. docs/observability).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from feature_flags import hash_id

VALID_EVENT_TYPES = {
    "conversation_started",
    "message_sent",
    "message_received",
    "rag_search_executed",
    "sharepoint_document_accessed",
    "ocr_started",
    "ocr_completed",
    "ocr_failed",
    "backend_action_called",
    "email_draft_generated",
    "audit_documentaire_started",
    "audit_documentaire_completed",
    "cost_estimated",
    "budget_warning_triggered",
    "user_blocked",
    "user_unblocked",
    "bot_emergency_stopped",
}

_VALID_STATUS = {"ok", "error", "blocked", "skipped"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _maybe_hash(raw: Optional[str]) -> Optional[str]:
    return hash_id(raw) if raw else None


def build_usage_event(
    event_type: str,
    *,
    status: str = "ok",
    environment: Optional[str] = None,
    bot_version: Optional[str] = None,
    user_id: Optional[str] = None,
    commercial_id: Optional[str] = None,
    team_id: Optional[str] = None,
    client_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    session_id: Optional[str] = None,
    action_name: Optional[str] = None,
    topic_name: Optional[str] = None,
    document_count: int = 0,
    page_count: int = 0,
    estimated_tokens_input: int = 0,
    estimated_tokens_output: int = 0,
    estimated_cost_eur: float = 0.0,
    cost_source: str = "ESTIME",
    error_code: Optional[str] = None,
    safe_error_message: Optional[str] = None,
    event_id: Optional[str] = None,
    timestamp_utc: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construit un événement d'usage conforme au schéma. Les identifiants bruts
    (user_id, commercial_id, client_id) sont hashés ici — ne JAMAIS passer de
    hash déjà calculé pour ces champs, passer la valeur brute.
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"event_type inconnu : {event_type}")
    if status not in _VALID_STATUS:
        raise ValueError(f"status invalide : {status}")

    return {
        "event_id": event_id or str(uuid.uuid4()),
        "timestamp_utc": timestamp_utc or _now_iso(),
        "environment": (environment or os.environ.get("AC360_ENVIRONMENT", "dev")),
        "bot_version": (bot_version or os.environ.get("AC360_BOT_VERSION", "0.0.0")),
        "event_type": event_type,
        "user_id_hash": _maybe_hash(user_id),
        "commercial_id_hash": _maybe_hash(commercial_id),
        "team_id": team_id,
        "client_id_hash": _maybe_hash(client_id),
        "conversation_id": conversation_id,
        "session_id": session_id,
        "action_name": action_name,
        "topic_name": topic_name,
        "document_count": int(document_count),
        "page_count": int(page_count),
        "estimated_tokens_input": int(estimated_tokens_input),
        "estimated_tokens_output": int(estimated_tokens_output),
        "estimated_cost_eur": round(float(estimated_cost_eur), 6),
        "cost_source": cost_source,
        "status": status,
        "error_code": error_code,
        "safe_error_message": safe_error_message,
    }


def _default_sink(line: str) -> None:
    """Sink par défaut : fichier JSONL si AC360_USAGE_SINK défini, sinon log safe."""
    sink_path = os.environ.get("AC360_USAGE_SINK")
    if sink_path:
        with open(sink_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return
    try:
        from safe_logger import log_security
        log_security("INFO", "usage_event", json.loads(line))
    except Exception:
        # Dernier recours : ne jamais lever depuis le traçage.
        pass


def emit_usage_event(
    event: Dict[str, Any],
    sink: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Émet un événement (best-effort). Toute exception d'émission est avalée :
    le traçage ne doit jamais interrompre le métier. Retourne l'événement.
    """
    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        (sink or _default_sink)(line)
    except Exception:
        pass
    return event


def track(event_type: str, *, sink: Optional[Callable[[str], None]] = None, **kwargs: Any) -> Dict[str, Any]:
    """Raccourci : construit puis émet un événement d'usage."""
    event = build_usage_event(event_type, **kwargs)
    return emit_usage_event(event, sink=sink)
