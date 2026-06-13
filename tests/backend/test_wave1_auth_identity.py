"""Wave 1 — corrections P0 auth/identité :
- Planner échange OBO (n'envoie plus le jeton passerelle à Graph)
- Fiche RDV : appartenance via paramètre explicite (anti-course inter-requêtes)
- config fail-fast quand TENANT_ID/CLIENT_ID manquent
"""
import json
import os
import sys
import types

import contextlib

import pytest
from fastapi import HTTPException
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402
import generate_fiche_rdv as gfr  # noqa: E402
import config  # noqa: E402
import auth  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402


# --- Identité dérivée de l'oid immuable (AUD-02) ---------------------------
def _verify_with_claims(claims):
    """Pilote verify_azure_ad_token jusqu'à l'extraction des claims (oid)."""
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy")
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("jwt.get_unverified_header",
                                  return_value={"kid": "123", "alg": "RS256"}))
        stack.enter_context(patch("auth._get_public_key", return_value="pubkey"))
        stack.enter_context(patch("jwt.decode", return_value=claims))
        stack.enter_context(patch.object(auth, "ALLOWED_ISSUERS", [claims.get("iss")]))
        stack.enter_context(patch.object(auth, "REQUIRED_SCOPES", []))
        stack.enter_context(patch.object(auth, "REQUIRED_ROLES", []))
        return auth.verify_azure_ad_token(creds)


def test_identity_is_oid_not_upn():
    oid = "deadbeef-0000-1111-2222-333344445555"
    out = _verify_with_claims({"iss": "https://i", "oid": oid, "upn": "a@gerep.fr"})
    assert out == oid  # identité = oid immuable, jamais l'upn réutilisable


def test_identity_guest_b2b_accepted_via_oid():
    # Un invité (B2B) a un oid par-locataire : il est un utilisateur de plein droit.
    oid = "guest123-0000-0000-0000-000000000000"
    out = _verify_with_claims({"iss": "https://i", "oid": oid,
                               "upn": "ext@autre-societe.com"})
    assert out == oid


def test_identity_missing_oid_rejected_401():
    with pytest.raises(HTTPException) as exc:
        _verify_with_claims({"iss": "https://i", "upn": "a@gerep.fr"})  # pas d'oid
    assert exc.value.status_code == 401


# --- Planner : OBO au lieu du passthrough -----------------------------------
async def test_planner_exchanges_obo_not_gateway_token(monkeypatch):
    captured = {}
    monkeypatch.setattr(api_server, "obo_configured", lambda: True)
    monkeypatch.setattr(api_server, "acquire_obo_graph_token", lambda raw: "graph-deleg-tok")

    async def fake_create(token, plan_id, bucket_id, title, due_date):
        captured.update(token=token, plan_id=plan_id, bucket_id=bucket_id, title=title)
        return {"id": "task-1"}

    monkeypatch.setattr(api_server, "create_planner_task", fake_create)
    req = types.SimpleNamespace(headers={"Authorization": "Bearer " + "gateway-aud-token"})
    request = api_server.PlannerTaskRequest(
        title="Relance client", due_date="2026-12-31", plan_id="PLAN1", bucket_id="BUCKET1")

    out = await api_server.api_create_planner_task(request, req, "u@gerep.fr")
    assert out["status"] == "success" and out["planner_task_id"] == "task-1"
    # Le jeton transmis à Graph est le jeton Graph DÉLÉGUÉ (OBO), pas celui de la passerelle.
    assert captured["token"] == "graph-deleg-tok"


async def test_planner_503_when_obo_unconfigured(monkeypatch):
    monkeypatch.setattr(api_server, "obo_configured", lambda: False)
    req = types.SimpleNamespace(headers={"Authorization": "Bearer " + "tok"})
    request = api_server.PlannerTaskRequest(
        title="t", due_date="2026-12-31", plan_id="P", bucket_id="B")
    with pytest.raises(HTTPException) as exc:
        await api_server.api_create_planner_task(request, req, "u@gerep.fr")
    assert exc.value.status_code == 503


# --- Fiche RDV : appartenance par paramètre explicite -----------------------
def test_fiche_owner_is_explicit_param(tmp_path, monkeypatch):
    monkeypatch.setattr(gfr, "JOBS_BASE_DIR", str(tmp_path))
    monkeypatch.delenv("CURRENT_USER_UPN", raising=False)
    gfr.generate_fiche_rdv("Client X", "synthèse", "alertes",
                           job_id="j1", owner_upn="alice@gerep.fr")
    meta = json.loads((tmp_path / "j1" / "meta.json").read_text(encoding="utf-8"))
    assert meta["user_upn"] == "alice@gerep.fr"


def test_fiche_owner_param_beats_stale_env(tmp_path, monkeypatch):
    # Simule une course : une autre requête a posé un UPN obsolète dans l'env.
    monkeypatch.setattr(gfr, "JOBS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("CURRENT_USER_UPN", "victim@gerep.fr")
    gfr.generate_fiche_rdv("Client X", "s", "a", job_id="j2", owner_upn="bob@gerep.fr")
    meta = json.loads((tmp_path / "j2" / "meta.json").read_text(encoding="utf-8"))
    assert meta["user_upn"] == "bob@gerep.fr"  # le paramètre prime → pas de mauvaise attribution


# --- config fail-fast -------------------------------------------------------
def test_config_require_auth_raises_without_identity(monkeypatch):
    monkeypatch.setattr(config, "_load_env", lambda: None)
    monkeypatch.delenv("TENANT_ID", raising=False)
    monkeypatch.delenv("CLIENT_ID", raising=False)
    with pytest.raises(config.ConfigurationError):
        config.load_config(require_auth=True)


def test_config_require_auth_ok_with_identity(monkeypatch):
    monkeypatch.setattr(config, "_load_env", lambda: None)
    monkeypatch.setenv("TENANT_ID", "t")
    monkeypatch.setenv("CLIENT_ID", "c")
    cfg = config.load_config(require_auth=True)
    assert cfg.tenant_id == "t" and cfg.client_id == "c"
