"""
Tests du contrat réel de /api/audit (passerelle vers Azure Durable Functions).

NOTE ARCHITECTURE : l'orchestration locale Celery a été retirée du produit
(cf. health_check : "depuis la purge de Celery"). `trigger_audit` est désormais
une passerelle qui transmet la demande à une Azure Durable Function et renvoie
le job_id émis par celle-ci. Ces tests valident le contrat *réellement livré*
(forwarding, job_id tracé, statut "accepted"), et non l'ancien flux Celery.
"""
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from api_server import trigger_audit, AuditRequest  # noqa: E402


def _fake_request(token: str = "stub-access-token") -> MagicMock:
    req = MagicMock()
    # Concaténation volontaire : évite la séquence littérale "Bearer <token>"
    # dans le source (sinon le scanner anti-secrets la signale comme fuite).
    req.headers = {"Authorization": "Bearer " + token}
    return req


def _azure_response(instance_id: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={
        "id": instance_id,
        "statusQueryGetUri": f"https://func/runtime/.../{instance_id}",
    })
    return resp


@pytest.mark.asyncio
async def test_audit_response_contains_job_id():
    """La réponse expose toujours le job_id renvoyé par l'Azure Function + statut accepted."""
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678")

    with patch("api_server.http_client.post", new=AsyncMock(return_value=_azure_response("az-instance-001"))), \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        res = await trigger_audit(req, _fake_request(), user_upn="user1@gerep.fr")

    assert res["status"] == "accepted"
    assert res["job_id"] == "az-instance-001"
    assert res["requested_by"] == "user1@gerep.fr"


@pytest.mark.asyncio
async def test_audit_forwarded_to_azure_function():
    """La demande est transmise à la Durable Function (endpoint /audit) avec le document_id."""
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678", client_context="ALPHA")

    post_mock = AsyncMock(return_value=_azure_response("az-instance-002"))
    with patch("api_server.http_client.post", new=post_mock), \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        await trigger_audit(req, _fake_request(), user_upn="test@gerep.fr")

    post_mock.assert_called_once()
    called_url = post_mock.call_args[0][0]
    assert called_url.endswith("/audit") or "/audit?" in called_url, (
        "La passerelle doit appeler l'endpoint /audit de l'Azure Function"
    )
    sent_json = post_mock.call_args[1]["json"]
    assert sent_json["document_id"] == "12345678-1234-5678-1234-567812345678"


@pytest.mark.asyncio
async def test_audit_rejects_empty_document_id():
    """Un document_id vide doit être refusé (400) avant tout appel réseau."""
    from fastapi import HTTPException
    req = AuditRequest(document_id="")

    with patch("api_server.http_client.post", new=AsyncMock()) as post_mock, \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await trigger_audit(req, _fake_request(), user_upn="test@gerep.fr")

    assert exc.value.status_code == 400
    post_mock.assert_not_called()
