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
    # document_id encode désormais (drive de l'item | item id) — drive global ici.
    assert out["document_id"] == "drive-d1|id-Contrat_GEREP.pdf"
    assert api_server._unpack_doc_id(out["document_id"]) == ("drive-d1", "id-Contrat_GEREP.pdf")
    assert out["document_name"] == "Contrat_GEREP.pdf"
    # La recherche porte bien le token délégué de l'utilisateur.
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer " + "graph-tok"


async def test_resolve_filters_non_auditable_extensions(monkeypatch):
    payload = {"value": [_item("notes.txt"), _item("Contrat.pdf"), _item("macro.xlsm")]}
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, payload)))
    out = await api_server.resolve_document(_req("contrat"), None, "u@gerep.fr")
    assert out["count"] == 1
    assert api_server._unpack_doc_id(out["document_id"])[1] == "id-Contrat.pdf"


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
    assert out["single"] is True
    assert api_server._unpack_doc_id(out["document_id"])[1] == "id-B.pdf"


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


@pytest.mark.parametrize("ctrl", ["\x00", "\x07", "\x09", "\x0a", "\x1f", "\x7f"])
async def test_resolve_rejects_control_chars_before_graph(monkeypatch, ctrl):
    """A10/CB-08 : tout caractère de contrôle dans la requête est refusé 400 avec
    le détail « caractères interdits », AVANT tout appel Graph — le garde
    _validate_resolve_query devient load-bearing (un refactor qui le retire
    casse ce test)."""
    fake = _FakeClient(_FakeResp(200, {"value": []}))
    monkeypatch.setattr(api_server, "http_client", fake)
    with pytest.raises(HTTPException) as exc:
        await api_server.resolve_document(_req(f"Gecina{ctrl}contrat"), None, "u@gerep.fr")
    assert exc.value.status_code == 400
    assert "interdit" in exc.value.detail.lower()
    assert fake.calls == []  # aucune recherche Graph déclenchée


@pytest.mark.parametrize("q,should_pass", [
    ("ab", True), ("z" * 200, True),    # bornes inclusives 2..200 : passent
    ("a", False), ("z" * 201, False),   # hors bornes : 400 avant tout Graph
])
async def test_resolve_query_length_bounds_inclusive(monkeypatch, q, should_pass):
    """CB-08 : les bornes 2..200 sont inclusives ; hors bornes => 400 sans Graph."""
    fake = _FakeClient(_FakeResp(200, {"value": []}))
    monkeypatch.setattr(api_server, "http_client", fake)
    if should_pass:
        out = await api_server.resolve_document(_req(q), None, "u@gerep.fr")
        assert out == {"count": 0}
        assert len(fake.calls) == 1
    else:
        with pytest.raises(HTTPException) as exc:
            await api_server.resolve_document(_req(q), None, "u@gerep.fr")
        assert exc.value.status_code == 400
        assert fake.calls == []


async def test_resolve_choice_deterministic_across_graph_reorder_cb01(monkeypatch):
    """CB-01 : à dates de modif égales, le tri est déterministe (clé secondaire id),
    donc `choice` résout le MÊME document même si Graph renvoie les résultats dans
    un ordre différent d'un appel à l'autre."""
    order1 = [_item("A.pdf", modified="2026-06-01T00:00:00Z"),
              _item("B.pdf", modified="2026-06-01T00:00:00Z")]
    fake1 = _FakeClient(_FakeResp(200, {"value": order1}))
    monkeypatch.setattr(api_server, "http_client", fake1)
    out1 = await api_server.resolve_document(_req("dossier", choice=1), None, "u@gerep.fr")

    fake2 = _FakeClient(_FakeResp(200, {"value": list(reversed(order1))}))
    monkeypatch.setattr(api_server, "http_client", fake2)
    out2 = await api_server.resolve_document(_req("dossier", choice=1), None, "u@gerep.fr")

    assert out1["document_id"] == out2["document_id"]  # même choix -> même document


def test_pack_unpack_doc_id_roundtrip():
    """Drive-aware id : composite (drive|item) <-> (drive, item) ; id nu rétro-compat."""
    assert api_server._pack_doc_id("b!DRIVE", "01ITEM") == "b!DRIVE|01ITEM"
    assert api_server._unpack_doc_id("b!DRIVE|01ITEM") == ("b!DRIVE", "01ITEM")
    assert api_server._unpack_doc_id("01ITEM") == (None, "01ITEM")  # id nu -> repli global
    assert api_server._pack_doc_id(None, "01ITEM") == "01ITEM"      # pas de drive -> pas de pack
    assert api_server._pack_doc_id("", "01ITEM") == "01ITEM"


async def test_resolve_uses_item_parent_drive(monkeypatch):
    """resolve encode le drive PROPRE de l'item (parentReference.driveId) — c'est ce
    qui permet d'auditer un document hors du SHAREPOINT_DRIVE_ID global."""
    item = {"id": "01ITEMX", "name": "Contrat.pdf",
            "lastModifiedDateTime": "2026-06-01T00:00:00Z",
            "parentReference": {"path": "/x", "driveId": "b!OTHER_DRIVE"}}
    monkeypatch.setattr(api_server, "http_client", _FakeClient(_FakeResp(200, {"value": [item]})))
    out = await api_server.resolve_document(_req("contrat"), None, "u@gerep.fr")
    assert out["document_id"] == "b!OTHER_DRIVE|01ITEMX"
    assert api_server._unpack_doc_id(out["document_id"]) == ("b!OTHER_DRIVE", "01ITEMX")
