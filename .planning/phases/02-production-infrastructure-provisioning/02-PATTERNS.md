# Phase 2: Production Infrastructure Provisioning - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 5 (1 modified, 4 created)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `infra/main.bicep` (MODIFY) | config (IaC) | declarative-resource | itself (extend in place) | exact (self) |
| `infra/prod.parameters.json` (CREATE) | config (params) | declarative-params | `infra/staging.parameters.json` | exact |
| `scripts/provision_app_registrations.ps1` (CREATE) | script (ops/az) | imperative-control-plane | `scripts/deploy_azure_ocr.ps1` (az + login + secret-to-env) | role-match |
| `scripts/provision.ps1` (CREATE) | script (orchestrator) | imperative-sequencing | `scripts/deploy_azure_ocr.ps1` (az pre-flight) + `scripts/package_release.ps1` (fail-closed gate) + `scripts/sync_copilot.ps1` (env-var checks, interleaved steps) | role-match |
| static-assertion validator (CREATE — e.g. `scripts/validate_infra.ps1`) | script (validation) | transform/assert | `scripts/package_release.ps1` (collect-violations → exit 1 gate) | role-match |

All Bicep work is **extend-in-place**; the analog for every new resource block is an existing block in the same `main.bicep`. New params must default to the staging shape so `staging.parameters.json` keeps compiling unchanged (RESEARCH §recommended structure).

---

## Pattern Assignments

### `infra/main.bicep` (config/IaC, declarative-resource) — MODIFY

**Analog:** itself. Each new construct mirrors an existing block. Concrete in-file anchors:

**Param declaration pattern** (lines 14-34): `@description('...')` (French) immediately above each `param`, `@allowed([...])` for enums, explicit defaults that match the staging shape. New params (`storageSku`, `enableIdentityStorage`, `enablePrivateNetworking`, `funcMaxInstanceCount`, `funcInstanceMemoryMB`, `funcRuntimeVersion`, `docIntelLocation`, blob/PITR retention days) follow this exact decorator-then-param form. Pin defaults to staging values (`Standard_LRS`, `false`, `'Y1'`-equivalent) so prod opts in via `prod.parameters.json`.

**Naming var pattern** (lines 36-42):
```bicep
var storageName = '${namePrefix}${environmentName}store'
var kvName = '${namePrefix}-kv-${environmentName}'
var funcName = '${namePrefix}-func-${environmentName}'
```
New names (VNet, PE, DNS-link) reuse `'${namePrefix}-...-${environmentName}'`. Note `privatelink.vaultcore.azure.net` is the ONE name that must be a literal, not interpolated (RESEARCH Pattern 3).

**Role-GUID var + role-assignment loop pattern** (lines 44-45, 91-99) — THE load-bearing analog for INF-07:
```bicep
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
...
resource kvRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in keyVaultSecretsReaderPrincipalIds: {
  name: guid(keyVault.id, pid, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: pid
    principalType: 'ServicePrincipal'
  }
}]
```
Copy this exact `guid(scope.id, principalId, roleId)` + `subscriptionResourceId(...)` + `principalType: 'ServicePrincipal'` shape for the new Durable-trio loop (scope `storage`, principal `functionApp.identity.principalId`) and the single Cognitive Services User assignment (scope `docIntel`). New role-GUID `var`s go beside `kvSecretsUserRoleId` (line 45). See RESEARCH §Code Examples lines 544-569 for the ready-made excerpt.

**Storage block** (lines 57-68) — extend for INF-09: change `sku: { name: 'Standard_LRS' }` → `sku: { name: storageSku }`; change `allowSharedKeyAccess: true` → `allowSharedKeyAccess: !enableIdentityStorage`; add a sibling `blobServices@2023-05-01` child (parent: storage) with `isVersioningEnabled`/`changeFeed`/`deleteRetentionPolicy`/`containerDeleteRetentionPolicy`/`restorePolicy` (RESEARCH Pattern 4, lines 393-403). Keep the existing French `// requis par Durable...` comment intent but update it — identity-based removes that requirement.

**Key Vault block** (lines 73-89) — already parameterized for prod: `publicNetworkAccess: keyVaultPublicNetworkAccess` (line 83) and the conditional `defaultAction: ... == 'Disabled' ? 'Deny' : 'Allow'` (line 86) are reused as-is; `prod.parameters.json` flips the param to `Disabled`. Add the VNet/PE/DNS section gated by `enablePrivateNetworking` (RESEARCH Pattern 3, lines 307-363).

**DocIntel block** (lines 104-115) — extend for INF-04: `sku: { name: 'F0' }` → `'S0'`; `location: location` → `location: docIntelLocation` (West Europe fallback); `disableLocalAuth: docIntelDisableLocalAuth` (line 113) is already parameterized — prod params set `true`.

**Plans** (lines 120-157) — for INF-02/03: funcPlan `sku: { name: 'Y1', tier: 'Dynamic' }` → `{ name: 'FC1', tier: 'FlexConsumption' }`; gwPlan `sku: { name: 'F1', tier: 'Free' }` → `{ name: 'B1', tier: 'Basic', capacity: 1 }`. **PRESERVE the load-bearing comment block (lines 128-150)** — the AUD-04 single-instance pin rationale; lines 153-156 explicitly say `capacity=1` lands "en Phase 2 (INF-02, B1)". This is the Phase-1-deferred pin now landing.

**sites blocks** (functionApp lines 162-177; gatewayApp lines 182-201) — both have `identity: { type: 'SystemAssigned' }` (lines 166, 186), `httpsOnly: true`, `minTlsVersion: '1.2'`, `ftpsState: 'Disabled'` already. For INF-03 add `functionAppConfig` (RESEARCH Pattern 1, lines 245-258) + identity-based `AzureWebJobsStorage__*` app settings; remove `linuxFxVersion` from the Flex functionApp ONLY (gateway keeps `Python|3.12`). For INF-02 add `alwaysOn: true` to gatewayApp siteConfig. **PRESERVE the `gunicorn --workers 1` appCommandLine (line 198) and its load-bearing comment (lines 194-197) verbatim.** Add `virtualNetworkSubnetId` to both (Flex→`Microsoft.App/environments` subnet; gateway→`Microsoft.Web/serverFarms` subnet).

**Outputs pattern** (lines 203-205): `output functionPrincipalId string = functionApp.identity.principalId` etc. — these already emit the MI principalIds the role loop consumes; reuse and extend if new outputs (e.g. KV secretUri) are needed for the orchestrator.

**Key Vault reference app-setting pattern** (INF-08, new): `{ name: 'OBO_CLIENT_SECRET', value: '@Microsoft.KeyVault(SecretUri=${...})' }` — RESEARCH §Code Examples line 539. Names must match what `scripts/config.py` reads (`OBO_CLIENT_SECRET`, `APPINSIGHTS_*`, OCR/Fabric creds — unchanged per RESEARCH Runtime State line 496).

---

### `infra/prod.parameters.json` (config/params) — CREATE

**Analog:** `infra/staging.parameters.json` (full file, 12 lines).

**Structure to copy exactly** (lines 1-12): same `$schema`, `contentVersion`, `parameters` object with `{ "value": ... }` wrappers.
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "namePrefix": { "value": "ac360" },
    "environmentName": { "value": "prod" },
    "keyVaultPublicNetworkAccess": { "value": "Disabled" },
    "docIntelDisableLocalAuth": { "value": true },
    ...
  }
}
```
**Prod deltas (per CONTEXT/RESEARCH):** `environmentName: "prod"`, `location: "francecentral"`, `docIntelLocation` (francecentral or westeurope fallback), `keyVaultPublicNetworkAccess: "Disabled"`, `docIntelDisableLocalAuth: true`, `storageSku: "Standard_GRS"`, `enableIdentityStorage: true`, `enablePrivateNetworking: true`, B1/capacity=1, FC1 params, unique Task Hub note, plus `keyVaultSecretsReaderPrincipalIds`/`gatewayOutboundIps` (populated from live per README lines 26-34).

---

### `scripts/provision_app_registrations.ps1` (script/ops) — CREATE

**Analog:** `scripts/deploy_azure_ocr.ps1` (az-driven, login-check, secret-handling) + RESEARCH Pattern 5 (lines 429-462, ready-made az ad app excerpt).

**Header/param pattern** (deploy_azure_ocr lines 1-21): `<# .SYNOPSIS ... #>` French comment-help block, then `param(...)` with typed defaults.

**az-presence + login-check pattern** (deploy_azure_ocr lines 23-36) — copy verbatim as a guard:
```powershell
if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur : Azure CLI n'est pas installé..." -ForegroundColor Red
    exit 1
}
$azAccount = az account show --query "name" -o tsv 2>$null
if (-not $azAccount) { az login | Out-Null; $azAccount = az account show --query "name" -o tsv }
```

**Secret-masking pattern** (deploy_azure_ocr lines 57-61): `::add-mask::` / `##vso[task.setsecret]` for CI. **Adapt, do not copy the `.env` write (lines 63-66)** — the OBO secret must go to Key Vault ONLY (`az keyvault secret set ... 1>$null` then `$secret = $null`), never to a file (RESEARCH Pattern 5 lines 452-455).

**Core pattern (NEW, from RESEARCH Pattern 5):** idempotent check-then-create by displayName (`az ad app list --filter "displayName eq '...'"`); API audience app gets NO `credential reset`; OBO app gets `az ad app credential reset` → KV; delegated scope GUIDs resolved at runtime via `az ad sp show --id 00000003-...` (NOT hardcoded); `az ad app permission add` then `admin-consent` (operator checkpoint). SharePoint OBO is delegated consent here — NOT an MI role assignment in Bicep (RESEARCH line 462).

---

### `scripts/provision.ps1` (script/orchestrator) — CREATE

**Analogs (composite):**
- **Pre-flight/login gate** → `scripts/deploy_azure_ocr.ps1` lines 23-36 (az presence + `az account show` + login).
- **Env-var-required + interleaved-steps** → `scripts/sync_copilot.ps1` lines 19-24 (required-var check → `exit 1`) and its function-decomposed step flow (lines 46-60).
- **Fail-closed gate philosophy** → `scripts/package_release.ps1` lines 16, 82-93 (`$ErrorActionPreference = "Stop"`, collect violations, `exit 1` before any mutating action; `-DryRun` switch lines 12-13, 89-92).

**Param + ErrorAction pattern** (package_release lines 11-16):
```powershell
param([string]$ExpectedSubscription, [switch]$WhatIfOnly = $true)
$ErrorActionPreference = "Stop"
```

**Core pattern (NEW, from RESEARCH §Code Examples lines 573-599):** blocking pre-flight (`az account show` || throw; subscription match; `az provider register -n Microsoft.App`/`-n Microsoft.KeyVault`; `az functionapp list-flexconsumption-locations` includes francecentral; DocIntel S0 probe; M365/Fabric residency = operator checkpoint). Then dependency-correct sequence: RG → app-regs (request scopes) → `az deployment group what-if` → [operator apply] → set OBO secret in KV + admin-consent → flip KV public access off → verify. Use the `Write-Host ... -ForegroundColor` status convention seen across all three analogs. Default to what-if/no-apply (nothing live this phase).

---

### static-assertion validator `scripts/validate_infra.ps1` (script/validation) — CREATE

**Analog:** `scripts/package_release.ps1` — the **collect-violations → fail-closed** structure (lines 64-93).

**Pattern to copy** (lines 65-93): a `Test-*` function that accumulates `$violations` over a checklist, prints each in red, and `exit 1` if any, else green + `exit 0`:
```powershell
function Test-PackageClean { param(...) $violations = @(); foreach (...) { ... $violations += $rel } return $violations }
$preViolations = Test-PackageClean ...
if ($preViolations.Count -gt 0) { ...; exit 1 }
```
**Core pattern (NEW):** run `az bicep build -f infra/main.bicep` (offline), then assert over the compiled ARM JSON the per-INF properties from RESEARCH §Validation Map (lines 674-684): `sku.name=='B1'`/`capacity==1`/`alwaysOn==true`; `FC1`/python 3.12; DocIntel `S0`+`disableLocalAuth`; `Standard_GRS`+blobServices retention/PITR/versioning+`allowSharedKeyAccess==false`+`AzureWebJobsStorage__credential==managedidentity`; every secret app-setting uses `@Microsoft.KeyVault(`; PE + `privatelink.vaultcore.azure.net` present; prod Task Hub ≠ staging; SharePoint OBO is NOT a roleAssignment. Use the `$ManifestObj | ConvertTo-Json` reporting idiom (package_release lines 114-123) if an evidence artifact is wanted.

---

## Shared Patterns

### Role assignments (RBAC)
**Source:** `infra/main.bicep` lines 91-99 (`kvRoleAssignments` loop) + var line 45.
**Apply to:** All INF-07 role assignments. Reuse `guid(scope.id, principalId, roleId)` + `subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)` + `principalType: 'ServicePrincipal'`. New role-GUID `var`s declared beside line 45. Ready excerpt: RESEARCH lines 544-569.

### Parameterized opt-in (staging-safe extension)
**Source:** `infra/main.bicep` lines 26-31, 83-86 (`keyVaultPublicNetworkAccess`, conditional `defaultAction`, `docIntelDisableLocalAuth`).
**Apply to:** Every new prod-only behavior. Add a bool/enum param defaulting to the staging value; prod opts in via `prod.parameters.json`. Keeps `staging.parameters.json` compiling untouched.

### az login + presence guard
**Source:** `scripts/deploy_azure_ocr.ps1` lines 23-36.
**Apply to:** `provision.ps1` and `provision_app_registrations.ps1` — copy the guard before any `az` mutation.

### Fail-closed gate + DryRun
**Source:** `scripts/package_release.ps1` lines 12-16, 82-93.
**Apply to:** `provision.ps1` (default what-if/no-apply) and `validate_infra.ps1` (collect → exit 1). `$ErrorActionPreference = "Stop"`.

### Secret hygiene (never to disk/logs)
**Source:** `scripts/deploy_azure_ocr.ps1` lines 57-61 (CI masking) — but REJECT its `.env.generated` write (lines 63-66) for the OBO secret.
**Apply to:** `provision_app_registrations.ps1` — OBO secret → `az keyvault secret set ... 1>$null`, then `$secret = $null`. CLAUDE.md: secrets never logged; no cleartext in app settings.

### French comment-help + colored status
**Source:** all `.ps1` analogs (`<# .SYNOPSIS #>` blocks; `Write-Host -ForegroundColor Cyan/Green/Red/Yellow`).
**Apply to:** Both new scripts — match the house style (CLAUDE.md: French allowed in docstrings/comments for the domain).

## No Analog Found

| File / Construct | Role | Reason |
|------|------|--------|
| Flex `functionAppConfig` block | IaC sub-construct | No existing Flex app in repo (current is Y1). Use RESEARCH Pattern 1 (lines 205-261). apiVersion acceptance is an open verify (build-check). |
| VNet + Private Endpoint + private DNS zone | IaC network section | No networking resources exist in `main.bicep` today. Use RESEARCH Pattern 3 (lines 300-366). |
| `az ad app` create/permission/admin-consent flow | ops control-plane | No app-registration script exists. Use RESEARCH Pattern 5 (lines 429-462). |

These three have no codebase analog; the planner should use the cited RESEARCH excerpts directly. Everything else copies an in-repo pattern.

## Metadata

**Analog search scope:** `infra/` (main.bicep, staging.parameters.json, README.md), `scripts/*.ps1` (11 scripts; deploy_azure_ocr, package_release, sync_copilot read in full/part).
**Files scanned:** 8
**Pattern extraction date:** 2026-06-13
