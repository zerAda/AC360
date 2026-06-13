# Roadmap: AC360 — Production Launch

## Overview

This milestone takes the feature-complete, security-hardened AC360 assistant from an undeployed repository to a live, compliant production service for one internal team (20–100 users, one operator). It is a deploy-and-harden effort, not a build — no new application features. The journey follows a hard, non-resequenceable deploy-order invariant: first re-audit the codebase and land the launch-blocking fixes in the repo, then provision production infrastructure with corrected SKUs and identity, then deploy the backend with observability live, then publish the Copilot agent to Teams, then assemble RGPD and security evidence (DPO work starting on day one, in parallel), and finally run a controlled real-prod E2E on synthetic data before a gated, gradual rollout to the team.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Deep Code Audit & Critical Fixes** - Re-validate hardening under prod (multi-worker) topology and land launch-blocking code fixes in the repo
- [ ] **Phase 2: Production Infrastructure Provisioning** - Stand up `rg-ac360-prod` in an EU region with corrected SKUs, identity, secrets, and minimal network hardening
- [ ] **Phase 3: Backend Deploy & Observability** - Deploy the fixed backend via a real prod CD pipeline with monitoring, alerting, and five solo-operator runbooks live
- [ ] **Phase 4: Copilot Studio Production Publish** - Publish the hardened agent to Teams 1:1 with rebound prod connections, SSO, and validated live guardrails
- [ ] **Phase 5: RGPD & Security Evidence Pack** - Produce the compliance and security-review evidence required before any real user or client data
- [ ] **Phase 6: Controlled E2E, Go/No-Go & Team Rollout** - Prove the full stack against real services on synthetic data, then gate and roll out to the team

## Phase Details

### Phase 1: Deep Code Audit & Critical Fixes
**Goal**: The committed hardening is re-validated against the production multi-worker topology, and every launch-blocking code fix is landed in the repo before the first prod deploy.
**Depends on**: Nothing (first phase)
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04, AUD-05, AUD-06, AUD-07, AUD-08
**Success Criteria** (what must be TRUE):
  1. Each "Addressed" mitigation is re-checked under an N>1-instance threat model; the gateway is pinned to a single instance (scale-out max = 1, one worker) and documented as load-bearing in IaC for in-memory state (rate limit, JWKS, ownership map).
  2. `owner_hash` is derived from the Entra Object ID (not UPN), and a cross-instance IDOR test confirms the durable `owner_hash` check is the authoritative gate (in-memory map is cache only).
  3. OBO token exchange retries transient failures with bounded exponential backoff, and client-facing error responses plus App Insights traces are redacted of PII/secrets.
  4. A document-access audit trail (user-id hash, document id, timestamp, verdict) is written to an immutable log.
  5. The download → OCR → compare → FIC chain is confirmed to keep `JOBS_BASE_DIR` artifacts available across the pipeline (single-activity or shared-store), with a written security-posture document feeding Phase 5.
**Plans**: TBD
**Risks**: Exact OBO delegated Graph scope list must be verified against the live staging app registration before being relied on in fixes/tests.

### Phase 2: Production Infrastructure Provisioning
**Goal**: A production resource group exists in an EU region with production-tier SKUs, wired identity and admin consent, secrets in Key Vault, and the minimal network hardening — all provisioned in the dependency-correct order before any backend deploy.
**Depends on**: Phase 1
**Requirements**: INF-01, INF-02, INF-03, INF-04, INF-05, INF-06, INF-07, INF-08, INF-09
**Success Criteria** (what must be TRUE):
  1. `rg-ac360-prod` is provisioned in an EU region with all Bicep `location` params set explicitly, running the gateway on App Service B1 (Always On), Durable Functions on a new Flex Consumption app, and Document Intelligence on S0 with `disableLocalAuth=true`.
  2. Production app registrations exist (API audience with no secret; OBO confidential client with secret in Key Vault), and OBO admin consent is granted in the production tenant for the required delegated Graph scopes (verified blocking pre-flight — no AADSTS65001).
  3. System-assigned Managed Identity role assignments are wired (Key Vault Secrets User, Storage Data Contributor, Cognitive Services User, Fabric read, SharePoint OBO), and all secrets resolve via Key Vault references + MI with zero cleartext in app settings.
  4. Key Vault has a Private Endpoint behind a minimal VNet; the Storage account has GRS/RA-GRS + blob & container soft-delete + PITR, identity-based `AzureWebJobsStorage` (`allowSharedKeyAccess=false`), and a unique production Task Hub name.
**Plans**: TBD
**Risks**: EU residency of the M365 tenant geo, Fabric capacity region, and DocIntel Form Recognizer availability in France Central must each be verified against the live GEREP tenant at provisioning time (West Europe is the confirmed DocIntel fallback). In-place Y1→Flex migration is unsupported — a new Functions app must be created.

### Phase 3: Backend Deploy & Observability
**Goal**: The fixed backend is deployed to production through a real, gated CD pipeline, with monitoring, alerting, a one-pane dashboard, and the five solo-operator runbooks live and tested before any end-to-end test.
**Depends on**: Phase 2
**Requirements**: CD-01, CD-02, OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05
**Success Criteria** (what must be TRUE):
  1. A real `cd-prod.yml` pipeline (OIDC federated credentials, `production` GitHub Environment with manual approval, Bicep what-if gate) deploys the fixed gateway + Functions to production, and the prod gateway answers `/health` 200 and `/ready` over Entra-gated TLS.
  2. Application Insights is wired on both the gateway and the Functions app; failure alerts fire on Functions/orchestration errors, gateway 5xx, and dependency failures (OCR/Fabric/Graph); a Standard availability test + alert run against the health endpoints.
  3. A FinOps budget alert is wired to a real notification sink (Teams webhook and/or Azure Cost Management), and a one-pane ops dashboard shows last-24h audits, error rate, p95 latency, and budget %.
  4. Five runbooks exist and are tested for a single operator: deploy (with MI / Key Vault-reference verification), rollback (<10-min path with defined trigger and known-good marker), secret rotation (per secret, including OBO app-registration steps, expiries tracked), incident triage (alert → cause → first action), and feature-flag kill-switch.
**Plans**: TBD
**Risks**: `cd-staging.yml` does NOT deploy to Azure (packages a zip only) — the prod CD pipeline is greenfield and must not be assumed to be an adaptation of staging.

### Phase 4: Copilot Studio Production Publish
**Goal**: The hardened agent is published to Teams for the target team as a 1:1 personal install, pointed at the live prod gateway, with SSO reconfigured and live guardrails validated against the repo.
**Depends on**: Phase 3
**Requirements**: PUB-01, PUB-02, PUB-03, PUB-04, PUB-05
**Success Criteria** (what must be TRUE):
  1. The production Copilot Studio environment is confirmed in an EU region, with connection references rebound to prod endpoints and the action endpoint set to the prod gateway URL using the prod API audience.
  2. Teams SSO is reconfigured and the agent republished; a real Teams 1:1 sign-in completes without repeated prompts or auth failure.
  3. Live guardrails are validated against the hardened repo (`useModelKnowledge=false`, uniform High moderation, validator gate) — a known-blocked prompt is blocked against the live agent.
  4. The agent is published to Teams for the target team as a 1:1 personal install (OBO + SharePoint RAG require 1:1 chats — not a channel/group bot).
**Plans**: TBD
**UI hint**: yes
**Risks**: Copilot Studio publish UI changes fast (MEDIUM research confidence) — validate the publish checklist against current Microsoft Learn at execution time; SSO changes can take hours to propagate, so publish off-hours.

### Phase 5: RGPD & Security Evidence Pack
**Goal**: All compliance and security-review evidence required before real users or real client data is produced and assembled, with the DPIA complete before the controlled-E2E phase.
**Depends on**: Phase 1 (code prerequisites: audit trail, PII-in-logs redaction); documentation work runs in parallel with Phases 3–4
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, RGP-01, RGP-02, RGP-03, RGP-04, RGP-05, RGP-06
**Success Criteria** (what must be TRUE):
  1. A security evidence pack exists: architecture + data-flow diagram with trust boundaries, authN/authZ description linked to existing tests, threat-coverage matrix (OWASP/LLM → mitigation → test), documented dependency/vuln posture (Dependabot on; PyJWT/deltalake pin policy), and an accepted-risk / known-issues register.
  2. The RGPD record of processing (Art. 30) is created with the DPO, and a DPIA is completed (or a documented reasoned CNIL ≥2-of-9 decision not to) before Phase 6 begins.
  3. A data-retention policy for jobs/OCR/FIC artifacts is defined and enforced (Storage lifecycle rule + `JOBS_BASE_DIR` TTL cleanup), and a PII-in-logs handling statement plus App Insights telemetry processor with short EU-region retention is in place.
  4. A data-subject request (DSR) procedure is documented, and EU data-residency is confirmed across Fabric capacity region, M365 tenant geo, Power Platform env region, and Bicep locations.
**Plans**: TBD
**Risks**: DPIA/record-of-processing is the long-pole docs item (depends on the DPO, external to the operator) — engage day one. EU-residency confirmation (Fabric capacity, M365 tenant geo) cannot be verified from research alone and must be checked against the live tenant.

### Phase 6: Controlled E2E, Go/No-Go & Team Rollout
**Goal**: The full production stack is proven against real Azure services using synthetic test data across happy and failure paths, then gated to exactly the target team and rolled out gradually after a signed Go/No-Go and a clean pilot signal.
**Depends on**: Phases 1–5 (full stack live, observability on, DPIA complete)
**Requirements**: GO-01, GO-02, GO-03, GO-04
**Success Criteria** (what must be TRUE):
  1. A controlled real-prod E2E against real Azure services using a synthetic test client/document produces the expected verdict across happy path + failure paths (OCR timeout, CLIENT_NON_TROUVE, Fabric-down, ECART+FIC), with a telemetry check proving no PII in App Insights.
  2. Feature-flag gating restricts access to exactly the target team at launch, and a Go/No-Go checklist is signed by the operator.
  3. A gradual rollout is executed: a pilot cohort of 2–5 users, then the full team after a 24–48h clean signal.
**Plans**: TBD
**Risks**: The E2E must use synthetic (not real-client) data and must restart the Functions app between download and FIC retrieval to prove cross-instance file durability; skipping failure paths or using real PII before the DPIA exists would invalidate the gate.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6
(Phase 5 documentation-only items may run in parallel with Phases 3–4; DPIA must complete before Phase 6.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Deep Code Audit & Critical Fixes | 0/TBD | Not started | - |
| 2. Production Infrastructure Provisioning | 0/TBD | Not started | - |
| 3. Backend Deploy & Observability | 0/TBD | Not started | - |
| 4. Copilot Studio Production Publish | 0/TBD | Not started | - |
| 5. RGPD & Security Evidence Pack | 0/TBD | Not started | - |
| 6. Controlled E2E, Go/No-Go & Team Rollout | 0/TBD | Not started | - |
