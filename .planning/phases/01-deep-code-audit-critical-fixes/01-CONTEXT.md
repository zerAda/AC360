# Phase 1: Deep Code Audit & Critical Fixes - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Re-validate the committed security hardening against the **production multi-worker topology** and land every **launch-blocking** code fix in the repo before the first prod deploy. Scope is audit + targeted fixes + tests + a written security-posture document — NOT a refactor or rewrite (stack is locked). Covers requirements AUD-01 through AUD-08.

In scope:
- Re-check each "Addressed" mitigation under an N>1-instance threat model.
- `owner_hash` from Entra Object ID; durable check as authoritative IDOR gate.
- Single-instance gateway pin documented as load-bearing for in-memory state.
- OBO bounded-backoff retry; PII/secret redaction in client errors + App Insights traces.
- Immutable document-access audit trail.
- Confirm JOBS_BASE_DIR artifact availability across the download→OCR→compare→FIC chain.

Out of scope: new features, re-architecture, distributed cache/Redis scale-out, fixing non-launch-blocking tech debt (logged as deferred).

</domain>

<decisions>
## Implementation Decisions

### Audit Scope & Triage
- Launch-blocking bar = items that break correctness or security under the production topology: the 5 success criteria plus the IDOR (owner_hash reuse) and PII-in-error/trace bugs surfaced in `.planning/codebase/CONCERNS.md`. Everything else is logged as deferred tech debt, not fixed this phase.
- In-memory store thread-safety (JWKS cache, rate-limit store): the single-instance pin (scale-out max = 1, one worker) is the mitigation. Document this as load-bearing in IaC; do NOT add async-lock rewrites this phase.
- Broad `except Exception` cleanup: tighten only in the auth / OBO / download hot paths touched this phase; leave other occurrences as deferred debt.
- Phase output: a written security-posture document (feeds Phase 5) + targeted code fixes + accompanying tests, all landed in-repo.

### owner_hash & IDOR Hardening
- Derive `owner_hash` from the Entra **Object ID** (`oid` claim) — stable across user re-provisioning (closes the UPN-reuse IDOR bug).
- Hash construction: SHA-256 of the `oid`, no salt (deterministic lookup required; `oid` is already an opaque GUID).
- The durable `owner_hash` check is the authoritative IDOR gate; the in-memory ownership map is treated as a fast-path cache only.
- Clean cutover — the app has never been deployed, so there are no existing hashes to migrate or dual-read.

### Audit Trail & PII Redaction
- Immutable log sink: App Insights custom events flowing to a Log Analytics workspace with a retention/immutability policy (native, solo-operator-friendly). Provisioning of the workspace policy is a Phase 2/3 dependency; this phase wires the emit path and field contract.
- Audit record fields: user-id hash, document id, timestamp (UTC), verdict — exactly per criterion. No raw PII (no UPN, no client name).
- Client-facing error bodies: route every HTTPException detail through `safe_logger.redact()`; return a generic message + correlation id to the client.
- App Insights trace redaction: extend `redact()` coverage so PII/secrets are stripped before telemetry emit, not just on file logs.

### OBO Retry & Pipeline File Integrity
- OBO token exchange retry: bounded exponential backoff — 3 attempts, ~0.5s base delay, with jitter; retry ONLY transient failures (request timeouts, 429, 503, connection errors), not auth/4xx.
- On exhausted retries, return HTTP 503 (service unavailable), not 502.
- JOBS_BASE_DIR: keep the single-activity chain so download→OCR→compare→FIC artifacts stay co-located (no cross-worker file loss); document this as the pipeline invariant.
- Verification: add a test asserting the chain shares the artifact path across stages.

### Claude's Discretion
- Exact backoff jitter algorithm, correlation-id format, security-posture doc structure, and test organization are at Claude's discretion, consistent with existing codebase conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/safe_logger.py` — `redact()` and `log_security()`; extend coverage to App Insights traces and HTTPException detail strings.
- `scripts/feature_flags.py` — `hash_id()` used for owner hashing; point at `oid` claim.
- `scripts/auth.py` — JWT/JWKS validation; source of the `oid` claim.
- `scripts/graph_obo.py` — OBO token exchange; add bounded backoff retry here.
- `azure_functions/shared/audit_pipeline.py` + `function_app.py` — pipeline orchestration; JOBS_BASE_DIR chain lives here.
- `infra/main.bicep` — document single-instance pin (scale-out max=1) as load-bearing.

### Established Patterns
- snake_case, type hints on core modules (mypy strict on listed modules), `from __future__ import annotations`.
- Errors raised as `HTTPException`; all externally observable output routed through `safe_logger.redact()`.
- Pure functions with dependency injection (AuditDeps) — testable without live cloud SDKs.

### Integration Points
- New audit-trail emit hooks into the document-access path in `scripts/api_server.py` and the download activity in `function_app.py`.
- `owner_hash` change touches `api_server.py` ownership checks + durable owner assertion.

### Reference
- `.planning/codebase/CONCERNS.md` is the authoritative inventory of bugs/tech debt for triage (dated 2026-06-11).

</code_context>

<specifics>
## Specific Ideas

- Open verification item (carry into planning): the exact OBO delegated Graph scope list must be verified against the live staging app registration before fixes/tests rely on it (per ROADMAP risk + STATE blocker).
- The security-posture document is an explicit Phase 1 deliverable feeding Phase 5 (RGPD & Security Evidence Pack).

</specifics>

<deferred>
## Deferred Ideas

- Async-lock thread-safety rewrites for in-memory stores (mitigated by single-instance pin).
- Distributed cache / Redis scale-out (explicitly out of scope this milestone).
- Symlink path-traversal hardening, Fabric-unavailable fallback mode, fuzzy-match indexing, admin dashboard, bulk/webhook endpoints — all logged in CONCERNS.md as non-launch-blocking.
- Full sweep of broad `except Exception` blocks outside touched hot paths.

</deferred>
