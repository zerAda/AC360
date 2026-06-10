"""
cost_tracker.py — Modèle de coût paramétrable AC360 (P0-07).

RÈGLE ABSOLUE (cf. mission) :
  - Ne jamais inventer de prix.
  - Ne jamais hardcoder une grille tarifaire non vérifiée.
  - Les prix réels Microsoft (Copilot Studio, OCR, Fabric...) ne sont PAS dans le
    repo → la grille par défaut est VIDE (0.0) et marquée « À VALIDER ».
  - Les tarifs réels sont injectés via l'environnement (AC360_RATE_CARD, JSON),
    résolvable depuis Key Vault / app settings, sans redéploiement.

Chaque coût produit porte un `cost_source` :
  REEL_MESURE  — mesuré sur facture réelle (jamais par défaut ici)
  ESTIME       — estimation à partir d'un tarif fourni
  PARAMETRABLE — tarif fourni via configuration
  A_VALIDER    — aucun tarif fourni → montant 0.0, à valider en environnement réel
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from feature_flags import hash_id

# Postes de coût connus. Valeur par défaut 0.0 = AUCUN prix inventé.
COST_CENTERS = (
    "copilot_studio_message",
    "copilot_studio_action",
    "ocr_document_intelligence",
    "fabric_onelake",
    "backend_api",
    "storage",
    "application_insights",
    "power_automate",
    "premium_connector",
)
DEFAULT_RATE_CARD: Dict[str, float] = {cc: 0.0 for cc in COST_CENTERS}

_RATE_CARD_ENV = "AC360_RATE_CARD"
_BUDGET_ENV = "AC360_BUDGET_EUR"
_BUDGET_WARN_PCT_ENV = "AC360_BUDGET_WARN_PCT"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_rate_card() -> Dict[str, float]:
    """
    Grille tarifaire effective = défaut (0.0) surchargée par AC360_RATE_CARD
    (JSON {cost_center: eur_par_unite}). Une valeur invalide est ignorée
    proprement (jamais d'inventer un prix).
    """
    card = dict(DEFAULT_RATE_CARD)
    raw = os.environ.get(_RATE_CARD_ENV)
    if raw:
        try:
            override = json.loads(raw)
            for cc, val in override.items():
                if cc in card and isinstance(val, (int, float)) and val >= 0:
                    card[cc] = float(val)
        except (ValueError, TypeError):
            pass
    return card


def get_unit_cost(cost_center: str) -> float:
    return load_rate_card().get(cost_center, 0.0)


def estimate_cost(
    cost_center: str,
    quantity: float,
    *,
    unit: str = "request",
    environment: Optional[str] = None,
    commercial_id: Optional[str] = None,
    team_id: Optional[str] = None,
    client_id: Optional[str] = None,
    use_case: Optional[str] = None,
    event_id: Optional[str] = None,
    timestamp_utc: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estime le coût d'une quantité consommée sur un poste. Retourne un cost_event
    conforme au schéma. Si aucun tarif n'est configuré, le montant est 0.0 et
    cost_source = A_VALIDER (jamais de prix inventé).
    """
    if cost_center not in COST_CENTERS:
        raise ValueError(f"cost_center inconnu : {cost_center}")
    if quantity < 0:
        raise ValueError("quantity ne peut pas être négative")

    unit_cost = get_unit_cost(cost_center)
    amount = round(unit_cost * float(quantity), 6)
    source = "PARAMETRABLE" if unit_cost > 0 else "A_VALIDER"

    return {
        "event_id": event_id or str(uuid.uuid4()),
        "timestamp_utc": timestamp_utc or _now_iso(),
        "environment": environment or os.environ.get("AC360_ENVIRONMENT", "dev"),
        "cost_center": cost_center,
        "quantity": float(quantity),
        "unit": unit,
        "unit_cost_eur": unit_cost,
        "estimated_cost_eur": amount,
        "cost_source": source,
        "commercial_id_hash": hash_id(commercial_id) if commercial_id else None,
        "team_id": team_id,
        "client_id_hash": hash_id(client_id) if client_id else None,
        "use_case": use_case,
    }


def _budget_eur() -> Optional[float]:
    raw = os.environ.get(_BUDGET_ENV)
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _warn_pct() -> float:
    raw = os.environ.get(_BUDGET_WARN_PCT_ENV, "80")
    try:
        return float(raw)
    except ValueError:
        return 80.0


def check_budget(
    spent_eur: float,
    budget_eur: Optional[float] = None,
    warn_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Évalue un budget. NE bloque RIEN (no block by default) : renvoie seulement un
    niveau d'alerte que la couche admin peut décider d'actionner (kill-switch).

    Niveaux : ok | warning | exceeded. Si aucun budget n'est configuré → unknown.
    """
    budget = budget_eur if budget_eur is not None else _budget_eur()
    pct_threshold = warn_pct if warn_pct is not None else _warn_pct()

    if budget is None or budget <= 0:
        return {
            "level": "unknown",
            "spent_eur": round(spent_eur, 4),
            "budget_eur": None,
            "ratio_pct": None,
        }

    ratio = (spent_eur / budget) * 100.0
    if ratio >= 100.0:
        level = "exceeded"
    elif ratio >= pct_threshold:
        level = "warning"
    else:
        level = "ok"
    return {
        "level": level,
        "spent_eur": round(spent_eur, 4),
        "budget_eur": round(budget, 4),
        "ratio_pct": round(ratio, 2),
        "warn_pct": pct_threshold,
    }
