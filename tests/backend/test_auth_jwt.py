import pytest
from fastapi import HTTPException
from unittest.mock import patch
import auth
from auth import verify_azure_ad_token
from fastapi.security import HTTPAuthorizationCredentials


def _creds():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy")


def _decode_path(claims):
    """Context-managers that drive verify_azure_ad_token to the claim-extraction tail.

    Bypasses signature/key fetch by mocking the header read, public key lookup and
    jwt.decode; relaxes issuer/scope/role gates so the oid logic is what's exercised.
    """
    return [
        patch("jwt.get_unverified_header", return_value={"kid": "123", "alg": "RS256"}),
        patch("auth._get_public_key", return_value="pubkey"),
        patch("jwt.decode", return_value=claims),
        patch.object(auth, "ALLOWED_ISSUERS", [claims.get("iss")]),
        patch.object(auth, "REQUIRED_SCOPES", []),
        patch.object(auth, "REQUIRED_ROLES", []),
    ]


def _run(claims):
    import contextlib
    with contextlib.ExitStack() as stack:
        for cm in _decode_path(claims):
            stack.enter_context(cm)
        return verify_azure_ad_token(_creds())


def test_verify_returns_oid_not_upn():
    oid = "11111111-2222-3333-4444-555555555555"
    out = _run({"iss": "https://issuer", "oid": oid, "upn": "user@gerep.fr"})
    assert out == oid


def test_verify_missing_oid_raises_401():
    with pytest.raises(HTTPException) as exc:
        _run({"iss": "https://issuer", "upn": "user@gerep.fr"})  # no oid
    assert exc.value.status_code == 401


def test_verify_guest_b2b_oid_accepted():
    # Guest/B2B: per-tenant oid present, external upn -> accepted, returns oid.
    oid = "99999999-aaaa-bbbb-cccc-dddddddddddd"
    out = _run({"iss": "https://issuer", "oid": oid, "upn": "guest@partner-corp.com"})
    assert out == oid


def test_verify_does_not_return_upn():
    oid = "abababab-cdcd-efef-0101-202020202020"
    out = _run({"iss": "https://issuer", "oid": oid, "upn": "someone@gerep.fr"})
    assert out != "someone@gerep.fr"
    assert out == oid


def test_verify_jwt_missing_kid():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="eyJhbGciOiJIUzI1NiJ9.e30.signature")
    with patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
        with pytest.raises(HTTPException) as exc:
            verify_azure_ad_token(creds)
        assert exc.value.status_code == 401
        assert "kid" in exc.value.detail


def test_verify_jwt_wrong_alg():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy")
    with patch("jwt.get_unverified_header", return_value={"kid": "123", "alg": "HS256"}):
        with pytest.raises(HTTPException) as exc:
            verify_azure_ad_token(creds)
        assert exc.value.status_code == 401
        assert "RS256" in exc.value.detail
