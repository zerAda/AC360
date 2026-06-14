"""Tests de neutralisation des attributs de span (OBS-01, AUD-06).

Vérifie le comportement de ``telemetry.RedactingSpanProcessor.on_end`` : avant que
le span ne franchisse la frontière vers l'exportateur Azure Monitor, le NOM du span et
CHAQUE valeur d'attribut de type ``str`` doivent être neutralisés via l'unique surface
de redaction auditée (``safe_logger.redact``). Les valeurs non-``str`` restent intactes,
et ``on_end`` ne doit JAMAIS lever d'exception (le scrubbing ne peut pas casser la
requête — RESEARCH §Pitfall 3).

``conftest.py`` ajoute déjà ``scripts/`` au PYTHONPATH ; aucun SDK Azure n'est requis
(``RedactingSpanProcessor`` est duck-typé).
"""
from telemetry import RedactingSpanProcessor

# --- Faux secrets / PII (réutilisés depuis test_safe_logger_redaction.py:17-26) ----
FAKE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    ".s3cr3tSignaturePartAbcDef0123456789"
)
FAKE_SECRET_VALUE = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"
FAKE_EMAIL = "jean.dupont@client-prive.fr"
FAKE_IBAN = "FR7630006000011234567890189"


class _StubSpan:
    """Span minimal duck-typé : exactement les attributs touchés par on_end.

    Aucun exportateur live, aucun SDK : ``_name`` (str mutable) et ``_attributes``
    (dict mutable), la forme que ``RedactingSpanProcessor.on_end`` lit/écrit.
    """

    def __init__(self, name="span", attributes=None):
        self._name = name
        self._attributes = attributes


def test_on_end_masks_string_pii_attributes():
    """Les attributs PII/secret ``str`` sont masqués ; le non-``str`` passe intact."""
    span = _StubSpan(
        attributes={
            "client.email": FAKE_EMAIL,
            "client.iban": FAKE_IBAN,
            "auth.header": f"Bearer {FAKE_JWT}",
            "ocr.key": f'AZURE_OCR_KEY="{FAKE_SECRET_VALUE}"',
            "http.status_code": 200,  # non-str : doit rester intact
        }
    )

    RedactingSpanProcessor().on_end(span)

    blob = str(span._attributes)
    # Aucune des quatre valeurs brutes ne doit subsister.
    assert FAKE_EMAIL not in blob
    assert FAKE_IBAN not in blob
    assert FAKE_JWT not in blob
    assert FAKE_SECRET_VALUE not in blob
    # Au moins un marqueur de masquage est présent.
    assert "MASQUÉ" in blob
    # Le passthrough non-str est préservé tel quel.
    assert span._attributes["http.status_code"] == 200


def test_on_end_masks_span_name():
    """Le nom du span contenant une PII est neutralisé."""
    span = _StubSpan(name=f"GET /user/{FAKE_EMAIL}")

    RedactingSpanProcessor().on_end(span)

    assert FAKE_EMAIL not in span._name
    assert "MASQUÉ" in span._name


def test_on_end_never_raises():
    """on_end avale toute erreur (attributs None / absents) : la requête ne casse pas."""

    class _BrokenSpan:
        _name = None
        _attributes = None

    # _attributes None : ne doit lever aucune exception.
    RedactingSpanProcessor().on_end(_BrokenSpan())

    # Objet sans aucun des attributs attendus : la garde try/except absorbe tout.
    RedactingSpanProcessor().on_end(object())
