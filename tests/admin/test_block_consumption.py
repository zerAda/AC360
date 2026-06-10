"""Test bout-en-bout du blocage de consommation (P0-09) :
admin autorisé → flag appliqué → feature_flags refuse l'usage → message propre.
"""
import pytest
import admin_controls as ac
import feature_flags as ff

VARS = ["AC360_GLOBAL_ENABLED", "AC360_OCR_ENABLED", "AC360_BLOCKED_USERS_HASHED", "AC360_ADMIN_ROLE"]


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for v in VARS:
        monkeypatch.delenv(v, raising=False)
    yield


def test_block_ocr_flow(monkeypatch):
    # 1. État initial : OCR autorisé.
    assert ff.is_allowed("ocr")[0] is True

    # 2. Un admin décide de couper l'OCR (coûteux).
    action = ac.apply_control(
        admin_id="admin@gerep.fr", roles=["AC360.Admin"],
        action="block_feature", scope="ocr", reason="pic de coût OCR",
    )
    assert action["result"] == "applied"

    # 3. L'application du blocage = app setting (géré par admin uniquement).
    monkeypatch.setenv("AC360_OCR_ENABLED", "false")

    # 4. L'usage OCR est désormais refusé proprement.
    allowed, reason = ff.is_allowed("ocr")
    assert allowed is False and reason == "feature_disabled"
    assert "désactivée" in ff.blocked_message(reason).lower()


def test_emergency_stop_blocks_all(monkeypatch):
    action = ac.apply_control(
        admin_id="admin@gerep.fr", roles=["AC360.Admin"],
        action="emergency_stop", scope="global", reason="incident",
    )
    assert action["result"] == "applied"
    monkeypatch.setenv("AC360_GLOBAL_ENABLED", "false")
    for feature in ("ocr", "rag", "email_draft", "audit"):
        assert ff.is_allowed(feature)[0] is False


def test_block_specific_user_only(monkeypatch):
    victim = ff.hash_id("gros.consommateur@gerep.fr")
    monkeypatch.setenv("AC360_BLOCKED_USERS_HASHED", victim)
    assert ff.is_allowed("ocr", user_id_hash=victim)[0] is False
    # Un autre commercial n'est pas impacté.
    other = ff.hash_id("normal@gerep.fr")
    assert ff.is_allowed("ocr", user_id_hash=other)[0] is True
