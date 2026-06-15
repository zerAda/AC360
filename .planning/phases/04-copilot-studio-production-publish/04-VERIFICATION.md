---
status: human_needed
phase: 04-copilot-studio-production-publish
verified: 2026-06-14
method: inline goal-backward verification (orchestrator) — offline gates green; live publish/SSO/install deferred to operator per the locked execution boundary
requirements: [PUB-01, PUB-02, PUB-03, PUB-04, PUB-05]
gates: "validate_copilot_yaml.py exit 0; pytest test_validate_copilot_yaml.py 7/7; full suite 211 passed/1 skipped; no ac360-gateway-staging in src/copilot; runbook + evidence doc authored"
---

# Phase 4 Verification — Copilot Studio Production Publish

**Phase goal:** The hardened agent is published to Teams for the target team as a 1:1 personal install, pointed at the live prod gateway, with SSO reconfigured and live guardrails validated against the repo.

**Verdict: HUMAN_NEEDED.** The autonomous, repo-side artifacts are complete and offline-verified; the live publish (Copilot Studio + Teams admin UI) is queued as operator checkpoints.

## Offline-verifiable (COMPLETE)

| Req | Evidence | Status |
|-----|----------|--------|
| PUB-02 | 7 `ac360-gateway-staging` URLs rebound to `ac360-gateway-prod.azurewebsites.net` across 4 topic files; `find_wiring_issues` fails closed on any staging host; grep clean | ✅ artifact |
| PUB-04 | `validate_copilot_yaml.py` asserts `useModelKnowledge=false` + agent `contentModeration=High` + uniform High RAG; CI-gated; 7 unit tests; `GUARDRAILS_VALIDATION.md` evidence doc | ✅ artifact |
| PUB-01 | EU-env confirmation procedure in `06-copilot-publish.md` Step 0 | ◷ operator |
| PUB-03 | Manual-Entra-V2 + Teams SSO reconfig procedure (Step 2) — anti-pattern "Authenticate with Microsoft" documented | ◷ operator |
| PUB-05 | 1:1 personal install procedure (Step 3, channel scope OFF, OBO/RAG rationale) | ◷ operator |

Gates: `validate_copilot_yaml.py` exit 0; `pytest tests/backend/test_validate_copilot_yaml.py -x` 7/7; full suite 211 passed/1 skipped; no staging host in `src/copilot`.

## Human verification required (operator — runbook `docs/production/runbooks/06-copilot-publish.md`)

1. Confirm EU prod Power Platform env (PUB-01).
2. Import solution + rebind connection refs + set action endpoint = prod gateway URL + prod API audience (PUB-02 live).
3. Reconfigure **manual Entra V2 + Teams SSO**; republish; 1:1 sign-in completes without repeated prompts (PUB-03).
4. Publish as **1:1 personal install** (channel scope OFF) for the target team (PUB-05).
5. **Known-blocked-prompt** test against the live agent → blocked; record evidence in `GUARDRAILS_VALIDATION.md` §2 (PUB-04 live).

These gate go-live but do not block downstream phases (5: RGPD/Security evidence; 6: E2E/Go-live).
