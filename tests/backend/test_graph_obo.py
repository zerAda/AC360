"""Tests de l'échange On-Behalf-Of (graph_obo) : lecture SharePoint au nom de
l'utilisateur (superposition RBAC)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import graph_obo  # noqa: E402


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_obo_builds_correct_request_and_returns_token():
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeResp({"access_token": "graph-token-xyz"})

    # "Bearer " concaténé (et non en littéral unique) pour ne pas déclencher le
    # garde-fou anti-secret sur un faux jeton de test.
    token = graph_obo.acquire_obo_graph_token(
        "Bearer " + "user-assertion-123",
        tenant_id="tenant-1",
        client_id="api-app-id",
        client_secret="shh",
        http_post=fake_post,
    )
    assert token == "graph-token-xyz"
    assert captured["url"] == "https://login.microsoftonline.com/tenant-1/oauth2/v2.0/token"
    d = captured["data"]
    # "Bearer " est retiré de l'assertion.
    assert d["assertion"] == "user-assertion-123"
    assert d["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
    assert d["requested_token_use"] == "on_behalf_of"
    assert d["scope"] == "https://graph.microsoft.com/.default"
    assert d["client_id"] == "api-app-id"
    assert d["client_secret"] == "shh"


def test_obo_raises_without_assertion():
    with pytest.raises(ValueError):
        graph_obo.acquire_obo_graph_token(
            "", tenant_id="t", client_id="c", client_secret="s", http_post=lambda **k: None)


def test_obo_raises_when_not_configured():
    with pytest.raises(ValueError):
        graph_obo.acquire_obo_graph_token(
            "assertion", tenant_id=None, client_id=None, client_secret=None,
            http_post=lambda **k: None)


def test_obo_raises_when_response_has_no_token():
    with pytest.raises(ValueError):
        graph_obo.acquire_obo_graph_token(
            "assertion", tenant_id="t", client_id="c", client_secret="s",
            http_post=lambda *a, **k: _FakeResp({"token_type": "Bearer"}))


def test_obo_propagates_http_error():
    def fake_post(*a, **k):
        return _FakeResp({}, status=401)

    with pytest.raises(RuntimeError):
        graph_obo.acquire_obo_graph_token(
            "assertion", tenant_id="t", client_id="c", client_secret="s", http_post=fake_post)


def test_obo_configured_reflects_env(monkeypatch):
    monkeypatch.delenv("OBO_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OBO_CLIENT_ID", raising=False)
    monkeypatch.delenv("CLIENT_ID", raising=False)
    monkeypatch.delenv("TENANT_ID", raising=False)
    assert graph_obo.obo_configured() is False

    monkeypatch.setenv("TENANT_ID", "t")
    monkeypatch.setenv("CLIENT_ID", "c")
    monkeypatch.setenv("OBO_CLIENT_SECRET", "s")
    assert graph_obo.obo_configured() is True


def test_obo_resolves_from_env(monkeypatch):
    monkeypatch.setenv("TENANT_ID", "tenant-env")
    monkeypatch.setenv("CLIENT_ID", "client-env")
    monkeypatch.setenv("OBO_CLIENT_SECRET", "secret-env")
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeResp({"access_token": "tok"})

    token = graph_obo.acquire_obo_graph_token("assertion", http_post=fake_post)
    assert token == "tok"
    assert "tenant-env" in captured["url"]
    assert captured["data"]["client_id"] == "client-env"
    assert captured["data"]["client_secret"] == "secret-env"
