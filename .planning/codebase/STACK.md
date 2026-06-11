# Technology Stack

**Analysis Date:** 2026-06-11

## Languages

**Primary:**
- Python 3.12 - Backend API, Azure Functions, data processing, and automation scripts
- YAML - Copilot Studio configuration and topic definitions (`.mcs.yml` files)
- PowerShell - Infrastructure provisioning, deployment, and operational scripts

**Secondary:**
- Bicep - Infrastructure-as-Code for Azure resource definitions
- JSON - Configuration, schemas, parameters, and test fixtures

## Runtime

**Environment:**
- Python 3.12 (configured in `setup.cfg` for mypy)
- Azure Functions Runtime 2.0 (Consumption/Premium plan)
- Microsoft Copilot Studio (cloud-hosted, proprietary Microsoft platform)

**Package Manager:**
- pip (Python package management)
- Lockfile: `requirements.txt` present (root and `azure_functions/`)
- No `pyproject.toml` or `poetry.lock` — uses traditional `setup.cfg` for pytest/mypy configuration

## Frameworks

**Core:**
- FastAPI 0.111.0+ - Async HTTP API gateway server (`scripts/api_server.py`)
- Uvicorn 0.29.0+ - ASGI server for FastAPI
- Azure Functions (Python v2 model) - Serverless orchestration via Durable Functions

**Testing:**
- pytest 8.0.0+ - Test framework
- pytest-asyncio 0.23.0+ - Async test support
- pytest-cov 5.0.0+ - Coverage reporting
- Configuration in `setup.cfg` with asyncio_mode auto, CLI logging enabled

**Build/Dev:**
- Bicep CLI - Infrastructure deployment
- Azure CLI - Azure resource management
- GitHub Actions - CI/CD pipeline (`.github/workflows/ci.yml`, `cd-staging.yml`)
- Gitleaks 8.18.2 - Secret detection in CI

## Key Dependencies

**Critical:**

- **Azure SDK Suite** (3.x+):
  - `azure-ai-formrecognizer` 3.3.3+ - Document Intelligence (OCR) for PDF/image analysis
  - `azure-identity` 1.15.0+ - Managed Identity and Entra ID authentication
  - `azure-functions` 1.18.0+ - Azure Functions runtime bindings
  - `azure-functions-durable` 1.2.9+ - Orchestration engine for long-running workflows

- **Authentication & Security**:
  - `PyJWT` 2.8.0+ - JWT token parsing and verification
  - `cryptography` 42.0.0+ - Cryptographic operations (RSA for JWKS validation)
  - `python-dotenv` 1.0.1+ - Environment variable loading from `.env`

- **Data & Analytics**:
  - `deltalake` 0.18.0+ - Read Delta tables from Microsoft Fabric OneLake (Python native, no ODBC)
  - `pandas` 2.2.0+ - DataFrame operations for data transformation
  - `pyarrow` 14.0.0+ - Arrow serialization for efficient Fabric I/O
  - `pyodbc` 5.1.0+ - SQL Server connectivity (legacy; OneLake preferred in new code)
  - `thefuzz` 0.22.0+ - Fuzzy string matching for client reconciliation
  - `python-Levenshtein` 0.25.0+ - Levenshtein distance algorithm (dependency of thefuzz)

- **Document Processing**:
  - `python-docx` 1.1.0+ - Read/write/generate DOCX files (FIC draft generation)
  - `defusedxml` 0.7.1+ - Safe XML parsing (protects against XXE attacks)
  - `PyYAML` 6.0.1+ - Parse YAML Copilot Studio configuration files

- **HTTP & Networking**:
  - `httpx` 0.27.0+ - Async HTTP client (used by FastAPI gateway and SharePoint downloads)
  - `requests` 2.31.0+ - Synchronous HTTP client (utility scripts, compatibility)

- **Schema & Validation**:
  - `pydantic` 2.7.0+ - Data model validation (FastAPI request/response models)
  - `jsonschema` 4.21.0+ - JSON schema validation for audit output formats

## Configuration

**Environment:**
- `.env` file (gitignored, example: `.env.example`)
- Key configuration groups:
  - **Entra ID Authentication**: `TENANT_ID`, `CLIENT_ID`, `REQUIRED_SCOPES`, `REQUIRED_ROLES`
  - **On-Behalf-Of (OBO)**: `OBO_CLIENT_ID`, `OBO_CLIENT_SECRET`, `AC360_REQUIRE_OBO`
  - **Azure Document Intelligence (OCR)**: `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY`, `AZURE_OCR_TIMEOUT_S`
  - **Microsoft Fabric**: `FABRIC_WORKSPACE_ID`, `FABRIC_GOLD_LAKEHOUSE_ID`, `FABRIC_CLIENT_TABLE`, `FABRIC_CACHE_TTL_SECONDS`
  - **Azure Durable Functions**: `AZURE_FUNCTION_URL`, `AZURE_FUNCTION_KEY`, `AZURE_DURABLE_KEY`, `TASK_HUB_NAME`, `SHAREPOINT_DRIVE_ID`
  - **Jobs & Storage**: `JOBS_BASE_DIR`, `ALLOWED_EXTENSIONS`
  - **Governance & Feature Flags**: `AC360_GLOBAL_ENABLED`, `AC360_OCR_ENABLED`, `AC360_RAG_ENABLED`, `AC360_AUDIT_ENABLED`, `AC360_BLOCKED_USERS_HASHED`, `AC360_BLOCKED_TEAMS`, `AC360_ADMIN_ROLE`
  - **Usage Tracking**: `AC360_ENVIRONMENT`, `AC360_BOT_VERSION`, `AC360_USAGE_SINK`
  - **FinOps**: `AC360_RATE_CARD`, `AC360_BUDGET_EUR`, `AC360_BUDGET_WARN_PCT`
  - **Teams Webhooks**: `TEAMS_WEBHOOK_URL`
  - **Application Insights**: `APPINSIGHTS_INSTRUMENTATIONKEY` (optional)

**Build:**
- `setup.cfg` - Pytest, mypy, flake8 configuration
- `azure_functions/host.json` - Azure Functions extension bundles and logging (Application Insights sampling enabled)
- `infra/main.bicep` - Infrastructure-as-Code for Azure resources
- `infra/staging.parameters.json` - Bicep parameter overrides for staging environment

## Platform Requirements

**Development:**
- Python 3.12+
- pip
- PowerShell 7+ (for deployment/ops scripts)
- Azure CLI (for local Azure interaction)
- Azure Functions Core Tools (for local Function app execution)
- git (version control)
- GitHub account (CI/CD)

**Production:**
- Microsoft Azure subscription
  - Azure App Service (for FastAPI gateway) or Azure Container Instances
  - Azure Functions Consumption/Premium Plan
  - Azure Storage Account (for Durable state and job artifacts)
  - Azure Key Vault (for secrets)
  - Azure Document Intelligence resource (for OCR)
  - Microsoft Fabric workspace and lakehouse
  - Azure SQL Database or Fabric SQL Endpoint (legacy)
  - Application Insights (optional, for monitoring)
- Microsoft 365 tenant with:
  - Microsoft Entra ID (authentication authority)
  - SharePoint Online (document source)
  - Teams (notification sink)
  - Microsoft Copilot Studio (frontend)

## Observability

**Logging Framework:**
- Python built-in `logging` module
- Application Insights integration via `APPINSIGHTS_INSTRUMENTATIONKEY` env var
- Custom safe logger (`scripts/safe_logger.py`) for redacting PII/secrets from logs

**Monitoring:**
- Application Insights (Azure native): enabled in `azure_functions/host.json`
- Custom usage tracking module (`scripts/usage_tracker.py`) — logs to optional JSON sink
- Structured logging with UTC timestamps and log level (setup.cfg: log_format = "%(asctime)s [%(levelname)s] %(message)s")

---

*Stack analysis: 2026-06-11*
