"""Tests du endpoint /api/audit/{job_id}/status (fail-closed + passthrough 404)."""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402

# oid de l'appelant utilisé dans ces tests de présentation. Depuis le cutover
# oid (clean-cutover), TOUT job terminal porte un owner_hash : les fixtures
# Durable ci-dessous l'incluent donc, sinon le gate fail-closed (WR-01) refuse
# en 403 avant d'atteindre le contrat de présentation testé ici.
_STATUS_OID = "u@gerep.fr"


def _durable_input(oid: str, **extra) -> str:
    payload = {"document_id": "doc-1", "owner_hash": api_server.hash_id(oid)}
    payload.update(extra)
    return json.dumps(payload)


@pytest.mark.asyncio
async def test_status_fails_closed_without_task_hub(monkeypatch):
    """Sans TASK_HUB_NAME configuré, le statut renvoie 500 (jamais un hub de test)."""
    monkeypatch.delenv("TASK_HUB_NAME", raising=False)
    with pytest.raises(HTTPException) as exc:
        await api_server.get_job_status(job_id="abc", oid="u@gerep.fr")
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_status_404_passthrough(monkeypatch):
    """Un 404 de la Durable Function doit rester un 404 (pas ré-emballé en 500)."""
    monkeypatch.setenv("TASK_HUB_NAME", "AC360Hub")
    resp = MagicMock()
    resp.status_code = 404
    with patch("api_server.http_client.get", new=AsyncMock(return_value=resp)):
        with pytest.raises(HTTPException) as exc:
            await api_server.get_job_status(job_id="missing", oid="u@gerep.fr")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_status_completed_returns_output(monkeypatch):
    monkeypatch.setenv("TASK_HUB_NAME", "AC360Hub")
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"runtimeStatus": "Completed",
                                        "input": _durable_input(_STATUS_OID),
                                        "output": {"verdict": "CONFORME"}})
    with patch("api_server.http_client.get", new=AsyncMock(return_value=resp)):
        out = await api_server.get_job_status(job_id="j1", oid=_STATUS_OID)
    assert out["status"] == "Completed"
    assert out["result"] == {"verdict": "CONFORME"}


@pytest.mark.asyncio
async def test_status_flattens_nested_audit_verdict(monkeypatch):
    """La sortie Durable réelle est imbriquée (output.result.verdict) : le endpoint
    remonte verdict/score/client au premier niveau pour un rendu propre côté bot."""
    monkeypatch.setenv("TASK_HUB_NAME", "AC360Hub")
    durable_output = {
        "status": "Completed",
        "result": {
            "client_document": "GEREP SA",
            "meilleur_match_fabric": "GEREP SA",
            "score_correspondance_nom": 98.0,
            "verdict": "ECART",
            "fields": [{"champ": "plafond_hospitalisation", "statut": "MISMATCH"}],
        },
        "fic_path": "/jobs/j2/FIC_Brouillon_GEREP_SA.docx",
        "error": None,
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"runtimeStatus": "Completed",
                                        "input": _durable_input(_STATUS_OID),
                                        "output": durable_output})
    with patch("api_server.http_client.get", new=AsyncMock(return_value=resp)):
        out = await api_server.get_job_status(job_id="j2", oid=_STATUS_OID)
    assert out["verdict"] == "ECART"
    assert out["client_document"] == "GEREP SA"
    assert out["reference_fabric"] == "GEREP SA"
    assert out["score_nom"] == 98.0
    assert out["fic_available"] is True
    assert isinstance(out["fields"], list) and out["fields"][0]["statut"] == "MISMATCH"
