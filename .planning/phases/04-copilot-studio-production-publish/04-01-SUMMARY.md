---
phase: 04-copilot-studio-production-publish
plan: 01
subsystem: copilot-studio-guardrails
tags: [pub-02, pub-04, ci-gate, validator, staging-cutover, tdd]
requires:
  - scripts/validate_copilot_yaml.py (existing CI gate)
  - src/copilot/AC360/settings.mcs.yml (existing guardrail config)
provides:
  - find_agent_guardrail_issues (offline PUB-04 assertion)
  - staging-host fail-closed branch in find_wiring_issues (PUB-02)
  - prod gateway URLs across the 4 topic files (cutover)
affects:
  - .github/workflows/ci.yml (validator gate now enforces 3 new assertions)
tech-stack:
  added: []
  patterns: [extend-not-replace CI gate, Wave-0 RED-first TDD, fail-closed host check]
key-files:
  created:
    - tests/backend/test_validate_copilot_yaml.py
  modified:
    - scripts/validate_copilot_yaml.py
    - src/copilot/AC360/topics/LancerAudit.mcs.yml
    - src/copilot/AC360/topics/StatutAudit.mcs.yml
    - src/copilot/AC360/topics/GenererFicheRDV.mcs.yml
    - src/copilot/AC360/topics/CreerRelancePlanner.mcs.yml
decisions:
  - "useModelKnowledge must be explicitly False — absent/None is a CI failure (grounding declared, not implicit)."
  - "Prod API audience GUID/scope NOT hardcoded in topic files — bound in the agent UI per Plan 02 runbook (Open Question 2 LOCKED)."
  - "Staging host folded into the existing find_wiring_issues fail-closed check; CI gate extended, never replaced (CLAUDE.md)."
metrics:
  duration: "~10 min"
  completed: 2026-06-15
  tasks: 3
  files: 6
---

# Phase 04 Plan 01: Copilot Studio Guardrail Gate + Staging→Prod Cutover Summary

Offline CI guardrail gate (PUB-04) and the staging→prod gateway cutover (PUB-02) are now
regression-proof repo facts: the validator fails closed on `useModelKnowledge != false`,
agent `contentModeration != High`, or any residual `ac360-gateway-staging` host, and all 7
gateway URLs now point at `ac360-gateway-prod.azurewebsites.net`.

## What Was Built

- **Task 1 (Wave-0 RED):** `tests/backend/test_validate_copilot_yaml.py` — 7 pytest functions
  importing the validator as `v` (conftest already injects `scripts/`). Covers the not-yet-existing
  `find_agent_guardrail_issues(data, filename)` (useModelKnowledge / contentModeration, and the
  non-settings-file no-op) plus the staging-host branch of `find_wiring_issues`. Intended RED:
  `find_agent_guardrail_issues` and the staging check did not exist when the test was written.

- **Task 2 (GREEN):** extended `scripts/validate_copilot_yaml.py`:
  - New constants `SETTINGS_FILE`, `PROD_GATEWAY_HOST`, `STAGING_GATEWAY_HOST`.
  - `find_agent_guardrail_issues(data, filename)` — returns `[]` unless `filename == SETTINGS_FILE`;
    reads `configuration.aISettings`; flags `useModelKnowledge is not False` (missing/None = fail)
    and `contentModeration != RAG_REQUIRED_MODERATION` ("High", reused).
  - `STAGING_GATEWAY_HOST` added to the `HttpRequestAction` fail-closed host check (message contains
    "staging").
  - New `guardrail_ko` bucket populated in the per-file loop, a `=== Contrôle garde-fous agent ===`
    print section, and folding into the final `if ko or rag_ko or wiring_ko or moderation_ko or
    guardrail_ko` exit condition. No existing check altered or removed.

- **Task 3 (cutover):** rebound the host substring `ac360-gateway-staging` → `ac360-gateway-prod`
  across the 4 topic files (7 occurrences: LancerAudit ×4 incl. the two interpolated `&`-built status
  URLs, StatutAudit ×1 interpolated, GenererFicheRDV ×1, CreerRelancePlanner ×1). Only the host
  substring changed — paths, `="Bearer " & System.User.AccessToken` headers, interpolation syntax,
  indentation, and node structure preserved verbatim (RESEARCH anti-pattern: no node restructuring;
  no prod audience GUID hardcoded).

## Static verification (offline, tool-confirmed)

- `grep ac360-gateway-staging src/copilot` → 0 matches (Grep tool confirmed).
- `grep ac360-gateway-prod.azurewebsites.net src/copilot/AC360/topics` → 7 matches across 4 files
  (LancerAudit 4, StatutAudit 1, GenererFicheRDV 1, CreerRelancePlanner 1) — Grep tool confirmed.
- Test↔validator contract traced by hand: all 7 tests resolve GREEN against the implemented logic
  (see Deferred Verification for why pytest was not executed here).

## Deviations from Plan

None — plan executed exactly as written (extend-not-replace, value-only host edits, no audience GUID).

## Deferred Verification (REQUIRES a shell — not executable in this executor session)

This executor session had no Bash/shell tool available (only Read/Write/Edit/Grep/Glob). The
following plan acceptance steps and the per-task + final commits could not be run here and MUST be
executed by an operator or a shell-capable run before this plan is considered closed:

1. `set TENANT_ID=test_tenant & set CLIENT_ID=test_client & set PYTHONPATH=scripts &
   python -m pytest tests/backend/test_validate_copilot_yaml.py -x` → expect exit 0 (GREEN).
2. `python scripts/validate_copilot_yaml.py` → expect exit 0 on the hardened+rebound repo.
3. `python -m pytest` (full suite) → expect green (no regression from the new file/symbols).
4. Per-task atomic commits (RED test / GREEN validator / cutover) and the final docs commit
   (SUMMARY.md, STATE.md, ROADMAP.md), plus `gsd-tools` STATE.md / ROADMAP.md / REQUIREMENTS.md
   updates (state.advance-plan, state.update-progress, state.record-metric, roadmap.update-plan-progress,
   requirements.mark-complete PUB-02 PUB-04).

All code changes are on disk and complete; only execution/commit of the above remains.

## Self-Check: PASSED (file-existence + content)

- FOUND: tests/backend/test_validate_copilot_yaml.py (7 tests, imports validate_copilot_yaml as v)
- FOUND: scripts/validate_copilot_yaml.py contains find_agent_guardrail_issues + guardrail_ko + STAGING_GATEWAY_HOST
- FOUND: 7 prod URLs / 0 staging URLs under src/copilot (Grep-confirmed)
- NOTE: commit-hash verification deferred — commits not made in this session (no shell tool).
