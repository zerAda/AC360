# Codebase Concerns

**Analysis Date:** 2026-06-11

## Tech Debt

**JWKS Cache Thread Safety:**
- Issue: Global mutable state (`_JWKS_CACHE`, `_JWKS_CACHE_TS`) in `scripts/auth.py` accessed by multiple async requests without synchronization lock
- Files: `scripts/auth.py:27-44`
- Impact: Race condition on cache update; potential inconsistent state or temporary auth failures if JWKS refresh happens during concurrent token validations in high-load scenarios
- Fix approach: Add `threading.Lock()` around `_JWKS_CACHE` access or use atomic compare-and-swap pattern; consider `asyncio.Lock()` instead for async context

**Rate Limit Store Not Thread-Safe:**
- Issue: Module-level dict `_rate_limit_store` in `scripts/api_server.py` modified without locks in async context
- Files: `scripts/api_server.py:105-152`
- Impact: Concurrent requests from same user may bypass rate limit checks; cleanup task could corrupt dict during iteration if request arrives simultaneously
- Fix approach: Use `asyncio.Lock()` for all reads/writes to `_rate_limit_store`; consider using `collections.deque` with maxlen for cleaner TTL semantics

**Broad Exception Handling:**
- Issue: Multiple `except Exception as e:` blocks that catch all exceptions including system/internal errors
- Files: `scripts/api_server.py` (8 occurrences), `scripts/audit_fabric_comparison.py`, `scripts/post_audit_workflow.py`
- Impact: Swallows unexpected errors (memory, system signals); makes debugging harder; may hide new bugs
- Fix approach: Replace broad `Exception` catches with specific exception types (httpx.HTTPError, ValueError, etc.); use `except Exception` only as final fallback with explicit logging

**Missing Optional Dependency Graceful Degradation:**
- Issue: `thefuzz` in `scripts/fabric_audit_engine.py:22-25` and `azure-ai-formrecognizer` imports wrapped in try/except but fallback behavior not always specified
- Files: `scripts/fabric_audit_engine.py:22-25`, `azure_functions/function_app.py:26-33`
- Impact: OCR/fuzzy name matching degrades silently; users get lower-quality results without knowing why
- Fix approach: Log warning when optional dependencies unavailable; document fallback behavior explicitly; consider failing fast if critical for feature

## Known Bugs

**Potential Path Traversal in Download Logic:**
- Symptoms: Although `scripts/api_server.py:166-173` validates UUID and uses `commonpath`, if symlinks exist in jobs directory, attacker could potentially escape
- Files: `scripts/api_server.py:155-178`, `azure_functions/shared/sharepoint.py:24-33`
- Trigger: Create symlink in jobs directory → use document ID pointing through symlink
- Workaround: None currently; jobs directory permissions should restrict symlink creation

**IDOR via owner_hash Reuse After User Deletion:**
- Symptoms: If Entra ID user is deleted/re-provisioned, user could be assigned same UPN → regain access to previous user's audit jobs via owner_hash collision
- Files: `scripts/feature_flags.py` (hash_id), `scripts/api_server.py:216-242`
- Trigger: Delete user → user with same display name recreated → old user's UPN hash matches
- Workaround: Use Object ID instead of UPN for hashing; add timestamp to owner_hash

**Rate Limit Cleanup Timing Window:**
- Symptoms: Between rate limit check and append, another request could pass check and both execute, violating max limit temporarily
- Files: `scripts/api_server.py:122-135`
- Trigger: Multiple concurrent requests at limit boundary
- Workaround: Race condition acceptable at scale of small teams; full isolation requires atomic increment

**OBO Token Exchange Error Propagation:**
- Symptoms: If OBO token exchange fails transiently, user gets 502 error instead of 503 (service unavailable)
- Files: `scripts/api_server.py:331-340`
- Trigger: OBO service intermittently unavailable
- Workaround: Implement retry with exponential backoff for OBO exchange

## Security Considerations

**JWKS Cache Missing Stale-While-Revalidate:**
- Risk: If JWKS fetch fails after TTL expires, cache becomes unreliable; old keys could be accepted after rotation
- Files: `scripts/auth.py:36-51`
- Current mitigation: TTL + force refresh on unknown kid
- Recommendations: Implement graceful degradation (accept slightly-expired cache on fetch failure); add metrics for cache misses; consider longer TTL with more aggressive key rotation checks

**Secrets in Error Messages:**
- Risk: Exception messages bubbled from OCR/Fabric may contain connection strings, keys, or PII
- Files: `azure_functions/shared/audit_pipeline.py:65-74`, `scripts/api_server.py:353-382`
- Current mitigation: `safe_logger.redact()` applied to logged messages; but JSON responses may leak in `error` field
- Recommendations: Always run errors through `redact()` before returning to client; audit all HTTPException detail strings

**Managed Identity Assumption Without Fallback:**
- Risk: If Azure Functions can't acquire Managed Identity token (env misconfigured), download fails with cryptic error
- Files: `azure_functions/function_app.py:41-66`, `scripts/fabric_onelake.py:43-46`
- Current mitigation: Fail-fast with clear error message
- Recommendations: Test on Functions runtime to ensure MI is provisioned; document MI setup as critical prerequisite

**Graph API Token Passed in Headers:**
- Risk: X-MS-Graph-Token header could be logged/cached if not carefully filtered
- Files: `scripts/api_server.py:320-333`, `azure_functions/function_app.py:206-220`
- Current mitigation: `safe_logger.redact()` masks Bearer tokens
- Recommendations: Never log raw headers; use custom header names that don't match `Authorization` patterns

**Fabric OneLake Cache Poisoning:**
- Risk: If Fabric data becomes corrupted/poisoned, in-memory cache serves stale data for hours (TTL = 3600s)
- Files: `scripts/fabric_onelake.py:58-120`
- Current mitigation: TTL + thread lock for cache refresh
- Recommendations: Add cache invalidation endpoint (admin-only); log cache load errors; implement simple integrity check (row count, hash)

## Performance Bottlenecks

**Fabric Reference Data Loaded On Every Audit:**
- Problem: `fabric_onelake.py:_build_indexes()` reads entire reference table and builds indexes; runs once per TTL but still blocks audit pipeline
- Files: `scripts/fabric_onelake.py:58-120`, `azure_functions/shared/audit_pipeline.py:120-180`
- Cause: Table not pre-loaded at Function startup; each instance rebuilds cache independently
- Improvement path: Pre-load cache during Function initialization (cold start cost); implement distributed cache (Redis) for multi-instance deployments; profile actual Fabric table size to confirm this is real bottleneck

**Fuzzy Name Matching O(n) Linear Scan:**
- Problem: `fabric_audit_engine.py` uses `thefuzz.fuzz.token_sort_ratio()` in loop over all reference names
- Files: `scripts/fabric_audit_engine.py:143-183`
- Cause: No indexing for prefix/trigram search; full scan necessary but slow for large customer bases
- Improvement path: Implement BK-tree or similar metric indexing for fuzzy matching; pre-filter by first 3 chars before fuzzy comparison; benchmark actual customer table size

**Document Download Redundancy:**
- Problem: Both pre-check (`_assert_user_can_access_document`) and actual download call Graph/SharePoint
- Files: `scripts/api_server.py:248-270`, `azure_functions/function_app.py:69-86`
- Cause: Defense-in-depth by design (eager fail at API boundary), but double I/O cost
- Improvement path: Accept slightly slower fail time; remove pre-check and rely solely on Function-side check; or cache access token for pre-check

**Safe Logger Regex Compilation Not Cached:**
- Problem: `safe_logger.redact()` compiles regexes on every log call
- Files: `scripts/safe_logger.py:62-80`
- Cause: Regexes defined module-level but matched at runtime; Python caches compiled patterns but could be faster
- Improvement path: Pre-compile regex objects at module level (`_JWT_RE = re.compile(...)`); Python caches, but explicit is clearer

## Fragile Areas

**OCR Pipeline Timeout Handling:**
- Files: `azure_functions/function_app.py:127-200`, `azure_functions/shared/audit_pipeline.py:100-180`
- Why fragile: Azure OCR timeout (120s default) configured via env var; exceeding timeout causes orchestration failure with vague error; no retry logic
- Safe modification: Add exponential backoff retry (3 attempts); log actual OCR API response times; make timeout configurable per document type
- Test coverage: `tests/backend/test_ocr_timeout.py` exists but doesn't test actual timeout behavior; uses mocks with instant responses

**Fabric OneLake Dependency:**
- Files: `scripts/fabric_onelake.py`, `azure_functions/shared/audit_pipeline.py`
- Why fragile: Entire audit pipeline fails if Fabric is unavailable, network timeout, or credentials revoked; no fallback audit engine
- Safe modification: Implement "audit without reference" mode (return NULL verdict if Fabric unavailable); add circuit breaker; test with network failure scenarios
- Test coverage: `tests/fabric/` test suite exists but mocks OneLake; no real network failure tests

**YAML Validation Script Import Complexity:**
- Files: `scripts/validate_copilot_yaml.py:220`
- Why fragile: Imports copilot YAML files by traversing `src/copilot/AC360/` and parsing YAML; any malformed file breaks validation
- Safe modification: Add schema validation before import; wrap file reads in try/except with clear error messages
- Test coverage: No automated tests for validation script; relies on manual CI runs

## Scaling Limits

**In-Memory Rate Limit Store:**
- Current capacity: `_rate_limit_store` dict grows unbounded until manual cleanup (max 1000 users before cleanup)
- Limit: 10K+ concurrent users would cause memory bloat; cleanup task is async and may not run
- Scaling path: Move to Redis or memcached; implement sliding window counter; use user ID hash sharding

**JWKS Cache Single Instance:**
- Current capacity: Single dict per instance; 1 copy of ~10 keys (typical Microsoft Entra ID)
- Limit: OK for single instance; multi-instance deployments have redundant caching (not a problem, but not optimal)
- Scaling path: Consider centralized cache (Redis) only if JWKS fetch becomes bottleneck; metrics would confirm

**Fabric OneLake Index Memory:**
- Current capacity: Index holds all customer names + SIRETs in memory (assuming <50K customers, ~5MB)
- Limit: 100K+ customers → ~50MB index per instance; multiple instances = N * index size
- Scaling path: Profile actual table size; consider lazy-loading or pagination; implement distributed cache

**API Server Connection Pool:**
- Current capacity: httpx AsyncClient with `max_connections=200`
- Limit: 200 concurrent outbound Graph/Fabric requests; upstream Rate-Limit-Remaining headers must be monitored
- Scaling path: Monitor Graph API quota usage; implement backoff based on 429 responses; consider dedicated connection pool per service

## Dependencies at Risk

**PyJWT >= 2.8.0:**
- Risk: JWT handling critical for auth; older versions had key algorithm confusion attacks; >= 2.8.0 is recent but not latest
- Impact: Vulnerability in JWT validation could bypass auth entirely
- Migration plan: Pin to 2.9.0+ once available/tested; set up Dependabot alerts; run security audit quarterly

**python-Levenshtein >= 0.25.0:**
- Risk: C extension with historical buffer overflow vulnerabilities; optional for fuzzy matching
- Impact: Low (optional); graceful degradation if not available
- Migration plan: Monitor releases; consider switching to pure-Python distance library (thefuzz has fallback)

**azure-functions-durable >= 1.2.9:**
- Risk: Azure SDK versions change frequently; orchestration logic is tightly coupled to SDK version
- Impact: Potential incompatibility after Azure runtime updates
- Migration plan: Pin to specific version; test thoroughly before updating; document breaking changes

**deltalake >= 0.18.0:**
- Risk: Rust bindings; potential safety issues in native code
- Impact: Fabric OneLake access crashes if corrupted/malicious data returned
- Migration plan: Monitor releases; add input validation on DataFrame columns; set up crash reporting

## Missing Critical Features

**No Audit Trail for Document Access:**
- Problem: API doesn't log which user accessed which document; GDPR/audit trail requirements may be unmet
- Blocks: Compliance audit, incident investigation
- Recommendation: Log document downloads with user ID, timestamp, result to Application Insights; ensure logs are immutable (Azure Log Analytics retention)

**No Bulk Operation Support:**
- Problem: Each audit/search is single-document; no batch endpoints
- Blocks: Power users who need to audit 100+ documents at once
- Recommendation: Add `/api/audit/batch` endpoint with job queue; or document maximum batch size limit

**No Export/Integration with External Systems:**
- Problem: Audit results stuck in AC360; no webhook/API for downstream systems (CRM, ERP, ticketing)
- Blocks: Workflow automation, business intelligence
- Recommendation: Add webhook support for audit completion; or expose audit results via read-only GraphQL API

**No Admin Dashboard:**
- Problem: No visibility into system health, failed audits, user activity without Application Insights
- Blocks: Ops team monitoring, incident response
- Recommendation: Build simple admin dashboard (read-only) showing last 24h audit stats, error rates, rate limit usage

## Test Coverage Gaps

**End-to-End OCR + Fabric Comparison:**
- What's not tested: Full pipeline (download → OCR → Fabric lookup → FIC generation) with real Azure services
- Files: `tests/azure_functions/test_function_app.py:176`, `tests/azure_functions/test_audit_pipeline.py:115`
- Risk: Integration bugs only discovered in production (e.g., OCR output schema change breaks comparison)
- Priority: High — OCR is external dependency; recommend staging environment full-stack test before each release

**Concurrent Rate Limit Violations:**
- What's not tested: Race condition where multiple requests at limit boundary bypass check
- Files: `tests/backend/test_rate_limit.py` — uses sequential requests only
- Risk: Rate limit ineffective under load
- Priority: Medium — requires threading/async test harness; consider property-based testing

**Path Traversal with Symlinks:**
- What's not tested: Jobs directory with symlinks; commonpath() behavior with symlink targets
- Files: `tests/backend/test_document_resolve.py`, no symlink test cases
- Risk: Escape confinement on systems with symlinks enabled
- Priority: High (if symlinks possible in deployment) — add test with actual symlinks

**Fabric Unavailability Fallback:**
- What's not tested: What happens when Fabric service is down; timeout behavior
- Files: `tests/fabric/` — all use mocks; no real network failure scenarios
- Risk: Audit pipeline complete failure instead of graceful degradation
- Priority: Medium — add chaos tests with network timeouts

**JWKS Rotation Edge Cases:**
- What's not tested: Kid not found → force refresh → still not found; concurrent refresh during validation
- Files: `tests/backend/test_auth_jwt_real.py`, `tests/backend/test_jwks_cache_ttl.py`
- Risk: Edge case authentication failure under key rotation
- Priority: Medium — add test with stale JWKS cache + unknown kid

---

*Concerns audit: 2026-06-11*
