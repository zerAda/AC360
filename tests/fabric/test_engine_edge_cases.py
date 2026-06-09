"""Cas limites du moteur d'audit (robustesse normalisation + comparaison + verdict)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from fabric_audit_engine import (  # noqa: E402
    normalize_amount, alias_field, extract_canonical_fields,
    compare_amount, audit,
)


def test_amount_european_thousands_and_decimals():
    assert normalize_amount("1.234,56") == 1234.56     # FR : point millier, virgule décimale
    assert normalize_amount("1,234.56") == 1234.56     # US : virgule millier, point décimal
    assert normalize_amount("€ 2 500") == 2500.0
    assert normalize_amount("1 234 567,89") == 1234567.89


def test_amount_zero_and_garbage():
    assert normalize_amount("0") == 0.0
    assert normalize_amount("abc") is None
    assert normalize_amount("--") is None
    assert compare_amount("0", "0")[0] == "MATCH"


def test_alias_priority_specific_over_generic():
    # "raison sociale" et "nom" mappent tous deux nom_client ; pas d'erreur.
    assert alias_field("Nom") == "nom_client"
    assert alias_field("Raison Sociale du Souscripteur") == "nom_client"
    # Un libellé numéro de contrat ne doit pas être capté par "nom".
    assert alias_field("Numéro de contrat") == "numero_contrat"


def test_extract_handles_value_below_label_in_table():
    ocr = {
        "fields": {},
        "tables": [{
            "cells": [
                {"row_index": 0, "column_index": 0, "content": "Plafond hospitalisation"},
                {"row_index": 1, "column_index": 0, "content": "3 000 €"},  # valeur en dessous
            ]
        }],
    }
    assert extract_canonical_fields(ocr)["plafond_hospitalisation"] == "3 000 €"


def test_audit_all_missing_is_client_non_trouve():
    result = audit({"document": {}, "reference": {}})
    assert result["verdict"] == "CLIENT_NON_TROUVE"
    assert result["fields"][0]["statut"] == "MISSING"


def test_audit_incertain_when_amount_close():
    result = audit({
        "document": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1005"},
        "reference": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000"},
    })
    # écart < 1 % -> UNCERTAIN sur le plafond -> verdict global INCERTAIN
    plafond = next(f for f in result["fields"] if f["champ"] == "plafond_hospitalisation")
    assert plafond["statut"] == "UNCERTAIN"
    assert result["verdict"] == "INCERTAIN"


def test_extract_never_raises_on_malformed_input():
    assert extract_canonical_fields({}) == {}
    assert extract_canonical_fields({"fields": {"X": "plain-string"}, "tables": []}) == {}
