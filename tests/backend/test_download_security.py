"""Tests de sécurité de /api/download (IDOR, traversal, UUID, fail-closed meta)."""
import json
import os
import sys

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402

VALID_UUID = "12345678-1234-5678-1234-567812345678"


def _make_job(tmp_path, job_id=VALID_UUID, owner="owner@gerep.fr", with_meta=True):
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "fiche.docx").write_text("contenu")
    if with_meta:
        (job_dir / "meta.json").write_text(json.dumps({"user_upn": owner}))
    return job_id


@pytest.mark.asyncio
async def test_owner_can_download(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    job_id = _make_job(tmp_path, owner="owner@gerep.fr")
    resp = await api_server.download_fiche_rdv(job_id, "fiche.docx", user_upn="owner@gerep.fr")
    assert isinstance(resp, FileResponse)


@pytest.mark.asyncio
async def test_idor_other_user_denied(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    job_id = _make_job(tmp_path, owner="owner@gerep.fr")
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv(job_id, "fiche.docx", user_upn="attacker@gerep.fr")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_meta_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    job_id = _make_job(tmp_path, with_meta=False)
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv(job_id, "fiche.docx", user_upn="owner@gerep.fr")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_filename_traversal_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    job_id = _make_job(tmp_path)
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv(job_id, "../../secret", user_upn="owner@gerep.fr")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_job_id_must_be_uuid(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv("not-a-uuid", "fiche.docx", user_upn="owner@gerep.fr")
    assert exc.value.status_code == 400
    assert "UUID" in exc.value.detail


@pytest.mark.asyncio
async def test_unknown_job_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    # UUID valide mais aucun répertoire de job -> 404.
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv(VALID_UUID, "fiche.docx", user_upn="owner@gerep.fr")
    assert exc.value.status_code == 404
