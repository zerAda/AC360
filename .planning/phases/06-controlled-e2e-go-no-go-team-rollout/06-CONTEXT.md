# Phase 6: Controlled E2E, Go/No-Go & Team Rollout - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Prove the full production stack against real Azure with synthetic test data (happy + failure paths), gate to exactly the target team, and roll out gradually after a signed Go/No-Go + clean pilot. Covers GO-01..04.

**Execution boundary (HARD-GATED):** This is the go-live phase. Its actual execution is blocked on (a) the DPO DPIA sign-off (RGP-02, Phase 5 — hard roadmap gate before Phase 6) and (b) the full live stack (Phases 2-4 operator actions: provision, deploy, publish). This phase therefore produces the **artifacts**: the E2E test harness + synthetic scenarios (GO-01), the allowlist gating code (GO-02), the Go/No-Go checklist (GO-03), and the gradual-rollout runbook (GO-04). The live E2E run, the operator sign-off, and the rollout are **operator checkpoints**.

Out of scope: new app features; the actual go-live execution (operator, post-gate).

</domain>

<decisions>
## Implementation Decisions

### Controlled E2E Harness (GO-01)
- Form: a **synthetic-data E2E script** (`scripts/e2e_smoke.py`) that drives the real prod endpoints (gateway `/api/audit` → status → result), env-parameterized (prod gateway URL + a test token). Offline: unit-tested with mocked HTTP (no live call); the **live run is an operator checkpoint**.
- Failure-path coverage: scripted + documented scenarios with expected verdicts — **OCR timeout, CLIENT_NON_TROUVE, Fabric-down, ECART+FIC** (plus the happy CONFORME path).
- Telemetry no-PII check: a **post-run check** (KQL query / script) asserting no PII appears in App Insights traces for the E2E run (reuses the AUD-06 redaction + RGP-04 posture).
- Synthetic data: a **clearly-fake test client + document** (no real client PII), documented as such.

### Gating & Go/No-Go (GO-02, GO-03)
- GO-02: **add an allowlist mode to `scripts/feature_flags.py`** — `AC360_ALLOWED_TEAMS` / `AC360_ALLOWED_USERS_HASHED`. **Deny-by-default when an allowlist is set** (only listed teams/users allowed); **backward-compatible when unset** (current blocklist behavior, no regression). Combined with the Phase 4 Teams 1:1 install scope. Unit-tested.
- GO-03: a **Go/No-Go checklist doc** aggregating every gate (deploy verified, alerts firing, DPIA DPO-signed, controlled E2E green + no-PII, gating confirmed to the target team) for **operator sign-off**.

### Gradual Rollout (GO-04)
- A **gradual-rollout runbook**: pilot cohort of 2-5 users → a **24-48h clean signal** → full team, using the allowlist as the lever.
- **Clean-signal criteria (explicit):** no Sev1/Sev2 alerts, gateway/Functions error rate below threshold, no PII-leak telemetry finding, budget within bound — sustained 24-48h.
- **Abort/rollback during rollout:** defined abort criteria → `docs/production/runbooks/02-rollback.md` + `05-killswitch.md`.

### Claude's Discretion
- E2E script structure, scenario fixture format, allowlist env var precedence details, and checklist/runbook layout are at Claude's discretion, consistent with existing scripts/ + docs/production/runbooks/ conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/feature_flags.py` — block-list model (`is_user_blocked`/`is_team_blocked`, `AC360_BLOCKED_*`); ADD the allowlist mode here (GO-02). `hash_id` reused for user-hash allowlist.
- `scripts/api_server.py` — the gating call site (`is_allowed`) the allowlist must flow through.
- `scripts/run_demo.py` (if present) — analog for the E2E driver script.
- `docs/production/runbooks/` — 02-rollback.md, 05-killswitch.md (abort path); add the rollout runbook + Go/No-Go checklist.
- Phase 3 observability (alerts, dashboard) + Phase 4 GUARDRAILS_VALIDATION.md — the clean-signal + no-PII evidence sources.

### Established Patterns
- DI/fake-driven tests (test_graph_obo `_FakeResp`/injected http_post) — analog for the E2E harness unit tests + the allowlist tests.
- Env-gated feature flags (CSV sets) — extend with allowlist CSV sets.

### Integration Points
- Allowlist flows: feature_flags.py → api_server.py `is_allowed` gate.
- E2E script → prod gateway endpoints (operator-run with prod env + token).
- Telemetry no-PII check → App Insights / Log Analytics (KQL).

### Reference
- Phase 5 DPIA DPO sign-off is the HARD gate before this phase's live execution (STATE blocker).

</code_context>

<specifics>
## Specific Ideas

- The allowlist must be **fail-safe**: an empty/unset allowlist must NOT accidentally lock everyone out (backward-compat = unset means "no allowlist restriction"); a *set* allowlist is deny-by-default. Make this explicit + tested.
- GO-01 telemetry no-PII check is the live proof of AUD-06/RGP-04 — link it to GUARDRAILS_VALIDATION.md §2.
- The Go/No-Go checklist is the single consolidated go-live punch-list referencing every prior-phase operator checkpoint.

</specifics>

<deferred>
## Deferred Ideas

- The live controlled E2E run, operator Go/No-Go sign-off, and the gradual rollout — operator checkpoints (gated on DPO sign-off + full live stack).
- REL-02 synthetic full-audit availability test on a schedule (v2).

</deferred>
