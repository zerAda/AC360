"""Itération adversariale — ferme des lacunes de confiance signalées à l'audit :
1. IDOR fiche RDV de bout en bout via le VRAI chemin (plus de meta.json fabriqué).
2. Validation directe de _validate_sharepoint_doc_id (jamais testée).
"""
import os
import sys

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402
import generate_fiche_rdv as gfr  # noqa: E402


# --- IDOR fiche RDV : génération réelle (owner=alice) puis téléchargement ----
async def test_fiche_idor_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    monkeypatch.setattr(gfr, "JOBS_BASE_DIR", str(tmp_path))

    request = api_server.FicheRDVRequest(client_name="Client X", summary="s", alert_points="a")
    out = await api_server.api_generate_fiche_rdv(request, user_upn="alice@gerep.fr")
    job_id = out["job_id"]
    filename = out["download_url"].split("/")[-1]

    # bob ne possède pas la fiche d'alice -> 403 (appartenance posée par le code réel).
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv(job_id, filename, user_upn="bob@gerep.fr")
    assert exc.value.status_code == 403

    # alice récupère la sienne.
    resp = await api_server.download_fiche_rdv(job_id, filename, user_upn="alice@gerep.fr")
    assert isinstance(resp, FileResponse)


# --- Validation document_id SharePoint --------------------------------------
@pytest.mark.parametrize("bad", [
    "", "../etc", "a/b", "a\\b", "a b", "a;b", 'a"b', "a'b", "a<b", "a>b",
    "a`b", "a..b", "x" * 513,
])
def test_validate_doc_id_rejects(bad):
    with pytest.raises(HTTPException) as exc:
        api_server._validate_sharepoint_doc_id(bad)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("ok", ["01ABCDEF2GHIJKLMNOP", "0123456789", "AbCd-Ef_Gh"])
def test_validate_doc_id_accepts(ok):
    assert api_server._validate_sharepoint_doc_id(ok) == ok
