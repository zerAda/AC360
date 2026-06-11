"""sharepoint.py — Téléchargement sécurisé d'un document SharePoint via Microsoft Graph.

Conçu pour être TESTABLE sans tenant réel : le client HTTP (`http_get`) et le
jeton (`access_token`) sont injectés. Aucune lecture de données réelle ici ; la
fonction écrit le binaire reçu dans un répertoire de job confiné.

Contrôles de sécurité :
  * allowlist d'extensions ;
  * plafond de taille (métadonnée Graph + taille réelle téléchargée) ;
  * nom de fichier assaini (anti path-traversal) ;
  * confinement du chemin de destination sous `dest_dir` (commonpath).
"""
from __future__ import annotations

import os
import re
from typing import Callable, Iterable, Optional

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_ALLOWED_EXT = frozenset({".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".tif"})
DEFAULT_MAX_BYTES = 25 * 1024 * 1024  # 25 Mo


def _safe_filename(name: Optional[str], fallback: str) -> str:
    """Réduit à un nom de fichier sûr : basename, sans séparateurs ni '..'."""
    base = os.path.basename(str(name or "")).strip()
    base = base.replace("\x00", "")
    # Conserver alphanum, espace, point, tiret, underscore ; remplacer le reste.
    base = re.sub(r"[^A-Za-z0-9 ._-]", "_", base)
    base = base.lstrip(".") or fallback  # éviter les fichiers cachés / vides
    if base in (".", "..", ""):
        base = fallback
    return base


def download_document(
    *,
    item_id: str,
    drive_id: str,
    dest_dir: str,
    access_token: str,
    http_get: Optional[Callable] = None,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    """Télécharge un item SharePoint via Graph et retourne le chemin local écrit.

    Lève ValueError sur extension non autorisée, taille excessive ou chemin non
    confiné ; propage les erreurs HTTP du client injecté.
    """
    if not item_id or not drive_id:
        raise ValueError("item_id et drive_id sont obligatoires.")

    import httpx  # import paresseux : pas requis pour les tests qui injectent http_get

    get = http_get or httpx.get
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Métadonnées (nom, taille, URL de téléchargement pré-authentifiée).
    meta_resp = get(f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}", headers=headers, timeout=15.0)
    meta_resp.raise_for_status()
    info = meta_resp.json() or {}

    allowed = frozenset(e.lower() for e in allowed_ext)
    filename = _safe_filename(info.get("name"), fallback=f"{_safe_filename(item_id, 'document')}.bin")
    ext = os.path.splitext(filename)[1].lower()
    if allowed and ext not in allowed:
        raise ValueError(f"Extension non autorisée : {ext or '(aucune)'}")

    declared_size = int(info.get("size") or 0)
    if declared_size and declared_size > max_bytes:
        raise ValueError(f"Document trop volumineux ({declared_size} octets > {max_bytes}).")

    # 2. Contenu : l'URL @microsoft.graph.downloadUrl est pré-signée (sans header auth).
    download_url = info.get("@microsoft.graph.downloadUrl")
    if download_url:
        content_resp = get(download_url, timeout=60.0)
    else:
        content_resp = get(
            f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content",
            headers=headers, timeout=60.0,
        )
    content_resp.raise_for_status()
    # La borne anti-mémoire AMONT est le contrôle de taille des métadonnées (avant
    # ce GET). Ici, repli quand la taille déclarée par Graph était absente/0 : on
    # rejette via Content-Length avant l'écriture disque et l'appel OCR. (Une borne
    # mémoire STRICTE imposerait un téléchargement en streaming — le client HTTP est
    # injecté/bufferisé ici ; cf. résiduel.)
    try:
        declared_len = int((getattr(content_resp, "headers", None) or {}).get("Content-Length", 0) or 0)
    except (ValueError, TypeError):
        declared_len = 0
    if declared_len and declared_len > max_bytes:
        raise ValueError(f"Document trop volumineux (Content-Length {declared_len} > {max_bytes}).")
    data = content_resp.content
    if data is not None and len(data) > max_bytes:
        raise ValueError(f"Contenu téléchargé trop volumineux ({len(data)} octets > {max_bytes}).")

    # 3. Écriture confinée sous dest_dir.
    base = os.path.abspath(dest_dir)
    os.makedirs(base, exist_ok=True)
    dest = os.path.abspath(os.path.join(base, filename))
    if os.path.commonpath([dest, base]) != base:
        raise ValueError("Chemin de destination hors du répertoire autorisé.")

    with open(dest, "wb") as f:
        f.write(data or b"")
    return dest
