# Project Research Summary

**Project:** AC360 — Production Launch
**Domain:** First production deployment of a brownfield, security-hardened Azure AI assistant (FastAPI + Durable Functions + Copilot Studio), French insurance / client-PII, RGPD-bound, solo operator, 20-100 internal users
**Researched:** 2026-06-13
**Confidence:** HIGH

## Executive Summary

AC360 is a feature-complete, security-hardened Teams assistant for commercial/insurance staff that has never been deployed. The production-launch milestone is a deployment and compliance operation, not a build — the application stack (Python 3.12, FastAPI, Azure Durable Functions, Copilot Studio, Fabric/OneLake, Document Intelligence, Key Vault, App Insights, Entra ID OBO) is locked and will not change. Research across all four dimensions confirms the same core finding: the codebase is well-designed but contains several single-process assumptions that silently break on Azure compute, and the existing IaC encodes development-tier SKUs that are not production-viable. Closing these gaps — not building new features — is the entire launch work.

The recommended approach is to execute the launch in six phases following a strict infrastructure-before-application ordering: provision prod infra with corrected SKUs, wire identity and admin consent, load secrets, harden the network, deploy the backend, and publish the Copilot agent. Before any real user reaches the system, a controlled E2E must pass against real Azure services using a synthetic test client. RGPD compliance (DPIA or documented decision, data-access audit trail, PII-in-logs fix, EU residency confirmation) is a go-live gate, not a post-launch task. The solo-operator model demands that monitoring, alerting, and five runbooks (deploy, rollback, secret rotation, incident triage, kill-switch) are live before the team is invited.

The dominant risks are: (1) in-memory state (rate limit, IDOR map, JWKS cache) that breaks correctness and security guarantees if the gateway ever runs more than one instance — this requires an explicit single-instance decision before go-live; (2) JOBS_BASE_DIR pointing at ephemeral per-instance temp storage, which silently loses OCR output and FIC drafts between Durable activities; (3) OBO admin consent that must be granted in the production tenant before any user touches the app (AADSTS65001 is a blocking pre-flight, not a runtime surprise); and (4) RGPD obligations that cannot be met by documentation alone — specifically the missing document-access audit trail, which requires real code. Every one of these is resolvable without a rewrite; the research gives precise mitigations.

---

## Key Findings

### Recommended Stack

The application stack is fully locked — research confirmed all six hosting decisions for deploying that exact stack to production. The one structural finding is that the existing `infra/main.bicep` targets development-tier SKUs throughout: App Service gateway on `F1` Free (no Always On, no SLA, no custom-domain TLS, CPU quota), Azure Functions on `Y1` Consumption (5-min execution cap that kills OCR-heavy audits, no VNet, cold starts), and Document Intelligence on `F0` (500 pages/month, 20 calls/min). All three are launch blockers.

**CRITICAL — CD pipeline gap:** `cd-staging.yml` does NOT deploy to Azure. It packages a zip and prints a checklist. A real production CD pipeline (`cd-prod.yml`) with OIDC federated credentials and a GitHub `production` Environment with manual approval gate is greenfield work.

**Core technology decisions (all HIGH confidence):**
- **App Service (Linux) B1** for FastAPI gateway — Always On, SLA, custom-domain TLS; upgrade from current `F1` (launch blocker)
- **Flex Consumption + 2 always-ready instances** for Durable Functions — replaces current `Y1`; kills cold starts, adds VNet for private KV routing; NOTE: in-place migration from Y1 to Flex is NOT supported — requires creating a new Functions app
- **Key Vault references + System-Assigned MI** for all secrets — zero cleartext in app settings; proven in staging
- **OIDC federated credentials + GitHub `production` Environment** for CD — removes long-lived deploy secret; manual approval gate for solo operator; currently greenfield
- **Document Intelligence S0** — replaces current `F0`; removes the 500-page/month cap; enables `disableLocalAuth=true` (Entra-only)
- **Copilot Studio: 1:1 personal install only** — OBO + SharePoint RAG are ONLY supported in 1:1 chats; distributing as a channel/group bot silently breaks the entire auth and RAG model

### Expected Features

Research defines "features" as the go-live capabilities (observability, reliability, operability, compliance, controlled-rollout mechanics). Application features (audit pipeline, FIC generation, RAG, SSO, IDOR guards) are already built and out of scope.

**Must have — go-live gates (P1):**
- App Insights mandatory on gateway and Functions; failure + availability + budget alerts wired and firing
- `/health` (liveness) + `/ready` (readiness) endpoints; Standard availability test + alert
- Storage data-protection: GRS/RA-GRS + blob soft-delete + container soft-delete + PITR (Durable task hub state)
- All secrets in Key Vault; OBO client-secret expiry tracked; secret-rotation runbook written before launch
- Five runbooks: deploy, rollback, secret rotation, incident triage, feature-flag kill-switch
- Three code fixes: (a) OBO transient retry with bounded backoff, (b) `owner_hash` hashed from Entra Object ID not UPN (UPN hash is a real PII-access bug on user re-provisioning), (c) client-facing error + App Insights trace redaction for PII
- Document-access audit trail (user-id-hash, doc-id, timestamp, verdict) to immutable log — the only RGPD item requiring new code; flagged as a compliance gap in CONCERNS.md
- RGPD pack: record of processing (Art. 30), DPIA or documented reasoned decision, retention policy + enforcement (Storage lifecycle + jobs TTL), PII-in-logs statement, DSR procedure
- Security evidence pack: data-flow diagram with trust boundaries, authN/Z description, threat-coverage matrix, dependency/vuln posture, accepted-risk register
- Controlled real-prod E2E with synthetic (not real-client) test data covering failure paths — green before opening to anyone
- Feature-flag gating to exactly the target team + Go/No-Go checklist signed

**Should have — post-pilot (P2):**
- Fabric graceful degradation (currently a full pipeline crash when Fabric is unavailable)
- Synthetic full-audit availability test (after core is stable)
- SLO + error-budget definition
- Secret-expiry calendar automation

**Defer — future milestone (P3):**
- Active/passive multi-region DR (overkill for 20-100 users)
- Redis distributed rate-limiting (limits bite at 10K+ users)
- Rich admin dashboard, batch/export, new audit types (explicit PROJECT.md deferrals)
- Horizontal scale-out (Redis IDOR map, distributed JWKS)

### Architecture Approach

The production topology is the existing `infra/main.bicep` applied with `prod.parameters.json` into a new `rg-ac360-prod` resource group in an EU region. No architectural redesign. Staging stays as-is as the rehearsal environment.

The recommended networking posture for go-live is NOT a full VNet lockdown — that is a solo-operator operability tax with marginal threat-model benefit for a Teams-only internal audience. Instead: minimal VNet for both apps + Key Vault Private Endpoint (the highest-value secret boundary), OCR Entra-only (`disableLocalAuth=true`), public-but-Entra/MI-gated access everywhere else. The Bicep params already support full private link as an additive future step.

**Major components (prod):**
1. **ac360-gateway-prod (App Service B1)** — FastAPI/Uvicorn; validates user JWT (JWKS), rate-limits (single-instance, in-memory safe), feature-gates, OBO exchange; System-Assigned MI; ingress locked to gateway outbound IPs; single instance (load-bearing for in-memory state)
2. **ac360-func-prod (Flex Consumption, 2 always-ready)** — Durable orchestrator + activities; download -> OCR -> Fabric lookup -> compare -> verdict -> FIC; identity-based AzureWebJobsStorage (no Shared Key); System-Assigned MI for Storage, OCR (Entra-only), Fabric (read-only), SharePoint (OBO user-delegated)
3. **ac360-kv-prod (Key Vault, RBAC, purge protection, Private Endpoint)** — OBO client secret, function key, Teams webhook; zero cleartext secrets in app settings
4. **Copilot Studio PROD environment (EU region, fixed at creation)** — Teams agent; SSO via Entra; OBO+SharePoint RAG in 1:1 chats only; `useModelKnowledge=false`, uniform High moderation, validator gate
5. **Storage account (GRS, soft-delete, PITR, no Shared Key)** — Durable task hub + transient job artifacts via JOBS_BASE_DIR (single-activity chain required)
6. **Application Insights + Log Analytics (EU region)** — mandatory for both apps; telemetry-side PII transform; deliberately short retention

**Deploy order invariant (cannot be resequenced):**

```
Pre-reqs (tenant/PP) -> Provision core infra -> Wire identity ->
Load secrets -> Harden network -> Deploy backend -> Publish Copilot ->
Controlled E2E -> Open to team
```

### Critical Pitfalls

**Pitfall 1 — LOAD-BEARING: In-memory state breaks on scale-out (rate limit, IDOR map, JWKS)**
The FastAPI gateway keeps rate-limit counters, the audit-job ownership map, and the JWKS cache in per-process Python dicts. On more than one App Service instance these diverge: rate limits become N x the configured limit, IDOR ownership checks can fail on "cold" instances, JWKS can serve stale keys. This is a security guarantee failure, not a performance issue.
Prevention: pin the gateway to a single instance (scale-out max = 1, one Uvicorn worker) and document it as load-bearing in IaC. Verify the durable `owner_hash` check is the authoritative IDOR gate (in-memory map = cache only, never the decision point).

**Pitfall 2 — LOAD-BEARING: JOBS_BASE_DIR on ephemeral per-instance Functions temp**
Durable pipeline writes downloaded documents, OCR output, and FIC drafts to `JOBS_BASE_DIR/{document_id}/`. On Azure Functions, per-instance temp is not shared and is wiped on restart or after ~12h. If download and OCR activities run on different workers, OCR gets file-not-found. FIC drafts can vanish before the user fetches them.
Prevention: confirm the entire download->OCR->compare->FIC chain runs in a single Durable activity (no cross-worker file handoff). If not, mount Azure Files or pass artifacts via Blob Storage. Define a retention/cleanup job (also RGPD).

**Pitfall 3 — BLOCKING PRE-FLIGHT: OBO admin consent missing in prod tenant (AADSTS65001)**
OBO is non-interactive. If the production app registration has not been granted admin consent for its delegated Graph scopes in the production tenant, every user fails auth with no prompt. Invisible in dev/test tenants with user-consent enabled.
Prevention: admin consent is a deployment prerequisite, not a runtime task. Add to deploy checklist. Verify before the controlled E2E. Single-source three values that must match: `aud`/App ID URI in app config, Copilot Studio action resource, app registration.

**Pitfall 4 — SILENT GUARDRAIL BYPASS: Copilot Studio publish drift**
Connection references, Teams SSO, and the hardened guardrail posture (`useModelKnowledge=false`, High moderation, validator gate) do not automatically carry from the repository to the published agent. A stale or misconfigured publish ships weaker guardrails to users with no warning.
Prevention: prod-publish checklist (re-bind connection refs, reconfigure Teams SSO + republish, validate live guardrails against repo via `validate_copilot_yaml.py`). Publish off-hours (SSO changes take hours to propagate).

**Pitfall 5 — SKU BLOCKER: Dev-tier Bicep SKUs in current `infra/main.bicep`**
Gateway `F1` (no Always On, CPU quota, no SLA), Functions `Y1` Consumption (5-min execution cap kills OCR-heavy audits, cold starts, no VNet), Document Intelligence `F0` (500-page/month cap). All three are launch blockers.
Prevention: `prod.parameters.json` with `B1` gateway, Flex Consumption Functions (new app — no in-place migration from Y1), `S0` DocIntel. Verify `host.json` extension bundle `[4.0.0, 5.0.0)`.

**Pitfall 6 — RGPD: PII in Application Insights + missing document-access audit trail**
`safe_logger.redact()` uses allowlist-by-pattern and misses arbitrary client business data in exception messages and App Insights telemetry. No audit trail of who accessed which document exists (CONCERNS.md flags this as a compliance gap).
Prevention: audit all telemetry and error-response paths; add App Insights telemetry processor to drop/hash PII; set short EU-region retention. Add document-access log (user-id-hash, doc-id, timestamp, verdict) to immutable store before go-live.

---

## Implications for Roadmap

Based on the combined research, a 6-phase structure is recommended. The ordering reflects hard dependency constraints from the deploy order invariant in ARCHITECTURE.md and the pitfall-to-phase mapping from PITFALLS.md.

### Phase 1: Deep Code Audit and Critical Fixes

**Rationale:** Before any prod infrastructure is provisioned with real data in flight, the codebase must be confirmed correct under prod-topology assumptions. Several mitigations were written/tested against a single-process local model and silently break on Azure compute. Fixes must be in the repo before the first prod deploy.
**Delivers:** confirmed single-instance gateway decision (pinned in IaC); verified durable `owner_hash` is the authoritative IDOR gate; `owner_hash` hashed from Entra Object ID (not UPN); OBO bounded-backoff retry; client-facing error + App Insights trace redaction; document-access audit trail code; JOBS_BASE_DIR single-activity audit result; written security posture document (feeds Phase 5).
**Addresses:** FEATURES P1 code fixes (OBO retry, owner_hash, PII redaction, audit trail)
**Avoids:** Pitfalls 1 (in-memory scale-out), 2 (JOBS_BASE_DIR), 6 (PII in telemetry), 8 (audit confirms presence not validity)
**Research flag:** Skip — all items precisely specified in CONCERNS.md and PITFALLS.md

### Phase 2: Infrastructure Provisioning (prod SKUs, identity, network)

**Rationale:** MIs do not exist until provisioned; role grants require MIs; KV references do not resolve until grants exist. Network hardening must happen before backend deploy (not after) to avoid breaking KV references mid-flight. Exact deploy order invariant from ARCHITECTURE.md Section 6.
**Delivers:** `rg-ac360-prod` in EU region; corrected SKUs (B1 gateway, new Flex Consumption Functions app, S0 DocIntel); prod app registrations (AC360-API-prod no secret, OBO confidential client + secret in KV); OBO admin consent granted in prod tenant; MI role assignments (KV Secrets User, Storage Data Contributor x3, Cognitive Services User, Fabric Viewer/DefaultReader, SharePoint Sites.Selected via PIM-elevated session); Key Vault Private Endpoint + minimal VNet; `docIntelDisableLocalAuth=true`; `allowSharedKeyAccess=false`; identity-based `AzureWebJobsStorage`; all secrets loaded; GRS + soft-delete + PITR on Storage; unique Task Hub name for prod; all Bicep `location` params explicit to EU region.
**Addresses:** FEATURES infra items; STACK all six hosting decisions
**Avoids:** Pitfalls 3 (consent as deploy step — blocking pre-flight), 5 (dev-tier SKUs); ARCHITECTURE anti-patterns 1-5
**Research flag:** Skip — STACK.md and ARCHITECTURE.md fully specify all decisions including Flex migration constraint

### Phase 3: Backend Deploy and Observability

**Rationale:** With infra live and secrets resolvable, the backend can be deployed. Observability must be live in the same phase and before the E2E — the whole point of the controlled E2E is to watch the pipeline through monitoring.
**Delivers:** `cd-prod.yml` GitHub Actions pipeline (OIDC, `workflow_dispatch`, `production` environment with manual approval gate, what-if gate before apply); gateway + Function zip-deployed to prod (from Phase 1 fixed codebase); `/health` + `/ready` endpoints; App Insights mandatory on both apps; failure alerts (Functions errors, 5xx, dependency failures); Standard availability test + alert; FinOps budget alert wired to notification sink; minimal ops dashboard (App Insights Workbook); five runbooks written and tested (deploy, rollback, secret rotation, incident triage, kill-switch).
**Addresses:** FEATURES observability and reliability items; STACK CD decision (greenfield — cd-staging.yml does not deploy)
**Avoids:** The cd-staging gap (real prod CD must be written, not adapted from the non-deploying staging workflow)
**Research flag:** Skip — standard GitHub Actions + App Insights patterns

### Phase 4: Copilot Studio Production Publish

**Rationale:** Depends on the gateway URL being live (Phase 3). Isolated as its own phase because Power Platform operations have their own failure modes independent of the Azure backend.
**Delivers:** prod Copilot Studio environment confirmed in EU region; agent imported; connection references rebound to prod endpoints; action endpoint set to prod gateway URL with audience AC360-API-prod; Teams SSO reconfigured (Authenticate with Microsoft) and republished; guardrails validated live (`useModelKnowledge=false`, High moderation, validator gate) against hardened repo via `validate_copilot_yaml.py`; agent published to Teams for target team (1:1 personal install only — not channel/group bot).
**Addresses:** FEATURES controlled go-live mechanics (Copilot side); STACK Copilot distribution decision
**Avoids:** Pitfall 4 (publish drift, SSO misconfiguration, stale guardrails); 1:1-only constraint (OBO+RAG break in channels)
**Research flag:** MEDIUM — Copilot Studio platform changes fast; validate publish checklist against current Microsoft Learn at execution time

### Phase 5: RGPD and Security Evidence Pack

**Rationale:** Produces all evidence required before real users or real client data are admitted. DPO engagement starts day one (external dependency — long-pole item). Code items from Phase 1 are prerequisites for the PII-in-logs statement and access trail. Can run in parallel with Phases 3-4 for the documentation-only items.
**Delivers:** record of processing (Art. 30 entry with DPO); DPIA or documented reasoned decision (CNIL PIA tool); data-retention policy + enforcement (Storage lifecycle rule + jobs TTL cleanup); PII-in-logs statement + App Insights telemetry processor; DSR procedure; data-flow diagram with trust boundaries; authN/Z description; threat-coverage matrix (OWASP/LLM risks -> mitigation -> test); dependency/vuln posture (Dependabot enabled; PyJWT, deltalake pin policy documented); accepted-risk register; EU data-residency confirmation (Fabric capacity region, M365 tenant geo, Power Platform env region, explicit Bicep location params).
**Addresses:** All FEATURES RGPD and security review readiness items
**Avoids:** Pitfall 6 (RGPD accountability gap); Pitfall 7 (E2E with real PII before DPIA exists)
**Research flag:** Skip — CNIL sources cited in FEATURES.md; items are precise

### Phase 6: Controlled E2E, Go/No-Go, and Team Rollout

**Rationale:** Final gate. Full stack live, observability on, DPIA in place before any real client data flows. Uses synthetic test data.
**Delivers:** controlled E2E using synthetic test client/doc covering: happy path, large/garbled scan (OCR timeout/retry), CLIENT_NON_TROUVE, Fabric-down simulation, ECART verdict + FIC generation, cross-instance IDOR backstop (poll after restart), App Insights grep for test client PII (proves no leak); Go/No-Go checklist signed by operator; pilot cohort (2-5 users) then full team after 24-48h clean signal.
**Addresses:** FEATURES controlled go-live mechanics; PROJECT.md launch gate
**Avoids:** Pitfall 7 (real PII before DPIA; happy-path-only test)
**Research flag:** Skip

### Phase Ordering Rationale

- Phase 1 before Phase 2: fixes (`owner_hash`, IDOR gate, PII redaction, audit trail) must be in the repo before the first prod deploy. Patching a live system is riskier than fixing the code first.
- Phase 2 before Phase 3: MIs and role grants must exist before KV references resolve at app startup; network hardening before deploy avoids the fail-if-KV-goes-private-after-deploy trap.
- Phase 3 before Phase 4: Copilot Studio action requires the prod gateway URL and `AC360-API-prod` audience.
- Phase 5 runs in parallel with Phases 3-4 for docs-only items; DPO engagement starts on day one. DPIA must complete before Phase 6.
- Phase 6 is the final gate — depends on all previous phases and Go/No-Go checklist.

### Research Flags Summary

| Phase | Flag | Reason |
|-------|------|--------|
| Phase 1 | Skip | All items specified precisely in CONCERNS.md + PITFALLS.md |
| Phase 2 | Skip | STACK.md + ARCHITECTURE.md fully specify all decisions |
| Phase 3 | Skip | Standard GitHub Actions + App Insights patterns |
| Phase 4 | MEDIUM | Copilot Studio platform changes fast; validate publish checklist before executing |
| Phase 5 | Skip | CNIL sources cited; RGPD items are precise |
| Phase 6 | Skip | Standard patterns |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All six hosting decisions verified against Microsoft Learn (2026-02 to 2026-06 revisions); confirmed against live infra/main.bicep |
| Features | HIGH | Azure ops facts verified against Microsoft Learn; RGPD facts verified against CNIL; gap analysis drawn from CONCERNS.md (primary source) |
| Architecture | HIGH | Grounded in live audited staging topology + two decision-critical facts verified against current Microsoft Learn |
| Pitfalls | HIGH | Platform pitfalls verified against Microsoft Learn; AC360-specific pitfalls drawn from CONCERNS.md + codebase architecture map |

**Overall confidence:** HIGH

### Gaps to Address

- **Flex Consumption migration:** in-place migration from Y1 to Flex is not supported — a new Functions app must be created. Verify this does not break any staging workflow before executing on prod.
- **Document Intelligence in France Central:** DocIntel Form Recognizer SKU/region pair availability in France Central should be confirmed at provisioning time; West Europe is the confirmed fallback.
- **Fabric capacity region:** must be verified against the live GEREP tenant before provisioning — research confirms France Central supports all Fabric workloads but cannot confirm the tenant's actual capacity configuration.
- **M365 tenant data location:** SharePoint/M365 tenant default geo must be confirmed as France/EU in the GEREP tenant. Cannot be verified from research alone.
- **OBO Graph scope list:** exact delegated scopes should be verified against the live staging app registration before replicating to prod (HIGH confidence in principle; MEDIUM for exact scope list).
- **Copilot Studio publish UI:** MEDIUM confidence due to platform change velocity; validate the publish checklist against current Microsoft Learn at execution time.

---

## Sources

### Primary (HIGH confidence)

- Microsoft Learn — Azure Functions Flex Consumption plan (rev 2026-03-18): Durable Functions support, always-ready, VNet, Python 3.12, 30s init timeout, no in-place migration, runtime 4.x
- Microsoft Learn — App Service plans overview (rev 2026-03-13): Free/Shared are dev/test only; Basic+ for dedicated compute with SLA
- Microsoft Learn — Use Key Vault references as app settings (rev 2026-04-09): @Microsoft.KeyVault syntax, MI default, 24h rotation, connection string not a secret
- Microsoft Learn — Connect and configure an agent for Teams and M365 Copilot (rev 2026-05-01): publish flow; SharePoint-auth knowledge unsupported in group/channel chats (1:1 only)
- Microsoft Learn — Configure Durable Functions App With Managed Identity (rev 2026-05-20): identity-based AzureWebJobsStorage, 3 Storage Data Contributor roles, extension >=2.7.0
- Microsoft Learn — Fabric region availability (rev 2026-03-05): France Central in "All workloads"; data residency follows capacity region
- Microsoft Learn — Disaster Recovery and Geo-Distribution in Durable Functions; Performance and Scale in Durable Functions; Storage considerations for Azure Functions (temp not shared, Azure Files for scale-out)
- Microsoft Learn — Application Insights availability tests; Manage personal data in Azure Monitor Logs (Purge API)
- CNIL — Carrying out a DPIA if necessary; Guidelines on DPIA (>=2-of-9 criteria mandatory); Practice Guide Security of Personal Data (2024)
- AC360 codebase: infra/main.bicep, infra/README.md, docs/security/SECURITY_AUDIT_STAGING.md, docs/governance/GOVERNANCE.md, .github/workflows/cd-staging.yml (confirmed: does NOT deploy to Azure — packages zip only)
- AC360 planning: .planning/codebase/CONCERNS.md, .planning/codebase/ARCHITECTURE.md, .planning/codebase/TESTING.md, .planning/PROJECT.md

### Secondary (MEDIUM confidence)

- Microsoft Copilot Studio — connection references per environment; SSO configuration (platform-version-sensitive)
- AADSTS65001 admin-consent requirement for non-interactive OBO — Microsoft Community Hub + Microsoft Q&A

---
*Research completed: 2026-06-13*
*Ready for roadmap: yes*
