# Requirements: AC360 — Production Launch

**Defined:** 2026-06-13
**Core Value:** AC360 is live in production — a 20–100 person team can reliably and compliantly audit client documents from Teams, end-to-end, and one person can operate it with confidence.

> Scope note: This milestone **deploys and hardens the existing, feature-complete AC360** for first production launch. "Requirements" here are launch-readiness capabilities (audit/fix, infra, observability, ops, compliance, controlled rollout) — NOT new application features. Application features (audit pipeline, FIC generation, RAG, SSO, IDOR guards) already exist and are out of scope (see Out of Scope).

## v1 Requirements

Go-live gate (P1). Each maps to a roadmap phase.

### Audit & Critical Fixes

- [ ] **AUD-01**: Deep code audit of existing AC360 re-validates every "addressed" mitigation under production (multi-worker) topology and surfaces launch-relevant bugs
- [ ] **AUD-02**: `owner_hash` is derived from the Entra **Object ID**, not UPN (closes PII-access bug on user re-provisioning)
- [ ] **AUD-03**: The durable `owner_hash` check is the authoritative IDOR gate; the in-memory ownership map is treated as cache only
- [ ] **AUD-04**: Gateway is pinned to a single instance (scale-out max = 1, one worker) and documented as load-bearing for in-memory state (rate limit, JWKS)
- [ ] **AUD-05**: OBO token exchange retries transient failures with bounded exponential backoff (no false 502 on first-call flakiness)
- [ ] **AUD-06**: Client-facing error responses and Application Insights traces are redacted of PII/secrets
- [x] **AUD-07**: Document-access audit trail (user-id hash, document id, timestamp, verdict) is written to an immutable log
- [x] **AUD-08**: The download → OCR → compare → FIC chain is confirmed to keep `JOBS_BASE_DIR` artifacts available across the pipeline (no cross-worker file loss)

### Infrastructure (prod provisioning)

- [ ] **INF-01**: Production resource group provisioned in an EU region with all Bicep `location` params set explicitly
- [ ] **INF-02**: FastAPI gateway runs on Azure App Service **B1** (replaces dev-tier F1) with Always On
- [ ] **INF-03**: Durable Functions run on a new **Flex Consumption** Functions app (replaces Y1; no OCR-killing 5-min cap, no cold starts)
- [ ] **INF-04**: Azure Document Intelligence on **S0** with `disableLocalAuth=true` (replaces F0)
- [ ] **INF-05**: Production app registrations exist (API audience with no secret; OBO confidential client with secret stored in Key Vault)
- [ ] **INF-06**: OBO admin consent granted in the production tenant for required delegated Graph scopes (blocking pre-flight)
- [ ] **INF-07**: System-assigned Managed Identity role assignments wired (Key Vault Secrets User, Storage Data Contributor, Cognitive Services User, Fabric read, SharePoint OBO)
- [ ] **INF-08**: All secrets in Key Vault via Key Vault references + MI; Key Vault Private Endpoint + minimal VNet; zero cleartext secrets in app settings
- [ ] **INF-09**: Storage account has GRS/RA-GRS + blob & container soft-delete + point-in-time restore; identity-based `AzureWebJobsStorage` (`allowSharedKeyAccess=false`); unique production Task Hub name

### Observability & Monitoring

- [ ] **OBS-01**: Application Insights mandatory and wired on both the gateway and the Functions app
- [ ] **OBS-02**: Failure alerts fire on Functions/orchestration errors, gateway 5xx, and dependency failures (OCR/Fabric/Graph)
- [ ] **OBS-03**: `/health` (liveness) and `/ready` (readiness) endpoints exist; a Standard availability test + alert run against them
- [ ] **OBS-04**: FinOps budget alert is wired to a real notification sink (Teams webhook and/or Azure Cost Management budget)
- [ ] **OBS-05**: A minimal one-pane ops dashboard shows last-24h audits, error rate, p95 latency, and budget %

### Deployment (CD)

- [ ] **CD-01**: A real `cd-prod.yml` pipeline exists (OIDC federated credentials, `production` GitHub Environment with manual approval, Bicep what-if gate before apply)
- [ ] **CD-02**: The fixed backend (gateway + Functions) is deployed to production via the pipeline

### Operability (runbooks for a solo operator)

- [ ] **OPS-01**: Deploy runbook (Bicep apply + Functions + App Service + Copilot publish, with MI / Key Vault-reference verification steps)
- [ ] **OPS-02**: Rollback runbook (<10-minute path back, defined trigger and known-good marker)
- [ ] **OPS-03**: Secret-rotation runbook (per secret, including OBO app-registration steps; expiry dates tracked)
- [ ] **OPS-04**: Incident-triage runbook (alert → likely cause → first action decision tree)
- [ ] **OPS-05**: Feature-flag kill-switch runbook (disable audit/OCR/RAG or block a user/team instantly)

### Copilot Studio Production Publish

- [ ] **PUB-01**: Production Copilot Studio environment confirmed in an EU region
- [ ] **PUB-02**: Connection references rebound to prod endpoints; action endpoint set to the prod gateway URL with the prod API audience
- [ ] **PUB-03**: Teams SSO reconfigured and the agent republished
- [ ] **PUB-04**: Live guardrails validated against the hardened repo (`useModelKnowledge=false`, uniform High moderation, validator gate)
- [ ] **PUB-05**: Agent published to Teams for the target team as a 1:1 personal install (OBO + SharePoint RAG require 1:1 chats)

### Security Review Evidence

- [ ] **SEC-01**: Architecture + data-flow diagram showing PII flow and trust boundaries
- [ ] **SEC-02**: AuthN/AuthZ description (Entra SSO, JWT RS256/JWKS, OBO scope, IDOR, read-only) linked to existing tests
- [ ] **SEC-03**: Threat-coverage matrix mapping OWASP/LLM risks → mitigation → test
- [ ] **SEC-04**: Dependency/vuln posture documented (Dependabot enabled; PyJWT/deltalake pin policy)
- [ ] **SEC-05**: Accepted-risk / known-issues register (CONCERNS.md items classified must-fix vs accepted)

### RGPD / Compliance Evidence

- [ ] **RGP-01**: Record of processing (Art. 30 entry) created with the DPO
- [ ] **RGP-02**: DPIA completed, or a documented reasoned decision not to (CNIL ≥2-of-9 criteria assessment)
- [ ] **RGP-03**: Data-retention policy for jobs/OCR/FIC artifacts, with enforcement (Storage lifecycle rule + `JOBS_BASE_DIR` TTL cleanup)
- [ ] **RGP-04**: PII-in-logs handling statement + App Insights telemetry processor; deliberate short EU-region log retention
- [ ] **RGP-05**: Data-subject request (DSR) procedure documented
- [ ] **RGP-06**: EU data-residency confirmed (Fabric capacity region, M365 tenant geo, Power Platform env region, Bicep locations)

### Controlled Go-Live

- [ ] **GO-01**: Controlled real-prod E2E against real Azure services using **synthetic** test client/document, covering happy path + failure paths (OCR timeout, CLIENT_NON_TROUVE, Fabric-down, ECART+FIC), with a telemetry check proving no PII leak
- [ ] **GO-02**: Feature-flag gating restricts access to exactly the target team at launch
- [ ] **GO-03**: Go/No-Go checklist signed by the operator
- [ ] **GO-04**: Gradual rollout executed (pilot cohort of 2–5, then full team after 24–48h clean signal)

## v2 Requirements

Post-pilot (P2). Tracked, not in this roadmap.

### Reliability+

- **REL-01**: Fabric graceful degradation / circuit breaker (return INCERTAIN/unavailable instead of crashing the pipeline)
- **REL-02**: Synthetic full-audit availability test (runs a real audit on a schedule)
- **OBS-06**: SLO + error-budget definition (e.g., 99% audit success)
- **OPS-06**: Automated secret-expiry calendar/alerting

## Out of Scope

Explicitly excluded for this milestone.

| Feature | Reason |
|---------|--------|
| New app features (new audit types, new topics, write/actions, batch, webhooks, integrations) | Deferred by PROJECT.md; bundling re-opens the threat model and delays a compliant launch |
| Multi-tenant / multi-team scale-out | Launch is for ONE team; multi-tenant changes auth/isolation/IDOR — huge review surface |
| Horizontal scale-out (Redis rate-limit, distributed cache/JWKS, BK-tree index) | All limits bite at 10K+ users / 100K+ customers — far beyond 20–100; gateway pinned single-instance instead |
| Full admin dashboard / BI / export | Real app feature; minimal 1-pane health workbook (OBS-05) ships instead |
| Custom backup tooling for Durable state | Azure Storage soft-delete + PITR + GRS (INF-09) already covers it |
| Re-architecting for resilience (circuit breakers everywhere, queue rework) | PROJECT.md forbids refactor; only targeted fixes (AUD-*) this milestone |
| External pen-test / formal certification | Disproportionate for an internal 20–100-user launch; internal review + honest risk register is the bar |
| Active/passive multi-region DR | Overkill for one internal team; revisit only if availability becomes contractual |

## Traceability

Populated during roadmap creation. Every v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUD-01 | Phase 1 | Pending |
| AUD-02 | Phase 1 | Pending |
| AUD-03 | Phase 1 | Pending |
| AUD-04 | Phase 1 | Pending |
| AUD-05 | Phase 1 | Pending |
| AUD-06 | Phase 1 | Pending |
| AUD-07 | Phase 1 | Complete |
| AUD-08 | Phase 1 | Complete |
| INF-01 | Phase 2 | Pending |
| INF-02 | Phase 2 | Pending |
| INF-03 | Phase 2 | Pending |
| INF-04 | Phase 2 | Pending |
| INF-05 | Phase 2 | Pending |
| INF-06 | Phase 2 | Pending |
| INF-07 | Phase 2 | Pending |
| INF-08 | Phase 2 | Pending |
| INF-09 | Phase 2 | Pending |
| CD-01 | Phase 3 | Pending |
| CD-02 | Phase 3 | Pending |
| OBS-01 | Phase 3 | Pending |
| OBS-02 | Phase 3 | Pending |
| OBS-03 | Phase 3 | Pending |
| OBS-04 | Phase 3 | Pending |
| OBS-05 | Phase 3 | Pending |
| OPS-01 | Phase 3 | Pending |
| OPS-02 | Phase 3 | Pending |
| OPS-03 | Phase 3 | Pending |
| OPS-04 | Phase 3 | Pending |
| OPS-05 | Phase 3 | Pending |
| PUB-01 | Phase 4 | Pending |
| PUB-02 | Phase 4 | Pending |
| PUB-03 | Phase 4 | Pending |
| PUB-04 | Phase 4 | Pending |
| PUB-05 | Phase 4 | Pending |
| SEC-01 | Phase 5 | Pending |
| SEC-02 | Phase 5 | Pending |
| SEC-03 | Phase 5 | Pending |
| SEC-04 | Phase 5 | Pending |
| SEC-05 | Phase 5 | Pending |
| RGP-01 | Phase 5 | Pending |
| RGP-02 | Phase 5 | Pending |
| RGP-03 | Phase 5 | Pending |
| RGP-04 | Phase 5 | Pending |
| RGP-05 | Phase 5 | Pending |
| RGP-06 | Phase 5 | Pending |
| GO-01 | Phase 6 | Pending |
| GO-02 | Phase 6 | Pending |
| GO-03 | Phase 6 | Pending |
| GO-04 | Phase 6 | Pending |

**Coverage:**

- v1 requirements: 49 total (AUD 8, INF 9, OBS 5, CD 2, OPS 5, PUB 5, SEC 5, RGP 6, GO 4)
- Mapped to phases: 49 ✓
- Unmapped: 0 ✓

> Count note: the prior header stated "44 total" as a round summary; the enumerated requirement IDs actually sum to **49**. All 49 are mapped here. Reconcile the summary figure if 44 was the intended hard count.

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after roadmap creation (traceability populated, 49/49 mapped)*
