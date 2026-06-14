---
phase: 02-production-infrastructure-provisioning
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - infra/main.bicep
  - infra/prod.parameters.json
  - infra/bicepconfig.json
  - scripts/provision.ps1
  - scripts/provision_app_registrations.ps1
  - scripts/validate_infra.ps1
findings:
  critical: 3
  warning: 7
  info: 4
  total: 14
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This phase provisions AC360's production infrastructure via Bicep IaC plus two PowerShell
orchestration scripts. The security architecture is largely sound: the OBO secret is correctly
kept out of files/logs and piped only to Key Vault, RBAC role assignments are scoped per-resource
(not subscription-wide), SharePoint OBO is correctly modeled as a delegated consent rather than a
Bicep role, the storage/Key Vault hardening (no shared keys, GRS, soft-delete/PITR, purge
protection, RBAC) is in place, and provision.ps1 defaults to what-if with fail-closed pre-flight
gates. The offline validator is thorough.

However, the review found **3 BLOCKER-class defects that will break a production deployment**:

1. A **Key Vault name mismatch** between the Bicep template and both PowerShell scripts. The
   secret will be written to a vault that the Function/Gateway apps do not reference, so the
   `OBO_CLIENT_SECRET` Key Vault reference will never resolve.
2. The **Gateway managed identity is never granted Key Vault Secrets User**, so even with the
   correct vault name the `@Microsoft.KeyVault(...)` reference cannot be read by the app.
3. **Document Intelligence is left publicly reachable (`publicNetworkAccess: 'Enabled'`)** with
   no private endpoint, while local key auth is disabled in prod — contradicting the INF-08
   private-perimeter intent and leaving OCR traffic on the public network.

The secret-handling guarantees requested for `provision_app_registrations.ps1` are met, with one
robustness gap (no `$LASTEXITCODE` check after the credential reset can write an empty secret to
Key Vault).

No structural findings block was provided.

## Critical Issues

### CR-01: Key Vault name mismatch — OBO secret written to a different vault than the apps reference

**File:** `infra/main.bicep:91`, `scripts/provision.ps1:50`, `scripts/provision_app_registrations.ps1:152`

**Issue:** Bicep computes the Key Vault name as `'${namePrefix}-kv-${environmentName}'` =
`ac360-kv-prod`. Both provisioning scripts default the target vault to `kv-ac360-prod`
(`provision.ps1` param `$KeyVaultName = 'kv-ac360-prod'`, passed into
`provision_app_registrations.ps1 -KeyVaultName`). The script writes the OBO secret with
`az keyvault secret set --vault-name $KeyVaultName ...` — i.e. to `kv-ac360-prod`, a vault Bicep
never created. Meanwhile `gatewayApp` resolves `OBO_CLIENT_SECRET` from
`${keyVault.properties.vaultUri}` of `ac360-kv-prod`. Result: either the `secret set` fails
(vault does not exist) or, if an unrelated `kv-ac360-prod` exists, the secret lands in the wrong
vault and the Gateway's KV reference returns empty at runtime — the OBO flow silently breaks in
production. The provision.ps1 step (6) `az keyvault update -n $KeyVaultName ...` also targets the
wrong vault.

**Fix:** Make the script default match the Bicep naming convention (and ideally derive it from
the deployment output `keyVaultName`):
```powershell
# provision.ps1
[string]$KeyVaultName = 'ac360-kv-prod',
```
Better: after step (4) read the actual name from the deployment output and pass it forward:
```powershell
$kvName = az deployment group show -g $ResourceGroup -n main `
    --query "properties.outputs.keyVaultName.value" -o tsv
& $appRegScript -KeyVaultName $kvName
```

### CR-02: Gateway managed identity is never granted Key Vault Secrets User — KV reference cannot resolve

**File:** `infra/main.bicep:185-193`, `infra/prod.parameters.json:21`

**Issue:** The only Key Vault Secrets User grants come from the `kvRoleAssignments` loop over
`keyVaultSecretsReaderPrincipalIds`, which is `[]` in `prod.parameters.json`. The Gateway app
(`gatewayApp`, system-assigned identity) consumes
`@Microsoft.KeyVault(SecretUri=...secrets/OBO-CLIENT-SECRET)` but is never added to that list and
gets no other KV role. Because the gateway's `principalId` is a runtime value not known until the
app exists, it cannot be self-referenced inside the same `for` parameter either. Net effect: the
`OBO_CLIENT_SECRET` app setting will fail to resolve (`Key Vault reference ... not resolved`),
and the gateway boots without the OBO secret — breaking authentication/OBO in production. The same
gap applies to the Function MI if it ever needs a KV-backed setting.

**Fix:** Add an explicit role assignment for the gateway (and function) MI against the Key Vault,
deployed in-template so the principalId is available:
```bicep
resource gwKvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, gatewayApp.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: gatewayApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}
```
If a two-pass operator flow is intended instead, provision.ps1 must explicitly capture
`gatewayPrincipalId` from outputs and run a documented `az role assignment create` step — currently
no step does this, and step (7) only *lists* assignments.

### CR-03: Document Intelligence left publicly reachable with no private endpoint while local auth disabled in prod

**File:** `infra/main.bicep:206`, `infra/prod.parameters.json:10,13`

**Issue:** `docIntel.properties.publicNetworkAccess` is hardcoded to `'Enabled'` with no parameter,
so even in prod (`enablePrivateNetworking=true`, `docIntelDisableLocalAuth=true`) the OCR endpoint
is reachable from the public internet. The private-networking section (INF-08) creates a Private
Endpoint and DNS zone for Key Vault only — there is no PE for Document Intelligence. With
`disableLocalAuth=true` the Function reaches DocIntel via Entra/MI over the public endpoint. This
contradicts the stated INF-08 private-perimeter posture and the RGPD/EU data-handling intent: PII
document content is OCR'd over a publicly exposed Cognitive Services endpoint. The offline
validator does not assert DocIntel `publicNetworkAccess`, so this drift is not caught.

**Fix:** Parameterize and disable public access in prod, and add a Cognitive Services private
endpoint (groupId `account`) on `snet-pe` plus the `privatelink.cognitiveservices.azure.net`
private DNS zone, mirroring the Key Vault PE pattern:
```bicep
@allowed([ 'Enabled', 'Disabled' ])
param docIntelPublicNetworkAccess string = 'Enabled' // Disabled in prod params
...
properties: {
  customSubDomainName: docIntelName
  publicNetworkAccess: docIntelPublicNetworkAccess
  disableLocalAuth: docIntelDisableLocalAuth
}
```
Sequence the flip after the PE exists (same Pitfall-2 ordering used for Key Vault).

## Warnings

### WR-01: Empty/failed OBO secret can be written to Key Vault — no exit-code check after credential reset

**File:** `scripts/provision_app_registrations.ps1:143-152`

**Issue:** `$ErrorActionPreference = "Stop"` does **not** make native-command (`az`) non-zero exit
codes terminating in PowerShell. If `az ad app credential reset` fails or returns nothing,
`$secret` becomes empty/`$null`, the masking lines no-op, and `az keyvault secret set --value $secret`
writes an empty secret to Key Vault — a silent, hard-to-diagnose production auth failure. No
`$LASTEXITCODE`/empty check guards this.

**Fix:**
```powershell
$secret = az ad app credential reset --id $oboAppId --append --display-name 'obo-prod' --years $SecretYears --query password -o tsv
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($secret)) {
    throw "OBO credential reset failed or returned empty secret; aborting before KV write."
}
```
Apply the same `$LASTEXITCODE` discipline to the other mutating `az` calls (app create, sp create,
permission add, secret set, admin-consent).

### WR-02: `Tasks.ReadWrite` delegated scope contradicts the read-only product guarantee

**File:** `scripts/provision_app_registrations.ps1:129`

**Issue:** The requested Graph scopes include `Tasks.ReadWrite` (Planner write for the FIC draft).
CLAUDE.md states AC360 is "read-only" and the core value is a read-only commercial assistant with
"no modification of SharePoint data." Granting a delegated write scope at provisioning time widens
the consent surface beyond the documented posture. Even if FIC-to-Planner is a real feature, this
should be an explicit, separately justified deviation, not bundled silently into least-privilege.

**Fix:** Confirm whether FIC drafting actually writes to Planner in this milestone. If not, drop
`Tasks.ReadWrite`. If yes, document the read-only exception in CLAUDE.md and the DPIA evidence, and
prefer the narrowest scope that satisfies the use case.

### WR-03: Storage account not network-restricted in prod (no `publicNetworkAccess: Disabled`, no PE)

**File:** `infra/main.bicep:135-148`

**Issue:** The storage account sets `allowBlobPublicAccess:false` and `allowSharedKeyAccess:false`
(good), but leaves the default `publicNetworkAccess: Enabled` with no `networkAcls` and no private
endpoint, even in the private-networking prod profile. Durable orchestration state and downloaded
client documents transit a storage account whose data-plane is reachable from any network (subject
only to Entra authz). For a private-perimeter prod posture this is inconsistent with the Key Vault
hardening.

**Fix:** Add a parameter `storagePublicNetworkAccess` (Disabled in prod) plus storage Private
Endpoints (blob/queue/table groupIds) on `snet-pe` and the corresponding `privatelink.*` DNS zones,
flipped after PE creation. At minimum set `networkAcls.defaultAction: 'Deny'` with VNet rules in prod.

### WR-04: `Get-Scope` resolves only `oauth2PermissionScopes` — `offline_access`/`User.Read` resolution is fragile

**File:** `scripts/provision_app_registrations.ps1:124-139`

**Issue:** `Get-Scope` queries `oauth2PermissionScopes[?value=='$v']` on the Graph SP. `offline_access`
and `User.Read` are present there, but this lookup is brittle: if any single scope returns empty the
script `exit 1`s mid-provisioning, after the API app and possibly OBO app/SP have already been
created — leaving a half-provisioned tenant on re-run. Idempotency is claimed but a partial failure
here is not cleanly recoverable.

**Fix:** Collect all resolved GUIDs first, validate the full set, and only then issue
`az ad app permission add`. Consider batching permissions in a single `--api-permissions` call so the
operation is atomic, and make the failure message actionable (which scope, which tenant).

### WR-05: Function `publicNetworkAccess` not locked down despite ingress IP restrictions

**File:** `infra/main.bicep:289-328`

**Issue:** The Function app relies on `ipSecurityRestrictions` (gateway outbound IPs) for ingress
locking, but `gatewayOutboundIps` is `[]` in `prod.parameters.json`. With an empty array,
`ipRestrictions` is empty and there is no explicit deny — the documented "Deny all implicite" only
holds if at least one Allow rule exists; an empty restriction list leaves the Function open to any
caller that can reach it. There is also no `publicNetworkAccess: Disabled` / `scmIpSecurityRestrictions`.

**Fix:** Treat empty `gatewayOutboundIps` as a fail-closed condition (assert non-empty in prod), or
add an explicit final Deny rule, and verify the SCM site is also restricted. Populate
`gatewayOutboundIps` in `prod.parameters.json` before go-live.

### WR-06: `az login` interactive fallback inside automation scripts undermines fail-closed intent

**File:** `scripts/provision.ps1:82-86`, `scripts/provision_app_registrations.ps1:44-48`

**Issue:** Both scripts, on detecting no active session, silently launch interactive `az login`.
For a production provisioning orchestrator this weakens the "fail-closed pre-flight gate" guarantee:
in a non-interactive/CI context `az login` will hang or pop a browser rather than failing fast, and
it can result in authenticating against an unexpected tenant before the subscription guard runs.

**Fix:** In an automation path, fail closed instead:
```powershell
if (-not $azAccount) { throw "Not authenticated to Azure. Run 'az login' (and select the prod tenant) before re-running." }
```
Or gate the interactive login behind an explicit `-Interactive` switch.

### WR-07: Subscription guard is a no-op when `-ExpectedSubscription` is omitted

**File:** `scripts/provision.ps1:90-95`

**Issue:** The subscription-match gate only throws when `$ExpectedSubscription` is provided. The
parameter has no default, so a routine run skips the guard entirely and will happily what-if/apply
against whatever subscription is active — exactly the "wrong subscription" hazard the gate exists to
prevent. For a production-only orchestrator this should be mandatory.

**Fix:** Make `-ExpectedSubscription` mandatory for apply runs (or default it to the known prod
subscription id and always assert), so the guard cannot be silently bypassed.

## Info

### IN-01: `pointInTimeRestoreDays` vs soft-delete window invariant is documented but not enforced

**File:** `infra/main.bicep:67-68,160`

**Issue:** Comments require `pointInTimeRestoreDays < blobSoftDeleteDays`, and prod params honor it
(6 < 7), but nothing enforces it. A future param edit setting PITR >= soft-delete will fail at
deploy time with an opaque ARM error.

**Fix:** Add a Bicep `assert` or a guard in `validate_infra.ps1` asserting
`pointInTimeRestoreDays < blobSoftDeleteDays`.

### IN-02: Storage name construction is fragile for non-default prefixes/environments

**File:** `infra/main.bicep:90`

**Issue:** `storageName = '${namePrefix}${environmentName}store'` = `ac360prodstore` (14 chars, valid
for the current values), but storage account names are capped at 24 lowercase-alphanumeric chars and
the expression does no length/charset validation. A longer `namePrefix` or `environmentName`, or one
containing a hyphen, produces an invalid name and a late deploy failure.

**Fix:** Add `@maxLength` constraints on `namePrefix`/`environmentName`, or use
`take(uniqueString(...), n)` and validate the composed name.

### IN-03: DevOps secret-mask line emits a literal token even when not running under Azure DevOps

**File:** `scripts/provision_app_registrations.ps1:149`

**Issue:** `Write-Host "##vso[task.setsecret]$secret"` is emitted unconditionally (unlike the
GitHub mask which is gated on `$env:GITHUB_ACTIONS`). Outside Azure DevOps this is just a no-op log
line, but it does momentarily place the secret value into a `Write-Host` expression. The secret is
still never persisted, but the masking should be symmetric and gated.

**Fix:** Gate it on `$env:TF_BUILD -eq 'True'` (Azure DevOps marker), matching the GitHub branch.

### IN-04: `bicepconfig.json` keeps `outputs-should-not-contain-secrets` at warning, not error

**File:** `infra/bicepconfig.json:7-12`

**Issue:** For security-sensitive IaC, leaving `secure-parameter-default` and
`outputs-should-not-contain-secrets` at `warning` means a future secret-in-output regression would
not fail the build/CI gate. The current outputs (principalIds, kvName) are not secrets, so there is
no live leak — this is a hardening suggestion.

**Fix:** Promote `secure-parameter-default` and `outputs-should-not-contain-secrets` to `error` so
the CI Bicep build fails closed on regressions.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
