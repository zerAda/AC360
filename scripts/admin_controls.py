from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from feature_flags import hash_id

ADMIN_ROLE_ENV = "AC360_ADMIN_ROLE"
_DEFAULT_ADMIN_ROLE = "AC360.Admin"

_ACTION_SCOPES = {
    "block_global": "global",
    "unblock_global": "global",
    "block_feature": {"ocr", "rag", "email_draft", "audit"},
    "unblock_feature": {"ocr", "rag", "email_draft", "audit"},
    "block_user": "user",
    "unblock_user": "user",
    "block_team": "team",
    "unblock_team": "team",
    "emergency_stop": "global",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def admin_role() -> str:
    return os.environ.get(ADMIN_ROLE_ENV) or _DEFAULT_ADMIN_ROLE


def is_admin(roles: Optional[Iterable[str]]) -> bool:
    if not roles:
        return False
    return admin_role() in set(roles)


def _scope_valid(action: str, scope: str) -> bool:
    expected = _ACTION_SCOPES.get(action)
    if expected is None:
        return False
    if isinstance(expected, set):
        return scope in expected
    return scope == expected


def apply_control(
    *,
    admin_id: str,
    roles: Optional[Iterable[str]],
    action: str,
    scope: str,
    target_id: Optional[str] = None,
    reason: Optional[str] = None,
    action_id: Optional[str] = None,
    timestamp_utc: Optional[str] = None,
) -> Dict[str, Any]:
    if action not in _ACTION_SCOPES or not _scope_valid(action, scope):
        result = "noop"
    elif not is_admin(roles):
        result = "denied_not_admin"
    else:
        result = "applied"

    return {
        "action_id": action_id or str(uuid.uuid4()),
        "timestamp_utc": timestamp_utc or _now_iso(),
        "admin_id_hash": hash_id(admin_id),
        "action": action if action in _ACTION_SCOPES else "block_global",
        "scope": scope if scope in {"global", "ocr", "rag", "email_draft", "audit", "user", "team"} else "global",
        "target_hash": hash_id(target_id) if target_id else None,
        "reason": reason,
        "result": result,
    }
