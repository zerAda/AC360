"""graph_obo.py — OAuth2 On-Behalf-Of exchange.

Échange le token d'accès de l'utilisateur (audience = cette API) contre un token
Microsoft Graph DÉLÉGUÉ qui agit AU NOM de l'utilisateur. Le téléchargement
SharePoint en aval honore alors les permissions propres de l'utilisateur
(superposition RBAC) : pas d'accès → refus Graph 403, l'audit ne démarre pas.
"""
from __future__ import annotations

import os
import random
import time
from typing import Any, Callable, Optional

_OBO_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"

# Transient Graph/Entra HTTP statuses worth retrying (throttling + gateway).
# Source (transient set / Retry-After): https://learn.microsoft.com/graph/throttling
_TRANSIENT_STATUS = frozenset({429, 503, 504})


def _resolve(value: Optional[str], *env_names: str) -> Optional[str]:
    if value:
        return value
    for name in env_names:
        v = os.environ.get(name)
        if v:
            return v
    return None


def obo_configured() -> bool:
    """True si l'échange OBO est configurable (tenant + client + secret présents)."""
    return bool(
        os.environ.get("OBO_CLIENT_SECRET")
        and os.environ.get("TENANT_ID")
        and (os.environ.get("OBO_CLIENT_ID") or os.environ.get("CLIENT_ID"))
    )


def acquire_obo_graph_token(
    user_assertion: str,
    *,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    scope: str = _GRAPH_DEFAULT_SCOPE,
    http_post: Optional[Callable] = None,
    timeout: float = 10.0,
) -> str:
    """Échange OBO : assertion utilisateur -> token Graph délégué.

    `http_post` est injectable pour les tests. Lève ValueError sur entrée/config
    manquante ou réponse sans token ; propage les erreurs HTTP du client.
    """
    assertion = (user_assertion or "").replace("Bearer ", "").strip()
    if not assertion:
        raise ValueError("user_assertion requis pour l'échange OBO.")

    tenant_id = _resolve(tenant_id, "TENANT_ID")
    client_id = _resolve(client_id, "OBO_CLIENT_ID", "CLIENT_ID")
    client_secret = _resolve(client_secret, "OBO_CLIENT_SECRET")
    if not (tenant_id and client_id and client_secret):
        raise ValueError("OBO non configuré (TENANT_ID / OBO_CLIENT_ID / OBO_CLIENT_SECRET).")

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": _OBO_GRANT,
        "client_id": client_id,
        "client_secret": client_secret,
        "assertion": assertion,
        "scope": scope,
        "requested_token_use": "on_behalf_of",
    }

    if http_post is None:
        import httpx
        http_post = httpx.post

    resp = http_post(url, data=data, timeout=timeout)
    resp.raise_for_status()
    token = (resp.json() or {}).get("access_token")
    if not token:
        raise ValueError("Réponse OBO sans access_token.")
    return token


def _is_transient(exc: BaseException) -> bool:
    """True si l'erreur OBO est transitoire (réessayable) et non un défaut de config.

    Transitoire = timeout/connexion httpx, ou réponse HTTP dans `_TRANSIENT_STATUS`
    (429/503/504). Les erreurs 4xx d'auth (401/403) et les `ValueError` de config
    NE SONT PAS transitoires : elles doivent remonter immédiatement (Pitfall 4).
    """
    import httpx

    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None) in _TRANSIENT_STATUS


# Plafond du délai Retry-After honoré : on ne bloque JAMAIS un worker du
# threadpool (acquire_obo_graph_token_retrying tourne sous run_in_threadpool)
# plus longtemps que ce cap. Un upstream throttlé/hostile renvoyant
# `Retry-After: 86400` ne peut donc pas épingler un thread une journée entière
# (déni de service sur l'instance unique).
_RETRY_AFTER_MAX_SECONDS = 30.0


def _retry_after_seconds(exc: BaseException) -> Optional[float]:
    """Délai Retry-After (en secondes) si l'erreur est un 429 avec en-tête valide.

    Le délai est borné à `_RETRY_AFTER_MAX_SECONDS` et les valeurs <= 0 (ou non
    numériques, ou en forme HTTP-date — non supportée ici) sont rejetées : on
    retombe alors sur le backoff plein-jitter de l'appelant. Cela évite à la fois
    `time.sleep(valeur_negative)` (ValueError non transitoire) et le blocage
    prolongé d'un worker."""
    resp = getattr(exc, "response", None)
    if getattr(resp, "status_code", None) != 429:
        return None
    headers = getattr(resp, "headers", None) or {}
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        secs = float(raw)
    except (TypeError, ValueError):
        return None
    if secs <= 0:
        return None
    return min(secs, _RETRY_AFTER_MAX_SECONDS)


def acquire_obo_graph_token_retrying(
    user_assertion: str,
    *,
    attempts: int = 3,
    base: float = 0.5,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    scope: str = _GRAPH_DEFAULT_SCOPE,
    http_post: Optional[Callable[..., Any]] = None,
    timeout: float = 10.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Échange OBO avec backoff exponentiel borné, réessayé sur erreurs transitoires.

    Enveloppe `acquire_obo_graph_token` (inchangée) : ne réessaie que les erreurs
    transitoires (httpx timeout/connexion + HTTP 429/503/504), jusqu'à `attempts`
    fois. Sur 429, l'en-tête Graph `Retry-After` est honoré comme délai ; sinon
    backoff plein-jitter `random.uniform(0, base * 2**i)`. Les erreurs non
    transitoires (4xx d'auth, `ValueError` de config) remontent immédiatement.
    À l'épuisement, lève la dernière erreur transitoire (l'appelant la mappe en
    HTTP 503, pas 502). `sleep` est injectable pour des tests rapides.
    """
    last_exc: Optional[BaseException] = None
    for i in range(attempts):
        try:
            return acquire_obo_graph_token(
                user_assertion,
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
                http_post=http_post,
                timeout=timeout,
            )
        except Exception as exc:  # narrow classification below; OBO hot path
            if not _is_transient(exc) or i == attempts - 1:
                raise
            last_exc = exc
            retry_after = _retry_after_seconds(exc)
            delay = retry_after if retry_after is not None else random.uniform(0, base * (2 ** i))
            sleep(delay)
    # Loop only exits via return or raise; this satisfies the type checker for the
    # theoretically-unreachable attempts<=0 case.
    assert last_exc is not None
    raise last_exc
