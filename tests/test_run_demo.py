"""Tests de la démo hors-ligne AC360 (fixtures synthétiques, aucun cloud)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import run_demo  # noqa: E402


def test_demo_detects_ecart_offline():
    """La démo par défaut doit détecter un écart de plafond (1 500 € vs 2000)."""
    lines = []
    result = run_demo.run(printer=lines.append)
    assert result["client_document"] == "GEREP SA"
    assert result["meilleur_match_fabric"] == "GEREP SA"
    assert result["verdict"] == "ECART"
    plafond = next(f for f in result["fields"] if f["champ"] == "plafond_hospitalisation")
    assert plafond["statut"] == "MISMATCH"
    # Le rapport lisible a bien été émis.
    assert any("VERDICT GLOBAL" in line for line in lines)


def test_select_reference_matches_by_name():
    refs = [{"nom_client": "GEREP SA"}, {"nom_client": "BETA CORP"}]
    assert run_demo.select_reference("GEREP SA", refs)["nom_client"] == "GEREP SA"
    assert run_demo.select_reference("ENTREPRISE INCONNUE", refs) is None
    assert run_demo.select_reference(None, refs) is None


def test_audit_from_sources_client_non_trouve():
    ocr = {"fields": {"Raison sociale": {"value": "SOCIETE FANTOME"}}, "tables": []}
    result = run_demo.audit_from_sources(ocr, [{"nom_client": "GEREP SA"}])
    assert result["verdict"] == "CLIENT_NON_TROUVE"


def test_demo_generates_fic(tmp_path):
    result = run_demo.run(make_fic=True, out_dir=str(tmp_path), printer=lambda *_: None)
    fic = result["_fic_path"]
    # python-docx est installé en CI -> un .docx doit être produit.
    assert fic and fic.endswith(".docx")
    assert os.path.isfile(fic)
