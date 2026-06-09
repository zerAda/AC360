"""Tests des en-têtes de sécurité HTTP et de l'honnêteté du /health."""
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402

client = TestClient(api_server.app)


def test_security_headers_present_on_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    assert r.headers.get("Cache-Control") == "no-store"
    assert "max-age" in r.headers.get("Strict-Transport-Security", "")


def test_health_has_no_inflated_security_claim():
    r = client.get("/health")
    body = r.text
    assert "Enterprise_Grade" not in body
    assert r.json()["auth"] == "entra-id-jwt"
