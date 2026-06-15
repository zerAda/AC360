"""jobs_ttl.py — Purge âgée des artefacts JOBS_BASE_DIR (RGP-03, application locale).

Les règles de cycle de vie du Storage Azure (``managementPolicies``) ne peuvent PAS
atteindre le système de fichiers LOCAL de la VM Functions où atterrissent les
documents téléchargés, l'OCR temporaire et les brouillons FIC (``JOBS_BASE_DIR``).
Ce module fournit le contrôle d'application RGP-03 côté FS local : une fonction PURE
et testable qui supprime UNIQUEMENT les entrées plus vieilles que la fenêtre de
rétention (jamais l'arbre entier — ce n'est PAS le wipe destructif
``scripts/cleanup_local_artifacts.ps1``, qui détruirait des audits en cours).

Conçue pour l'injection de dépendances (``now`` / ``remover``) afin d'être testée
sans horloge murale ni suppression réelle.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import Callable, Optional

__all__ = ["prune_jobs_dir"]


def _default_remove(path: str) -> None:
    """Suppression best-effort : rmtree pour un dossier, remove pour un fichier."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def prune_jobs_dir(
    base_dir: str,
    *,
    max_age_seconds: int,
    now: Optional[float] = None,
    remover: Optional[Callable[[str], None]] = None,
) -> list[str]:
    """Supprime les entrées de ``base_dir`` dont le mtime précède ``now - max_age_seconds``.

    Args:
        base_dir: répertoire racine des artefacts (JOBS_BASE_DIR).
        max_age_seconds: fenêtre de rétention en secondes ; toute entrée plus
            ancienne que ``now - max_age_seconds`` est supprimée.
        now: horodatage de référence (epoch secondes) ; ``time.time()`` par défaut
            (injectable pour les tests).
        remover: callable de suppression (injectable) ; ``_default_remove`` par défaut.

    Returns:
        La liste des chemins supprimés (best-effort).

    Tolérances (best-effort, ne lève jamais) :
        - ``base_dir`` inexistant -> retourne ``[]``.
        - une erreur ``OSError`` sur une entrée (getmtime/remover) n'interrompt pas
          le balayage des autres entrées.
    """
    ref = time.time() if now is None else now
    rm = _default_remove if remover is None else remover
    cutoff = ref - max_age_seconds
    deleted: list[str] = []

    if not os.path.isdir(base_dir):
        return deleted

    for entry in os.listdir(base_dir):
        path = os.path.join(base_dir, entry)
        try:
            if os.path.getmtime(path) < cutoff:
                rm(path)
                deleted.append(path)
        except OSError:
            # best-effort : on continue avec les autres entrées (RGP-03).
            continue

    return deleted
