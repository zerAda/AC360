---
phase: 02-production-infrastructure-provisioning
plan: 04
subsystem: infra
tags: [bicep, flex-consumption, app-service, document-intelligence, iac, compute-tier]
requires:
  - "02-01: prod.parameters.json declares funcMaxInstanceCount/funcInstanceMemoryMB/funcRuntimeVersion/deploymentContainerName/docIntelLocation; offline validate_infra.ps1"
provides:
  - "infra/main.bicep prod compute tier: B1 gateway (capacity=1, Always On), FC1 Flex functions (functionAppConfig), S0 DocIntel"
  - "New staging-safe Bicep params: funcMaxInstanceCount, funcInstanceMemoryMB, funcRuntimeVersion, deploymentContainerName, docIntelLocation"
  - "Resolved Open Q2: Microsoft.Web/sites@2023-12-01 accepts functionAppConfig (no apiVersion bump needed)"
affects:
  - "02-05: completes Flex storage auth (AzureWebJobsStorage__* MI app settings), Durable role trio, Cognitive Services User role, GRS storage + blobServices, KV private endpoint"
tech-stack:
  added: []
  patterns:
    - "Flex Consumption functionAppConfig (deployment.storage blobContainer via SystemAssignedIdentity, scaleAndConcurrency, runtime)"
    - "Every prod behavior is a new Bicep param defaulting to the staging value (staging-safe parameterization)"
key-files:
  created: []
  modified:
    - "infra/main.bicep"
decisions:
  - "Microsoft.Web/sites@2023-12-01 already accepts functionAppConfig — NO bump to 2024-04-01 required (Open Q2 closed)"
  - "Flex functionApp drops linuxFxVersion (runtime now in functionAppConfig); gateway keeps Python|3.12 (not Flex)"
  - "Flex storage auth wiring (AzureWebJobsStorage__* MI app settings) deliberately deferred to 02-05 to keep this file compiling"
metrics:
  duration: 28
  completed: "2026-06-14"
  tasks: 3
  files: 1
---

# Phase 02 Plan 04: Production Compute Tier (B1 gateway / FC1 Flex / S0 DocIntel) Summary

Extended `infra/main.bicep` in place with the production compute tier — B1 App Service gateway with explicit `capacity=1` + Always On (AUD-04 single-instance pin now landed), a new Flex Consumption (FC1) Functions app with a `functionAppConfig` block (blobContainer deployment via SystemAssignedIdentity, scale/concurrency, Python 3.12 runtime), and Document Intelligence promoted to S0 — all parameterized so `staging.parameters.json` keeps compiling.

## What Was Built

- **Task 1 — apiVersion build-check (Open Q2):** Added a minimal `functionAppConfig` stub to `functionApp` on the existing `Microsoft.Web/sites@2023-12-01` and ran `az bicep build`. It exits 0 — `2023-12-01` accepts `functionAppConfig`, so **no apiVersion bump to 2024-04-01 was needed**. Existing hardening (`httpsOnly`, `minTlsVersion`, `ftpsState`, `ipSecurityRestrictions`) untouched. Commit `77902bf`.
- **Task 2 — Gateway B1 + capacity=1 + Always On (INF-02):** `gwPlan.sku` changed from `{ name: 'F1', tier: 'Free' }` to `{ name: 'B1', tier: 'Basic', capacity: 1 }` (the D-AUD-04 Phase-1-deferred explicit pin, which F1/Free refused). Added `alwaysOn: true` to `gatewayApp.siteConfig`. The AUD-04 LOAD-BEARING comment block and the `gunicorn --workers 1` appCommandLine + its load-bearing comment are preserved verbatim. Only the inline note on the sku line was updated to state the pin is now landed on B1. No `autoscaleSettings` resource targets `gwPlan`. Commit `de42e09`.
- **Task 3 — FC1 Flex functions + S0 DocIntel + staging-safe params (INF-03/04):** Declared 5 new params (defaults = staging shape): `funcMaxInstanceCount=40`, `funcInstanceMemoryMB=2048` (`@allowed([512,2048,4096])`), `funcRuntimeVersion='3.12'`, `deploymentContainerName='app-package'`, `docIntelLocation=location`. `funcPlan.sku` Y1/Dynamic → FC1/FlexConsumption (keeps `reserved:true`). `functionApp`: removed `linuxFxVersion` (Flex-incompatible), kept `minTlsVersion`/`ftpsState`/`ipSecurityRestrictions`/identity/`httpsOnly`, added the full `functionAppConfig` (deployment.storage blobContainer = `${storage...blob}${deploymentContainerName}` with `authentication.type='SystemAssignedIdentity'`; scaleAndConcurrency; runtime python `funcRuntimeVersion`). DocIntel `F0` → `S0`, `location` → `docIntelLocation`. Commit `4b17b56`.

## Verification

| Gate | Result |
|------|--------|
| `az bicep build -f infra/main.bicep` (default/staging params) | exits 0 |
| Compiled ARM: FC1 plan, tier FlexConsumption | present |
| functionAppConfig: auth=SystemAssignedIdentity, runtime=funcRuntimeVersion, scaleAndConcurrency | present |
| functionApp linuxFxVersion | absent (Flex-correct); gateway keeps `Python\|3.12` |
| docIntel sku | S0 |
| Gateway: B1, capacity=1, alwaysOn=true, `--workers 1` | all present |
| No `autoscaleSettings`/`Microsoft.Insights` resource targets gwPlan | confirmed (only comment references) |
| AUD-04 comment block + gunicorn appCommandLine | preserved verbatim |

## Deviations from Plan

None — plan executed exactly as written. Open Q2 resolved in the favorable direction (no apiVersion bump needed), so Task 1 made no apiVersion change.

## Expected validator state (not a failure)

`scripts/validate_infra.ps1` now fails-closed (12 violations) because a B1 plan is present, which arms the per-INF assertions. This is **expected** at this point in the phase sequence:

- **Out-of-scope until 02-05:** all INF-09 (storage GRS, `allowSharedKeyAccess=false`, blobServices retention/PITR/versioning/changeFeed, `AzureWebJobsStorage__credential=managedidentity`), INF-08 (KV private endpoint + `privatelink.vaultcore.azure.net` DNS zone), INF-07 (Durable storage role trio + Cognitive Services User). The plan explicitly defers identity-based AzureWebJobsStorage app settings and the role trio to 02-05.
- **Static-analysis false negatives (staging-safe params working as designed):** `INF-03 runtime.version != '3.12' (= [parameters('funcRuntimeVersion')])` — the validator reads the unresolved ARM expression, not the default `'3.12'`; and `INF-04 disableLocalAuth != true` — `docIntelDisableLocalAuth` defaults to `false` (staging) and is `true` only under prod params. Both confirm the staging-safe parameterization (every prod behavior is a param defaulting to the staging value). The validator is designed to pass only once the full prod shape (through 02-05) is compiled with prod params.

The authoritative gate for this plan — `az bicep build` exit 0 — passes.

## Flex storage auth note (carried to 02-05)

The Flex app's `functionAppConfig.deployment.storage.authentication.type` is `SystemAssignedIdentity` (no connection string), but the runtime AzureWebJobsStorage identity wiring (`AzureWebJobsStorage__accountName` / `AzureWebJobsStorage__credential=managedidentity` app settings) and the Durable storage RBAC trio are completed in plan 02-05. This file compiles green without them.

## Self-Check: PASSED

- infra/main.bicep: FOUND (modified)
- Commit 77902bf: FOUND
- Commit de42e09: FOUND
- Commit 4b17b56: FOUND
- .planning/phases/02-production-infrastructure-provisioning/02-04-SUMMARY.md: FOUND
