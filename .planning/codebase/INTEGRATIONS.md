# External Integrations

**Analysis Date:** 2026-06-11

## APIs & External Services

**Microsoft Entra ID (Authentication):**
- Service: Microsoft Entra ID (OAuth2 / OpenID Connect)
- What it's used for: User authentication, token validation, On-Behalf-Of (OBO) flow for delegated SharePoint access
  - SDK/Client: PyJWT (manual token validation) + Azure SDK
  - Auth: Service Principal (Client ID / Client Secret for OBO flow)
  - Implementation: `scripts/auth.py` validates incoming JWT tokens via JWKS endpoint
  - JWKS Endpoint: Configured dynamically at `https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys`
  - Env vars: `TENANT_ID`, `CLIENT_ID`, `OBO_CLIENT_ID`, `OBO_CLIENT_SECRET`, `JWKS_TIMEOUT`, `JWKS_TTL_SECONDS`

**Microsoft Graph API:**
- Service: Microsoft Graph REST API
- What it's used for: Document downloads from SharePoint (via item ID), user profile data, delegated permissions
  - SDK/Client: `httpx` (async HTTP client in `scripts/api_server.py` and `azure_functions/shared/sharepoint.py`)
  - Auth: Bearer token (user's delegated token for OBO flow, or Managed Identity token)
  - Endpoints: `https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content`
  - Env vars: `SHAREPOINT_DRIVE_ID` (Graph drive ID containing client folders)
  - Implementation: `azure_functions/shared/sharepoint.py` handles downloads with error propagation (403/404 indicate RBAC denial)

**Microsoft Copilot Studio (Frontend):**
- Service: Copilot Studio (proprietary Power Platform service)
- What it's used for: NLP intent recognition, RAG orchestration, topic routing, conversation management
  - Integration: Declarative YAML configuration (`.mcs.yml` files in `src/copilot/AC360/`)
  - Connection References: Three MCP connectors defined in `src/copilot/AC360/connectionreferences.mcs.yml`:
    - `shared_a365copilotchatmcp` - Copilot Chat MCP (conversation context)
    - `shared_a365memcp` - Microsoft 365 MCP (enterprise connectors)
    - `shared_workiqsharepoint` - WorkIQ SharePoint MCP (SharePoint Query and RAG)
  - Topics: Defined in `src/copilot/AC360/topics/*.mcs.yml` (e.g., ConversationStart, Brouillonmailcommercial, CreerRelancePlanner)
  - Knowledge: RAG nodes point to SharePoint library `Dossiers_Clients_POC_SL6AtdmRQelfg9pN9oVIp` (folder-based document indexing)
  - Settings: System prompt + guardrails in `agent.mcs.yml` (read-only, anti-injection, sourcing rules)
  - Admin Actions: Custom connectors trigger API endpoints (validate_copilot.yaml validates topic correctness)

**Microsoft Teams (Notifications):**
- Service: Teams Incoming Webhooks
- What it's used for: Async notification of audit completion, workflow alerts
  - Endpoint: Webhook URL from Teams channel connector
  - Env var: `TEAMS_WEBHOOK_URL` (stored in Azure Key Vault, not checked into repo)
  - Implementation: Optional post-audit notification (Phase 5)

**Microsoft Planner (Task Management):**
- Service: Microsoft Graph Planner API
- What it's used for: Create follow-up tasks from audit context (commercial follow-up)
  - SDK/Client: HTTP via `httpx` using Entra ID bearer token
  - Auth: Managed Identity or delegated user token
  - Implementation: `scripts/planner_integration.py` — POST `/planner/buckets/{bucket_id}/tasks`
  - Env vars: `PLANNER_DEFAULT_PLAN_ID`, `PLANNER_DEFAULT_BUCKET_ID`, `PLANNER_API_ENDPOINT`

## Data Storage

**Databases:**

**Microsoft Fabric (Primary):**
- Provider: Microsoft Fabric (Analytics platform)
- Type: Delta Lake format (parquet-backed columnar tables)
- What it's used for: Reference data (client master records, SIRET/CompanyName mappings)
  - Connection: OneLake (ADLS Gen2 compatible, native Python SDK — `deltalake` + `pyarrow`)
  - Client: `deltalake.DeltaTable` + `pyarrow.parquet` (zero ODBC dependency)
  - Env vars: `FABRIC_WORKSPACE_ID`, `FABRIC_GOLD_LAKEHOUSE_ID`, `FABRIC_CLIENT_TABLE` (defaults to `tbl_super_product_client_api_gold`), `FABRIC_CACHE_TTL_SECONDS`
  - Implementation: `scripts/fabric_onelake.py` handles connection via Managed Identity, in-memory indexing by SIRET (O(1) lookups), fuzzy name matching as fallback
  - Table schema: Readable client names + SIRET (gold table); pseudonymized RGPD table available separately (`tbl_full_client_gold`)

**Azure SQL Database (Legacy):**
- Provider: Microsoft SQL Server
- Type: Relational database (SQL endpoint from Fabric)
- What it's used for: Fallback reference data access (being deprecated in favor of OneLake)
  - Connection: ODBC via `pyodbc`
  - Env vars: `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE`
  - Status: Legacy; OneLake (delta tables) is the preferred path going forward

**Local Storage:**
- Type: Azure Storage Account (File Shares / Blob Storage)
- What it's used for: Temporary audit job artifacts (downloaded PDFs, OCR results, FIC drafts)
  - Path: `JOBS_BASE_DIR` env var (defaults to `jobs/` directory, per-document-id subdirectories)
  - Persistence: Transient; cleaned up by `scripts/cleanup_local_artifacts.ps1` after processing

**File Storage (SharePoint Online):**
- Provider: Microsoft SharePoint Online
- Type: Document library (`Dossiers_Clients_POC`)
- What it's used for: Source document repository (client files: contracts, proposals, notices)
  - Access: Via Microsoft Graph (drives API)
  - Env var: `SHAREPOINT_DRIVE_ID` (Graph drive ID)
  - RBAC: User's permissions are honored via delegated token (OBO flow)

## Caching

**In-Process Cache:**
- Fabric client reference table: Cached in memory with TTL (`FABRIC_CACHE_TTL_SECONDS`, default 3600s)
  - Implementation: `scripts/fabric_onelake.py` uses thread-safe dict (`_cache`) with timestamp-based expiry
  - Indexed by SIRET (exact match) and fuzzy name matching
  - Reloaded from OneLake after TTL expiry

**JWKS Token Cache:**
- Azure Entra ID public keys: Cached with configurable TTL (`JWKS_TTL_SECONDS`, default 3600s)
  - Implementation: `scripts/auth.py` fetches and caches JWKS for token signature validation
  - Prevents repeated calls to Entra ID JWKS endpoint

## Authentication & Identity

**Auth Provider:** Microsoft Entra ID (OAuth2 / OpenID Connect)

**Implementation Approaches:**

1. **User Authentication (Primary)**:
   - Inbound: Bearer token from Copilot Studio / Teams client
   - Validation: JWT signature verification via JWKS (RS256 algorithm)
   - Scope/Role enforcement: Checks `REQUIRED_SCOPES` and `REQUIRED_ROLES` in token claims
   - Implementation: `scripts/auth.py` — `verify_azure_ad_token()` dependency for FastAPI endpoints
   - Logs security events via `scripts/safe_logger.py` (no PII in logs)

2. **Service-to-Service (On-Behalf-Of)**:
   - Flow: Exchange user's Entra ID token for Graph API token
   - Purpose: Delegate SharePoint access — audit sees only documents user can access
   - Implementation: `scripts/graph_obo.py` — `acquire_obo_graph_token()`
   - Env vars: `OBO_CLIENT_ID`, `OBO_CLIENT_SECRET`, `AC360_REQUIRE_OBO`
   - Feature flag: `AC360_REQUIRE_OBO=true` enforces OBO; `false` allows fallback to Managed Identity (app-level permissions, no RBAC)

3. **Application Identity (Managed Identity)**:
   - For Azure resources: Service Principal via Managed Identity
   - Scope: Document Intelligence, Fabric, Key Vault, Storage
   - Implementation: Azure SDK `DefaultAzureCredential()` (tries MI first, falls back to local dev auth)
   - No credentials stored in code; Azure handles identity lifecycle

## Monitoring & Observability

**Error Tracking:**
- Service: None (logging to Application Insights optional)
- Custom: `scripts/safe_logger.py` — redaction of PII/secrets in exception messages before logging
- Logs: Sent to Application Insights if `APPINSIGHTS_INSTRUMENTATIONKEY` is configured

**Logs:**
- Framework: Python built-in `logging` module
- Sinks:
  - **Console** (local dev): Logged via pytest CLI if test runs
  - **Application Insights** (production): If `APPINSIGHTS_INSTRUMENTATIONKEY` is set in Azure Key Vault
  - **Custom JSON sink** (optional): `AC360_USAGE_SINK` env var specifies path to append usage events
- Format: `%(asctime)s [%(levelname)s] %(message)s` with ISO 8601 timestamps
- Redaction: Automatic masking of PII, secrets, tokens via `redact()` function in `safe_logger.py`

**Usage Tracking:**
- Implementation: `scripts/usage_tracker.py` — tracks API calls, feature flag evaluations, cost events
- Sink: JSON Lines format to file or Application Insights
- Env vars: `AC360_ENVIRONMENT`, `AC360_BOT_VERSION`, `AC360_USAGE_SINK`

**Cost Tracking:**
- Implementation: `scripts/cost_tracker.py` — tracks OCR document count, Fabric queries, API calls
- Rate card: JSON-formatted `AC360_RATE_CARD` (empty by default; no costs charged until configured)
- Budget: `AC360_BUDGET_EUR` + warning threshold `AC360_BUDGET_WARN_PCT` (default 80%)

## CI/CD & Deployment

**Hosting:**
- Platform: Microsoft Azure (multi-tier)
  - **API Gateway**: Azure App Service (Linux, Python 3.12) or Azure Container Instances
  - **Orchestration Engine**: Azure Functions (Consumption/Premium Plan) with Durable Functions
  - **State Store**: Azure Storage Account (Durable task hub)
  - **Secrets**: Azure Key Vault (RBAC-secured)
  - **Compute**: Managed identities for service-to-service auth

**CI Pipeline:**
- Service: GitHub Actions (`.github/workflows/ci.yml`)
- Stages:
  1. **Security Scan** (blocking): Gitleaks secret detection + Python linting
  2. **Unit Tests**: pytest with coverage reporting
  3. **Copilot YAML Validation**: `scripts/validate_copilot_yaml.py` checks Copilot Studio topic structure
  4. **Integration Tests** (if available): Marked by `@pytest.mark.integration`
- Artifact: Python package (wheel) published to artifact feed
- Trigger: Push to main/develop, pull requests to main
- Concurrency: Cancels stale runs on same branch

**CD Pipeline:**
- Service: GitHub Actions (`.github/workflows/cd-staging.yml`)
- Deployment: Bicep IaC to Azure resource group
- Environment: Staging (dev->test->prod strategy managed by ENVIRONMENT_STRATEGY.md)
- Secrets: Injected from GitHub via Azure Key Vault lookup
- Pre-deployment validation: `what-if` analysis recommended before applying Bicep changes (see `infra/main.bicep`)

**IaC:**
- Tool: Bicep (Azure DSL)
- File: `infra/main.bicep` — Declares all production Azure resources (hardened posture)
- Parameters: `infra/staging.parameters.json` — Environment-specific overrides (IP restrictions, network access, auth settings)
- Hardening: httpsOnly=true, TLS 1.2 minimum, no blob public access, Key Vault RBAC, purge protection enabled

## Governance & Feature Flags

**Kill-Switch System (P0-09):**
- Env vars: `AC360_GLOBAL_ENABLED`, `AC360_OCR_ENABLED`, `AC360_RAG_ENABLED`, `AC360_EMAIL_DRAFT_ENABLED`, `AC360_AUDIT_ENABLED`
- Blacklist enforcement: `AC360_BLOCKED_USERS_HASHED` (SHA-256 hashed UPNs), `AC360_BLOCKED_TEAMS`
- Admin role enforcement: `AC360_ADMIN_ROLE` (Entra ID role required for control actions)
- Implementation: `scripts/feature_flags.py` — `is_allowed()` checks before audit execution

**Security Gates:**
- DLP Policy (Power Platform): Configured to block unauthorized connectors
- Entra ID Conditional Access: Can restrict app access by location/device (controlled by IT)
- RBAC: SharePoint permissions enforced via OBO token delegation
- Anti-injection: Copilot System Prompt (`agent.mcs.yml`) forbids prompt override, data exfiltration, multi-client aggregation

## Environment Configuration

**Required env vars (on startup):**
- `TENANT_ID`, `CLIENT_ID` — Mandatory for API gateway
- `AZURE_FUNCTION_URL`, `TASK_HUB_NAME` — Mandatory for Durable orchestration
- `SHAREPOINT_DRIVE_ID` — Mandatory for document downloads

**Optional but recommended (production):**
- `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY` — Enable document intelligence pipeline
- `FABRIC_WORKSPACE_ID`, `FABRIC_GOLD_LAKEHOUSE_ID` — Enable client reference lookups
- `TEAMS_WEBHOOK_URL` — Enable audit completion notifications
- `APPINSIGHTS_INSTRUMENTATIONKEY` — Enable cloud observability
- All of above in Azure Key Vault (never in code or `.env`)

**Secrets location:**
- **Local dev**: `.env` file (gitignored, example: `.env.example`)
- **Production**: Azure Key Vault — secrets rotated per `docs/security/SECRET_ROTATION.md`
- **CI/CD**: GitHub encrypted secrets (passed to Azure Key Vault lookup in deployment scripts)

## Webhooks & Callbacks

**Incoming:**
- Copilot Studio → FastAPI Gateway: POST `/api/audit` — User query for document analysis
- Durable Functions Management: Webhook from Task Hub for status polling (internal)
- Planner Task Creation: API call (not webhook-based)

**Outgoing:**
- FastAPI → Azure Durable Functions: HTTP POST to `AZURE_FUNCTION_URL` to trigger orchestrations
- Azure Functions → SharePoint: Graph API downloads (via HTTPS)
- Azure Functions → Fabric: OneLake access (HTTPS/ADLS Gen2)
- Azure Functions → Teams: Webhook POST to `TEAMS_WEBHOOK_URL` (audit completion notification)
- Azure Functions → Planner: Graph API POST to create tasks

---

*Integration audit: 2026-06-11*
