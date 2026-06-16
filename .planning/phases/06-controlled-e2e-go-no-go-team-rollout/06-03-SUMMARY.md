---
phase: 06-controlled-e2e-go-no-go-team-rollout
plan: 03
status: complete
completed: 2026-06-14
requirements: [GO-01]
test_result: "test_e2e_smoke 6 passed"
---

# Plan 06-03 Summary — Synthetic E2E smoke harness (GO-01)

Executed inline. Created `scripts/e2e_smoke.py`: a synthetic-data E2E driver (audit → status-poll → result) with **injectable** `http_post`/`http_get`/`sleep` seams (offline-testable, no live call). `SYNTHETIC_CLIENT` is clearly fake (no real PII); `SCENARIOS` cover happy CONFORME + ECART+FIC + CLIENT_NON_TROUVE + OCR-timeout + Fabric-down with expected verdicts; `classify_result` reads the schema verdict; `no_pii_kql(correlation_id)` returns the App Insights query asserting 0 PII (email/IBAN) traces. `main()` is the operator live entry (httpx, env-driven) — not run by CI.

**Verification:** 6 harness tests green (mocked HTTP). The actual live run against prod + the no-PII check are operator checkpoints (gated on the live stack + DPO sign-off).
