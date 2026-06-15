"""llm — Assistance LLM locale via Ollama (onix-actions).

« En mieux » qu'AC360 : option d'extraction des champs canoniques depuis un texte
brut par un LLM LOCAL (Ollama, http://ollama:11434), sans aucun appel cloud.

Dégrade proprement : si Ollama est injoignable ou répond mal, on lève une erreur
claire que l'endpoint /audit convertit en repli (extraction heuristique).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

import httpx

CANONICAL_FIELDS = (
    "nom_client",
    "plafond_hospitalisation",
    "date_effet",
    "numero_contrat",
    "motif_operation",
)

_PROMPT = (
    "Tu es un extracteur de données. À partir du TEXTE, renvoie UNIQUEMENT un objet "
    "JSON valide (aucun texte autour) avec EXACTEMENT ces clés : "
    + ", ".join(CANONICAL_FIELDS)
    + ". Mets null si une information est absente. Ne réécris pas les valeurs, "
    "recopie-les telles quelles.\n\nTEXTE:\n{texte}\n\nJSON:"
)


def ollama_base_url() -> str:
    return os.environ.get("ONIX_OLLAMA_URL", "http://ollama:11434").rstrip("/")


def ollama_model() -> str:
    return os.environ.get("ONIX_LLM_MODEL", "llama3.2:3b")


def _extract_json(raw: str) -> Optional[dict]:
    raw = (raw or "").strip()
    # Retire d'éventuels fences ```json ... ```
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def extract_fields_llm(text: str, *, timeout: float = 60.0) -> Dict[str, Any]:
    """Extrait les champs canoniques d'un texte via Ollama. Lève en cas d'échec."""
    if not (text or "").strip():
        raise ValueError("Texte vide.")
    url = f"{ollama_base_url()}/api/generate"
    payload = {
        "model": ollama_model(),
        "prompt": _PROMPT.format(texte=text[:8000]),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    try:
        resp = httpx.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:  # réseau / Ollama absent
        raise RuntimeError(f"Ollama indisponible: {e}") from e

    data = resp.json()
    parsed = _extract_json(data.get("response", ""))
    if not isinstance(parsed, dict):
        raise RuntimeError("Réponse LLM non exploitable (JSON invalide).")
    # On ne garde que les clés canoniques connues.
    return {k: parsed.get(k) for k in CANONICAL_FIELDS if parsed.get(k) not in (None, "")}
