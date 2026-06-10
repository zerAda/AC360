"""Tests kill-switch / feature flags (P0-09)."""
import pytest
import feature_flags as ff

FEATURE_VARS = [
    "AC360_GLOBAL_ENABLED", "AC360_OCR_ENABLED", "AC360_RAG_ENABLED",
    "AC360_EMAIL_DRAFT_ENABLED", "AC360_AUDIT_ENABLED",
    "AC360_BLOCKED_USERS_HASHED", "AC360_BLOCKED_TEAMS",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for v in FEATURE_VARS:
        monkeypatch.delenv(v, raising=False)
    yield


def test_default_everything_enabled():
    # No block by default : tout activé sans configuration.
    assert ff.is_global_enabled() is True
    assert ff.is_feature_enabled("ocr") is True
    assert ff.is_feature_enabled("rag") is True
    allowed, reason = ff.is_allowed("ocr")
    assert allowed is True and reason is None


def test_global_kill_switch(monkeypatch):
    monkeypatch.setenv("AC360_GLOBAL_ENABLED", "false")
    assert ff.is_global_enabled() is False
    # Le global coupe TOUTES les fonctionnalités.
    assert ff.is_feature_enabled("ocr") is False
    allowed, reason = ff.is_allowed("rag")
    assert allowed is False and reason == "global_disabled"


def test_feature_specific_block(monkeypatch):
    monkeypatch.setenv("AC360_OCR_ENABLED", "false")
    assert ff.is_feature_enabled("ocr") is False
    # Les autres fonctionnalités restent actives.
    assert ff.is_feature_enabled("rag") is True
    allowed, reason = ff.is_allowed("ocr")
    assert allowed is False and reason == "feature_disabled"


def test_user_block_uses_hash(monkeypatch):
    h = ff.hash_id("commercial@gerep.fr")
    monkeypatch.setenv("AC360_BLOCKED_USERS_HASHED", f"{h},deadbeef")
    assert ff.is_user_blocked(h) is True
    assert ff.is_user_blocked(ff.hash_id("autre@gerep.fr")) is False
    allowed, reason = ff.is_allowed("ocr", user_id_hash=h)
    assert allowed is False and reason == "user_blocked"


def test_team_block(monkeypatch):
    monkeypatch.setenv("AC360_BLOCKED_TEAMS", "equipe-nord,equipe-sud")
    assert ff.is_team_blocked("equipe-nord") is True
    assert ff.is_team_blocked("equipe-est") is False


def test_unknown_flag_value_does_not_block(monkeypatch):
    # Une valeur inconnue ne doit JAMAIS bloquer par accident.
    monkeypatch.setenv("AC360_OCR_ENABLED", "peut-etre")
    assert ff.is_feature_enabled("ocr") is True


def test_hash_is_deterministic_and_not_plaintext():
    h = ff.hash_id("User@Gerep.FR")
    assert h == ff.hash_id("user@gerep.fr")  # normalisé
    assert "gerep" not in h and len(h) == 64


def test_blocked_message_is_clean():
    msg = ff.blocked_message("user_blocked")
    assert "suspendu" in msg.lower()
    assert "@" not in msg  # aucune donnée sensible
