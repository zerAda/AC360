"""Tests de l'orchestration pure run_audit (sans runtime Durable ni cloud)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "azure_functions", "shared"))

from audit_pipeline import AuditDeps, run_audit  # noqa: E402


def _ocr_with(nom="GEREP SA", plafond="1 000 €"):
    return {
        "metadata": {"source_file": "doc.pdf", "extraction_mode": "test"},
        "fields": {
            "Raison sociale": {"value": nom, "confidence": 0.98},
            "Plafond hospitalisation": {"value": plafond, "confidence": 0.9},
        },
        "tables": [],
    }


def _deps(*, ocr=None, reference=None, fic_calls=None, ocr_raises=False):
    def download(doc_id):
        return f"/tmp/{doc_id}.pdf"

    def do_ocr(path):
        if ocr_raises:
            raise RuntimeError("AZURE_OCR_KEY=supersecret-leaked-value boom")
        return ocr if ocr is not None else _ocr_with()

    def fetch_reference(identity):
        return reference

    def make_fic(name, result):
        if fic_calls is not None:
            fic_calls.append((name, result.get("verdict")))
        return "/tmp/fic.docx"

    return AuditDeps(download=download, ocr=do_ocr,
                     fetch_reference=fetch_reference, make_fic=make_fic)


def test_run_audit_conforme():
    deps = _deps(reference={"nom_client": "GEREP SA", "plafond_hospitalisation": "1000"})
    out = run_audit("11111111-1111-1111-1111-111111111111", None, deps)
    assert out["status"] == "Completed"
    assert out["result"]["verdict"] == "CONFORME"
    assert out["fic_path"] is None
    assert [s["name"] for s in out["stages"]][:3] == ["validate", "download", "ocr"]


def test_run_audit_ecart_triggers_fic():
    fic_calls = []
    deps = _deps(reference={"nom_client": "GEREP SA", "plafond_hospitalisation": "9999"},
                 fic_calls=fic_calls)
    out = run_audit("22222222-2222-2222-2222-222222222222", None, deps)
    assert out["status"] == "Completed"
    assert out["result"]["verdict"] == "ECART"
    assert out["fic_path"] == "/tmp/fic.docx"
    assert fic_calls == [("GEREP SA", "ECART")]


def test_run_audit_client_not_found():
    deps = _deps(reference=None)
    out = run_audit("33333333-3333-3333-3333-333333333333", None, deps)
    assert out["status"] == "Completed"
    assert out["result"]["verdict"] == "CLIENT_NON_TROUVE"
    assert out["fic_path"] is None


def test_run_audit_uses_client_context_when_ocr_has_no_name():
    deps = _deps(ocr={"metadata": {"source_file": "d", "extraction_mode": "t"},
                      "fields": {}, "tables": []},
                 reference={"nom_client": "BETA"})
    out = run_audit("44444444-4444-4444-4444-444444444444", "BETA", deps)
    assert out["status"] == "Completed"
    # client_context a servi de repli pour interroger Fabric
    assert out["result"]["meilleur_match_fabric"] == "BETA"


def test_run_audit_failure_is_neutralised():
    deps = _deps(ocr_raises=True)
    out = run_audit("55555555-5555-5555-5555-555555555555", None, deps)
    assert out["status"] == "Failed"
    assert out["result"] is None
    # Le secret présent dans l'exception ne doit jamais fuiter dans l'erreur.
    assert "supersecret-leaked-value" not in out["error"]


def test_run_audit_missing_document_id():
    deps = _deps()
    out = run_audit("", None, deps)
    assert out["status"] == "Failed"
    assert "document_id" in out["error"]


def test_run_audit_rejects_malformed_ocr():
    import pytest
    pytest.importorskip("jsonschema")
    # OCR sans le champ requis 'fields' -> rejet au stade ocr_schema.
    bad_ocr = {"metadata": {"source_file": "d", "extraction_mode": "t"}}  # pas de 'fields'/'tables'
    deps = _deps(ocr=bad_ocr, reference={"nom_client": "X"})
    out = run_audit("66666666-6666-6666-6666-666666666666", None, deps)
    assert out["status"] == "Failed"
    assert "schéma" in out["error"]
    assert any(s["name"] == "ocr_schema" and not s["ok"] for s in out["stages"])


def test_run_audit_result_conforms_to_schema():
    import pytest
    pytest.importorskip("jsonschema")
    deps = _deps(reference={"nom_client": "GEREP SA", "plafond_hospitalisation": "1000"})
    out = run_audit("77777777-7777-7777-7777-777777777777", None, deps)
    # Le stage de validation du résultat doit être OK.
    assert any(s["name"] == "result_schema" and s["ok"] for s in out["stages"])
