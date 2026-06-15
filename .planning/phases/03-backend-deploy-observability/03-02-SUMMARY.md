---
phase: 03-backend-deploy-observability
plan: 02
status: complete
completed: 2026-06-14
requirements: [OBS-01, OBS-03]
test_result: "201 passed, 1 skipped (tests/backend + tests/azure_functions)"
---

# Plan 03-02 Summary — App Wiring: /ready + Telemetry Export (OBS-01, OBS-03)

**Note:** the gateway-side work (api_server.py /ready + setup_telemetry) was landed by the executor before a session limit; the Functions-side wiring (host.json + function_app.py) and the SUMMARY/state were completed inline by the orchestrator.

## What landed

### Gateway (api_server.py) — OBS-01 + OBS-03
- `setup_telemetry()` (from `scripts/telemetry.py`) called ONCE at FastAPI `startup` (line ~93), wrapped in try/except so a telemetry misconfig never breaks startup; gate-inert when the AppInsights env gate is closed (dev/test).
- New `GET /ready` (readiness, OBS-03): Entra-gated (`Depends(verify_azure_ad_token)` → 401 unauth), returns 200 `{"status":"ready"}` when coarse dependency checks pass (Key Vault reference resolved — `OBO_CLIENT_SECRET` no longer the `@Microsoft.KeyVault(...)` literal; `AZURE_FUNCTION_URL` set), else 503 `{"status":"degraded"}`. NO secret/PII/exception detail leaked — coarse booleans only (same posture as `_redacted_detail`). `/health` remains the anonymous liveness 200 (availability-test target).

### Functions (host.json + function_app.py) — OBS-01
- `host.json`: added `"telemetryMode": "OpenTelemetry"` (Azure Functions OTel mode).
- `function_app.py`: guarded `setup_telemetry()` call at worker import — the SAME gated, lazy-import, AUD-06-redaction-preserving factory as the gateway (RedactingSpanProcessor). Inert without the SDK / without the AppInsights gate; never raises at import (pytest collection safe). Complemented by the `PYTHON_APPLICATIONINSIGHTS_ENABLE_TELEMETRY` app setting wired in main.bicep (Plan 03-03).

### Tests (test_ready_endpoint.py)
- Wave-0 xfail scaffold flipped to real assertions: 401 unauth, 200 ready, 503 degraded, no-detail-leak.

## Verification
- `pytest tests/backend/test_ready_endpoint.py tests/backend/test_telemetry_redaction.py -x` → 7 passed.
- `pytest tests/backend tests/azure_functions` → **201 passed, 1 skipped** (no regressions).
- `host.json` valid JSON; `telemetryMode == OpenTelemetry`.
- AUD-06 redaction preserved end-to-end (RedactingSpanProcessor reuses `safe_logger.redact`, no new regex).

## Notes
- Live telemetry visibility in App Insights is verified post-deploy (operator checkpoint — depends on Phase 2 live infra + Phase 3 first deploy).
