---
phase: 04-copilot-studio-production-publish
plan: 02
status: complete (artifacts) — live actions deferred to operator
completed: 2026-06-14
requirements: [PUB-01, PUB-02, PUB-03, PUB-04, PUB-05]
---

# Plan 04-02 Summary — Publish Runbook + Guardrails Evidence

**Note:** authored inline by the orchestrator after the executor subagent died on a stream-idle timeout (no partial work on disk).

## What landed

- **`docs/production/runbooks/06-copilot-publish.md`** — solo-operator publish runbook: prerequisite gate (Phase 2/3 live), EU env confirm (PUB-01), solution import + connection-reference rebind to prod + action endpoint = prod gateway URL + `<PROD_API_AUDIENCE_SCOPE>` placeholder (PUB-02), **"Authenticate manually" (Entra ID V2) + Teams SSO** with the explicit rationale that this is the ONLY mode exposing `System.User.AccessToken` for the gateway Bearer — "Authenticate with Microsoft" documented as the rejected anti-pattern (PUB-03), **1:1 personal install** with channel scope OFF and the OBO/SharePoint-RAG 1:1 rationale (PUB-05), live acceptance tests (1:1 sign-in no-repeat-prompt, known-blocked-prompt, OBO scope), a `## Dry-run / validation` offline section, rollback, and an evidence-capture list. Microsoft Learn URLs cited throughout.
- **`docs/security/GUARDRAILS_VALIDATION.md`** — evidence doc feeding Phase 5 (SEC-03/SEC-04): the **offline** proof (useModelKnowledge=false + agent contentModeration=High in settings.mcs.yml, uniform High RAG, validator exit 0, no staging host — all CI-gated and unit-tested) plus a **live** evidence slot (known-blocked-prompt, grounded-only, OBO scoping, no-PII telemetry) for the operator post-publish.

## Operator checkpoints (deferred — recorded)

Live publish, EU-env confirmation, manual-Entra-V2 + Teams SSO reconfig, 1:1 install, and the known-blocked-prompt test require the live GEREP tenant + Power Platform/Teams admin (and Phase 2/3 live). Procedure + acceptance + evidence-capture are in the runbook and GUARDRAILS_VALIDATION.md §2.

## Verification (offline)

- `python scripts/validate_copilot_yaml.py` exit 0; `pytest tests/backend/test_validate_copilot_yaml.py -x` green (from 04-01); full suite 211 passed / 1 skipped.
- Both runbook + evidence doc present; runbook has a `## Dry-run / validation` section; no `<PROD_API_AUDIENCE_SCOPE>` GUID hardcoded.

## Requirements

PUB-02 + PUB-04 offline parts landed in 04-01; PUB-01/03/05 artifacts (runbook + checklists) delivered here, live execution deferred to operator. All recorded in the Phase 4 verification + a STATE blocker.
