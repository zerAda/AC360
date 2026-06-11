"""Wave 3 — vérification JWT RÉELLE (signe avec une clé RSA de test et exerce le
chemin cryptographique de auth.py : signature, exp, audience, issuer, scope, upn,
et confusion d'algorithme). Comble la lacune où les tests existants mockaient la
vérification elle-même (risque : un bypass d'auth serait passé inaperçu)."""
import os
import sys
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import auth  # noqa: E402

_KEY_A = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_KEY_B = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def _use_test_key(monkeypatch):
    # La passerelle récupérera NOTRE clé publique de test pour ce kid.
    monkeypatch.setattr(auth, "_get_public_key", lambda kid: _KEY_A.public_key())
    yield


def _make_token(key=None, alg="RS256", **overrides):
    now = int(time.time())
    claims = {
        "aud": auth.API_AUDIENCE,
        "iss": auth.ALLOWED_ISSUERS[0],
        "iat": now, "nbf": now - 5, "exp": now + 3600,
        "scp": "Audit.Trigger",
        "upn": "user@gerep.fr",
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key or _KEY_A, algorithm=alg, headers={"kid": "test-kid"})


def _verify(token):
    return auth.verify_azure_ad_token(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


def test_valid_token_returns_upn():
    assert _verify(_make_token()) == "user@gerep.fr"


def test_forged_signature_rejected():
    # Signé par une AUTRE clé que celle que la passerelle attend -> 401.
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(key=_KEY_B))
    assert exc.value.status_code == 401


def test_expired_token_rejected():
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(exp=int(time.time()) - 30))
    assert exc.value.status_code == 401


def test_not_yet_valid_token_rejected():
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(nbf=int(time.time()) + 600))
    assert exc.value.status_code == 401


def test_wrong_audience_rejected():
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(aud="api://some-other-app"))
    assert exc.value.status_code == 401


def test_wrong_issuer_rejected():
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(iss="https://login.microsoftonline.com/attacker/v2.0"))
    assert exc.value.status_code == 401


def test_missing_required_scope_rejected():
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(scp="SomeOtherScope"))
    assert exc.value.status_code == 403


def test_missing_upn_rejected():
    with pytest.raises(HTTPException) as exc:
        _verify(_make_token(upn=None))
    assert exc.value.status_code == 401


def test_alg_confusion_hs256_rejected():
    # Jeton HS256 (clé symétrique) : doit être refusé AVANT toute vérification de
    # signature (RS256 est épinglé) -> bloque key-confusion HMAC-avec-clé-publique.
    forged = jwt.encode({"aud": auth.API_AUDIENCE}, "x" * 40,
                        algorithm="HS256", headers={"kid": "test-kid"})
    with pytest.raises(HTTPException) as exc:
        _verify(forged)
    assert exc.value.status_code == 401


def test_missing_kid_rejected():
    forged = jwt.encode({"aud": auth.API_AUDIENCE}, _KEY_A, algorithm="RS256")
    with pytest.raises(HTTPException) as exc:
        _verify(forged)
    assert exc.value.status_code == 401
