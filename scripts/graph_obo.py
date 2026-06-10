"""graph_obo.py — OAuth2 On-Behalf-Of exchange.

Échange le token d'accès de l'utilisateur (audience = cette API) contre un token
Microsoft Graph DÉLÉGUÉ qui agit AU NOM de l'utilisateur. Le téléchargement
SharePoint en aval honore alors les permissions propres de l'utilisateur
(superposition RBAC) : pas d'accès → refus Graph 403, l'audit ne démarre pas.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

_OBO_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


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
