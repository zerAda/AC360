"""Contrat de la piste d'audit (AUD-07) — Wave 0 RED scaffold.

Spécification exécutable du contrat d'événement d'accès document, à satisfaire
par ``scripts/audit_trail.emit_document_access`` (livré en Plan 01-04, ABSENT à
la Wave 0). L'import du module est volontairement DIRECT (pas de
``pytest.importorskip`` ni d'import paresseux) : tant que le module n'existe pas,
ces tests échouent par ``ModuleNotFoundError`` — c'est l'état RED attendu de la
Wave 0.

Contrat verrouillé (RESEARCH §AUD-07) :
- l'événement émis porte EXACTEMENT les clés
  ``{user_id_hash, document_id, ts_utc, verdict}`` — aucun champ libre en plus ;
- ``user_id_hash == hash_id(oid)`` (SHA-256 de l'oid, sans sel) et l'oid brut
  n'apparaît dans AUCUNE dimension ;
- une valeur PII empoisonnée (email réaliste) passée dans le flux est
  redactée/absente des dimensions émises ;
- ``ts_utc`` est une chaîne ISO-8601 UTC.

DI uniquement : aucun exportateur Azure Monitor vivant — on assère sur le seam
pré-émission (les dimensions passées au sink ``log_security``).
"""
import os
import sys
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from feature_flags import hash_id  # noqa: E402

# Import DIRECT du module non-encore-construit : ModuleNotFoundError = RED Wave 0
# attendu (le helper atterrit en Plan 01-04).
import audit_trail  # noqa: E402
from audit_trail import emit_document_access  # noqa: E402

# --- Constantes PII factices (style test_safe_logger_redaction.py) ----------
FAKE_OID = "11112222-3333-4444-5555-666677778888"
FAKE_EMAIL = "jean.dupont@client-prive.fr"

# Contrat de champ verrouillé.
_CONTRACT_KEYS = {"user_id_hash", "document_id", "ts_utc", "verdict"}


def _capture_dims():
    """Patche le seam d'émission gaté par APPINSIGHTS_* et capture les dimensions
    passées au sink. Retourne un context manager + la liste accumulée."""
    captured = []

    def _fake_log_security(level, message, data=None):
        captured.append({"level": level, "message": message, "data": data})

    return captured, patch.object(audit_trail, "log_security", _fake_log_security)


def _emitted_dimensions(captured):
    """Extrait le dict de dimensions de l'unique événement émis."""
    assert len(captured) == 1, f"un seul événement attendu, observé {len(captured)}"
    data = captured[0]["data"]
    assert isinstance(data, dict), "les dimensions émises doivent être un dict"
    return data


def test_event_carries_exactly_the_four_contracted_fields(monkeypatch):
    """(a) Les dimensions émises portent EXACTEMENT les 4 clés contractuelles."""
    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATIONKEY", "fake-key-00000000")
    captured, cm = _capture_dims()
    with cm:
        emit_document_access(oid=FAKE_OID, document_id="doc-001", verdict="CONFORME")
    dims = _emitted_dimensions(captured)
    assert set(dims.keys()) == _CONTRACT_KEYS, (
        f"contrat AUD-07 violé : clés émises {set(dims.keys())} != {_CONTRACT_KEYS}"
    )


def test_user_id_hash_is_hash_of_oid_and_raw_oid_absent(monkeypatch):
    """(b) user_id_hash == hash_id(oid) et l'oid brut n'apparaît nulle part."""
    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATIONKEY", "fake-key-00000000")
    captured, cm = _capture_dims()
    with cm:
        emit_document_access(oid=FAKE_OID, document_id="doc-002", verdict="ECART")
    dims = _emitted_dimensions(captured)
    assert dims["user_id_hash"] == hash_id(FAKE_OID), (
        "user_id_hash doit être le SHA-256 sans sel de l'oid (hash_id)"
    )
    # L'oid brut ne doit fuiter dans AUCUNE valeur de dimension.
    for key, value in dims.items():
        assert FAKE_OID not in str(value), (
            f"oid brut fuité dans la dimension {key!r}"
        )


def test_poisoned_pii_is_redacted_or_absent(monkeypatch):
    """(c) Une PII empoisonnée (email) passée dans le flux est redactée/absente."""
    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATIONKEY", "fake-key-00000000")
    captured, cm = _capture_dims()
    with cm:
        # On empoisonne le document_id avec un email réaliste : il doit être
        # redacté avant émission (ou absent), jamais émis en clair.
        emit_document_access(
            oid=FAKE_OID,
            document_id=f"doc-{FAKE_EMAIL}",
            verdict="INCERTAIN",
        )
    dims = _emitted_dimensions(captured)
    for key, value in dims.items():
        assert FAKE_EMAIL not in str(value), (
            f"PII (email) émise en clair dans la dimension {key!r}"
        )


def test_ts_utc_is_iso8601_utc(monkeypatch):
    """(d) ts_utc est une chaîne ISO-8601 horodatée en UTC."""
    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATIONKEY", "fake-key-00000000")
    captured, cm = _capture_dims()
    with cm:
        emit_document_access(oid=FAKE_OID, document_id="doc-003", verdict="CONFORME")
    dims = _emitted_dimensions(captured)
    ts = dims["ts_utc"]
    assert isinstance(ts, str), "ts_utc doit être une chaîne"
    parsed = datetime.fromisoformat(ts)
    assert parsed.utcoffset() is not None, "ts_utc doit porter un offset (UTC)"
    assert parsed.utcoffset().total_seconds() == 0, "ts_utc doit être en UTC (offset 0)"


def test_emit_is_inert_when_appinsights_gate_unset(monkeypatch):
    """Garde du gate env : sans APPINSIGHTS_*, l'émission est inerte (rien émis)."""
    monkeypatch.delenv("APPINSIGHTS_INSTRUMENTATIONKEY", raising=False)
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    captured, cm = _capture_dims()
    with cm:
        emit_document_access(oid=FAKE_OID, document_id="doc-004", verdict="CONFORME")
    assert captured == [], "l'émission doit être inerte tant que le gate AppInsights est absent"
