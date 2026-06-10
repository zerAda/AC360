"""Test du contrôle d'appartenance des jobs d'audit (anti-IDOR) :
un utilisateur ne peut consulter que le statut/verdict de SES audits.
"""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


@pytest.fixture(autouse=True)
def _clean():
    api_server._audit_job_owners.clear()
    yield
    api_server._audit_job_owners.clear()


def test_owner_recorded_and_enforced():
    api_server._record_audit_owner("job-1", "alice@gerep.fr")
    # Le propriétaire passe.
    api_server._assert_audit_owner("job-1", "alice@gerep.fr")  # ne lève pas
    # Un autre utilisateur authentifié est refusé (403).
    with pytest.raises(HTTPException) as exc:
        api_server._assert_audit_owner("job-1", "bob@gerep.fr")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_status_endpoint_blocks_non_owner():
    api_server._record_audit_owner("job-2", "alice@gerep.fr")
    # bob tente de lire le job d'alice via l'endpoint → 403 AVANT tout appel réseau.
    with pytest.raises(HTTPException) as exc:
        await api_server.get_job_status("job-2", user_upn="bob@gerep.fr")
    assert exc.value.status_code == 403


def test_unknown_job_does_not_raise_owner_error():
    # Job inconnu (ex. après redémarrage) : pas de blocage d'appartenance
    # (fail-open documenté — le verrou cross-instance est un suivi recommandé).
    api_server._assert_audit_owner("never-seen", "anyone@gerep.fr")  # ne lève pas


def test_record_owner_ignores_empty_job():
    api_server._record_audit_owner(None, "alice@gerep.fr")
    api_server._record_audit_owner("", "alice@gerep.fr")
    assert "" not in api_server._audit_job_owners
