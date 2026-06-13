# Pitfalls Research

**Domain:** First production deployment of a brownfield, security-hardened Azure app (FastAPI gateway + Azure Durable Functions + Copilot Studio agent in Teams), French insurance / client-PII (RGPD), solo-operated, 20–100 internal users.
**Researched:** 2026-06-13
**Confidence:** HIGH on the technical platform pitfalls (verified against Microsoft Learn + codebase docs); MEDIUM on Copilot Studio promotion specifics (platform changes fast); HIGH on the AC360-code-specific findings (drawn from `.planning/codebase/CONCERNS.md` + `ARCHITECTURE.md`).

> Scope note: This is a **deploy-what-exists** milestone, not a refactor. Several pitfalls below are already *documented as known* in `CONCERNS.md`/`ARCHITECTURE.md` ("addressed", "partial", "scaling path"). The danger in THIS milestone is that those mitigations were written/tested against a **single-process local model** and silently break the moment the app runs on **scaled-out Azure compute**. The in-memory-state pitfalls are the single highest-risk theme of this launch.

---

## Critical Pitfalls

### Pitfall 1: In-memory state breaks the moment Azure scales out past 1 instance (IDOR + rate limit + JWKS)

**What goes wrong:**
AC360 keeps three pieces of security-relevant state in per-process Python dicts:
- `_rate_limit_store` (rate limiting, `scripts/api_server.py:105-152`)
- the audit-job **ownership map** used as the IDOR fast-path (`api_server.py:216-242`, 5000-entry cache)
- `_JWKS_CACHE` (`scripts/auth.py:27-44`)

The instant the FastAPI gateway runs on more than one instance (App Service scale-out, multiple Functions workers, or even multiple Uvicorn/Gunicorn workers in one container), each process has its **own** copy. Rate limits become "N× the configured limit" because requests round-robin across instances. The IDOR ownership map can **miss** on the instance that didn't handle the original audit — and `ARCHITECTURE.md:300-302` says the durable `owner_hash` is the real backstop, so this *should* degrade to a correctness-preserving slow path, **but only if the durable check is actually reached on every status call and never silently skipped**. If any code path trusts the in-memory map as authoritative, a user can land on a "cold" instance and either be denied their own job or (worst case) the ownership check passes incorrectly.

**Why it happens:**
The mitigations in `ARCHITECTURE.md` ("Unbounded Memory Growth — Addressed", "IDOR — Addressed") were designed and tested in a single-process model. `ARCHITECTURE.md:254` literally notes "in-memory, per-process; not shared across workers in production" — the gap is *known on paper* but the production topology hasn't been pinned to make it safe. Microsoft's own guidance confirms in-memory counters do not survive multi-instance deployments and an external store (Redis) is required for consistent enforcement.

**How to avoid:**
- **Decision first:** explicitly choose the production topology. For 20–100 users the cleanest safe answer is **pin the gateway to a single instance** (App Service: scale-out max = 1, or `WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT`-equivalent, one Uvicorn worker) and document that the in-memory design is *load-bearing* on single-instance.
- If single-instance is unacceptable, move rate-limit + ownership to a shared store (Azure Cache for Redis or a Durable Entity) **before** go-live. Redis is the standard fix.
- Make the **durable `owner_hash` check authoritative**, not the in-memory map — verify in the audit that `/api/status` *cannot* return results without the durable ownership comparison succeeding (the in-memory map should be a cache, never the gate).
- Add the missing **concurrent** rate-limit test (`CONCERNS.md:209-213` flags it untested) and an explicit multi-instance IDOR test (request job on instance A, poll on instance B).

**Warning signs:**
- App Service / Functions plan allows auto-scale and nothing pins instance count to 1.
- Rate-limit alerts never fire even under bursty usage (limit silently multiplied).
- Intermittent "job not found" / 403 on status polls that disappear on retry (you hit a different instance).

**Phase to address:** Deep code audit (confirm durable owner_hash is authoritative) + Deployment/infra phase (pin instance count or add Redis). This must be settled **before** the controlled E2E test.

---

### Pitfall 2: JOBS_BASE_DIR points at ephemeral, per-instance Functions storage — downloaded client docs/OCR/FIC drafts vanish or aren't found

**What goes wrong:**
The Durable orchestration downloads the client document, OCR output, and generated FIC drafts to `JOBS_BASE_DIR / {document_id}/` (`ARCHITECTURE.md:127,186`). On Azure Functions, the local temp filesystem (`%TEMP%` / `C:\local\Temp`) is **per-instance, not shared, and wiped on restart or after ~12h**. Two failure modes: (a) the **download activity** runs on instance A but the **OCR/compare/FIC activity** runs on instance B → file not found, orchestration fails mid-pipeline; (b) a FIC draft written for later retrieval disappears on instance recycle before the user fetches it. This is exactly the "ephemeral — but where does it live in prod?" question from the brief, and the answer is: **nowhere durable, unless you make it so.**

**Why it happens:**
`ARCHITECTURE.md:186` already labels JOBS_BASE_DIR "(ephemeral)" but the implication for a *multi-activity Durable* pipeline wasn't closed: Durable activities are independently scheduled and **can run on different workers**. Local temp works perfectly on a dev box (one machine, files persist) and fails non-deterministically in prod.

**How to avoid:**
- Keep the **entire** download→OCR→compare→FIC chain inside a **single activity** so all file I/O stays on one worker (simplest, fits "deploy what exists"). If the pipeline already does this, verify it explicitly in the audit.
- OR back JOBS_BASE_DIR with **Azure Files** (mounted share, shared across instances) — Microsoft's recommended approach for cross-instance scale-out file needs.
- OR pass artifacts between activities via **Blob Storage** (write blob, pass URL), not local paths.
- Set JOBS_BASE_DIR to a writable, known location in prod and **fail-fast on startup** if it's unwritable.
- Define a **retention/cleanup job** for whatever store you choose (also an RGPD requirement — see Pitfall 9).

**Warning signs:**
- Pipeline fails intermittently at the OCR or FIC step with "file not found", only under load / after scale events.
- FIC download works immediately after audit but 404s minutes later.
- No Azure Files mount and no blob hand-off in the Function config.

**Phase to address:** Deep code audit (confirm single-activity vs multi-activity file handoff) + Deployment phase (provision Azure Files / blob if needed). Verify in controlled E2E by forcing a restart between download and FIC retrieval.

---

### Pitfall 3: OBO / delegated Graph fails in prod on missing admin consent or token-audience mismatch (AADSTS65001)

**What goes wrong:**
The On-Behalf-Of flow exchanges the user's token for a Graph token to read SharePoint as the user (`api_server.py:320-333`). In prod this fails hard if: the middle-tier app registration **hasn't been granted admin consent** for its delegated Graph scopes (`Sites.Read.All` / `Files.Read.All`) in the **production tenant**; the **audience (`aud`) of the incoming token doesn't match** the API's expected audience/App ID URI; or the Copilot Studio action's token was issued for a different resource than the gateway validates. OBO is **non-interactive**, so when consent is missing it returns `AADSTS65001` with no user prompt — the user just gets an error. `CONCERNS.md:51-55` already flags OBO error propagation returns a misleading 502.

**Why it happens:**
Dev/test tenants often have user-consent enabled or consent already clicked, masking the requirement. The prod tenant is typically locked down (admin-consent-required), and the app-registration consent is a **separate manual step** that's easy to forget. Audience mismatches creep in when the App ID URI, the `aud` config (`AppConfig`, `ARCHITECTURE.md:342`), and the Copilot Studio action's configured resource drift apart across environments.

**How to avoid:**
- Pre-flight checklist: in the **production** app registration, grant **admin consent** for all delegated Graph scopes before any user hits it. Treat missing consent as a **blocking deploy failure**, not a runtime surprise.
- Pin and cross-check three values to one source of truth: API `aud`/App ID URI, the token-validation `aud` in `AppConfig`, and the Copilot Studio action resource.
- Fix the error mapping so transient OBO failure → 503 and consent/audience failure → a clear 401/403 with a safe message (closes `CONCERNS.md:51-55`).
- Validate **least-privilege scoping**: confirm Graph delegated scopes are read-only (`Sites.Read.All`, not `.ReadWrite`) — read-only is a core AC360 guardrail.

**Warning signs:**
- First real user login returns Graph 401/403 while the local box "works."
- Logs show `AADSTS65001` / `AADSTS650057` / `invalid_audience`.
- The prod app registration's API permissions show "Not granted for <tenant>".

**Phase to address:** Deployment phase (app-registration + consent) and Deep audit (error mapping + audience single-sourcing). First thing exercised in the controlled E2E (real user token → real SharePoint).

---

### Pitfall 4: Copilot Studio promotion drift — connection references, SSO, and moderation/guardrails don't carry to the published Teams agent

**What goes wrong:**
Publishing the agent to Teams in the production environment commonly breaks on three things: (1) **connection references** (the SharePoint connector, the custom action calling the FastAPI gateway) are environment-scoped and come over **unbound** — they must be re-authenticated/re-pointed in the target environment or every action 401s/500s; (2) **Teams SSO** is **not** automatically active — per Microsoft Learn, you must reconfigure the agent to "Authenticate with Microsoft" and **republish**, and "failing to configure the Teams SSO settings as instructed causes users to always fail authentication"; changes can take **hours** to take effect; (3) the **moderation/guardrail posture** (the recently hardened uniform High moderation on RAG nodes, validator gate, `useModelKnowledge:false`) lives in the agent/topic YAML and only protects users **if the published version is the hardened one** — a stale or wrong-environment publish silently ships weaker guardrails.

**Why it happens:**
Copilot Studio environments (dev/test/prod) are separate; solution export/import and "publish" are different operations, and connection references + auth are intentionally **not** carried as secrets. SSO has a known republish-and-wait gotcha. The hardening work was committed to the repo YAML but "published" is a separate manual act that can lag the repo.

**How to avoid:**
- Build a **publish checklist** for the prod environment: re-bind every connection reference, grant connector consent, set the action's endpoint to the prod gateway URL, configure Teams SSO (Authenticate with Microsoft) and **republish**, then wait and re-test.
- After publish, **diff the live agent against the repo** to prove the hardened topics (High moderation, validator gate, `useModelKnowledge:false`) are what's actually live — `scripts/validate_copilot_yaml.py` + the `tests/copilot/` guardrail tests should gate this.
- Verify SSO end-to-end in a Teams **1:1 chat** (group/meeting chats don't support SSO + manual auth).
- Confirm the action's audience/scope matches the gateway (ties to Pitfall 3).

**Warning signs:**
- Actions return 401/500 right after publish ("connection not configured").
- Users are prompted to sign in repeatedly or always fail auth in Teams.
- A red-team/jailbreak prompt that the repo tests catch actually succeeds against the live agent (stale publish).

**Phase to address:** Copilot publish phase. Verified in controlled E2E (real Teams user, real conversation, attempt a known-blocked prompt).

---

### Pitfall 5: Durable Functions on the wrong hosting plan — long audits killed by the Consumption 5-min cap / cold starts; Task Hub & storage misconfig

**What goes wrong:**
A document audit is download → OCR (Azure Document Intelligence, up to ~120s, `CONCERNS.md:117-121`) → Fabric lookup → compare → FIC. On the **Consumption plan** the per-function-execution timeout defaults to **5 minutes (max 10)** and the host can **scale to zero**, so a cold start adds latency and an OCR-heavy activity can be **recycled mid-execution**. Separately: the **Durable Task Hub** is backed by an Azure Storage account (queues/tables/blobs). Misconfig causes silent, ugly failures: two function apps sharing one Task Hub name **steal each other's messages**; the storage account in a **different region** from the Functions adds latency and is an RGPD data-residency problem; using a non-recommended storage type breaks Durable. Microsoft also notes Consumption-plan **connection limits** cause sporadic activity failures under load and no 64-bit (less memory).

**Why it happens:**
Consumption is the cheapest default and "just works" in a demo, so the plan choice is made implicitly. Durable's storage/Task-Hub coupling is invisible until two environments collide or a region is chosen by accident.

**How to avoid:**
- Choose **Functions Premium (Elastic Premium / EP1)** or a dedicated/App Service plan for the Functions app so long orchestrations aren't capped at 5 min and cold-start/always-ready is controllable. (Note: orchestrator code itself is short; it's the **activities** that need the headroom — but the safe default for this pipeline is Premium.)
- Set per-environment **unique Task Hub names**; never share a Task Hub across dev/prod.
- Place the **Durable storage account, Functions, OCR, and Fabric all in the same EU region** (e.g. France Central / West Europe) — performance *and* RGPD residency.
- Keep OCR within a bounded activity with a real deadline + retry (`CONCERNS.md:117-121` says the timeout test uses instant mocks — add a real one).
- The Bicep IaC (already in repo) should encode plan, region, Task Hub name, and storage — verify it does.

**Warning signs:**
- Orchestrations "Failed" with vague errors only on large PDFs; fine on small ones.
- Intermittent connectivity errors calling activities under light concurrency (Consumption connection limits).
- Two environments' jobs interfering; storage account region ≠ Functions region.

**Phase to address:** Deployment/infra phase (Bicep: plan, region, Task Hub, storage). Verified in controlled E2E with a **realistically large** test document, not a tiny one.

---

### Pitfall 6: PII leaks into Application Insights / logs despite `safe_logger` — and there's no document-access audit trail

**What goes wrong:**
Two RGPD-critical gaps: (1) `safe_logger.redact()` (`ARCHITECTURE.md:268-272`) masks **known patterns** (KEY=, TOKEN=, emails, IBAN), but client PII in **arbitrary shapes** — a client's company name, SIRET, policy numbers, OCR'd field values, exception messages from Fabric/OCR — can still reach App Insights. `CONCERNS.md:65-69` explicitly warns secrets/PII may leak via the JSON `error` field even though logs are redacted. App Insights custom telemetry "can contain any data you choose," and once PII is there it's subject to RGPD (and Microsoft's Purge API is the only deletion path). (2) `CONCERNS.md:181-184`: **no audit trail of which user accessed which document** — required for an RGPD accountability/incident record.

**Why it happens:**
Redaction is allowlist-by-pattern; PII that doesn't match a pattern (most client business data) sails through. Default App Insights sampling/retention may also be longer than RGPD-justifiable for PII. The access-trail gap is a missing feature, not a bug.

**How to avoid:**
- Audit **every** path that emits to App Insights / returns an `error` field: ensure client field values and OCR output are **never** logged at info level; pass all error strings through `redact()` before they hit a response or telemetry (closes `CONCERNS.md:65-69`).
- Add **App Insights data-collection transformations / telemetry processors** to drop or hash PII server-side, and set a **short, justified retention** for the workspace; ensure the Log Analytics workspace is in the **EU region**.
- Add the **document-access audit log** (user-id-hash, doc id, timestamp, verdict) to an immutable store — satisfies RGPD accountability and incident investigation (`CONCERNS.md:181-184`).
- Confirm OCR'd documents sent to Azure Document Intelligence are covered by the same residency/retention story.

**Warning signs:**
- Searching App Insights for a known test client's name returns hits.
- Exception traces in telemetry contain Fabric rows or OCR field values.
- No query can answer "who accessed document X and when."

**Phase to address:** Deep code audit (log/error paths) + Compliance phase (retention, residency, access trail, DPIA evidence). Explicitly probed during controlled E2E by grepping telemetry for the known test client's PII.

---

### Pitfall 7: The "controlled real-prod E2E" leaks real client data or skips the real failure paths

**What goes wrong:**
The controlled E2E is meant to prove the system against real services before opening to the team — but it can **backfire**: (a) using a **real client's** document means real PII flows through OCR, Fabric, logs, and a generated FIC draft **before** RGPD controls are proven — turning the smoke test into an unlogged data-processing event; (b) the test "passes" by exercising only the **happy path** (small clean PDF, client that exists, CONFORME verdict) and never hits the paths most likely to break in prod: large/garbled scans (OCR timeout), `CLIENT_NON_TROUVE`, Fabric unavailable (`CONCERNS.md:123-127` — no fallback, full pipeline failure), scale-out IDOR (Pitfall 1), and ephemeral-file handoff (Pitfall 2).

**Why it happens:**
"Controlled" gets interpreted as "one careful run," and the most reassuring run is the happy path. Real client data feels "more realistic" so it's reached for first.

**How to avoid:**
- Use a **synthetic but realistic** test client/document seeded into ARTUS/Fabric specifically for E2E — gets real-service coverage **without** real-person PII. If a real client must be used, get it into the RGPD record-of-processing and DPIA first.
- Script the E2E to deliberately cover **failure paths**: oversized/low-quality scan (force OCR timeout/retry), non-existent client (`CLIENT_NON_TROUVE`), Fabric-down simulation, ECART verdict that triggers FIC generation, and a cross-instance status poll (IDOR backstop).
- Restart the Functions app **between** download and FIC retrieval to prove file durability (Pitfall 2).
- After the run, **grep App Insights** for the test client's identifiers to prove no PII leaked (Pitfall 6).
- Capture the run as **threat-coverage / launch evidence** for the internal security review.

**Warning signs:**
- The E2E plan has one scenario and it's the happy path.
- The chosen test document is a real client's file.
- No assertion in the E2E checks logs/telemetry for PII.

**Phase to address:** Controlled E2E phase, with prerequisites from Compliance phase (synthetic data + DPIA) done first.

---

### Pitfall 8: Deep code audit confirms hardening exists but misses that mitigations are single-process-only / mock-tested

**What goes wrong:**
The audit's stated goal is to "prove the committed hardening is actually complete." The trap is a **paper-passing audit**: it confirms the code for IDOR, rate limiting, path traversal, OCR timeout, and redaction *exists* and tests *pass* — but the tests are **mock-based and single-process** (`TESTING.md`, `CONCERNS.md`): OCR-timeout test uses instant mocks (`CONCERNS.md:121`); rate-limit test is sequential only (`CONCERNS.md:211`); Fabric tests mock OneLake with no network-failure case (`CONCERNS.md:127`); path-traversal test has no symlink case (`CONCERNS.md:217-219`); JWKS rotation edge cases untested (`CONCERNS.md:227-231`). So the audit "passes" against a model that doesn't match production (multi-instance, real timeouts, real network failures).

**Why it happens:**
Green tests are persuasive. Auditing for *presence of mitigation* is easier than auditing for *mitigation validity under the production topology*.

**How to avoid:**
- Audit against a **production-topology threat model**, not the test harness: for each "Addressed" item in `ARCHITECTURE.md`, ask "does this still hold with N>1 instances, real latency, and a restart mid-pipeline?"
- Close the specific test gaps that matter for launch: concurrent rate-limit, cross-instance IDOR, real OCR timeout, Fabric-unavailable behavior, symlink path-traversal (or prove symlinks impossible in the prod FS).
- Also resolve the open **known bugs** from `CONCERNS.md` that are launch-relevant: IDOR via `owner_hash` reuse after user re-provisioning (hash **Object ID**, not UPN — `CONCERNS.md:39-43`); JWKS cache thread-safety / stale-while-revalidate under concurrency (`CONCERNS.md:7-11,59-63`); broad `except Exception` blocks hiding new bugs (`CONCERNS.md:19-23`).
- Output the audit as a written posture document (feeds the internal security review).

**Warning signs:**
- Audit sign-off cites "all tests pass" as the evidence.
- No test exercises >1 instance or a real (non-mocked) external timeout/failure.
- `owner_hash` still derived from UPN.

**Phase to address:** Deep code audit phase (first phase of the milestone).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep in-memory rate-limit / ownership / JWKS maps | No Redis to provision; ships as-is | Silently wrong on scale-out; security guarantees void | **Only** if gateway is pinned to single instance AND that's documented/enforced in IaC |
| JOBS_BASE_DIR on local Functions temp | Zero storage setup | Cross-instance file loss; FIC drafts vanish; no RGPD retention control | Only if whole pipeline is one activity AND retention is handled |
| `safe_logger` allowlist redaction only | Already built | Non-pattern client PII still leaks to App Insights | Never for prod with real PII — needs telemetry-side transform + retention |
| Consumption Functions plan | Cheapest | 5-min cap kills OCR-heavy audits; cold starts; connection limits | Only after confirming every activity finishes well under 5 min at p99 |
| Broad `except Exception` swallowing | Fewer crashes | Hides new prod bugs; complicates triage for solo operator | Final-fallback only, with explicit logged context |
| No document-access audit trail | Faster ship | RGPD accountability + incident investigation impossible | Never for client-PII processing under RGPD |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Copilot Studio → FastAPI action | Action points at dev URL / connection reference unbound after publish | Re-bind connection + set prod endpoint in target env; diff live agent vs repo |
| Entra OBO → Graph/SharePoint | Forget **admin consent** in prod tenant; audience drift | Grant admin consent pre-deploy; single-source the `aud`/App ID URI; read-only scopes |
| Durable Functions → Azure Storage | Shared/auto Task Hub name; storage in wrong region | Unique Task Hub per env; storage co-located in EU region |
| Functions → Azure Files / Blob for artifacts | Rely on per-instance local temp across activities | Single activity for file chain, or Azure Files / blob hand-off |
| App → App Insights | Send raw telemetry assuming "no PII" | Telemetry processors / collection transforms drop+hash PII; short EU-region retention |
| Managed Identity → Fabric/Graph | MI not provisioned on Functions in prod → cryptic failure | Verify MI on the runtime as a deploy prerequisite (`CONCERNS.md:71-75`) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fabric reference table reloaded per instance/TTL | First audit slow after each cold start; memory per instance | Pre-load at Function init; profile real table size (`CONCERNS.md:91-95`) | Multi-instance × large customer base |
| Fuzzy name match O(n) linear scan | Audit latency grows with customer count | Pre-filter by prefix before fuzzy (`CONCERNS.md:97-101`) | Large ARTUS table (100k+) |
| OCR cold start + 5-min Consumption cap | Large scans fail/recycle | Premium plan; bounded activity + retry | OCR-heavy / large documents |
| httpx pool max_connections=200 vs Graph 429 | Upstream throttling under burst | Honor Retry-After / backoff on 429 (`CONCERNS.md:152-155`) | Concurrent multi-user bursts |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Trusting in-memory IDOR map as authoritative on scale-out | User A sees User B's audit, or denied own | Durable `owner_hash` is the gate; in-memory only a cache |
| `owner_hash` derived from UPN | Re-provisioned user inherits prior user's jobs | Hash **Object ID** + timestamp (`CONCERNS.md:39-43`) |
| Secrets/PII in HTTPException `error` field | Leak to client + telemetry | Run all error detail through `redact()` (`CONCERNS.md:65-69`) |
| Graph token in `X-MS-Graph-Token` header logged | Token exposure in App Insights | Never log raw headers; redact Bearer (`CONCERNS.md:77-81`) |
| Stale publish ships weaker Copilot guardrails | Jailbreak / hallucination reaches users | Diff live agent vs hardened repo before go-live |
| JWKS stale cache accepts rotated-out key | Auth bypass window | Stale-while-revalidate + force-refresh on unknown kid (`CONCERNS.md:59-63`) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| OBO consent/audience error surfaced as raw 502 | User confused, no recourse | Clear "ask admin to grant access" message; 503 only for transient |
| Teams SSO change takes hours, users hit during window | Repeated sign-in prompts / auth failures | Publish SSO change off-hours; verify before opening to team |
| Fabric down → whole audit fails with vague error | User thinks app is broken | Graceful "reference unavailable, try later" verdict (`CONCERNS.md:123-127`) |
| FIC draft 404s minutes after audit | User loses generated report | Durable artifact storage + retention (Pitfall 2) |

## "Looks Done But Isn't" Checklist

- [ ] **Rate limiting:** tests pass — but verify it's enforced with the **production instance count** (single-instance pinned, or Redis-backed).
- [ ] **IDOR protection:** "Addressed" — but verify durable `owner_hash` is the **authoritative gate** across instances, and hash uses Object ID not UPN.
- [ ] **JOBS_BASE_DIR:** writes succeed locally — but verify artifacts survive **cross-activity / cross-instance / restart** in prod, with a retention policy.
- [ ] **OBO / Graph:** works in dev — but verify **admin consent granted in the prod tenant** and audience matches the Copilot action.
- [ ] **Copilot publish:** agent appears in Teams — but verify connection refs re-bound, **SSO reconfigured + republished**, and live guardrails == hardened repo.
- [ ] **PII redaction:** unit tests green — but verify **no client business PII** reaches App Insights (telemetry-side transform + EU retention).
- [ ] **OCR timeout handling:** test exists — but it uses instant mocks; verify a **real** long/oversized document behaves.
- [ ] **Durable plan:** functions run — but verify the **plan/region/Task Hub/storage** in Bicep match EU-residency + non-5-min-cap requirements.
- [ ] **Audit trail:** logging exists — but verify a **document-access record** (who/what/when) exists for RGPD.
- [ ] **DPIA / record of processing:** documented before any **real** client data touches prod.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Scaled out, rate/IDOR state split | LOW | Pin instance count to 1 immediately; plan Redis migration |
| JOBS_BASE_DIR file loss in prod | MEDIUM | Consolidate to single activity or mount Azure Files; re-run affected audits |
| OBO AADSTS65001 at launch | LOW | Admin grants consent in prod app reg; retry (no code change) |
| Copilot stale/weak publish live | LOW | Re-publish hardened version; re-run guardrail tests against live agent |
| PII found in App Insights | MEDIUM-HIGH | Add telemetry transform; **Purge API** to delete existing PII; shorten retention; log as RGPD incident if applicable |
| Audit on Consumption hits 5-min cap | MEDIUM | Switch Functions to Premium plan; redeploy; re-test large doc |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. In-memory state vs scale-out | Deep audit + Deployment | Instance count pinned (or Redis); cross-instance IDOR + concurrent rate-limit tests pass |
| 2. JOBS_BASE_DIR ephemeral | Deep audit + Deployment | Restart-between-steps E2E retrieves FIC successfully |
| 3. OBO / Graph consent+audience | Deployment + Deep audit | Real user token → real SharePoint succeeds; no AADSTS65001 |
| 4. Copilot publish drift | Copilot publish | Live agent diffs clean vs repo; Teams 1:1 SSO works; known-blocked prompt blocked |
| 5. Durable plan/Task Hub/region | Deployment (Bicep) | Large-doc audit completes; storage+functions same EU region; unique Task Hub |
| 6. PII in App Insights + no access trail | Deep audit + Compliance | Telemetry grep for test client PII returns nothing; access log queryable |
| 7. Controlled E2E leaks PII / skips failures | Controlled E2E (after Compliance) | Synthetic data used; failure paths scripted; telemetry PII-clean |
| 8. Audit confirms presence not validity | Deep audit | Each "Addressed" item re-checked under prod topology; launch-relevant known bugs fixed |

## Sources

- [Performance and Scale in Durable Functions — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable-functions/durable-functions-perf-and-scale) (Task Hub, scale-out, batch size)
- [Durable Functions Troubleshooting Guide — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable-functions/durable-functions-troubleshooting-guide) (memory, connection limits, plan)
- [Azure Functions Consumption plan timeout — w3tutorials](https://www.w3tutorials.net/blog/azure-functions-timeout-for-consumption-plan/) (5-min default / 10-min max)
- [Storage considerations for Azure Functions — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/storage-considerations) (per-instance temp; Azure Files for scale-out)
- [Temp directory persistence in Azure Functions — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/938994/temp-directory-files-persistence-in-azure-function) (temp not shared, wiped ~12h/restart)
- [Configure SSO with Microsoft Entra ID for agents in Teams — Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-sso-teams) (reconfigure + republish; failure if misconfigured; 1:1 only)
- [Create and manage connections — Microsoft Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-connections) (connection references per environment)
- [Connect and configure an agent for Teams — Microsoft Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams) (publish flow)
- [On-Behalf-Of / AADSTS65001 admin consent — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/571628/aadsts65001-the-user-or-administrator-has-not-cons) (non-interactive OBO needs prior admin consent)
- [Deploying an Agentic Service with Delegated OBO Access — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/deploying-an-agentic-service-to-microsoft-365-copilot-with-delegated-obo-access/4514197) (treat missing consent as blocking deploy failure)
- [Manage personal data in Azure Monitor Logs — Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/personal-data-mgmt) (Purge API, PII deletion)
- [Architecture best practices for App Insights — Azure Well-Architected](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/application-insights) (custom telemetry can contain any data; your responsibility)
- [FastAPI multi-instance rate limiting — Upstash / community](https://upstash.com/docs/redis/tutorials/python_rate_limiting) (in-memory counters don't survive multi-instance; Redis fix)
- AC360 codebase docs (authoritative, project-specific): `.planning/codebase/CONCERNS.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/TESTING.md`, `.planning/PROJECT.md`

---
*Pitfalls research for: AC360 first-production deployment (Azure Durable Functions + FastAPI + Copilot Studio, RGPD client-PII, solo operator)*
*Researched: 2026-06-13*
