"""
Tests de neutralisation des journaux (anti fuite d'info / log-injection).

Couvre :
- l'unité `safe_logger.redact()` (masquage secrets/PII, contrôles, troncature) ;
- l'intégration `api_server.run_audit_pipeline()` : le stderr brut du pipeline
  ne doit JAMAIS être passé tel quel à `db_manager.log_audit_action` — il doit
  être neutralisé via `redact()` avant d'être persisté dans audit_logs.details.
"""
from unittest.mock import MagicMock, patch

import api_server
from safe_logger import redact

# --- Faux secrets / PII réutilisés dans les tests ---------------------------
FAKE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    ".s3cr3tSignaturePartAbcDef0123456789"
)
FAKE_SECRET_VALUE = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"
FAKE_EMAIL = "jean.dupont@client-prive.fr"
FAKE_IBAN = "FR7630006000011234567890189"


def _stderr_with_secrets():
    """Reproduit une trace pipeline réaliste (chemin, trace, secrets, PII, ANSI)."""
    return (
        "Traceback (most recent call last):\n"
        '  File "C:\\AC360\\scripts\\process_document_ocr.py", line 42, in <module>\n'
        f"    Auth header: Bearer {FAKE_JWT}\n"
        f'    AZURE_OCR_KEY="{FAKE_SECRET_VALUE}"\n'
        f"    Client: {FAKE_EMAIL} | IBAN {FAKE_IBAN}\n"
        "RuntimeError: \x1b[31mL'extraction OCR a échoué\x1b[0m\n"
    )


# ---------------------------------------------------------------------------
# Unité : safe_logger.redact()
# ---------------------------------------------------------------------------
def test_redact_masque_secrets_et_pii():
    raw = (
        f"token={FAKE_JWT} "
        f'AZURE_OCR_KEY="{FAKE_SECRET_VALUE}" '
        f"mail={FAKE_EMAIL} iban={FAKE_IBAN}"
    )
    out = redact(raw)

    assert FAKE_JWT not in out
    assert FAKE_SECRET_VALUE not in out
    assert FAKE_EMAIL not in out
    assert FAKE_IBAN not in out
    assert "MASQUÉ" in out  # au moins un marqueur de masquage présent


def test_redact_supprime_controles_et_ansi():
    out = redact("ligne1\nligne2\r\n\x1b[31mrouge\x1b[0m\tindente")

    # Aucun caractère de contrôle ne subsiste (anti forge de lignes de log).
    assert "\n" not in out
    assert "\r" not in out
    assert "\t" not in out
    assert "\x1b" not in out
    # Le contenu lisible est préservé.
    assert "ligne1" in out and "ligne2" in out and "rouge" in out


def test_redact_tronque_les_messages_longs():
    out = redact("A" * 5000, max_len=200)

    assert len(out) <= 200 + 60  # 200 utiles + marqueur de troncature borné
    assert "tronqué" in out


def test_redact_robuste_aux_entrees_invalides():
    assert redact(None) == ""
    assert redact(12345678901234) == "[PII_MASQUÉE]"  # 14 chiffres -> masqué


# ---------------------------------------------------------------------------
# Intégration : run_audit_pipeline -> log_audit_action
# ---------------------------------------------------------------------------
def test_run_audit_pipeline_neutralise_stderr_avant_persistance():
    """
    Quand le pipeline échoue (returncode != 0), le stderr (secrets + PII) doit
    être neutralisé AVANT d'être passé à db_manager.log_audit_action.
    """
    fake_proc = MagicMock()
    fake_proc.returncode = 1
    fake_proc.stderr = _stderr_with_secrets()

    fake_log = MagicMock()

    with patch("api_server.subprocess.run", return_value=fake_proc), \
         patch("api_server.os.makedirs"), \
         patch("db_manager.log_audit_action", fake_log):
        api_server.run_audit_pipeline(
            job_id="job-test-0001",
            doc_path="C:\\AC360\\jobs\\doc.pdf",
            user_principal_name="agent@gerep.fr",
        )

    # On isole l'appel d'échec END_AUDIT / FAILED.
    failed_calls = [
        c for c in fake_log.call_args_list
        if len(c.args) >= 4 and c.args[1] == "END_AUDIT" and c.args[2] == "FAILED"
    ]
    assert failed_calls, "log_audit_action n'a pas reçu d'appel END_AUDIT/FAILED"

    details = failed_calls[0].args[3]

    # Aucun secret ni PII en clair ne doit être persisté.
    assert FAKE_JWT not in details
    assert FAKE_SECRET_VALUE not in details
    assert FAKE_EMAIL not in details
    assert FAKE_IBAN not in details

    # Aucun caractère de contrôle (anti log-injection sur audit_logs.details).
    assert "\n" not in details
    assert "\r" not in details
    assert "\x1b" not in details

    # Le message reste exploitable : préfixe métier + marqueurs de masquage.
    assert details.startswith("Erreur Pipeline:")
    assert "MASQUÉ" in details
