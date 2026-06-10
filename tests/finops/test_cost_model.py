"""Tests modèle de coût (P0-07) : conformité schéma + couverture des postes."""
import json
import os
import pytest
import cost_tracker as ct

jsonschema = pytest.importorskip("jsonschema")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _schema(name):
    with open(os.path.join(ROOT, "schemas", name), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("AC360_RATE_CARD", raising=False)
    yield


def test_cost_event_conforms_to_schema():
    schema = _schema("cost_event.schema.json")
    ev = ct.estimate_cost("ocr_document_intelligence", 5, unit="page", commercial_id="c@gerep.fr")
    jsonschema.validate(ev, schema)  # ne doit pas lever


def test_all_cost_centers_have_default_rate():
    card = ct.load_rate_card()
    for cc in ct.COST_CENTERS:
        assert cc in card
        assert card[cc] == 0.0  # défaut : aucun prix inventé


def test_rate_card_only_accepts_known_centers(monkeypatch):
    monkeypatch.setenv("AC360_RATE_CARD", '{"inexistant": 5.0, "storage": 0.02}')
    card = ct.load_rate_card()
    assert "inexistant" not in card
    assert card["storage"] == 0.02


def test_cost_source_values_are_in_schema_enum():
    schema = _schema("cost_event.schema.json")
    allowed = set(schema["properties"]["cost_source"]["enum"])
    ev_unset = ct.estimate_cost("storage", 1)
    assert ev_unset["cost_source"] in allowed
