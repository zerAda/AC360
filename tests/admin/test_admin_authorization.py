"""Tests autorisation admin & blocage consommation (P0-09).

Garantie centrale : un commercial NE PEUT PAS se débloquer lui-même.
"""
import pytest
import admin_controls as ac


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("AC360_ADMIN_ROLE", raising=False)
    yield


def test_non_admin_cannot_apply_control():
    action = ac.apply_control(
        admin_id="commercial@gerep.fr",
        roles=["AC360.User"],
        action="unblock_user",
        scope="user",
        target_id="commercial@gerep.fr",
    )
    assert action["result"] == "denied_not_admin"


def test_commercial_cannot_self_unblock():
    # Même en se ciblant soi-même, sans rôle admin → refusé.
    action = ac.apply_control(
        admin_id="commercial@gerep.fr",
        roles=[],
        action="unblock_global",
        scope="global",
    )
    assert action["result"] == "denied_not_admin"


def test_admin_can_apply():
    action = ac.apply_control(
        admin_id="admin@gerep.fr",
        roles=["AC360.Admin"],
        action="block_global",
        scope="global",
        reason="budget dépassé",
    )
    assert action["result"] == "applied"
    assert action["action"] == "block_global"


def test_target_is_hashed_not_plaintext():
    action = ac.apply_control(
        admin_id="admin@gerep.fr",
        roles=["AC360.Admin"],
        action="block_user",
        scope="user",
        target_id="cible@gerep.fr",
    )
    assert action["target_hash"] == ac.hash_id("cible@gerep.fr")
    assert "gerep" not in (action["target_hash"] or "")
    assert "gerep" not in action["admin_id_hash"]


def test_invalid_action_is_noop():
    action = ac.apply_control(
        admin_id="admin@gerep.fr",
        roles=["AC360.Admin"],
        action="delete_everything",
        scope="global",
    )
    assert action["result"] == "noop"


def test_scope_mismatch_is_noop():
    action = ac.apply_control(
        admin_id="admin@gerep.fr",
        roles=["AC360.Admin"],
        action="block_feature",
        scope="global",  # block_feature attend ocr/rag/email_draft/audit
    )
    assert action["result"] == "noop"


def test_custom_admin_role(monkeypatch):
    monkeypatch.setenv("AC360_ADMIN_ROLE", "GEREP.SuperAdmin")
    assert ac.is_admin(["GEREP.SuperAdmin"]) is True
    assert ac.is_admin(["AC360.Admin"]) is False
