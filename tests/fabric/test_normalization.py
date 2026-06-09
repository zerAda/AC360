"""Tests de normalisation (montants, dates, noms, contrats) + aliasing OCR."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from fabric_audit_engine import (  # noqa: E402
    normalize_amount, normalize_date, normalize_name, normalize_contract,
    alias_field, extract_canonical_fields,
)


def test_normalize_amount_fr_and_en():
    assert normalize_amount("1 000,50 €") == 1000.5
    assert normalize_amount("1 000,50 €") == 1000.5   # espace insécable
    assert normalize_amount("1,000.50") == 1000.5
    assert normalize_amount("2000") == 2000.0
    assert normalize_amount("3 000 €") == 3000.0
    assert normalize_amount("") is None
    assert normalize_amount(None) is None
    assert normalize_amount("N/A") is None


def test_normalize_date_iso():
    assert normalize_date("01/06/2026") == "2026-06-01"
    assert normalize_date("2026-06-01") == "2026-06-01"
    assert normalize_date("01.06.2026") == "2026-06-01"
    assert normalize_date("") is None
    assert normalize_date("pas une date") is None


def test_normalize_name_and_contract():
    assert normalize_name("Sociéte  GÉREP  SA") == "SOCIETE GEREP SA"
    assert normalize_name(None) == ""
    # Seuls les caractères non alphanumériques sont retirés (le "N" de "N°" reste).
    assert normalize_contract("N° 12-AB 3456") == "N12AB3456"
    assert normalize_contract("12-AB 3456") == "12AB3456"
    assert normalize_contract(None) == ""


def test_alias_field_maps_real_di_labels():
    assert alias_field("Raison sociale") == "nom_client"
    assert alias_field("Plafond hospi.") == "plafond_hospitalisation"
    assert alias_field("Date d'effet") == "date_effet"
    assert alias_field("N° de contrat") == "numero_contrat"
    assert alias_field("Libellé inconnu xyz") is None


def test_extract_canonical_fields_from_arbitrary_labels():
    ocr = {
        "fields": {
            "Raison sociale": {"value": "GEREP SA", "confidence": 0.98},
            "Plafond hospitalisation": {"value": "1 500 €", "confidence": 0.9},
        },
        "tables": [],
    }
    canon = extract_canonical_fields(ocr)
    assert canon["nom_client"] == "GEREP SA"
    assert canon["plafond_hospitalisation"] == "1 500 €"


def test_extract_plafond_from_table_geometry():
    ocr = {
        "fields": {},
        "tables": [{
            "cells": [
                {"row_index": 0, "column_index": 0, "content": "Garantie"},
                {"row_index": 0, "column_index": 1, "content": "Montant"},
                {"row_index": 1, "column_index": 0, "content": "Plafond hospitalisation"},
                {"row_index": 1, "column_index": 1, "content": "2 000 €"},
            ]
        }],
    }
    canon = extract_canonical_fields(ocr)
    assert canon["plafond_hospitalisation"] == "2 000 €"
