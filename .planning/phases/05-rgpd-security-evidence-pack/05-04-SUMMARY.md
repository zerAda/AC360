---
phase: 05-rgpd-security-evidence-pack
plan: 04
subsystem: security-evidence
tags: [security, owasp-llm, stride, dependabot, supply-chain, accepted-risk, rgpd]
requires:
  - docs/security/SECURITY_POSTURE.md
  - docs/security/GUARDRAILS_VALIDATION.md
  - .planning/codebase/CONCERNS.md
  - .github/dependabot.yml
  - per-phase <threat_model> STRIDE registers (Phases 1-5)
provides:
  - docs/security/SEC-03-threat-coverage-matrix.md
  - docs/security/SEC-04-dependency-posture.md
  - docs/security/SEC-05-accepted-risk-register.md
affects:
  - .github/dependabot.yml
tech-stack:
  added: []
  patterns: [dependabot-groups-security-updates]
key-files:
  created:
    - docs/security/SEC-03-threat-coverage-matrix.md
    - docs/security/SEC-04-dependency-posture.md
    - docs/security/SEC-05-accepted-risk-register.md
  modified:
    - .github/dependabot.yml
decisions:
  - "SEC-03 synthesizes OWASP LLM Top 10 2025 (9/10 mapped; LLM04 out-of-scope, no training/fine-tuning) + per-phase STRIDE registers; every row carries mitigation + evidence/test."
  - "SEC-04 documents the existing .github/dependabot.yml (not recreated) + PyJWT/deltalake/durable/Levenshtein pin policy; optional security-updates groups added; no packages installed."
  - "SEC-05 classifies every CONCERNS.md item; all launch-blocking bugs = must-fix-done; remaining debt = accepted-deferred (none launch-blocking); no-WORM caveat flagged for DPO."
metrics:
  duration: ~8 min
  completed: 2026-06-15
  tasks: 3
  files: 4
---

# Phase 5 Plan 04: SEC-03/04/05 Security Evidence Pack Summary

OWASP LLM 2025 + STRIDE threat-coverage matrix (SEC-03), Dependabot + pin-policy dependency posture (SEC-04), and a CONCERNS.md accepted-risk register (SEC-05) — completing the five-component security evidence pack with every risk row carrying a mitigation and a proving test/reference.

## What Was Built

### Task 1 — SEC-03 threat-coverage matrix
`docs/security/SEC-03-threat-coverage-matrix.md`. Two synthesized tables:
- **OWASP LLM Top 10 (2025)** → AC360 mitigation → evidence/test. 9/10 risks mapped (LLM01 prompt injection, LLM02 sensitive info disclosure, LLM03 supply chain, LLM05 improper output handling, LLM06 excessive agency, LLM07 system prompt leakage, LLM08 vector/embedding, LLM09 misinformation, LLM10 unbounded consumption). LLM04 (data/model poisoning) marked out-of-scope (no training/fine-tuning). Each row cites real evidence: `GUARDRAILS_VALIDATION.md`, `validate_copilot_yaml.py`, `tests/security/test_no_plaintext_secrets.py`, `tests/backend/test_telemetry_redaction.py`, `schemas/audit_result.schema.json`, `tests/backend/test_audit_ownership.py` / `test_job_isolation.py`, `GOVERNANCE.md §3`.
- **STRIDE coverage** synthesized from the per-phase `<threat_model>` registers — representative T-0x IDs from Phases 1–5 (T-01-SC, T-02-03/11/24, T-03-01/03/05, T-04-01/02/06/09, T-05-06/08/09/10/12/13/14), each with mitigation + proof.
- Cross-references SEC-01 (diagram), SEC-02 (authn tests), SEC-04 (supply chain), SEC-05 (accepted risk).

### Task 2 — SEC-04 dependency posture
`docs/security/SEC-04-dependency-posture.md`. Documents the **existing** `.github/dependabot.yml` (pip at `/`, `/azure_functions`, `/scripts` + github-actions, weekly, `dependencies`/`security` labels) — not recreated. Transcribes the pin policy from CONCERNS.md "Dependencies at Risk": PyJWT (>=2.8.0; pin 2.9.0+ when available; algorithm-confusion rationale), deltalake (>=0.18.0; Rust bindings, DataFrame validation), azure-functions-durable (>=1.2.9; pin specific, test before update), python-Levenshtein (optional, graceful degradation). Documents the vuln-response posture (Dependabot security PRs, `pip-audit` CI gate, quarterly review per GOVERNANCE §3). **No packages installed** (phase no-op per RESEARCH Package Legitimacy Audit).
- Optional tightening applied to `.github/dependabot.yml`: added a `groups: security: { applies-to: security-updates, patterns: ["*"] }` block to all three pip ecosystems, keeping every existing entry. Validated as valid YAML (`yaml.safe_load` → `ok`).

### Task 3 — SEC-05 accepted-risk register
`docs/security/SEC-05-accepted-risk-register.md`. Classifies **every** CONCERNS.md item across Tech Debt, Known Bugs, Security, Performance, Fragile Areas, Scaling Limits, Missing Features, Test Coverage Gaps into `must-fix-done` (Phase 1 fixes: IDOR oid, OBO 503, redaction, audit-trail seam, single-instance pin) vs `accepted-deferred` (symlink hardening, broad-except sweep, JWKS SWR, Fabric fallback/circuit-breaker, fuzzy O(n) index, in-memory scaling, missing features, test gaps). Each row: Item | Catégorie | Disposition | Justification | Source. The "no-WORM" audit-trail caveat (SECURITY_POSTURE §7) is carried as a dedicated accepted-risk row **flagged for DPO confirmation**. States explicitly that no accepted-deferred item is launch-blocking.

## Verification

Plan structural greps (PowerShell Select-String + grep) — all pass:
- SEC-03: simple-match count 15 (≥4 required); `LLM0` rows 16 (≥5); evidence refs `tests/|GUARDRAILS|validate_copilot|schemas/` = 25; `STRIDE` + `SEC-03` present.
- SEC-04: simple-match count 18 (≥4); `dependabot.yml` refs 5; `PyJWT` + `deltalake` present; `.github/dependabot.yml` parses as valid YAML (`ok`).
- SEC-05: simple-match count 45 (≥3); `accepted-deferred` 31 (≥3); `must-fix-done` present; `IDOR|symlink|WORM` matches 9; `SEC-05` present.

## Deviations from Plan

None — plan executed exactly as written. The optional `groups` tightening of `.github/dependabot.yml` was applied (explicitly offered by the plan as optional) and the file remains valid YAML; all pre-existing entries preserved.

## Known Stubs

None. All three documents are fully populated evidence docs sourced from existing repo artifacts; no placeholder/empty values.

## Threat Flags

None — these are documentation deliverables; they introduce no new network endpoint, auth path, file-access pattern, or schema change at a trust boundary. SEC-03/04/05 document the existing threat surface rather than adding to it.

## Self-Check: PASSED

Files created (verified present):
- FOUND: docs/security/SEC-03-threat-coverage-matrix.md
- FOUND: docs/security/SEC-04-dependency-posture.md
- FOUND: docs/security/SEC-05-accepted-risk-register.md
- FOUND (modified): .github/dependabot.yml (valid YAML)

No per-task commits in this executor session (orchestrator verifies + commits per the plan's session contract).
