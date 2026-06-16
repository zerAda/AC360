---
status: human_needed
phase: 06-controlled-e2e-go-no-go-team-rollout
verified: 2026-06-14
method: inline goal-backward verification (orchestrator) — harness/gating/docs offline-verified; live E2E + sign-off + rollout are operator checkpoints (hard-gated on DPO DPIA + full live stack)
requirements: [GO-01, GO-02, GO-03, GO-04]
gates: "test_feature_flags_allowlist 8 passed; test_e2e_smoke 6 passed; full suite 230 passed/1 skipped; both runbooks present with required sections"
---

# Phase 6 Verification — Controlled E2E, Go/No-Go & Team Rollout

**Phase goal:** Prove the full production stack against real Azure with synthetic data, gate to exactly the target team, and roll out gradually after a signed Go/No-Go + clean pilot.

**Verdict: HUMAN_NEEDED.** All Phase 6 **artifacts** are built and offline-verified. The phase's defining outcomes — the live controlled E2E run, the operator Go/No-Go sign-off, and the gradual rollout — are operator checkpoints, **hard-gated on the Phase 5 DPO DPIA sign-off and the full live stack** (Phases 2-4 operator actions).

## Complete (offline-verified)

| Req | Evidence | Status |
|-----|----------|--------|
| GO-01 | `scripts/e2e_smoke.py` — synthetic-data E2E driver (5 scenarios: CONFORME/ECART+FIC/CLIENT_NON_TROUVE/OCR-timeout/Fabric-down), injectable HTTP, `no_pii_kql`; 6 unit tests | ✅ harness / ◷ **live run operator** |
| GO-02 | `feature_flags.py` allowlist (`AC360_ALLOWED_USERS_HASHED`/`AC360_ALLOWED_TEAMS`, deny-by-default when set, fail-safe when unset, block-overrides-allow); 8 tests | ✅ |
| GO-03 | `docs/production/runbooks/07-go-no-go-checklist.md` — consolidated all-gate punch-list + sign-off block | ✅ checklist / ◷ **operator sign-off** |
| GO-04 | `docs/production/runbooks/08-gradual-rollout.md` — pilot→clean-signal→full + abort path | ✅ runbook / ◷ **rollout operator** |

Gates: `pytest tests/backend/test_feature_flags_allowlist.py` 8 passed; `test_e2e_smoke.py` 6 passed; full suite 230 passed/1 skipped; both runbooks present with required sections (07: 9 sections + DPIA refs; 08: pilot/clean-signal/abort).

## Human verification required (operator — gated on DPO DPIA sign-off + live stack)

1. **Run the controlled E2E** (`scripts/e2e_smoke.py`) against the live prod stack with the synthetic client/doc; confirm expected verdicts across all 5 paths (GO-01).
2. **No-PII telemetry check** (`no_pii_kql`) → 0 in App Insights for the run (GO-01 / AUD-06 / RGP-04).
3. **Set the allowlist** to exactly the target team and confirm deny-by-default for outsiders (GO-02 live).
4. **Sign the Go/No-Go checklist** (runbook 07) — requires the DPO DPIA sign-off (RGP-02) box checked (GO-03).
5. **Execute the gradual rollout** (runbook 08): pilot 2-5 → 24-48h clean signal → full team (GO-04).
