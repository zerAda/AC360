"""
safe_logger.py — Neutralisation des messages avant journalisation.

Les sorties de sous-processus (stderr/stdout du pipeline PowerShell, traces
Python remontées par les étapes OCR/Audit/FIC, etc.) peuvent contenir des
chemins de fichiers, des extraits de documents clients ou des secrets.
Conformément à la Baseline Sécurité (cf. docs/security/SECURITY_BASELINE.md
§6.1 et §7), aucune donnée client ni aucun secret ne doit être persisté en
clair dans les journaux : base SQLite (audit_logs.details), console ou
Application Insights.

`redact()` neutralise une chaîne AVANT journalisation :
- suppression des séquences d'échappement ANSI ;
- masquage des secrets évidents (JWT, jetons Bearer, URL webhook Teams,
  couples clé=valeur sensibles : password / secret / api_key / token /
  connection string / AZURE_OCR_KEY...) ;
- masquage des PII évidentes (e-mails, IBAN, longues séquences de chiffres
  type NIR / carte bancaire / numéro de compte) ;
- suppression des caractères de contrôle, dont CR/LF (anti log-injection :
  empêche la forge de fausses lignes de journal) ;
- troncature à une longueur maximale bornée.

Les motifs de secrets s'alignent sur ceux de .gitleaks.toml.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, Mapping


logger = logging.getLogger("AC360")
logger.setLevel(logging.INFO)


def log_security(level: str, message: str, data: dict = None):
    """
    Journalise un message de sécurité de manière neutre et sécurisée.
    """
    safe_msg = redact(message)
    extra_info = f" | {data}" if data else ""
    full_msg = f"{safe_msg}{extra_info}"

    if level == "INFO":
        logger.info(full_msg)
    elif level == "WARNING":
        logger.warning(full_msg)
    elif level == "ERROR":
        logger.error(full_msg)
    else:
        logger.debug(full_msg)


__all__ = ["redact", "redact_mapping", "MAX_LEN", "logger", "log_security"]

# Longueur maximale conservée pour un message journalisé (extrait borné).
MAX_LEN = 800

_MASK_SECRET = "[SECRET_MASQUÉ]"
_MASK_EMAIL = "[EMAIL_MASQUÉ]"
_MASK_PII = "[PII_MASQUÉE]"

# Séquences d'échappement ANSI (couleurs, déplacements de curseur...).
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/\-]{12,}=*")
_WEBHOOK_RE = re.compile(r"https://[^\s/]*\.webhook\.office\.com/\S+")
_KV_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|client[_\-]?secret|api[_\-]?key|apikey|"
    r"access[_\-]?token|token|account[_\-]?key|accountkey|"
    r"connection[_\-]?string|conn[_\-]?str|azure_ocr_key)"
    r"(\s*[:=]\s*)"
    r"['\"]?[^\s'\";,]{4,}"
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_LONG_DIGITS_RE = re.compile(r"\b\d(?:[ \-]?\d){12,}\b")

# Caractères de contrôle C0/C1 + DEL (dont \t, \r, \n) -> remplacés par espace.
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MULTISPACE_RE = re.compile(r"\s{2,}")


def redact(message, max_len=MAX_LEN):
    if message is None:
        return ""
    if not isinstance(message, str):
        message = str(message)

    # 1. Retrait des séquences d'échappement ANSI (avant suppression des
    #    contrôles, sinon le préfixe \x1b disparaît et le texte "[31m" reste).
    text = _ANSI_RE.sub("", message)

    # 2. Masquage des secrets (motifs les plus spécifiques d'abord).
    text = _JWT_RE.sub(_MASK_SECRET, text)
    text = _BEARER_RE.sub("Bearer " + _MASK_SECRET, text)
    text = _WEBHOOK_RE.sub(_MASK_SECRET, text)
    text = _KV_SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + _MASK_SECRET, text)

    # 3. Masquage des PII (IBAN avant la séquence de chiffres générique).
    text = _EMAIL_RE.sub(_MASK_EMAIL, text)
    text = _IBAN_RE.sub(_MASK_PII, text)
    text = _LONG_DIGITS_RE.sub(_MASK_PII, text)

    # 4. Neutralisation des caractères de contrôle (CR/LF inclus) -> espace.
    text = _CTRL_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text).strip()

    # 5. Troncature bornée.
    if len(text) > max_len:
        total = len(text)
        text = text[:max_len].rstrip() + f"... [tronqué, {total} caractères au total]"

    return text


def redact_mapping(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    """Neutralise les VALEURS d'un dict (dimensions de télémétrie, paramètres
    d'un message detail) en réutilisant la SEULE surface auditée `redact()`.

    Chaque valeur de type `str` est passée par `redact()` (mêmes motifs/masques
    que pour les journaux — aucun nouveau regex n'est introduit ici). Les valeurs
    non-textuelles (int, None, bool, etc.) sont conservées telles quelles. Le
    dict d'entrée n'est pas muté : un nouveau dict est retourné.

    Seam consommée par le middleware télémétrie d'api_server (Plan 01-06) et par
    l'émission audit-trail (Plan 01-04).
    """
    return {
        key: (redact(value) if isinstance(value, str) else value)
        for key, value in mapping.items()
    }
