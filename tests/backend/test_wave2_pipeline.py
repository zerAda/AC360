"""Wave 2 — IDOR robuste cross-instance via l'entrée d'orchestration Durable."""
import json
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


def _data_with_owner(upn):
    return {"input": {"owner_hash": api_server.hash_id(upn)}}


def test_durable_owner_mismatch_raises_403():
    with pytest.raises(HTTPException) as exc:
        api_server._assert_durable_owner(_data_with_owner("alice@gerep.fr"), "bob@gerep.fr")
    assert exc.value.status_code == 403


def test_durable_owner_match_passes():
    api_server._assert_durable_owner(_data_with_owner("alice@gerep.fr"), "alice@gerep.fr")


def test_durable_owner_absent_does_not_raise():
    # Job legacy sans owner_hash -> pas de blocage ici (autres contrôles couvrent).
    api_server._assert_durable_owner({"input": {"document_id": "d"}}, "anyone@gerep.fr")
    api_server._assert_durable_owner({}, "anyone@gerep.fr")


def test_durable_owner_string_input_is_parsed():
    # L'entrée Durable peut être sérialisée en chaîne JSON.
    data = {"input": json.dumps({"owner_hash": api_server.hash_id("alice@gerep.fr")})}
    with pytest.raises(HTTPException) as exc:
        api_server._assert_durable_owner(data, "bob@gerep.fr")
    assert exc.value.status_code == 403


def test_durable_owner_malformed_string_input_does_not_raise():
    api_server._assert_durable_owner({"input": "not-json{{"}, "anyone@gerep.fr")
