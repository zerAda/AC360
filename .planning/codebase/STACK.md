# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.12 - Backend logic, OCR pipeline, audit engine, FastAPI gateway. All sources in `scripts/`.
- PowerShell (pwsh) - Orchestration, Azure provisioning, SharePoint automation, Copilot sync, release packaging. All sources in `scripts/*.ps1`.

**Secondary:**
- YAML (Microsoft Copilot Studio `.mcs.yml` dialect) - Conversational agent topics, actions, knowledge, connection references. Located in `src/copilot-workspace/AC360/` and `src/copilot/AC360/`.

## Runtime

**Environment:**
- Python 3.12 (pinned in CI: `.github/workflows/ci.yml` uses `setup-python@v5` with `python-version: "3.12"`)
- Azure Functions Python worker (`azure_functions/local.settings.json`: `FUNCTIONS_WORKER_RUNTIME: python`). Note: only `host.json`/`local.settings.json` are present; the compiled worker modules exist as `azure_functions/__pycache__/*.cpython-312.pyc` (`function_app`, `audit_engine`, `rdv_engine`) but the `.py` sources are not checked in to this tree.
- PowerShell Core on Ubuntu in CI (`apt-get install -y powershell`).

**Package Manager:**
- pip
- Lockfile: missing (no `requirements.lock` / hashes). Dependencies use `>=` floor pins in `requirements.txt`.

## Frameworks

**Core:**
- FastAPI >=0.111.0 - HTTP API gateway in front of Azure Durable Functions (`scripts/api_server.py`, title "AC360 Audit Engine API" v3.0.0).
- Uvicorn[standard] >=0.29.0 - ASGI server for the FastAPI app.
- Starlette middleware (via FastAPI) - Custom `AppInsightsMiddleware` and rate-limiting in `scripts/api_server.py`.
- Celery >=5.3.0 + Redis >=5.0.0 - Async task queue / broker (declared in `requirements.txt`).

**Testing:**
- pytest >=8.0.0 - Test runner. Config in `setup.cfg` (`[tool:pytest]`, `testpaths = tests`, `asyncio_mode = auto`).
- pytest-asyncio >=0.23.0 - Async test support.

**Build/Dev:**
- flake8 - Lint (config in `setup.cfg` `[flake8]`, `max-line-length = 120`, ignores E501/W503/E203). Non-blocking lint job in CI.
- Gitleaks 8.18.2 - Secret scanning (blocking CI job, config `.gitleaks.toml`).
- Azure Functions Extension Bundle `[4.*, 5.0.0)` (`azure_functions/host.json`).

## Key Dependencies

**Critical:**
- azure-ai-formrecognizer >=3.3.3 - Azure AI Document Intelligence client for OCR (`scripts/process_document_ocr.py`, `prebuilt-document` model).
- azure-identity >=1.15.0 - `DefaultAzureCredential` for Entra ID token acquisition to Fabric SQL (`scripts/audit_fabric_comparison.py`).
- pyodbc >=5.1.0 - ODBC connection to Microsoft Fabric SQL endpoint (uses `ODBC Driver 17 for SQL Server`).
- PyJWT >=2.8.0 + cryptography >=42.0.0 - JWT RS256 validation against Entra ID JWKS (`scripts/auth.py`).
- httpx >=0.27.0 - Async HTTP for Microsoft Graph (Planner) and Azure Function backend calls.

**Infrastructure:**
- pandas >=2.2.0 - Tabular data handling for Fabric/Artus comparison.
- thefuzz >=0.22.0 + python-Levenshtein >=0.25.0 - Fuzzy client-name matching during audit reconciliation.
- pydantic >=2.7.0 - Request/response models in FastAPI.
- python-docx >=1.1.0 - DOCX generation/reading (`scripts/read_docx.py`, `scripts/generate_fic_draft.py`, `scripts/generate_fiche_rdv.py`).
- pyyaml >=6.0.1 - Copilot topic YAML validation (`scripts/validate_copilot_yaml.py`).
- requests >=2.31.0 - Teams webhook notification (`scripts/post_audit_workflow.py`).
- python-dotenv >=1.0.1 - `.env` loading across scripts.

## Configuration

**Environment:**
- Configured via `.env` (loaded with `load_dotenv()`); `.env.generated` is written by `scripts/deploy_azure_ocr.ps1` with OCR endpoint/key and is git-ignored.
- A `config.py` module is imported by `scripts/auth.py` and `scripts/planner_integration.py` (`JWKS_URL`, `CLIENT_ID`, `API_AUDIENCE`, `ALLOWED_ISSUERS`, `REQUIRED_SCOPES`, `REQUIRED_ROLES`, `TENANT_ID`) but is not present in the committed tree — it is expected at runtime on `PYTHONPATH=scripts`.
- Key runtime env vars: `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY`, `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE`, `AZURE_FUNCTION_URL`, `AZURE_FUNCTION_KEY`, `APPINSIGHTS_INSTRUMENTATIONKEY`, `TEAMS_WEBHOOK_URL`, `TENANT_ID`, `CLIENT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`.

**Build:**
- `setup.cfg` - pytest + flake8 configuration.
- `conftest.py` (root) and `tests/backend/conftest.py` - test fixtures / env setup.
- `azure_functions/host.json` - Functions host + Application Insights sampling.
- `azure_functions/local.settings.json` - local Functions settings (dev storage emulator).

## Platform Requirements

**Development:**
- Python 3.12, pip
- Azure CLI (`az`) - required for `scripts/deploy_azure_ocr.ps1`.
- Power Platform CLI (`pac`) - required for `scripts/sync_copilot.ps1`.
- PnP PowerShell (`Connect-PnPOnline`) - required for SharePoint scripts.
- `ODBC Driver 17 for SQL Server` - required for Fabric connectivity.

**Production:**
- Azure: Document Intelligence (Cognitive Services FormRecognizer, SKU S0, `westeurope`), Azure Durable Functions backend, Microsoft Fabric SQL, Application Insights, Microsoft Entra ID.
- Microsoft Power Platform / Copilot Studio (environment `org2cf282f3.crm4.dynamics.com`, bot id `c82f127c-8f47-f111-bec6-000d3ab9a512`).
- SharePoint Online (`https://gerep.sharepoint.com/sites/AC360`).
- CI/CD on GitHub Actions (ubuntu-latest).

---

*Stack analysis: 2026-06-08*
