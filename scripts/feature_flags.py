from __future__ import annotations

import hashlib
import os
from typing import Optional, Tuple

FEATURE_ENV = {
    "ocr": "AC360_OCR_ENABLED",
    "rag": "AC360_RAG_ENABLED",
    "email_draft": "AC360_EMAIL_DRAFT_ENABLED",
    "audit": "AC360_AUDIT_ENABLED",
}

_GLOBAL_ENV = "AC360_GLOBAL_ENABLED"
_BLOCKED_USERS_ENV = "AC360_BLOCKED_USERS_HASHED"
_BLOCKED_TEAMS_ENV = "AC360_BLOCKED_TEAMS"
# GO-02 — allowlist (gate à EXACTEMENT l'équipe cible au lancement). FAIL-SAFE :
# vide/non défini => AUCUNE restriction (rétro-compatible) ; défini => deny-by-default
# (seuls les listés passent). Un BLOCK l'emporte toujours sur un allow (kill-switch).
_ALLOWED_USERS_ENV = "AC360_ALLOWED_USERS_HASHED"
_ALLOWED_TEAMS_ENV = "AC360_ALLOWED_TEAMS"

_TRUE = {"1", "true", "yes", "on", "enabled"}
_FALSE = {"0", "false", "no", "off", "disabled"}


def hash_id(raw: str) -> str:
    return hashlib.sha256((raw or "").strip().lower().encode("utf-8")).hexdigest()


def _flag(env_name: str, default: bool = True) -> bool:
    val = os.environ.get(env_name)
    if val is None or val.strip() == "":
        return default
    norm = val.strip().lower()
    if norm in _TRUE:
        return True
    if norm in _FALSE:
        return False
    return default  # unknown value → fail open


def _csv_set(env_name: str) -> set:
    raw = os.environ.get(env_name, "") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}


def is_global_enabled() -> bool:
    return _flag(_GLOBAL_ENV, default=True)


def is_feature_enabled(feature: str) -> bool:
    if not is_global_enabled():
        return False
    env_name = FEATURE_ENV.get(feature)
    if env_name is None:
        return True
    return _flag(env_name, default=True)


def is_user_blocked(user_id_hash: Optional[str]) -> bool:
    if not user_id_hash:
        return False
    return user_id_hash in _csv_set(_BLOCKED_USERS_ENV)


def is_team_blocked(team_id: Optional[str]) -> bool:
    if not team_id:
        return False
    return team_id in _csv_set(_BLOCKED_TEAMS_ENV)


def is_user_allowlisted(user_id_hash: Optional[str]) -> bool:
    """GO-02 fail-safe : allowlist vide => True (aucune restriction) ; définie =>
    seul un user_id_hash listé passe (un appelant sans hash ne peut pas prouver son
    appartenance => refusé)."""
    allow = _csv_set(_ALLOWED_USERS_ENV)
    if not allow:
        return True
    return bool(user_id_hash) and user_id_hash in allow


def is_team_allowlisted(team_id: Optional[str]) -> bool:
    """GO-02 fail-safe : allowlist d'équipes vide => True ; définie => seule une
    team_id listée passe."""
    allow = _csv_set(_ALLOWED_TEAMS_ENV)
    if not allow:
        return True
    return bool(team_id) and team_id in allow


def is_allowed(
    feature: str,
    user_id_hash: Optional[str] = None,
    team_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    if not is_global_enabled():
        return False, "global_disabled"
    if not is_feature_enabled(feature):
        return False, "feature_disabled"
    # Les BLOCKS (kill-switch) priment sur l'allowlist : on les évalue d'abord.
    if is_user_blocked(user_id_hash):
        return False, "user_blocked"
    if is_team_blocked(team_id):
        return False, "team_blocked"
    # GO-02 : gate allowlist (deny-by-default quand défini ; sinon aucune restriction).
    if not is_user_allowlisted(user_id_hash):
        return False, "user_not_allowlisted"
    if not is_team_allowlisted(team_id):
        return False, "team_not_allowlisted"
    return True, None


_USER_MESSAGES = {
    "global_disabled": "Le service AC360 est temporairement suspendu par un administrateur.",
    "feature_disabled": "Cette fonctionnalité est temporairement désactivée par un administrateur.",
    "user_blocked": "Votre accès à AC360 est actuellement suspendu. Contactez votre administrateur.",
    "team_blocked": "L'accès AC360 de votre équipe est actuellement suspendu. Contactez votre administrateur.",
    "user_not_allowlisted": "AC360 est en déploiement contrôlé ; votre compte ne fait pas encore partie du périmètre autorisé.",
    "team_not_allowlisted": "AC360 est en déploiement contrôlé ; votre équipe ne fait pas encore partie du périmètre autorisé.",
}


def blocked_message(reason: Optional[str]) -> str:
    return _USER_MESSAGES.get(reason or "", "Action non disponible pour le moment.")
