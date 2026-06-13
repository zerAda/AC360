# Phase 2: Production Infrastructure Provisioning - Research

**Researched:** 2026-06-13
**Domain:** Azure IaC (Bicep) — Flex Consumption Functions, App Service B1, identity-based Storage for Durable Functions, Key Vault Private Endpoint + minimal VNet, system-assigned MI RBAC, Entra app registration + OBO admin consent via az CLI, EU region availability
**Confidence:** HIGH on Bicep/CLI idioms and role GUIDs (all verified against current Microsoft Learn + repo); MEDIUM on France Central S0/Flex availability (correctly a live `az` pre-flight, not a static fact)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**EU Region & Data Residency**
- Primary region for `rg-ac360-prod`: **France Central** (RGPD / GEREP tenant alignment).
- DocIntel fallback: if France Central lacks Document Intelligence **S0**, deploy DocIntel to **West Europe** (confirmed fallback) while keeping the rest of the stack in France Central. All Bicep `location` params set explicitly; per-resource override allowed for DocIntel.
- EU-residency verification (M365 tenant geo, Fabric capacity region, DocIntel S0 availability) is a **blocking pre-flight script + operator checkpoint** — do NOT provision until confirmed against the live GEREP tenant.
- Storage redundancy: **GRS** (geo-redundant, paired EU region) per INF-09.

**Provisioning Execution Model**
- IaC: **extend the existing `infra/main.bicep`** (no rewrite) and add a `prod.parameters.json`. Promote staging→prod params (B1 gateway, Flex Consumption functions, DocIntel S0, `disableLocalAuth=true`, VNet/PE, GRS storage, identity-based AzureWebJobsStorage, unique prod Task Hub).
- App registrations + OBO admin consent (NOT expressible in Bicep): an **idempotent `az`/PowerShell script** (`az ad app create/update`, `az ad app permission add/admin-consent`). API audience app has no secret; OBO confidential client secret generated and stored in Key Vault.
- Execution boundary: produce all Bicep + scripts + a **sequenced provisioning runbook**; the actual `az deployment`, the admin-consent grant, and residency verification are **operator checkpoints** (blocking).
- Dependency ordering: a single **`provision.ps1` orchestrator** (RG → identity/app-regs → Key Vault + secrets → storage → DocIntel → plans → apps → role assignments → PE/VNet) with pre-flight gates (residency, consent, subscription/login checks).

**Network Hardening Scope**
- Private Endpoint: **Key Vault only** (+ VNet integration for gateway/functions outbound).
- Managed Identity: **system-assigned MI** on both the gateway App Service and the Functions app.
- Public access posture: lock down via `disableLocalAuth` (DocIntel) and `allowSharedKeyAccess=false` (Storage) + MI; keep services public-with-MI where no PE is required.
- Secrets: **zero cleartext** in app settings — all via `@Microsoft.KeyVault(...)` references resolved by MI (INF-08). Includes OBO client secret, OCR/Fabric credentials.
- Role assignments (INF-07): Key Vault Secrets User, Storage Blob Data Contributor, Cognitive Services User, Fabric read, SharePoint OBO — system-assigned MI principals.

**Carried prerequisites / open verification (operator)**
- OBO delegated Graph scope list (carried from Phase 1 / AUD-05 / INF-06): verify the exact consented scopes on the production OBO app registration; admin consent is a blocking pre-flight (no AADSTS65001).
- Single-instance gateway pin from Phase 1: `prod.parameters.json` must set App Service plan `sku.capacity = 1` (B1); no autoscale rule above 1.

### Claude's Discretion
- Exact resource naming suffixes, VNet/subnet CIDR ranges, parameter file structure, and runbook step granularity — consistent with existing `infra/` conventions.

### Deferred Ideas (OUT OF SCOPE)
- Private Endpoints for Storage and DocIntel (kept public-with-MI; minimal VNet only).
- Full-private (no public access) topology — revisit only if a security review requires it.
- Multi-region DR / active-passive.
- Actual live provisioning execution — operator-run via the produced runbook/scripts.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INF-01 | Production RG in an EU region; all Bicep `location` params explicit | RQ6 + §Provisioning Order; `location` is already a param in `main.bicep`; prod.parameters.json sets it to `francecentral`, DocIntel gets its own `docIntelLocation` param |
| INF-02 | Gateway on App Service **B1** with Always On | §Standard Stack (gwPlan B1) + RQ7; `sku: { name: 'B1', tier: 'Basic', capacity: 1 }`, `siteConfig.alwaysOn = true`; lands the Phase-1-deferred explicit `capacity=1` pin |
| INF-03 | New **Flex Consumption** Functions app (replaces Y1) | **RQ1** — `serverfarms` FC1/FlexConsumption + `sites` `functionAppConfig` (deployment/scaleAndConcurrency/runtime python 3.12); in-place Y1→Flex unsupported (new app) |
| INF-04 | Document Intelligence **S0** + `disableLocalAuth=true` | §Standard Stack (DocIntel) + RQ6; change `sku.name` F0→S0, set `docIntelDisableLocalAuth=true` in prod params, grant MI Cognitive Services User |
| INF-05 | Prod app registrations (API audience no secret; OBO confidential client secret in Key Vault) | **RQ5** — `az ad app create` + `az ad app credential reset`; secret piped to `az keyvault secret set`; API app exposes `Audit.Trigger` via `az ad app update --set api.oauth2PermissionScopes` |
| INF-06 | OBO admin consent for delegated Graph scopes (blocking pre-flight) | **RQ5** — `az ad app permission add --api 00000003-... --api-permissions {guid}=Scope` then `az ad app permission admin-consent`; verify no AADSTS65001; scope list = open verification item |
| INF-07 | System-assigned MI role assignments (KV Secrets User, Storage Data Contributor, Cognitive Services User, Fabric read, SharePoint OBO) | **RQ4** — built-in role GUIDs table; SharePoint OBO is **delegated Graph consent, not an MI role**; Fabric/OneLake read is a data-plane grant, not always an Azure RBAC role |
| INF-08 | All secrets in Key Vault via references + MI; KV Private Endpoint + minimal VNet; zero cleartext | **RQ3** + §Code Examples; `@Microsoft.KeyVault(SecretUri=...)` app settings; KV `publicNetworkAccess=Disabled`; `privateEndpoints` + `privatelink.vaultcore.azure.net` + VNet integration |
| INF-09 | Storage GRS/RA-GRS + blob & container soft-delete + PITR; identity-based AzureWebJobsStorage (`allowSharedKeyAccess=false`); unique prod Task Hub | **RQ2** + §Storage; `sku Standard_GRS`, `blobServices` deleteRetentionPolicy + containerDeleteRetentionPolicy + restorePolicy + isVersioningEnabled+changeFeed; `AzureWebJobsStorage__accountName`/`__credential=managedidentity`; Durable role trio; `taskHub` in host.json / app setting |
</phase_requirements>

## Summary

Every genuine unknown in this phase is now resolved against current Microsoft Learn (most pages updated 2026-05/06) and the existing `infra/main.bicep`. The phase is an **extend-in-place** job: the staging baseline already has the right shape (params, role-assignment loop, hardened KV/Storage/DocIntel) — prod work is (1) swapping SKUs (F0→S0, Y1→Flex, F1→B1), (2) adding the Flex `functionAppConfig` block (the single largest new construct), (3) adding identity-based `AzureWebJobsStorage` + the Durable role trio, (4) adding GRS + soft-delete + PITR to the storage account, (5) adding a minimal VNet + Key Vault Private Endpoint + VNet integration, and (6) adding a standalone idempotent `az`-based app-registration/admin-consent script that Bicep cannot express.

The five Bicep/CLI answers with the highest leverage:

1. **Flex Consumption** is `serverfarms` `sku: { name: 'FC1', tier: 'FlexConsumption' }` + `sites` `kind: 'functionapp,linux'` with a NEW top-level `functionAppConfig` object (deployment.storage → blobContainer + auth `SystemAssignedIdentity`; scaleAndConcurrency `maximumInstanceCount`/`instanceMemoryMB`; runtime `{ name: 'python', version: '3.12' }`). Python 3.12 is supported; Durable Functions on Flex is supported with the Azure Storage provider. **In-place Y1→Flex migration is explicitly unsupported** — confirms the new-app decision. `[VERIFIED: learn.microsoft.com/azure/azure-functions/flex-consumption-plan]`
2. **Identity-based `AzureWebJobsStorage`** = set `AzureWebJobsStorage__accountName=<name>` (or the three `__blobServiceUri`/`__queueServiceUri`/`__tableServiceUri`) and `AzureWebJobsStorage__credential=managedidentity`; remove the connection-string setting; set `allowSharedKeyAccess=false`. The Functions MI needs the **Durable trio**: Storage Blob Data Contributor + Storage Queue Data Contributor + Storage Table Data Contributor. `[VERIFIED: learn.microsoft.com/azure/azure-functions/functions-reference#connecting-to-host-storage-with-an-identity]`
3. **Key Vault Private Endpoint** = a `Microsoft.Network/virtualNetworks` (subnet with `privateEndpointNetworkPolicies: 'Disabled'`), a `Microsoft.Network/privateEndpoints` (groupIds `['vault']`), a `Microsoft.Network/privateDnsZones` named exactly **`privatelink.vaultcore.azure.net`**, a `virtualNetworkLinks` child, and a `privateDnsZoneGroups` child on the PE; set KV `publicNetworkAccess: 'Disabled'`. VNet integration on the apps is the `virtualNetworkSubnetId` property — note **two different subnet delegations**: Flex Functions need `Microsoft.App/environments` (/27 min); App Service B1 needs `Microsoft.Web/serverFarms` (/28 min). `[VERIFIED]`
4. **Role GUIDs** are confirmed: Storage Blob Data Contributor `ba92f5b4-2d11-453d-a403-e96b0029c9fe`, Storage Queue Data Contributor `974c5e8b-45b9-4653-ba55-5f855dd0fb88`, Storage Table Data Contributor `0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3`, Cognitive Services User `a97b65f3-24c7-4388-baec-2e87135dc908`, Key Vault Secrets User `4633458b-17de-408a-b874-0445c86b69e6` (already in repo). **SharePoint OBO is delegated Graph consent, not an MI RBAC role.** Fabric/OneLake read is a data-plane grant, not a guaranteed Azure RBAC role.
5. **App registration + admin consent** = `az ad app create` for both apps; `az ad app permission add --id {obo} --api 00000003-0000-0000-c000-000000000000 --api-permissions {scopeGuid}=Scope` per delegated scope; then `az ad app permission admin-consent --id {obo}` (must run as Global/Privileged Role Admin). The exact consented scope set is the one carried-forward open verification item.

**Primary recommendation:** Extend `infra/main.bicep` with parameterized SKUs + the Flex `functionAppConfig` + identity-based storage + minimal-VNet/KV-PE module section, keep the staging path working by defaulting new params to the staging shape, add `prod.parameters.json`, and ship a separate idempotent `scripts/provision_app_registrations.ps1` (az-based) plus the `provision.ps1` orchestrator with blocking pre-flight gates. Validate with `az bicep build` + `az deployment group what-if` (no live apply this phase).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Resource topology / SKUs / locations (INF-01..04, 09) | Infra (`infra/main.bicep` + `prod.parameters.json`) | — | Declarative IaC owns all Azure resource shape |
| Flex Functions host config (INF-03) | Infra (`functionAppConfig` in `sites`) | Runtime (deployed code Phase 3) | `functionAppConfig` is platform config, distinct from app code |
| Identity-based storage wiring (INF-09) | Infra (app settings + role assignments) | Functions runtime (reads `AzureWebJobsStorage__*`) | RBAC + connection config is infra; runtime consumes it |
| MI principals + role assignments (INF-07) | Infra (`roleAssignments` loop + new role GUIDs) | Entra (principalIds are the apps' system-assigned MIs) | RBAC on Azure resources is Bicep; principalIds emitted as outputs |
| Network hardening: VNet + KV PE + integration (INF-08) | Infra (`virtualNetworks`/`privateEndpoints`/`privateDnsZones` + `virtualNetworkSubnetId`) | — | Pure network IaC |
| Secret storage + references (INF-08) | Infra (KV + `@Microsoft.KeyVault` app settings) | App startup (`scripts/config.py` reads resolved env) | KV references resolved by platform via MI |
| App registrations + delegated scopes + admin consent (INF-05, 06) | Entra control plane (`az ad app *`, **not Bicep**) | Operator checkpoint (admin-consent grant) | Entra app objects + consent are not ARM resources |
| SharePoint access (OBO) | Entra delegated consent (Graph scopes on OBO app) | Runtime (OBO token exchange, Phase 1) | **Delegated, per-user — not an MI role on a resource** |
| Fabric/OneLake read | Fabric data-plane grant / workspace role | Runtime (Fabric SQL query) | Not a guaranteed Azure RBAC role; verify the actual grant mechanism |
| Provisioning sequencing + pre-flight gates | Ops script (`scripts/provision.ps1`) | Operator checkpoints | Orchestration + blocking gates are imperative, outside Bicep |

## Standard Stack

This phase introduces **no new application packages** — it is IaC + provisioning scripts. The "stack" here is the set of Azure resource types, API versions, and CLI commands. No `pip install` occurs in this phase.

### Core resource types & API versions (verified against current Learn schema)

| Resource | API version | Purpose | Notes |
|----------|-------------|---------|-------|
| `Microsoft.Web/serverfarms` | `2023-12-01` (in repo) or `2024-04-01` | Flex plan (FC1) + B1 gateway plan | Repo uses 2023-12-01; FC1 supported. Keep repo version unless a newer feature is needed. |
| `Microsoft.Web/sites` | `2023-12-01` (repo) — **`2024-04-01`+ recommended for `functionAppConfig`** | Flex function app + B1 gateway | `functionAppConfig` is the Flex shape; the latest stable templates use `2024-04-01`/`2025-03-01`. **Verify `functionAppConfig` is accepted by the chosen apiVersion via `az bicep build`** `[ASSUMED on exact min apiVersion]` |
| `Microsoft.Storage/storageAccounts` | `2023-05-01` (repo) | Durable + jobs storage | Add `blobServices` child for soft-delete/PITR |
| `Microsoft.Storage/storageAccounts/blobServices` | `2023-05-01` | soft-delete + container soft-delete + PITR + versioning + change feed | Required for INF-09 |
| `Microsoft.KeyVault/vaults` | `2023-07-01` (repo) | Secrets store | Set `publicNetworkAccess: 'Disabled'` for prod |
| `Microsoft.CognitiveServices/accounts` | `2023-05-01` (repo) | DocIntel S0 | `kind: 'FormRecognizer'`, `sku.name: 'S0'`, `disableLocalAuth: true` |
| `Microsoft.Authorization/roleAssignments` | `2022-04-01` (repo) | MI RBAC | Extend the existing loop with new role GUIDs |
| `Microsoft.Network/virtualNetworks` | `2023-11-01` / `2024-05-01` | Minimal VNet + subnets | One subnet for PE, one delegated subnet per app tier |
| `Microsoft.Network/privateEndpoints` | `2023-11-01` / `2024-05-01` | KV private endpoint | `groupIds: ['vault']` |
| `Microsoft.Network/privateDnsZones` | `2020-06-01` | `privatelink.vaultcore.azure.net` | Exact zone name is mandatory |
| `Microsoft.Network/privateDnsZones/virtualNetworkLinks` | `2020-06-01` | Link zone to VNet | `registrationEnabled: false` |
| `Microsoft.Network/privateEndpoints/privateDnsZoneGroups` | `2023-11-01` | Wire PE → DNS zone | Auto-creates A record |

### Built-in role definition GUIDs (verified)

| Role | GUID | Assigned to | Scope | Requirement |
|------|------|-------------|-------|-------------|
| Key Vault Secrets User | `4633458b-17de-408a-b874-0445c86b69e6` | gateway MI + functions MI | Key Vault | INF-07/08 (already in repo) |
| Storage Blob Data Contributor | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | functions MI | Storage account | INF-07/09 (Durable) |
| Storage Queue Data Contributor | `974c5e8b-45b9-4653-ba55-5f855dd0fb88` | functions MI | Storage account | INF-09 (Durable) |
| Storage Table Data Contributor | `0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3` | functions MI | Storage account | INF-09 (Durable + diagnostic events) |
| Cognitive Services User | `a97b65f3-24c7-4388-baec-2e87135dc908` | functions MI | DocIntel account | INF-04/07 (Entra-only OCR) |
| Storage Blob Data Owner | `b7e6dc6d-f1e8-4753-8033-0f276bb0955b` | (alt to Contributor for host) | Storage account | Optional — see RQ2 note |

`[VERIFIED: learn.microsoft.com/azure/role-based-access-control/built-in-roles]` — these GUIDs are Azure-global constants (stable across tenants/regions).

### Microsoft Graph well-known IDs (for the app-reg script)

| Identifier | Value | Use |
|------------|-------|-----|
| Microsoft Graph resource appId | `00000003-0000-0000-c000-000000000000` | `--api` value in `az ad app permission add` `[VERIFIED: learn.microsoft.com/cli/azure/ad/app/permission]` |

**Delegated Graph permission (scope) GUIDs** — needed by the OBO app per the `function_app` docstrings (Files.Read.All / Sites.Read.All for SharePoint, Tasks.ReadWrite for Planner FIC). These are well-known Graph constants but the **exact scope set actually consented on staging is an open verification item** (carried from Phase 1 Open Q1):

| Delegated scope | GUID | Provenance |
|-----------------|------|------------|
| `Files.Read.All` | `df85f4d6-205c-4ac5-a5ea-6bf408dba283` | `[ASSUMED]` — well-known Graph value; confirm via `az ad sp show --id 00000003-0000-0000-c000-000000000000 --query "oauth2PermissionScopes[?value=='Files.Read.All'].id"` |
| `Sites.Read.All` | `205e70e5-aba6-4c52-a976-6d2d46c48043` | `[ASSUMED]` — confirm via same `az ad sp show` query |
| `Tasks.ReadWrite` | `2219042f-cab5-40cc-b0d2-16b1540b4c5f` | `[ASSUMED]` — confirm via same `az ad sp show` query |
| `offline_access` | `7427e0e9-2fba-42fe-b0c0-848c9e6a8182` | `[ASSUMED]` — required for OBO refresh; confirm |
| `User.Read` | `e1fe6dd8-ba31-4d61-89e7-88639da4683d` | `[VERIFIED]` — appears in official `az ad app permission add` example |

> **Do not hardcode the `[ASSUMED]` GUIDs blindly.** The script should resolve them at runtime from `az ad sp show` (idempotent, tenant-correct) OR the operator confirms them in a `checkpoint:human-verify`. Registry/string existence ≠ "this is the scope our staging app actually consented." See Open Questions.

**No package legitimacy audit required:** this phase installs zero external packages. (Section omitted intentionally — nothing to slopcheck.)

## Architecture Patterns

### System Architecture Diagram (provisioning data flow + runtime trust boundaries)

```
 OPERATOR (provision.ps1)                          ENTRA CONTROL PLANE (az ad — NOT Bicep)
   │  pre-flight gates:                              ┌─────────────────────────────────────┐
   │   - az login + subscription                     │ API audience app  (NO secret)        │
   │   - EU residency (M365 geo / Fabric /           │   exposes scope: Audit.Trigger       │
   │     az functionapp list-flexconsumption-        │ OBO confidential app (secret)        │
   │     locations / DocIntel S0 in region)          │   delegated Graph: Files.Read.All,   │
   │   - admin-consent success (no AADSTS65001)      │     Sites.Read.All, Tasks.ReadWrite, │
   ▼                                                 │     offline_access  → admin-consent  │
 ┌──────────────── az deployment group create (main.bicep + prod.parameters.json) ─────────┐
 │  RG (francecentral)                              secret ──piped──► Key Vault secret      │
 │   ├─ Storage (Standard_GRS, allowSharedKeyAccess=false, soft-delete+PITR+versioning)     │
 │   ├─ Key Vault (publicNetworkAccess=Disabled, RBAC, purge protection)                    │
 │   │     ▲ @Microsoft.KeyVault(SecretUri) refs resolved by MI                             │
 │   ├─ DocIntel (S0, disableLocalAuth=true)  [or West Europe fallback — own location param]│
 │   ├─ serverfarms: gwPlan (B1, capacity=1) + funcPlan (FC1/FlexConsumption)               │
 │   ├─ sites: gatewayApp (app,linux, B1, alwaysOn, --workers 1, MI)                        │
 │   │         functionApp (functionapp,linux, functionAppConfig{deploy/scale/runtime}, MI) │
 │   ├─ VNet: subnet-pe (PE policies off) | subnet-fx (deleg Microsoft.App/environments)    │
 │   │        | subnet-gw (deleg Microsoft.Web/serverFarms)                                 │
 │   ├─ privateEndpoint(KV, groupIds=['vault']) → privatelink.vaultcore.azure.net + DNS grp │
 │   └─ roleAssignments loop: KV Secrets User (both MIs) + Storage Blob/Queue/Table Data    │
 │        Contributor (func MI) + Cognitive Services User (func MI on DocIntel)             │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
        outputs: functionPrincipalId, gatewayPrincipalId, keyVaultName  (feed Phase 3 deploy)

 RUNTIME (Phase 3): functionApp MI ──blob/queue/table data plane (no shared key)──► Storage
                    functionApp MI ──Cognitive Services User──► DocIntel (Entra-only)
                    gateway/func   ──VNet integration──► KV private endpoint (private IP)
                    OBO token (per-user delegated) ──Graph──► SharePoint / Planner
```

### Recommended `infra/` structure (extend in place)

```
infra/
├── main.bicep              # EXTEND: parameterize SKUs; add functionAppConfig,
│                           #   identity-based storage app settings + role trio,
│                           #   blobServices (soft-delete/PITR), VNet+PE module/section,
│                           #   VNet integration (virtualNetworkSubnetId)
├── staging.parameters.json # unchanged (new params default to staging shape)
├── prod.parameters.json    # NEW: francecentral, B1+capacity=1, FC1, S0,
│                           #   docIntelDisableLocalAuth=true, GRS, KV PE on,
│                           #   identity-based storage on, unique prod taskHub
└── README.md               # EXTEND: prod what-if/apply + PE/VNet ordering notes

scripts/
├── provision.ps1                       # NEW: orchestrator + blocking pre-flight gates
└── provision_app_registrations.ps1     # NEW: idempotent az ad app create/permission/consent
                                        #   + secret → Key Vault
```

### Pattern 1: Flex Consumption function app (INF-03) — RQ1

**What:** Flex uses a dedicated plan SKU and a NEW `functionAppConfig` object on `sites` that replaces the legacy Y1 app-settings-driven config (`FUNCTIONS_EXTENSION_VERSION`, `WEBSITE_RUN_FROM_PACKAGE`, etc. are deprecated/moved on Flex).
**When to use:** The prod Functions app (always — Y1→Flex in-place is unsupported, so this is a new resource).
**Example:**
```bicep
// Source: learn.microsoft.com/azure/azure-functions/flex-consumption-plan
//         + Azure-Samples/azure-functions-flex-consumption-samples (FC1 sku shape)
@allowed([ 'francecentral', 'westeurope' ])
param location string = 'francecentral'
param funcMaxInstanceCount int = 40       // Flex min max-scale = 1; default 100; pick small for one team
param funcInstanceMemoryMB int = 2048     // allowed: 512 | 2048 | 4096
param funcRuntimeVersion string = '3.12'  // Python 3.10/3.11/3.12/3.13 supported on Flex
param deploymentContainerName string = 'app-package'

resource funcPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: funcPlanName
  location: location
  sku: { name: 'FC1', tier: 'FlexConsumption' }   // <-- Flex SKU
  properties: { reserved: true }                   // Linux
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {   // verify apiVersion accepts functionAppConfig via az bicep build
  name: funcName
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: funcPlan.id
    httpsOnly: true
    // VNet integration (outbound) — Flex subnet delegation = Microsoft.App/environments
    virtualNetworkSubnetId: vnet::subnetFx.id
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      // NOTE on Flex: do NOT set linuxFxVersion or FUNCTIONS_* version app settings (deprecated/moved)
      appSettings: [
        // identity-based AzureWebJobsStorage — see Pattern 4
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
        { name: 'AzureWebJobsStorage__credential',  value: 'managedidentity' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: '@Microsoft.KeyVault(SecretUri=${appInsightsConnSecretUri})' } // Phase 3 wires AI
        // Durable unique prod task hub (INF-09): also settable in host.json; app setting override shown
        // (Durable reads taskHub from host.json durableTask.hubName; ensure prod value is unique)
      ]
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentContainerName}'
          authentication: { type: 'SystemAssignedIdentity' }   // no connection string
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: funcMaxInstanceCount
        instanceMemoryMB: funcInstanceMemoryMB
      }
      runtime: { name: 'python', version: funcRuntimeVersion }
    }
  }
}
```
**Lands in:** `infra/main.bicep` (replaces the current Y1 `funcPlan` + `functionApp`); params in `prod.parameters.json`.
**Open verification:** the minimum `Microsoft.Web/sites` apiVersion that accepts `functionAppConfig` — repo is on `2023-12-01`; confirm via `az bicep build`. If rejected, bump to `2024-04-01`. `[ASSUMED]`

### Pattern 2: App Service B1 gateway with explicit capacity=1 (INF-02) — RQ7

**What:** Promote the F1 plan to B1 and land the Phase-1-deferred explicit `sku.capacity = 1` (F1 refused it). Add `alwaysOn`. Keep the load-bearing single-worker comment and the `gunicorn --workers 1` start command verbatim.
**Example:**
```bicep
// Phase 1 left a load-bearing comment block here — PRESERVE IT.
resource gwPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: gwPlanName
  location: location
  sku: { name: 'B1', tier: 'Basic', capacity: 1 }   // explicit capacity=1 (INF-02; Phase 1 deferred)
  properties: { reserved: true }                      // Linux
}
resource gatewayApp 'Microsoft.Web/sites@2023-12-01' = {
  // ... identity SystemAssigned, httpsOnly, MI, etc. (unchanged) ...
  properties: {
    serverFarmId: gwPlan.id
    httpsOnly: true
    virtualNetworkSubnetId: vnet::subnetGw.id     // App Service delegation = Microsoft.Web/serverFarms
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      alwaysOn: true                               // INF-02
      appCommandLine: 'gunicorn --workers 1 -k uvicorn.workers.UvicornWorker api_server:app'  // load-bearing
    }
  }
}
```
**Anti-pattern:** adding any `Microsoft.Insights/autoscaleSettings` targeting `gwPlan` with `maximum > 1` — breaks AUD-04 in-memory-state invariant.

### Pattern 3: Key Vault Private Endpoint + minimal VNet + VNet integration (INF-08) — RQ3

**What:** A small VNet with three subnets (KV PE; Flex-delegated; App-Service-delegated), a private endpoint for the vault, the `privatelink.vaultcore.azure.net` private DNS zone linked to the VNet, and a DNS zone group wiring the PE A-record. KV flips to `publicNetworkAccess: 'Disabled'`. The apps reach KV references over the VNet via `virtualNetworkSubnetId`.
**Critical ordering:** KV references break if `publicNetworkAccess=Disabled` is applied **before** the PE + VNet integration exist. Apply PE + integration first, then flip KV public access off (the staging README already warns about this exact failure mode).
**Example:**
```bicep
// Source: learn.microsoft.com/azure/key-vault/general/private-link-service
param vnetAddressPrefix string = '10.42.0.0/24'
param subnetPePrefix string   = '10.42.0.0/27'   // PE subnet
param subnetFxPrefix string   = '10.42.0.32/27'  // Flex functions (delegation Microsoft.App/environments, /27 min)
param subnetGwPrefix string   = '10.42.0.64/28'  // App Service B1 (delegation Microsoft.Web/serverFarms, /28 min)

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${namePrefix}-vnet-${environmentName}'
  location: location
  properties: {
    addressSpace: { addressPrefixes: [ vnetAddressPrefix ] }
    subnets: [
      { name: 'snet-pe', properties: {
          addressPrefix: subnetPePrefix
          privateEndpointNetworkPolicies: 'Disabled'   // required for PE
      }}
      { name: 'snet-fx', properties: {
          addressPrefix: subnetFxPrefix
          delegations: [ { name: 'flexdeleg', properties: { serviceName: 'Microsoft.App/environments' } } ]
      }}
      { name: 'snet-gw', properties: {
          addressPrefix: subnetGwPrefix
          delegations: [ { name: 'gwdeleg', properties: { serviceName: 'Microsoft.Web/serverFarms' } } ]
      }}
    ]
  }
  resource subnetPe 'subnets' existing = { name: 'snet-pe' }
  resource subnetFx 'subnets' existing = { name: 'snet-fx' }
  resource subnetGw 'subnets' existing = { name: 'snet-gw' }
}

resource kvDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'           // EXACT name — mandatory
  location: 'global'
}
resource kvDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: kvDnsZone
  name: '${namePrefix}-kvdns-link'
  location: 'global'
  properties: { registrationEnabled: false, virtualNetwork: { id: vnet.id } }
}
resource kvPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: '${namePrefix}-kv-pe-${environmentName}'
  location: location
  properties: {
    subnet: { id: vnet::subnetPe.id }
    privateLinkServiceConnections: [ {
      name: 'kv-plsc'
      properties: {
        privateLinkServiceId: keyVault.id
        groupIds: [ 'vault' ]                        // KV sub-resource group id
      }
    } ]
  }
}
resource kvPeDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: kvPe
  name: 'default'
  properties: { privateDnsZoneConfigs: [ {
    name: 'vaultcore'
    properties: { privateDnsZoneId: kvDnsZone.id }
  } ] }
}
// KV: set publicNetworkAccess to 'Disabled' in prod params (existing keyVaultPublicNetworkAccess param)
//     and networkAcls.defaultAction => 'Deny' (already conditional in repo).
```
**Lands in:** new section in `infra/main.bicep` gated by a `enablePrivateNetworking` bool param (default false → staging unaffected; true in `prod.parameters.json`). VNet integration via `virtualNetworkSubnetId` on both `sites`.
**RP registration:** Flex VNet integration requires the `Microsoft.App` resource provider registered — add to pre-flight (`az provider register -n Microsoft.App`).

### Pattern 4: Identity-based AzureWebJobsStorage + Durable role trio + GRS/soft-delete/PITR (INF-09) — RQ2

**What:** Make the Functions host use MI for storage (no connection string, `allowSharedKeyAccess=false`), and harden the account (GRS + blob/container soft-delete + PITR + versioning + change feed). Grant the Functions MI the Durable trio.
**Example:**
```bicep
param storageSku string = 'Standard_GRS'                  // INF-09 (staging stays Standard_LRS)
param enableIdentityStorage bool = false                  // true in prod.parameters.json
param blobSoftDeleteDays int = 7
param containerSoftDeleteDays int = 7
param pointInTimeRestoreDays int = 6                       // must be < soft-delete + versioning windows

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: storageSku }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: !enableIdentityStorage          // prod: false → identity-only
  }
}
resource blobSvc 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    isVersioningEnabled: true                             // prereq for PITR
    changeFeed: { enabled: true }                         // prereq for PITR
    deleteRetentionPolicy: { enabled: true, days: blobSoftDeleteDays }
    containerDeleteRetentionPolicy: { enabled: true, days: containerSoftDeleteDays }
    restorePolicy: { enabled: true, days: pointInTimeRestoreDays }   // PITR
  }
}

// Functions MI role assignments — DURABLE TRIO (extend the existing role-assignment loop)
var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageQueueDataContributor = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var storageTableDataContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
// assign all three to functionApp.identity.principalId, scope: storage
```
**Identity-based connection app settings** (on the Functions app — Pattern 1 shows placement):
```
AzureWebJobsStorage__accountName = <storageName>     // global Azure DNS suffix → endpoints inferred
AzureWebJobsStorage__credential  = managedidentity   // system-assigned MI (no clientId/resourceId)
# (alternative explicit form, use if custom DNS/sovereign:)
# AzureWebJobsStorage__blobServiceUri  = https://<name>.blob.core.windows.net
# AzureWebJobsStorage__queueServiceUri = https://<name>.queue.core.windows.net
# AzureWebJobsStorage__tableServiceUri = https://<name>.table.core.windows.net
```
**Why the trio:** Durable Functions uses blobs, queues, AND tables for orchestration/activity coordination and state. Learn's host-storage table is explicit: Durable = Storage Blob Data Contributor + Storage Queue Data Contributor + Storage Table Data Contributor. (Host-only minimum would be Storage Blob Data Owner + Table Data Contributor; the Durable trio supersedes it for this app.) `[VERIFIED: functions-reference#connecting-to-host-storage-with-an-identity]`
**Unique prod Task Hub:** Durable reads the hub name from `host.json` `extensions.durableTask.hubName`. Set a unique prod value (e.g. `ac360prodhub`). This is **application config (Phase 3 deploys host.json)**, but the unique name must be DECIDED here and recorded; an app setting override is also possible. Flag for the planner: ensure prod hub name ≠ staging hub name to avoid cross-environment state collision.
**Caveat:** With `allowSharedKeyAccess=false`, Flex deployment storage MUST use the `SystemAssignedIdentity` auth shown in Pattern 1 (no connection string) — these two decisions are coupled.

### Pattern 5: App registrations + delegated scopes + admin consent (INF-05/06) — RQ5

**What:** Two Entra app objects created idempotently via `az ad app` (NOT Bicep). API audience app exposes `Audit.Trigger` and carries no secret; OBO confidential client gets a secret (→ Key Vault) and delegated Graph scopes + admin consent.
**Idempotency pattern:** check-then-create by `displayName` (`az ad app list --filter "displayName eq '...'"`), reuse appId if present.
**Example (PowerShell-wrapped az):**
```powershell
# --- API audience app (no secret) ---
$apiAppId = az ad app list --filter "displayName eq 'AC360-API-prod'" --query "[0].appId" -o tsv
if (-not $apiAppId) {
  $apiAppId = az ad app create --display-name 'AC360-API-prod' --sign-in-audience AzureADMyOrg --query appId -o tsv
}
# Expose the Audit.Trigger delegated scope (set api.oauth2PermissionScopes via az ad app update / manifest).
# Set identifierUri so tokens carry the api://<appId> audience:
az ad app update --id $apiAppId --identifier-uris "api://$apiAppId"

# --- OBO confidential client (secret → Key Vault) ---
$oboAppId = az ad app list --filter "displayName eq 'AC360-OBO-prod'" --query "[0].appId" -o tsv
if (-not $oboAppId) {
  $oboAppId = az ad app create --display-name 'AC360-OBO-prod' --sign-in-audience AzureADMyOrg --query appId -o tsv
}
# Resolve delegated Graph scope GUIDs from the LIVE Graph SP (tenant-correct, not hardcoded):
$graph = '00000003-0000-0000-c000-000000000000'
function Get-Scope($v) { az ad sp show --id $graph --query "oauth2PermissionScopes[?value=='$v'].id | [0]" -o tsv }
$scopes = 'Files.Read.All','Sites.Read.All','Tasks.ReadWrite','offline_access','User.Read'  # OPEN VERIFICATION (see Open Q1)
foreach ($s in $scopes) {
  $gid = Get-Scope $s
  az ad app permission add --id $oboAppId --api $graph --api-permissions "$gid=Scope" --only-show-errors
}
# Generate secret and store ONLY in Key Vault (never echo to logs/files):
$secret = az ad app credential reset --id $oboAppId --append --display-name 'obo-prod' --years 1 --query password -o tsv
az keyvault secret set --vault-name $kvName --name 'OBO-CLIENT-SECRET' --value $secret 1>$null
$secret = $null   # drop from memory

# --- OPERATOR CHECKPOINT: admin consent (must be Global/Privileged Role Admin) ---
az ad app permission admin-consent --id $oboAppId     # fail-fast; verify no AADSTS65001 on first OBO call
```
**Lands in:** `scripts/provision_app_registrations.ps1`. The OBO secret's Key Vault SecretUri feeds the `@Microsoft.KeyVault(...)` app setting on the gateway (Pattern in §Code Examples).
**Admin consent verification:** after consent, the runbook's smoke check is a real OBO exchange (Phase 3) — AADSTS65001 means consent missing. The pre-flight gate asserts `az ad app permission list-grants` shows the expected scopes before declaring success.
**Provenance discipline:** SharePoint access is **delegated/OBO consent on this app** — there is no MI RBAC role for SharePoint. Do NOT add a "SharePoint OBO" role assignment to `roleAssignments`; INF-07's "SharePoint OBO" item is satisfied here, in the app-reg script.

### Anti-Patterns to Avoid
- **Putting app registrations or admin consent in Bicep.** Entra app objects and consent are not ARM resources; use `az ad`. `[VERIFIED]`
- **Setting `linuxFxVersion` or `FUNCTIONS_EXTENSION_VERSION`/`WEBSITE_RUN_FROM_PACKAGE` on a Flex app.** These are deprecated/moved on Flex; runtime/version live in `functionAppConfig.runtime`. `[VERIFIED: flex-consumption-plan#deprecated-properties-and-settings]`
- **Flipping KV `publicNetworkAccess=Disabled` before PE + VNet integration exist.** Breaks `@Microsoft.KeyVault` references (staging README warns of this). Order PE/integration first.
- **Reusing the staging Durable Task Hub name in prod.** Cross-environment orchestration-state collision. Use a unique prod hub name.
- **Hardcoding delegated scope GUIDs without confirming against the live tenant Graph SP.** Resolve at runtime or operator-verify (Open Q1).
- **An autoscale rule on the gateway plan with maximum > 1.** Breaks AUD-04.
- **Assigning Owner/Contributor to the Functions MI for storage.** Management-plane roles do NOT grant data-plane access; identity-based storage needs the data roles. `[VERIFIED]`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Functions host storage auth | A KV-stored connection string + rotation | Identity-based `AzureWebJobsStorage__credential=managedidentity` + data roles | No secret to rotate; `allowSharedKeyAccess=false` is the hardened posture (INF-09) |
| KV private DNS resolution | Manual A-records / custom DNS | `privateDnsZoneGroups` on the PE + `privatelink.vaultcore.azure.net` zone | Auto-creates/maintains the A record on PE IP changes |
| Secret distribution to apps | Echoing secrets into app settings | `@Microsoft.KeyVault(SecretUri=...)` references resolved by MI | Zero cleartext in app settings (INF-08) |
| Delegated scope GUID lookup | Pasting GUIDs from a blog | `az ad sp show --id 00000003-...` query at runtime | Tenant-correct, slop-proof, idempotent |
| App-reg idempotency | Blind `create` (duplicates on rerun) | check-then-create by displayName | Re-runnable provisioning |
| Region availability check | Assuming France Central supports Flex/S0 | `az functionapp list-flexconsumption-locations` + DocIntel region probe at pre-flight | Availability changes; must be live-checked |
| Durable backup | Custom backup tooling | GRS + blob/container soft-delete + PITR (INF-09) | Native; explicitly the chosen approach (REQUIREMENTS Out-of-Scope) |

**Key insight:** Almost everything maps to a declarative Bicep property or a single `az` command. The only imperative logic is the app-registration/consent script and the pre-flight gates — both because Entra/consent/region-availability are outside ARM's declarative model.

## Runtime State Inventory

> This phase **provisions new infrastructure**; the application has never been deployed. There is no existing live runtime state to migrate. The relevant question is instead *forward* state collisions and operator-side registrations.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no prod resources exist yet. Durable state, blobs, jobs all created fresh. **Forward-looking:** prod Durable Task Hub name must be UNIQUE vs staging (`ac360prodhub`) to prevent cross-env orchestration-state collision if both ever share an account. | Decide + record unique prod hub name (host.json Phase 3) |
| Live service config | **App registrations + admin consent live in Entra, not git.** The OBO consented scope set on the staging app is the source of truth to replicate to prod — and is NOT exported to the repo. | `provision_app_registrations.ps1` + operator verify scopes against live staging app (Open Q1) |
| OS-registered state | None — no deployed App Service/Functions; no scheduled tasks. | None |
| Secrets/env vars | OBO client secret is GENERATED at provisioning and stored ONLY in Key Vault (never git/`.env`). App settings read it via `@Microsoft.KeyVault(...)`. Existing code (`scripts/config.py`) reads `OBO_CLIENT_SECRET`, `APPINSIGHTS_*`, OCR/Fabric creds by name — names unchanged. | Provision script writes secret to KV; prod app settings reference it |
| Build artifacts | None this phase (no code deploy — that's Phase 3). | None |

**Forward residency state (must be confirmed live, not in repo):** M365 tenant geo, Fabric capacity region, Power Platform env region, DocIntel S0 + Flex availability in France Central — all blocking pre-flight checks.

## Common Pitfalls

### Pitfall 1: `functionAppConfig` rejected by the repo's apiVersion
**What goes wrong:** `Microsoft.Web/sites@2023-12-01` may not recognize `functionAppConfig`, producing a Bicep build/what-if error.
**Why:** Flex `functionAppConfig` was added to newer API versions; current samples use `2024-04-01`/`2025-03-01`.
**How to avoid:** Run `az bicep build -f infra/main.bicep` immediately after adding the block; if it errors on `functionAppConfig`, bump the `sites` (and possibly `serverfarms`) apiVersion. Keep `roleAssignments`/`storage` versions unchanged. `[ASSUMED min apiVersion — verify]`

### Pitfall 2: KV references break the instant public access is disabled
**What goes wrong:** Apps return 500s resolving `@Microsoft.KeyVault(...)` because the vault is private but the apps aren't yet on the VNet / DNS doesn't resolve.
**Why:** Ordering — `publicNetworkAccess=Disabled` applied before PE + VNet integration + DNS zone group.
**How to avoid:** Provision order: VNet → PE → DNS zone + link + zone group → app VNet integration → THEN flip KV public access off (or deploy KV public, integrate, and flip in a second pass). The staging README already documents this exact hazard. Add a what-if review checkpoint before the flip.

### Pitfall 3: Identity-based storage silently fails — wrong/missing data roles
**What goes wrong:** Functions host can't start or Durable orchestrations stall; logs show 403/AuthorizationFailure on blob/queue/table.
**Why:** Management roles (Owner/Contributor) assigned instead of data roles, or only Blob granted (missing Queue/Table for Durable), or role propagation lag.
**How to avoid:** Assign exactly the Durable trio (Blob+Queue+Table Data Contributor) to the Functions MI scoped to the storage account; allow for RBAC propagation delay (operator checkpoint: re-test after a few minutes). `[VERIFIED]`

### Pitfall 4: Flex subnet delegation wrong → VNet integration fails
**What goes wrong:** Function app VNet integration fails or the subnet is unusable.
**Why:** Flex requires `Microsoft.App/environments` delegation (NOT `Microsoft.Web/serverFarms`, which is for App Service/Premium). Min /27. Underscores in subnet names unsupported on Flex. `Microsoft.App` RP must be registered.
**How to avoid:** Use `Microsoft.App/environments` for the Flex subnet, `Microsoft.Web/serverFarms` for the B1 gateway subnet; /27 and /28 minimums respectively; no `_` in names; pre-flight `az provider register -n Microsoft.App`. `[VERIFIED: functions-networking-options]`

### Pitfall 5: AADSTS65001 — admin consent not actually granted
**What goes wrong:** First OBO call fails with "consent required"; users see errors.
**Why:** `az ad app permission add` only REQUESTS scopes; `admin-consent` must run separately as a privileged admin, and SP must exist.
**How to avoid:** After `permission add`, ensure the SP exists (`az ad sp create --id <appId>` if needed), run `az ad app permission admin-consent`, and verify via `az ad app permission list-grants`. This is a blocking operator checkpoint. (Carried Phase 1 decision: OBO exhaustion → 503, so a 503 in prod smoke-test is a consent/scope signal.)

### Pitfall 6: France Central lacks Flex or DocIntel S0
**What goes wrong:** Deployment fails at plan/account creation in France Central.
**Why:** Flex availability is region-gated and changes; DocIntel S0 regional availability is not guaranteed.
**How to avoid:** Pre-flight `az functionapp list-flexconsumption-locations` MUST include `francecentral`; probe DocIntel S0 in France Central, and if unavailable, set `docIntelLocation=westeurope` (the locked fallback) while keeping everything else in France Central. Both EU. `[MEDIUM — must be live-verified]`

## Code Examples

### Key Vault reference in an app setting (INF-08) — resolved by MI
```bicep
// Source: learn.microsoft.com/azure/app-service/app-service-key-vault-references
// The gateway's OBO secret comes from KV, never cleartext:
{ name: 'OBO_CLIENT_SECRET', value: '@Microsoft.KeyVault(SecretUri=${oboSecret.properties.secretUri})' }
// Requires: app MI has Key Vault Secrets User on the vault (already in repo's role loop),
// and (prod) the app is VNet-integrated so it can reach the private KV.
```

### Extend the existing role-assignment loop with the new roles (INF-07)
```bicep
// Pattern mirrors the repo's kvRoleAssignments loop (guid(scope.id, pid, roleId)).
var storageDataRoles = [
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'   // Storage Blob Data Contributor
  '974c5e8b-45b9-4653-ba55-5f855dd0fb88'   // Storage Queue Data Contributor
  '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'   // Storage Table Data Contributor
]
resource funcStorageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for r in storageDataRoles: {
  name: guid(storage.id, functionApp.identity.principalId, r)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', r)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}]
resource funcDocIntelRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(docIntel.id, functionApp.identity.principalId, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: docIntel
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}
```

### Provisioning order with blocking pre-flight gates (provision.ps1) — RQ7
```powershell
# Source synthesis: CONTEXT decisions + Learn region/RP requirements.
# --- BLOCKING PRE-FLIGHT (fail-fast; nothing live until all pass) ---
az account show 1>$null || throw 'Not logged in (az login).'
$sub = az account show --query id -o tsv
if ($sub -ne $ExpectedSubscription) { throw "Wrong subscription: $sub" }
az provider register -n Microsoft.App        # Flex VNet integration prereq
az provider register -n Microsoft.KeyVault
# EU residency + capability gates (operator confirms / script asserts):
$flex = az functionapp list-flexconsumption-locations --query "[?name=='francecentral'] | length(@)" -o tsv
if ($flex -eq '0') { throw 'Flex not available in France Central — escalate.' }
# DocIntel S0 region probe (operator checkpoint): if unavailable, set docIntelLocation=westeurope.
# M365 tenant geo / Fabric capacity region / Power Platform env region => OPERATOR CHECKPOINT (manual confirm).

# --- DEPENDENCY-CORRECT ORDER ---
# 1. RG
az group create -n rg-ac360-prod -l francecentral
# 2. App registrations + admin consent  (provision_app_registrations.ps1) — produces OBO secret → KV later
#    (KV must exist before secret set; so split: create apps+request scopes here; set secret after step 4)
# 3. Bicep deploy WHAT-IF (no apply) — operator reviews:
az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p `@infra/prod.parameters.json
# 4. (OPERATOR CHECKPOINT) Bicep apply:  az deployment group create ...   => creates KV, storage, plans, apps, VNet, PE, roles
# 5. Set OBO secret into the now-existing KV; admin-consent (OPERATOR CHECKPOINT)
# 6. (Second pass, OPERATOR CHECKPOINT) flip KV publicNetworkAccess=Disabled once VNet integration confirmed
# 7. Verify: az ad app permission list-grants; MI role assignments; KV reference resolution
```
> The split (request scopes early, set secret after KV exists, consent after apps exist) is why the orchestrator interleaves the two scripts rather than running each end-to-end.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Y1 Dynamic Consumption (5-min cap, cold starts) | Flex Consumption (FC1, configurable memory/scale, VNet) | Flex GA 2024-2025 | New app required (no in-place migration); `functionAppConfig` block |
| Connection-string `AzureWebJobsStorage` | Identity-based `AzureWebJobsStorage__credential=managedidentity` + data roles | Identity-based connections GA | `allowSharedKeyAccess=false`; no secret to rotate |
| `linuxFxVersion` / `FUNCTIONS_EXTENSION_VERSION` app settings | `functionAppConfig.runtime` (Flex) | Flex | Legacy version settings deprecated on Flex |
| KV access policies | KV RBAC (`enableRbacAuthorization=true`) | Long-standing | Repo already on RBAC; role GUIDs not access policies |

**Deprecated/outdated:**
- On Flex, do not set `linuxFxVersion`, `FUNCTIONS_EXTENSION_VERSION`, `WEBSITE_RUN_FROM_PACKAGE` — moved/deprecated. `[VERIFIED]`
- F1/Free plan (staging) → B1 for prod; F1 cannot set `capacity` or `alwaysOn`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Microsoft.Web/sites@2023-12-01` accepts `functionAppConfig`; if not, bump to `2024-04-01` | Pattern 1 / Pitfall 1 | Bicep build fails — caught immediately by `az bicep build`; low risk |
| A2 | Delegated Graph scope GUIDs (Files.Read.All / Sites.Read.All / Tasks.ReadWrite / offline_access) | §Graph IDs / Pattern 5 | Wrong scope = broken OBO; MITIGATED by runtime `az ad sp show` resolution + operator verify (Open Q1) |
| A3 | France Central supports Flex AND DocIntel S0 | Pitfall 6 / RQ6 | Deployment fails; MITIGATED by blocking pre-flight + West Europe DocIntel fallback (locked) |
| A4 | Fabric/OneLake read is a data-plane/workspace grant, not a fixed Azure RBAC role GUID | Map / INF-07 | If a specific RBAC role exists, role-assignment loop needs it; verify actual Fabric access mechanism with operator |
| A5 | The exact consented OBO scope set on staging is the correct prod set | Open Q1 | Over/under-permission; MITIGATED by operator verify against live staging app |
| A6 | PITR `restorePolicy.days` < soft-delete/versioning retention window | Pattern 4 | Bicep validation error if days exceeds; pick conservative defaults (e.g., PITR 6 < soft-delete 7) |

## Open Questions

1. **Exact OBO delegated Graph scope set (carried from Phase 1 Open Q1 + STATE.md blocker)**
   - What we know: OBO exchanges to a delegated Graph token; endpoints need SharePoint file/site read (`Files.Read.All`/`Sites.Read.All` per `function_app._download` docstrings) and Planner `Tasks.ReadWrite`; `offline_access` for refresh.
   - What's unclear: the precise scope set actually consented on the **staging** app registration, and whether `.default` resolves them.
   - Recommendation: `checkpoint:human-verify` — operator runs `az ad app permission list` on the staging OBO app, replicate to prod. Script resolves GUIDs via `az ad sp show` (don't hardcode). Blocking for INF-06.

2. **`Microsoft.Web/sites` minimum apiVersion for `functionAppConfig`**
   - Recommendation: add the block on the repo's `2023-12-01`; if `az bicep build` rejects, bump `sites` to `2024-04-01`. Cheap to verify in Wave 0.

3. **Fabric/OneLake read access mechanism for the Functions MI (INF-07)**
   - What we know: INF-07 lists "Fabric read"; Fabric access is often a workspace role / OneLake data-plane grant, not always a built-in Azure RBAC role.
   - Recommendation: operator confirms how the Functions MI is granted Fabric/OneLake read (workspace role assignment vs Azure RBAC). If it's a workspace grant, it's a manual/Fabric-API step in the runbook, not a Bicep `roleAssignment`. `checkpoint:human-verify`.

4. **DocIntel S0 availability in France Central**
   - Recommendation: live probe at pre-flight; West Europe is the locked fallback (own `docIntelLocation` param). Operator checkpoint.

5. **Unique prod Task Hub name landing point**
   - Hub name lives in `host.json` (deployed Phase 3). Decide the value now (`ac360prodhub`); record it so Phase 3 sets it and it differs from staging.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Azure CLI (`az`) | what-if, app-reg script, pre-flight | ✓ (local) | 2.67.0 | — |
| Bicep CLI | `az bicep build` validation | ✓ (local) | 0.44.1 | `az bicep install` |
| Live Azure subscription | `az deployment` apply | ✗ (operator) | — | Operator checkpoint (this phase produces artifacts only) |
| GEREP M365/Entra tenant | app-reg + admin consent + residency | ✗ (operator) | — | Operator checkpoint |
| Flex Consumption in France Central | INF-03 | ? (live-verify) | — | None for Flex; escalate if absent (no EU Flex fallback decided) |
| DocIntel S0 in France Central | INF-04 | ? (live-verify) | — | **West Europe** (locked) |
| `Microsoft.App` + `Microsoft.KeyVault` RP registered | Flex VNet integration + KV | ? (subscription) | — | `az provider register` (pre-flight) |

**Missing dependencies with no fallback:** none block *artifact production* this phase (Bicep + scripts + runbook are self-contained; `az bicep build` runs locally). Live apply/consent/residency are intentional operator checkpoints.
**Missing dependencies with fallback:** DocIntel region (West Europe fallback). Flex-in-France-Central has NO chosen fallback — flag to operator as an escalation, not a silent substitution.

## Validation Architecture

> nyquist_validation = true (config). IaC has no unit-test framework; "validation" = Bicep static analysis + what-if + script self-checks. This section defines how each INF requirement is mechanically validated WITHOUT a live subscription.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `az bicep build` (compile/lint) + `az deployment group what-if` (dry-run, needs login) + PowerShell `-WhatIf`/`Pester` (optional) for script logic |
| Config file | none — Bicep linter via `bicepconfig.json` (optional, add in Wave 0 if stricter rules wanted) |
| Quick run command | `az bicep build -f infra/main.bicep` (offline; no auth) |
| Full suite command | `az bicep build -f infra/main.bicep && az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json` (what-if needs operator login) |
| arm-ttk | Optional: ARM Template Test Toolkit (`Test-AzTemplate`) — PowerShell module; flag as Wave 0 nice-to-have, not required |

### Phase Requirements → Validation Map
| Req ID | Behavior | Validation Type | Automated Command / Check | Available offline? |
|--------|----------|-----------------|---------------------------|--------------------|
| INF-01 | RG + explicit `location` everywhere | static grep + build | `az bicep build` passes; grep: no resource uses `resourceGroup().location` implicitly where explicit needed; `prod.parameters.json` sets `location=francecentral` | ✅ |
| INF-02 | B1 + capacity=1 + alwaysOn | static | build passes; assert `gwPlan.sku.name=='B1'`, `capacity==1`, `gatewayApp ... alwaysOn==true`; gunicorn `--workers 1` present | ✅ |
| INF-03 | Flex app correct shape | build + what-if | `az bicep build` accepts `functionAppConfig`; what-if shows FC1 plan + python 3.12 runtime | build ✅ / what-if needs auth |
| INF-04 | DocIntel S0 + disableLocalAuth | static | assert `docIntel.sku.name=='S0'`, `disableLocalAuth==true` in prod params | ✅ |
| INF-05 | App regs (API no secret; OBO secret→KV) | script self-check | `provision_app_registrations.ps1` dry-run / Pester: API app has no `credential reset`; OBO secret only `keyvault secret set`, never echoed | ✅ (logic) |
| INF-06 | Admin consent + no AADSTS65001 | runtime check (operator) | post-consent `az ad app permission list-grants` shows expected scopes; OBO smoke = no 65001 | ✗ live-only |
| INF-07 | MI role assignments wired | static + what-if | assert role GUIDs present scoped correctly; SharePoint OBO NOT a roleAssignment; what-if shows assignments | build ✅ |
| INF-08 | KV refs + PE + VNet + zero cleartext | static + grep | grep app settings: every secret uses `@Microsoft.KeyVault(`; no literal secret values; PE + `privatelink.vaultcore.azure.net` + DNS group present; KV `publicNetworkAccess` param=Disabled in prod | ✅ |
| INF-09 | GRS + soft-delete + PITR + identity storage + unique hub | static | assert `sku Standard_GRS`; `blobServices` deleteRetention + containerDeleteRetention + restorePolicy + versioning + changeFeed; `allowSharedKeyAccess==false`; `AzureWebJobsStorage__credential==managedidentity`; prod hub name ≠ staging | ✅ |

### Sampling Rate
- **Per task commit:** `az bicep build -f infra/main.bicep` (must pass; offline, fast).
- **Per wave merge:** build + a static-assertion check script over the compiled JSON (grep/jq for the per-INF assertions above) + script Pester (if added).
- **Phase gate:** build green + a documented `what-if` run (operator, against the live sub) reviewed and attached as evidence before `/gsd-verify-work`. Live apply remains a separate operator checkpoint (OPS-01 / Phase 3).

### Wave 0 Gaps
- [ ] `infra/prod.parameters.json` — does not exist yet (new file).
- [ ] `scripts/provision.ps1` — orchestrator + pre-flight gates (new).
- [ ] `scripts/provision_app_registrations.ps1` — app-reg/consent (new).
- [ ] Static-assertion validator: a small script (PowerShell or `jq` over `az bicep build` JSON output) asserting the per-INF properties above — enables automated, offline INF verification. (Recommended; closes the "IaC has no test runner" gap for Nyquist.)
- [ ] Optional: `bicepconfig.json` (linter rules) + arm-ttk in CI.
- [ ] No package install needed.

## Security Domain

> security_enforcement = true; security_asvs_level = 1; block_on = high.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | yes | Trust boundaries: MI everywhere, private KV, identity-based storage; documented in this research's diagram |
| V2 Authentication | yes | Entra app regs; OBO confidential client (secret in KV); API audience app | 
| V4 Access Control | yes | Least-privilege MI role assignments (data roles, not Owner); SharePoint via per-user delegated OBO (no broad MI) |
| V6 Cryptography / Secret Mgmt | **yes** | Key Vault (RBAC, purge protection, soft-delete) + `@Microsoft.KeyVault` refs; `allowSharedKeyAccess=false`; secret generated→KV, never logged |
| V9 Communications | yes | `httpsOnly`, TLS1.2, KV Private Endpoint, VNet integration for private egress |
| V10 Malicious Code / Supply chain | partial | No new packages this phase; IaC validated by `az bicep build` |
| V14 Configuration | **yes** | No cleartext secrets in app settings; `disableLocalAuth` (DocIntel); `publicNetworkAccess=Disabled` (KV); explicit locations (data residency) |

### Known Threat Patterns for Azure IaC provisioning
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shared-key storage access / key leakage | Spoofing / Info disclosure | Identity-based `AzureWebJobsStorage` + `allowSharedKeyAccess=false` + data-role RBAC (INF-09) |
| Secret in app settings / logs | Info disclosure | KV references + secret generated→KV only; never echoed in script (INF-08/05) |
| Over-privileged MI (Owner/Contributor) | Elevation of privilege | Least-privilege data roles, scoped to the specific resource (INF-07) |
| Public KV exposure | Info disclosure | Private Endpoint + `publicNetworkAccess=Disabled` + VNet integration (INF-08) |
| Local-auth bypass on OCR | Spoofing | DocIntel `disableLocalAuth=true` + Cognitive Services User MI (INF-04) |
| Missing/incorrect admin consent → broken auth or over-consent | Elevation / DoS | Explicit scoped delegated consent, verified via `list-grants`; no app-level Graph roles (INF-06) |
| Data residency violation | Compliance | Explicit EU `location` params; blocking residency pre-flight; West Europe DocIntel fallback (INF-01, RGP-06 precursor) |
| Cross-environment Durable state collision | Tampering | Unique prod Task Hub name (INF-09) |

## Sources

### Primary (HIGH confidence)
- [VERIFIED] learn.microsoft.com/azure/azure-functions/flex-consumption-plan — Flex benefits, instance sizes (512/2048/4096), Python 3.10-3.13 supported, Durable supported (Azure Storage provider), min max-scale=1, in-place migration unsupported, deprecated settings, `Microsoft.App/environments` delegation (updated 2026-06-02).
- [VERIFIED] learn.microsoft.com/azure/azure-functions/functions-reference#connecting-to-host-storage-with-an-identity — `AzureWebJobsStorage__accountName`/`__credential=managedidentity`/`__blobServiceUri`/`__queueServiceUri`/`__tableServiceUri`; Durable trio (Blob+Queue+Table Data Contributor); host-only minimum (updated 2026-06-03).
- [VERIFIED] learn.microsoft.com/azure/templates/microsoft.web/sites (bicep) — `functionAppConfig` schema (deployment.storage/authentication, scaleAndConcurrency, runtime); latest stable apiVersion 2025-03-01; kind `functionapp`.
- [VERIFIED] learn.microsoft.com/azure/key-vault/general/private-link-service — `privatelink.vaultcore.azure.net` zone, PE groupId `vault`, DNS zone + link + record, `publicNetworkAccess=Disabled` (updated 2026-06-12).
- [VERIFIED] learn.microsoft.com/azure/azure-functions/functions-networking-options — Flex VNet integration (regional), subnet delegations table (Flex `Microsoft.App/environments` /27; App Service `Microsoft.Web/serverFarms` /28), `Microsoft.App` RP requirement (updated 2026-06-11).
- [VERIFIED] learn.microsoft.com/azure/role-based-access-control/built-in-roles — Storage Blob/Queue/Table Data Contributor, Storage Blob Data Owner, Cognitive Services User, Key Vault Secrets User GUIDs.
- [VERIFIED] learn.microsoft.com/cli/azure/ad/app/permission — `az ad app permission add/grant/admin-consent`, Graph appId `00000003-...`, `{guid}=Scope`/`=Role`, User.Read GUID example (updated 2026-04-07).
- [VERIFIED] learn.microsoft.com/azure/azure-functions/flex-consumption-how-to — `az functionapp list-flexconsumption-locations` (live region check); Python create example (updated 2026-06-11).

### Secondary (MEDIUM confidence)
- Azure-Samples/azure-functions-flex-consumption-samples — FC1/FlexConsumption sku shape + `functionAppConfig` deployment/scale/runtime example (sample defaults python 3.11 / 2048MB / 100 max).
- Repo source (authoritative for landing sites): `infra/main.bicep`, `infra/staging.parameters.json`, `infra/README.md`, Phase 1 `01-RESEARCH.md` (single-instance pin context).
- WebSearch (Microsoft Q&A) — DocIntel S0 "available in France Central" — NOT authoritative; must be live-verified.

### Tertiary (LOW confidence — must verify)
- Delegated Graph scope GUIDs (Files.Read.All / Sites.Read.All / Tasks.ReadWrite / offline_access) — resolve via `az ad sp show` at runtime (A2/Open Q1).
- France Central Flex + DocIntel S0 availability — live `az` probe (A3/Open Q4).
- Minimum `Microsoft.Web/sites` apiVersion accepting `functionAppConfig` (A1/Open Q2).
- Fabric/OneLake read grant mechanism (A4/Open Q3).

## Metadata

**Confidence breakdown:**
- Flex Bicep shape (serverfarms FC1 + functionAppConfig): HIGH — Learn schema + sample agree; only apiVersion-acceptance to confirm via build.
- Identity-based storage + Durable role trio: HIGH — Learn host-storage table explicit.
- KV Private Endpoint + VNet + delegations: HIGH — Learn PE guide + networking-options delegation table.
- Role GUIDs: HIGH — Azure-global constants.
- App-reg/admin-consent CLI: HIGH on commands; MEDIUM on exact scope set (operator-verify).
- France Central S0/Flex availability: MEDIUM — correctly a live pre-flight, not a static fact.

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (re-confirm Flex region list, `functionAppConfig` apiVersion, and Graph scope GUIDs at execution; region availability is volatile — always re-probe live).
</content>
</invoke>
