# External Integrations

**Analysis Date:** 2026-06-10

## APIs & External Services

**Microsoft Entra ID:**
- Service: Azure AD / Microsoft Entra ID
- What it's used for: User authentication, token verification via RS256 JWT verification, JWKS key rotation
- SDK/Client: `PyJWT`, `cryptography` (RSA validation)
- Auth: Bearer token in Authorization header; JWKS endpoint: `https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys`
- Config: `TENANT_ID`, `CLIENT_ID`, `JWKS_TIMEOUT`, `JWKS_TTL_SECONDS`
- Implementation: `scripts/auth.py` — Validates JWT signature, checks scopes/roles, caches JWKS with TTL

**Microsoft Graph API:**
- Service: Microsoft Graph v1.0
- What it's used for: Document download from SharePoint, Planner task creation, user plan enumeration
- SDK/Client: `httpx` (async) for direct REST calls
- Auth: Bearer token (user delegated or app-only)
- Base URL: `https://graph.microsoft.com/v1.0`
- Endpoints used:
  - `POST /drives/{drive_id}/items/{item_id}` — Get metadata and download URL
  - `GET /drives/{drive_id}/items/{item_id}/content` — Download document content
  - `POST /planner/tasks` — Create task in Planner (delegated permission `Tasks.ReadWrite`)
  - `GET /me/planner/plans` — List user's plans
- Implementation: `azure_functions/shared/sharepoint.py` (download), `scripts/planner_integration.py` (Planner)

**Microsoft Teams Webhooks:**
- Service: Microsoft Teams Incoming Webhook
- What it's used for: Alert notifications when audit discrepancies are detected
- SDK/Client: `requests` (sync HTTP POST)
- Auth: Webhook URL (pre-authenticated)
- Config: `TEAMS_WEBHOOK_URL` (environment variable)
- Payload: MessageCard JSON format
- Implementation: `scripts/post_audit_workflow.py` — Sends alert with comparison results

## Data Storage

**Databases:**
- **Microsoft Fabric (Gold Lakehouse - OneLake - Primary):**
  - Type: Delta Lake tables (Apache Arrow format)
  - Table: `tbl_super_product_client_api_gold` (client reference data: numcli, client_name, siret, product_name)
  - Connection: OneLake ADLS Gen2 path: `abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}/Tables/dbo/{table_name}`
  - Auth: DefaultAzureCredential (Managed Identity in production, az CLI in local dev)
  - Client: `deltalake` (pure Python, no ODBC) via `pyarrow` for DataFrame conversion
  - Config: `FABRIC_WORKSPACE_ID`, `FABRIC_GOLD_LAKEHOUSE_ID`, `FABRIC_CLIENT_TABLE`, `FABRIC_CACHE_TTL_SECONDS`
  - Implementation: `scripts/fabric_onelake.py` — Loads reference data once per TTL, indexes by SIRET and fuzzy name match

- **Microsoft Fabric (Legacy SQL Endpoint - Not Primary):**
  - Type: SQL warehouse via ODBC
  - Connection string: `FABRIC_SQL_ENDPOINT` (e.g., `*.datawarehouse.fabric.microsoft.com`)
  - Client: `pyodbc`
  - Config: `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE`
  - Status: Deprecated; replaced by OneLake Delta direct access

**File Storage:**
- **SharePoint Online:**
  - Purpose: Source of audit documents (PDF, DOCX, XLSX)
  - Access: Microsoft Graph API with bearer token
  - Config: `SHAREPOINT_DRIVE_ID` (drive ID containing client folders)
  - Implementation: `azure_functions/shared/sharepoint.py`

- **Local Filesystem:**
  - Purpose: Temporary job workspace (document staging, OCR output, FIC draft generation)
  - Location: `{JOBS_BASE_DIR}` (default: `jobs/`)
  - Config: `JOBS_BASE_DIR`, `ALLOWED_EXTENSIONS`

**Caching:**
- In-memory cache (instance-level):
  - Fabric reference table: Loaded once, expires after `FABRIC_CACHE_TTL_SECONDS` (default 3600s)
  - JWKS (Entra ID keys): Cached with TTL, forced refresh on unknown `kid`
- No distributed cache (Redis/Memcached); single instance assumption

## Authentication & Identity

**Auth Provider:**
- Service: Microsoft Entra ID (Azure AD)
- Implementation approach:
  - User login via Copilot Studio → OAuth 2.0 Authorization Code flow (handled by Copilot, not this backend)
  - API endpoints protected by Bearer token JWT verification
  - Token verified: RS256 signature validation, issuer check, audience validation, scope/role claims
  - Entra ID JWKS fetched on-demand with TTL caching

**Authorization:**
- Scope validation: `REQUIRED_SCOPES` (e.g., "Audit.Trigger") extracted from token
- Role validation: `REQUIRED_ROLES` extracted from token (optional)
- Per-request validation in `scripts/auth.py` — `verify_azure_ad_token()` dependency

**Service Accounts:**
- Managed Identity (Azure Functions): No explicit credentials; DefaultAzureCredential chain
- Local development: `az login` → DefaultAzureCredential picks up cached token

## Monitoring & Observability

**Error Tracking:**
- Service: Azure Application Insights (optional)
- Config: `APPINSIGHTS_INSTRUMENTATIONKEY`
- Implementation: Middleware in `scripts/api_server.py` logs request metadata (method, path, status, duration)

**Logs:**
- Approach: Python `logging` module + custom safe logger
- Implementation: `scripts/safe_logger.py` — Redacts secrets (JWT tokens, bearer tokens, webhook URLs, SIRETs) from logs
- Destination: stdout (captured by Azure App Service / Functions runtime)
- Azure Functions: Built-in logging via `logging` module; extension bundle enables Application Insights auto-instrumentation

**Tracing:**
- Durable Functions: Built-in tracing of orchestration, activity calls, and status polling
- Manual logging in `scripts/api_server.py` and activity functions

## CI/CD & Deployment

**Hosting:**
- Platform: Azure (App Service for FastAPI, Azure Functions for Durable orchestration)
- No explicit CI/CD service configured in repo; deployment scripts present but not integrated

**CI Pipeline:**
- Service: None detected (GitHub Actions not configured; pre-commit hooks only)
- Pre-commit hooks: flake8, mypy, gitleaks (local developer checks)

**Deployment:**
- Scripts: `scripts/package_release.ps1`, `scripts/cleanup_local_artifacts.ps1` (PowerShell)
- Runbook: `docs/alm/DEPLOYMENT_RUNBOOK.md`

## Environment Configuration

**Required env vars (Critical):**
- `TENANT_ID` - Entra ID tenant ID for OAuth and JWKS
- `CLIENT_ID` - Application registration ID for token audience validation
- `AZURE_FUNCTION_URL` - URL of Durable Functions instance (e.g., `http://localhost:7071/api`)
- `AZURE_FUNCTION_KEY` - Durable Functions host key (fallback if `AZURE_DURABLE_KEY` not set)
- `AZURE_DURABLE_KEY` - Durable task hub system key (required for webhook polling in production)
- `SHAREPOINT_DRIVE_ID` - Drive ID of SharePoint folder containing client documents
- `FABRIC_WORKSPACE_ID` - Fabric workspace ID
- `FABRIC_GOLD_LAKEHOUSE_ID` - Lakehouse ID containing reference tables
- `AZURE_OCR_ENDPOINT` - Azure Document Intelligence endpoint URL
- `AZURE_OCR_KEY` - Azure Document Intelligence API key

**Optional env vars:**
- `JOBS_BASE_DIR` - Temporary job directory (default: `jobs`)
- `ALLOWED_EXTENSIONS` - CSV of allowed document extensions (default: `.pdf,.docx,.xlsx,.txt`)
- `TEAMS_WEBHOOK_URL` - Teams incoming webhook URL for alerts
- `APPINSIGHTS_INSTRUMENTATIONKEY` - Application Insights instrumentation key
- `JWKS_TIMEOUT` - JWKS fetch timeout in seconds (default: 10)
- `JWKS_TTL_SECONDS` - JWKS cache TTL in seconds (default: 3600)
- `FABRIC_CACHE_TTL_SECONDS` - Fabric reference table cache TTL in seconds (default: 3600)
- `REQUIRED_SCOPES` - CSV of required scopes in token (default: `Audit.Trigger`)
- `REQUIRED_ROLES` - CSV of required roles in token (optional)
- `FABRIC_CLIENT_TABLE` - Fabric reference table name (default: `tbl_super_product_client_api_gold`)
- `TASK_HUB_NAME` - Durable task hub name (default: `AC360Hub`)

**Secrets location:**
- Development: `.env` file (git-ignored)
- Production: Azure Key Vault (accessed via Managed Identity)
- CI/CD: GitHub Actions secrets (not configured)

## Webhooks & Callbacks

**Incoming:**
- **Durable Functions Status Webhooks:** Endpoints at `{AZURE_FUNCTION_HOST}/runtime/webhooks/durabletask/...` (system-managed)
  - Called by `scripts/api_server.py` via `GET` to poll orchestration status
  - URL: `/runtime/webhooks/durabletask/instances/{instanceId}?taskHub={TASK_HUB_NAME}&connection={storageConn}&code={AZURE_DURABLE_KEY}`

**Outgoing:**
- **Microsoft Teams Webhook:** Single POST to `TEAMS_WEBHOOK_URL`
  - Triggered when audit detects discrepancies
  - Payload: MessageCard JSON

**Copilot Studio Actions:**
- AC360 Copilot invokes Python backend via REST API:
  - `POST /api/audit` - Initiate audit pipeline (document_id, client_context)
  - `GET /api/audit/{instance_id}/status` - Poll orchestration status
  - `GET /api/audit/{instance_id}/download-results` - Retrieve FIC draft or audit report

---

*Integration audit: 2026-06-10*
