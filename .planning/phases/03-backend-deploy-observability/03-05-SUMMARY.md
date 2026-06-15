---
phase: 03-backend-deploy-observability
plan: 05
subsystem: ops / runbooks
tags: [runbooks, operability, solo-operator, deploy, rollback, secret-rotation, incident-triage, kill-switch, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05]
dependency_graph:
  requires:
    - ".github/workflows/cd-prod.yml (Plan 03-04 — the pipeline the deploy/rollback runbooks drive)"
    - "infra/observability.bicep alerts (Plan 03-03 — the alert rows of the triage tree)"
    - "scripts/feature_flags.py hash_id + AC360_* env-vars (kill-switch mechanism)"
    - "docs/production/EMERGENCY_SHUTDOWN_RUNBOOK.md (house style + cross-link target)"
    - "Phase-2 02-06-SUMMARY operator checkpoints (folded into the deploy runbook)"
  provides:
    - "docs/production/runbooks/01-deploy.md — OPS-01 deploy runbook (pipeline + OIDC federated-cred + GitHub Environment + MI/KV verification + gatewayOutboundIps arming)"
    - "docs/production/runbooks/02-rollback.md — OPS-02 <10-min tag-redeploy rollback (no B1 slots)"
    - "docs/production/runbooks/03-secret-rotation.md — OPS-03 per-secret rotation incl. OBO app-reg + expiry tracking"
    - "docs/production/runbooks/04-incident-triage.md — OPS-04 alert→cause→first-action decision tree"
    - "docs/production/runbooks/05-killswitch.md — OPS-05 feature-flag kill-switch cross-linking the emergency runbook"
  affects:
    - "Go-live / operations: the operability layer that lets ONE person run AC360 in production"
tech_stack:
  added: []
  patterns:
    - "House runbook style (EMERGENCY_SHUTDOWN_RUNBOOK.md): title + > Objectif: blockquote + ## Principe + numbered ## Procédure (powershell az-CLI, backtick continuation, -g rg-ac360-prod) + ## Vérifications post-action table"
    - "Every runbook carries an offline-exercisable ## Dry-run / validation section"
    - "Secrets/PII never embedded: placeholders (<ORG>/<REPO>, <hash>, OBO-CLIENT-SECRET name) + hash_id for user blocking (T-03-17)"
key_files:
  created:
    - docs/production/runbooks/01-deploy.md
    - docs/production/runbooks/02-rollback.md
    - docs/production/runbooks/03-secret-rotation.md
    - docs/production/runbooks/04-incident-triage.md
    - docs/production/runbooks/05-killswitch.md
  modified: []
decisions:
  - "OPS-01 / Open Q1 / Pitfall 5 RESOLVED: TWO federated credentials — deploy job subject :environment:production, whatif job subject :ref:refs/tags/prod-* (what-if runs outside the production Environment to keep the diff visible before approval). Alternative (fold what-if into the gated job) rejected — it would hide the diff before approval."
  - "Rollback = tag-redeploy, NOT slot-swap: B1 has no deployment slots (slots need S1+, which breaks the AUD-04 single-instance pin); the known-good marker is the previous immutable prod-* git tag re-run via cd-prod.yml workflow_dispatch."
  - "OIDC deployment has NO secret to rotate — recorded as an OIDC benefit row in the secret-rotation table (T-03-20)."
metrics:
  duration: "~15 min"
  completed: "2026-06-15"
  tasks_completed: 2
  tasks_total: 3
  files_created: 5
  files_modified: 0
---

# Phase 03 Plan 05: Solo-Operator Runbooks (OPS-01..05) Summary

Five solo-operator runbooks under `docs/production/runbooks/`, authored in the house
decision-tree style (analog: `EMERGENCY_SHUTDOWN_RUNBOOK.md`), each carrying an
offline-exercisable `## Dry-run / validation` section — the operability layer that lets
ONE person deploy, roll back, rotate secrets, triage incidents, and kill-switch AC360 in
production. The full live execution of each runbook against the live prod stack is
recorded as a deferred operator checkpoint (Task 3).

## What Was Built

- **`docs/production/runbooks/01-deploy.md`** (OPS-01) — the deploy flow via `cd-prod.yml`
  PLUS the operator-only prerequisites intentionally kept out of the YAML: GitHub
  `production` Environment + required reviewer; the 3 OIDC secrets (`AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID`,
  no SP password); `az ad app federated-credential create` with subject
  `repo:<ORG>/<REPO>:environment:production` AND the second credential for the what-if job
  (`:ref:refs/tags/prod-*`) — the resolved OPS-01 / Pitfall 5 decision; least-privilege
  Contributor on `rg-ac360-prod` only; the folded-in Phase-2 02-06 operator checkpoints
  (EU residency, what-if evidence, OBO admin consent, Fabric grant); the post-first-deploy
  `gatewayOutboundIps` arming step; and a MI / Key-Vault-reference verification table
  (OBO_CLIENT_SECRET + App Insights conn-string resolve, not the `@Microsoft.KeyVault` literal; `/ready` keyvault_ref ok).
- **`docs/production/runbooks/02-rollback.md`** (OPS-02) — `<10-min` rollback = re-run
  `cd-prod.yml` (workflow_dispatch `ref`) against the previous known-good `prod-YYYYMMDD-N`
  git tag; explicit trigger table (sustained 5xx, failed `/health` webtest, stuck `/ready` 503,
  broken Flex deploy); explicit "B1 has NO slots (slots need S1+ → breaks AUD-04)" statement;
  timed `<10-min` verification (`/health` 200 + `/ready` ready).
- **`docs/production/runbooks/03-secret-rotation.md`** (OPS-03) — per-secret table
  (`OBO-CLIENT-SECRET`, `AZURE_OCR_KEY`, Fabric creds, and the OIDC "no secret to rotate"
  benefit row) with rotation steps; the OBO procedure includes the app-registration reset
  (`az ad app credential reset`) → Key Vault `OBO-CLIENT-SECRET` set → app restart → KV-reference
  resolution + OBO smoke; an expiry-tracking table (last rotation / expires / next rotation).
- **`docs/production/runbooks/04-incident-triage.md`** (OPS-04) — `alert → likely cause →
  first action` decision tree as a markdown table covering the four Plan-03 alert types
  (gateway 5xx `gw5xx`; dependency `depFail` OCR/Fabric/Graph; Functions/orchestration
  `funcErr`/`func5xx`; `/health` availability webtest) plus the budget alert; workbook
  one-pane as the first place to look; cross-references runbooks 02 / 03 / 05 as escalations.
- **`docs/production/runbooks/05-killswitch.md`** (OPS-05) — the feature-flag kill-switch
  (`AC360_*_ENABLED`, `AC360_BLOCKED_USERS_HASHED`, `AC360_BLOCKED_TEAMS`) with
  `az webapp config appsettings set -g rg-ac360-prod` commands to disable audit/OCR/RAG or
  block a user/team instantly; `hash_id` step for blocking a user (no cleartext UPN);
  explicit cross-link to `docs/production/EMERGENCY_SHUTDOWN_RUNBOOK.md`; no-redeploy /
  reversible / traced guarantees.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | deploy + rollback + secret-rotation runbooks | (sequential — see git log) | 01-deploy.md, 02-rollback.md, 03-secret-rotation.md |
| 2 | incident-triage + kill-switch runbooks | (sequential — see git log) | 04-incident-triage.md, 05-killswitch.md |

> Sequential-executor note: per the session directive, false-negative `commit_failed`
> from the SDK is expected on this OneDrive Windows path; the commit HASH is authoritative
> via `git show --stat`. The five runbook files are the load-bearing deliverable and are
> present on disk.

## Verification

Offline (the directive's structural-grep fallback, since `pymarkdown` requires a live pip install):

- All five files exist under `docs/production/runbooks/`.
- `## Dry-run` present in all five (`grep -l "## Dry-run"` → 5 files).
- `01-deploy.md`: `federated-credential` (2), `environment:production` (8) — OPS-01 prerequisites + resolved Pitfall-5 decision.
- `02-rollback.md`: `prod-` (11), `slot` (7 — the no-slots-on-B1 statement).
- `03-secret-rotation.md`: `OBO-CLIENT-SECRET` (8) + expiry-tracking table present.
- `04-incident-triage.md`: `alert/cause/action` columns (26 hits); the four Plan-03 alert types referenced.
- `05-killswitch.md`: `AC360_OCR_ENABLED`/`AC360_BLOCKED_USERS_HASHED` (8), `EMERGENCY_SHUTDOWN_RUNBOOK` cross-link (2), `rg-ac360-prod` (8 — prod, not staging).
- House style preserved: each file is `# AC360 — <titre> (OPS-0N)` + `> Objectif :` + `## Principe` + numbered `## Procédure` (powershell az-CLI, backtick continuation, `-g rg-ac360-prod`) + `## Vérifications post-action` table.

## Deferred Operator Checkpoint (Task 3 — full live runbook execution)

Per the session checkpoint handling, Task 3 (`checkpoint:human-verify`, gate="blocking") was
NOT paused on. The runbooks were authored fully with their offline dry-run/validation
sections; the full live execution against the live prod stack is recorded here as a deferred
operator checkpoint (CONTEXT execution boundary — depends on Phase-2 live infra + the first
live deploy from Plan 04). **No live prod actions were performed this session.**

Operator must execute each runbook once against live prod:

1. **01-deploy** — run a real deploy via `cd-prod.yml` end-to-end (covered by Plan 04 Task 2);
   confirm the MI / Key-Vault-reference verification steps pass live.
2. **02-rollback** — roll back to a previous `prod-*` tag and time it (`<10-min` target);
   confirm `/health` 200 + `/ready` ready after rollback.
3. **03-secret-rotation** — rotate at least `OBO-CLIENT-SECRET` once (app-reg secret → Key
   Vault → confirm KV reference resolves) and record the new expiry date in the tracking table.
4. **04-incident-triage** — walk the tree against one real (or synthetically triggered) alert
   and confirm the first-action step is correct.
5. **05-killswitch** — toggle one feature flag (e.g. `AC360_OCR_ENABLED=false` then `true`)
   live and confirm the effect (audit 403 while off, `/health` stays 200).

**Resume signal:** Operator types "approved" once each runbook has been executed once against
live prod (deploy; rollback timed `<10-min`; OBO secret rotated; triage walked; one flag
toggled); or describes which runbook step failed for gap-closure.

## Deviations from Plan

None — both autonomous tasks executed exactly as written. The `pymarkdown` lint step
(Task 1/2 `<verify>`) requires a live `pip install pymarkdownlnt` not available in this
session; the directive's offline structural-grep fallback (each file exists + contains the
required sections/markers) was used instead, and all acceptance greps pass. The runbooks
follow the well-formed analog (`EMERGENCY_SHUTDOWN_RUNBOOK.md`) structure (ATX headings,
fenced code blocks, GFM tables) so they are expected to lint clean once the operator runs
pymarkdown with `--disable-rules MD013,MD024,MD033,MD041`.

## Threat Flags

No new security surface beyond the plan's `<threat_model>`. The runbooks use placeholders
(`<ORG>/<REPO>`, `<hash>`, `OBO-CLIENT-SECRET` name only) and `hash_id` for user blocking —
no live secrets or cleartext UPNs embedded (T-03-17 honored). Rollback targets immutable
`prod-*` tags (T-03-19); the secret-rotation expiry table mitigates silent-expiry outage
(T-03-20); kill-switch/rotation mutations are admin-only and traced (T-03-18).

## Self-Check: PASSED

- docs/production/runbooks/01-deploy.md — FOUND
- docs/production/runbooks/02-rollback.md — FOUND
- docs/production/runbooks/03-secret-rotation.md — FOUND
- docs/production/runbooks/04-incident-triage.md — FOUND
- docs/production/runbooks/05-killswitch.md — FOUND
- .planning/phases/03-backend-deploy-observability/03-05-SUMMARY.md — FOUND
- All five runbooks contain `## Dry-run` — CONFIRMED (grep -l → 5 files)
- Commits: sequential-executor path — HASH authoritative via `git show --stat` (SDK commit_failed is a known false-negative on this OneDrive Windows path per the session directive)
