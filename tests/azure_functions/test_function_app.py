"""Tests du wrapper Durable (logique testable sans le SDK Azure)."""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "azure_functions", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "azure_functions"))

import function_app as fa  # noqa: E402
from audit_pipeline import AuditDeps  # noqa: E402


# --- Adaptateurs FIC --------------------------------------------------------
def test_build_garanties_and_date_effet():
    audit_result = {
        "fields": [
            {"champ": "plafond_hospitalisation", "valeur_reference": "1000", "valeur_document": "1 000 €"},
            {"champ": "date_effet", "valeur_reference": "2026-06-01", "valeur_document": "01/06/2026"},
            {"champ": "vide", "valeur_reference": None, "valeur_document": None},
        ]
    }
    garanties = fa._build_garanties(audit_result)
    assert garanties["plafond_hospitalisation"] == "1000"
    assert garanties["date_effet"] == "2026-06-01"
    assert "vide" not in garanties
    assert fa._date_effet(audit_result) == "2026-06-01"


def test_make_fic_calls_generator_with_adapted_args(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    captured = {}

    def fake_generate(client_name, date_effet, plafonds, output_path):
        captured.update(client=client_name, date=date_effet, plafonds=plafonds, out=output_path)

    import generate_fic_draft
    monkeypatch.setattr(generate_fic_draft, "generate_fic_document", fake_generate)

    audit_result = {"fields": [{"champ": "plafond_hospitalisation",
                                "valeur_reference": "1000", "valeur_document": "1 000 €"}]}
    path = fa._make_fic("GEREP SA", audit_result)
    assert captured["client"] == "GEREP SA"
    assert captured["plafonds"] == {"plafond_hospitalisation": "1000"}
    assert path.endswith("FIC_Brouillon_GEREP_SA.docx")


# --- Adaptateur référence Fabric (OneLake) ---------------------------------
def test_fetch_reference_uses_onelake(monkeypatch):
    import fabric_onelake
    monkeypatch.setattr(
        fabric_onelake, "fetch_client_reference",
        lambda client_name=None, siret=None: {
            "numcli": "1", "nom_client": "GEREP SA",
            "siret": "39000000000000", "produits": ["Produit A"],
        },
    )
    ref = fa._fetch_reference({"nom_client": "GEREP", "siret": "39000000000000"})
    assert ref["nom_client"] == "GEREP SA"
    assert ref["produits"] == ["Produit A"]


def test_fetch_reference_prioritises_siret(monkeypatch):
    import fabric_onelake
    captured = {}

    def fake(client_name=None, siret=None):
        captured["siret"] = siret
        captured["name"] = client_name
        return {"nom_client": "X", "siret": siret, "numcli": "9", "produits": []}

    monkeypatch.setattr(fabric_onelake, "fetch_client_reference", fake)
    fa._fetch_reference({"nom_client": "GEREP", "siret": "39000000000000"})
    assert captured["siret"] == "39000000000000"


def test_fetch_reference_none_when_no_match(monkeypatch):
    import fabric_onelake
    monkeypatch.setattr(fabric_onelake, "fetch_client_reference",
                        lambda client_name=None, siret=None: None)
    assert fa._fetch_reference({"nom_client": "absent"}) is None


# --- Corps d'activité -------------------------------------------------------
def test_run_activity_happy_path(monkeypatch):
    deps = AuditDeps(
        download=lambda d: "/tmp/x.pdf",
        ocr=lambda p: {"metadata": {"source_file": "x", "extraction_mode": "t"},
                       "fields": {"Raison sociale": {"value": "GEREP SA"}}, "tables": []},
        fetch_reference=lambda ident: {"nom_client": "GEREP SA", "plafond_hospitalisation": "1000"},
        make_fic=lambda n, r: None,
    )
    monkeypatch.setattr(fa, "_DEPS", deps)
    out = fa._run_activity({"document_id": "11111111-1111-1111-1111-111111111111"})
    assert out["status"] == "Completed"
    assert out["result"]["verdict"] in {"CONFORME", "INCERTAIN", "ECART"}


def test_run_activity_never_raises_on_bad_payload():
    out = fa._run_activity({})  # pas de document_id
    assert out["status"] == "Failed"


# --- Orchestration (générateur) --------------------------------------------
def test_audit_orchestration_calls_activity():
    ctx = MagicMock()
    ctx.get_input.return_value = {"document_id": "doc-1", "client_context": "ALPHA"}
    ctx.call_activity.return_value = "ACTIVITY_TASK"

    gen = fa._audit_orchestration(ctx)
    task = next(gen)  # exécute jusqu'au yield context.call_activity(...)
    assert task == "ACTIVITY_TASK"
    name, payload = ctx.call_activity.call_args[0]
    assert name == "activity_run_audit"
    assert payload["document_id"] == "doc-1"

    # Renvoyer le résultat d'activité -> valeur de retour de l'orchestration.
    with pytest.raises(StopIteration) as stop:
        gen.send({"verdict": "CONFORME"})
    assert stop.value.value == {"verdict": "CONFORME"}
