<!-- refreshed: 2026-06-10 -->
# Architecture

**Analysis Date:** 2026-06-10

## System Overview

AC360 is a dual-layer system: **Copilot Studio chatbot** (Microsoft Copilot Studio / Teams) + **backend audit pipeline** (FastAPI + Azure Durable Functions). The backend orchestrates document OCR → audit comparison → FIC document generation, all read-only, federated via Microsoft Entra ID.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Users (Teams / Copilot Chat)                          │
│                              (Entra ID Auth)                                 │
└────────────────────────┬─────────────────────────────────────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         ▼                                ▼
   ┌──────────────────┐           ┌─────────────────────┐
   │ Copilot Studio   │           │  FastAPI Backend    │
   │  (Topics/RAG)    │───────────▶  (`api_server.py`)  │
   │ SharePoint RAG   │           │  Port 8000          │
   └──────────────────┘           └────────┬────────────┘
         │                                 │
         │                    ┌────────────┴─────────────┐
         │                    ▼                          ▼
         │          ┌──────────────────────┐   ┌────────────────────┐
         │          │ Azure Functions      │   │ Rate Limiting,     │
         │          │ (Durable Functions)  │   │ JWT Auth, JWKS     │
         │          │ `function_app.py`    │   │ Cache, Path Sec.   │
         │          └──────┬──┬──┬─────────┘   └────────────────────┘
         │                 │  │  │
         │    ┌────────────┘  │  └──────────────┐
         │    │               │                 │
         │    ▼               ▼                 ▼
         │  Download        OCR             Fetch Reference
         │  SharePoint   (Doc Intelligence)  (Fabric OneLake)
         │  via Graph       via Azure         Delta Lake
         │  API
         │
         └──────────────► Audit Comparison Engine
                          (`fabric_audit_engine.py`)
                          ▼
                    ┌──────────────────┐
                    │  FIC Generation  │
                    │  (Word Document) │
                    │ `generate_fic..` │
                    └──────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Copilot Studio Agent** | Multi-topic conversational AI, SharePoint RAG, moderation | `src/copilot/AC360/agent.mcs.yml` |
| **FastAPI API Server** | HTTP gateway, JWT/JWKS auth, rate limiting, job orchestration | `scripts/api_server.py` |
| **Azure Durable Functions** | Orchestrates async audit pipeline (download → OCR → compare → FIC) | `azure_functions/function_app.py` |
| **Audit Pipeline (Pure Logic)** | Testable orchestration (no I/O, deps injected) | `azure_functions/shared/audit_pipeline.py` |
| **SharePoint Integration** | Secure document download via Graph API | `azure_functions/shared/sharepoint.py` |
| **OCR Extraction** | Azure Document Intelligence bridge | `scripts/process_document_ocr.py` |
| **Audit Comparison Engine** | Typified field matching, normalization, verdict logic | `scripts/fabric_audit_engine.py` |
| **Fabric OneLake Reference** | Client reference lookup (SIRET-first, then name match) | `scripts/fabric_onelake.py` |
| **FIC Document Generation** | Word document template + OCR/Fabric data → signed FIC | `scripts/generate_fic_draft.py` |
| **Config & Auth** | Centralized config (fail-fast), JWT verification, JWKS cache | `scripts/config.py`, `scripts/auth.py` |
| **Tkinter Desktop UI** | Local audit (PDF/Excel matching, batch mode, export) | `src/main.py`, `src/core.py` |

## Pattern Overview

**Overall:** **Layered (3-tier) + Async Pipeline** with dependency injection for testability.

**Key Characteristics:**
- **Read-only guardrails** - No document modification, deletion, or creation (except FIC draft for review)
- **Injection-based testing** - Core pipeline (`audit_pipeline.py`) accepts `AuditDeps` object; all I/O pluggable (fakes in tests, real in prod)
- **Import-safe modules** - Azure SDK imports protected in try/except; pytest can run without runtime
- **Schema validation** - OCR, audit input, audit result validated against JSON schemas in `schemas/`
- **Fail-fast configuration** - Auth env vars (TENANT_ID, CLIENT_ID) verified at API startup, not lazily

## Layers

**Presentation Layer (UI / Routing):**
- Purpose: HTTP endpoints, WebSocket management, user auth gateway
- Location: `scripts/api_server.py`
- Contains: FastAPI routes (@app.post, @app.get), middleware (AppInsights, rate-limit, security headers), JWT validation, job status polling
- Depends on: `config.py`, `auth.py`, Azure Functions REST client
- Used by: Copilot Studio (HTTP POST `/api/audit`), Teams (polling `/api/audit/{job_id}/status`), file downloads (`/api/download/{job_id}/{filename}`)

**Orchestration Layer (Async Pipeline):**
- Purpose: Coordinate document → OCR → audit → FIC workflow as durable, resilient steps
- Location: `azure_functions/` (function_app.py, shared/audit_pipeline.py)
- Contains: Durable Functions orchestrator, activity functions, pure audit logic, dependency injection frame
- Depends on: Graph API, Document Intelligence, Fabric SDK, file I/O
- Used by: FastAPI gateway (via Azure Functions HTTP trigger), job status monitoring

**Business Logic Layer (Typified Audit):**
- Purpose: Field extraction, normalization, comparison, verdict assignment
- Location: `scripts/fabric_audit_engine.py`, `scripts/fabric_onelake.py`, `scripts/process_document_ocr.py`
- Contains: OCR field aliasing, montant/date/name normalization, threshold-based matching (MATCH/MISMATCH/UNCERTAIN), SIRET-first reference lookup
- Depends on: None (pure Python, no cloud imports); schemas for validation
- Used by: `audit_pipeline.py` (compare function), tests (direct unit testing)

**Data Access Layer (Cloud Integrations):**
- Purpose: Abstract external APIs (SharePoint, Document Intelligence, Fabric, Graph)
- Location: `azure_functions/shared/sharepoint.py`, `scripts/auth.py`, `scripts/fabric_onelake.py`
- Contains: Graph API client (document download, item metadata), Entra ID token validation, JWKS fetching, Fabric Delta Lake reads
- Depends on: httpx, azure-identity, azure.functions (in runtime only)
- Used by: Orchestration layer (via AuditDeps injection)

**Desktop/Local Audit (Tkinter App):**
- Purpose: Standalone PDF/Excel audit without cloud dependencies (for demo, testing, or air-gapped environments)
- Location: `src/main.py`, `src/core.py`
- Contains: Tkinter GUI, PDF parsing (pdfplumber), Excel parsing (pandas), normalization, fuzzy matching (thefuzz), export (Excel, CSV, PDF via reportlab)
- Depends on: pdfplumber, pandas, openpyxl, thefuzz, reportlab
- Used by: Local users (python src/main.py), demo scripts

## Data Flow

### Primary Request Path (Cloud Audit via Copilot)

1. **User Query in Teams** → Copilot Studio topic routed (e.g., "Lancer Audit")
2. **Copilot Studio** → HTTP POST to `scripts/api_server.py:/api/audit` with `document_id` (UUID v4 from SharePoint)
3. **API Gateway** (`api_server.py`) → Validates JWT (RS256 via JWKS), document_id (UUID + confinement), rate limit (10/hour/user)
4. **Trigger Azure Function** → POST to `azure_functions/function_app.py:http_start` (Durable Functions orchestrator)
5. **Orchestrator** (`function_app.py:_audit_orchestration`) → Calls activities in sequence:
   - **Download Activity** → `sharepoint.py:download_document()` → Graph API `/drives/{drive_id}/items/{item_id}/content` → writes `jobs/{uuid}/filename.pdf`
   - **OCR Activity** → `process_document_ocr.py:extract_document_azure()` → Azure Document Intelligence → JSON dict with fields/tables
   - **Audit Activity** → `audit_pipeline.py:run_audit()` → Calls deps:
     - `fetch_reference(identity)` → `fabric_onelake.py` → OneLake Delta Lake (SIRET/name match)
     - `compare(audit_input)` → `fabric_audit_engine.py:audit()` → verdict (CONFORME/ECART/INCERTAIN/CLIENT_NON_TROUVE)
     - `make_fic(client_name, audit_result)` → `generate_fic_draft.py` → Word doc (if verdict = ECART or INCERTAIN)
6. **Return Status** → Client polls `GET /api/audit/{job_id}/status` until orchestration completes
7. **Download FIC** (if generated) → `GET /api/download/{job_id}/FIC_Brouillon_ClientName.docx`

**State Management:**
- Job metadata (document_id, UPN, timestamps) stored in Durable Functions state store (Azure Storage Queue/Table)
- Intermediate artifacts (downloaded PDF, OCR JSON, FIC .docx) in `JOBS_BASE_DIR` (default `./jobs`)
- No persistent DB (by design); job cleanup via `cleanup_local_artifacts.ps1`

### Secondary Flow: Planner Task Creation (Optional)

1. User sends command in Copilot topic (e.g., "CreerRelancePlanner")
2. POST `/api/planner/task` with `{title, due_date, plan_id, bucket_id}`
3. API validates JWT, creates Microsoft Planner task (via Power Automate or direct Graph call in `planner_integration.py`)

### Tertiary Flow: Local Desktop Audit (Tkinter)

1. User runs `python src/main.py`
2. Selects PDF (bank remittance) + Excel (reference data)
3. Normalizes names (via `Normalizer`), parses montants (regex `[\d\s]+[,\.]\d{2}`)
4. Fuzzy matches societies (SequenceMatcher ≥ 75%)
5. Calculates écarts (Excel - PDF) → coloring (OK green, Manque red, Excès yellow)
6. Exports results (Excel, CSV, PDF via `ResultExporter`)
7. Stores audit in SQLite history (`test_audits.db`)

## Key Abstractions

**AuditDeps (Dependency Injection Frame):**
- Purpose: Makes audit orchestration testable without cloud resources
- Examples: `azure_functions/shared/audit_pipeline.py` lines 78–94
- Pattern: `@dataclass` with callables for download, ocr, fetch_reference, make_fic, compare
  - Tests inject fakes (return hardcoded JSON, no HTTP)
  - Prod injects real implementations (Azure SDK calls)

**Normalizer (Field Normalization):**
- Purpose: Consistent name/value comparison across OCR output + Fabric reference
- Examples: `scripts/fabric_audit_engine.py:_norm_key()`, `src/core.py:Normalizer.normalize()`
- Pattern: Accent stripping, case folding, alphanum-only, whitespace collapse

**FieldAliasing (_FIELD_ALIASES):**
- Purpose: Map arbitrary OCR labels ("Raison sociale", "Plafond hospi.") → canonical fields (nom_client, plafond_hospitalisation)
- Examples: `scripts/fabric_audit_engine.py` lines 30–48
- Pattern: Dict of canonical → [alias1, alias2, ...]; longest-match-first to avoid "nom" capturing "nom du client"

**RateLimiter (In-Memory Store):**
- Purpose: Enforce 10 audits/hour/UPN without external cache
- Examples: `scripts/api_server.py` lines 98–130
- Pattern: `_rate_limit_store[upn] = [timestamps within window]`; cleanup on overflow; periodic asyncio task

## Entry Points

**FastAPI Server:**
- Location: `scripts/api_server.py`
- Triggers: `POST /api/audit`, `GET /api/audit/{job_id}/status`, `GET /api/download/{job_id}/{filename}`, `POST /api/planner/task`, `POST /api/generate-fiche-rdv`, `GET /health`
- Responsibilities: Request validation, auth, rate-limit, job routing, file serving
- Environment: Reads TENANT_ID, CLIENT_ID, AZURE_FUNCTION_URL, AZURE_FUNCTION_KEY, JOBS_BASE_DIR, APPINSIGHTS_INSTRUMENTATIONKEY

**Azure Function Orchestrator:**
- Location: `azure_functions/function_app.py`
- Triggers: HTTP POST from FastAPI (via Durable Functions runtime)
- Responsibilities: Coordinate download → OCR → audit → FIC activities
- Environment: Reads SHAREPOINT_DRIVE_ID, AZURE_FUNCTION_URL, JOBS_BASE_DIR

**Tkinter Desktop App:**
- Location: `src/main.py`
- Entry: `if __name__ == '__main__': main()`
- Responsibilities: File selection, audit execution (threading), batch processing, export
- Dependencies: tkinter (stdlib), pdfplumber, pandas, openpyxl, thefuzz, reportlab, Pillow

**Copilot Studio Agent:**
- Location: `src/copilot/AC360/agent.mcs.yml`
- Topics: ConversationStart, Rsumdossierclient, LancerAudit, Recherchedocumentclient, PreparationRDVRenouvellement, Escalate, etc.
- Knowledge Source: SharePoint Online (hardened RAG, no general LLM knowledge)

## Architectural Constraints

- **Threading:** FastAPI runs single-threaded event loop (uvicorn async); desktop app uses threading (background audit thread to avoid UI freeze). Azure Functions are event-driven (single orchestration instance per job_id).
- **Global state:** Rate-limit store (`_rate_limit_store` in api_server.py) is in-memory, not shared across instances. Durable Functions state stored in Azure Storage, not in-process.
- **Circular imports:** None detected; modules carefully import conditionally (e.g., azure.* only in function_app.py try/except).
- **Synchronous OCR/Fabric calls:** All I/O in Azure Function activities is synchronous (blocking httpx/requests calls); orchestrator layer is async but activities run in thread pool.
- **Document isolation:** Each audit gets `jobs/{uuid}/` directory; no cross-job file access (confinement enforced via os.path.commonpath).
- **Schema validation:** Optional (depends on jsonschema availability) but strongly encouraged; schemas in `schemas/` (audit_input.schema.json, audit_result.schema.json, ocr_result.schema.json).

## Anti-Patterns

### Hardcoded Secrets in Code

**What happens:** Env vars like TENANT_ID, CLIENT_ID visible in config module docstrings/comments
**Why it's wrong:** Risk of leakage in error messages, logs, or stack traces if not carefully redacted
**Do this instead:** Use `safe_logger.redact()` on all exception messages; mask sensitive assigns in error strings (see `audit_pipeline.py` lines 51–53, _SENSITIVE_ASSIGN regex)

### Direct Azure SDK Imports at Module Level

**What happens:** Early `import azure.functions` would fail pytest collection outside runtime
**Why it's wrong:** Breaks local test execution and CI/CD
**Do this instead:** Wrap in `try/except` with `_DURABLE_AVAILABLE` flag (see `function_app.py` lines 25–32); tests inject fakes via AuditDeps

### Missing Path Confinement in File Operations

**What happens:** Downloading SharePoint doc with user-supplied filename could write outside job directory
**Why it's wrong:** Path traversal vulnerability (e.g., filename = "../../../etc/passwd")
**Do this instead:** Sanitize with `_safe_filename()`, then validate final path with `os.path.commonpath()` (see `sharepoint.py` lines 24–33, 88–93)

### Unvalidated document_id in Job Directory Lookups

**What happens:** API accepts any string for document_id, allows arbitrary dir access
**Why it's wrong:** Enumeration/disclosure of other users' audit results
**Do this instead:** Require UUID v4 format, verify directory exists, use commonpath for confinement (see `api_server.py` lines 137–173, _validate_document_id)

### Missing JWKS Caching / TTL

**What happens:** Every API request fetches JWKS from Microsoft, causing rate limits
**Why it's wrong:** Unavailability if Microsoft's service is slow; performance degradation
**Do this instead:** Cache JWKS with TTL (default 3600s), validate token signature locally (see `auth.py` with `cachetools.TTLCache`)

## Error Handling

**Strategy:** Fail-fast on configuration (startup), graceful degradation on transient errors (retries), audit operation never crashes the API (exceptions caught, returned as status "Failed").

**Patterns:**
- **Configuration errors** (missing TENANT_ID): Raised at app startup via `load_config(require_auth=True)`, halts server
- **Auth errors** (invalid JWT): HTTPException 401 or 403, logged with safe_logger.redact()
- **Path traversal** (bad document_id): HTTPException 400 (format) or 404 (not found), logged
- **Rate limit exceeded**: HTTPException 429, no error detail (prevents enumeration)
- **Audit failures** (OCR crash, Fabric unreachable): Captured in `audit_pipeline.py:run_audit()`, returned as `{"status": "Failed", "error": "...", "stages": [...]}` (never raises)
- **Transient cloud errors**: Orchestration retries automatically (Durable Functions retry policies); if all retries fail, audit status = "Failed" + error message

## Cross-Cutting Concerns

**Logging:** 
- Desktop app: `print()` statements with `[PHASE]` prefixes, no PII
- Backend: `safe_logger.log_security()` for sensitive events (auth, path checks); masks secrets via regex; Application Insights integration via AppInsightsMiddleware

**Validation:**
- **Input:** JWT signature (RS256 JWKS), document_id (UUID + confinement), montants (regex), dates (ISO 8601), file extensions (allowlist)
- **Output:** Schema validation (audit_result.schema.json) optional but encouraged; FIC generation validates client name (non-empty, length-bounded)

**Authentication:**
- **Copilot Studio users:** Entra ID implicit (built-in); JWT issued by Microsoft
- **API callers:** JWT RS256 validation via JWKS (`/discovery/v2.0/keys`); scopes checked (Audit.Trigger), roles optional
- **Desktop app:** No auth (local file-based)

---

*Architecture analysis: 2026-06-10*
