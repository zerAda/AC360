<!-- GSD:project-start source:PROJECT.md -->

## Project

**AC360**

AC360 is a read-only commercial assistant for Microsoft Teams, built on Microsoft Copilot Studio with a Python backend (FastAPI + Azure Durable Functions). It lets commercial/insurance staff search SharePoint client folders and run automated document audits — extracting fields via OCR, comparing them against the Fabric/ARTUS reference system, and producing a conformity verdict (CONFORME / ECART / INCERTAIN / CLIENT_NON_TROUVE) plus an optional FIC draft — all under strict security guardrails (Entra ID SSO, user-scoped permissions, no hallucinations).

The application is feature-complete and security-hardened in the repository but has **never been deployed**. This milestone takes the existing AC360 from local/dev to a live, stable, compliant production service for one internal team.

**Core Value:** AC360 is live in production — a 20–100 person team can reliably and compliantly audit client documents from Teams, end-to-end, and one person can operate it with confidence.

### Constraints

- **Tech stack**: Locked to the existing stack — this milestone deploys what exists; no rewrites or new frameworks.
- **Operability**: Single operator — monitoring, alerting, and runbooks must be usable by one person.
- **Compliance**: EU/French data protection (RGPD/GDPR) applies to client PII — retention, PII handling, and DPIA evidence required before go-live.
- **Security**: Read-only enforcement and no-hallucination guardrails must be preserved through deployment.
- **Platform**: Requires an Azure subscription and an M365 tenant (Entra ID, SharePoint, Teams, Copilot Studio).
- **Timeline**: ASAP but no hard deadline — quality and compliance take priority over speed.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12 - Backend API, Azure Functions, data processing, and automation scripts
- YAML - Copilot Studio configuration and topic definitions (`.mcs.yml` files)
- PowerShell - Infrastructure provisioning, deployment, and operational scripts
- Bicep - Infrastructure-as-Code for Azure resource definitions
- JSON - Configuration, schemas, parameters, and test fixtures

## Runtime

- Python 3.12 (configured in `setup.cfg` for mypy)
- Azure Functions Runtime 2.0 (Consumption/Premium plan)
- Microsoft Copilot Studio (cloud-hosted, proprietary Microsoft platform)
- pip (Python package management)
- Lockfile: `requirements.txt` present (root and `azure_functions/`)
- No `pyproject.toml` or `poetry.lock` — uses traditional `setup.cfg` for pytest/mypy configuration

## Frameworks

- FastAPI 0.111.0+ - Async HTTP API gateway server (`scripts/api_server.py`)
- Uvicorn 0.29.0+ - ASGI server for FastAPI
- Azure Functions (Python v2 model) - Serverless orchestration via Durable Functions
- pytest 8.0.0+ - Test framework
- pytest-asyncio 0.23.0+ - Async test support
- pytest-cov 5.0.0+ - Coverage reporting
- Configuration in `setup.cfg` with asyncio_mode auto, CLI logging enabled
- Bicep CLI - Infrastructure deployment
- Azure CLI - Azure resource management
- GitHub Actions - CI/CD pipeline (`.github/workflows/ci.yml`, `cd-staging.yml`)
- Gitleaks 8.18.2 - Secret detection in CI

## Key Dependencies

- **Azure SDK Suite** (3.x+):
- **Authentication & Security**:
- **Data & Analytics**:
- **Document Processing**:
- **HTTP & Networking**:
- **Schema & Validation**:

## Configuration

- `.env` file (gitignored, example: `.env.example`)
- Key configuration groups:
- `setup.cfg` - Pytest, mypy, flake8 configuration
- `azure_functions/host.json` - Azure Functions extension bundles and logging (Application Insights sampling enabled)
- `infra/main.bicep` - Infrastructure-as-Code for Azure resources
- `infra/staging.parameters.json` - Bicep parameter overrides for staging environment

## Platform Requirements

- Python 3.12+
- pip
- PowerShell 7+ (for deployment/ops scripts)
- Azure CLI (for local Azure interaction)
- Azure Functions Core Tools (for local Function app execution)
- git (version control)
- GitHub account (CI/CD)
- Microsoft Azure subscription
- Microsoft 365 tenant with:

## Observability

- Python built-in `logging` module
- Application Insights integration via `APPINSIGHTS_INSTRUMENTATIONKEY` env var
- Custom safe logger (`scripts/safe_logger.py`) for redacting PII/secrets from logs
- Application Insights (Azure native): enabled in `azure_functions/host.json`
- Custom usage tracking module (`scripts/usage_tracker.py`) — logs to optional JSON sink
- Structured logging with UTC timestamps and log level (setup.cfg: log_format = "%(asctime)s [%(levelname)s] %(message)s")

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Module names: lowercase with underscores, matching function/class names they contain (`api_server.py`, `safe_logger.py`, `auth.py`)
- Test files: `test_<module>.py` (e.g., `test_auth_jwt.py`, `test_safe_logger_redaction.py`)
- Configuration: `conftest.py` for pytest fixtures and setup at each directory level
- Use snake_case for all function names: `verify_azure_ad_token()`, `normalize_amount()`, `extract_canonical_fields()`
- Private/internal functions: prefix with underscore: `_truthy()`, `_norm_key()`, `_fetch_jwks()`, `_jwks_cache_valid()`
- Async functions use same convention: `async def trigger_audit()`, `async def test_rate_limit_enforced_per_user()`
- Module-level constants: UPPERCASE with underscores: `JWKS_TTL_SECONDS`, `_RATE_LIMIT_MAX`, `FEATURE_ENV`, `_MASK_SECRET`
- Regular variables: snake_case: `tenant_id`, `job_id`, `user_upn`, `document_id`
- Temporary/loop variables: lowercase: `f`, `m`, `c` (when iterating, reuse patterns from codebase)
- Private module state: underscore prefix: `_JWKS_CACHE`, `_JWKS_CACHE_TS`, `_rate_limit_store`
- Type hints use snake_case for generics and proper capitalization for classes: `Dict[str, List[str]]`, `Optional[str]`, `BaseModel`, `HTTPException`
- Dataclass names: PascalCase: `AppConfig`, `AuditRequest`, `DocumentResolveRequest`

## Code Style

- Line length: maximum 120 characters (configured in `setup.cfg` `[flake8]`)
- Indentation: 4 spaces
- Use `from __future__ import annotations` for forward-compatible type hints (present in 9 core modules)
- Tool: flake8 (configured in `setup.cfg`)
- Ignored rules: E203, W503, W504, E402, E741
- Excludes: `__pycache__`, `.git`, `.venv`, jobs, `.pytest_cache`, `.mypy_cache`, `.planning`, `.claude`
- Tool: mypy (configured in `setup.cfg`)
- Strict typing enforced on core modules only: `scripts/fabric_audit_engine.py`, `scripts/feature_flags.py`, `scripts/usage_tracker.py`, `scripts/cost_tracker.py`, `scripts/admin_controls.py`, `scripts/graph_obo.py`, `azure_functions/shared/audit_pipeline.py`, `azure_functions/shared/sharepoint.py`
- Other modules: ignore missing imports (`ignore_missing_imports = true`)
- Python version: 3.12

## Import Organization

- No path aliases configured; imports use relative paths from `scripts/` directory
- Tests add `scripts/` to PYTHONPATH explicitly in conftest.py files to enable absolute imports: `sys.path.insert(0, ...)`
- Fabric SDK integration uses conditional imports to avoid blocking non-Fabric environments

## Error Handling

- FastAPI endpoints raise `HTTPException(status_code=..., detail=...)` for HTTP errors (400, 401, 403, 429, 503)
- Custom exceptions: `ConfigurationError` extends `RuntimeError` (in `scripts/config.py`)
- Validation errors: raise `ValueError` with descriptive message (e.g., in sharepoint module for file extension/size)
- Auth failures: raise `HTTPException(401)` with security-appropriate detail message
- Rate limiting violations: raise `HTTPException(429)` with user-friendly message
- JSON parsing errors: handled gracefully with fallback to next parsing attempt (e.g., in `_assert_durable_owner()`)
- Try-except used minimally; prefer explicit validation before operations
- All error details logged via `safe_logger.log_security()` to redact secrets/PII before persistence
- Secrets (JWT, API keys, IBAN, emails) masked with placeholders like `[SECRET_MASQUÉ]`, `[EMAIL_MASQUÉ]`, `[PII_MASQUÉE]`
- No control characters (CR/LF) in persisted error details (prevents log injection)

## Logging

- Module-level logger creation: `logger = logging.getLogger("AC360")` with level `logging.INFO`
- Log redaction MANDATORY: all user-facing or externally observable output routed through `safe_logger.redact()`
- Security events: use `safe_logger.log_security(level, message, data=None)` function
- No plaintext secrets logged anywhere (checked by `tests/security/test_no_plaintext_secrets.py`)
- AppInsights integration: when `APPINSIGHTS_INSTRUMENTATIONKEY` set, telemetry logged via `log_security("INFO", "AppInsights_Telemetry", {...})`

## Comments

- **Docstrings (triple quotes):** Always present on:
- **Inline comments:** Sparingly, for non-obvious logic
- **Comment style:** Use English in code comments; French allowed in docstrings for French-centric domain (e.g., "conforme à la Baseline Sécurité")
- Not used; this is Python, uses docstrings instead
- Parameter docs in docstring (numpy/Google style):

## Function Design

- Type hints required on all function parameters and return types (enforced by mypy on core modules)
- Use `Optional[Type]` for nullable values, avoid `None` as default for production code
- Keyword-only arguments for named parameters: `def build_usage_event(event_type: str, *, status: str = "ok", ...)`
- No `*args` or `**kwargs` in public APIs; explicit parameters or dataclass models preferred
- Always include return type hint
- Consistent return types: don't return `None` mixed with values in same function without clear intent
- On failure, raise exception rather than returning `None` (except for truly optional lookups)

## Module Design

- Use `__all__` to declare public API: `__all__ = ["redact", "MAX_LEN", "logger", "log_security"]`
- Private module state prefixed with underscore: `_JWKS_CACHE`, `_JWKS_CACHE_TS`, `_ANSI_RE`
- Not used; imports source modules directly
- Each module has single clear responsibility (e.g., `safe_logger.py` = redaction, `auth.py` = JWT verification, `feature_flags.py` = feature toggling)
- Initialization logic in `load_*()` functions called at import or startup, never on module import
- Configuration loaded via `config.load_config(require_auth=True)` at app startup (fail-fast pattern)

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```

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

- **Read-only enforcement:** No modification of SharePoint data; all responses are citations from existing documents
- **User-scoped permissions:** Audit trails keyed to user identity (UPN hash); SharePoint access validated per-user
- **Injection-safe input:** Path traversal guards, allowlist filtering, shell-safe regex patterns
- **Fail-fast architecture:** Configuration errors on startup; missing auth variables prevent app launch
- **Testable by design:** Pure functions with dependency injection (no direct cloud SDK calls in core logic)

## Layers

- Purpose: User-facing conversational interface; RAG query orchestration
- Location: `src/copilot/AC360/`
- Contains: 25+ topics (YAML), connection references, agent instructions, knowledge sources
- Depends on: SharePoint Read-Only connector, FastAPI backend for audit/drafting endpoints
- Used by: End users via Teams or Copilot Web
- Purpose: HTTP entry point; authentication, rate limiting, feature gates, document resolution
- Location: `scripts/api_server.py` (646 lines), utility modules in `scripts/`
- Contains: REST endpoints (`/api/audit`, `/api/status`, `/api/document/resolve`), middleware for security headers, token validation
- Depends on: Azure Entra ID (JWKS), Azure Durable Functions, feature flag store, safe logging
- Used by: Copilot Studio actions and external API consumers
- Purpose: Async workflow engine for document audit pipelines with retry/durability semantics
- Location: `azure_functions/function_app.py` (240+ lines)
- Contains: Activity definitions (download, OCR, Fabric query, FIC generation), orchestration state machine
- Depends on: Azure Blob Storage (for Durable state), Graph API, Document Intelligence, Fabric SQL
- Used by: FastAPI backend (async job triggering)
- Purpose: Pure, testable logic for audit, comparison, and document processing
- Location: `scripts/` directory (15+ Python modules)
- Contains: Audit engine, OCR post-processing, Fabric query builder, FIC generation, admin controls
- Depends on: Pandas, thefuzz (fuzzy name matching), pydantic for validation
- Used by: Durable Functions activities, test suite, CLI utilities
- Purpose: 30+ test files covering security, logic, and integration
- Location: `tests/backend/`, `tests/azure_functions/`, `tests/admin/`
- Contains: Unit tests, mocks for cloud services, integration tests with schema validation
- Depends on: pytest, pytest-asyncio, unittest.mock
- Coverage: Auth (JWT, OBO), rate limiting, path traversal, IDOR, job isolation, OCR timeout

## Data Flow

### Primary Request Path: Document Audit

### Secondary Flow: RAG Search

### Tertiary Flow: Document Resolution

- **In-Memory (FastAPI):** User rate limit tracking, audit job ownership (fast-path IDOR)
- **Azure Storage (Durable):** Orchestration state, job history, outputs
- **Azure Key Vault:** Secrets (OCR key, Fabric credentials), rotated via secret rotation runbook
- **File System (JOBS_BASE_DIR):** Downloaded documents, OCR results, generated FIC drafts (ephemeral)

## Key Abstractions

- Purpose: Decouple audit orchestration from cloud I/O; enables testing without real Azure services
- Examples: `azure_functions/shared/audit_pipeline.py:78`
- Pattern: Dataclass with `download()`, `ocr()`, `fetch_reference()`, `make_fic()`, `compare()` callables
- Usage: `run_audit(document_id, client_context, deps=AuditDeps(...))`
- Purpose: Centralized, frozen configuration; fail-fast on missing required vars
- Examples: `scripts/config.py:27`
- Pattern: Frozen dataclass with computed properties (JWKS URL, issuer)
- Usage: Imported early in app startup; prevents misconfiguration from reaching endpoints
- Purpose: JSON schema validation for audit outputs; ensures consistent structure
- Examples: `schemas/audit_result.schema.json`
- Pattern: JSONSchema with required fields (verdict, client_document, fields, score)
- Usage: Validated in `azure_functions/shared/audit_pipeline.py` during orchestration
- Purpose: Per-user, per-team, per-feature admin controls without database
- Examples: `scripts/feature_flags.py`
- Pattern: Hash-based lookup with configurable block reasons
- Usage: `is_allowed("audit", user_id_hash=hash_id(upn))` in FastAPI handler

## Entry Points

- Location: `scripts/api_server.py`
- Triggers: HTTP requests (POST /api/audit, GET /api/status, POST /api/document/resolve, etc.)
- Responsibilities:
- Location: `src/copilot/AC360/agent.mcs.yml`
- Triggers: User messages in Teams channel or Copilot Web
- Responsibilities:
- Location: `azure_functions/function_app.py` (orchestration entry point)
- Triggers: HTTP POST from FastAPI (function URL + code key)
- Responsibilities:
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

### Credential Leakage in Logs (Addressed)

### Unbounded Memory Growth (Addressed)

### Timing Attacks on Feature Flags (Partial Mitigation)

### Path Traversal via Document ID (Addressed)

### IDOR: Access to Others' Audit Jobs (Addressed)

### Shell Injection in Generated Reports (Addressed)

## Error Handling

- **Config Phase (Startup):** Missing TENANT_ID/CLIENT_ID → process exits immediately. Caught by supervision layer (systemd/Container).
- **Request Phase (Endpoint):** Invalid JWT → HTTP 401 + safe error message (no token details leaked). Missing header → 400. Rate limited → 429.
- **Activity Phase (Durable):** Network error in Graph API → automatic retry (configurable, default 3 attempts). Exhausted retries → audit marked "Failed" with error detail.
- **Validation Phase:** JSON schema mismatch → logged but processed (graceful degrade, not reject).
- **Logging:** All errors logged via `safe_logger.log_security()` with sanitized message (secrets redacted).

## Cross-Cutting Concerns

- Framework: Python `logging` module + `safe_logger` wrapper
- Approach: Structured logging (key-value pairs) to Application Insights
- Redaction: `safe_logger.redact()` removes patterns (API_KEY=..., PASSWORD=..., etc.)
- PII: User identity logged as hash (SHA256) not cleartext UPN
- Input: HTTPException on malformed requests (document_id format, query length)
- Output: JSONSchema validation of audit results (schemas/*.json)
- Configuration: Pydantic model (AppConfig) with frozen dataclass
- Provider: Microsoft Entra ID (OAuth 2.0)
- Token Format: JWT RS256
- Verification:
- Audience: Copilot Studio action client ID (from config)
- Scopes: Configurable (default: "Audit.Trigger")
- Roles: Optional (configurable via REQUIRED_ROLES)
- User-scoped: Audit results tied to user identity (UPN hash)
- SharePoint-scoped: Graph API access token respects user's SharePoint permissions (user-delegated OBO flow)
- Feature-scoped: Admin can block audit/rag/email_draft per user, team, or globally (feature_flags.py)

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
