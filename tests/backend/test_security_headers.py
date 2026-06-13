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


# --- AUD-06 : redaction des dimensions de télémétrie + détails dynamiques ------

def test_appinsights_dimensions_routed_through_redaction(monkeypatch):
    """Les dimensions de télémétrie AppInsights passent par le helper de redaction
    avant émission (aucune valeur sensible ne fuit vers le puits)."""
    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATIONKEY", "test-ikey")
    captured = {}

    def _fake_log(level, message, data=None):
        captured["message"] = message
        captured["data"] = data

    # redact_mapping est la seule surface auditée : on vérifie qu'elle est appelée.
    seen = {"called": False}
    real_redact_mapping = api_server.redact_mapping

    def _spy(mapping):
        seen["called"] = True
        return real_redact_mapping(mapping)

    monkeypatch.setattr(api_server, "redact_mapping", _spy)
    monkeypatch.setattr(api_server, "log_security", _fake_log)

    r = client.get("/health")
    assert r.status_code == 200
    assert seen["called"], "les dimensions de télémétrie doivent passer par redact_mapping"
    assert captured.get("message") == "AppInsights_Telemetry"


def test_redact_detail_helper_masks_sensitive_value():
    """Le helper de detail redacté masque une PII/un secret interpolé."""
    detail = api_server._redacted_detail("Échec", "user bob@gerep.fr token leaked")
    assert "bob@gerep.fr" not in detail
    assert "[EMAIL_MASQUÉ]" in detail
