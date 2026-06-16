"""GO-02 — allowlist gating (fail-safe). Restrict access to EXACTLY the target team.

Fail-safe contract (load-bearing — getting it wrong either exposes the service to
everyone or bricks it):
- allowlist UNSET/empty  -> NO restriction (backward-compatible with the blocklist model)
- allowlist SET          -> deny-by-default (only listed teams/users allowed)
- a BLOCK always overrides an allow (defense-in-depth kill-switch still wins)
"""
import importlib
import os

import feature_flags


def _reload(env: dict):
    """Reload feature_flags with a clean env subset (module reads os.environ live,
    but reload guards against any module-level caching)."""
    for k in ("AC360_ALLOWED_USERS_HASHED", "AC360_ALLOWED_TEAMS",
              "AC360_BLOCKED_USERS_HASHED", "AC360_BLOCKED_TEAMS",
              "AC360_GLOBAL_ENABLED", "AC360_AUDIT_ENABLED"):
        os.environ.pop(k, None)
    os.environ.update(env)
    return importlib.reload(feature_flags)


def test_allowlist_unset_allows_anyone(monkeypatch):
    ff = _reload({})
    ok, reason = ff.is_allowed("audit", user_id_hash="abc", team_id="team-x")
    assert ok is True and reason is None


def test_user_allowlist_set_denies_unlisted(monkeypatch):
    ff = _reload({"AC360_ALLOWED_USERS_HASHED": "hash-allowed"})
    ok, reason = ff.is_allowed("audit", user_id_hash="hash-other", team_id=None)
    assert ok is False and reason == "user_not_allowlisted"


def test_user_allowlist_set_allows_listed(monkeypatch):
    ff = _reload({"AC360_ALLOWED_USERS_HASHED": "hash-allowed,hash-2"})
    ok, reason = ff.is_allowed("audit", user_id_hash="hash-allowed", team_id=None)
    assert ok is True and reason is None


def test_team_allowlist_set_denies_unlisted_team(monkeypatch):
    ff = _reload({"AC360_ALLOWED_TEAMS": "target-team"})
    ok, reason = ff.is_allowed("audit", user_id_hash="anyone", team_id="other-team")
    assert ok is False and reason == "team_not_allowlisted"


def test_team_allowlist_set_allows_listed_team(monkeypatch):
    ff = _reload({"AC360_ALLOWED_TEAMS": "target-team"})
    ok, reason = ff.is_allowed("audit", user_id_hash="anyone", team_id="target-team")
    assert ok is True and reason is None


def test_block_overrides_allowlist(monkeypatch):
    ff = _reload({
        "AC360_ALLOWED_USERS_HASHED": "hash-allowed",
        "AC360_BLOCKED_USERS_HASHED": "hash-allowed",  # same user allowed AND blocked
    })
    ok, reason = ff.is_allowed("audit", user_id_hash="hash-allowed", team_id=None)
    assert ok is False and reason == "user_blocked"  # block wins


def test_set_user_allowlist_with_none_user_denied(monkeypatch):
    ff = _reload({"AC360_ALLOWED_USERS_HASHED": "hash-allowed"})
    ok, reason = ff.is_allowed("audit", user_id_hash=None, team_id=None)
    assert ok is False and reason == "user_not_allowlisted"  # can't prove membership


def test_blocked_message_covers_new_reasons(monkeypatch):
    ff = _reload({})
    assert ff.blocked_message("user_not_allowlisted") != "Action non disponible pour le moment."
    assert ff.blocked_message("team_not_allowlisted") != "Action non disponible pour le moment."
