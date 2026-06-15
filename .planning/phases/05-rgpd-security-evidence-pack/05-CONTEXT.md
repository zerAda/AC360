# Phase 5: RGPD & Security Evidence Pack - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Produce and assemble all compliance + security-review evidence required before real users / real client data. Covers SEC-01..05 (security pack) and RGP-01..06 (RGPD). The DPIA (RGP-02) must be complete before Phase 6 begins.

**Execution boundary:** Most of this phase is documentation/evidence + two small code/IaC deliverables (RGP-03 retention enforcement, RGP-04 telemetry retention). The DPO-dependent items (RGP-01 record of processing, RGP-02 DPIA sign-off) are **drafted autonomously** but their finalization/sign-off is an **external (DPO) operator checkpoint** — the DPIA draft + CNIL assessment are produced here; DPO sign-off is the hard gate before Phase 6. Live EU-residency confirmation (RGP-06) reuses the Phase 2 operator checkpoints; the Bicep-locations portion is verifiable now.

Depends on: Phase 1 (audit trail, redaction, security posture doc), Phases 2-4 (infra, observability, guardrails evidence). Out of scope: new app features; external pen-test / certification (out of scope per REQUIREMENTS).

</domain>

<decisions>
## Implementation Decisions

### Security Evidence Pack (SEC-01..05)
- SEC-01 diagrams: **Mermaid in markdown** (versionable, GitHub-rendered) — architecture + data-flow with PII flow + trust boundaries.
- SEC-02: authN/authZ description (Entra SSO, JWT RS256/JWKS, OBO scope, IDOR, read-only) **linked to existing tests** (test_auth_jwt, test_audit_ownership, test_job_isolation, etc.).
- SEC-03: threat-coverage matrix **synthesized from the per-phase `<threat_model>` STRIDE blocks + OWASP LLM Top 10 + existing tests** (OWASP/LLM risk → mitigation → test).
- SEC-04: add **`.github/dependabot.yml` (pip ecosystem)** + document the PyJWT/deltalake pin policy (from CONCERNS.md "Dependencies at Risk").
- SEC-05: accepted-risk / known-issues register — **classify CONCERNS.md items** must-fix-done (Phase 1 fixes) vs accepted-deferred (ref Phase 1 `deferred-items.md`).

### RGPD Data Lifecycle (RGP-03, RGP-04)
- RGP-03: **Storage lifecycle management rule (Bicep)** deleting job/OCR/FIC blobs + a **`JOBS_BASE_DIR` TTL cleanup** (code/script). Job-artifact retention = **30 days** (data-minimization; configurable Bicep param).
- RGP-04: **PII-in-logs handling statement** doc + confirm the **RedactingSpanProcessor** (Phase 3, `scripts/telemetry.py`) as the App Insights telemetry processor + set **Log Analytics retention = 90 days** (short, EU-region) in Bicep (observability.bicep / main.bicep).

### RGPD Governance (RGP-01, RGP-02, RGP-05, RGP-06)
- RGP-02: **draft the full DPIA + CNIL ≥2-of-9 criteria assessment** as a document; **DPO sign-off = external operator checkpoint** and the **hard gate before Phase 6**.
- RGP-01: **draft the Art. 30 record-of-processing entry**; DPO finalizes.
- RGP-05: **document the DSR (data-subject request) procedure**, leveraging the read-only + ephemeral-artifacts (30-day TTL) architecture.
- RGP-06: **EU data-residency confirmation doc** aggregating the verifiable Bicep `location` values (France Central / West Europe DocIntel) + the Phase 2 operator residency checkpoints (M365 geo, Fabric region, Power Platform env region).

### Claude's Discretion
- Evidence-pack file organization (docs/security/ + docs/governance/), Mermaid diagram detail, DPIA template structure, and the TTL-cleanup script form are at Claude's discretion, consistent with existing docs/ conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/security/SECURITY_POSTURE.md` (Phase 1), `docs/security/GUARDRAILS_VALIDATION.md` (Phase 4), `docs/security/SECURITY_BASELINE.md` — the security-pack home + analogs.
- `.planning/codebase/CONCERNS.md` — source for SEC-05 (accepted-risk) + SEC-04 (deps at risk).
- Per-phase `<threat_model>` blocks in all PLAN.md files — source for SEC-03 matrix.
- `scripts/telemetry.py` (RedactingSpanProcessor), `scripts/safe_logger.py` — RGP-04 telemetry processor evidence.
- `scripts/audit_trail.py` — AUD-07 immutable audit trail (4-field, no PII) — SEC/RGPD evidence.
- `infra/main.bicep` + `infra/observability.bicep` — add Storage lifecycle rule (RGP-03) + Log Analytics retention (RGP-04); Bicep `location` values for RGP-06.
- Phase 1 `deferred-items.md`, Phase 2/3/4 operator checkpoints — feed SEC-05 + RGP-06.

### Established Patterns
- Markdown docs in docs/{security,governance,production}; French allowed in domain docs.
- Bicep parameterized staging-safe; validate via `az bicep build` + `validate_infra.ps1`.

### Integration Points
- SEC-03 references existing tests by path; SEC-02 links authn tests.
- RGP-03 Storage lifecycle + JOBS_BASE_DIR TTL: Bicep + a cleanup script (cron/timer or documented manual).
- RGP-04 Log Analytics retention param flows into observability.bicep.

### Reference
- DPIA / record-of-processing depend on the external DPO (STATE blocker) — draft here, DPO finalizes; DPIA hard-gates Phase 6.

</code_context>

<specifics>
## Specific Ideas

- The read-only + no-write + ephemeral-artifacts (30-day TTL) + audit-trail (hashed user id, no raw PII) architecture is the backbone of the DPIA risk-reduction narrative and the DSR procedure — make that explicit.
- The threat matrix should map OWASP LLM Top 10 (prompt injection, sensitive info disclosure, etc.) to the concrete AC360 mitigations (contentModeration High, useModelKnowledge false, redaction, IDOR gate, OBO) and the tests that prove them.

</specifics>

<deferred>
## Deferred Ideas

- DPO sign-off of the DPIA + Art. 30 record (external operator checkpoint; hard gate before Phase 6).
- Live EU-residency confirmation against the tenant (Phase 2 operator checkpoint; aggregated here).
- External pen-test / formal certification (out of scope per REQUIREMENTS).
- Automated secret-expiry calendar (OPS-06, v2).

</deferred>
