"""Tests conformité des événements d'usage au schéma (P0-08)."""
import json
import os
import pytest
import usage_tracker as ut

jsonschema = pytest.importorskip("jsonschema")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _usage_schema():
    with open(os.path.join(ROOT, "schemas", "usage_event.schema.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("event_type", sorted(ut.VALID_EVENT_TYPES))
def test_every_event_type_conforms(event_type):
    schema = _usage_schema()
    ev = ut.build_usage_event(
        event_type,
        environment="staging",
        bot_version="1.2.3",
        user_id="u@gerep.fr",
        commercial_id="u@gerep.fr",
        client_id="ClientX",
        page_count=2,
        estimated_tokens_input=100,
        estimated_tokens_output=50,
        estimated_cost_eur=0.0,
    )
    jsonschema.validate(ev, schema)


def test_hash_fields_match_schema_pattern():
    schema = _usage_schema()
    ev = ut.build_usage_event("ocr_completed", user_id="x@gerep.fr")
    jsonschema.validate(ev, schema)
    assert len(ev["user_id_hash"]) == 64


def test_null_identifiers_are_valid():
    schema = _usage_schema()
    ev = ut.build_usage_event("conversation_started")  # pas d'identifiants
    jsonschema.validate(ev, schema)
    assert ev["user_id_hash"] is None
