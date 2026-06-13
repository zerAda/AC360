# Stack Research — Production Hosting & Deployment

**Domain:** Deploying an existing, hardened Azure + Copilot Studio app (AC360) to production
**Researched:** 2026-06-13
**Confidence:** HIGH (all six decisions verified against current Microsoft Learn docs, 2026-02 → 2026-06 revisions)

> **Scope note.** AC360 is feature-complete and the application stack is LOCKED (Python 3.12, FastAPI, Azure Durable Functions, Copilot Studio, Fabric/OneLake, Document Intelligence, Key Vault, App Insights, Entra ID OBO). This document resolves only the **hosting and deployment** decisions needed to run that exact app in production for a solo operator and 20–100 internal users. It does NOT propose application rewrites or new frameworks.
>
> The existing `infra/main.bicep` already encodes a posture: **App Service for the FastAPI gateway** (currently `F1` Free) and **Consumption (`Y1`) for the Functions app**. The recommendations below confirm the gateway-on-App-Service choice and prescribe two concrete changes: **move the gateway plan off Free to `B1`**, and **move the Function app from `Y1` Consumption to Flex Consumption** (with always-ready for the orchestrator).

---

## Recommended Stack

### Core hosting decisions (the six questions, resolved)

| Decision | Choice | Why (solo operator, 20–100 internal users) | Confidence |
|----------|--------|---------------------------------------------|------------|
| **1. Host the FastAPI gateway** | **Azure App Service (Linux), `B1` Basic plan** | Microsoft's explicit guidance: "When building web apps, Azure App Service is an ideal option." It's the lowest-ops PaaS for a single ASGI web API — built-in TLS, custom domain, managed identity, Key Vault references, App Insights, slots (Standard+), and zero container tooling to maintain. The existing Bicep already targets App Service; only the **SKU must change from `F1` to `B1`** because Free/Shared tiers are dev/test only (no Always On, CPU-minute quota, no custom-domain TLS binding, no SLA, no scale-out). For one team, one always-on instance is plenty. | HIGH |
| **2. Functions plan for Durable orchestration** | **Flex Consumption**, with **2 always-ready instances on the `durable` scale group**, 2048 MB | Flex Consumption is Microsoft's recommended serverless plan and **explicitly supports Durable Functions** (Azure Storage or Durable Task Scheduler provider). It keeps scale-to-zero (pay-per-use) economics but adds **always-ready instances to kill cold starts** on the orchestrator — the audit pipeline is latency-sensitive (a user is waiting in Teams). It also adds VNet integration, which the prod hardening path (private Key Vault/DocIntel) needs. Cheaper and simpler to operate than Premium (EP) for this volume. | HIGH |
| **3. Publish Copilot Studio agent to Teams** | **Publish → connect Teams & M365 Copilot channel → "Show to my teammates and shared users" (Built with Power Platform)**, OR submit for admin approval if pinning org-wide. **Do NOT rely on @mention in a team channel for the audit flow.** | This scopes the agent to exactly the shared user set (the one team) without org-wide admin rollout. **Critical constraint:** in Teams *group chats and channels*, Copilot Studio agents **cannot use SharePoint knowledge sources that require end-user auth** — supported **only in 1:1 chats**. AC360's RAG + OBO is user-scoped, so distribute it for **1:1 personal use**, not as a channel-mentionable bot. | HIGH |
| **4. Secrets** | **Key Vault references in app settings** (`@Microsoft.KeyVault(...)`) resolved via **system-assigned managed identity** + **Key Vault Secrets User** RBAC role | No secret values in env/app settings — the app setting holds only a reference URI; the platform resolves it via MI at runtime. App reads `os.environ` unchanged (no code change). Matches the app's existing `DefaultAzureCredential()` model. Bicep already grants `Key Vault Secrets User` to MI principals via `keyVaultSecretsReaderPrincipalIds`. | HIGH |
| **5. CI/CD to production** | **Extend existing GitHub Actions with a `cd-prod.yml` using OIDC federated credentials + a protected `production` GitHub Environment (required reviewer = the operator)**. Deploy with **raw Bicep (`az deployment group create` + `what-if` gate)**, not azd. | The repo is already Bicep + GitHub Actions; raw `az deployment` keeps one IaC tool and the existing `what-if` discipline. A GitHub `production` Environment with a required-approver protection rule gives the solo operator a deliberate manual gate and OIDC removes long-lived secrets. **`azd` would be a second, redundant toolchain** — not worth it for an existing Bicep estate. | HIGH |
| **6. Identity/auth in production** | **Two app registrations** kept as-is: (a) the **API/gateway app** (audience for inbound JWT, exposes `Audit.Trigger` scope) and (b) the **OBO confidential client** (`OBO_CLIENT_ID`/secret, holds delegated Graph perms). OBO secret lives in **Key Vault**, not env. | This is the app's existing design; production just needs: admin consent granted for the delegated Graph scopes, the OBO client secret stored/rotated in Key Vault, and the gateway/Function MIs granted Cognitive Services User (DocIntel), Storage, and OneLake access. | HIGH (design) / MEDIUM (exact Graph scope list — verify in tenant) |

### Supporting infrastructure (already in Bicep — confirm/tune)

| Component | Recommended prod setting | Purpose | Notes |
|-----------|--------------------------|---------|-------|
| Storage account (Durable + jobs) | `Standard_LRS`, TLS1_2, no public blob, shared-key enabled | Durable task hub state + ephemeral job artifacts | `allowSharedKeyAccess: true` still required by Durable Functions today — keep it. Already correct in Bicep. |
| Key Vault | RBAC, purge protection, soft-delete 90d; **`publicNetworkAccess: Disabled` + Private Endpoint in PROD** | Central secret store | Bicep parameterizes this (`keyVaultPublicNetworkAccess`). Flip to `Disabled` for prod and add a Private Endpoint; Flex Consumption routes through the VNet automatically (no `vnetRouteAllEnabled` needed). |
| Document Intelligence (OCR) | **`S0` (Standard)**, `disableLocalAuth: true` (Entra-only) | OCR pipeline | Current Bicep is `F0` (free) — **`F0` caps at ~500 pages/month and 20 calls/min**; move to `S0` for production. Wire MI + `Cognitive Services User` role, then set `disableLocalAuth: true` to drop the `AZURE_OCR_KEY`. |
| Application Insights + Log Analytics workspace | Workspace-based App Insights; **use `APPLICATIONINSIGHTS_CONNECTION_STRING`** | Monitoring, alerting, FinOps budget alerts | Connection string is **not a secret** — set it directly (not via Key Vault) so the portal telemetry blade works. The instrumentation-key-only path is legacy. |
| App Service plan (gateway) | `B1` Basic, Always On = true, Linux Python 3.12 | Runs FastAPI/Uvicorn | Upgrade to `S1` only if/when deployment slots (blue-green) are wanted. |

## Installation / wiring (key commands)

```bash
# --- Gateway plan: move F1 -> B1 (edit Bicep, then deploy) ---
# in infra/main.bicep gwPlan: sku { name: 'B1', tier: 'Basic' }; functionApp.siteConfig.alwaysOn = true

# --- Function app: Flex Consumption plan (replace Y1) ---
az functionapp plan ...   # OR define Microsoft.Web/serverfarms with FlexConsumption in Bicep
# Set always-ready on the durable group:
az functionapp scale config set -g <rg> -n <func> --trigger-type durable --identifier durable --instance-count 2

# --- Key Vault reference in an app setting (no secret in env) ---
az webapp config appsettings set -g <rg> -n <gateway> --settings \
  OBO_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=ac360-kv-prod;SecretName=obo-client-secret)"

# --- Grant gateway MI read access to Key Vault (RBAC) ---
az role assignment create --assignee <gatewayPrincipalId> \
  --role "Key Vault Secrets User" --scope <keyVaultResourceId>

# --- GitHub OIDC: federated credential scoped to the production environment ---
az ad app federated-credential create --id <appId> --parameters '{
  "name":"github-prod","issuer":"https://token.actions.githubusercontent.com",
  "subject":"repo:<org>/<repo>:environment:production",
  "audiences":["api://AzureADTokenExchange"]}'

# --- Prod deploy step (in cd-prod.yml, after azure/login@v2 OIDC) ---
az deployment group what-if -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json
az deployment group create  -g rg-ac360-prod -f infra/main.bicep -p @infra/prod.parameters.json
```

## Alternatives Considered

| Recommended | Alternative | When the alternative would win |
|-------------|-------------|--------------------------------|
| **App Service (B1) for gateway** | **Azure Container Apps** | If you wanted scale-to-zero on the gateway, a container-first workflow, or microservice fan-out. Not worth the extra container/registry ops for one always-on internal API. The app isn't containerized today; App Service runs the Python code directly. |
| **App Service for gateway** | **Fold gateway into the Functions app (one host)** | Tempting for cost, but the FastAPI gateway does stateful in-memory work (rate-limit map, JWKS cache, IDOR owner map) and is a clean security boundary. Keep it separate; the architecture relies on it. |
| **Flex Consumption for Functions** | **Premium (EP1) Elastic Premium** | Choose EP only if you need **no-cold-start guarantees beyond always-ready, unlimited execution duration, or features Flex lacks**. For 20–100 users Flex + 2 always-ready instances is cheaper and meets latency needs. |
| **Flex Consumption** | **Consumption (Y1, current)** | Y1 is fine functionally but has **cold starts, no always-ready, no VNet**. The undeployed app currently targets Y1; upgrade to Flex for the latency-sensitive orchestrator and the private-networking prod path. |
| **Raw Bicep + GitHub Actions** | **`azd up`** | azd shines for greenfield template-driven provisioning. Here it would duplicate an existing, hardened Bicep estate and add a tool to learn — net negative for a solo operator. |
| **OIDC federated credentials** | **Service principal client secret in GitHub Secrets** | Only if OIDC federation is blocked by tenant policy. OIDC removes a long-lived secret to rotate — strictly better for solo ops. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **App Service `F1`/Free or Shared tier in prod** | No Always On (app idles/cold-starts), CPU-minute quota, no custom-domain TLS binding, no SLA, no scale-out. Current Bicep `gwPlan` is `F1` — a launch blocker. | `B1` Basic (or `S1` if slots wanted) |
| **Document Intelligence `F0` (Free) in prod** | ~500 pages/month + 20 calls/min cap; will throttle real audit traffic. Current Bicep is `F0`. | `S0` Standard |
| **Functions `Y1` Consumption for the user-facing orchestrator** | Cold starts add seconds while a user waits in Teams; no VNet for private KV/DocIntel. | Flex Consumption + always-ready |
| **Secrets as plain App Service app settings / `.env` in prod** | Settings are encrypted at rest but visible to anyone with portal/config read; no rotation/audit. | Key Vault references + MI |
| **Distributing AC360 as a channel-mentionable Teams bot** | Copilot Studio agents in **group/channel chats cannot use SharePoint knowledge requiring end-user auth** — AC360's OBO RAG breaks there. | Personal **1:1** install (shared-user "Built with Power Platform", or admin-approved org listing) |
| **GitHub long-lived SP secret for deploy** | Long-lived credential to rotate/leak; against current Microsoft guidance. | OIDC federated credential scoped to `environment:production` |
| **Migrating an existing Function app in-place to Flex** | **In-place plan migration to Flex is not supported.** | Create a new Flex Consumption Function app and redeploy code |

## Stack Patterns by Variant

**If you keep prod fully private (recommended for RGPD client PII):**
- Key Vault `publicNetworkAccess: Disabled` + Private Endpoint; DocIntel `publicNetworkAccess: Disabled` + PE.
- Use **Flex Consumption VNet integration** for the Function app (auto-routes; no `vnetRouteAllEnabled`).
- Gateway on `B1` can still reach private endpoints via VNet integration (regional VNet integration is available on Basic+).

**If cost is the dominant constraint and a brief cold start is tolerable:**
- Keep Function app on **Flex Consumption with 0 always-ready** (pure pay-per-use) and accept first-call latency.
- Keep gateway on `B1` regardless — Free is not production-viable.

**If you later want blue-green / zero-downtime gateway deploys:**
- Scale the gateway plan to `S1` Standard to unlock **deployment slots**.
- Flex Consumption Functions get zero-downtime via **rolling updates** (slots not supported on Flex).

## Version / platform compatibility

| Item | Constraint | Notes |
|------|-----------|-------|
| Python 3.12 | Supported on Flex Consumption (3.10–3.13) and App Service Linux | App stack version is fine on both targets. |
| Functions runtime | **4.x only** on Flex; non-C# apps must use extension bundle `[4.0.0, 5.0.0)` | Verify `azure_functions/host.json` bundle range before deploy. |
| Durable Functions on Flex | Storage providers limited to **Azure Storage** or **Durable Task Scheduler** | App uses Azure Storage today — compatible. |
| Flex app init timeout | App must start within **30s** (not configurable) | Watch heavy module imports (pandas/pyarrow/deltalake) at cold start; pre-warm via always-ready. |
| Key Vault reference rotation | New secret versions picked up within **24h** (or immediately on app restart) | For urgent rotation, restart the app or call the configreferences refresh API. |

## Sources

- Microsoft Learn — Azure Functions Flex Consumption plan (rev 2026-03-18): Durable Functions support, always-ready, VNet, Python 3.12, 30s init, no in-place migration, runtime 4.x — HIGH
- Microsoft Learn — Comparing Container Apps with other options (rev 2026-02-18): "When building web apps, Azure App Service is an ideal option" — HIGH
- Microsoft Learn — App Service plans overview (rev 2026-03-13): Free/Shared are dev/test only; Basic+ for dedicated compute, slots at Standard — HIGH
- Microsoft Learn — Use Key Vault references as app settings (rev 2026-04-09): `@Microsoft.KeyVault` syntax, MI default, Key Vault Secrets User role, 24h rotation, App Insights conn string not a secret — HIGH
- Microsoft Learn — Connect and configure an agent for Teams and M365 Copilot (rev 2026-05-01): publish flow, availability options, Built with Power Platform vs Built for your org, **SharePoint-auth knowledge unsupported in group/channel chats (1:1 only)** — HIGH
- Microsoft Learn — Deploy to Azure with IaC and GitHub Actions; Bicep deploy-github-actions: OIDC federated credentials, protected `production` environment with required reviewers, what-if gate — HIGH
- Existing repo: `infra/main.bicep`, `infra/staging.parameters.json`, `.github/workflows/cd-staging.yml` — confirmed current SKUs (gateway `F1`, func `Y1`, DocIntel `F0`) and that **`cd-staging.yml` packages a zip only and does not actually deploy to Azure** (gap) — HIGH

---
*Stack research for: production hosting & deployment of AC360*
*Researched: 2026-06-13*
