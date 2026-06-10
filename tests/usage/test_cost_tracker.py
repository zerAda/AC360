"""Tests cost tracker (P0-07) : aucun prix inventé, paramétrage par env."""
import pytest
import cost_tracker as ct


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for v in ("AC360_RATE_CARD", "AC360_BUDGET_EUR", "AC360_BUDGET_WARN_PCT"):
        monkeypatch.delenv(v, raising=False)
    yield


def test_no_invented_prices_by_default():
    # Sans grille fournie : montant 0.0 et source A_VALIDER (jamais inventé).
    ev = ct.estimate_cost("ocr_document_intelligence", 10, unit="page")
    assert ev["unit_cost_eur"] == 0.0
    assert ev["estimated_cost_eur"] == 0.0
    assert ev["cost_source"] == "A_VALIDER"


def test_rate_card_override_makes_it_parametrable(monkeypatch):
    monkeypatch.setenv("AC360_RATE_CARD", '{"ocr_document_intelligence": 0.01}')
    ev = ct.estimate_cost("ocr_document_intelligence", 10, unit="page")
    assert ev["unit_cost_eur"] == 0.01
    assert ev["estimated_cost_eur"] == pytest.approx(0.1)
    assert ev["cost_source"] == "PARAMETRABLE"


def test_unknown_cost_center_raises():
    with pytest.raises(ValueError):
        ct.estimate_cost("bitcoin_mining", 1)


def test_negative_quantity_raises():
    with pytest.raises(ValueError):
        ct.estimate_cost("backend_api", -5)


def test_malformed_rate_card_is_ignored(monkeypatch):
    monkeypatch.setenv("AC360_RATE_CARD", "{not valid json")
    ev = ct.estimate_cost("storage", 100, unit="gb")
    assert ev["cost_source"] == "A_VALIDER"  # pas de crash, pas de prix inventé


def test_commercial_and_client_hashed():
    ev = ct.estimate_cost(
        "copilot_studio_message", 1, unit="message",
        commercial_id="c@gerep.fr", client_id="ACME",
    )
    assert ev["commercial_id_hash"] and "gerep" not in ev["commercial_id_hash"]
    assert ev["client_id_hash"] and "acme" not in ev["client_id_hash"].lower()
