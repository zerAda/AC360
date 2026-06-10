"""Tests résolution des paramètres Planner (anti-POC) : placeholders -> config,
date -> datetime ISO Graph."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for v in ("PLANNER_DEFAULT_PLAN_ID", "PLANNER_DEFAULT_BUCKET_ID"):
        monkeypatch.delenv(v, raising=False)
    yield


def test_placeholders_resolve_from_env(monkeypatch):
    monkeypatch.setenv("PLANNER_DEFAULT_PLAN_ID", "plan-real-123")
    monkeypatch.setenv("PLANNER_DEFAULT_BUCKET_ID", "bucket-real-456")
    plan, bucket, _ = api_server._resolve_planner_params("DEFAULT_PLAN", "DEFAULT_BUCKET", "2026-12-31")
    assert plan == "plan-real-123"
    assert bucket == "bucket-real-456"


def test_placeholders_without_env_stay_empty():
    plan, bucket, _ = api_server._resolve_planner_params("DEFAULT_PLAN", "DEFAULT_BUCKET", None)
    assert plan == "" and bucket == ""  # -> l'endpoint renverra 400 (échec clair)


def test_real_ids_pass_through():
    plan, bucket, _ = api_server._resolve_planner_params("p1", "b1", None)
    assert plan == "p1" and bucket == "b1"


def test_date_only_normalized_to_iso_datetime():
    _, _, due = api_server._resolve_planner_params("p", "b", "2026-12-31")
    assert due == "2026-12-31T00:00:00Z"


def test_full_datetime_unchanged():
    _, _, due = api_server._resolve_planner_params("p", "b", "2026-12-31T09:30:00Z")
    assert due == "2026-12-31T09:30:00Z"


def test_empty_due_unchanged():
    _, _, due = api_server._resolve_planner_params("p", "b", None)
    assert due is None
