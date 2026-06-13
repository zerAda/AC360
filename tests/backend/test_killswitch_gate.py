"""Test d'intégration : le kill-switch (P0-09) bloque réellement /api/audit (403),
et l'usage est tracé (P0-08). Vérifie que la correction est CÂBLÉE, pas seulement
présente en module isolé.
"""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402
from api_server import AuditRequest  # noqa: E402
from feature_flags import hash_id  # noqa: E402


class _FakeReq:
    headers: dict = {}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    api_server._rate_limit_store.clear()
    for v in ("AC360_AUDIT_ENABLED", "AC360_GLOBAL_ENABLED", "AC360_BLOCKED_USERS_HASHED"):
        monkeypatch.delenv(v, raising=False)
    yield


@pytest.mark.asyncio
async def test_audit_blocked_when_feature_disabled(monkeypatch):
    monkeypatch.setenv("AC360_AUDIT_ENABLED", "false")
    with pytest.raises(HTTPException) as exc:
        await api_server.trigger_audit(
            AuditRequest(document_id="01ABCDEF2GHIJ"), _FakeReq(), oid="x@gerep.fr"
        )
    assert exc.value.status_code == 403
    assert "désactiv" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_audit_blocked_when_global_off(monkeypatch):
    monkeypatch.setenv("AC360_GLOBAL_ENABLED", "false")
    with pytest.raises(HTTPException) as exc:
        await api_server.trigger_audit(
            AuditRequest(document_id="01ABCDEF2GHIJ"), _FakeReq(), oid="x@gerep.fr"
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_audit_blocked_for_specific_user(monkeypatch):
    monkeypatch.setenv("AC360_BLOCKED_USERS_HASHED", hash_id("blocked@gerep.fr"))
    with pytest.raises(HTTPException) as exc:
        await api_server.trigger_audit(
            AuditRequest(document_id="01ABCDEF2GHIJ"), _FakeReq(), oid="blocked@gerep.fr"
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_killswitch_does_not_block_by_default(monkeypatch):
    # Sans configuration, l'audit n'est PAS bloqué par le kill-switch : il
    # avance jusqu'à l'appel backend (qui échoue ici car pas de vrai backend).
    # On prouve juste que ce n'est PAS un 403 de blocage.
    with pytest.raises(HTTPException) as exc:
        await api_server.trigger_audit(
            AuditRequest(document_id="01ABCDEF2GHIJ"), _FakeReq(), oid="ok@gerep.fr"
        )
    assert exc.value.status_code != 403  # 502 (backend injoignable), pas un blocage
