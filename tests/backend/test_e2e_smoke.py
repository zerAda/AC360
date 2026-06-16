"""GO-01 — E2E harness logic (offline, mocked HTTP; NO live call).

Verifies request-building, verdict classification, the poll loop, the synthetic-only
data contract, and the no-PII KQL helper — all with injected fake HTTP seams.
"""
import e2e_smoke


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_build_request_uses_synthetic_client():
    body = e2e_smoke.build_audit_request(e2e_smoke.SYNTHETIC_CLIENT, "e2e-synthetic-x")
    assert body["client_context"] == e2e_smoke.SYNTHETIC_CLIENT
    assert "SYNTHETIQUE" in body["client_context"]  # clearly-fake marker
    assert body["document_id"] == "e2e-synthetic-x"


def test_classify_result_extracts_verdict():
    assert e2e_smoke.classify_result({"verdict": "CONFORME"}) == "CONFORME"
    assert e2e_smoke.classify_result({}) is None
    assert e2e_smoke.classify_result("nope") is None


def test_run_scenario_happy_path_no_live_call():
    calls = {"post": 0, "get": 0}

    def fake_post(url, json=None, headers=None):
        calls["post"] += 1
        return _FakeResp({"id": "job-1"})

    def fake_get(url, headers=None):
        calls["get"] += 1
        return _FakeResp({"runtimeStatus": "Completed", "output": {"verdict": "CONFORME"}})

    scenario = {"name": "happy_conforme", "doc": "e2e-synthetic-conforme", "expected": "CONFORME"}
    r = e2e_smoke.run_scenario(
        scenario, base_url="https://prod.example", token="t",
        http_post=fake_post, http_get=fake_get, sleep=lambda s: None,
    )
    assert r["ok"] is True and r["verdict"] == "CONFORME"
    assert calls["post"] == 1 and calls["get"] == 1  # injected seams used; no real network


def test_run_scenario_polls_until_complete():
    seq = [
        _FakeResp({"runtimeStatus": "Running"}),
        _FakeResp({"runtimeStatus": "Running"}),
        _FakeResp({"runtimeStatus": "Completed", "output": {"verdict": "ECART"}}),
    ]

    def fake_get(url, headers=None):
        return seq.pop(0)

    slept = []
    r = e2e_smoke.run_scenario(
        {"name": "ecart_fic", "doc": "e2e-synthetic-ecart", "expected": "ECART"},
        base_url="https://prod.example", token="t",
        http_post=lambda *a, **k: _FakeResp({"id": "job-2"}),
        http_get=fake_get, sleep=slept.append,
    )
    assert r["verdict"] == "ECART" and r["ok"] is True
    assert len(slept) == 2  # polled twice before completion


def test_scenarios_cover_all_required_paths():
    names = {s["name"] for s in e2e_smoke.SCENARIOS}
    assert {"happy_conforme", "ecart_fic", "client_non_trouve", "ocr_timeout", "fabric_down"} <= names
    # every scenario doc is clearly synthetic
    assert all(s["doc"].startswith("e2e-synthetic-") for s in e2e_smoke.SCENARIOS)


def test_no_pii_kql_targets_correlation_and_pii_patterns():
    kql = e2e_smoke.no_pii_kql("corr-123")
    assert "corr-123" in kql
    assert "matches regex" in kql  # email / IBAN PII patterns
    assert "0" in kql  # expected count is zero
