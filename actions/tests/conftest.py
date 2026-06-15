"""Fixtures pytest : isole la base SQLite et les répertoires par test, et fournit
un client FastAPI authentifié avec une clé API de test."""
from __future__ import annotations

import importlib
import os
import sys

import pytest

# Rendre le package `app` importable (actions/ est la racine).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

API_KEY = "test-key-0123456789"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Environnement isolé : DB/jobs/reference dans tmp, clé API et flags par défaut."""
    monkeypatch.setenv("ONIX_ACTIONS_API_KEY", API_KEY)
    monkeypatch.setenv("ONIX_ACTIONS_DB", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("ONIX_JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("ONIX_REFERENCE_DIR", str(tmp_path / "reference"))
    # Repartir d'un état de flags neutre.
    for var in list(os.environ):
        if var.startswith("ONIX_") and var.endswith("_ENABLED"):
            monkeypatch.delenv(var, raising=False)
    return tmp_path


@pytest.fixture()
def client(env):
    """TestClient FastAPI avec DB initialisée (startup déclenché)."""
    from fastapi.testclient import TestClient

    # Réimport propre pour que les modules relisent les env vars.
    import app.admin_state as admin_state
    import app.main as main

    importlib.reload(admin_state)
    importlib.reload(main)

    with TestClient(main.app) as c:
        c.headers.update({"X-API-Key": API_KEY})
        yield c
