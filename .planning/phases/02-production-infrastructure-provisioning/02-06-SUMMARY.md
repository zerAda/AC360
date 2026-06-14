---
phase: 02-production-infrastructure-provisioning
plan: 06
status: awaiting-operator
completed: pending-operator
requirements: [INF-06]
---

# Plan 02-06 Summary — Operator Live-Action Checkpoints (DEFERRED)

**This plan's three tasks are blocking operator checkpoints that require a live Azure subscription + GEREP production tenant + a privileged (Global / Privileged Role) admin.** They cannot be executed in the autonomous session (no live cloud access). Per the milestone execution-boundary decision, all IaC + scripts are produced and offline-verified; these live actions are queued for the operator. Live `az deployment` apply is deferred to Phase 3 / OPS-01.

**Status: AWAITING OPERATOR.** Fill in the recorded values below when each checkpoint is performed, then this plan closes.

## Operator runbook (what to do, in order)

### Checkpoint 1 — EU residency + France Central availability (INF-01 / RGP-06 precursor)
```
az login                                  # GEREP production subscription
az account show --query id -o tsv         # confirm = intended prod subscription id
pwsh scripts/provision.ps1 -ExpectedSubscription <prod-sub-id> -WhatIfOnly
```
Confirm and record:
- [ ] Flex Consumption available in **francecentral** (pre-flight passes; if not → STOP/escalate, no EU Flex fallback chosen)
- [ ] DocIntel **S0** region used: `francecentral` OR `westeurope` (locked fallback — set `docIntelLocation=westeurope` in `infra/prod.parameters.json` only if S0 absent in France Central)
- [ ] M365 tenant geo = EU: __________
- [ ] Fabric capacity region = EU: __________
- [ ] Power Platform environment region = EU: __________

### Checkpoint 2 — Bicep what-if as provisioning evidence (no live apply this phase)
```
az group create -n rg-ac360-prod -l francecentral
az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json
```
Confirm in the diff and record (attach the what-if output):
- [ ] B1 gateway plan, capacity=1, Always On; gunicorn `--workers 1`; no autoscale max>1
- [ ] FC1 Flex Functions app (functionAppConfig, python 3.12)
- [ ] DocIntel S0, disableLocalAuth=true, publicNetworkAccess=Disabled, Cognitive Services Private Endpoint
- [ ] Storage Standard_GRS, soft-delete + PITR + versioning + changeFeed, allowSharedKeyAccess=false, publicNetworkAccess=Disabled + networkAcls Deny, identity-based AzureWebJobsStorage, unique Task Hub `ac360prodhub`
- [ ] MI role assignments: Durable trio (Blob/Queue/Table) + Cognitive Services User + Key Vault Secrets User (gateway + function)
- [ ] VNet + Key Vault Private Endpoint + privatelink.vaultcore.azure.net DNS

### Checkpoint 3 — OBO admin consent + scope reconciliation + Fabric grant (INF-06)
```
pwsh scripts/provision_app_registrations.ps1 -KeyVaultName ac360-kv-prod   # after KV exists (post-apply)
az ad app permission admin-consent --id <obo-appId>
az ad app permission list-grants --id <obo-appId>
```
Confirm and record:
- [ ] `AC360-API-prod` created (no secret); `AC360-OBO-prod` secret in Key Vault `OBO-CLIENT-SECRET` only
- [ ] Prod delegated scope set reconciled against the live STAGING OBO app; recorded set: __________
- [ ] Admin consent granted; `list-grants` shows expected scopes; OBO smoke (Phase 3) returns **no AADSTS65001**
- [ ] Fabric/OneLake read grant mechanism for the Functions MI: workspace grant vs Azure RBAC → recorded: __________
- [ ] `Tasks.ReadWrite` write-scope exception recorded for DPIA/SEC (Phase 5)

## Notes
- All artifacts these checkpoints exercise are committed and offline-verified (waves 1-3 + the code-review fixes): `infra/main.bicep`, `infra/prod.parameters.json`, `scripts/provision.ps1`, `scripts/provision_app_registrations.ps1`, `scripts/validate_infra.ps1`.
- `az bicep build` exit 0; `validate_infra.ps1` exit 0 (prod posture).
- DocIntel + Key Vault `publicNetworkAccess=Disabled` flips must occur AFTER their Private Endpoints exist (provision.ps1 ordering / RESEARCH Pitfall 2).
- `gatewayOutboundIps` in `prod.parameters.json` must be populated at go-live (after the gateway exists) to arm the explicit ingress deny-all.
