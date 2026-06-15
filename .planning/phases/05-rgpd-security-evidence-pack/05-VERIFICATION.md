---
status: human_needed
phase: 05-rgpd-security-evidence-pack
verified: 2026-06-14
method: inline goal-backward verification (orchestrator) — code/IaC + evidence docs offline-verified; DPO sign-off (RGP-01/02) and live residency (RGP-06) are external/operator checkpoints
requirements: [SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, RGP-01, RGP-02, RGP-03, RGP-04, RGP-05, RGP-06]
gates: "test_jobs_ttl 5 passed; az bicep build main+observability exit 0; cited authn tests 29 passed; all SEC/RGP docs present with required sections"
---

# Phase 5 Verification — RGPD & Security Evidence Pack

**Phase goal:** All compliance and security-review evidence produced and assembled, with the DPIA complete before the controlled-E2E phase.

**Verdict: HUMAN_NEEDED.** The full evidence pack + the two enforcement deliverables are produced and offline-verified. The **DPO sign-off of the DPIA (RGP-02) and Art. 30 record (RGP-01) is the hard external gate before Phase 6**, and the live-tenant residency confirmation (RGP-06) is an operator checkpoint.

## Complete (offline-verified)

| Req | Evidence | Status |
|-----|----------|--------|
| SEC-01 | `docs/security/SEC-01-architecture-dataflow.md` — 2 Mermaid diagrams, trust boundaries, PII flow | ✅ |
| SEC-02 | `SEC-02-authn-authz.md` — controls linked to 20 test paths; cited tests 29 pass | ✅ |
| SEC-03 | `SEC-03-threat-coverage-matrix.md` — OWASP LLM Top-10 + STRIDE → mitigation → test | ✅ |
| SEC-04 | `SEC-04-dependency-posture.md` — existing dependabot.yml documented + PyJWT/deltalake pin policy; security grouping added | ✅ |
| SEC-05 | `SEC-05-accepted-risk-register.md` — CONCERNS.md classified must-fix-done vs accepted-deferred | ✅ |
| RGP-03 | `jobs_ttl.prune_jobs_dir` (5 tests) + daily timer + storage `managementPolicies` rule + `RGP-03-retention-policy.md` (honest ~37d window) | ✅ |
| RGP-04 | Log Analytics retention param (90d) + `RGP-04-pii-in-logs-statement.md` (RedactingSpanProcessor) | ✅ |
| RGP-05 | `RGP-05-DSR-procedure.md` — DSR rights via read-only + ephemeral + hashed-audit architecture | ✅ |
| RGP-06 | `RGP-06-data-residency.md` — Bicep locations verified (francecentral); tenant items marked operator-checkpoint | ✅ (Bicep) / ◷ (tenant) |
| RGP-01 | `RGP-01-record-of-processing.md` — Art. 30 draft, all 7 fields | ◷ **DPO finalize** |
| RGP-02 | `RGP-02-DPIA.md` — DPIA + CNIL 9-criteria (≥2 met) | ◷ **DPO sign-off — HARD GATE before Phase 6** |

Gates: `pytest tests/azure_functions/test_jobs_ttl.py` 5 passed; `az bicep build` main + observability exit 0; cited authn tests 29 passed; all evidence docs present with required sections; GOVERNANCE.md retention contradiction reconciled.

## Human verification required (external DPO / operator)

1. **DPO signs the DPIA (RGP-02)** — the hard gate before Phase 6 go-live. The draft + CNIL 9-criteria assessment (criteria 4/6/8 met → DPIA warranted) is ready for review.
2. **DPO finalizes the Art. 30 record (RGP-01)** — controller/DPO identity fields.
3. **Live EU residency (RGP-06)** — confirm M365 tenant geo, Fabric capacity region, Power Platform env region EU (Phase 2 / 02-06 checkpoint). Bicep locations already verified francecentral.
4. **Live retention apply** — confirm the storage lifecycle rule + 90-day Log Analytics retention on the deployed prod resources.

> Phase 6 (controlled E2E / go-live) is **blocked on the DPO DPIA sign-off** per the roadmap dependency.
