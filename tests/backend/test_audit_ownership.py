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


# --- AUD-03 : contrôle Durable AUTORITAIRE basé sur hash_id(oid) ---------------

_OID_ALICE = "11111111-1111-1111-1111-111111111111"
_OID_BOB = "22222222-2222-2222-2222-222222222222"


def _durable_entry(owner_oid):
    """Entrée d'orchestration Durable telle que renvoyée par le webhook statut :
    `input` est une chaîne JSON contenant l'owner_hash persisté (hash de l'oid)."""
    import json
    return {
        "runtimeStatus": "Completed",
        "input": json.dumps({"document_id": "doc-1",
                             "owner_hash": api_server.hash_id(owner_oid)}),
    }


def test_durable_owner_match_passes():
    # Le propriétaire (même oid) passe le contrôle Durable autoritaire.
    api_server._assert_durable_owner(_durable_entry(_OID_ALICE), _OID_ALICE)  # ne lève pas


def test_durable_owner_mismatch_raises_403():
    # owner_hash persisté != hash_id(oid appelant) -> 403 (gate autoritaire dur).
    with pytest.raises(HTTPException) as exc:
        api_server._assert_durable_owner(_durable_entry(_OID_ALICE), _OID_BOB)
    assert exc.value.status_code == 403


def test_durable_owner_uses_oid_hash_not_raw():
    # Le hash persisté est bien hash_id(oid) — un oid brut comparé tel quel échouerait.
    entry = _durable_entry(_OID_ALICE)
    import json
    persisted = json.loads(entry["input"])["owner_hash"]
    assert persisted == api_server.hash_id(_OID_ALICE)
    assert persisted != _OID_ALICE  # ce n'est jamais l'oid en clair
