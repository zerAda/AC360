"""config.py — Configuration centralisée AC360 (import-safe, fail-fast au runtime).

L'import de ce module n'échoue JAMAIS (pytest peut le collecter). La validation
fail-fast des variables critiques se fait via ``load_config(require_auth=True)``,
appelée au démarrage de l'application.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional


class ConfigurationError(RuntimeError):
    """Variable d'environnement critique manquante."""


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@dataclass(frozen=True)
class AppConfig:
    tenant_id: Optional[str]
    client_id: Optional[str]
    jobs_base_dir: str
    allowed_extensions: FrozenSet[str]
    required_scopes: List[str] = field(default_factory=list)
    required_roles: List[str] = field(default_factory=list)
    jwks_timeout: float = 10.0

    @property
    def jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"


def _split_csv(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_config(require_auth: bool = False) -> AppConfig:
    """Charge la configuration. Si ``require_auth`` : fail-fast sur les variables
    d'authentification obligatoires (TENANT_ID, CLIENT_ID)."""
    _load_env()

    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")

    if require_auth:
        missing = [name for name, val in (("TENANT_ID", tenant_id), ("CLIENT_ID", client_id)) if not val]
        if missing:
            raise ConfigurationError(
                "Variables d'environnement obligatoires manquantes : "
                + ", ".join(missing)
                + ". Définissez-les avant de lancer l'application."
            )

    jobs_base_dir = os.path.abspath(os.getenv("JOBS_BASE_DIR", "jobs"))
    allowed = os.getenv("ALLOWED_EXTENSIONS")
    allowed_set = (
        frozenset(e if e.startswith(".") else f".{e}" for e in _split_csv(allowed))
        if allowed
        else frozenset({".pdf", ".docx", ".xlsx", ".txt"})
    )

    # Autorisation : scopes/roles attendus dans le token (séparés par des virgules)
    required_scopes = _split_csv(os.getenv("REQUIRED_SCOPES", "Audit.Trigger"))
    required_roles = _split_csv(os.getenv("REQUIRED_ROLES", ""))

    return AppConfig(
        tenant_id=tenant_id,
        client_id=client_id,
        jobs_base_dir=jobs_base_dir,
        allowed_extensions=allowed_set,
        required_scopes=required_scopes,
        required_roles=required_roles,
        jwks_timeout=float(os.getenv("JWKS_TIMEOUT", "10")),
    )
