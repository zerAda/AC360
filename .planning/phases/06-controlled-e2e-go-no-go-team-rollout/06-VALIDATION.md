---
phase: 6
slug: controlled-e2e-go-no-go-team-rollout
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-14
---

# Phase 6 — Validation Strategy

> The allowlist gating (GO-02) and the E2E harness logic (GO-01) are offline-verifiable via pytest with mocked HTTP. The live E2E run, Go/No-Go sign-off, and rollout are operator checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`setup.cfg`, asyncio_mode auto) |
| **Quick run command** | `python -m pytest tests/backend/test_feature_flags_allowlist.py tests/backend/test_e2e_smoke.py -x` |
| **Full suite command** | `python -m pytest tests/backend tests/azure_functions tests/security` |
| **Doc validation** | markdown lint / structural grep on the Go/No-Go checklist + rollout runbook |

---

## Sampling Rate

- **After every task commit:** the relevant quick command (pytest on the allowlist / E2E-harness tests; grep on docs).
- **After every wave:** full backend+functions+security suite.
- **Phase gate:** full suite green + allowlist fail-safe tests green + checklist/runbook structural greps pass. The live E2E run + operator sign-off + rollout are operator checkpoints (not automated gates).

---

## Per-Requirement Validation Map

| Req | Behavior | Type | Command / check | Live? |
|-----|----------|------|-----------------|-------|
| GO-01 (harness) | E2E script builds the request + classifies the verdict per scenario; mocked HTTP | unit | `pytest tests/backend/test_e2e_smoke.py -x` | offline |
| GO-01 (live run) | real-prod E2E happy + 4 failure paths + no-PII telemetry | manual | operator runs `scripts/e2e_smoke.py` vs prod + KQL no-PII check | operator |
| GO-02 (allowlist) | allowlist set → only listed teams/users allowed (deny-by-default); unset → no restriction (backward-compat); fail-safe | unit | `pytest tests/backend/test_feature_flags_allowlist.py -x` | offline |
| GO-03 (checklist) | Go/No-Go checklist exists with all gate rows + sign-off block | structural | grep | offline (sign-off = operator) |
| GO-04 (rollout) | rollout runbook with pilot→clean-signal→full, criteria, abort path | structural | grep | offline (execution = operator) |

---

## Wave 0 Requirements

- [ ] `tests/backend/test_feature_flags_allowlist.py` — allowlist deny-by-default, unset=no-restriction (fail-safe), user+team allowlist, RED first
- [ ] `tests/backend/test_e2e_smoke.py` — E2E harness request-build + verdict-classification with mocked HTTP (no live call)
- [ ] No framework install (pytest present)

---

## Manual-Only Verifications (operator checkpoints — gated on DPO sign-off + live stack)

| Behavior | Req | Why Manual | Instructions |
|----------|-----|------------|--------------|
| Controlled real-prod E2E (happy + 4 failure paths) | GO-01 | Needs live prod stack | Run `scripts/e2e_smoke.py` against prod with synthetic client/doc; confirm expected verdicts |
| Telemetry no-PII check | GO-01 | Needs live App Insights | Run the KQL no-PII query for the E2E correlation id; confirm no PII (→ GUARDRAILS_VALIDATION §2) |
| Operator Go/No-Go sign-off | GO-03 | Human decision | Complete + sign the checklist (incl. DPIA DPO sign-off gate) |
| Gradual rollout pilot→full | GO-04 | Live, time-based | Allowlist pilot 2-5 → 24-48h clean signal → full team |

---

## Validation Sign-Off

- [ ] GO-02 allowlist (fail-safe, backward-compat) + GO-01 harness logic offline-verified
- [ ] Go/No-Go checklist + rollout runbook present with required sections
- [ ] Live E2E / sign-off / rollout documented as operator checkpoints (gated on DPO + live stack)
- [ ] `nyquist_compliant: true` set

**Approval:** pending
