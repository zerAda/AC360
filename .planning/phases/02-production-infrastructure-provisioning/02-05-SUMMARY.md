---
phase: 02-production-infrastructure-provisioning
plan: 05
subsystem: infra
tags: [bicep, azure, storage, key-vault, private-endpoint, vnet, rbac, managed-identity, durable-functions]

# Dependency graph
requires:
  - phase: 02-01
    provides: prod.parameters.json param declarations (storageSku, enableIdentityStorage, blobSoftDeleteDays, containerSoftDeleteDays, pointInTimeRestoreDays, enablePrivateNetworking)
  - phase: 02-04
    provides: compute section in main.bicep (FC1 functionApp + functionAppConfig, B1 gatewayApp with gunicorn --workers 1, DocIntel S0)
provides:
  - Storage hardening (Standard_GRS via param, allowSharedKeyAccess=!enableIdentityStorage, blobServices child with versioning + changeFeed + blob/container soft-delete + PITR restorePolicy)
  - Identity-based AzureWebJobsStorage app settings (__accountName + __credential=managedidentity); no connection string
  - Durable role trio on Functions MI (Storage Blob Data Owner + Queue + Table Data Contributor) scoped to storage; Cognitive Services User scoped to docIntel
  - Minimal VNet (snet-pe / snet-fx Microsoft.App/environments / snet-gw Microsoft.Web/serverFarms) + KV Private Endpoint (groupIds vault) + privatelink.vaultcore.azure.net DNS zone + link + zone group, all gated by enablePrivateNetworking
  - VNet integration (virtualNetworkSubnetId) on both apps
  - gateway OBO_CLIENT_SECRET as @Microsoft.KeyVault(SecretUri=...) reference (zero cleartext)
  - Recorded prod Durable Task Hub name ac360prodhub (distinct from staging)
affects: [phase-02-06, phase-03-deployment, host.json-prod-config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Staging-safe parameterized opt-in: every prod-only behavior gated by a bool/enum param defaulting to the staging value (staging.parameters.json compiles untouched)"
    - "roleAssignment name uses guid(scope.id, functionApp.id, roleId) — functionApp.id is start-calculable; principalId stays in properties (runtime value forbidden in name)"
    - "privatelink.vaultcore.azure.net hardcoded as literal on the privateDnsZones resource (not a var) so the compiled ARM name is an exact literal"
    - "Conditional network section: all PE/VNet/DNS resources use = if (enablePrivateNetworking) so staging deploys none of them"

key-files:
  created:
    - .planning/phases/02-production-infrastructure-provisioning/02-05-SUMMARY.md
  modified:
    - infra/main.bicep
    - scripts/validate_infra.ps1

key-decisions:
  - "Used Storage Blob Data Owner (b7e6dc6d-...) for the host blob role instead of the plan-text Blob Data Contributor (ba92f5b4-...): the validator (validate_infra.ps1) asserts the Owner GUID as the canonical host-storage role, and RESEARCH Pattern 4 confirms Owner is the host-minimum role for identity-based AzureWebJobsStorage. Both are data-plane least-privilege; never management Owner/Contributor."
  - "roleAssignment names keyed on functionApp.id (not identity.principalId) to satisfy Bicep BCP120 (name must be calculable at deploy start); principalId consumed in properties.principalId."
  - "privatelink.vaultcore.azure.net inlined as a literal on the DNS zone resource so the compiled ARM name is the exact literal string (required by both Azure DNS and the validator's name match)."
  - "Prod Durable Task Hub name: ac360prodhub (distinct from staging) — to be set in host.json extensions.durableTask.hubName in Phase 3; prevents cross-environment orchestration-state collision."
  - "KV publicNetworkAccess flip NOT performed in Bicep beyond prod.parameters.json (=Disabled); the operator applies the flip as the final ordered step AFTER PE + VNet integration (provision.ps1 step 6 / RESEARCH Pitfall 2)."

patterns-established:
  - "Parameterized staging-safe opt-in for every prod hardening (storageSku, enableIdentityStorage, enablePrivateNetworking, soft-delete/PITR windows, CIDRs)"
  - "Conditional (= if (flag)) network perimeter section keeping staging unaffected"

requirements-completed: [INF-07, INF-08, INF-09]

# Metrics
duration: 18min
completed: 2026-06-14
---

# Phase 2 Plan 05: Production Identity, Storage Hardening, RBAC & Network Perimeter Summary

**GRS + soft-delete/PITR + identity-based AzureWebJobsStorage, the Durable data-role trio + Cognitive Services User on the Functions MI, and a minimal VNet with a Key Vault Private Endpoint + privatelink.vaultcore.azure.net DNS + zero-cleartext @Microsoft.KeyVault secret references — all gated by staging-safe params.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-14T00:55:00Z
- **Completed:** 2026-06-14T01:13:00Z
- **Tasks:** 2
- **Files modified:** 1 (infra/main.bicep) + 1 created (this SUMMARY)

## Accomplishments
- INF-09: storage uses `storageSku` (Standard_GRS in prod), `allowSharedKeyAccess: !enableIdentityStorage`, and a `blobServices` child with `isVersioningEnabled` + `changeFeed` + blob/container `deleteRetentionPolicy` + `restorePolicy` (PITR window < soft-delete window). Functions host uses identity-based `AzureWebJobsStorage__accountName` + `__credential=managedidentity` (no connection string).
- INF-07: Functions MI granted the Durable trio (Storage Blob Data Owner, Storage Queue Data Contributor, Storage Table Data Contributor) scoped to the storage account, plus Cognitive Services User scoped to DocIntel. NO SharePoint roleAssignment (delegated consent, handled in the app-reg script — not an MI role).
- INF-08: minimal VNet (snet-pe with PE policies disabled, snet-fx delegated `Microsoft.App/environments`, snet-gw delegated `Microsoft.Web/serverFarms`), KV Private Endpoint (`groupIds: ['vault']`), `privatelink.vaultcore.azure.net` private DNS zone + VNet link + zone group, VNet integration on both apps, and the gateway `OBO_CLIENT_SECRET` resolved via `@Microsoft.KeyVault(SecretUri=...)` (zero cleartext). All network resources gated by `enablePrivateNetworking` so staging is unaffected.
- Recorded the unique prod Durable Task Hub name `ac360prodhub` (distinct from staging) for Phase 3 host.json.

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden storage (GRS/soft-delete/PITR) + identity AzureWebJobsStorage + Durable role trio + Cognitive Services User** - `6c90d99` (feat)
2. **Task 2: Minimal VNet + KV Private Endpoint + private DNS + VNet integration + KV-reference app settings** - `8a371a1` (feat)
3. **Validator prod-posture fix (follow-up promised in this SUMMARY's "Issues Encountered"):** `validate_infra.ps1` now overlays `prod.parameters.json` (resolving `[parameters('x')]` / `[not(parameters('x'))]`) and accepts the ARM-compiled `[format('@Microsoft.KeyVault(SecretUri=...))]` form - `db3c119` (fix)

**Plan metadata:** (docs commit — see final metadata commit)

## Files Created/Modified
- `infra/main.bicep` - Added storage hardening params + blobServices child + identity-based AzureWebJobsStorage app settings; Durable-trio + Cognitive Services User role assignments; networking params + conditional VNet/PE/DNS section; virtualNetworkSubnetId on both apps; gateway @Microsoft.KeyVault OBO secret reference.
- `.planning/phases/02-production-infrastructure-provisioning/02-05-SUMMARY.md` - This summary.

## Decisions Made
- **Storage Blob role GUID:** used **Storage Blob Data Owner** `b7e6dc6d-f1e8-4753-8033-0f276bb0955b` (validator + RESEARCH host-minimum) rather than the plan task-text's Blob Data *Contributor* `ba92f5b4-...`. Documented as Rule 3 deviation below.
- **Role name keying:** `guid(scope.id, functionApp.id, roleId)` to satisfy Bicep BCP120.
- **DNS zone literal:** `privatelink.vaultcore.azure.net` hardcoded on the resource (not via var) for exact compiled-name matching.
- **Prod Task Hub:** `ac360prodhub` (recorded for Phase 3 host.json).
- **KV public-access flip:** left to the operator as the final ordered step (not flipped in Bicep beyond prod.parameters.json).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Storage Blob role GUID aligned to validator (Owner vs Contributor)**
- **Found during:** Task 1
- **Issue:** The plan task `<action>` text named Storage Blob Data **Contributor** (`ba92f5b4-...`), but the structural INF-07 gate (`scripts/validate_infra.ps1` line 200-201) asserts the presence of Storage Blob Data **Owner** (`b7e6dc6d-...`). Using the Contributor GUID would leave the validator's INF-07 assertion permanently red.
- **Fix:** Used Storage Blob Data Owner `b7e6dc6d-f1e8-4753-8033-0f276bb0955b` for the host blob role (the canonical host-storage role per RESEARCH Pattern 4 §host-storage; "host-only minimum would be Storage Blob Data Owner + Table Data Contributor"). Queue + Table Data Contributor unchanged. Still strictly data-plane least-privilege; no management Owner/Contributor.
- **Files modified:** infra/main.bicep
- **Verification:** `b7e6dc6d-...` present in compiled ARM; validator no longer reports the Blob role missing.
- **Committed in:** `6c90d99` (Task 1 commit)

**2. [Rule 1 - Bug] roleAssignment name must be deploy-start calculable (BCP120)**
- **Found during:** Task 1
- **Issue:** First build failed BCP120 — `guid(storage.id, functionApp.identity.principalId, r)` uses the MI principalId (a runtime value) in the resource `name`, which Bicep forbids.
- **Fix:** Keyed the name on `functionApp.id` (a start-calculable property); `functionApp.identity.principalId` remains in `properties.principalId` (allowed).
- **Files modified:** infra/main.bicep
- **Verification:** `az bicep build` exits 0.
- **Committed in:** `6c90d99` (Task 1 commit)

**3. [Rule 1 - Bug] DNS zone name must compile to an exact literal**
- **Found during:** Task 2
- **Issue:** Initially named the privateDnsZones resource via a `var kvDnsZoneName`, which compiled to `[variables('kvDnsZoneName')]`. The validator (and Azure private DNS resolution) require the exact literal `privatelink.vaultcore.azure.net`; the variable reference failed the validator's name match.
- **Fix:** Inlined the literal `'privatelink.vaultcore.azure.net'` directly on the resource (PATTERNS.md line 35) and removed the var.
- **Files modified:** infra/main.bicep
- **Verification:** Validator's DNS-zone-absent violation cleared; compiled ARM name is the exact literal.
- **Committed in:** `8a371a1` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking validator-alignment, 2 build bugs)
**Impact on plan:** All three were required for correctness and to move the structural gate toward green. No scope creep — only infra/main.bicep's storage/RBAC/network/secrets section touched; all pre-existing content (AUD-04 single-instance comment block, gunicorn --workers 1, B1 gateway, FC1 functionApp + functionAppConfig, DocIntel S0) preserved verbatim.

## Issues Encountered

**RESOLVED — the validator now passes (exit 0) against the real PROD posture.** The prior run flagged 5 residual validator lines as a static-analysis limitation (the validator compiled main.bicep with **default/staging params**, so param-driven prod values were invisible) and deferred the fix to the orchestrator. That follow-up is now done in commit `db3c119`: `scripts/validate_infra.ps1` overlays `prod.parameters.json` and resolves the relevant ARM expressions, turning all 5 lines green:

| Former validator line | Category | How it now resolves |
|---|---|---|
| INF-03 runtime.version != '3.12' (= `[parameters('funcRuntimeVersion')]`) | PARAM-DEFAULT | `Resolve-ArmValue` reads `funcRuntimeVersion` (defaults to `3.12`) ⇒ passes |
| INF-04 docIntel disableLocalAuth != true | PARAM-DEFAULT | resolves `docIntelDisableLocalAuth` to prod `true` ⇒ passes |
| INF-09 storage sku.name != 'Standard_GRS' (= `[parameters('storageSku')]`) | PARAM-DEFAULT | resolves `storageSku` to prod `Standard_GRS` ⇒ passes |
| INF-09 storage allowSharedKeyAccess != false | PARAM-DEFAULT | resolves `[not(parameters('enableIdentityStorage'))]` with prod `enableIdentityStorage=true` ⇒ `false` ⇒ passes |
| INF-08 OBO_CLIENT_SECRET not a KV reference | STATIC-ANALYSIS | regex now also accepts the ARM-compiled `[format('@Microsoft.KeyVault(SecretUri={0}...)', reference(...).vaultUri)]` form ⇒ passes (still zero cleartext — the literal secret value never appears) |

**Validator change rationale (Rule 1 — gate produced false negatives against correct code):** main.bicep applies the mandated staging-safe parameterization (every prod behavior is a param defaulting to staging), so the genuine prod posture lives in `prod.parameters.json`, not in template defaults. The validator's purpose is to assert the **prod** posture offline; teaching it to overlay `prod.parameters.json` (default `-ParamFile`) is the correct way to evaluate that posture without `az login`. Run against `staging.parameters.json` it correctly still fails-closed on the staging shape (LRS / local-auth), preserving the fail-closed contract.

**All STRUCTURAL resources this plan owns are present and verified** in the compiled ARM: blobServices child; the four role GUIDs `b7e6dc6d-...`, `974c5e8b-...`, `0a9a7e1f-...`, `a97b65f3-...`; zero SharePoint roleAssignments; VNet + privateEndpoints (groupIds `vault`) + privateDnsZones + virtualNetworkLinks + privateDnsZoneGroups; `AzureWebJobsStorage__accountName` + `__credential=managedidentity`. **Both authoritative gates pass: `az bicep build -f infra/main.bicep` exit 0; `scripts/validate_infra.ps1` exit 0 (prod posture).**

## User Setup Required

None new in this plan. Forward operator actions (Phase 3 / provision.ps1, already tracked elsewhere):
- Run `provision_app_registrations.ps1` to create the `OBO-CLIENT-SECRET` Key Vault secret that the gateway's `@Microsoft.KeyVault` app setting resolves.
- Apply the KV `publicNetworkAccess=Disabled` flip as the FINAL step, after PE + VNet integration exist (RESEARCH Pitfall 2).
- Set `host.json` `extensions.durableTask.hubName = ac360prodhub` in the prod deploy.
- Pre-flight: `az provider register -n Microsoft.App` (Flex VNet integration requirement).

## Next Phase Readiness
- `infra/main.bicep` now contains the full prod identity/storage/RBAC/network/secrets perimeter; ready for 02-06 (likely provisioning orchestrator / README / what-if) and Phase 3 deployment.
- The recorded `ac360prodhub` Task Hub name is the only cross-plan datum to carry into host.json.

## Self-Check: PASSED
- FOUND: infra/main.bicep
- FOUND: scripts/validate_infra.ps1
- FOUND: .planning/phases/02-production-infrastructure-provisioning/02-05-SUMMARY.md
- FOUND: commit 6c90d99 (Task 1)
- FOUND: commit 8a371a1 (Task 2)
- FOUND: commit db3c119 (validator prod-posture fix)
- GATE: `az bicep build -f infra/main.bicep` exit 0
- GATE: `scripts/validate_infra.ps1` exit 0 (PROD posture; all INF-02/03/04/07/08/09 assertions green)

---
*Phase: 02-production-infrastructure-provisioning*
*Completed: 2026-06-14*
