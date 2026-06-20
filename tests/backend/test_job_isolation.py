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
        res = await trigger_audit(req, _fake_request(), oid="user1@gerep.fr")

    assert res["status"] == "accepted"
    assert res["job_id"] == "az-instance-001"
    assert res["requested_by"] == "user1@gerep.fr"
    # Anti-fuite : le statusQueryGetUri Durable (porteur d'une clé SAS ?code=) ne
    # doit JAMAIS être exposé au client. Le poll passe par l'endpoint passerelle
    # gété par IDOR, en chemin relatif sans secret.
    assert "statusQueryGetUri" not in res
    assert res["status_url"] == "/api/audit/az-instance-001/status"


@pytest.mark.asyncio
async def test_audit_forwarded_to_azure_function():
    """La demande est transmise à la Durable Function (endpoint /audit) avec le document_id."""
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678", client_context="ALPHA")

    post_mock = AsyncMock(return_value=_azure_response("az-instance-002"))
    with patch("api_server.http_client.post", new=post_mock), \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        await trigger_audit(req, _fake_request(), oid="test@gerep.fr")

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
            await trigger_audit(req, _fake_request(), oid="test@gerep.fr")

    assert exc.value.status_code == 400
    post_mock.assert_not_called()


@pytest.mark.asyncio
async def test_audit_validates_before_charging_quota():
    """CB-02 : la validation du document_id précède le décompte du quota — une
    entrée invalide est refusée 400 sans consommer un des 10 audits/heure ni
    toucher le réseau (le quota ne borne que les vrais audits)."""
    from fastapi import HTTPException
    req = AuditRequest(document_id="../../etc/passwd")  # caractères interdits -> 400

    rate_limit = AsyncMock(return_value=None)
    with patch("api_server.http_client.post", new=AsyncMock()) as post_mock, \
         patch("api_server._check_rate_limit", new=rate_limit):
        with pytest.raises(HTTPException) as exc:
            await trigger_audit(req, _fake_request(), oid="test@gerep.fr")

    assert exc.value.status_code == 400
    post_mock.assert_not_called()
    rate_limit.assert_not_called()  # CB-02 : pas de décompte de quota sur entrée invalide


# --- AUD-03 : isolation inter-oid (IDOR fermé) --------------------------------

_OID_A = "aaaaaaaa-0000-0000-0000-000000000001"
_OID_B = "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.mark.asyncio
async def test_owner_hash_persisted_from_oid():
    """L'owner_hash transmis à la Durable Function est hash_id(oid), pas l'oid brut."""
    import api_server
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678")
    post_mock = AsyncMock(return_value=_azure_response("az-instance-010"))
    with patch("api_server.http_client.post", new=post_mock), \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)), \
         patch("api_server.obo_configured", return_value=False):
        await trigger_audit(req, _fake_request(), oid=_OID_A)
    sent_json = post_mock.call_args[1]["json"]
    assert sent_json["owner_hash"] == api_server.hash_id(_OID_A)
    assert sent_json["owner_hash"] != _OID_A


@pytest.mark.asyncio
async def test_two_oids_produce_distinct_owner_hash():
    """Deux oids distincts -> deux owner_hash distincts : B ne peut pas accéder au job de A."""
    import api_server
    assert api_server.hash_id(_OID_A) != api_server.hash_id(_OID_B)


@pytest.mark.asyncio
async def test_durable_gate_blocks_cross_oid_status_read():
    """Le contrôle Durable autoritaire refuse à B (403) la lecture du statut du job de A."""
    import json
    from fastapi import HTTPException
    import api_server

    durable_data = {
        "runtimeStatus": "Running",
        "input": json.dumps({"document_id": "doc-x",
                             "owner_hash": api_server.hash_id(_OID_A)}),
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=durable_data)

    with patch("api_server.http_client.get", new=AsyncMock(return_value=resp)), \
         patch.dict(os.environ, {"TASK_HUB_NAME": "hub"}):
        with pytest.raises(HTTPException) as exc:
            await api_server.get_job_status("doc-x", oid=_OID_B)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_obo_exhaustion_returns_503_not_502():
    """AUD-05 : l'épuisement du wrapper OBO (réessais) -> HTTP 503 (retriable), pas 502."""
    from fastapi import HTTPException
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678")

    def _boom(*_a, **_k):
        raise RuntimeError("transient OBO failure exhausted")

    with patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)), \
         patch("api_server.obo_configured", return_value=True), \
         patch("api_server.acquire_obo_graph_token_retrying", side_effect=_boom):
        with pytest.raises(HTTPException) as exc:
            await trigger_audit(req, _fake_request(), oid=_OID_A)
    assert exc.value.status_code == 503
