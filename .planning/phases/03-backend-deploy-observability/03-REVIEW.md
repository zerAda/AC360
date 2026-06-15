---
phase: 03-backend-deploy-observability
reviewed: 2026-06-14
depth: standard (inline orchestrator review — subagent reviewer skipped after repeated session limits)
files_reviewed: 7
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 3: Code Review Report (inline)

Reviewed the production-facing artifacts created/modified this phase: `scripts/telemetry.py`, `scripts/api_server.py` (/ready + startup telemetry), `azure_functions/function_app.py` + `host.json`, `infra/observability.bicep`, `infra/budget.bicep`, `.github/workflows/cd-prod.yml`.

## Verdict: clean (no Critical/Warning)

- **telemetry.py (OBS-01, AUD-06):** lazy SDK import (module imports without `azure-monitor-opentelemetry`); `RedactingSpanProcessor.on_end` routes the span name + every `str` attribute through the single audited `safe_logger.redact` (no new regex); body wrapped in try/except so scrubbing never raises in the request path; `setup_telemetry()` gate-inert when the AppInsights env gate is closed. Correct.
- **/ready (OBS-03):** Entra-gated (`Depends(verify_azure_ad_token)` → 401), returns 200/503 with coarse booleans only — no secret/PII/exception detail leaked; `/health` unchanged as anonymous liveness. Correct.
- **function_app.py + host.json (OBS-01):** `telemetryMode: OpenTelemetry`; guarded `setup_telemetry()` reuses the same gated, redaction-preserving factory; import-safe. Correct.
- **observability.bicep / budget.bicep (OBS-01/02/04/05):** all compile (`az bicep build` exit 0); App Insights connection string wired as a Key Vault reference (zero cleartext); action group webhook is param-driven (no hardcoded URL); budget subscription-scoped. `validate_infra.ps1` passes the prod posture. Correct.
- **cd-prod.yml (CD-01/02):** OIDC (`id-token: write`, no stored SP secret), Bicep what-if gate, `production` Environment approval, Flex `remote-build: true` (no scm/oryx flags), pinned actions. Offline YAML parse OK. Correct.

## Info (non-blocking)

- **IN-01 (telemetry.py):** `on_end` mutates the private `span._attributes`/`span._name`. This is the pragmatic pre-export mutation point (ReadableSpan attributes are immutable at export), but depends on OpenTelemetry internals — revisit if the SDK changes. Low risk.
- **IN-02 (telemetry.py):** only top-level `str` attribute values are redacted; OTel sequence-valued (list/tuple of str) attributes are not recursed. AC360's custom telemetry emits scalar dimensions (and the middleware already uses `redact_mapping`), so the exposure is low-probability. Consider recursing into sequence values in a future hardening pass.

## Verification

- Full suite: 204 passed, 1 skipped (incl. the plaintext-secret scanner, after the /ready fixture false-positive fix).
- `az bicep build` exit 0 for main/observability/budget; `validate_infra.ps1` exit 0; cd-prod.yml valid UTF-8 YAML.
