---
phase: 03-backend-deploy-observability
plan: 04
subsystem: ci-cd / deployment
tags: [cd, github-actions, oidc, bicep-what-if, environment-approval, flex-functions, supply-chain, CD-01, CD-02]
dependency_graph:
  requires:
    - "infra/main.bicep + infra/prod.parameters.json (Phase 02 baseline; deploy target)"
    - "infra/budget.bicep + main.bicep actionGroupId output (Plan 03-03 — subscription-scoped budget sub-deploy)"
    - "OPERATOR (deferred): Phase-2 live infra in rg-ac360-prod; GitHub production Environment + reviewer; AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID secrets; Entra federated credentials"
  provides:
    - ".github/workflows/cd-prod.yml — gated OIDC production CD pipeline (build -> whatif -> deploy)"
  affects:
    - "Plan 03-05 deploy runbook (docs/production/runbooks/01-deploy.md) — owns the operator-only OIDC/Environment/federated-credential setup referenced from the YAML header"
tech_stack:
  added:
    - "GitHub Actions: azure/login@v2 (OIDC federated, no stored SP secret)"
    - "azure/webapps-deploy@v3 (gateway App Service B1)"
    - "Azure/functions-action@v1 remote-build:true (Functions Flex — One Deploy)"
    - "azure/cli@v2 (Bicep what-if gate + RG-scoped apply + subscription-scoped budget sub-deploy)"
    - "actions/checkout@v4, actions/setup-python@v5, actions/upload-artifact@v4, actions/download-artifact@v4"
  patterns:
    - "OIDC over stored secrets (id-token: write; T-03-13 mitigation — no long-lived deploy secret)"
    - "what-if diff gate as a separate pre-approval job (needs: build) before the gated deploy job"
    - "production GitHub Environment manual reviewer as the unreviewed-deploy gate (T-03-15)"
    - "subscription-scoped budget via separate `az deployment sub create` (Pitfall 4 — not in RG-scoped main.bicep apply)"
    - "Flex remote-build:true with NO Kudu/Oryx build flags (Pitfall 1)"
    - "first-party actions pinned to major tags (supply-chain T-03-SC)"
key_files:
  created:
    - .github/workflows/cd-prod.yml
  modified: []
decisions:
  - "what-if kept as a SEPARATE pre-approval job (preserves diff visibility before manual approval) rather than folding it into the gated deploy job — Pitfall 5 / OPS-01: the what-if job runs outside the production Environment so it carries a different OIDC subject and needs its own federated credential (documented in the YAML header + deferred to Plan 05 runbook)."
  - "Budget sub-deploy reads actionGroupId from main.bicep outputs at deploy time (az deployment group show ... outputs.actionGroupId.value) and passes it into budget.bicep's actionGroupId param; amount=200 / alertEmails=[] mirror prod.parameters.json (operator confirms alertEmails in Plan 05)."
  - "Functions ship SOURCE (not a pre-built package) because Flex uses Oryx remote build; only the gateway is zipped (dist/gateway.zip)."
metrics:
  duration: "~12 min"
  completed: 2026-06-14
  tasks_completed: 1
  tasks_total: 2
  files_created: 1
  files_modified: 0
---

# Phase 03 Plan 04: Production CD Pipeline (cd-prod.yml) Summary

Greenfield gated OIDC production CD pipeline (`build -> what-if diff gate -> production-Environment-approved deploy`) that applies `main.bicep`, sub-deploys the subscription-scoped budget, and deploys the gateway (App Service B1) plus Functions (Flex remote build) — with the first live run captured as a deferred operator checkpoint.

## What Was Built

`.github/workflows/cd-prod.yml` — a structurally complete, lint-clean production CD workflow:

- **Triggers:** `push: tags: ['prod-*']` (immutable rollback marker — OPS-02) + `workflow_dispatch.inputs.ref` (deploy/rollback to a Tag/SHA).
- **`permissions: { id-token: write, contents: read }`** — OIDC token fetch (CD-01).
- **Job `build`** — checkout@v4, setup-python@v5 (3.12, pip cache), zips the gateway (`dist/gateway.zip`), uploads `deploy-artifacts` (gateway zip + Functions SOURCE for remote build + infra).
- **Job `whatif`** (`needs: build`) — azure/login@v2 (OIDC), `az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json | tee whatif.txt`, diff appended to `$GITHUB_STEP_SUMMARY` (the GATE — diff visible before approval).
- **Job `deploy`** (`needs: whatif`, `environment: production` manual reviewer gate) — download-artifact@v4, azure/login@v2 (OIDC), `az deployment group create` (main.bicep), captures `actionGroupId` output, a SEPARATE `az deployment sub create -f infra/budget.bicep` (subscription-scoped — Pitfall 4), `azure/webapps-deploy@v3` (gateway), `Azure/functions-action@v1 remote-build:true` (Functions Flex, no Kudu/Oryx flags), and a post-deploy step-summary with /health + /ready live checks.
- **Header comment block** lists the operator-only prerequisites intentionally kept OUT of the YAML, pointing to `docs/production/runbooks/01-deploy.md` (Plan 05).

Resource names confirmed against `infra/main.bicep` (`funcName = ac360-func-prod`, `gatewayName = ac360-gateway-prod`, RG `rg-ac360-prod`, location `francecentral`) and `infra/prod.parameters.json` / `infra/budget.bicep` param names (`amount`, `actionGroupId`, `alertEmails`).

## Verification

Offline, all from the plan's acceptance criteria:

- `yamllint -d relaxed .github/workflows/cd-prod.yml` → exit 0 (only relaxed line-length warnings).
- `python yaml.safe_load(..., encoding='utf-8')` → OK (valid YAML; cp1252 console default tripped on emoji bytes — encoding artifact, not a YAML error).
- Structural greps: `id-token: write` (1), `environment: production` (1), `what-if` (in `whatif` job that `needs:`-precedes `deploy`), `azure/webapps-deploy@v3` (1), `Azure/functions-action@v1` (1), `remote-build: true` (1), `scm-do-build-during-deployment|enable-oryx-build` (**0**), `az deployment sub create` (1 step + budget), `azure/login@v2` (2), stored SP password/secret (**0** — only AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID referenced).

## Deferred Operator Checkpoint (Task 2 — NOT executed this session)

Task 2 (`checkpoint:human-verify`, first live prod deploy) is the CONTEXT-locked execution boundary: it depends on Phase-2 live infra plus operator-only GitHub/Entra setup that cannot exist yet. Per the session's checkpoint handling, the YAML was authored fully and the operator steps are recorded here (and in the YAML header) for the Plan 05 deploy runbook. **No live deploy was performed.**

Operator prerequisites before the first live run (→ `docs/production/runbooks/01-deploy.md`, OPS-01):

1. Phase-2 infra provisioned live in `rg-ac360-prod`.
2. Create the GitHub `production` Environment with a **required reviewer** (manual approval gate for the `deploy` job).
3. Create 3 GitHub repo/Environment secrets (OIDC — no SP password): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
4. Create Entra federated credential for the **deploy** job: subject `repo:<ORG>/<REPO>:environment:production`.
5. Create a **second** federated credential for the **whatif** job (it runs outside the `production` Environment, so its OIDC subject differs — Pitfall 5 / OPS-01 decision). Resolve the exact subject (tag/PR) in Plan 05.
6. Grant the deploy identity a **least-privilege** role on `rg-ac360-prod` only (Contributor on the RG, not subscription Owner; T-03-14) — plus a subscription-scoped assignment sufficient for the budget sub-deploy.

Live verification (when run): push a `prod-YYYYMMDD-N` tag → confirm what-if diff posted → approve the `production` gate → confirm main.bicep apply + budget sub-deploy + gateway + Functions Flex deploy (no `ModuleNotFoundError`) → confirm `GET /health` 200 and `GET /ready` over Entra-gated TLS (200/503).

## Deviations from Plan

None — plan executed exactly as written. The single deviation from the RESEARCH Code Example 1 sketch is the budget `actionGroupId` wiring: the example did not show it, but the plan's `<action>` explicitly required reading the `actionGroupId` output from main.bicep and passing it into the budget sub-deploy (implemented as `az deployment group show ... outputs.actionGroupId.value`).

## Self-Check: PASSED
