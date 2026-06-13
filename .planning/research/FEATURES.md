# Feature Research

**Domain:** Production go-live readiness for an internal Azure-hosted AI assistant (French insurance / commercial client-data; RGPD applies to client PII)
**Researched:** 2026-06-13
**Confidence:** HIGH (Azure ops facts verified against Microsoft Learn; RGPD facts verified against CNIL; tailored to the AC360 codebase via `.planning/codebase/`)

> **Scope note.** "Features" here means the *capabilities of the launch itself* — observability, reliability, operability, security-review readiness, RGPD evidence, and controlled-rollout mechanics. The **application** features (audit pipeline, FIC generation, RAG, SSO, IDOR guards) are already built and are explicitly OUT of scope (see Anti-Features). Targets one internal team (20–100 users), one solo operator.
>
> **Legend.** `[DOCS]` = pure documentation/artifact, no code. `[INFRA]` = Azure/Bicep/portal config. `[CODE]` = application code change. `[PROC]` = a process/decision the operator performs once.

---

## Feature Landscape

### Table Stakes (Launch is irresponsible without these)

#### 1. Observability & Monitoring

| Feature | Why Expected | Complexity | Type | Notes |
|---------|--------------|------------|------|-------|
| App Insights wired end-to-end (gateway + Functions) | Cannot operate blind; `APPINSIGHTS_INSTRUMENTATIONKEY` is currently *optional* — must become mandatory in prod | LOW | INFRA | host.json already has AI sampling; ensure connection string set on App Service too, not just Functions |
| Failure alert: orchestration/audit failures | Solo operator must be paged when audits fail, not learn from users | LOW | INFRA | Alert on Functions `FunctionErrors` / failed orchestration count > 0 over 5 min |
| Failure alert: gateway 5xx / dependency failures | OBO, Graph, Fabric, OCR all fail externally; need signal | LOW | INFRA | Alert on requests `resultCode >= 500`; separate alert for dependency failures (OCR/Fabric/Graph) |
| Standard availability test on a health endpoint + alert | Detect "service down" before the team does | LOW | INFRA | App Insights **Standard test**; set `failedLocationCount = 1` only if single region, else default 2+ to avoid false positives. Requires a public unauthenticated `/health` (see Reliability) |
| FinOps budget alert actually firing | `AC360_BUDGET_EUR` / `AC360_BUDGET_WARN_PCT` already supported in code — must be wired to a real notification sink | LOW | INFRA+CODE | Code computes spend; connect `TEAMS_WEBHOOK_URL` and/or an Azure **Cost Management budget** alert on the resource group as a backstop |
| Minimal ops dashboard (1 pane) | Solo operator needs a single "is it healthy?" view: last-24h audits, error rate, p95 latency, budget % | LOW | INFRA | App Insights Workbook or a shared dashboard; CONCERNS.md flags "No Admin Dashboard" — the *lightweight* version is table stakes, the full app-feature dashboard is not |

#### 2. Reliability

| Feature | Why Expected | Complexity | Type | Notes |
|---------|--------------|------------|------|-------|
| `/health` (liveness) + `/ready` (readiness) endpoints | Required by the availability test and by App Service health-check probe | LOW | CODE | Liveness = process up; readiness = can reach Key Vault + Functions. Keep unauthenticated but information-free |
| Durable state + job-artifact backup | Task-hub state and job artifacts live in **one Azure Storage account**; losing it loses in-flight audits and downloadable results | LOW | INFRA | Per Microsoft Learn, all task-hub state is in the Storage account. Enable **blob soft-delete + container soft-delete + point-in-time restore**; choose **GRS/RA-GRS** redundancy. This is config, not a custom backup job |
| Secret rotation capability (Key Vault) | `OBO_CLIENT_SECRET`, `AZURE_OCR_KEY`, `AZURE_FUNCTION_KEY` will expire/leak; must be rotatable without redeploy | MEDIUM | INFRA+DOCS | Store all secrets in Key Vault, reference via Key Vault references / Managed Identity. Document expiry dates. OBO client secret has a hard Entra expiry — track it |
| Retry on OBO token exchange | CONCERNS.md: transient OBO failure returns 502 with no retry; first-call flakiness will look like an outage | LOW | CODE | Add bounded exponential backoff (existing OCR pipeline already models retry intent). Small, high-value |
| Graceful degradation when Fabric unavailable | CONCERNS.md "Fragile Areas": whole pipeline fails hard if Fabric is down; should return INCERTAIN/unavailable verdict, not a crash | MEDIUM | CODE | Optional for go-live if Fabric SLA is trusted; **strongly recommended** because Fabric is the single hardest dependency |
| Managed Identity verified on Functions runtime | CONCERNS.md: MI assumed without runtime verification; download fails cryptically if misprovisioned | LOW | INFRA+PROC | Verify during deploy, not in incident. Part of deploy runbook |

#### 3. Operability for ONE Person (Runbooks)

Non-negotiable minimum set. Each is `[DOCS]` (a written, tested runbook) unless noted.

| Runbook | Why Non-Negotiable | Complexity | Notes |
|---------|--------------------|------------|-------|
| **Deploy** | Repeatable prod deploy (Bicep apply + Functions + App Service + Copilot publish), with the MI/secret prerequisites checklist | MEDIUM | Tie to existing GitHub Actions `cd-staging.yml`; add prod. Include "verify MI" and "verify Key Vault references resolve" steps |
| **Rollback** | When a deploy breaks prod, solo operator needs a <10-min path back | MEDIUM | App Service deployment slots OR redeploy previous artifact + Bicep what-if. Define the rollback trigger and the known-good marker |
| **Secret rotation** | OBO secret / OCR key / function key rotation without downtime | MEDIUM | Step-by-step per secret, with the Entra app-registration steps for the OBO secret. Highest-friction runbook — write it before you need it |
| **Incident triage** | One person, no on-call team: decision tree from alert → likely cause → first action | MEDIUM | Map each alert (5xx, audit-fail, availability-down, budget) to a first diagnostic. Include "how to read App Insights failures" |
| **Feature-flag kill switch** | Instantly disable audit/OCR/RAG or block a user/team if something misbehaves with real PII | LOW | Pure docs — the code exists (`AC360_*_ENABLED`, `AC360_BLOCKED_*`). Document the exact env-var change and how it propagates |

#### 4. Security Review Readiness (evidence/artifacts)

Internal security reviews of an internal AI app on Azure typically ask for these as **evidence**, most of which already exist in the codebase and just need to be *assembled and pointed to*.

| Artifact | What Reviewer Expects | Complexity | Type | Notes |
|---------|----------------------|------------|------|-------|
| Architecture + data-flow diagram | Where PII flows: Teams → Copilot → gateway → Functions → SharePoint/OCR/Fabric; trust boundaries | LOW | DOCS | One diagram; trust boundary at each external call |
| AuthN/AuthZ description | Entra SSO, JWT RS256/JWKS, OBO delegated scope, IDOR `owner_hash`, read-only enforcement | LOW | DOCS | All implemented; describe + link tests (`test_auth_jwt`, `test_job_isolation`, IDOR E2E) |
| Secret-handling statement | No secrets in repo (Gitleaks in CI), Key Vault + MI, redacting logger | LOW | DOCS | Reference `test_no_forbidden_files.py`, `safe_logger`. **Fix first**: CONCERNS.md "Secrets in Error Messages" — error `detail`/JSON may leak unredacted; close before review |
| Threat-coverage matrix | Maps OWASP/LLM-top-risks → mitigation → test | MEDIUM | DOCS | Red-team suite exists (`tests/red_team/`); tabulate: IDOR, path traversal, injection, no-hallucination moderation gate, rate limit |
| Dependency / vuln posture | Pinned deps, Dependabot, known-at-risk libs | LOW | DOCS+INFRA | CONCERNS.md "Dependencies at Risk" (PyJWT, deltalake) — state pin policy + enable Dependabot |
| Known-issues register with risk acceptance | Honest list of residual risks + accept/mitigate decision | LOW | DOCS | Convert CONCERNS.md items into accepted-risk vs must-fix-before-launch. Reviewers trust honesty over a clean-but-hollow report |
| **Must-fix before review:** owner_hash IDOR on UPN reuse | CONCERNS.md: deleted/re-provisioned UPN regains prior user's jobs | LOW | CODE | Hash on Entra **Object ID** not UPN. Small change, real PII-access bug — do not present as "accepted" |

#### 5. RGPD / GDPR Evidence for Client PII

Concrete artifacts (CNIL-aligned), not "be compliant." For an internal launch these are the table-stakes set.

| Artifact | What It Is | Complexity | Type | Notes |
|---------|-----------|------------|------|-------|
| **Record of processing (registre / Art. 30)** | Entry describing AC360: purpose (document conformity audit), categories of client PII, recipients, retention, security measures | LOW | DOCS | Likely AC360 is a *new processing activity* on the company register — must be added. Often a 1-page form your DPO already templates |
| **DPIA — or documented decision not to** | Per CNIL: DPIA mandatory when **≥2 of the 9 criteria** met. AC360 plausibly hits: large-scale-ish processing + innovative tech (LLM/OCR on personal data) | MEDIUM | DOCS | If <2 criteria, you must still **document the reasoned decision** not to do one. Use the free **CNIL PIA tool**. Engage the DPO early — this is the long-pole item |
| **Data-retention policy for jobs/artifacts** | Audit jobs, OCR output, FIC drafts contain client PII; define retention + auto-deletion | LOW→MEDIUM | DOCS+CODE | Policy is docs; *enforcement* needs a TTL/cleanup on `JOBS_BASE_DIR` + storage lifecycle rule. Storage lifecycle = INFRA, low effort |
| **PII-in-logs handling statement** | Evidence that logs do not retain raw PII | LOW | DOCS | `safe_logger.redact()` exists + tested. **Fix first**: ensure errors returned to client + App Insights traces are redacted (CONCERNS.md). Set App Insights/Log Analytics retention deliberately |
| **Document-access audit trail** | Who accessed which client document, when, result | MEDIUM | CODE | CONCERNS.md "Missing Critical Features: No Audit Trail for Document Access" — flagged as a **GDPR/audit gap**. Log to App Insights/Log Analytics (immutable retention). This is the one RGPD item that needs real code and should be treated as table stakes |
| **Data-subject request (DSR) procedure** | How a client-PII access/erasure request is handled given AC360 holds only transient derived data | LOW | DOCS | AC360 is read-only over SharePoint/Fabric (system of record elsewhere); document that DSRs are served from source systems and that AC360's only retained PII is in jobs/artifacts (covered by retention policy) |

#### 6. Controlled Go-Live Mechanics

| Feature | Why Expected | Complexity | Type | Notes |
|---------|--------------|------------|------|-------|
| Real-prod controlled E2E with known test client/doc | The PROJECT.md launch gate: prove the full pipeline against real Azure services before any real user | MEDIUM | PROC | Pick a known SIRET/document with a known expected verdict. Run download→OCR→Fabric→verdict→FIC. CONCERNS.md flags the full real-service E2E as untested — this is where it gets covered |
| Feature-flag gating to exactly one team | Restrict to the target team at launch; flip off instantly if needed | LOW | DOCS+INFRA | Code exists (`AC360_BLOCKED_TEAMS`, per-team gates) + Copilot Studio publish-to-team scoping. Mostly configuration + the kill-switch runbook |
| Gradual rollout (pilot → team) | De-risk: a few friendly users before the full 20–100 | LOW | PROC | Day-1 cohort of 2–5, then widen after 24–48h clean signal. Pure process given the flag system |
| Go/No-Go checklist | Single gate that ties all the above into one decision | LOW | DOCS | Alerts firing? Backup on? Runbooks written? RGPD register entry done? E2E green? Owner_hash + log-leak fixed? |

---

### Differentiators (Strengthen the launch; not required)

| Feature | Value Proposition | Complexity | Type | Notes |
|---------|-------------------|------------|------|-------|
| Active/passive multi-region failover | Survives a regional Azure outage; shared Storage account + Task Hub keeps state | HIGH | INFRA | Microsoft's documented DR pattern (Traffic Manager). Overkill for one internal team — defer unless availability is contractual |
| Synthetic transaction test (full audit, not just ping) | Availability test that runs a real audit hourly, catching OCR/Fabric breakage | MEDIUM | CODE+INFRA | Stronger than `/health`; costs OCR/Fabric calls + budget. Nice once core is stable |
| Distributed rate-limit / cache (Redis) | Removes in-memory single-instance limits | MEDIUM | INFRA+CODE | CONCERNS.md scaling note — irrelevant at 20–100 users. Anti-feature *for this milestone* (see below) |
| SLO/error-budget definition | Turns "is it up?" into a managed target | LOW | DOCS | Lightweight (e.g. 99% audit success). Helps a solo operator decide when to stop firefighting |
| Automated dependency/expiry calendar | Alerts before OBO secret / OCR key expiry | LOW | INFRA | Prevents the classic "expired secret = silent outage". Cheap insurance |
| Circuit breaker on Fabric/OCR | Fail fast + auto-recover instead of hanging | MEDIUM | CODE | Upgrades the graceful-degradation table-stakes item |

---

### Anti-Features (Do NOT build this milestone)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **New app features** (new audit types, new topics, write/actions, batch, webhooks, external integrations) | They surface in CONCERNS.md "Missing Critical Features" and feel natural to add | PROJECT.md explicitly defers them; bundling them re-opens the threat model and delays a compliant launch | Ship the hardened read-only app; log feature requests for a future milestone |
| Multi-tenant / multi-team scale-out | "Make it reusable across teams" | Launch is for ONE team; multi-tenant changes auth, isolation, IDOR model — huge review surface | Single-team gating now; revisit only after stable prod usage |
| Horizontal scale-out (Redis rate-limit, distributed cache, BK-tree fuzzy index) | CONCERNS.md scaling limits look alarming | All limits bite at 10K+ users / 100K+ customers — orders of magnitude beyond 20–100 users | Document the limit as accepted-at-current-scale; revisit if usage grows |
| Full admin dashboard / BI / export | "We'd love analytics" | Real app feature; competes with launch priorities | Ship the *minimal* 1-pane health workbook (table stakes); defer rich dashboards |
| Custom backup tooling for Durable state | "We need backups" | Re-implements what Azure Storage soft-delete + PITR + GRS already provides | Use built-in Storage data-protection config — no code |
| Re-architecting for resilience (circuit breakers everywhere, queue rework) | Fragile areas in CONCERNS.md | PROJECT.md forbids refactor; deploy what exists | Targeted fixes only: OBO retry, Fabric degradation, owner_hash, log-leak |
| Pen-test / external audit / formal certification | "Be thorough" | Out of proportion for an internal 20–100-user launch; slow and costly | Internal security review + honest known-issues register is the right bar |

---

## Feature Dependencies

```
Availability test + alert
    └──requires──> /health + /ready endpoints (CODE)

FinOps budget alert (firing)
    └──requires──> Notification sink wired (TEAMS_WEBHOOK_URL or Cost Mgmt budget)

Durable-state backup
    └──requires──> GRS/RA-GRS + soft-delete + PITR on the Storage account (INFRA)

Data-retention enforcement
    └──requires──> Retention policy (DOCS)
                       └──requires──> Storage lifecycle rule + jobs TTL cleanup (INFRA/CODE)

RGPD evidence pack
    ├──requires──> Document-access audit trail (CODE)  ← only code-heavy RGPD item
    ├──requires──> PII-in-logs fix: redact client-facing errors + AI traces (CODE)
    └──requires──> Record of processing + DPIA-or-decision (DOCS, DPO-gated)

Security review readiness
    ├──requires──> owner_hash → Object ID fix (CODE, must-fix)
    └──requires──> Secrets-in-error-messages fix (CODE, shared with RGPD logs fix)

Controlled real-prod E2E
    ├──requires──> Deploy runbook executed + MI verified
    ├──requires──> Observability live (so failures are visible during the test)
    └──requires──> Feature-flag gating (so only the test user reaches prod)

Go/No-Go checklist ──gates──> Open to pilot cohort ──gates──> Open to full team
```

### Dependency Notes

- **Two code fixes pay double.** The "secrets in error messages" fix satisfies *both* the security-review secret-handling artifact and the RGPD PII-in-logs statement. The `owner_hash`→Object ID fix is both a security must-fix and an RGPD access-control improvement. Sequence these first; they unblock two evidence streams each.
- **The audit trail is the long pole among code items for RGPD** — it is the one RGPD artifact that cannot be satisfied by documentation alone, and CONCERNS.md already flags it as a compliance gap.
- **The DPIA/record-of-processing is the long pole among docs items** — it depends on a person (DPO) outside the operator, so start it on day one in parallel with everything else.
- **Observability must precede the controlled E2E**, not follow it — the whole point of the E2E is to watch the pipeline through the monitoring you just built.

---

## MVP Definition (Go-Live Readiness)

### Launch With (Go-Live Gate)

- [ ] App Insights mandatory on both halves; failure + availability + budget alerts firing — *can't operate blind*
- [ ] `/health` + `/ready`; Standard availability test + alert — *detect outage before users*
- [ ] Storage account data-protection (GRS + soft-delete + PITR) — *don't lose in-flight audits/results*
- [ ] All secrets in Key Vault; rotation runbook written; expiry dates tracked — *avoid silent expired-secret outage*
- [ ] Five runbooks: deploy, rollback, secret rotation, incident triage, kill-switch — *one person can operate it*
- [ ] Fixes: OBO retry, owner_hash→Object ID, client-facing error/AI-trace redaction — *correctness + security + RGPD*
- [ ] Document-access audit trail to immutable log — *RGPD + incident investigation*
- [ ] RGPD pack: record of processing, DPIA-or-documented-decision, retention policy (+ enforcement), PII-in-logs statement, DSR procedure
- [ ] Security pack: data-flow diagram, authN/Z description, threat-coverage matrix, dependency posture, accepted-risk register
- [ ] Controlled real-prod E2E with known test client/doc — green
- [ ] Feature-flag gating to the one team + Go/No-Go checklist signed

### Add After Validation (post-pilot)

- [ ] Synthetic full-audit availability test — *once the team is on and core is stable*
- [ ] Fabric graceful degradation / circuit breaker — *after observing real Fabric reliability*
- [ ] SLO + error-budget — *once you have baseline prod metrics*
- [ ] Secret-expiry calendar automation — *after first manual rotation proves the runbook*

### Future Consideration (later milestone)

- [ ] Active/passive multi-region DR — *only if availability becomes contractual*
- [ ] Rich admin dashboard, batch/export/webhooks, new audit types — *explicit PROJECT.md deferrals*
- [ ] Scale-out (Redis, distributed cache) — *only past ~thousands of users*

---

## Prioritization Matrix

| Item | Operator/Launch Value | Cost | Priority |
|------|----------------------|------|----------|
| App Insights + failure/budget/availability alerts | HIGH | LOW | P1 |
| /health + /ready | HIGH | LOW | P1 |
| Storage data-protection (backup) | HIGH | LOW | P1 |
| 5 runbooks | HIGH | MEDIUM | P1 |
| Secrets-in-errors + AI-trace redaction fix | HIGH | LOW | P1 |
| owner_hash → Object ID fix | HIGH | LOW | P1 |
| Document-access audit trail | HIGH | MEDIUM | P1 |
| Record of processing + DPIA/decision + retention policy | HIGH | MEDIUM | P1 |
| Security evidence pack (docs) | HIGH | LOW | P1 |
| Controlled real-prod E2E | HIGH | MEDIUM | P1 |
| Feature-flag gating + Go/No-Go | HIGH | LOW | P1 |
| OBO retry | MEDIUM | LOW | P1 |
| Retention enforcement (lifecycle + TTL) | MEDIUM | LOW | P2 |
| Fabric graceful degradation | MEDIUM | MEDIUM | P2 |
| Synthetic full-audit test | MEDIUM | MEDIUM | P2 |
| SLO/error-budget | MEDIUM | LOW | P2 |
| Multi-region DR / scale-out | LOW (this scale) | HIGH | P3 |

**Key:** P1 = go-live gate · P2 = soon after pilot · P3 = future milestone

---

## Sources

- CNIL — *Carrying out a DPIA if necessary* & *Guidelines on DPIA* (≥2-of-9 criteria → DPIA mandatory; else document the decision; free CNIL PIA tool): https://www.cnil.fr/en/carrying-out-protection-impact-assessment-if-necessary · https://www.cnil.fr/en/guidelines-dpia — **HIGH**
- CNIL — *Practice Guide: Security of Personal Data (2024)* (logs, retention, security measures expected): https://www.cnil.fr/sites/default/files/2024-03/cnil_guide_securite_personnelle_ven_0.pdf — **HIGH**
- Microsoft Learn — *Application Insights availability tests* (Standard test, alert `failedLocationCount`, single-region guidance): https://learn.microsoft.com/en-us/azure/azure-monitor/app/availability — **HIGH**
- Microsoft Learn — *Disaster Recovery and Geo-Distribution in Durable Functions* (all task-hub state in the Storage account; active/passive shared-Storage pattern): https://learn.microsoft.com/en-us/azure/azure-functions/durable-functions/durable-functions-disaster-recovery-geo-distribution — **HIGH**
- Microsoft Learn — *Durable Functions task hubs / storage providers* (state container layout, recoverable vs non-recoverable data): https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-task-hubs — **HIGH**
- Project context: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/TESTING.md`, `.planning/codebase/STACK.md` — **HIGH** (primary source for what already exists vs what is a gap)

---
*Feature research for: production go-live readiness of an internal Azure AI assistant under RGPD*
*Researched: 2026-06-13*
