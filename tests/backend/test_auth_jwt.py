import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
from auth import verify_azure_ad_token
from fastapi.security import HTTPAuthorizationCredentials

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
