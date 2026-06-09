"""Test du rate-limiting par utilisateur (anti abus / DoS applicatif)."""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import api_server  # noqa: E402


@pytest.mark.asyncio
async def test_rate_limit_enforced_per_user():
    api_server._rate_limit_store.clear()
    upn = "ratelimit@gerep.fr"

    # Les N premières requêtes passent.
    for _ in range(api_server._RATE_LIMIT_MAX):
        await api_server._check_rate_limit(upn)

    # La suivante est refusée (429).
    with pytest.raises(HTTPException) as exc:
        await api_server._check_rate_limit(upn)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_isolated_between_users():
    api_server._rate_limit_store.clear()
    for _ in range(api_server._RATE_LIMIT_MAX):
        await api_server._check_rate_limit("userA@gerep.fr")
    # Un autre utilisateur n'est pas impacté par le quota du premier.
    await api_server._check_rate_limit("userB@gerep.fr")
