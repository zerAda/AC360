# Testing Patterns

**Analysis Date:** 2026-06-11

## Test Framework

**Runner:**
- pytest 8.0.0+
- Config: `setup.cfg` `[tool:pytest]` section
- Test paths: `tests/` directory
- Python files matched: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

**Async Support:**
- pytest-asyncio 0.23.0+ with `asyncio_mode = auto`
- Async test functions marked with `@pytest.mark.asyncio`

**Assertion Library:**
- pytest's built-in assertions (`assert`, `pytest.raises()`)
- No external assertion library (pytest native is sufficient)

**Run Commands:**
```bash
pytest                           # Run all tests
pytest tests/backend/            # Run specific directory
pytest tests/backend/test_auth_jwt.py::test_verify_jwt_missing_kid  # Single test
pytest -v                        # Verbose output (default in setup.cfg)
pytest --tb=short               # Short traceback format (default)
pytest --cov=scripts            # Generate coverage report
pytest --cov-report=html        # Coverage HTML report
pytest -k "auth"                # Filter by keyword
pytest -m asyncio               # Filter by marker
```

## Test File Organization

**Location:**
- Tests are co-located in `tests/` directory structure mirroring `scripts/` and `azure_functions/`
- Example: `scripts/api_server.py` → `tests/backend/test_api_server.py` (subset), `tests/backend/test_job_isolation.py`, etc.
- Functional grouping: `tests/backend/`, `tests/fabric/`, `tests/admin/`, `tests/copilot/`, `tests/finops/`, `tests/security/`, `tests/usage/`, `tests/azure_functions/`, `tests/red_team/`

**Naming:**
- Convention: `test_<module>_<function>.py` or `test_<feature>.py`
- Examples: `test_auth_jwt.py`, `test_safe_logger_redaction.py`, `test_document_resolve.py`
- Total: 258 test functions across the suite

**Structure:**
```
tests/
├── conftest.py                     # Global pytest config (env injection)
├── backend/
│   ├── conftest.py               # Backend-specific setup
│   ├── test_auth_jwt.py           # Auth tests
│   ├── test_safe_logger_redaction.py
│   ├── test_job_isolation.py
│   └── ...
├── fabric/
│   ├── test_schema_validation.py
│   ├── test_normalization.py
│   └── ...
├── copilot/
│   ├── test_hardened_rag_topics.py
│   ├── test_agent_guardrails.py
│   └── ...
└── ...
```

## Test Structure

**Global Conftest** (`conftest.py`):
```python
"""
conftest.py — Global pytest configuration for AC360.

IMPORTANT: Test environment variables injected HERE, BEFORE any module import,
so that the fail-fast of config.py does not block pytest collection in CI/CD
or local environments without .env.
"""
import sys, os
_TEST_ENV_DEFAULTS = {
    "TENANT_ID": os.getenv("TENANT_ID", "test-tenant-00000000-0000-0000-0000-000000000000"),
    "CLIENT_ID": os.getenv("CLIENT_ID", "test-client-00000000-0000-0000-0000-000000000000"),
    "JOBS_BASE_DIR": os.getenv("JOBS_BASE_DIR", os.path.join(os.path.dirname(__file__), "jobs")),
    # ... more defaults
}
for _key, _val in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _val)

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
```

**Suite Organization** (from `tests/backend/test_auth_jwt.py`):
```python
import pytest
from fastapi import HTTPException
from unittest.mock import patch
from auth import verify_azure_ad_token
from fastapi.security import HTTPAuthorizationCredentials

def test_verify_jwt_missing_kid():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="eyJ...")
    with patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
        with pytest.raises(HTTPException) as exc:
            verify_azure_ad_token(creds)
        assert exc.value.status_code == 401
        assert "kid" in exc.value.detail

def test_verify_jwt_wrong_alg():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy")
    with patch("jwt.get_unverified_header", return_value={"kid": "123", "alg": "HS256"}):
        with pytest.raises(HTTPException) as exc:
            verify_azure_ad_token(creds)
        assert exc.value.status_code == 401
        assert "RS256" in exc.value.detail
```

**Patterns:**
- No test classes; flat function-based tests (pytest prefers functions over classes)
- Setup via `@pytest.fixture(autouse=True)` at module level
- Cleanup via `yield` in fixture (setup-teardown)
- One logical assertion per test function (or pytest.raises context for multiple error conditions)

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**
```python
from unittest.mock import patch, MagicMock, AsyncMock

# Sync mocking
with patch("api_server.subprocess.run", return_value=fake_proc):
    api_server.run_audit_pipeline(...)

# Async mocking
with patch("api_server.http_client.post", new=AsyncMock(return_value=response)):
    await trigger_audit(req, request, user_upn="user@gerep.fr")

# Attribute mocking
with patch.object(api_server, "_rate_limit_store", {}):
    await api_server._check_rate_limit(upn)

# Manual mock objects
fake = MagicMock()
fake.calls = []
fake.returncode = 1
fake.stderr = "error output"
```

**What to Mock:**
- External HTTP clients: `http_client.post()`, `httpx.get()`
- System subprocess calls: `subprocess.run()`
- Authentication checks: `jwt.get_unverified_header()`, `_fetch_jwks()`
- File system operations: `os.makedirs()`, file reads
- Cloud service calls: Azure Durable Functions endpoints (mocked as HTTP POST)
- Database operations: returned DataFrames or query results
- Environment variables: use `monkeypatch.setenv()` or manual `os.environ` setting in fixtures

**What NOT to Mock:**
- Core business logic functions (e.g., `redact()`, `normalize_amount()`, `alias_field()`)
- Schema validation (use real JSON schemas from `schemas/`)
- Security algorithms (JWT parsing, HMAC verification) — use real libraries, mock only network I/O
- Module imports — test actual imports, mock only external calls

**Example - Backend API Test** (`tests/backend/test_job_isolation.py`):
```python
@pytest.mark.asyncio
async def test_audit_forwarded_to_azure_function():
    """Verify request is forwarded to Azure Durable Function /audit endpoint."""
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678", client_context="ALPHA")
    post_mock = AsyncMock(return_value=_azure_response("az-instance-002"))
    
    with patch("api_server.http_client.post", new=post_mock), \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        await trigger_audit(req, _fake_request(), user_upn="test@gerep.fr")
    
    post_mock.assert_called_once()
    called_url = post_mock.call_args[0][0]
    assert called_url.endswith("/audit") or "/audit?" in called_url
    sent_json = post_mock.call_args[1]["json"]
    assert sent_json["document_id"] == "12345678-1234-5678-1234-567812345678"
```

## Fixtures and Factories

**Test Data:**
```python
# Fixture-based data creation (from test_document_resolve.py)
@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("SHAREPOINT_DRIVE_ID", "drive-d1")
    monkeypatch.setattr(api_server, "obo_configured", lambda: True)
    monkeypatch.setattr(api_server, "acquire_obo_graph_token", lambda raw: "graph-tok")
    api_server._rate_limit_store.clear()
    yield
    api_server._rate_limit_store.clear()

# Factory helper functions (from test_document_resolve.py)
def _item(name, modified="2026-05-01T00:00:00Z", path="/drives/d1/root:/ClientX"):
    return {"id": f"id-{name}", "name": name,
            "lastModifiedDateTime": modified, "parentReference": {"path": path}}

def _req(query, choice=None):
    return api_server.DocumentResolveRequest(query=query, choice=choice)

# Real schema loading (from test_schema_validation.py)
def _load(name):
    with open(os.path.join(SCHEMAS_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)
```

**Location:**
- Fixtures in conftest.py files (global and per-directory)
- Helper functions in test files themselves (small, single-use factories)
- Real data in `tests/evaluation/AC360_EVALUATION_DATASET.json` and `schemas/` directory

## Coverage

**Requirements:** No hard minimum enforced, but strong coverage maintained on:
- Security-critical paths: auth (100%), safe_logger (100%), path traversal guards (100%)
- Business logic: fabric_audit_engine, cost/usage tracking (>90%)
- API contracts: endpoint request/response validation (>85%)

**View Coverage:**
```bash
pytest --cov=scripts --cov-report=html
# Opens htmlcov/index.html showing line-by-line coverage
```

**Notable Coverage:**
- `tests/security/test_no_forbidden_files.py` — Scans for plaintext secrets in source
- `tests/security/test_no_dangerous_shell_patterns.py` — Detects shell injection risks

## Test Types

**Unit Tests:**
- Scope: Single function or small module in isolation
- Mocking: All external dependencies (HTTP, DB, file system, auth)
- Examples: `test_redact_masque_secrets_et_pii()`, `test_normalize_amount_fr_and_en()`, `test_rate_limit_enforced_per_user()`
- Location: `tests/backend/`, `tests/fabric/`, `tests/finops/`, `tests/usage/`, `tests/admin/`

**Integration Tests:**
- Scope: Multiple components working together, but still isolated from cloud
- Mocking: Only external services (Azure Functions, Microsoft Graph, Azure Cognitive Services)
- Examples: `test_audit_forwarded_to_azure_function()`, `test_run_audit_pipeline_neutralizes_stderr_before_persistence()`
- Location: `tests/backend/test_job_isolation.py`, `tests/azure_functions/test_function_app.py`

**Contract Tests:**
- Scope: Request/response contracts and API boundaries
- Pattern: Validate HTTP status codes, JSON response structure, error detail messages
- Examples: `test_audit_response_contains_job_id()`, `test_audit_rejects_empty_document_id()`
- Location: Throughout backend tests

**Schema Validation Tests:**
- Scope: Output conforms to JSON schemas
- Pattern: Load schema from `schemas/*.schema.json`, validate instance against it
- Examples: `test_audit_output_conforms_to_audit_result_schema()`, `test_schemas_are_valid_jsonschema()`
- Location: `tests/fabric/test_schema_validation.py`

**E2E/Acceptance Tests:**
- Framework: None dedicated; acceptance tests minimal and integrated into backend tests
- Examples: `tests/test_run_demo.py` — runs the demo end-to-end with real local setup

**Copilot/Agent Tests:**
- Scope: YAML configuration validation, guardrails, silent-RAG detection
- Examples: `test_rag_node_declares_explicit_answer_variable()`, `test_moderation_gate_high()`
- Location: `tests/copilot/test_hardened_rag_topics.py`, `tests/copilot/test_agent_guardrails.py`

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_audit_response_contains_job_id():
    req = AuditRequest(document_id="12345678-1234-5678-1234-567812345678")
    
    with patch("api_server.http_client.post", new=AsyncMock(return_value=_azure_response("az-001"))), \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        res = await trigger_audit(req, _fake_request(), user_upn="user1@gerep.fr")
    
    assert res["status"] == "accepted"
    assert res["job_id"] == "az-001"
```

**Error Testing:**
```python
def test_audit_rejects_empty_document_id():
    from fastapi import HTTPException
    req = AuditRequest(document_id="")
    
    with patch("api_server.http_client.post", new=AsyncMock()) as post_mock, \
         patch("api_server._check_rate_limit", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await trigger_audit(req, _fake_request(), user_upn="test@gerep.fr")
    
    assert exc.value.status_code == 400
    post_mock.assert_not_called()
```

**Parametrization:**
```python
@pytest.mark.parametrize("topic", TARGET_TOPICS)
def test_rag_node_declares_explicit_answer_variable(topic):
    data = _load_topic(topic)
    rag = _rag_nodes(data)
    assert rag, f"{topic}: aucun nœud SearchAndSummarizeContent trouvé"
    for node in rag:
        assert node.get("variable") == "Topic.Answer"
```

**Logging Redaction Verification:**
```python
def test_redact_masque_secrets_et_pii():
    raw = (
        f"token={FAKE_JWT} "
        f'AZURE_OCR_KEY="{FAKE_SECRET_VALUE}" '
        f"mail={FAKE_EMAIL} iban={FAKE_IBAN}"
    )
    out = redact(raw)
    
    assert FAKE_JWT not in out
    assert FAKE_SECRET_VALUE not in out
    assert FAKE_EMAIL not in out
    assert FAKE_IBAN not in out
    assert "MASQUÉ" in out  # At least one masking marker present
```

## Test Environment

**Env Setup** (from global conftest.py):
- TENANT_ID, CLIENT_ID: stub UUIDs (no real auth)
- JOBS_BASE_DIR: temporary directory or `tests/jobs`
- AZURE_OCR_KEY, AZURE_OCR_ENDPOINT: fake values
- FABRIC_SQL_ENDPOINT, FABRIC_DATABASE: test stubs
- SHAREPOINT_DRIVE_ID: injected per-test via monkeypatch
- AC360_*: feature flags, rate limits, blocked users injected as needed

**Isolation:**
- Test state cleared before/after: `_rate_limit_store.clear()`, `monkeypatch` resets after test
- Each test starts clean (no cross-test pollution)
- Fixtures with `autouse=True` apply automatically to all tests in the module

---

*Testing analysis: 2026-06-11*
