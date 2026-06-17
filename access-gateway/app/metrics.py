"""metrics — observabilité Prometheus pour la passerelle RBAC onix.

Expose des compteurs et histogrammes (préfixés ``onix_gateway_``) sur le
chemin réel de la requête : RBAC, garde-fous, citations, latences, erreurs
amont. Toutes les primitives sont **exception-safe** : un défaut Prometheus
ne doit JAMAIS modifier le comportement HTTP de la passerelle.

Configuration :
  GATEWAY_METRICS_ENABLED  (bool, défaut : true) — quand false, aucun
  compteur n'est incrémenté et GET /metrics renvoie 404.

Modèle multi-worker :
  En mode uvicorn multi-worker (``--workers N``), chaque processus dispose de
  son propre registre mémoire. Le préfixe ``prometheus_multiprocess_dir``
  (variable d'env ``PROMETHEUS_MULTIPROC_DIR``) permet à prometheus-client de
  persister les métriques sur disque et d'agréger les valeurs de tous les
  workers à chaque scrape — voir docs/OBSERVABILITY.md §multiprocess. En mode
  single-worker (défaut en dev et conteneur standard), aucune configuration
  supplémentaire n'est nécessaire.
"""
from __future__ import annotations

import logging

_logger = logging.getLogger("onix.gateway")

# ─────────────────────────────────────────────────────────────────────────────
# Définitions des métriques (une seule fois au niveau module).
# ─────────────────────────────────────────────────────────────────────────────
try:
    from prometheus_client import Counter, Histogram

    # Requêtes totales par endpoint et décision (allow / deny).
    REQUESTS_TOTAL = Counter(
        "onix_gateway_requests_total",
        "Nombre total de requêtes traitées par la passerelle",
        ["endpoint", "decision"],
    )

    # Déclenchements du garde-fous : règle et blocage (true / false).
    GUARDRAIL_TOTAL = Counter(
        "onix_gateway_guardrail_total",
        "Passages dans le post-filtre garde-fous (par règle et statut de blocage)",
        ["rule", "blocked"],
    )

    # Réponse sans contexte documentaire reconstruit.
    ANSWER_NO_CONTEXT_TOTAL = Counter(
        "onix_gateway_answer_no_context_total",
        "Réponses Onyx 2xx dont le contexte documentaire reconstruit est vide",
    )

    # Présence de citation dans la réponse FINALE (après post-filtre éventuel).
    ANSWER_WITH_CITATION_TOTAL = Counter(
        "onix_gateway_answer_with_citation_total",
        "Réponses FINALES (post-filtre) comportant au moins une citation de source",
    )
    ANSWER_WITHOUT_CITATION_TOTAL = Counter(
        "onix_gateway_answer_without_citation_total",
        "Réponses FINALES (post-filtre) sans aucune citation de source",
    )

    # Latence bout-en-bout (appel amont + post-filtre) en secondes.
    # Buckets adaptés aux délais d'un LLM local (génération lente possible).
    REQUEST_LATENCY_SECONDS = Histogram(
        "onix_gateway_request_latency_seconds",
        "Latence bout-en-bout de l'appel amont + post-filtre (secondes)",
        buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120),
    )

    # Erreurs de relais vers Onyx (timeout, connexion refusée, etc.) → 502.
    UPSTREAM_ERRORS_TOTAL = Counter(
        "onix_gateway_upstream_errors_total",
        "Erreurs de relais HTTP vers l'amont Onyx (→ 502)",
    )

    # Retours utilisateur (feedback optionnel).
    FEEDBACK_TOTAL = Counter(
        "onix_gateway_feedback_total",
        "Retours utilisateur sur les réponses (up / down)",
        ["rating"],
    )

    _METRICS_AVAILABLE = True

except Exception as _exc:  # pragma: no cover — jamais déclenché en tests normaux
    _logger.debug("prometheus_client indisponible, métriques désactivées : %s", _exc)
    _METRICS_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Helpers exception-safe (appelés depuis main.py).
# Chaque helper vérifie la disponibilité ET attrape les exceptions Prometheus
# pour n'JAMAIS propager d'erreur à l'appelant.
# ─────────────────────────────────────────────────────────────────────────────

def inc_requests(endpoint: str, decision: str) -> None:
    """Incrémente `onix_gateway_requests_total{endpoint, decision}`."""
    if not _METRICS_AVAILABLE:
        return
    try:
        REQUESTS_TOTAL.labels(endpoint=endpoint, decision=decision).inc()
    except Exception as exc:
        _logger.debug("metrics inc_requests: %s", exc)


def inc_guardrail(rule: str, blocked: bool) -> None:
    """Incrémente `onix_gateway_guardrail_total{rule, blocked}`."""
    if not _METRICS_AVAILABLE:
        return
    try:
        GUARDRAIL_TOTAL.labels(rule=rule, blocked=str(blocked).lower()).inc()
    except Exception as exc:
        _logger.debug("metrics inc_guardrail: %s", exc)


def inc_answer_no_context() -> None:
    """Incrémente `onix_gateway_answer_no_context_total`."""
    if not _METRICS_AVAILABLE:
        return
    try:
        ANSWER_NO_CONTEXT_TOTAL.inc()
    except Exception as exc:
        _logger.debug("metrics inc_answer_no_context: %s", exc)


def inc_citation(has_citation: bool) -> None:
    """Incrémente l'un des deux compteurs de citation selon la présence."""
    if not _METRICS_AVAILABLE:
        return
    try:
        if has_citation:
            ANSWER_WITH_CITATION_TOTAL.inc()
        else:
            ANSWER_WITHOUT_CITATION_TOTAL.inc()
    except Exception as exc:
        _logger.debug("metrics inc_citation: %s", exc)


def observe_latency(seconds: float) -> None:
    """Enregistre une observation dans `onix_gateway_request_latency_seconds`."""
    if not _METRICS_AVAILABLE:
        return
    try:
        REQUEST_LATENCY_SECONDS.observe(seconds)
    except Exception as exc:
        _logger.debug("metrics observe_latency: %s", exc)


def inc_upstream_error() -> None:
    """Incrémente `onix_gateway_upstream_errors_total`."""
    if not _METRICS_AVAILABLE:
        return
    try:
        UPSTREAM_ERRORS_TOTAL.inc()
    except Exception as exc:
        _logger.debug("metrics inc_upstream_error: %s", exc)


def inc_feedback(rating: str) -> None:
    """Incrémente `onix_gateway_feedback_total{rating}`."""
    if not _METRICS_AVAILABLE:
        return
    try:
        FEEDBACK_TOTAL.labels(rating=rating).inc()
    except Exception as exc:
        _logger.debug("metrics inc_feedback: %s", exc)
