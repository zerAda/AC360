---
phase: 05-rgpd-security-evidence-pack
plan: 03
subsystem: security-evidence
tags: [security, rgpd, evidence-pack, authn, authz, mermaid, traceability]
requires: [SECURITY_POSTURE.md, scripts/auth.py, scripts/graph_obo.py, tests/backend/]
provides: [SEC-01-architecture-dataflow, SEC-02-authn-authz]
affects: [SEC-03-threat-coverage-matrix]
tech-stack:
  added: []
  patterns: [mermaid-diagrams, control-to-test-traceability, trust-boundary-subgraphs]
key-files:
  created:
    - docs/security/SEC-01-architecture-dataflow.md
    - docs/security/SEC-02-authn-authz.md
  modified: []
decisions:
  - "SEC-01 uses two Mermaid flowcharts (architecture + PII data-flow) with subgraph trust boundaries, per locked CONTEXT decision"
  - "SEC-02 traces every authN/authZ control to at least one existing test cited by path (no new tests authored)"
metrics:
  duration: ~12m
  completed: 2026-06-15
requirements: [SEC-01, SEC-02]
---

# Phase 5 Plan 03: SEC-01 + SEC-02 Security Evidence Docs Summary

Two security-evidence-pack documents authored as pure markdown from existing repo
artifacts: **SEC-01** (Mermaid architecture + PII data-flow with explicit trust
boundaries) and **SEC-02** (authN/authZ description with every control traced to an
existing test by path).

## What was built

### Task 1 — SEC-01 (`docs/security/SEC-01-architecture-dataflow.md`)
- **2 Mermaid `flowchart` blocks**: (1) component/architecture diagram with four
  `subgraph` trust boundaries (Entra SSO, OBO user-delegated, data-plane, observability);
  (2) PII data-flow diagram marking PII entry (OCR), ephemeral storage
  (`JOBS_BASE_DIR` + blobs, RGP-03 30-day TTL), and redacted telemetry out
  (`RedactingSpanProcessor` -> Log Analytics, RGP-04 90-day).
- Prose "Frontières de confiance" section: 4-boundary table (untrusted input crossing
  + boundary control + proof pointer) and explicit PII enters/ephemeral/exits narrative.
- RGP-03/RGP-04 cross-refs and SEC-02/SEC-03 cross-refs. French domain prose, English identifiers.

### Task 2 — SEC-02 (`docs/security/SEC-02-authn-authz.md`)
- "Contrôle -> Description -> Test (chemin)" traceability table covering: Entra SSO +
  JWT RS256/JWKS, `oid` identity, IDOR gate (`_assert_durable_owner` / `owner_hash`),
  OBO user-delegated (RBAC, never persisted, 503-not-502), read-only enforcement, and
  the associated redaction/security-headers surface.
- Per-control detail sections citing concrete test functions (not just files).
- ASVS V2/V3/V4 mapping. Anchored to `SECURITY_POSTURE.md` §3/§4 as upstream source.
- **20 `tests/...` path citations**; every control row cites ≥1 real, green test.

## Verification

Structural grep assertions run locally (shell available) — all pass:

| Assertion | Result |
|-----------|--------|
| SEC-01 ` ```mermaid ` count ≥ 2 | 2 ✅ |
| SEC-01 contains `SEC-01` | ✅ |
| SEC-01 trust-boundary terms (OBO/trust/confiance/boundary/frontière) | 22 matches ✅ |
| SEC-01 PII-flow terms (JOBS_BASE_DIR/OCR/PII) | 30 matches ✅ |
| SEC-02 `tests/` count ≥ 3 | 20 ✅ |
| SEC-02 contains `test_auth_jwt` AND `test_audit_ownership` | 5 / 4 ✅ |
| SEC-02 RS256/JWKS | 9 ✅ |
| SEC-02 OBO AND read-only/lecture seule | 8 / 6 ✅ |
| Task1 PowerShell verify (≥2 mermaid AND SEC-01) | passes ✅ |
| Task2 PowerShell verify (4 SimpleMatch patterns ≥4) | passes ✅ |

Cited tests are real files confirmed present in `tests/backend/` (test function names
extracted directly from source). The orchestrator should run the plan's `<verification>`
test command to confirm green:
`python -m pytest tests/backend/test_auth_jwt.py tests/backend/test_audit_ownership.py tests/backend/test_job_isolation.py -x`

## Deviations from Plan

None — both deliverables authored exactly as specified (filenames, sections, Mermaid
blocks, test-by-path traceability). No package installs (consistent with phase research:
slopcheck no-op for Phase 5).

## Known Stubs

None. Both docs are complete prose/diagram deliverables sourced from existing artifacts.

## Self-Check: PASSED

- FOUND: docs/security/SEC-01-architecture-dataflow.md
- FOUND: docs/security/SEC-02-authn-authz.md
- FOUND: .planning/phases/05-rgpd-security-evidence-pack/05-03-SUMMARY.md
- All structural grep assertions for both Task 1 and Task 2 pass (table above).
- Commits: deferred to orchestrator (this session authored files; orchestrator commits).
