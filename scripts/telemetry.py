"""telemetry.py — Câblage OpenTelemetry / Azure Monitor avec redaction préservée (OBS-01).

Ce module fournit le câblage de télémétrie de production pour AC360 :

- ``RedactingSpanProcessor`` : un processeur de spans qui neutralise le NOM du span
  et CHAQUE valeur d'attribut de type ``str`` à travers l'UNIQUE surface de redaction
  auditée (``safe_logger.redact``) AVANT que le span ne franchisse la frontière vers
  l'exportateur Azure Monitor. Aucun nouveau regex de redaction n'est introduit
  (AUD-06 — surface de redaction unique) ; on réutilise exactement les motifs/masques
  de ``safe_logger`` (mêmes que ``redact_mapping`` à safe_logger.py:137-140).
- ``setup_telemetry()`` : câble l'exportateur réel ``configure_azure_monitor`` UNIQUEMENT
  lorsque le gate d'environnement AppInsights est posé. Tant que le gate est fermé
  (dev / test / import), la fonction est INERTE et retourne ``None`` (même posture que
  ``audit_trail.emit_document_access`` à audit_trail.py:77-78).

Sûreté à l'import : ce module n'importe AUCUN paquet ``azure.*`` ni ``opentelemetry.*``
au niveau module. L'exportateur n'est importé que paresseusement à l'intérieur de
``setup_telemetry()`` (même discipline que function_app.py:26-33), de sorte que la
collection pytest n'exige jamais le paquet ``azure-monitor-opentelemetry``.

L'exportateur réel (``configure_azure_monitor``) est la dépendance que la Phase 1 avait
explicitement reportée à la Phase 3 OBS-01, derrière le même gate AppInsights.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from safe_logger import redact

__all__ = ["RedactingSpanProcessor", "setup_telemetry"]

# Gate d'environnement AppInsights — même garde qu'à audit_trail.py:47 et
# api_server.py:84. L'une ou l'autre variable suffit à activer la télémétrie.
_APPINSIGHTS_ENV_VARS = (
    "APPINSIGHTS_INSTRUMENTATIONKEY",
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
)


def _appinsights_gate_open() -> bool:
    """Vrai si le gate AppInsights est posé (au moins une variable non vide)."""
    return any(
        (os.environ.get(name) or "").strip() for name in _APPINSIGHTS_ENV_VARS
    )


class RedactingSpanProcessor:
    """Processeur de spans qui neutralise nom + attributs ``str`` avant export.

    Choix de conception (AUD-06) : classe duck-typée plutôt que sous-classe de
    ``opentelemetry.sdk.trace.SpanProcessor``. Cela évite tout import ``opentelemetry.*``
    au niveau module (sûreté à l'import / collection pytest sans le SDK) tout en restant
    pleinement testable hors SDK : la distribution Azure Monitor accepte tout objet
    exposant ``on_start`` / ``on_end`` / ``shutdown`` / ``force_flush``.

    ``on_end`` route ``span._name`` et chaque valeur ``str`` de ``span._attributes`` à
    travers ``safe_logger.redact`` — EXACTEMENT la même surface auditée que
    ``redact_mapping`` (safe_logger.py:137-140). Les valeurs non-``str`` (int, bool,
    None...) sont laissées intactes. AUCUN nouveau regex de redaction n'est ajouté ici.
    """

    def on_start(self, span: Any, parent_context: Optional[Any] = None) -> None:
        """Aucune neutralisation au démarrage : les attributs PII arrivent après."""
        return None

    def on_end(self, span: Any) -> None:
        """Neutralise le nom du span et ses attributs ``str`` avant export.

        Tout le corps est enveloppé dans ``try/except Exception`` : la neutralisation
        de la télémétrie ne doit JAMAIS lever d'exception dans le chemin de requête
        (RESEARCH §Pitfall — le scrubbing ne peut pas casser la requête).
        """
        try:
            name = getattr(span, "_name", None)
            if isinstance(name, str):
                span._name = redact(name)

            attributes = getattr(span, "_attributes", None)
            if attributes:
                for key, value in list(attributes.items()):
                    if isinstance(value, str):
                        attributes[key] = redact(value)
        except Exception:  # pragma: no cover - filet de sécurité défensif
            pass

    def shutdown(self) -> None:
        """Aucune ressource détenue : rien à libérer."""
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Aucun tampon interne : flush immédiat réussi."""
        return True


def setup_telemetry() -> None:
    """Câble l'exportateur Azure Monitor (gaté, import paresseux, redaction-préservée).

    INERTE par défaut : si le gate AppInsights est fermé (aucune des deux variables
    d'environnement n'est posée), retourne immédiatement ``None`` sans importer le SDK
    (même posture inerte qu'``audit_trail.emit_document_access`` à audit_trail.py:77-78).

    Lorsque le gate est ouvert, importe paresseusement ``configure_azure_monitor`` et
    l'appelle avec ``logger_name="AC360"`` (même nom que ``safe_logger.logger``) et
    ``span_processors=[RedactingSpanProcessor()]`` afin que la redaction s'exécute dans
    le chemin d'export.

    N'est PAS appelée à l'import : ``api_server`` (Plan 02) l'invoque au démarrage.
    """
    if not _appinsights_gate_open():
        return None

    # Import paresseux : le SDK lourd n'est requis que lorsque le gate est ouvert
    # (collection pytest et import hors prod n'exigent jamais le paquet).
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(
        logger_name="AC360",
        span_processors=[RedactingSpanProcessor()],
    )
    return None
