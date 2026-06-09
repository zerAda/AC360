"""Tests du cache JWKS avec TTL (rotation des clés Entra ID)."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import auth  # noqa: E402


def _reset_cache():
    auth._JWKS_CACHE = None
    auth._JWKS_CACHE_TS = 0.0


def _fake_resp(keys):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"keys": keys})
    return resp


def test_cache_used_within_ttl_then_refetched_after():
    _reset_cache()
    get = MagicMock(return_value=_fake_resp([{"kid": "k1"}]))
    clock = {"t": 1000.0}

    with patch("auth.httpx.get", get), patch("auth.time.monotonic", lambda: clock["t"]), \
         patch.object(auth, "JWKS_TTL_SECONDS", 3600):
        auth._fetch_jwks()                 # fetch #1
        clock["t"] = 1000.0 + 60           # +60s < TTL
        auth._fetch_jwks()                 # cache hit
        assert get.call_count == 1

        clock["t"] = 1000.0 + 4000         # > TTL
        auth._fetch_jwks()                 # refetch
        assert get.call_count == 2


def test_force_refetch_bypasses_cache():
    _reset_cache()
    get = MagicMock(return_value=_fake_resp([{"kid": "k1"}]))
    with patch("auth.httpx.get", get), patch("auth.time.monotonic", lambda: 0.0):
        auth._fetch_jwks()
        auth._fetch_jwks(force=True)
        assert get.call_count == 2


def test_unknown_kid_forces_single_refresh():
    _reset_cache()
    # 1er JWKS sans la clé ; après refresh forcé, la clé apparaît.
    responses = [_fake_resp([{"kid": "old"}]), _fake_resp([{"kid": "old"}, {"kid": "new"}])]
    get = MagicMock(side_effect=responses)
    with patch("auth.httpx.get", get), patch("auth.time.monotonic", lambda: 0.0), \
         patch("auth.RSAAlgorithm.from_jwk", lambda s: "PUBKEY"):
        key = auth._get_public_key("new")
        assert key == "PUBKEY"
        assert get.call_count == 2  # fetch initial + refresh forcé sur kid inconnu
