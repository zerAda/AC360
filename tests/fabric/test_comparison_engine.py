"""Tests du moteur de comparaison typé (MATCH/MISMATCH/UNCERTAIN/MISSING + verdict)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from fabric_audit_engine import (  # noqa: E402
    compare_name, compare_amount, compare_date, compare_contract, audit,
)


def test_compare_name_statuses():
    assert compare_name("GEREP SA", "GEREP SA")[0] == "MATCH"
    # Variante proche -> UNCERTAIN (score < 95 mais >= 85)
    assert compare_name("GEREP SA", "GEREP SAS")[0] == "UNCERTAIN"
    # Entités différentes -> MISMATCH
    assert compare_name("ALPHA", "BETA CORP")[0] == "MISMATCH"
    # Côté manquant -> MISSING
    assert compare_name("", "GEREP SA")[0] == "MISSING"


def test_compare_amount_statuses():
    assert compare_amount("1000", "1000")[0] == "MATCH"
    assert compare_amount("1 000,00 €", "1000")[0] == "MATCH"
    assert compare_amount("1000", "1500")[0] == "MISMATCH"
    assert compare_amount("1000", None)[0] == "MISSING"
    # Écart < 1 % -> UNCERTAIN
    assert compare_amount("1000", "1005")[0] == "UNCERTAIN"


def test_compare_date_and_contract():
    assert compare_date("01/06/2026", "2026-06-01")[0] == "MATCH"
    assert compare_date("01/06/2026", "02/06/2026")[0] == "MISMATCH"
    assert compare_contract("12-AB-3456", "12AB3456")[0] == "MATCH"
    assert compare_contract("12AB3456", "99ZZ0000")[0] == "MISMATCH"


def test_audit_verdict_conforme():
    result = audit({
        "document": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1 000 €",
                     "date_effet": "01/06/2026", "numero_contrat": "AB-123"},
        "reference": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000",
                      "date_effet": "2026-06-01", "numero_contrat": "AB123"},
    })
    assert result["verdict"] == "CONFORME"
    assert result["score_correspondance_nom"] >= 95
    assert all(f["statut"] == "MATCH" for f in result["fields"])


def test_audit_verdict_ecart():
    result = audit({
        "document": {"nom_client": "GEREP SA", "plafond_hospitalisation": "5 000 €"},
        "reference": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000"},
    })
    assert result["verdict"] == "ECART"
    plafond = next(f for f in result["fields"] if f["champ"] == "plafond_hospitalisation")
    assert plafond["statut"] == "MISMATCH"


def test_audit_ecart_beats_uncertain_cb06():
    """CB-06 : un MISMATCH confirmé prime sur un champ seulement UNCERTAIN —
    l'écart réel n'est PAS masqué en INCERTAIN."""
    result = audit({
        "document": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1005",
                     "numero_contrat": "12AB3456"},
        "reference": {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000",
                      "numero_contrat": "99ZZ0000"},
    })
    statuts = {f["champ"]: f["statut"] for f in result["fields"]}
    assert statuts["plafond_hospitalisation"] == "UNCERTAIN"  # écart < 1 %
    assert statuts["numero_contrat"] == "MISMATCH"            # écart confirmé
    assert result["verdict"] == "ECART"  # l'ECART prime sur l'INCERTAIN


def test_compare_amount_zero_reference_cb07():
    """CB-07 : référence = 0 ne casse pas la comparaison (pas de division par zéro,
    pas de confusion avec « absente »)."""
    assert compare_amount("0", "0")[0] == "MATCH"       # 0 ~ 0
    assert compare_amount("5", "0")[0] == "MISMATCH"    # 5 vs 0 : écart, pas UNCERTAIN


def test_audit_verdict_client_non_trouve():
    result = audit({
        "document": {"nom_client": "ENTREPRISE INCONNUE"},
        "reference": {"nom_client": "GEREP SA"},
    })
    assert result["verdict"] == "CLIENT_NON_TROUVE"


def test_audit_result_keys_present():
    result = audit({"document": {"nom_client": "X"}, "reference": {"nom_client": "X"}})
    for key in ("client_document", "score_correspondance_nom", "fields", "verdict",
                "motif_operation", "motif_source"):
        assert key in result
