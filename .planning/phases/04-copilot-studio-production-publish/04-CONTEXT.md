# Phase 4: Copilot Studio Production Publish - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Publish the hardened AC360 Copilot Studio agent to Teams for the target team as a 1:1 personal install, pointed at the live prod gateway, with SSO reconfigured and live guardrails validated against the repo. Covers PUB-01..05.

**Execution boundary (milestone decision):** Copilot Studio publish, EU-environment confirmation, Teams SSO reconfiguration, and the 1:1 Teams install are **operator UI actions** (not scriptable / no live tenant this session). This phase produces: a publish runbook, a prod connection-reference config (templated), the **PUB-04 guardrail validation against the repo** (offline-enforceable — the one genuinely autonomous deliverable), a guardrails-validation evidence doc (feeds Phase 5), and operator acceptance checklists. Depends on Phase 2 (prod gateway URL + prod API audience app reg) and Phase 3 (deployed gateway) being live — both pending.

Out of scope: new topics/agent features (stack locked); the actual live publish (operator).

</domain>

<decisions>
## Implementation Decisions

### Publish Execution & Environment (PUB-01, PUB-02)
- Capture the publish as a **runbook** (`docs/production/runbooks/06-copilot-publish.md`) — Copilot Studio publish is UI-driven, not reliably scriptable.
- EU environment confirmation (PUB-01): **operator checkpoint** + recorded in the runbook (Power Platform env region EU verified against the live tenant).
- Connection-reference rebind (PUB-02): a **templated prod `connectionreferences` config** + documented rebind steps; the action endpoint is set to the **prod gateway URL** using the **prod API audience** (from the Phase 2 app registration).
- Publish-UI volatility (carried STATE blocker): **validate the publish checklist against current Microsoft Learn** at execution (research step).

### Guardrails Validation — PUB-04
- **Extend `scripts/validate_copilot_yaml.py`** to assert, offline against the repo `.mcs.yml`: `useModelKnowledge=false`, uniform **High** moderation on RAG nodes, and the validator gate present. This is the autonomous, CI-enforceable deliverable.
- **Live known-blocked-prompt test**: a documented operator test in the runbook (a known-blocked prompt is blocked against the live published agent).
- **Guardrails-validation evidence doc** produced (feeds Phase 5 SEC-03/SEC-04).

### Teams SSO & 1:1 Install (PUB-03, PUB-05)
- SSO reconfig (PUB-03): documented runbook steps (Entra app + Teams manifest SSO) — operator.
- Install scope (PUB-05): **1:1 personal install** — OBO + SharePoint RAG require 1:1 chats (NOT a channel/group bot); document the rationale.
- A **Teams 1:1 sign-in acceptance checklist** (completes without repeated prompts / auth failure) — operator.

### Claude's Discretion
- Runbook structure, the exact validator assertions/messages, and the connection-ref template format are at Claude's discretion, consistent with existing `docs/` + `scripts/validate_copilot_yaml.py` conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/copilot/AC360/` — agent.mcs.yml, connectionreferences.mcs.yml, settings.mcs.yml, topics/, actions/, knowledge/. The connection-ref + guardrail source of truth.
- `scripts/validate_copilot_yaml.py` — existing CI gate (CLAUDE.md) — extend for PUB-04 guardrail assertions.
- `docs/production/runbooks/` — Phase 3 runbook home; add 06-copilot-publish.md.
- Phase 2 prod app registrations (API audience app id) + Phase 3 prod gateway URL — the connection-ref/action endpoint targets.

### Established Patterns
- `.mcs.yml` Copilot Studio config; existing hardening (uniform High moderation on RAG nodes, validator gate, useModelKnowledge=false) is the posture PUB-04 verifies.
- Runbook style (solo-operator, dry-run section) from Phase 3.

### Integration Points
- connection references → prod gateway action endpoint (Phase 3) + prod API audience (Phase 2).
- validate_copilot_yaml.py runs in CI (ci.yml) — PUB-04 assertions gate the pipeline.

### Reference
- Copilot Studio publish UI volatility (MEDIUM confidence, STATE blocker) — validate against current Microsoft Learn at Phase 4 execution.

</code_context>

<specifics>
## Specific Ideas

- The 1:1-personal-install constraint is load-bearing: OBO (user-delegated SharePoint access) and SharePoint RAG only work in 1:1 chats, not channel/group context — document explicitly in the runbook.
- PUB-04 guardrail validation is the bridge to Phase 5: its evidence doc feeds SEC-03 (threat-coverage) and SEC-04.

</specifics>

<deferred>
## Deferred Ideas

- The actual live publish, EU-env confirmation, SSO reconfig, and 1:1 install — operator UI checkpoints (depend on Phase 2/3 live).
- New topics / agent capabilities — out of scope (stack locked).

</deferred>
