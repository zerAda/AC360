# Architecture

**Analysis Date:** 2026-06-11

## System Overview

AC360 is a read-only commercial assistant for Microsoft Teams, powered by Microsoft Copilot Studio. It provides intelligent document search and analysis across SharePoint client folders while enforcing strict security boundaries (SSO, user-scoped permissions, no hallucinations).

```
┌──────────────────────────────────────────────────────────────────────────┐
│           Copilot Studio (AC360) - Conversational Layer                  │
│  `src/copilot/AC360/` - Topics, RAG, Actions, Connection References     │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
      ┌────┴─────────────────────────────────────────────────────────┐
      │                    OAuth / Entra ID SSO                      │
      ▼                                                              ▼
┌──────────────────────┐                        ┌──────────────────────────┐
│  FastAPI Backend API │◄────────────────────►  │  Microsoft Entra ID      │
│  `scripts/api_*.py`  │   JWT RS256 (JWKS)     │  Authentication & Authz  │
│  `azure_functions/`  │                        └──────────────────────────┘
└──────────┬───────────┘
           │ Orchestration: Download → OCR → Fabric → Compare → FIC
      ┌────┴────────────────────────────────────────┐
      │                                              │
      ▼                                              ▼
┌──────────────────────┐                ┌──────────────────────────────┐
│  SharePoint Online   │                │  Azure Services              │
│  (Dossiers_Clients)  │                │  • Document Intelligence OCR │
│  Read-Only Delegate  │                │  • Microsoft Fabric (SQL)    │
└──────────────────────┘                │  • Application Insights      │
                                         └──────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Copilot Agent** | Conversation topics, RAG orchestration, user intent routing | `src/copilot/AC360/agent.mcs.yml` |
| **Topics** | Flow logic for 25+ use cases (summary, search, alerts, drafts) | `src/copilot/AC360/topics/` |
| **Knowledge Sources** | SharePoint site connection, RAG configuration | `src/copilot/AC360/knowledge/` |
| **FastAPI Server** | HTTP API for audit triggers, status queries, document resolve | `scripts/api_server.py` |
| **Authentication** | JWT RS256 validation, JWKS caching, scope/role verification | `scripts/auth.py` |
| **Durable Functions** | Orchestration engine for multi-stage audit pipelines | `azure_functions/function_app.py` |
| **Audit Pipeline** | Pure orchestration logic (document→OCR→Fabric→compare) | `azure_functions/shared/audit_pipeline.py` |
| **Audit Engine** | Field aliasing, normalization, comparison, verdict logic | `scripts/fabric_audit_engine.py` |
| **SharePoint I/O** | Secure document download via Graph with size/extension guards | `azure_functions/shared/sharepoint.py` |
| **Feature Gates** | Per-user, per-team consumption blocking and admin controls | `scripts/feature_flags.py` |
| **Safe Logger** | PII/secret redaction in logs and error messages | `scripts/safe_logger.py` |

## Pattern Overview

**Overall:** Three-tier distributed pipeline with clear separation of concerns:
1. **Conversation Layer** (Copilot Studio) – Intent parsing, RAG search, user-facing responses
2. **API/Auth Layer** (FastAPI) – HTTP boundary, JWT validation, rate limiting, feature gates
3. **Processing Layer** (Durable Functions + Scripts) – Stateless orchestration, cloud integrations

**Key Characteristics:**
- **Read-only enforcement:** No modification of SharePoint data; all responses are citations from existing documents
- **User-scoped permissions:** Audit trails keyed to user identity (UPN hash); SharePoint access validated per-user
- **Injection-safe input:** Path traversal guards, allowlist filtering, shell-safe regex patterns
- **Fail-fast architecture:** Configuration errors on startup; missing auth variables prevent app launch
- **Testable by design:** Pure functions with dependency injection (no direct cloud SDK calls in core logic)

## Layers

**Copilot Studio (Presentation Layer):**
- Purpose: User-facing conversational interface; RAG query orchestration
- Location: `src/copilot/AC360/`
- Contains: 25+ topics (YAML), connection references, agent instructions, knowledge sources
- Depends on: SharePoint Read-Only connector, FastAPI backend for audit/drafting endpoints
- Used by: End users via Teams or Copilot Web

**FastAPI Backend (API/Security Layer):**
- Purpose: HTTP entry point; authentication, rate limiting, feature gates, document resolution
- Location: `scripts/api_server.py` (646 lines), utility modules in `scripts/`
- Contains: REST endpoints (`/api/audit`, `/api/status`, `/api/document/resolve`), middleware for security headers, token validation
- Depends on: Azure Entra ID (JWKS), Azure Durable Functions, feature flag store, safe logging
- Used by: Copilot Studio actions and external API consumers

**Orchestration Layer (Durable Functions):**
- Purpose: Async workflow engine for document audit pipelines with retry/durability semantics
- Location: `azure_functions/function_app.py` (240+ lines)
- Contains: Activity definitions (download, OCR, Fabric query, FIC generation), orchestration state machine
- Depends on: Azure Blob Storage (for Durable state), Graph API, Document Intelligence, Fabric SQL
- Used by: FastAPI backend (async job triggering)

**Business Logic Layer (Scripts):**
- Purpose: Pure, testable logic for audit, comparison, and document processing
- Location: `scripts/` directory (15+ Python modules)
- Contains: Audit engine, OCR post-processing, Fabric query builder, FIC generation, admin controls
- Depends on: Pandas, thefuzz (fuzzy name matching), pydantic for validation
- Used by: Durable Functions activities, test suite, CLI utilities

**Test Suite:**
- Purpose: 30+ test files covering security, logic, and integration
- Location: `tests/backend/`, `tests/azure_functions/`, `tests/admin/`
- Contains: Unit tests, mocks for cloud services, integration tests with schema validation
- Depends on: pytest, pytest-asyncio, unittest.mock
- Coverage: Auth (JWT, OBO), rate limiting, path traversal, IDOR, job isolation, OCR timeout

## Data Flow

### Primary Request Path: Document Audit

1. **User Request** (`Teams` or `Copilot Web`)
   - User asks AC360 to audit a client document

2. **Copilot Topic Routing** (`src/copilot/AC360/topics/*.yml`)
   - Topic matches intent and extracts document ID

3. **FastAPI: POST /api/audit** (`scripts/api_server.py:299`)
   - Validates document_id against allowlist (no path traversal)
   - Verifies Azure AD token (JWT RS256 via JWKS)
   - Checks rate limits (10 audits/hour per user)
   - Checks feature gates (admin may block user/feature/team)
   - Acquires OBO token if configured (delegate Graph access to user)
   - Pre-checks user's SharePoint access (fast-path, as-user Graph call)
   - Triggers Azure Durable Function with `owner_hash` for IDOR protection

4. **Durable Orchestration** (`azure_functions/function_app.py`)
   - **Download Activity:** Graph API (user-delegated or app identity)
     - Fetches document metadata (name, size)
     - Validates extension (.pdf, .docx, .png, .jpg, .tiff)
     - Validates size (max 25 MB)
     - Sanitizes filename (anti path-traversal)
     - Downloads to `JOBS_BASE_DIR / {document_id}/`
   
   - **OCR Activity:** Azure Document Intelligence
     - Processes PDF/image → extracts structured fields (client name, policy #, dates)
     - Result validated against `schemas/ocr_result.schema.json`
   
   - **Fabric Query Activity:** Microsoft Fabric SQL Endpoint
     - Queries ARTUS (reference system) for matching client record
     - Lookup by SIRET (exact match) or name (fuzzy via thefuzz)
   
   - **Compare Activity:** `scripts/fabric_audit_engine.py`
     - Pure comparison logic (zero cloud calls)
     - Field aliasing (OCR "Raison Sociale" → canonical "nom_client")
     - Normalization (dates, currency, whitespace)
     - Verdict: CONFORME | ECART | INCERTAIN | CLIENT_NON_TROUVE
   
   - **FIC Generation** (Optional): `scripts/generate_fic_draft.py`
     - If verdict ∈ {ECART, INCERTAIN}, generate audit report (Word document)
     - Stored for manual review; not sent to client automatically

5. **Status Query** (`scripts/api_server.py:/api/status/{job_id}`)
   - User polls for audit completion
   - Ownership verified (owner_hash stored in Durable input)
   - Returns flattened response: verdict, field details, FIC availability

6. **Copilot Presentation**
   - Audit results formatted as structured response with citations
   - No synthesis beyond source data (useModelKnowledge: false)

### Secondary Flow: RAG Search

1. **User Query** (`Teams`)
   - "Find the latest contract for client Alpha"

2. **Copilot RAG Action** (`src/copilot/AC360/knowledge/`)
   - Uses native Copilot Studio RAG on SharePoint library
   - SharePoint search filtered to user's accessible folders
   - Returns document excerpts with citations

3. **Copilot Response**
   - Strictly sourced; no extrapolation

### Tertiary Flow: Document Resolution

1. **User Search** (`POST /api/document/resolve`)
   - Query: "Alpha contract" or "SIRET 12345678901234"

2. **FastAPI Resolution** (`scripts/api_server.py` - document_resolve handler)
   - Graph API: Searches SharePoint drive for matching files
   - Filters by extension (auditable types)
   - Returns paginated list with item IDs and names

3. **User Selection**
   - User picks document from list → triggers audit if desired

**State Management:**
- **In-Memory (FastAPI):** User rate limit tracking, audit job ownership (fast-path IDOR)
- **Azure Storage (Durable):** Orchestration state, job history, outputs
- **Azure Key Vault:** Secrets (OCR key, Fabric credentials), rotated via secret rotation runbook
- **File System (JOBS_BASE_DIR):** Downloaded documents, OCR results, generated FIC drafts (ephemeral)

## Key Abstractions

**AuditDeps (Dependency Injection):**
- Purpose: Decouple audit orchestration from cloud I/O; enables testing without real Azure services
- Examples: `azure_functions/shared/audit_pipeline.py:78`
- Pattern: Dataclass with `download()`, `ocr()`, `fetch_reference()`, `make_fic()`, `compare()` callables
- Usage: `run_audit(document_id, client_context, deps=AuditDeps(...))`

**AppConfig (Configuration as Data):**
- Purpose: Centralized, frozen configuration; fail-fast on missing required vars
- Examples: `scripts/config.py:27`
- Pattern: Frozen dataclass with computed properties (JWKS URL, issuer)
- Usage: Imported early in app startup; prevents misconfiguration from reaching endpoints

**Audit Result Schema:**
- Purpose: JSON schema validation for audit outputs; ensures consistent structure
- Examples: `schemas/audit_result.schema.json`
- Pattern: JSONSchema with required fields (verdict, client_document, fields, score)
- Usage: Validated in `azure_functions/shared/audit_pipeline.py` during orchestration

**Feature Flags as Categorical Gates:**
- Purpose: Per-user, per-team, per-feature admin controls without database
- Examples: `scripts/feature_flags.py`
- Pattern: Hash-based lookup with configurable block reasons
- Usage: `is_allowed("audit", user_id_hash=hash_id(upn))` in FastAPI handler

## Entry Points

**FastAPI Application Server:**
- Location: `scripts/api_server.py`
- Triggers: HTTP requests (POST /api/audit, GET /api/status, POST /api/document/resolve, etc.)
- Responsibilities:
  - Listen on port (default 8000)
  - Validate JWT bearer tokens
  - Enforce rate limits per user
  - Check feature gates
  - Invoke Durable Functions
  - Return job status or document lists

**Copilot Studio Bot:**
- Location: `src/copilot/AC360/agent.mcs.yml`
- Triggers: User messages in Teams channel or Copilot Web
- Responsibilities:
  - Parse user intent (25 topics)
  - Invoke RAG search or FastAPI endpoints
  - Format responses with citations
  - Enforce read-only guardrails (system prompt)

**Azure Durable Functions:**
- Location: `azure_functions/function_app.py` (orchestration entry point)
- Triggers: HTTP POST from FastAPI (function URL + code key)
- Responsibilities:
  - Coordinate multi-stage workflow
  - Retry failed activities (built-in durability)
  - Persist state to Azure Storage
  - Return job ID and status query URI

**Background Tasks & Utilities:**
- **Validate Copilot YAML:** `scripts/validate_copilot_yaml.py` (CI/CD gate)
- **Package Release:** `scripts/package_release.ps1` (security checks before deployment)
- **Sync Copilot:** `scripts/sync_copilot.ps1` (push/pull Copilot definitions)
- **Run Demo:** `scripts/run_demo.py` (interactive walkthrough)

## Architectural Constraints

- **Threading:** Async/await throughout FastAPI; single-threaded event loop per worker. Durable Functions handle parallelism via activity concurrency limits.
- **Global state:** Rate limit map in FastAPI (in-memory, per-process; not shared across workers in production). Audit ownership map (5000-entry cache, cleared on overflow). JWKS cache with TTL-based refresh.
- **Circular imports:** None detected. Clean module hierarchy: config → auth → api_server; audit_pipeline → fabric_audit_engine; sharepoint (no circular deps).
- **Secrets:** NEVER hardcoded. Always from `os.environ` or `azure.identity.DefaultAzureCredential` (Managed Identity). `.env` files for local dev only; never committed.
- **File paths:** All relative paths resolved via `os.path.abspath()` with `os.path.commonpath()` checks to prevent traversal escapes.
- **Cloud SDK isolation:** Durable Functions SDK (`azure.durable_functions`) imported only in `function_app.py` (runtime-specific); wrapped with try/except to not break test collection.

## Anti-Patterns

### Hallucination Risk (Addressed)

**What happens:** LLM might extrapolate beyond source documents to fill gaps (e.g., inventing client details).
**Why it's wrong:** Commercial context demands factual accuracy; invented details harm client relationships and incur liability.
**Do this instead:** Copilot agent config enforces `useModelKnowledge: false` + system prompt forbids extrapolation. Test suite includes hostile prompts (`tests/red_team/`) to detect jailbreaks.

### Credential Leakage in Logs (Addressed)

**What happens:** Exception messages might include API keys, tokens, or sensitive data in stack traces.
**Why it's wrong:** Logs are shipped to Application Insights; secrets in logs = security incident.
**Do this instead:** `scripts/safe_logger.py` redacts patterns like `KEY=...`, `TOKEN=...`, `PASSWORD=...` before logging. Audit pipeline wraps exceptions with `_safe_error()` (also in `azure_functions/shared/audit_pipeline.py:65`).

### Unbounded Memory Growth (Addressed)

**What happens:** In-memory caches (rate limits, audit owners) grow without limit, causing OOM.
**Why it's wrong:** Production deployments run 24/7; unbounded growth crashes the service.
**Do this instead:** Rate limit store has explicit 1000-entry cleanup threshold. Audit owner map caps at 5000 entries and clears on overflow. JWKS cache has TTL-based invalidation.

### Timing Attacks on Feature Flags (Partial Mitigation)

**What happens:** Admin checks `is_allowed(user_id)` but the check is fast for blocked users, slow for allowed ones (info leak).
**Why it's wrong:** Adversary can measure response time to infer admin blocking.
**Do this instead:** Hash-based constant-time lookup. Future: Add jitter to response times.

### Path Traversal via Document ID (Addressed)

**What happens:** Attacker passes `document_id = "../../etc/passwd"` to download arbitrary files.
**Why it's wrong:** Breaks read-only guarantee; exposes system files.
**Do this instead:** 
  - FastAPI validates document_id as UUID format only (`scripts/api_server.py:155`)
  - Durable Function download uses `os.path.commonpath()` to ensure resolved path stays under `JOBS_BASE_DIR` (`azure_functions/shared/sharepoint.py:99`)
  - Filename sanitization strips path separators and null bytes

### IDOR: Access to Others' Audit Jobs (Addressed)

**What happens:** User A polls `GET /api/status/job_B` (User B's audit) and gets results.
**Why it's wrong:** User A learns about User B's documents (confidentiality breach).
**Do this instead:** 
  - Ownership tracked in memory map (fast-path) for first 5000 jobs
  - For scale-out: ownership persisted in Durable orchestration input (owner_hash)
  - Both checks verify hash(user_upn) matches before returning status (`scripts/api_server.py:216`, `api_server.py:225`)

### Shell Injection in Generated Reports (Addressed)

**What happens:** Client data (e.g., company name containing `; rm -rf /`) rendered into PowerShell script.
**Why it's wrong:** Script executed as admin → data loss.
**Do this instead:** Generated scripts are **read-only** (`scripts/package_release.ps1` enforces PowerShell `-WhatIf` by default). FIC drafts are Word documents, not scripts. No shell command interpolation of user data.

## Error Handling

**Strategy:** Fail-fast configuration validation; graceful degradation at runtime.

**Patterns:**
- **Config Phase (Startup):** Missing TENANT_ID/CLIENT_ID → process exits immediately. Caught by supervision layer (systemd/Container).
- **Request Phase (Endpoint):** Invalid JWT → HTTP 401 + safe error message (no token details leaked). Missing header → 400. Rate limited → 429.
- **Activity Phase (Durable):** Network error in Graph API → automatic retry (configurable, default 3 attempts). Exhausted retries → audit marked "Failed" with error detail.
- **Validation Phase:** JSON schema mismatch → logged but processed (graceful degrade, not reject).
- **Logging:** All errors logged via `safe_logger.log_security()` with sanitized message (secrets redacted).

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module + `safe_logger` wrapper
- Approach: Structured logging (key-value pairs) to Application Insights
- Redaction: `safe_logger.redact()` removes patterns (API_KEY=..., PASSWORD=..., etc.)
- PII: User identity logged as hash (SHA256) not cleartext UPN

**Validation:**
- Input: HTTPException on malformed requests (document_id format, query length)
- Output: JSONSchema validation of audit results (schemas/*.json)
- Configuration: Pydantic model (AppConfig) with frozen dataclass

**Authentication:**
- Provider: Microsoft Entra ID (OAuth 2.0)
- Token Format: JWT RS256
- Verification:
  1. Unverified header extracted → check `kid` and `alg`
  2. Public key fetched from JWKS endpoint (cached, TTL 1 hour)
  3. Signature verified
  4. Claims validated (exp, nbf, aud, iss, scp, roles)
- Audience: Copilot Studio action client ID (from config)
- Scopes: Configurable (default: "Audit.Trigger")
- Roles: Optional (configurable via REQUIRED_ROLES)

**Authorization:**
- User-scoped: Audit results tied to user identity (UPN hash)
- SharePoint-scoped: Graph API access token respects user's SharePoint permissions (user-delegated OBO flow)
- Feature-scoped: Admin can block audit/rag/email_draft per user, team, or globally (feature_flags.py)

---

*Architecture analysis: 2026-06-11*
