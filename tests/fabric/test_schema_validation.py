"""Valide que les sorties du moteur respectent les schémas JSON AC360."""
import json
import os
import sys

import pytest

jsonschema = pytest.importorskip("jsonschema")  # skip propre si non installé

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from fabric_audit_engine import audit  # noqa: E402

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "schemas")


def _load(name):
    with open(os.path.join(SCHEMAS_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def test_schemas_are_valid_jsonschema():
    for name in ("ocr_result.schema.json", "audit_input.schema.json", "audit_result.schema.json"):
        schema = _load(name)
        jsonschema.Draft202012Validator.check_schema(schema)


def test_audit_output_conforms_to_audit_result_schema():
    schema = _load("audit_result.schema.json")
    result = audit({
        "document": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1 000 €",
                     "date_effet": "01/06/2026", "numero_contrat": "AB-123",
                     "motif_operation": "modification de garantie"},
        "reference": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000",
                      "date_effet": "2026-06-01", "numero_contrat": "AB123"},
    })
    jsonschema.validate(instance=result, schema=schema)


def test_audit_input_example_conforms():
    schema = _load("audit_input.schema.json")
    example = {
        "document": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1 000 €"},
        "reference": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000"},
    }
    jsonschema.validate(instance=example, schema=schema)
