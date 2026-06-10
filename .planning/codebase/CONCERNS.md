# Codebase Concerns

**Analysis Date:** 2026-06-10

## Tech Debt

### 1. Deprecated PDF Parsing Methods in Core

**Issue:** Two legacy PDF parsing methods (`parse_content()` and `extract_amounts()`) marked DEPRECATED remain in codebase but still referenced by tests.

**Files:** `src/core.py` (lines 152-194)

**Impact:** 
- Code duplication and maintenance burden
- Test suite depends on legacy interface despite claimed deprecation
- Future refactoring will be blocked if these methods are referenced in older test files

**Fix approach:** 
- Migrate all test references from `PDFParser.parse_content()` to `PDFParser.parse_file()` (which uses pdfplumber)
- Migrate `extract_amounts()` calls to the new amount extraction pattern in `_extract_montant_from_line()`
- Remove DEPRECATED methods once migration is verified in tests
- Add deprecation warning in tests to catch remaining usage

### 2. Bare Exception Handling

**Issue:** Multiple locations use bare `except:` clauses that swallow all exceptions indiscriminately.

**Files:**
- `src/core.py` line 192 (PDFParser)
- `src/core.py` line 247 (ExcelParser)
- `src/main.py` line 418 (batch processing)

**Impact:** 
- Silent failures make debugging difficult
- Errors are logged but execution continues unpredictably
- Cannot distinguish between different failure modes

**Fix approach:** 
- Replace bare `except:` with specific exception types (`ValueError`, `ImportError`, `IOError`, etc.)
- Add conditional logging based on exception type
- Let unrecoverable exceptions propagate up with context

### 3. N+1 Query Pattern in Fuzzy Matching

**Issue:** `OptimizedMatcher.match_with_index()` performs O(n²) comparisons when exact match fails. For each unmatched PDF entry, it iterates through entire Excel dataset with fuzzy matching.

**Files:** `src/core.py` lines 340-369

**Impact:** 
- Performance degrades quadratically with dataset size
- Documented as "O(n)" optimization but not fully optimized
- At 1000+ companies, fuzzy matching becomes bottleneck

**Fix approach:** 
- Implement fuzzy matching index using pre-computed phonetic hashes (e.g., Soundex, Metaphone)
- Cache fuzzy scores for company name pairs to avoid recalculation
- Set a fuzzy matching threshold cutoff to skip obviously bad matches early
- Add performance benchmarking test with 1000+ records

## Known Bugs

### 1. Floating Point Precision in Amount Calculations

**Issue:** Montant (amount) calculations using float arithmetic may accumulate rounding errors when processing many records.

**Files:** `src/core.py` lines 517-524 (EcartCalculator)

**Symptom:** Total ecart sum differs from expected by small amounts (detected but only logged as warning on line 544-545)

**Trigger:** Process 100+ transactions with amounts like 1234.56 EUR

**Workaround:** Use Decimal type for monetary calculations instead of float

**Fix approach:**
- Import Decimal from decimal module
- Convert all montant values to Decimal at parsing time
- Update validation check at lines 544-545 to use Decimal arithmetic
- Increase tolerance threshold to 0.01 EUR only for final summary

### 2. IBAN Validation Regex Too Permissive

**Issue:** IBAN validation at `src/core.py` line 89 checks `^FR\d{2}\s` but allows any characters after the space, including incomplete IBANs.

**Files:** `src/core.py` line 88-90 (PDFParser)

**Symptom:** Invalid or truncated IBANs pass validation if they start with "FR" + 2 digits

**Trigger:** PDF contains malformed IBAN like "FR12 ABC" (incomplete check digit)

**Workaround:** Manual validation of IBAN length must occur at extraction time

**Fix approach:**
- Enforce full IBAN format: `^FR\d{2}[A-Z0-9]{23}$` (27 characters total)
- Add IBAN checksum validation using mod-97 algorithm
- Return validation status in parse result; filter invalid IBANs at Filters stage

### 3. Race Condition in Batch Processing File Deletion

**Issue:** In `src/main.py` lines 577-578, `_safe_delete_file()` is called immediately after audit completion, but file might still be locked by OS if processing is async.

**Files:** `src/main.py` lines 313-326 (deletion method), line 577-578 (call site)

**Symptom:** File deletion fails silently; user is not notified of leftover files

**Trigger:** Run batch mode with Excel files locked by external process; reset immediately afterward

**Workaround:** Manually delete files after 2-3 seconds delay

**Fix approach:**
- Add retry logic with exponential backoff (3 attempts, 100ms→500ms delay)
- Raise exception if final attempt fails (fail-closed)
- Update UI to show deletion status to user
- Queue files for deferred deletion if immediate removal fails

## Security Considerations

### 1. Rate Limiting Store Memory Leak

**Issue:** In-memory rate limit store (`_rate_limit_store` dict in `scripts/api_server.py` line 100) can grow unbounded if cleanup task is never scheduled or if user count grows rapidly.

**Files:** `scripts/api_server.py` lines 100-130

**Risk:** 
- Memory exhaustion attack: attacker creates false user identities to fill the store
- No upper bound on store size; cleanup is async and may lag behind insertions
- Cleanup threshold (1000 keys) is arbitrary and may be insufficient

**Current mitigation:** Cleanup task runs asynchronously when store exceeds 1000 entries, but is not guaranteed to complete before new entries arrive

**Recommendations:**
- Replace in-memory store with Redis or external cache (multi-instance ready)
- Add maximum store size enforcement with LRU eviction
- Set explicit TTL on each entry instead of relying on periodic cleanup
- Add monitoring/alerting on store size and cleanup task latency
- For immediate production: reduce cleanup threshold to 100, increase cleanup frequency

### 2. Document ID Validation Path-Traversal Residual

**Issue:** Path-traversal validation at `scripts/api_server.py` line 137 uses UUID format check, but UUID validation is strict and only works if IDs are truly UUIDs. If backend uses other ID schemes (e.g., numeric job_id), validation may be incomplete.

**Files:** `scripts/api_server.py` lines 137-175 (commented section suggests UUID validation)

**Risk:** 
- If ID scheme changes, validation rules must be updated
- No allowlist for valid directories; only validates format
- Existence check uses filesystem which may have symlink/race condition

**Current mitigation:** Documented in test `tests/backend/test_path_traversal.py`; tested with various payloads

**Recommendations:**
- Whitelist allowed job directory prefixes explicitly
- Validate using `os.path.commonpath()` to prevent symlink escape
- Document ID scheme contract explicitly (must be UUID v4 alphanumeric only)
- Add per-instance ID namespace isolation if multi-tenant later

### 3. JWKS Cache TTL Default Too Long

**Issue:** JWKS_TTL_SECONDS defaults to 3600 (1 hour) when env var missing. Microsoft Entra ID key rotation may occur faster than cache refresh.

**Files:** `scripts/auth.py` line 25

**Risk:** 
- If Entra ID rotates keys frequently (e.g., on security incident), old cached keys remain valid for up to 1 hour
- Force refresh on unknown `kid` exists but only after failed validation (reactive, not proactive)
- No alerting if force refresh is triggered frequently

**Current mitigation:** Force refresh on unknown kid (line 59); TTL configurable via env var

**Recommendations:**
- Reduce default TTL to 300 seconds (5 minutes) for production
- Add monitoring on force-refresh events; alert if triggered >5 times/hour
- Implement proactive refresh 5 minutes before expiry (30 sec buffer)
- Document Entra ID key rotation frequency in deployment guide

## Performance Bottlenecks

### 1. PDF Text Extraction Line-by-Line Processing

**Issue:** PDF parsing in `src/core.py` lines 66-113 processes each line independently without context, leading to split records across lines requiring lookahead logic.

**Problem:** 
- Each line tested for patterns (IBAN, montant); requires multiple regex passes per line
- Lookahead to next line for missing montants adds complexity and misses edge cases
- Large PDFs (1000+ pages) cause excessive regex compilation/matching

**Files:** `src/core.py` lines 44-114 (PDFParser.parse_file)

**Cause:** pdfplumber text extraction loses table structure; regex-based line parsing is brittle

**Improvement path:**
- Use pdfplumber's `extract_table()` method instead of raw text extraction to preserve structure
- Batch process lines in groups of 3-4 (IBAN + 2 lines for name/amount) to reduce lookahead
- Pre-compile all regexes at module load time
- Add benchmarking: current speed baseline needed; target <5s for 500-page PDF

### 2. Excel Parsing Column Detection Linear Search

**Issue:** `ExcelParser.detect_columns()` at lines 205-249 iterates through all keywords and columns with nested loops. Large Excel files with many columns (100+) and extended keyword lists will be slow.

**Files:** `src/core.py` lines 205-249

**Cause:** O(m*n) where m = keywords, n = columns; no early exit optimization

**Impact:** Noticeable delay (>1s) for files with 50+ columns and custom headers

**Improvement path:**
- Build single lowercase column map once; iterate keywords against it
- Return on first match instead of testing all combinations
- Add unit test with 100-column Excel file; measure time
- Target: <100ms for column detection on 100-column file

### 3. Fuzzy Matching Score Recalculation

**Issue:** Fuzzy matcher uses `SequenceMatcher.ratio()` without caching. Same company name pairs may be compared multiple times if batched audits process overlapping datasets.

**Files:** `src/core.py` lines 320-321 (FuzzyMatcher)

**Impact:** Batch mode (9+ phase) comparing 1000+ companies wastes CPU on redundant comparisons

**Improvement path:**
- Add simple LRU cache (cachetools.LRUCache) for match results keyed by (nom_pdf, nom_excel)
- Document cache size (default 1000 pairs); make configurable
- Test with overlapping batch inputs; measure cache hit rate

## Fragile Areas

### 1. AuditHistory SQLite Database

**Issue:** Audit history uses SQLite with no transaction isolation, concurrent writes, or connection pooling. Multi-instance deployment will have issues.

**Files:** `src/core.py` lines 430-503 (AuditHistory class)

**Why fragile:** 
- Each method opens new connection without retry logic
- No transaction boundaries; partial inserts possible on crash
- SQLite locks entire DB file on write; batch audits will serialize
- No schema versioning; migrations will break old audits.db

**Safe modification:** 
- Use context manager with explicit transactions (already present at line 437)
- Add retry decorator with exponential backoff for connection errors
- Test concurrent writes with threading.Thread calls
- Migration: provide schema_version table and migration functions before adding columns

**Test coverage gaps:** 
- No tests for concurrent audit saves
- No tests for corrupted/missing audits.db
- Missing: concurrent write conflict scenarios

### 2. ThreadingUI Event Loop Blocking

**Issue:** Threading event loop at `src/main.py` lines 179-180 (batch processing) and line 375-376 does not protect shared state (`self.last_resultats`, batch items list).

**Why fragile:** 
- No locks on `self.batch_items` list; concurrent reads/writes during live updates possible
- `self.should_cancel` flag is not atomic; race condition between thread check and cancellation
- UI update calls via `self.root.after()` are queued but may execute out of order if multiple batches run

**Safe modification:** 
- Add threading.Lock for batch_items access
- Use threading.Event for should_cancel instead of boolean
- Document that only one batch can run at a time; disable "Mode Batch" button during execution
- Add unit test with explicit threading.Thread for simultaneous audit + cancel

**Test coverage gaps:**
- No test of simultaneous batch/cancel operations
- No test of rapid button clicks during processing

### 3. Bin-file-handling in Upload/Delete

**Issue:** File deletion in `src/main.py` line 322 checks if path is under work_dir but uses `str.startswith()` which is vulnerable to symlink escape and prefix matching bugs.

**Why fragile:** 
- `startswith()` check passes if work_dir is "/home/user/app" and file is "/home/user/app_backup/file" (prefix match but different directory)
- Symbolic links can escape the chroot check
- Race condition: file could be moved between check and deletion

**Safe modification:**
- Use `os.path.commonpath()` and verify it equals normalized work_dir
- Resolve symlinks with `os.path.realpath()` before comparison
- Use `pathlib.Path.relative_to()` which raises exception on escape attempts
- Example: `Path(file_abs).relative_to(Path(work_dir))` then check no ".." components

**Test coverage gaps:**
- No test of symlink escape attempts
- No test of prefix matching edge cases (app vs app_backup)

## Scaling Limits

### 1. Batch Processing Sequential Bottleneck

**Current capacity:** Single-threaded batch processing in `src/main.py` line 382-429 processes couples sequentially. Throughput = audits_per_second * number_in_batch.

**Limit:** 
- At 2 audits/sec (assuming 5s per audit), batch of 100 couples = 50 seconds processing + UI overhead
- User can't cancel individual items; must cancel entire batch
- No progress granularity per couple (only shows percentage)

**Scaling path:**
- Add ThreadPoolExecutor for parallel audit processing (max 4 workers to avoid resource exhaustion)
- Queue couples with results callback for individual completion tracking
- Implement cancellation token per couple; allow selective cancellation from UI
- Store batch results in temp DB (SQLite) instead of memory to avoid OOM on large batches

### 2. In-Memory Result Storage

**Issue:** Results stored in `self.last_resultats` and batch results in all_results list (line 413). Large audits with 10000+ companies will consume significant memory.

**Current limit:** Assume ~200 bytes per result dict × 10000 companies = 2MB per audit. 10 concurrent batches = 20MB. Tkinter on Windows may have UI lag above 50MB.

**Scaling path:**
- Stream results to file during audit (JSON Lines format) instead of accumulating list
- Page results in UI (show first 100, load more on scroll)
- Implement result export with chunked writing instead of loading all in memory
- For multi-instance: move result storage to persistent backend (database)

### 3. PDF Parsing Memory for Large Documents

**Issue:** `pdfplumber.open()` loads entire PDF into memory. 1000-page PDFs at 1MB/page = 1GB RAM.

**Current limit:** Windows Tkinter app limited to ~512MB heap; will crash on very large PDFs

**Scaling path:**
- Stream PDF parsing page-by-page using pdfplumber's page-by-page API
- Accumulate results in generator or write to temp file instead of list
- Implement size check before opening; warn user if >100MB, offer to split
- For high-volume: migrate to backend API (FastAPI) for async processing

## Dependencies at Risk

### 1. pdfplumber Dependency Stability

**Risk:** `pdfplumber` is actively maintained but has breaking changes between minor versions. No pinned version in requirements.txt.

**Current:** `requirements.txt` line 1 just says `fastapi>=0.111.0`; no pdfplumber constraint

**Impact:** 
- Pip install could pick incompatible version
- Text extraction behavior may differ between versions
- Known issue: pdfplumber 0.9+ changed table extraction API

**Mitigation plan:**
- Pin pdfplumber to exact version (current: 0.10.8) with range `pdfplumber>=0.10.8,<0.11`
- Add test that verifies extraction behavior against known PDF sample
- Document in README which pdfplumber version was tested
- Monitor upstream for breaking changes quarterly

### 2. thefuzz (fuzz matching) Optional Dependency

**Risk:** Fuzzy matching gracefully degrades to equality if thefuzz unavailable (line 23 fabric_audit_engine.py), but this silent fallback may cause audit failures without warning.

**Current mitigation:** Try/except at import; fallback to strict matching

**Impact:** User gets worse matching accuracy without notification

**Mitigation plan:**
- Make thefuzz required in requirements.txt (remove try/except grace)
- Add explicit check at app startup: `if _fuzz is None: raise RuntimeError("thefuzz required")`
- Add test that verifies thefuzz is available and working

## Missing Critical Features

### 1. No Audit Trail / Logging of Data Access

**Issue:** No centralized audit log of who ran which audit, what data was processed, and what results were generated. Only in-database entry without user/timestamp correlation.

**Files:** `src/core.py` (AuditHistory) and `scripts/api_server.py` (no audit endpoint logging)

**Blocks:** 
- GDPR: Cannot demonstrate who accessed which personal data
- Compliance: No traceable record for audits
- Incident response: Cannot determine when data breach occurred

**Remediation path:**
- Implement structured audit logging with: user (from JWT), timestamp, document_id, result summary, IP address
- Send logs to Application Insights or centralized logging backend
- Implement 1-year retention policy
- Add audit log query endpoint (requires AUDIT_LOGS read role)

### 2. No Result Encryption at Rest

**Issue:** audit results stored in SQLite plaintext (`audits.db` and `results` table). If DB is exfiltrated, company financial data is exposed.

**Files:** `src/core.py` lines 437-462 (AuditHistory database schema)

**Blocks:** Data protection requirements for regulated customers

**Remediation path:**
- Encrypt sensitive fields (montant_pdf, montant_excel, ecart, societe, iban) using AES-256-GCM with key from Azure Key Vault
- Implement transparent encryption/decryption in AuditHistory
- Add migration script to encrypt existing data
- Test with NIST test vectors to verify correctness
- Document key rotation procedure

### 3. No Rollback / Undo for Batch Processing

**Issue:** Batch audits cannot be undone if results are incorrect. All results are saved to history immediately; no draft/approve workflow.

**Files:** `src/main.py` lines 415-419 (batch history save is not transactional)

**Blocks:** Prevents use in regulated environments requiring approval before audit is final

**Remediation path:**
- Add audit status field: DRAFT → APPROVED → FINAL
- Implement soft-delete (mark_deleted instead of physical delete) for audit records
- Add approval workflow for batches: show summary, require human approval before finalizing
- Add UI "Undo last audit" for 30 minutes after completion

## Test Coverage Gaps

### 1. No Testing of Out-of-Order Date Parsing

**Issue:** Date parsing in fabric_audit_engine accepts multiple formats but does not handle dates in non-ISO order (e.g., DD/MM/YYYY vs MM/DD/YYYY ambiguity).

**Files:** `scripts/fabric_audit_engine.py` (no date parsing function shown)

**What's not tested:** 
- Dates parsed as wrong date when format is ambiguous (12/03/2025 = Dec 3 or Mar 12?)
- International date format handling in schema validation

**Risk:** 
- French documents use DD/MM/YYYY; OCR may return MM/DD/YYYY
- Audits fail silently if date is off by a month

**Priority:** Medium — affects all insurance contract audits

### 2. No Testing for Concurrent Azure Function Calls

**Issue:** `azure_functions/function_app.py` delegates to Durable Functions, but tests mock everything. Real deployment may expose race conditions.

**Files:** `tests/azure_functions/test_function_app.py` (uses mocks)

**What's not tested:** 
- Multiple simultaneous audit requests to same Function App instance
- Function App retry behavior on transient errors
- DurableOrchestrationContext state consistency

**Risk:** Production traffic may trigger untested concurrency bugs

**Priority:** High — currently untestable without Azure account in CI

### 3. No Testing of Full E2E Audit Flow

**Issue:** No test executes complete path: document → OCR → Fabric → comparison → FIC generation with real-ish data.

**Files:** Test suite splits by layer (test_ocr_fabric, test_audit_pipeline, etc.) but no E2E integration test

**What's not tested:** 
- Data loss between pipeline stages
- Schema mismatches between OCR result and audit_input
- FIC generation with actual audit results

**Risk:** Integration bugs discovered only in production

**Priority:** High — critical for production readiness

---

*Concerns audit: 2026-06-10*
