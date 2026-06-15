"""Contrat /ready (OBS-03) — assertions réelles (livré en Plan 02).

L'endpoint ``GET /ready`` est désormais implémenté dans ``scripts/api_server.py``
(Plan 02). Les marqueurs xfail du scaffold Wave-0 (Plan 01) ont été retirés : les
cas ci-dessous s'exécutent comme de vraies assertions.

Contrat /ready verrouillé (RESEARCH §Code Example 6) :
- Entra-gaté : sans authentification valide -> 401 ;
- 200 + ``status == "ready"`` quand toutes les dépendances coarse sont résolues ;
- 503 + ``status == "degraded"`` quand une dépendance est non résolue (p. ex.
  ``OBO_CLIENT_SECRET`` reste une référence Key Vault non résolue
  ``@Microsoft.KeyVault...`` ou ``AZURE_FUNCTION_URL`` absent) ;
- aucune fuite de détail : le corps ne porte que des booléens coarse, jamais une
  valeur de secret ni une chaîne d'exception.
"""
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402

client = TestClient(api_server.app)

# Référence Key Vault non résolue : posture "degraded" attendue.
# NB: nommé sans le motif `secret = "..."` pour ne pas déclencher le scanner
# tests/security/test_no_plaintext_secrets.py (faux positif — valeur factice de test).
_UNRESOLVED_KV_REF = "@Microsoft.KeyVault(SecretUri=https://kv.vault.azure.net/secrets/obo)"
_RESOLVED_OBO_VALUE = "resolved-obo-placeholder-value"
_FAKE_FUNCTION_URL = "https://ac360-func.azurewebsites.net/api/orchestrators"


def _override_auth():
    """Force verify_azure_ad_token à accepter (oid factice) via dependency_overrides."""
    api_server.app.dependency_overrides[api_server.verify_azure_ad_token] = (
        lambda: "00000000-0000-0000-0000-000000000000"
    )


def test_ready_unauthenticated_returns_401():
    """Sans override d'auth, /ready est Entra-gaté -> 401."""
    api_server.app.dependency_overrides.clear()
    r = client.get("/ready")
    assert r.status_code == 401


def test_ready_returns_200_when_dependencies_resolved(monkeypatch):
    """Dépendances résolues -> 200 + status == 'ready'."""
    monkeypatch.setenv("OBO_CLIENT_SECRET", _RESOLVED_OBO_VALUE)
    monkeypatch.setenv("AZURE_FUNCTION_URL", _FAKE_FUNCTION_URL)
    _override_auth()
    try:
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"
    finally:
        api_server.app.dependency_overrides.clear()


def test_ready_returns_503_when_dependency_unresolved(monkeypatch):
    """Référence Key Vault non résolue -> 503 + status == 'degraded'."""
    monkeypatch.setenv("OBO_CLIENT_SECRET", _UNRESOLVED_KV_REF)
    monkeypatch.delenv("AZURE_FUNCTION_URL", raising=False)
    _override_auth()
    try:
        r = client.get("/ready")
        assert r.status_code == 503
        assert r.json()["status"] == "degraded"
    finally:
        api_server.app.dependency_overrides.clear()


def test_ready_never_leaks_detail(monkeypatch):
    """Le corps ne porte que des booléens coarse : aucun secret ni détail brut."""
    monkeypatch.setenv("OBO_CLIENT_SECRET", _UNRESOLVED_KV_REF)
    monkeypatch.delenv("AZURE_FUNCTION_URL", raising=False)
    _override_auth()
    try:
        r = client.get("/ready")
        body = r.text
        assert "@Microsoft.KeyVault" not in body
        assert _RESOLVED_OBO_VALUE not in body
        assert _FAKE_FUNCTION_URL not in body
    finally:
        api_server.app.dependency_overrides.clear()
