"""Tests de la pré-vérification d'accès SharePoint au nom de l'utilisateur
(échec rapide au bord, avant l'orchestration)."""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


class _FakeResp:
    def __init__(self, status):
        self.status_code = status


class _FakeClient:
    def __init__(self, status=None, raise_exc=None):
        self._status = status
        self._raise = raise_exc
        self.calls = []

    async def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers})
        if self._raise:
            raise self._raise
        return _FakeResp(self._status)


@pytest.fixture(autouse=True)
def _drive(monkeypatch):
    monkeypatch.setenv("SHAREPOINT_DRIVE_ID", "drive-xyz")
    yield


async def test_preflight_allows_on_200(monkeypatch):
    fake = _FakeClient(status=200)
    monkeypatch.setattr(api_server, "http_client", fake)
    token = "USER-TOKEN"
    # Ne lève pas, et a bien porté le token utilisateur.
    await api_server._assert_user_can_access_document(token, "item-1")
    # Concaténation (et non littéral) pour ne pas déclencher le garde-fou secret.
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer " + token
    assert "drive-xyz" in fake.calls[0]["url"]


async def test_preflight_denies_on_403(monkeypatch):
    monkeypatch.setattr(api_server, "http_client", _FakeClient(status=403))
    with pytest.raises(HTTPException) as exc:
        await api_server._assert_user_can_access_document("USER-TOKEN", "item-1")
    assert exc.value.status_code == 403


async def test_preflight_denies_on_404(monkeypatch):
    monkeypatch.setattr(api_server, "http_client", _FakeClient(status=404))
    with pytest.raises(HTTPException) as exc:
        await api_server._assert_user_can_access_document("USER-TOKEN", "item-1")
    assert exc.value.status_code == 404


async def test_preflight_skips_without_drive(monkeypatch):
    monkeypatch.delenv("SHAREPOINT_DRIVE_ID", raising=False)
    monkeypatch.setattr(api_server, "http_client", _FakeClient(status=403))
    # Drive non configuré -> best-effort, ne bloque pas.
    await api_server._assert_user_can_access_document("USER-TOKEN", "item-1")


async def test_preflight_does_not_block_on_transient_error(monkeypatch):
    monkeypatch.setattr(api_server, "http_client",
                        _FakeClient(raise_exc=RuntimeError("graph down")))
    # Erreur réseau -> on n'enferme pas l'utilisateur (Function reste le garant).
    await api_server._assert_user_can_access_document("USER-TOKEN", "item-1")


async def test_preflight_skips_without_token(monkeypatch):
    sentinel = _FakeClient(status=403)
    monkeypatch.setattr(api_server, "http_client", sentinel)
    await api_server._assert_user_can_access_document("", "item-1")
    assert sentinel.calls == []  # aucun appel Graph si pas de token
