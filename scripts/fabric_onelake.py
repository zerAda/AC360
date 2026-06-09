"""fabric_onelake.py — Accès aux données de référence GEREP via Microsoft Fabric
OneLake (tables Delta), SANS ODBC.

Pur Python (deltalake + azure-identity) : fonctionne sur Azure Functions
Consumption via l'identité managée, et en local via Azure CLI.

Table de référence : ``tbl_super_product_client_api_gold`` du Lakehouse Gold —
elle expose des noms client LISIBLES + SIRET (la table client agrégée
``tbl_full_client_gold`` est, elle, pseudonymisée/hashée pour le RGPD).

Le rapprochement privilégie le SIRET (clé exacte) puis le nom (fuzzy >= 85).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

_WS = os.getenv("FABRIC_WORKSPACE_ID")
_LH = os.getenv("FABRIC_GOLD_LAKEHOUSE_ID")
_TABLE = os.getenv("FABRIC_CLIENT_TABLE", "tbl_super_product_client_api_gold")
_NAME_MATCH_MIN = 85


def _token() -> str:
    """Jeton OneLake/ADLS : identité managée (Function) ou az CLI (local)."""
    from azure.identity import DefaultAzureCredential
    cred = DefaultAzureCredential()
    return cred.get_token("https://storage.azure.com/.default").token


def _read_table(table: str, columns: Optional[List[str]] = None):
    import pandas as pd  # noqa: F401  (deltalake -> pandas)
    from deltalake import DeltaTable
    if not _WS or not _LH:
        raise RuntimeError("FABRIC_WORKSPACE_ID / FABRIC_GOLD_LAKEHOUSE_ID non configurés.")
    url = f"abfss://{_WS}@onelake.dfs.fabric.microsoft.com/{_LH}/Tables/dbo/{table}"
    dt = DeltaTable(url, storage_options={"bearer_token": _token(), "use_fabric_endpoint": "true"})
    return dt.to_pandas(columns=columns)


def normalize_siret(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == 14 else ""


def _row_to_ref(row, df, numcli) -> Dict[str, Any]:
    produits = sorted(
        str(p) for p in df[df["numcli"] == numcli]["product_name"].dropna().unique()
    )
    return {
        "numcli": str(numcli),
        "nom_client": str(row["client_name"]),
        "siret": normalize_siret(row["siret"]),
        "produits": produits,
    }


def fetch_client_reference(client_name: Optional[str] = None,
                           siret: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retourne la meilleure correspondance client (dict) depuis Fabric, ou None.

    Le dict est consommable par fabric_audit_engine.audit (clé ``nom_client``) et
    porte en plus ``siret``, ``numcli`` et la liste ``produits`` souscrits.
    """
    df = _read_table(_TABLE, columns=["numcli", "client_name", "siret", "product_name"])

    # 1) SIRET exact (clé la plus fiable).
    sd = normalize_siret(siret)
    if sd:
        match = df[df["siret"].map(normalize_siret) == sd]
        if len(match):
            r = match.iloc[0]
            return _row_to_ref(r, df, r["numcli"])

    # 2) Nom fuzzy.
    if client_name:
        from fabric_audit_engine import normalize_name, _name_score
        target = normalize_name(client_name)
        best = None
        best_score = 0
        # Déduplique sur le couple (numcli, client_name) pour limiter le travail.
        seen = df.drop_duplicates(subset=["numcli", "client_name"])
        for _, row in seen.iterrows():
            score = _name_score(target, normalize_name(row["client_name"]))
            if score > best_score:
                best_score = score
                best = row
        if best is not None and best_score >= _NAME_MATCH_MIN:
            return _row_to_ref(best, df, best["numcli"])

    return None
