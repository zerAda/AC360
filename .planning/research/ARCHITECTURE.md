# Architecture Research — Production Deployment Topology

**Domain:** Internal Microsoft 365 / Azure document-audit assistant (Copilot Studio + FastAPI gateway + Durable Functions), French insurance, RGPD-bound, solo operator, 20–100 internal users
**Researched:** 2026-06-13
**Confidence:** HIGH (grounded in the live, audited staging topology + current Microsoft Learn docs for the two decision-critical facts)

> Scope note: the application architecture EXISTS and is mapped (`.planning/codebase/ARCHITECTURE.md`). This file answers **how to deploy that existing architecture to production** — environments, resource topology, identity flow, networking boundary, secrets, EU residency, and build/deploy order. It does **not** redesign the app.

---

## 1. Environment Strategy (staging → prod)

### Current state (verified live)

A single hardened **staging** environment exists in resource group `rg-ac360-staging`, region per the GEREP tenant, deployed from `infra/main.bicep` + `infra/staging.parameters.json`. CD is manual (`.github/workflows/cd-staging.yml`, `workflow_dispatch`) and produces a release zip via `scripts/package_release.ps1`; Copilot import/publish is a manual checklist step. Posture is audited (`docs/security/SECURITY_AUDIT_STAGING.md`): TLS 1.2 everywhere, Key Vault RBAC + purge protection, MIs at least privilege, OneLake read-only, Function ingress locked to gateway outbound IPs.

### Recommended prod model: **two parallel resource groups, one Bicep, parameter-swapped**

The existing Bicep already parameterizes `environmentName` (drives all resource names) and the two prod-only hardening switches (`keyVaultPublicNetworkAccess`, `docIntelDisableLocalAuth`). So prod is the **same template with `prod.parameters.json`** — not a new design.

```
Azure Subscription (GEREP tenant)
├── rg-ac360-staging   (exists)   environmentName=staging
│     ac360-gateway-staging, ac360-func-staging, ac360-kv-staging,
│     ac360stagingstore, ac360-docintel-staging, App Insights
│
└── rg-ac360-prod      (NEW)      environmentName=prod
      ac360-gateway-prod, ac360-func-prod, ac360-kv-prod,
      ac360prodstore, ac360-docintel-prod, App Insights (prod)
```

**Why a separate RG, not a separate subscription:** at 20–100 internal users with a solo operator, a second subscription adds billing/governance overhead with no isolation benefit that an RG + RBAC boundary doesn't already give. A separate RG gives a clean blast radius, independent lifecycle, and one-line teardown. **Decision: single prod resource group `rg-ac360-prod`.**

**Why keep staging:** staging is the rehearsal stage for Bicep `what-if`, the controlled real-prod E2E dry-run target, and the place to validate the two prod hardening switches before they touch prod. Do **not** collapse to a single environment — the milestone explicitly requires a controlled E2E before opening to users, and that needs a non-prod proving ground.

### Promotion flow

| Stage | Action | Gate |
|-------|--------|------|
| Build | `package_release.ps1` (gitleaks, bandit, pip-audit, pytest, `validate_copilot_yaml.py`) | All blocking checks green |
| Provision prod infra | `az deployment group what-if` → review → `create` against `rg-ac360-prod` with `prod.parameters.json` | what-if diff reviewed by operator |
| Deploy backend | Zip-deploy gateway + Function to prod apps | `/health` green, smoke test |
| Publish Copilot | Import package to **prod Copilot Studio environment**, publish to Teams | Checklist in `cd-staging.yml` adapted for prod |
| Controlled E2E | Known test client/doc, real prod services | Verdict correct end-to-end |
| Open to team | Remove gate / flip `AC360_GLOBAL_ENABLED` | Operator sign-off |

**Concrete next step for CD:** clone `cd-staging.yml` → `cd-prod.yml` with `environment: production` (GitHub environment protection rule = manual approval), `prod.parameters.json`, and prod secrets. Keep it `workflow_dispatch` — a solo operator wants deploys to be deliberate, not push-triggered.

---

## 2. Production Resource Topology & Identity Flow

### System overview (prod)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Microsoft Teams client  ──►  Copilot Studio agent (AC360, PROD env)      │
│  (Power Platform managed; user signs in with Entra ID SSO)                │
└───────────────┬──────────────────────────────────────────────────────────┘
                │  HTTPS + user Entra ID bearer token (JWT RS256)
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ac360-gateway-prod  — App Service (Linux, Python 3.12)                    │
│  FastAPI: validate JWT (JWKS), rate-limit, feature gates, OBO exchange     │
│  Identity: System-Assigned MI                                              │
└───────┬───────────────────────────────────────────────┬──────────────────┘
        │ HTTPS + function key (ingress locked to        │ KV reference
        │ gateway outbound IPs)                          │ (MI → Secrets User)
        ▼                                                ▼
┌─────────────────────────────────────┐        ┌──────────────────────────┐
│  ac360-func-prod — Azure Functions  │        │  ac360-kv-prod            │
│  Durable orchestrator (Consumption  │        │  Key Vault (RBAC, purge   │
│  Y1 or Premium). System-Assigned MI │        │  protection, Private EP*) │
└──┬──────────┬──────────┬─────────┬──┘        └──────────────────────────┘
   │ Durable  │ OBO/MI   │ MI      │ MI
   │ state    │ Graph    │ token   │ token
   ▼          ▼          ▼         ▼
┌────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────────────────────┐
│ Storage│ │SharePoint│ │ Document   │ │ Microsoft Fabric / OneLake        │
│ (task  │ │ Online   │ │ Intelligence│ │ (ARTUS gold table, read-only)    │
│  hub)  │ │ (Graph)  │ │ OCR (Entra) │ │ region = France Central (EU)     │
└────────┘ └──────────┘ └────────────┘ └──────────────────────────────────┘
        all telemetry ──► Application Insights (prod)
* Private Endpoint = recommended prod hardening; see §3 for the resolved decision.
```

### Identity flow, component-by-component

This is the crux — three distinct identity mechanisms, each used deliberately:

| Edge | Caller → Callee | Identity mechanism | Why this one |
|------|------------------|--------------------|--------------|
| Teams → Copilot | User → agent | Entra ID SSO (interactive) | User identity must flow through for RBAC |
| Copilot → Gateway | Agent action → FastAPI | **User's Entra ID bearer token** (JWT RS256), audience = `AC360-API-prod` app registration, scope `Audit.Trigger` | Gateway authorizes the *user*, not the bot; preserves user-scoped permissions |
| Gateway → Function | FastAPI → Durable | **Function key** + ingress IP allowlist (gateway outbound IPs only) | Function is private infra; key + network lock = defense in depth |
| Gateway/Function → Key Vault | App → secrets | **System-Assigned Managed Identity** → role *Key Vault Secrets User*, consumed via `@Microsoft.KeyVault(...)` references | Zero secrets in app settings; verified live |
| Function → SharePoint | Durable → Graph | **On-Behalf-Of** (user-delegated): exchange user token via `OBO_CLIENT_ID`/`OBO_CLIENT_SECRET` for a Graph token; fallback to MI (Sites.Selected) when `AC360_REQUIRE_OBO=false` | OBO enforces "AI never sees a doc the user can't open" — the core RGPD guardrail. **Prod must set `AC360_REQUIRE_OBO=true`.** |
| Function → Document Intelligence | Durable → OCR | **System-Assigned MI** → role *Cognitive Services User* (Entra-only); key fallback supported | Removes `AZURE_OCR_KEY` from settings; code already supports MI |
| Function → Fabric/OneLake | Durable → ARTUS | **System-Assigned MI** → workspace *Viewer* + OneLake *DefaultReader* (read-only) | Verified live; no write path to client data |
| Function → Storage (task hub) | Durable runtime → blob/queue/table | **System-Assigned MI** → Storage Blob/Queue/Table Data Contributor (identity-based connection) | See §4 — this closes the last Shared-Key residual |
| All → App Insights | App → telemetry | Connection string (or MI) | Observability |

**Identity registrations to stand up in prod (mirror staging):**
- App registration `AC360-API-prod` — validates tokens (audience + `Audit.Trigger` scope). **No secret** (an API doesn't need one).
- App registration for **OBO** (confidential client) with `OBO_CLIENT_SECRET` in Key Vault — the one place a client secret legitimately exists. Rotate per `SECRET_ROTATION.md`.
- System-Assigned MIs on `ac360-gateway-prod` and `ac360-func-prod` (auto-created by Bicep; their `principalId`s feed the `keyVaultSecretsReaderPrincipalIds` array and the Graph/Fabric/OCR role grants).
- **Do NOT recreate** the `AC360-Automation` setup SP (Sites.FullControl.All). It was deliberately deleted in staging. For prod SharePoint `Sites.Selected` grant, use a short-lived PIM-elevated session, then remove.

---

## 3. Networking / Security Boundary — RESOLVED

### The tradeoff

The staging audit flags Private Endpoints (Key Vault, Storage) and Entra-only OCR as "residual PROD hardening," but explicitly *not applied* because they require VNet integration of the apps and risk breaking the live environment. The question: is VNet + Private Endpoints **warranted** for a 20–100-user internal app run by one person, or is **public + Entra-gated** sufficient?

### Resolution

**Recommended posture for go-live: public endpoints, Entra-gated, with two cheap private-link wins — NOT a full VNet lockdown.**

Rationale, weighing the actual threat model against solo-operator operability:

1. **The data-plane attack surface is already closed by identity, not network.** Gateway requires a valid user JWT (Entra). Function requires a function key *and* its ingress is locked to the gateway's outbound IPs (external IP → 403, verified live). OneLake is read-only via MI. SharePoint is OBO user-scoped. There is no anonymous reachable data path. For an internal app this is the dominant control.

2. **Full VNet integration is a real operability tax on a solo operator.** It introduces a VNet, subnets, Private DNS zones, App Service VNet integration on both apps, and Private Endpoints for KV + Storage + OCR + Fabric. Each is a thing that can silently break Key Vault references or Durable storage at 2 a.m. with one person on call. The milestone constraint is explicit: *monitoring, alerting, and runbooks must be usable by one person.* A private-network topology fights that constraint.

3. **But two private-link moves are low-cost, high-signal, and worth doing:**
   - **Key Vault Private Endpoint + `publicNetworkAccess=Disabled` + `defaultAction=Deny`** (the `keyVaultPublicNetworkAccess` param already exists). Secrets are the highest-value asset; a private vault is the single most defensible hardening step. This *does* require the apps to reach the vault privately — so it pulls in VNet integration for the two apps + a Private DNS zone. Treat this as the one VNet you stand up.
   - **`docIntelDisableLocalAuth=true`** (Entra-only OCR) — no networking needed, just the MI role grant + removing `AZURE_OCR_KEY`. Pure win; do it.

4. **Storage Private Endpoint and Fabric private link: defer.** Storage holds only ephemeral Durable state and transient job artifacts (documents are deleted post-pipeline per GOVERNANCE §4). With Shared Key removed (§4) and `allowBlobPublicAccess=false`, public-with-Deny-default + identity-based access is adequate. Fabric private link is an enterprise-capacity feature with its own operational weight — not warranted at this scale.

**Net decision:** Stand up a **minimal VNet for the two apps + a Key Vault Private Endpoint**, make OCR Entra-only, and keep everything else public-but-Entra/MI-gated. This is the 80/20: it closes the secrets boundary (the residual that actually matters) without imposing a full private-network operational burden on one person. If a future security review *mandates* full private link, the Bicep params are already shaped for it — it's an additive change, not a redesign.

**Optional, only if IT requires it:** Front Door / WAF + IP allowlist in front of the gateway. Not needed for an internal Teams-only audience; the gateway is reached by Copilot Studio, not by arbitrary browsers.

---

## 4. Secrets & Identity Assignments per Component

### Key Vault model (verified, carry to prod)

- `ac360-kv-prod`: **RBAC mode**, purge protection ON, soft-delete 90 days. Prod-only: `publicNetworkAccess=Disabled` + Private Endpoint (see §3).
- Secrets consumed **only** via `@Microsoft.KeyVault(SecretUri=...)` app-setting references, resolved by each app's System-Assigned MI holding *Key Vault Secrets User*. **Zero cleartext keys in app settings** — this invariant is non-negotiable and already proven in staging.
- Non-secret identifiers (`TENANT_ID`, `CLIENT_ID`, URLs) stay as plain app settings — correct, they aren't secrets.

### What lives where, in prod

| Secret / setting | Storage | Consumed by | Identity to read it |
|------------------|---------|-------------|---------------------|
| `OBO_CLIENT_SECRET` | Key Vault (`obo-client-secret`) | Gateway (OBO exchange) | Gateway MI → Secrets User |
| `function-key` | Key Vault | Gateway (call Function) | Gateway MI → Secrets User |
| `AZURE_OCR_KEY` | **Removed in prod** (Entra-only OCR) | — | Function MI → Cognitive Services User |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Key Vault or app setting | Both apps | MI / plain setting |
| `TEAMS_WEBHOOK_URL` | Key Vault | Function (notifications) | Function MI → Secrets User |
| `TENANT_ID`, `CLIENT_ID`, `SHAREPOINT_DRIVE_ID`, `FABRIC_WORKSPACE_ID`, `AZURE_FUNCTION_URL` | Plain app settings | Both | n/a (non-secret) |
| `AzureWebJobsStorage` | **Identity-based connection (no key)** | Function runtime | Function MI → Storage Blob/Queue/Table Data Contributor |

### Managed-identity role assignments (prod target — least privilege)

| MI | Roles |
|----|-------|
| `ac360-gateway-prod` MI | Key Vault *Secrets User* (scoped to vault) |
| `ac360-func-prod` MI | Key Vault *Secrets User*; SharePoint Graph **Sites.Selected** (per-site grant only); Fabric workspace **Viewer** + OneLake **DefaultReader**; Document Intelligence **Cognitive Services User**; Storage **Blob/Queue/Table Data Contributor** |

**Verified fact (closes a stale assumption):** the Bicep comment `allowSharedKeyAccess: true // requis par Durable Functions aujourd'hui` is **now outdated**. Current Microsoft Learn (Durable Functions extension ≥ 2.7.0, doc dated 2026-05) confirms `AzureWebJobsStorage` supports an **identity-based connection**: delete the connection string, set `AzureWebJobsStorage__accountName`, and grant the Function MI the three Storage Data Contributor roles (Blob, Queue, Table). Prod should adopt this and set `allowSharedKeyAccess=false`, closing residual #4 from the staging audit. (Confidence: HIGH — official doc, current.)

---

## 5. Data Residency (RGPD — EU / France)

The domain is French insurance client PII → all stateful components must sit in an EU (ideally France) region. Component-by-component confirmation:

| Component | Residency control | EU/France status |
|-----------|-------------------|------------------|
| App Service (gateway) | `location` param in Bicep | Set to **France Central** (or West Europe) |
| Azure Functions | `location` param | Same region as gateway |
| Storage (Durable state + transient docs) | `location` param | Same region |
| Key Vault | `location` param | Same region |
| Document Intelligence (OCR) | `location` param; Cognitive Services processes in-region | Same region — **confirm the SKU/region pair offers Form Recognizer in France Central**; West Europe is the safe fallback |
| Application Insights | Region selected at workspace creation | EU region |
| **Microsoft Fabric / OneLake (ARTUS)** | Region of the **Fabric capacity** the workspace is assigned to | **France Central is in Fabric's "All workloads" region list** — confirmed available (Microsoft Learn, dated 2026-03). Data resides where the capacity lives. |
| SharePoint Online | M365 tenant geo (Multi-Geo possible) | Governed by GEREP tenant data location — confirm tenant default geo = France/EU |
| Copilot Studio / Power Platform | Power Platform environment region | **Create the prod Copilot environment in an EU region**; Power Platform environment region is fixed at creation |

**Verified residency facts (HIGH confidence, current Microsoft Learn):**
1. **Fabric data residency follows the capacity region**, and **France Central supports all Fabric workloads** (incl. lakehouse/OneLake). So the ARTUS gold table can be physically resident in France. Action: ensure the Fabric capacity backing the workspace is provisioned in France Central (or another EU region), and verify the tenant **home region** is EU (a non-EU home region degrades Fabric feature access and may force a multi-geo capacity).
2. **Document Intelligence** processes in the region of the resource — co-locating the OCR resource in France Central/West Europe keeps document content in-region.

**Residency confirmation checklist (must verify against the live tenant before go-live, not just from docs):**
- [ ] Fabric capacity region = EU (France Central preferred); tenant home region = EU.
- [ ] All Bicep `location` resolves to one EU region (set `location` param explicitly; don't rely on `resourceGroup().location` if the RG could be non-EU).
- [ ] SharePoint/M365 tenant data location = France/EU.
- [ ] Power Platform prod environment created in EU region.
- [ ] OneLake table confirmed pseudonymized (GOVERNANCE notes GEREP-side hashing) — defense in depth for the reference data.

---

## 6. Build / Deploy Order (dependency-ordered)

Derived from the resource dependency graph (identities and KV must exist before grants; grants before apps can resolve references; backend before Copilot can call it). **This ordering feeds roadmap phase sequencing.**

```
0. PRE-REQS (one-time, tenant/Power Platform)
   ├─ Create rg-ac360-prod in an EU region
   ├─ Create Power Platform PROD environment (EU region)
   ├─ Create app registrations: AC360-API-prod (no secret), OBO confidential client (+secret)
   └─ Confirm Fabric capacity region = EU; SharePoint site identified

1. PROVISION CORE INFRA  (az deployment group what-if → review → create, prod.parameters.json)
   ├─ Storage, Key Vault (purge protection), Document Intelligence,
   │  Function + Gateway (System-Assigned MIs created here)
   └─ OUTPUT: functionPrincipalId, gatewayPrincipalId, keyVaultName

2. WIRE IDENTITY  (depends on §1 MIs existing)
   ├─ Put gateway/func principalIds into keyVaultSecretsReaderPrincipalIds → redeploy (KV role assignments)
   ├─ Grant Function MI: SharePoint Sites.Selected (PIM-elevated, per-site), Fabric Viewer+OneLake DefaultReader,
   │  Document Intelligence Cognitive Services User, Storage Blob/Queue/Table Data Contributor
   └─ (PIM session removed afterwards; no standing setup SP)

3. LOAD SECRETS  (depends on KV + MIs)
   ├─ Put obo-client-secret, function-key, teams-webhook, appinsights into Key Vault
   ├─ Set app settings as @Microsoft.KeyVault references; set AC360_REQUIRE_OBO=true
   └─ Switch AzureWebJobsStorage to identity-based; set allowSharedKeyAccess=false

4. HARDEN NETWORK  (maintenance window — depends on apps existing)
   ├─ VNet + subnets + App Service VNet integration (both apps) + Private DNS zone
   ├─ Key Vault Private Endpoint → publicNetworkAccess=Disabled, defaultAction=Deny
   ├─ docIntelDisableLocalAuth=true; remove AZURE_OCR_KEY
   └─ Function ingress: gatewayOutboundIps allowlist (Deny all implicit)
   (validate KV references + OCR + Durable still resolve BEFORE opening to users)

5. DEPLOY BACKEND CODE  (depends on infra + secrets resolvable)
   ├─ package_release.ps1 (gitleaks/bandit/pip-audit/pytest/validate_copilot_yaml — all blocking)
   ├─ Zip-deploy Function (Durable) then Gateway (FastAPI)
   └─ Smoke: /health 200, JWKS reachable, function key call succeeds

6. PUBLISH COPILOT STUDIO  (depends on gateway URL live)
   ├─ Import package into PROD Copilot environment
   ├─ Point connection references at PROD (SharePoint Knowledge, gateway action endpoint, audience=AC360-API-prod)
   ├─ Verify useModelKnowledge=false, moderation=High on RAG nodes
   └─ Publish agent to Teams for the target team

7. CONTROLLED PROD E2E  (depends on full stack live)
   ├─ Known test client/doc → audit → expect correct verdict end-to-end against real services
   └─ Verify App Insights telemetry + Teams notification path

8. OPEN TO TEAM
   └─ Flip AC360_GLOBAL_ENABLED / remove gate after operator sign-off
```

**Critical ordering invariants (why this can't be reordered):**
- MIs don't exist until §1 → can't grant roles or wire KV references before then.
- Key Vault references won't resolve until §2 (MI as Secrets User) + §3 (secrets present) → backend (§5) will fail startup (fail-fast config) if deployed earlier.
- **Network hardening (§4) before backend deploy (§5):** if you flip KV to private *after* the app is running without VNet integration, references break. Doing it before deploy means the first deploy already runs in the hardened topology.
- Copilot (§6) needs the gateway URL + `AC360-API-prod` audience to exist → after §5.

---

## Anti-Patterns (production deployment, this stack)

### Anti-Pattern 1: Re-creating a broad-privilege setup service principal in prod
**What people do:** spin up an automation SP with `Sites.FullControl.All` + a secret to script the SharePoint grant.
**Why it's wrong:** it was deliberately deleted in staging as a removed attack surface; a standing high-privilege secret is the worst RGPD/security liability here.
**Do this instead:** PIM-elevate the operator for a short window, grant `Sites.Selected` per-site, drop elevation. No standing setup identity.

### Anti-Pattern 2: Deploying Bicep with empty `gatewayOutboundIps` to prod
**What people do:** run `az deployment group create` with the default empty array.
**Why it's wrong:** an empty array **removes the Function ingress lock** (the README warns of exactly this). The Function becomes reachable beyond the gateway.
**Do this instead:** always populate `gatewayOutboundIps` from `az webapp show --query possibleOutboundIpAddresses` first, and **always `what-if` before apply**.

### Anti-Pattern 3: Trusting `resourceGroup().location` for residency
**What people do:** leave `location` defaulting to the RG location.
**Why it's wrong:** if the RG is created in a non-EU region, every resource silently lands outside the EU — an RGPD violation with client PII.
**Do this instead:** set `location` explicitly to an EU region in `prod.parameters.json`; verify post-deploy.

### Anti-Pattern 4: Disabling OBO in prod ("MI is simpler")
**What people do:** leave `AC360_REQUIRE_OBO=false`, letting the Function read SharePoint with app-level (MI) permissions.
**Why it's wrong:** it breaks the "AI never sees a document the user couldn't open" guarantee — the central RGPD/security guardrail. The app could surface another user's client folder.
**Do this instead:** `AC360_REQUIRE_OBO=true` in prod; MI Sites.Selected is a constrained fallback, not the primary path.

### Anti-Pattern 5: Push-triggered prod deploys for a solo operator
**What people do:** auto-deploy prod on merge to main.
**Why it's wrong:** one person can't safely absorb an unattended prod change; the milestone wants deliberate, gated releases.
**Do this instead:** `workflow_dispatch` + GitHub environment protection (manual approval) on `cd-prod.yml`.

---

## Integration Points (prod)

| Service | Integration pattern | Notes / gotchas |
|---------|---------------------|-----------------|
| Copilot Studio (Power Platform) | Managed SaaS; agent published to Teams; calls gateway via action with user JWT | Prod environment region is **fixed at creation** — pick EU. DLP policy must allow the gateway/connectors. |
| Microsoft Graph (SharePoint) | OBO (user token → Graph token) from gateway; MI Sites.Selected fallback in Function | 403/404 = RBAC denial, surfaced honestly. Per-site grant only. |
| Document Intelligence | MI Entra-only (Cognitive Services User) | Confirm Form Recognizer SKU available in chosen EU region; remove key after validation. |
| Microsoft Fabric / OneLake | MI read-only (Viewer + OneLake DefaultReader); native `deltalake`/`pyarrow`, no ODBC | Capacity region = EU governs residency. In-memory TTL cache reduces calls. |
| Azure Storage (Durable) | Identity-based connection (no Shared Key) | Requires extension ≥2.7.0 + 3 Storage Data Contributor roles. |
| Application Insights | Connection string / MI | One workspace per environment; EU region. |
| Teams (notifications) | Incoming webhook from Function | URL in Key Vault. |

---

## Sources

- `infra/main.bicep`, `infra/README.md`, `infra/staging.parameters.json` (live, parameterized hardened IaC) — HIGH
- `docs/security/SECURITY_AUDIT_STAGING.md` (verified-by-command staging posture + residual prod actions) — HIGH
- `docs/governance/GOVERNANCE.md` (RGPD data-handling rules, ALM flow) — HIGH
- `.github/workflows/cd-staging.yml` (existing CD + publish checklist) — HIGH
- `.planning/codebase/{ARCHITECTURE,STRUCTURE,INTEGRATIONS}.md` (authoritative app architecture) — HIGH
- Microsoft Learn — *Fabric region availability* (dated 2026-03-05): France Central in "All workloads"; data residency follows capacity region — HIGH
- Microsoft Learn — *Configure Durable Functions App With Managed Identity* (dated 2026-05-20): identity-based `AzureWebJobsStorage`, 3 Storage Data Contributor roles, extension ≥2.7.0 — HIGH

---
*Architecture research (production deployment topology) for: AC360 internal document-audit assistant*
*Researched: 2026-06-13*
