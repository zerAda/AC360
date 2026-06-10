# Codebase Structure

**Analysis Date:** 2026-06-10

## Directory Layout

```
AC360/
├── src/                              # Core application & Copilot Studio agent
│   ├── main.py                       # Tkinter desktop UI (PDF/Excel audit)
│   ├── core.py                       # Business logic (parsing, matching, normalization)
│   ├── requirements.txt               # Desktop app dependencies (pdfplumber, pandas, etc.)
│   └── copilot/                      # Microsoft Copilot Studio definitions (YAML)
│       └── AC360/                    # Agent "AC360"
│           ├── agent.mcs.yml         # Agent metadata (name, channel, settings)
│           ├── settings.mcs.yml      # Security (moderation, knowledge, auth)
│           ├── connectionreferences.mcs.yml  # Power Automate connection refs
│           ├── topics/               # Conversation topics (30+ .mcs.yml files)
│           │   ├── ConversationStart.mcs.yml
│           │   ├── Rsumdossierclient.mcs.yml
│           │   ├── LancerAudit.mcs.yml
│           │   ├── PreparationRDVRenouvellement.mcs.yml
│           │   └── ...
│           ├── knowledge/            # RAG sources (SharePoint document pointers)
│           │   └── *.mcs.yml         # Knowledge graph definitions
│           ├── actions/              # Power Automate custom actions
│           └── icon.png
├── azure_functions/                  # Backend orchestration (Durable Functions)
│   ├── function_app.py               # Azure Functions runtime + Durable orchestrator
│   ├── host.json                     # Functions app configuration
│   ├── local.settings.json.example    # Template for local dev environment
│   ├── requirements.txt               # Backend dependencies (fastapi, pydantic, etc.)
│   ├── build_package.ps1             # PowerShell script to package for Azure deploy
│   ├── README.md                      # Setup & deployment guide
│   └── shared/                       # Testable, import-safe modules
│       ├── audit_pipeline.py         # Orchestration logic + AuditDeps injection frame
│       └── sharepoint.py             # Graph API download + path confinement
├── scripts/                          # Utility & service modules
│   ├── api_server.py                 # FastAPI gateway (routes, auth, rate-limit)
│   ├── auth.py                       # JWT/JWKS verification + token caching
│   ├── config.py                     # Centralized config (fail-fast validation)
│   ├── fabric_audit_engine.py        # Core audit logic (field aliasing, normalization, comparison)
│   ├── fabric_onelake.py             # Fabric OneLake reference lookup (SIRET/name match)
│   ├── process_document_ocr.py       # Azure Document Intelligence bridge
│   ├── generate_fic_draft.py         # Word document generation (python-docx)
│   ├── generate_fiche_rdv.py         # RDV meeting document template
│   ├── post_audit_workflow.py        # Teams notifications + RGPD cleanup
│   ├── db_manager.py                 # SQLite for audit history (local only)
│   ├── safe_logger.py                # Redacted logging (masks secrets)
│   ├── planner_integration.py        # Microsoft Planner task creation
│   ├── validate_copilot_yaml.py      # YAML schema validation for topics
│   ├── run_demo.py                   # Demo execution script
│   ├── sync_copilot.ps1              # PowerShell: sync agent to Copilot Studio cloud
│   ├── deploy_azure_ocr.ps1          # PowerShell: provision Document Intelligence
│   └── cleanup_local_artifacts.ps1   # PowerShell: purge jobs/ directory
├── tests/                            # Comprehensive test suite
│   ├── conftest.py                   # Pytest fixtures (auth tokens, fake AWS/cloud)
│   ├── backend/                      # API & auth tests
│   │   ├── test_auth_jwt.py          # JWT signature validation
│   │   ├── test_path_traversal.py    # Security: path confinement, document_id validation
│   │   ├── test_download_security.py # SharePoint download safeguards
│   │   ├── test_rate_limit.py        # Rate limiter correctness
│   │   ├── test_job_status.py        # Job polling + artifact management
│   │   └── ...
│   ├── azure_functions/              # Durable Functions tests
│   │   ├── test_function_app.py      # Orchestrator + activity mocking
│   │   ├── test_audit_pipeline.py    # Pure audit logic (no cloud)
│   │   └── test_sharepoint.py        # Download confinement + allowlist
│   ├── fabric/                       # Audit comparison engine
│   │   ├── test_comparison_engine.py # Field matching, verdicts
│   │   ├── test_normalization.py     # Accent removal, date parsing
│   │   ├── test_onelake_matching.py  # SIRET/name lookup
│   │   └── test_schema_validation.py # JSON schema conformance
│   ├── copilot/                      # Copilot Studio topic validation
│   │   ├── test_topics_integrity.py  # YAML structure, missing fields
│   │   ├── test_hardened_rag_topics.py  # RAG security (no general knowledge)
│   │   └── test_topics_silent_and_security.py
│   ├── security/                     # Security hardening checks
│   │   ├── test_no_plaintext_secrets.py  # Grep for hardcoded API keys
│   │   └── test_no_forbidden_files.py    # Ban .env, *.key, etc.
│   ├── red_team/                     # Adversarial testing
│   │   └── test_red_team_automated.py    # Automated attack scenarios
│   └── acceptance/                   # E2E integration tests (requires real cloud)
├── schemas/                          # JSON Schema definitions
│   ├── audit_input.schema.json       # Audit request format (document_id, client_context)
│   ├── audit_result.schema.json      # Audit response (verdict, fields, FIC path)
│   └── ocr_result.schema.json        # Document Intelligence output format
├── docs/                             # Runbooks, architecture, governance
│   ├── architecture/                 # System design, sequence diagrams
│   ├── alm/                          # Deployment runbooks, release checklist
│   ├── security/                     # Defense-in-depth audit, threat model
│   ├── governance/                   # RGPD, data classification, audit trails
│   ├── copilot/                      # Topic design, RAG tuning
│   ├── observability/                # Logging, Application Insights setup
│   └── product/                      # Use cases, user stories
├── prompts/                          # LLM prompts (Copilot Studio topics, summarization)
├── workflows/                        # GitHub Actions CI/CD
│   ├── test.yml                      # pytest on every push
│   ├── security_scan.yml             # bandit, pip-audit, gitleaks
│   └── deploy_staging.yml            # Deploy to staging Azure subscription
├── demo/                             # Demo data & output artifacts
│   ├── out/                          # Generated FIC drafts, test audit reports
│   └── README.md                     # How to run demo
├── .planning/                        # GSD planning outputs
│   ├── codebase/                     # (This directory)
│   │   ├── ARCHITECTURE.md           # Architecture patterns & layers
│   │   ├── STRUCTURE.md              # (This file)
│   │   ├── STACK.md                  # Technology stack
│   │   ├── INTEGRATIONS.md           # External APIs (Graph, Document Intelligence, Fabric)
│   │   ├── CONVENTIONS.md            # Naming, style, import order
│   │   ├── TESTING.md                # Test structure, fixtures
│   │   └── CONCERNS.md               # Tech debt, security gaps, performance issues
│   └── phases/                       # Implementation phases
│       ├── 01-socle-securise/PLAN.md
│       ├── 02-qualite-documentaire/PLAN.md
│       └── ...
├── .env.example                      # Template environment variables
├── conftest.py                       # Root pytest configuration
├── AGENTS.md                         # Agent metadata (from Copilot Studio)
├── AUDIT_FINAL_ENTERPRISE_READINESS.md  # Security & compliance audit results
└── README.md (implied by standard)

```

## Directory Purposes

**src/main.py & src/core.py:**
- Purpose: Standalone desktop audit app (Tkinter UI + PDF/Excel parsing)
- Contains: File selection, threading, normalization, fuzzy matching (thefuzz), export (Excel/CSV/PDF), audit history (SQLite)
- Key files: `src/main.py` (1200 lines, UI + controls), `src/core.py` (partial, shown: Normalizer, PDFParser, ExcelParser, Filters, OptimizedMatcher, EcartCalculator, ResultExporter, AuditHistory)

**src/copilot/AC360/:**
- Purpose: Copilot Studio agent definition (YAML)
- Contains: 30+ topic files, RAG knowledge graph, connection references
- Key files: `agent.mcs.yml` (root agent), `settings.mcs.yml` (security: moderation=High, useModelKnowledge=false), `topics/*.mcs.yml` (conversation flows)

**azure_functions/:**
- Purpose: Backend orchestration (Durable Functions for async job management)
- Contains: Orchestrator, activities (download, OCR, audit, FIC), function triggers, local settings template
- Key files: `function_app.py` (entry point, Durable orchestration), `shared/audit_pipeline.py` (pure logic, deps injected), `shared/sharepoint.py` (Graph API client)

**scripts/:**
- Purpose: Utility modules + service logic
- Contains: FastAPI server, JWT auth, config, audit engine, Fabric integration, OCR bridge, FIC generation, PowerShell helpers
- Key files: `api_server.py` (HTTP gateway), `fabric_audit_engine.py` (core audit logic), `config.py` (centralized config)

**tests/:**
- Purpose: Comprehensive test coverage (unit, integration, security, acceptance)
- Contains: Test suites organized by domain (backend, azure_functions, fabric, copilot, security, red_team)
- Key files: `conftest.py` (fixtures), `backend/test_*.py` (API security), `azure_functions/test_*.py` (orchestration)

**schemas/:**
- Purpose: JSON Schema definitions for request/response validation
- Contains: audit_input, audit_result, ocr_result schemas
- Key files: `audit_result.schema.json` (verdict, fields, FIC path), `audit_input.schema.json` (document_id, client_context)

**docs/:**
- Purpose: Runbooks, architecture, security, governance
- Contains: Subdirectories for ALM (deployment), security (audit results), architecture (diagrams), copilot (topic design)
- Key files: `alm/DEPLOYMENT_RUNBOOK.md`, `security/`, `architecture/`

## Key File Locations

**Entry Points:**
- `scripts/api_server.py`: FastAPI server (POST /api/audit, GET /api/audit/{job_id}/status, etc.)
- `azure_functions/function_app.py`: Azure Durable Functions orchestrator (async pipeline)
- `src/main.py`: Tkinter desktop app (local audit, batch mode)
- `src/copilot/AC360/agent.mcs.yml`: Copilot Studio agent (Teams conversation router)

**Configuration:**
- `.env.example`: Template for TENANT_ID, CLIENT_ID, AZURE_FUNCTION_URL, JOBS_BASE_DIR, etc.
- `scripts/config.py`: Centralized config loading + validation (fail-fast on missing auth vars)
- `azure_functions/host.json`: Function app metadata + triggers
- `azure_functions/local.settings.json.example`: Local dev environment template

**Core Logic:**
- `scripts/fabric_audit_engine.py`: Field aliasing, normalization, matching, verdict logic
- `azure_functions/shared/audit_pipeline.py`: Orchestration + AuditDeps injection (testable without cloud)
- `azure_functions/shared/sharepoint.py`: Graph API download + confinement validation
- `scripts/fabric_onelake.py`: Fabric OneLake reference lookup (SIRET-first, then name match)

**Security & Auth:**
- `scripts/auth.py`: JWT signature verification (RS256 JWKS), token caching (TTLCache)
- `scripts/safe_logger.py`: PII/secret redaction for logs
- `scripts/api_server.py` (lines 98–130): Rate-limiter implementation

**Data Processing:**
- `scripts/process_document_ocr.py`: Azure Document Intelligence bridge (PDF → OCR JSON)
- `scripts/generate_fic_draft.py`: Word document generation (python-docx template)
- `src/core.py`: PDF parsing (pdfplumber), Excel parsing (pandas), normalization, matching (thefuzz)

**Testing:**
- `tests/conftest.py`: pytest fixtures (fake tokens, mock AWS/cloud services)
- `tests/backend/test_auth_jwt.py`: JWT validation tests
- `tests/backend/test_path_traversal.py`: Path confinement + document_id validation
- `tests/fabric/test_comparison_engine.py`: Audit logic + verdict assignment
- `tests/azure_functions/test_audit_pipeline.py`: Orchestration (no cloud)

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `api_server.py`, `fabric_audit_engine.py`)
- YAML (Copilot): `PascalCase.mcs.yml` (e.g., `ConversationStart.mcs.yml`, `Rsumdossierclient.mcs.yml`)
- PowerShell: `verb_noun.ps1` (e.g., `sync_copilot.ps1`, `deploy_azure_ocr.ps1`)
- Test: `test_<module>.py` (e.g., `test_auth_jwt.py`, `test_path_traversal.py`)

**Directories:**
- Domain-based: `scripts/`, `tests/`, `docs/` (not by layer)
- Subdomain grouping: `tests/backend/`, `tests/fabric/`, `tests/copilot/`, `tests/security/`
- Copilot: `src/copilot/<agent_name>/<asset_type>/` (topics, knowledge, actions, settings)

**Functions:**
- Private (internal): `_snake_case()` (e.g., `_validate_document_id()`, `_safe_filename()`)
- Public (exported): `snake_case()` (e.g., `download_document()`, `run_audit()`, `audit()`)
- Async: `async def` with `await` calls (FastAPI routes, not activities)

**Classes:**
- `PascalCase` (e.g., `AuditDeps`, `AuditApp`, `PDFParser`, `ExcelParser`, `Normalizer`, `OptimizedMatcher`)

**Variables:**
- Constants: `UPPER_SNAKE_CASE` (e.g., `AMOUNT_ABS_TOL`, `_DOCID_FORBIDDEN`, `DEFAULT_MAX_BYTES`)
- Module-level state: `_snake_case` prefixed with `_` (e.g., `_rate_limit_store`, `_fuzz`)
- Local: `snake_case` (e.g., `document_id`, `ocr_result`, `verdict`)

## Where to Add New Code

**New Feature (e.g., Add a new audit rule):**
- Primary code: `scripts/fabric_audit_engine.py` (add to _FIELD_ALIASES or audit() function logic)
- Tests: `tests/fabric/test_comparison_engine.py` (add test case for new rule)
- Schema: Update `schemas/audit_result.schema.json` if new verdict type or field
- Integration: Update `azure_functions/shared/audit_pipeline.py` if new dependency injection needed

**New Copilot Topic (e.g., Add a new conversation flow):**
- Implementation: `src/copilot/AC360/topics/TopicName.mcs.yml` (copy template from existing topic)
- Integration: Reference in `src/copilot/AC360/agent.mcs.yml` (list under topics)
- Test: `tests/copilot/test_topics_integrity.py` (add to integrity checks)
- Knowledge: If data-driven, add to `src/copilot/AC360/knowledge/`

**New API Endpoint (e.g., Add POST /api/validate-document):**
- Implementation: Add `@app.post()` route in `scripts/api_server.py`
- Auth: Use `Depends(verify_azure_ad_token)` dependency
- Validation: Call `_validate_sharepoint_doc_id()` or similar
- Tests: Create `tests/backend/test_validate_document.py`

**New Component/Module:**
- Testable core: Place in `scripts/` if stateless (e.g., `new_processor.py`)
- If stateful/cloud: Place in `azure_functions/shared/` if depends on injection frame
- If Tkinter-related: Place in `src/` 
- Import-safety: Wrap cloud SDK imports in try/except if running in multiple contexts

**Utilities:**
- Shared helpers: `scripts/` (e.g., `safe_logger.py`, `config.py`)
- Desktop-only: `src/core.py` (e.g., PDF/Excel parsers)
- Tests fixtures: `tests/conftest.py` (global pytest hooks, shared mocks)

**Documentation:**
- Architecture decisions: `docs/architecture/`
- Deployment procedures: `docs/alm/DEPLOYMENT_RUNBOOK.md`
- Security findings: `docs/security/`
- Product/use cases: `docs/product/`

## Special Directories

**jobs/**
- Purpose: Temporary per-audit working directory
- Generated: Yes (created at runtime for each audit)
- Committed: No (in .gitignore)
- Contents: Downloaded PDF, OCR JSON, FIC Word doc, status logs
- Cleanup: `scripts/cleanup_local_artifacts.ps1` or automatic on 24h TTL (Durable state cleanup)

**.planning/codebase/**
- Purpose: GSD codebase mapping (this directory)
- Generated: Yes (by `/gsd-map-codebase` orchestrator)
- Committed: Yes
- Contents: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**schemas/**
- Purpose: JSON Schema definitions for runtime validation
- Generated: No (hand-written, versioned)
- Committed: Yes
- Contents: audit_input.schema.json, audit_result.schema.json, ocr_result.schema.json

**demo/out/**
- Purpose: Generated demo artifacts (test FICs, audit reports)
- Generated: Yes (by `scripts/run_demo.py`)
- Committed: No (.gitignore)
- Contents: FIC_Brouillon_*.docx, audit_report.xlsx

---

*Structure analysis: 2026-06-10*
