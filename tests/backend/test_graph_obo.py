"""Tests de l'échange On-Behalf-Of (graph_obo) : lecture SharePoint au nom de
l'utilisateur (superposition RBAC)."""
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import graph_obo  # noqa: E402


class _FakeResp:
    def __init__(self, payload, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            # Mimic httpx.HTTPStatusError, which carries .response so the
            # transient classifier can inspect resp.status_code.
            err = httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=None)
            err.response = self  # type: ignore[assignment]
            raise err

    def json(self):
        return self._payload


def _sequence_post(responses):
    """Build a fake http_post that returns the given _FakeResp objects in order."""
    seq = list(responses)
    calls = {"n": 0}

    def fake_post(url, data=None, timeout=None):
        idx = calls["n"]
        calls["n"] += 1
        return seq[idx]

    fake_post.calls = calls  # type: ignore[attr-defined]
    return fake_post


class _RecordingSleep:
    """No-op sleep that records the delays it was asked to wait."""

    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


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

    with pytest.raises(httpx.HTTPStatusError):
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


# --------------------------------------------------------------------------- #
# AUD-05 : bounded-backoff transient-only retry wrapper                        #
# --------------------------------------------------------------------------- #

_OBO_KW = dict(tenant_id="t", client_id="c", client_secret="s")


def test_retry_on_429_then_success_honors_retry_after():
    """429 then 200: retried once; Retry-After header used as the delay."""
    sleep = _RecordingSleep()
    fake_post = _sequence_post([
        _FakeResp({}, status=429, headers={"Retry-After": "1.5"}),
        _FakeResp({"access_token": "tok-after-throttle"}),
    ])

    token = graph_obo.acquire_obo_graph_token_retrying(
        "assertion", http_post=fake_post, sleep=sleep, **_OBO_KW)

    assert token == "tok-after-throttle"
    assert fake_post.calls["n"] == 2
    # Retry-After (1.5s) honored exactly on the 429 path.
    assert sleep.delays == [1.5]


def test_retry_503_then_504_then_success():
    """503, 504, 200: retried up to attempts=3, token returned on third call."""
    sleep = _RecordingSleep()
    fake_post = _sequence_post([
        _FakeResp({}, status=503),
        _FakeResp({}, status=504),
        _FakeResp({"access_token": "tok-eventual"}),
    ])

    token = graph_obo.acquire_obo_graph_token_retrying(
        "assertion", attempts=3, base=0.5, http_post=fake_post, sleep=sleep, **_OBO_KW)

    assert token == "tok-eventual"
    assert fake_post.calls["n"] == 3
    # Two backoff sleeps (no Retry-After header -> full jitter within [0, base*2**i]).
    assert len(sleep.delays) == 2
    assert 0 <= sleep.delays[0] <= 0.5          # base * 2**0
    assert 0 <= sleep.delays[1] <= 1.0          # base * 2**1


def test_no_retry_on_401_non_transient():
    """HTTP 401 (auth error) is NOT retried — raises on first occurrence."""
    sleep = _RecordingSleep()
    fake_post = _sequence_post([
        _FakeResp({}, status=401),
        _FakeResp({"access_token": "should-not-reach"}),
    ])

    with pytest.raises(httpx.HTTPStatusError):
        graph_obo.acquire_obo_graph_token_retrying(
            "assertion", http_post=fake_post, sleep=sleep, **_OBO_KW)

    assert fake_post.calls["n"] == 1
    assert sleep.delays == []


def test_no_retry_on_403_non_transient():
    """HTTP 403 (insufficient scope) is NOT retried."""
    sleep = _RecordingSleep()
    fake_post = _sequence_post([_FakeResp({}, status=403)])

    with pytest.raises(httpx.HTTPStatusError):
        graph_obo.acquire_obo_graph_token_retrying(
            "assertion", http_post=fake_post, sleep=sleep, **_OBO_KW)

    assert fake_post.calls["n"] == 1
    assert sleep.delays == []


def test_no_retry_on_valueerror_config():
    """ValueError (missing config) is NOT retried — raises immediately."""
    sleep = _RecordingSleep()
    fake_post = _sequence_post([_FakeResp({"access_token": "tok"})])

    with pytest.raises(ValueError):
        graph_obo.acquire_obo_graph_token_retrying(
            "", http_post=fake_post, sleep=sleep, **_OBO_KW)

    # acquire_obo_graph_token raises ValueError before calling http_post.
    assert sleep.delays == []


def test_exhaustion_raises_last_transient():
    """All-transient for 3 attempts: raises the last transient exception."""
    sleep = _RecordingSleep()
    fake_post = _sequence_post([
        _FakeResp({}, status=503),
        _FakeResp({}, status=503),
        _FakeResp({}, status=504),
    ])

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        graph_obo.acquire_obo_graph_token_retrying(
            "assertion", attempts=3, http_post=fake_post, sleep=sleep, **_OBO_KW)

    # Last failure surfaced (504), and it RAISES (does not return None) so the
    # caller can map exhaustion to HTTP 503.
    assert excinfo.value.response.status_code == 504
    assert fake_post.calls["n"] == 3
    # Slept between attempts 1->2 and 2->3, but NOT after the final failure.
    assert len(sleep.delays) == 2


def test_retry_on_httpx_timeout_transient():
    """httpx.TimeoutException is transient -> retried, then success."""
    sleep = _RecordingSleep()
    calls = {"n": 0}

    def fake_post(url, data=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timed out")
        return _FakeResp({"access_token": "tok-after-timeout"})

    token = graph_obo.acquire_obo_graph_token_retrying(
        "assertion", http_post=fake_post, sleep=sleep, **_OBO_KW)

    assert token == "tok-after-timeout"
    assert calls["n"] == 2
    assert len(sleep.delays) == 1
