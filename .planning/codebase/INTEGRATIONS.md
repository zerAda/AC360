# External Integrations

**Analysis Date:** 2026-06-08

## APIs & External Services

**OCR / Document Intelligence:**
- Azure AI Document Intelligence (Cognitive Services FormRecognizer) - extracts key-value pairs and tables from client documents.
  - SDK/Client: `azure-ai-formrecognizer` (`DocumentAnalysisClient`, `prebuilt-document` model) in `scripts/process_document_ocr.py`
  - Auth: `AzureKeyCredential` from env vars `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY`
  - Provisioned by `scripts/deploy_azure_ocr.ps1` (kind FormRecognizer, SKU S0, westeurope)

**Microsoft Graph (Planner):**
- Microsoft Graph v1.0 (`https://graph.microsoft.com/v1.0`) - creates Planner tasks and reads user plans for follow-up/relance workflows.
  - SDK/Client: raw `httpx` calls in `scripts/planner_integration.py` (`create_planner_task`, `get_user_plans`)
  - Auth: delegated bearer token (`Tasks.ReadWrite`), passed through from the caller's Entra token

**Azure Durable Functions backend:**
- Internal Azure Functions app fronted by FastAPI gateway.
  - Client: `httpx.AsyncClient` in `scripts/api_server.py`
  - Auth: `AZURE_FUNCTION_KEY`; base URL `AZURE_FUNCTION_URL` (default `http://localhost:7071/api`)

**Copilot Studio (Power Platform connectors):**
- Connector references in `src/copilot-workspace/AC360/connectionreferences.mcs.yml`:
  - `shared_a365copilotchatmcp` (Microsoft 365 Copilot Chat MCP)
  - `shared_a365memcp` (M365 Enterprise MCP)
  - `shared_workiqsharepoint` (WorkIQ SharePoint, used by actions in `src/copilot-workspace/AC360/actions/`)

## Data Storage

**Databases:**
- Microsoft Fabric SQL endpoint (Artus management data, e.g. `Artus_Contrats` table)
  - Connection: `pyodbc` with `ODBC Driver 17 for SQL Server`, `FABRIC_SQL_ENDPOINT:1433`, `Encrypt=yes` (`scripts/audit_fabric_comparison.py`)
  - Auth: Entra ID via `DefaultAzureCredential`, access token injected into ODBC attr `1256` (SQL_COPT_SS_ACCESS_TOKEN), scope `https://database.windows.net/.default`
  - Env: `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE`
  - Fallback: simulated management data when env vars are absent or connection fails
- Redis >=5.0.0 - Celery broker/result backend (declared in `requirements.txt`)

**File Storage:**
- SharePoint Online (`https://gerep.sharepoint.com/sites/AC360`) - client document library, the agent's only knowledge source.
  - Access: PnP PowerShell (`Connect-PnPOnline`, `Get-PnPFolderItem`) in `scripts/sharepoint_auto_classifier.ps1` and sibling SharePoint scripts
  - Azure Functions local dev uses Azure Storage emulator (`AzureWebJobsStorage: UseDevelopmentStorage=true`)

**Caching:**
- In-process JWKS cache (`_JWKS_CACHE` in `scripts/auth.py`)
- In-process rate-limit store (`_rate_limit_store` in `scripts/api_server.py`, 10 req / 3600 s)

## Authentication & Identity

**Auth Provider:**
- Microsoft Entra ID (Azure AD)
  - API: JWT RS256 validation against Entra JWKS (`scripts/auth.py`, `verify_azure_ad_token`), checks `kid`, audience, issuer, scopes, roles via `config.py` (`JWKS_URL`, `CLIENT_ID`, `API_AUDIENCE`, `ALLOWED_ISSUERS`, `REQUIRED_SCOPES`, `REQUIRED_ROLES`)
  - Fabric: `DefaultAzureCredential` token-based ODBC auth
  - SharePoint: App-Only mode via `ENTRA_CLIENT_ID` / `ENTRA_CLIENT_SECRET` (interactive mode explicitly disallowed in production scripts)
  - Copilot Studio: respects connected-user SharePoint permissions (read-only, no web browsing, `gptCapabilities.webBrowsing: false`)

## Monitoring & Observability

**Error Tracking / Telemetry:**
- Azure Application Insights - enabled in `azure_functions/host.json` (sampling, live metrics) and via `AppInsightsMiddleware` in `scripts/api_server.py` gated on `APPINSIGHTS_INSTRUMENTATIONKEY`. Setup documented in `docs/observability/APPINSIGHTS_SETUP.md`.

**Logs:**
- Custom `scripts/safe_logger.py` (`logger`, `log_security`) for structured/secure logging
- pytest log config in `setup.cfg` (`log_cli = true`, INFO level)

## CI/CD & Deployment

**Hosting:**
- Copilot Studio environment `https://org2cf282f3.crm4.dynamics.com` (bot `c82f127c-8f47-f111-bec6-000d3ab9a512`)
- Azure (Functions, Document Intelligence, Fabric) in `westeurope`

**CI Pipeline:**
- GitHub Actions `.github/workflows/ci.yml` (AC360 CI): security-scan (Gitleaks 8.18.2 + security tests, blocking) → validate-yaml (Copilot topics) → test (pytest, JUnit XML artifact) → lint (flake8, non-blocking) → package-dry-run (PowerShell) → notify-success
- GitHub Actions `.github/workflows/cd-staging.yml` (AC360 CD — Staging): manual `workflow_dispatch`, runs `scripts/package_release.ps1`, uploads release artifact, emits post-deploy checklist
- Copilot sync via Power Platform CLI (`pac`) in `scripts/sync_copilot.ps1` (Pull/Push between cloud and `src/copilot`)

## Environment Configuration

**Required env vars:**
- `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY` (Document Intelligence)
- `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE` (Fabric SQL)
- `AZURE_FUNCTION_URL`, `AZURE_FUNCTION_KEY` (Durable Functions backend)
- `APPINSIGHTS_INSTRUMENTATIONKEY` (telemetry)
- `TEAMS_WEBHOOK_URL` (Teams alerts)
- `TENANT_ID`, `CLIENT_ID` (Entra ID / JWT)
- `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET` (SharePoint App-Only)

**Secrets location:**
- `.env` (runtime, git-ignored) and `.env.generated` (produced by `deploy_azure_ocr.ps1`, git-ignored)
- GitHub Actions secrets: `TENANT_ID`, `CLIENT_ID`
- CI masks secrets via Gitleaks and `::add-mask::` / `##vso[task.setsecret]`

## Webhooks & Callbacks

**Incoming:**
- FastAPI endpoints in `scripts/api_server.py` (e.g. `/run-audit`, `/health` per CD checklist) invoked by Copilot Studio / clients

**Outgoing:**
- Microsoft Teams Incoming Webhook (`TEAMS_WEBHOOK_URL`) - posts MessageCard audit-discrepancy alerts (`scripts/post_audit_workflow.py`)
- Microsoft Graph Planner task creation (`scripts/planner_integration.py`)

---

*Integration audit: 2026-06-08*
