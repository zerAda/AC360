# Technology Stack

**Analysis Date:** 2026-06-10

## Languages

**Primary:**
- Python 3.12 - Core backend, Azure Functions, API server, audit engine, and document processing

**Secondary:**
- YAML - Copilot Studio configuration and topic definitions
- JSON - Configuration files and API payloads

## Runtime

**Environment:**
- Python 3.12.10
- Azure Functions Runtime (v2 model, Python)
- FastAPI for HTTP API layer

**Package Manager:**
- pip with requirements.txt per module
- Lockfile: Not used (requirements.txt with pinned versions)

## Frameworks

**Core:**
- FastAPI 0.111.0+ - REST API framework for audit engine
- uvicorn 0.29.0+ - ASGI server for FastAPI
- Pydantic 2.7.0+ - Request/response validation and data models

**Azure Integration:**
- azure-functions 1.18.0+ - Azure Functions runtime for Durable orchestration
- azure-functions-durable 1.2.9+ - Durable Functions orchestration framework
- azure-identity 1.15.0+ - Authentication with Managed Identity and DefaultAzureCredential
- azure-ai-formrecognizer 3.3.3+ - Azure Document Intelligence (OCR/extraction)

**Authentication & Validation:**
- PyJWT 2.8.0+ - JWT token verification
- cryptography 42.0.0+ - Cryptographic operations for RSA key validation
- HTTPBearer (FastAPI security) - Bearer token extraction from Authorization headers

**Data Processing:**
- pandas 2.2.0+ - Data manipulation and analysis (Fabric data loading, comparison)
- deltalake 0.18.0+ - Direct access to Microsoft Fabric Delta Lake tables (OneLake)
- pyarrow 14.0.0+ - Arrow format support for Delta Lake
- python-docx 1.1.0+ - DOCX document generation (FIC draft documents)
- pyyaml 6.0.1+ - YAML parsing (Copilot Studio configuration)
- jsonschema 4.21.0+ - JSON schema validation

**Document Processing:**
- pdfplumber 0.10.0+ - PDF content extraction
- openpyxl 3.0.0+ - Excel workbook handling
- defusedxml 0.7.1+ - Secure XML parsing (defense against XXE attacks)

**String Matching:**
- thefuzz 0.22.0+ - Fuzzy string matching for client name reconciliation
- python-Levenshtein 0.25.0+ - Levenshtein distance computation for fuzzy matching

**HTTP & Networking:**
- httpx 0.27.0+ - Async HTTP client for Graph API, Planner, Durable Functions webhooks
- requests 2.31.0+ - Sync HTTP client for legacy integrations (Teams webhook)

**Configuration & Environment:**
- python-dotenv 1.0.1+ - .env file loading for local development
- pyodbc 5.1.0+ - ODBC database connections (legacy Fabric SQL endpoint, not primary path)

**Testing & Quality:**
- pytest 8.0.0+ - Unit and integration test framework
- pytest-asyncio 0.23.0+ - Async test support for FastAPI and async functions
- pytest-cov 5.0.0+ - Code coverage reporting
- flake8 7.1.1 - Linting (via pre-commit hook)
- mypy 1.11.2 - Static type checking (via pre-commit hook)
- gitleaks 8.18.2 - Secret detection (via pre-commit hook)

## Key Dependencies

**Critical:**
- `PyJWT 2.8.0` - RS256 verification of Entra ID tokens; security-critical for API authentication
- `azure-identity 1.15.0` - Managed Identity credential flow; required for Azure Function execution
- `deltalake 0.18.0` - Direct Python access to Fabric OneLake without ODBC; core data reconciliation path
- `azure-ai-formrecognizer 3.3.3` - OCR extraction from PDF/DOCX; Phase 3 audit functionality
- `azure-functions-durable 1.2.9` - Orchestration of multi-step audit workflow (download → OCR → compare → generate)
- `defusedxml 0.7.1` - Hardening against XXE attacks in document parsing

**Infrastructure:**
- `httpx 0.27.0` - Async HTTP for Graph API calls, Planner integration, Durable webhook polling
- `pandas 2.2.0` - Client reference data loading and field-level comparison
- `python-docx 1.1.0` - FIC (Fiche d'Identité Crédit) document generation for audit output
- `thefuzz 0.22.0` - Client name fuzzy matching (secondary reconciliation after SIRET)

## Configuration

**Environment:**
- `.env.example` - Template with all configurable variables
- Variables stored in Azure Key Vault (production) or `.env` (local development)
- No configuration files (INI/TOML for app logic); all via environment variables

**Build:**
- `host.json` - Azure Functions extension bundle configuration (version [4.*, 5.0.0))
- `requirements.txt` - Project root for main API dependencies
- `azure_functions/requirements.txt` - Durable Functions specific dependencies
- `scripts/requirements.txt` - CLI/utility script dependencies
- `src/requirements.txt` - Data extraction utility dependencies (pandas, pdfplumber, openpyxl)

**Code Quality:**
- `.pre-commit-config.yaml` - Hooks for trailing whitespace, YAML/JSON validation, flake8, mypy, gitleaks
- `.gitleaks.toml` - Secret pattern detection rules (Teams webhooks, bearer tokens, SHAREPOINT_DRIVE_ID)

## Platform Requirements

**Development:**
- Python 3.12+
- pip package manager
- Azure CLI or az login for local identity (DefaultAzureCredential in dev)
- Optional: Azure Functions Core Tools for local Function testing

**Production:**
- Azure Subscription (hosting, Key Vault, Storage, Document Intelligence, Fabric workspace)
- Azure App Service (API server runtime)
- Azure Functions (Durable orchestration runtime)
- Azure Durable Storage account (task hub state)
- Microsoft Fabric workspace with Gold Lakehouse containing `tbl_super_product_client_api_gold`
- Microsoft Entra ID tenant with app registration (OAuth, token verification)
- SharePoint Online with configured drive (document ingestion)
- Optional: Application Insights (monitoring, telemetry)

---

*Stack analysis: 2026-06-10*
