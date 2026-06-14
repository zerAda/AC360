"""Scaffold RED Wave-0 du contrat /ready (OBS-03).

L'endpoint ``GET /ready`` N'EXISTE PAS encore : il atterrit en Plan 02. Ce fichier
verrouille le contrat exact que Plan 02 doit implémenter, en miroir des scaffolds RED
de la Wave-0 de la Phase 1.

Contrat /ready verrouillé (RESEARCH §Code Example 6) :
- Entra-gaté : sans authentification valide -> 401 ;
- 200 + ``status == "ready"`` quand toutes les dépendances coarse sont résolues ;
- 503 + ``status == "degraded"`` quand une dépendance est non résolue (p. ex.
  ``OBO_CLIENT_SECRET`` reste une référence Key Vault non résolue
  ``@Microsoft.KeyVault...`` ou ``AZURE_FUNCTION_URL`` absent) ;
- aucune fuite de détail : le corps ne porte que des booléens coarse, jamais une
  valeur de secret ni une chaîne d'exception.

Décision xfail-jusqu'à-Plan-02 : tant que la route ``/ready`` est absente, FastAPI
répond 404. Les cas 401/200/503/no-leak sont donc marqués
``@pytest.mark.xfail(strict=False)`` pour que la suite de CE plan reste verte tout en
encodant le contrat. L'exécuteur de Plan 02 retire ces marqueurs (ou les voit passer
en xpass) une fois l'endpoint livré.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402

client = TestClient(api_server.app)

_XFAIL_UNTIL_PLAN_02 = pytest.mark.xfail(
    reason="OBS-03 /ready lands in Plan 02", strict=False
)

# Référence Key Vault non résolue : posture "degraded" attendue.
_UNRESOLVED_KV_REF = "@Microsoft.KeyVault(SecretUri=https://kv.vault.azure.net/secrets/obo)"
_RESOLVED_SECRET = "resolved-obo-secret-value"
_FAKE_FUNCTION_URL = "https://ac360-func.azurewebsites.net/api/orchestrators"


def _override_auth():
    """Force verify_azure_ad_token à accepter (oid factice) via dependency_overrides."""
    api_server.app.dependency_overrides[api_server.verify_azure_ad_token] = (
        lambda: "00000000-0000-0000-0000-000000000000"
    )


@_XFAIL_UNTIL_PLAN_02
def test_ready_unauthenticated_returns_401():
    """Sans override d'auth, /ready est Entra-gaté -> 401."""
    api_server.app.dependency_overrides.clear()
    r = client.get("/ready")
    assert r.status_code == 401


@_XFAIL_UNTIL_PLAN_02
def test_ready_returns_200_when_dependencies_resolved(monkeypatch):
    """Dépendances résolues -> 200 + status == 'ready'."""
    monkeypatch.setenv("OBO_CLIENT_SECRET", _RESOLVED_SECRET)
    monkeypatch.setenv("AZURE_FUNCTION_URL", _FAKE_FUNCTION_URL)
    _override_auth()
    try:
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"
    finally:
        api_server.app.dependency_overrides.clear()


@_XFAIL_UNTIL_PLAN_02
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


@_XFAIL_UNTIL_PLAN_02
def test_ready_never_leaks_detail(monkeypatch):
    """Le corps ne porte que des booléens coarse : aucun secret ni détail brut."""
    monkeypatch.setenv("OBO_CLIENT_SECRET", _UNRESOLVED_KV_REF)
    monkeypatch.delenv("AZURE_FUNCTION_URL", raising=False)
    _override_auth()
    try:
        r = client.get("/ready")
        body = r.text
        assert "@Microsoft.KeyVault" not in body
        assert _RESOLVED_SECRET not in body
        assert _FAKE_FUNCTION_URL not in body
    finally:
        api_server.app.dependency_overrides.clear()
