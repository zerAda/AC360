"""fabric_onelake.py — Accès aux données de référence GEREP via Microsoft Fabric
OneLake (tables Delta), SANS ODBC, conçu pour être EFFICACE et ROBUSTE.

Pur Python (deltalake + azure-identity) : fonctionne sur Azure Functions
Consumption via l'identité managée, et en local via Azure CLI.

Stratégie de rapprochement (par ordre de fiabilité) :
  1. SIRET exact  -> index en mémoire, O(1). Clé d'entreprise fiable.
  2. Nom (fuzzy)  -> repli uniquement, sur une liste pré-normalisée.

Performance : la table de référence est chargée UNE fois par instance puis mise
en cache (TTL configurable). Les requêtes d'audit n'effectuent plus de lecture
OneLake ni de boucle O(n) à chaque appel — juste des lookups indexés.

Table de référence : ``tbl_super_product_client_api_gold`` (noms client LISIBLES
+ SIRET ; la table client agrégée ``tbl_full_client_gold`` est pseudonymisée RGPD).
"""
from __future__ import annotations

import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

_WS = os.getenv("FABRIC_WORKSPACE_ID")
_LH = os.getenv("FABRIC_GOLD_LAKEHOUSE_ID")
_TABLE = os.getenv("FABRIC_CLIENT_TABLE", "tbl_super_product_client_api_gold")
_CACHE_TTL = int(os.getenv("FABRIC_CACHE_TTL_SECONDS", "3600"))
_NAME_MATCH_MIN = 85

_SIRET_RE = re.compile(r"\D")
_lock = threading.Lock()
# Cache d'instance : index SIRET + lignes pré-normalisées pour le fuzzy.
_cache: Dict[str, Any] = {"ts": 0.0, "by_siret": {}, "by_numcli": {}, "names": []}


def normalize_siret(value: Any) -> str:
    digits = _SIRET_RE.sub("", str(value or ""))
    return digits if len(digits) == 14 else ""


def _token() -> str:
    """Jeton OneLake/ADLS : identité managée (Function) ou az CLI (local)."""
    from azure.identity import DefaultAzureCredential
    return DefaultAzureCredential().get_token("https://storage.azure.com/.default").token


def _read_table(table: str, columns: Optional[List[str]] = None):
    from deltalake import DeltaTable
    if not _WS or not _LH:
        raise RuntimeError("FABRIC_WORKSPACE_ID / FABRIC_GOLD_LAKEHOUSE_ID non configurés.")
    url = f"abfss://{_WS}@onelake.dfs.fabric.microsoft.com/{_LH}/Tables/dbo/{table}"
    dt = DeltaTable(url, storage_options={"bearer_token": _token(), "use_fabric_endpoint": "true"})
    return dt.to_pandas(columns=columns)


def _build_indexes() -> None:
    """Charge la table de référence et construit les index (SIRET, produits par
    numcli, liste de noms normalisés). Coûteux -> exécuté une fois par TTL."""
    from fabric_audit_engine import normalize_name

    df = _read_table(_TABLE, columns=["numcli", "client_name", "siret", "product_name"])

    by_siret: Dict[str, Dict[str, Any]] = {}
    by_numcli: Dict[str, Dict[str, Any]] = {}
    names: List[Tuple[str, str]] = []  # (nom_normalisé, numcli)

    # Produits agrégés par client (une seule passe).
    produits: Dict[str, set] = {}
    for row in df.itertuples(index=False):
        numcli = str(row.numcli)
        if row.product_name:
            produits.setdefault(numcli, set()).add(str(row.product_name))

    seen = set()
    for row in df.itertuples(index=False):
        numcli = str(row.numcli)
        if numcli in seen:
            continue
        seen.add(numcli)
        ref = {
            "numcli": numcli,
            "nom_client": str(row.client_name) if row.client_name is not None else None,
            "siret": normalize_siret(row.siret),
            "produits": sorted(produits.get(numcli, set())),
        }
        by_numcli[numcli] = ref
        if ref["siret"]:
            by_siret[ref["siret"]] = ref
        if ref["nom_client"]:
            names.append((normalize_name(ref["nom_client"]), numcli))

    _cache.update(ts=time.monotonic(), by_siret=by_siret, by_numcli=by_numcli, names=names)


def _ensure_cache(force: bool = False) -> None:
    with _lock:
        fresh = _cache["by_numcli"] and (time.monotonic() - _cache["ts"]) < _CACHE_TTL
        if not force and fresh:
            return
        _build_indexes()


def fetch_client_reference(client_name: Optional[str] = None,
                           siret: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retourne la meilleure correspondance client (dict) depuis Fabric, ou None.

    Priorité : SIRET exact (O(1)) puis nom fuzzy (>= 85). Le dict porte
    ``nom_client`` (consommé par l'audit), ``siret``, ``numcli`` et ``produits``.
    """
    _ensure_cache()

    # 1) SIRET exact — clé fiable, lookup indexé.
    sd = normalize_siret(siret)
    if sd:
        hit = _cache["by_siret"].get(sd)
        if hit:
            return dict(hit)

    # 2) Repli nom fuzzy — sur la liste pré-normalisée (pas de re-lecture OneLake).
    if client_name:
        from fabric_audit_engine import normalize_name, _name_score
        target = normalize_name(client_name)
        best_numcli = None
        best_score = 0
        for norm_name, numcli in _cache["names"]:
            score = _name_score(target, norm_name)
            if score > best_score:
                best_score = score
                best_numcli = numcli
        if best_numcli is not None and best_score >= _NAME_MATCH_MIN:
            return dict(_cache["by_numcli"][best_numcli])

    return None
