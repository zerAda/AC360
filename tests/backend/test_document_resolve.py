"""Tests de la résolution documentaire en langage naturel (/api/documents/resolve) :
recherche Graph AU NOM de l'utilisateur (OBO), filtrage extensions, tri récence,
sélection par numéro. Remplace l'exigence d'un drive-item-id opaque."""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


class _FakeResp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, resp=None, raise_exc=None):
        self.resp = resp
        self._raise = raise_exc
        self.calls = []

    async def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        if self._raise:
            raise self._raise
        return self.resp


def _item(name, modified="2026-05-01T00:00:00Z", path="/drives/d1/root:/ClientX"):
    return {"id": f"id-{name}", "name": name,
            "lastModifiedDateTime": modified, "parentReference": {"path": path}}


def _req(query, choice=None):
    return api_server.DocumentResolveRequest(query=query, choice=choice)


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("SHAREPOINT_DRIVE_ID", "drive-d1")
    monkeypatch.setattr(api_server, "obo_configured", lambda: True)
    # resolve_document échange via le wrapper réessayant (AUD-05/WR-04).
    monkeypatch.setattr(api_server, "acquire_obo_graph_token_retrying", lambda raw: "graph-tok")
    api_server._rate_limit_store.clear()
    yield
    api_server._rate_limit_store.clear()


async def test_resolve_single_match(monkeypatch):
    fake = _FakeClient(_FakeResp(200, {"value": [_item("Contrat_GEREP.pdf")]}))
    monkeypatch.setattr(api_server, "http_client", fake)
    out = await api_server.resolve_document(_req("contrat GEREP"), None, "u@gerep.fr")
    assert out["count"] == 1 and out["single"] is True
    assert out["document_id"] == "id-Contrat_GEREP.pdf"
    assert out["document_name"] == "Contrat_GEREP.pdf"
    # La recherche porte bien le token délégué de l'utilisateur.
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer " + "graph-tok"


async def test_resolve_filters_non_auditable_extensions(monkeypatch):
    payload = {"value": [_item("notes.txt"), _item("Contrat.pdf"), _item("macro.xlsm")]}
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, payload)))
    out = await api_server.resolve_document(_req("contrat"), None, "u@gerep.fr")
    assert out["count"] == 1
    assert out["document_id"] == "id-Contrat.pdf"


async def test_resolve_multiple_sorted_by_recency(monkeypatch):
    payload = {"value": [
        _item("Ancien.pdf", modified="2024-01-01T00:00:00Z"),
        _item("Recent.pdf", modified="2026-06-01T00:00:00Z"),
        _item("Moyen.docx", modified="2025-03-01T00:00:00Z"),
    ]}
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, payload)))
    out = await api_server.resolve_document(_req("dossier"), None, "u@gerep.fr")
    assert out["count"] == 3 and out["single"] is False
    assert "document_id" not in out
    lines = out["display"].splitlines()
    assert lines[0].startswith("1. **Recent.pdf**")
    assert lines[1].startswith("2. **Moyen.docx**")
    assert "modifié 2026-06-01" in lines[0]


async def test_resolve_choice_picks_nth(monkeypatch):
    payload = {"value": [
        _item("A.pdf", modified="2026-06-01T00:00:00Z"),
        _item("B.pdf", modified="2026-05-01T00:00:00Z"),
        _item("C.pdf", modified="2026-04-01T00:00:00Z"),
    ]}
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, payload)))
    out = await api_server.resolve_document(_req("dossier", choice=2), None, "u@gerep.fr")
    assert out["single"] is True and out["document_id"] == "id-B.pdf"


async def test_resolve_invalid_choice_rejected(monkeypatch):
    payload = {"value": [_item("A.pdf"), _item("B.pdf")]}
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, payload)))
    for bad in (0, 3, -1):
        with pytest.raises(HTTPException) as exc:
            await api_server.resolve_document(_req("dossier", choice=bad), None, "u@gerep.fr")
        assert exc.value.status_code == 400


async def test_resolve_no_match(monkeypatch):
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, {"value": []})))
    out = await api_server.resolve_document(_req("client fantome"), None, "u@gerep.fr")
    assert out == {"count": 0}


async def test_resolve_rejects_bad_queries(monkeypatch):
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, {"value": []})))
    for bad in ("", "a", "x" * 201, "abc\x00def"):
        with pytest.raises(HTTPException) as exc:
            await api_server.resolve_document(_req(bad), None, "u@gerep.fr")
        assert exc.value.status_code == 400


async def test_resolve_403_passthrough(monkeypatch):
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(403)))
    with pytest.raises(HTTPException) as exc:
        await api_server.resolve_document(_req("contrat"), None, "u@gerep.fr")
    assert exc.value.status_code == 403


async def test_resolve_graph_error_is_502(monkeypatch):
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(500)))
    with pytest.raises(HTTPException) as exc:
        await api_server.resolve_document(_req("contrat"), None, "u@gerep.fr")
    assert exc.value.status_code == 502


async def test_resolve_requires_obo(monkeypatch):
    monkeypatch.setattr(api_server, "obo_configured", lambda: False)
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, {"value": []})))
    with pytest.raises(HTTPException) as exc:
        await api_server.resolve_document(_req("contrat"), None, "u@gerep.fr")
    assert exc.value.status_code == 503


async def test_resolve_escapes_odata_quote(monkeypatch):
    fake = _FakeClient(_FakeResp(200, {"value": []}))
    monkeypatch.setattr(api_server, "http_client", fake)
    await api_server.resolve_document(_req("l'avenant"), None, "u@gerep.fr")
    # Quote simple doublée (littéral OData) puis URL-encodée : %27%27.
    assert "%27%27" in fake.calls[0]["url"]
