"""Tests usage tracker (P0-08) : hashing PII, naming ESTIMATED, émission safe."""
import json
import pytest
import usage_tracker as ut
import feature_flags as ff


def test_build_event_hashes_pii():
    ev = ut.build_usage_event(
        "ocr_completed",
        user_id="commercial@gerep.fr",
        commercial_id="commercial@gerep.fr",
        client_id="ClientACME",
        page_count=3,
        document_count=1,
    )
    # Aucune valeur en clair, uniquement des hash.
    assert ev["user_id_hash"] == ff.hash_id("commercial@gerep.fr")
    assert ev["client_id_hash"] == ff.hash_id("ClientACME")
    assert "gerep" not in json.dumps(ev)
    assert "ACME".lower() not in json.dumps(ev).lower()


def test_estimated_token_fields_are_named_estimated():
    ev = ut.build_usage_event("message_received", estimated_tokens_input=10, estimated_tokens_output=20)
    assert "estimated_tokens_input" in ev and "estimated_tokens_output" in ev
    # Interdiction d'un champ "tokens réels" non prouvé.
    assert "tokens_input" not in ev and "real_tokens" not in ev


def test_invalid_event_type_raises():
    with pytest.raises(ValueError):
        ut.build_usage_event("not_a_real_event")


def test_invalid_status_raises():
    with pytest.raises(ValueError):
        ut.build_usage_event("ocr_started", status="exploded")


def test_emit_is_best_effort_never_raises():
    def broken_sink(_line):
        raise IOError("disk full")
    ev = ut.build_usage_event("ocr_started")
    # Ne doit PAS lever : le traçage ne casse jamais le métier.
    out = ut.emit_usage_event(ev, sink=broken_sink)
    assert out is ev


def test_track_emits_to_custom_sink():
    captured = []
    ut.track("conversation_started", sink=captured.append, conversation_id="c1")
    assert len(captured) == 1
    parsed = json.loads(captured[0])
    assert parsed["event_type"] == "conversation_started"
    assert parsed["conversation_id"] == "c1"


def test_explicit_timestamp_and_id_for_determinism():
    ev = ut.build_usage_event(
        "ocr_started", event_id="fixed-id", timestamp_utc="2026-01-01T00:00:00Z",
    )
    assert ev["event_id"] == "fixed-id"
    assert ev["timestamp_utc"] == "2026-01-01T00:00:00Z"
