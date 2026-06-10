"""Tests seuils de budget (P0-07) : alerte sans blocage automatique."""
import pytest
import cost_tracker as ct


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for v in ("AC360_BUDGET_EUR", "AC360_BUDGET_WARN_PCT"):
        monkeypatch.delenv(v, raising=False)
    yield


def test_unknown_when_no_budget():
    assert ct.check_budget(100.0)["level"] == "unknown"


def test_ok_below_warning():
    r = ct.check_budget(50.0, budget_eur=100.0, warn_pct=80.0)
    assert r["level"] == "ok"
    assert r["ratio_pct"] == 50.0


def test_warning_at_threshold():
    r = ct.check_budget(85.0, budget_eur=100.0, warn_pct=80.0)
    assert r["level"] == "warning"


def test_exceeded_over_budget():
    r = ct.check_budget(120.0, budget_eur=100.0)
    assert r["level"] == "exceeded"
    assert r["ratio_pct"] == 120.0


def test_budget_from_env(monkeypatch):
    monkeypatch.setenv("AC360_BUDGET_EUR", "200")
    monkeypatch.setenv("AC360_BUDGET_WARN_PCT", "75")
    r = ct.check_budget(160.0)
    assert r["level"] == "warning"  # 80% >= 75%


def test_check_budget_never_blocks():
    # check_budget renvoie un NIVEAU, il ne coupe rien (no auto-block).
    r = ct.check_budget(99999.0, budget_eur=1.0)
    assert r["level"] == "exceeded"
    assert "blocked" not in r  # aucune action de blocage automatique
