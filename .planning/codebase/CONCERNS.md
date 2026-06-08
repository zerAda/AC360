# Codebase Concerns

**Analysis Date:** 2026-06-08

> Cross-referenced with `AC360_FINAL_ENTERPRISE_READINESS_REPORT.md` (certification 2026-06-04, score 91/100). That report tracks 12 resolved P0 issues plus a "Risques Résiduels" roadmap. This document records the residual risks plus additional concrete issues found in the current source tree that the readiness report does not call out.

---

## Tech Debt

**Azure Durable Functions backend not present in repo:**
- Issue: `scripts/api_server.py` proxies all audit requests to `AZURE_FUNCTION_URL` (`/audit`, Durable Functions status webhook), but there is no `azure_functions/` implementation in the working tree (only a top-level untracked `azure_functions/` placeholder dir). The OCR → Fabric → FIC pipeline (`process_document_ocr.py`, `audit_fabric_comparison.py`, `generate_fic_draft.py`, `post_audit_workflow.py`) exists only as standalone CLI scripts, not wired into any orchestrator.
- Files: `scripts/api_server.py:108-141`, `scripts/api_server.py:227-266`
- Impact: The end-to-end audit flow is not executable as deployed. `/api/audit` returns `502` unless an external Azure Function is running. Pipeline scripts are invoked manually via argparse, not by the API.
- Fix approach: Implement and commit the Durable Functions app (or a Celery/worker equivalent), or document clearly that the backend is external. Readiness report flags this as "Fabric/OCR non connecté — Phase 2".

**Dual / inconsistent fuzzy-match thresholds:**
- Issue: `match_client_name` enforces a strict `>= 85` score, but downstream code still references the old `75` threshold in messages and alert logic. The reject-word penalty in `perform_audit` writes `"commentaire": "Fuzzy matching < 75%"` and `post_audit_workflow.send_teams_alert` / `main` test `score_correspondance_nom < 75`.
- Files: `scripts/audit_fabric_comparison.py:117-123`, `scripts/audit_fabric_comparison.py:186`, `scripts/post_audit_workflow.py:30`, `scripts/post_audit_workflow.py:130`
- Impact: A client matched at score 78 is treated as "found" by the audit (`>= 75` not used) yet `match_client_name` already rejected it (returns `None`). Conversely, scores in the 75–84 band silently differ between the matcher and the alert layer, creating confusing/incorrect audit verdicts.
- Fix approach: Centralise the threshold in `config.py` as a single constant; align matcher, audit comments, and Teams-alert logic.

**Hardcoded environment / bot identifiers in PowerShell:**
- Issue: `sync_copilot.ps1` hardcodes the Dataverse environment URL and Copilot bot GUID.
- Files: `scripts/sync_copilot.ps1:17-18` (`$EnvironmentId`, `$BotId`)
- Impact: Script cannot target staging vs prod without editing source; tenant migration requires code changes.
- Fix approach: Promote to script parameters or environment variables.

**Pandas `read_sql` over raw pyodbc connection:**
- Issue: `fetch_artus_data` uses `pd.read_sql(query, conn, ...)` with a bare pyodbc connection, which pandas warns against (recommends SQLAlchemy engine).
- Files: `scripts/audit_fabric_comparison.py:62-73`
- Impact: Deprecation warnings; fragile across pandas versions. Parameterisation is correct (anti-injection), but the access pattern is brittle.
- Fix approach: Wrap the connection in a SQLAlchemy engine or use a pyodbc cursor directly.

---

## Known Bugs

**Malformed timestamp format string in archival:**
- Symptoms: Archive filenames carry a corrupted timestamp. `datetime.now().strftime("%Y%md_%H%M%S")` contains `%md` — `%m` (month) followed by a literal `d`, not `%m%d`. The day is never emitted; an `d` literal is injected instead.
- Files: `scripts/post_audit_workflow.py:89`
- Trigger: Any audit producing an écart (archival path).
- Workaround: None; cosmetic but corrupts the audit trail naming. Fix to `"%Y%m%d_%H%M%S"`.

**`perform_audit` reads `keyValuePairs` but `match_client_name`/OCR produces `key_value_pairs`:**
- Symptoms: The OCR output (`process_document_ocr.py`) emits a `fields` dict and `tables`; it never emits a top-level `keyValuePairs`. `perform_audit`'s fallback loop iterates `ocr_data.get("keyValuePairs", [])`, which is always empty for real OCR output, so the key-value fallback for the hospitalisation ceiling never fires on production data (only in the hand-built test fixture).
- Files: `scripts/audit_fabric_comparison.py:160-165`, `scripts/process_document_ocr.py:50-60`
- Trigger: Real Azure OCR document where the ceiling is in a key/value pair rather than a table.
- Workaround: Align key naming (`fields` vs `keyValuePairs`) between OCR extractor and audit consumer.

**Fragile "next-cell" ceiling extraction:**
- Symptoms: Ceiling value is inferred by taking the cell immediately following any cell containing "hospitalisation"/"chambre" in a flat `cells` list, ignoring row/column geometry.
- Files: `scripts/audit_fabric_comparison.py:145-157`
- Trigger: Any table where the value is not the literal next cell in iteration order (multi-column tables, header rows, merged cells).
- Workaround: Use `row_index`/`column_index` to locate the value cell relative to the label cell.

---

## Security Considerations

**`/api/download/{job_id}/{filename}` lacks ownership / job-isolation check:**
- Risk: The endpoint validates `filename` against path traversal but performs no check that `job_id` belongs to the authenticated `user_upn`. Any authenticated user who knows or guesses a `job_id` (UUID) can download another user's generated FIC/RDV document (IDOR).
- Files: `scripts/api_server.py:188-213`
- Current mitigation: Filename traversal block (`..`, `/`, `\`); UUID job IDs are hard to guess.
- Recommendations: Bind jobs to UPN at creation and verify ownership on download. (Worktree branches contain `test_idor_job_access.py` / `test_job_ownership.py` — this concern is being actively worked but is not enforced in the main-branch `api_server.py`.)

**Durable Functions status endpoint relies on shared system key, not user identity:**
- Risk: `get_job_status` appends `&code={AZURE_FUNCTION_KEY}` (a shared function key) and queries the Durable Functions instance directly with hardcoded `taskHub=TestHubName&connection=Storage`. There is no per-user authorization on the status result, and the inline comment admits the auth model is unresolved ("Dans un setup complet... ou on utilise la clé système").
- Files: `scripts/api_server.py:245-260`
- Current mitigation: Caller must hold a valid Entra ID token to reach the endpoint.
- Recommendations: Enforce job ownership; remove the hardcoded `TestHubName` task hub before production.

**Teams webhook delivery over plain `requests` without retry/validation:**
- Risk: `send_teams_alert` posts client names and audit écarts to a webhook URL from env. Alert payload includes client identity and document values in clear text to an external endpoint.
- Files: `scripts/post_audit_workflow.py:12-55`
- Current mitigation: `safe_logger.redact` masks secrets/PII in logs (not in the outbound Teams payload). Webhook URL is env-sourced.
- Recommendations: Confirm the Teams channel is governed/DLP-scoped; consider minimising PII in alert facts.

**JWKS cache has no TTL / signed-key rotation handling:**
- Risk: `_JWKS_CACHE` is a process-global dict cached indefinitely; it is only invalidated (once) on a kid miss. There is no time-based expiry.
- Files: `scripts/auth.py:13-45`
- Current mitigation: On unknown `kid`, the cache is cleared and refetched once.
- Recommendations: Add TTL-based refresh; consider `PyJWKClient` (which the readiness report claims is used, but the actual code uses a hand-rolled `_fetch_jwks`/`RSAAlgorithm.from_jwk` cache — a discrepancy worth reconciling).

**Documentation instructs storing secrets in plaintext `.env` on the prod host:**
- Risk: `docs/observability/APPINSIGHTS_SETUP.md` tells operators to add `APPINSIGHTS_INSTRUMENTATIONKEY` to the production `.env`. Multiple scripts call `load_dotenv()` and read OCR/Fabric/webhook secrets from env.
- Files: `docs/observability/APPINSIGHTS_SETUP.md:33-39`, `scripts/process_document_ocr.py:16-19`, `scripts/audit_fabric_comparison.py:18-21`
- Current mitigation: `.env` is gitignored; readiness checklist says use Azure Key Vault.
- Recommendations: Make Key Vault the documented default; reframe `.env` as local-dev only.

---

## Performance Bottlenecks

**In-memory rate-limit and JWKS state will not survive multi-instance scaling:**
- Problem: `_rate_limit_store` (per-UPN sliding window) and `_JWKS_CACHE` are process-local dicts.
- Files: `scripts/api_server.py:60-90`, `scripts/auth.py:13`
- Cause: No shared store (Redis) for rate-limit counters; each replica enforces its own quota.
- Improvement path: Back rate limiting with Azure Redis Cache (the readiness report already lists Redis provisioning as a pre-go-live "MOYEN" item).

**`create_planner_task` / `get_user_plans` open a fresh `httpx.AsyncClient` per call:**
- Problem: Unlike `api_server` (which uses a shared pooled client), `planner_integration.py` instantiates `httpx.AsyncClient()` per request.
- Files: `scripts/planner_integration.py:24-26`, `scripts/planner_integration.py:46-48`
- Cause: No connection reuse; risks socket churn under load.
- Improvement path: Reuse the module-level pooled client from `api_server`.

---

## Fragile Areas

**FIC business-rule keyword matching (`evaluate_fic_rules`):**
- Files: `scripts/generate_fic_draft.py:25-40`
- Why fragile: Eligibility hinges on substring keyword matching against a free-text `motif` ("modif", "conseil", "reprise de gestion"...). The audit hardcodes `motif_operation = "modification de garantie"` (`audit_fabric_comparison.py:193`, labelled "Valeur simulée"), so the rule always fires "Requis" regardless of the real document. Default branch generates a FIC "if in doubt".
- Safe modification: Drive `motif` from real extracted data; replace substring matching with an explicit enum/lookup; add unit tests per rule branch.
- Test coverage: Rule-branch coverage not evident in `tests/`.

**OCR client-name extraction depends on a literal `nom_client` field:**
- Files: `scripts/audit_fabric_comparison.py:131-136`
- Why fragile: `perform_audit` only finds the client name if `ocr_data["fields"]["nom_client"]` exists, but Azure Document Intelligence emits arbitrary key text (`kv_pair.key.content`), not a normalised `nom_client` key. Real OCR output will rarely contain that exact key, so the client name silently defaults to `""`.
- Safe modification: Add a normalisation/aliasing layer mapping OCR key variants to canonical fields; reject empty client names instead of proceeding.
- Test coverage: Only the hand-crafted fixture in `tests/backend/test_ocr_fabric.py` uses the exact `nom_client` key — masks the gap.

**File-write side effects in pipeline scripts assume current-working-directory:**
- Files: `scripts/audit_fabric_comparison.py:198-231`, `scripts/generate_fic_draft.py:128-168`, `scripts/post_audit_workflow.py:87`
- Why fragile: Default output paths (`audit_report.json`, `Archives_Documentaires/Erreurs_Audit`, `--output-dir "."`) are relative to CWD; archival creates folders under CWD rather than a controlled jobs dir.
- Safe modification: Anchor all outputs to `config.JOBS_BASE_DIR`.

---

## Scaling Limits

**Single-process FastAPI state ceiling:**
- Current capacity: One uvicorn process; rate-limit dict cleanup triggers at `>1000` keys.
- Limit: Horizontal scaling breaks per-user quota correctness and duplicates JWKS fetches.
- Scaling path: Externalise counters/cache to Redis; run stateless replicas behind a load balancer.

---

## Dependencies at Risk

**Optional heavy SDKs imported with `sys.exit(1)` on ImportError:**
- Risk: `process_document_ocr.py` and `audit_fabric_comparison.py` hard-exit the process if Azure SDK / pyodbc / azure-identity are missing, rather than degrading.
- Impact: A partial environment cannot import these modules for unit testing without the full Azure stack; couples test collection to optional native deps (pyodbc + ODBC Driver 17).
- Migration plan: Guard imports lazily inside functions, or split SDK-dependent code from importable logic.

**`requests` (sync) used in `post_audit_workflow` vs `httpx` (async) elsewhere:**
- Risk: Two HTTP stacks in one codebase; inconsistent timeout/retry behaviour. `send_teams_alert` sets no timeout on the `requests.post`.
- Files: `scripts/post_audit_workflow.py:51`
- Impact: A hung Teams webhook blocks the post-audit step indefinitely.
- Migration plan: Standardise on `httpx`; always pass a timeout.

---

## Missing Critical Features

**End-to-end orchestration / job persistence:**
- Problem: No committed worker, queue, or durable orchestrator ties OCR → Fabric → FIC → Teams together. `/api/audit` depends on an external Azure Function that is absent from the repo.
- Blocks: Real audits cannot run from the API as shipped; status polling targets a placeholder task hub.

**Observability not wired:**
- Problem: Application Insights is documented but only emitted as a `log_security` line when an env key is present; no SDK/exporter integration.
- Files: `scripts/api_server.py:38-55`, `docs/observability/APPINSIGHTS_SETUP.md`
- Blocks: No distributed tracing/metrics in production (readiness report: "Application Insights non branché — J+30").

---

## Test Coverage Gaps

**Pipeline integration (OCR → audit → FIC → post-audit) untested end-to-end:**
- What's not tested: The full chain; only isolated unit tests with mocked Azure clients and hand-built fixtures exist.
- Files: `tests/backend/test_ocr_fabric.py`
- Risk: Field-name mismatches (`fields` vs `keyValuePairs`/`nom_client`), threshold inconsistencies (85 vs 75), and the timestamp bug all pass the current suite because fixtures sidestep them.
- Priority: High

**`api_server.py` Durable-Function proxy paths not covered in main-branch tests:**
- What's not tested: `/api/audit`, `/api/audit/{job_id}/status` happy/error paths against the external function; download IDOR.
- Files: `scripts/api_server.py:108-266` (IDOR/ownership tests exist only on worktree branches, not the main tree)
- Risk: Auth-bypass / cross-user download regressions land unnoticed.
- Priority: High

**FIC rule engine branch coverage absent:**
- What's not tested: `evaluate_fic_rules` exclusion vs creation vs default branches.
- Files: `scripts/generate_fic_draft.py:25-40`
- Risk: Incorrect FIC generation (regulatory devoir-de-conseil document) without detection.
- Priority: Medium

**Stale duplicated source under `.claude/worktrees/`:**
- What's not tested / concern: Multiple full copies of `scripts/` and `tests/` exist under `.claude/worktrees/*` with diverging implementations (e.g. `job_store.py`, `safe_paths.py`, `api_http_auth` tests) not present in the main tree.
- Files: `.claude/worktrees/priceless-hopper-c25b4c/scripts/*`, `.claude/worktrees/optimistic-lamarr-f833b7/*`, `.claude/worktrees/inspiring-lehmann-25f749/*`
- Risk: Confusion over the source of truth; security fixes (IDOR, job isolation, path safety) live in worktrees but may not be merged to `main`. Ensure these are not packaged/deployed and reconcile divergence.
- Priority: Medium

---

*Concerns audit: 2026-06-08*
