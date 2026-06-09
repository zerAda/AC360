"""Tests du endpoint /api/audit/{job_id}/status (fail-closed + passthrough 404)."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


@pytest.mark.asyncio
async def test_status_fails_closed_without_task_hub(monkeypatch):
    """Sans TASK_HUB_NAME configuré, le statut renvoie 500 (jamais un hub de test)."""
    monkeypatch.delenv("TASK_HUB_NAME", raising=False)
    with pytest.raises(HTTPException) as exc:
        await api_server.get_job_status(job_id="abc", user_upn="u@gerep.fr")
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_status_404_passthrough(monkeypatch):
    """Un 404 de la Durable Function doit rester un 404 (pas ré-emballé en 500)."""
    monkeypatch.setenv("TASK_HUB_NAME", "AC360Hub")
    resp = MagicMock()
    resp.status_code = 404
    with patch("api_server.http_client.get", new=AsyncMock(return_value=resp)):
        with pytest.raises(HTTPException) as exc:
            await api_server.get_job_status(job_id="missing", user_upn="u@gerep.fr")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_status_completed_returns_output(monkeypatch):
    monkeypatch.setenv("TASK_HUB_NAME", "AC360Hub")
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"runtimeStatus": "Completed", "output": {"verdict": "CONFORME"}})
    with patch("api_server.http_client.get", new=AsyncMock(return_value=resp)):
        out = await api_server.get_job_status(job_id="j1", user_upn="u@gerep.fr")
    assert out["status"] == "Completed"
    assert out["result"] == {"verdict": "CONFORME"}
