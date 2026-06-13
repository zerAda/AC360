# Phase 2: Production Infrastructure Provisioning - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Provision (as code + scripts + runbook) a production-grade Azure footprint for AC360 in an EU region, in dependency-correct order, before any backend deploy. Covers INF-01 through INF-09: resource group + prod-tier SKUs, production app registrations + OBO admin consent, system-assigned Managed Identity role assignments, Key Vault secrets via references, minimal network hardening (Key Vault Private Endpoint + VNet), and hardened Storage (GRS, soft-delete, PITR, identity-based AzureWebJobsStorage, unique prod Task Hub).

**Execution boundary (milestone decision):** This phase produces all Bicep IaC, parameter files, the app-registration/admin-consent script, RBAC/secret wiring, and a sequenced provisioning runbook. The actual live actions — `az deployment`, granting admin consent, and EU-residency verification against the live GEREP tenant — are **operator checkpoints**. Nothing live is touched without the operator (no Azure subscription available this session).

Out of scope: backend code deploy (Phase 3), Copilot publish (Phase 4), any rewrite of application code (stack locked). In-place Y1→Flex migration is unsupported — a NEW Functions app is created.

</domain>

<decisions>
## Implementation Decisions

### EU Region & Data Residency
- Primary region for `rg-ac360-prod`: **France Central** — data residency for French insurance client PII, aligns with RGPD and the GEREP tenant.
- DocIntel fallback: if France Central lacks Document Intelligence **S0**, deploy DocIntel to **West Europe** (confirmed fallback) while keeping the rest of the stack in France Central — both EU. All Bicep `location` params set explicitly (per-resource override allowed for DocIntel).
- EU-residency verification (M365 tenant geo, Fabric capacity region, DocIntel S0 availability) is a **blocking pre-flight script + operator checkpoint** — do NOT provision until confirmed against the live GEREP tenant.
- Storage redundancy: **GRS** (geo-redundant, paired EU region) per INF-09.

### Provisioning Execution Model
- IaC: **extend the existing `infra/main.bicep`** (no rewrite — stack locked) and add a `prod.parameters.json`. Promote staging→prod params (B1 gateway, Flex Consumption functions, DocIntel S0, `disableLocalAuth=true`, VNet/PE, GRS storage, identity-based AzureWebJobsStorage, unique prod Task Hub).
- App registrations + OBO admin consent (NOT expressible in Bicep): an **idempotent `az`/PowerShell script** (`az ad app create/update`, `az ad app permission add/admin-consent`) run by the operator. API audience app has no secret; OBO confidential client secret is generated and stored in Key Vault.
- Execution boundary: produce all Bicep + scripts + a **sequenced provisioning runbook**; the actual `az deployment`, the admin-consent grant, and residency verification are **operator checkpoints** (blocking).
- Dependency ordering: a single **`provision.ps1` orchestrator** that runs steps in dependency-correct order (RG → identity/app-regs → Key Vault + secrets → storage → DocIntel → plans → apps → role assignments → PE/VNet) with pre-flight gates (residency, consent, subscription/login checks).

### Network Hardening Scope
- Private Endpoint: **Key Vault only** (per "minimal VNet" criterion), plus VNet integration for gateway/functions outbound.
- Managed Identity: **system-assigned MI** on both the gateway App Service and the Functions app.
- Public access posture: lock down via `disableLocalAuth` (DocIntel) and `allowSharedKeyAccess=false` (Storage) + MI; keep services public-with-MI where no PE is required (avoids over-engineering for a single internal team).
- Secrets: **zero cleartext** in app settings — all via `@Microsoft.KeyVault(...)` references resolved by MI (INF-08). Includes the OBO client secret, OCR/Fabric credentials.
- Role assignments (INF-07): Key Vault Secrets User, Storage Blob Data Contributor, Cognitive Services User, Fabric read, SharePoint OBO — system-assigned MI principals.

### Carried prerequisites / open verification (operator)
- OBO delegated Graph scope list (carried from Phase 1 / AUD-05 / INF-06): verify the exact consented scopes on the production OBO app registration; admin consent is a blocking pre-flight (no AADSTS65001).
- Single-instance gateway pin from Phase 1: `prod.parameters.json` must set App Service plan `sku.capacity = 1` (B1) so the explicit-capacity pin Phase 1 deferred is now landed; no autoscale rule above 1.

### Claude's Discretion
- Exact resource naming suffixes, VNet/subnet CIDR ranges, parameter file structure, and runbook step granularity are at Claude's discretion, consistent with the existing `infra/` conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `infra/main.bicep` (205 lines) — staging-tier baseline: storage, Key Vault, DocIntel, func plan, gateway plan + app, function app, KV role assignments loop. Extend in place for prod.
- `infra/staging.parameters.json` — parameter-file analog for the new `prod.parameters.json`.
- `infra/README.md` — infra doc analog.
- Phase 1 landed the gateway single-worker pin (`gunicorn --workers 1`) + load-bearing comment in `main.bicep`; prod params add explicit `sku.capacity=1`.

### Established Patterns
- Bicep params with explicit `location`, `namePrefix`/`environmentName` naming vars, role-assignment loops over principal-id arrays.
- `kvSecretsUserRoleId` role GUID pattern for RBAC; extend with the other built-in role GUIDs.
- PowerShell ops scripts live in `scripts/*.ps1` (e.g. `package_release.ps1`, `sync_copilot.ps1`) — analog for `provision.ps1` and the app-reg/consent script.

### Integration Points
- `prod.parameters.json` feeds `main.bicep`; `provision.ps1` orchestrates `az deployment group create` + the app-reg/consent script + pre-flight gates.
- App settings reference Key Vault secrets resolved by MI; consumed by `scripts/config.py` at app startup (Phase 3 deploy).

### Reference
- ROADMAP Phase 2 risks: EU residency (M365 geo, Fabric region, DocIntel France Central) must be verified live at provisioning; West Europe is the confirmed DocIntel fallback; Y1→Flex in-place migration unsupported (new app required).

</code_context>

<specifics>
## Specific Ideas

- Resource group name `rg-ac360-prod`; unique production Task Hub name (e.g. `ac360prodhub`).
- API audience app registration carries NO secret; OBO confidential client secret lives only in Key Vault.
- A blocking pre-flight in `provision.ps1`: verify `az login` + correct subscription, EU residency (M365 geo / Fabric region / DocIntel S0 availability), and (post app-reg) admin-consent success before proceeding.

</specifics>

<deferred>
## Deferred Ideas

- Private Endpoints for Storage and DocIntel (kept public-with-MI this phase — minimal VNet only).
- Full-private (no public access) topology — revisit only if a security review requires it.
- Multi-region DR / active-passive (explicitly out of scope for one internal team).
- Actual live provisioning execution — operator-run via the produced runbook/scripts; this phase delivers the artifacts + checkpoints.

</deferred>
