"""security — Authentification par clé API + validation d'entrées (onix-actions).

- Clé API obligatoire via header `X-API-Key` (ou `Authorization: Bearer <clé>`),
  comparée en temps constant. Aucune clé en dur : lue dans `ONIX_ACTIONS_API_KEY`.
- Garde-fous : taille de fichier, extensions autorisées, anti path-traversal.
- Notion d'« admin » : un porteur de la clé API est administrateur du service
  (le périmètre réseau est déjà interne, sans port hôte). Optionnellement, une
  clé admin distincte (`ONIX_ACTIONS_ADMIN_KEY`) peut restreindre /admin/*.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, status

# Limites d'entrée (configurables).
MAX_UPLOAD_BYTES = int(os.environ.get("ONIX_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
ALLOWED_UPLOAD_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp")


def _expected_key() -> str:
    return os.environ.get("ONIX_ACTIONS_API_KEY", "").strip()


def _expected_admin_key() -> Optional[str]:
    k = os.environ.get("ONIX_ACTIONS_ADMIN_KEY", "").strip()
    return k or None


def _constant_eq(a: str, b: str) -> bool:
    # Comparaison en temps constant (anti timing) sur des digests de taille fixe.
    da = hashlib.sha256((a or "").encode()).digest()
    db = hashlib.sha256((b or "").encode()).digest()
    return hmac.compare_digest(da, db)


def _extract_key(x_api_key: Optional[str], authorization: Optional[str]) -> str:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Dépendance FastAPI : exige une clé API valide. Retourne un identifiant
    d'appelant opaque (utilisé seulement pour le hashage d'usage)."""
    expected = _expected_key()
    if not expected:
        # Refus de fonctionner sans clé : pas d'ouverture par défaut.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service non configuré (ONIX_ACTIONS_API_KEY absente).",
        )
    provided = _extract_key(x_api_key, authorization)
    if not provided or not _constant_eq(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide ou absente.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return "api-caller"


def require_admin(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
) -> str:
    """Dépendance pour /admin/* : exige la clé API ; si une clé admin distincte
    est définie, elle est requise en plus (header X-Admin-Key)."""
    require_api_key(x_api_key, authorization)
    admin_expected = _expected_admin_key()
    if admin_expected is not None:
        if not x_admin_key or not _constant_eq(x_admin_key.strip(), admin_expected):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droit administrateur requis (X-Admin-Key).",
            )
    return "admin"


def validate_upload(filename: str, size: int) -> None:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(status_code=400, detail=f"Extension non autorisée : {ext or '(aucune)'}")
    if size <= 0:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux (> {MAX_UPLOAD_BYTES // (1024*1024)} Mo).",
        )
