"""Tests du rapprochement Fabric/OneLake : SIRET prioritaire, fuzzy en repli,
cache (une seule lecture par TTL)."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import fabric_onelake as fo  # noqa: E402


def _fake_df():
    return pd.DataFrame([
        {"numcli": "100", "client_name": "GEREP SA", "siret": "39000000000001", "product_name": "Sante"},
        {"numcli": "100", "client_name": "GEREP SA", "siret": "39000000000001", "product_name": "Prevoyance"},
        {"numcli": "200", "client_name": "BETA CORP", "siret": "39000000000002", "product_name": "Sante"},
    ])


@pytest.fixture
def patched(monkeypatch):
    calls = {"reads": 0}

    def fake_read(table, columns=None):
        calls["reads"] += 1
        return _fake_df()

    monkeypatch.setattr(fo, "_read_table", fake_read)
    fo._cache.update(ts=0.0, by_siret={}, by_numcli={}, names=[])  # reset cache
    return calls


def test_siret_exact_match_and_products(patched):
    r = fo.fetch_client_reference(siret="3900 0000 0000 01")  # 14 chiffres, espaces ignorés
    assert r["numcli"] == "100"
    assert r["nom_client"] == "GEREP SA"
    assert set(r["produits"]) == {"Sante", "Prevoyance"}


def test_cache_reads_table_once(patched):
    fo.fetch_client_reference(siret="39000000000001")
    fo.fetch_client_reference(siret="39000000000002")
    fo.fetch_client_reference(client_name="GEREP SA")
    assert patched["reads"] == 1  # une seule lecture OneLake (cache)


def test_name_fuzzy_fallback(patched):
    r = fo.fetch_client_reference(client_name="GEREP  SA")
    assert r is not None and r["numcli"] == "100"


def test_siret_takes_priority_over_name(patched):
    # SIRET de BETA mais nom de GEREP -> le SIRET gagne.
    r = fo.fetch_client_reference(client_name="GEREP SA", siret="39000000000002")
    assert r["numcli"] == "200"


def test_no_match_returns_none(patched):
    assert fo.fetch_client_reference(client_name="ENTREPRISE INCONNUE",
                                     siret="00000000000000") is None
