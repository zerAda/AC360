# Testing Patterns

**Analysis Date:** 2026-06-10

## Test Framework

**Runner:**
- pytest 8.0.0+ 
- Config file: `conftest.py` (root and `tests/backend/conftest.py` for backend-specific setup)
- Coverage tracking: pytest-cov 5.0.0+

**Assertion Library:**
- pytest built-in assertions: `assert result == expected`
- pytest.raises() for exception testing: `with pytest.raises(HTTPException) as exc:`
- Exception assertions: `assert exc.value.status_code == 401`

**Run Commands:**
```bash
pytest                     # Run all tests
pytest -v                  # Verbose output
pytest --cov              # With coverage report
pytest tests/backend/      # Run specific test directory
pytest -k test_auth       # Filter by test name pattern
pytest -x                 # Stop on first failure
pytest --tb=short         # Shorter traceback format
```

## Test File Organization

**Location:**
- `tests/backend/` for FastAPI API server tests
- `tests/fabric/` for Fabric/audit engine tests
- `tests/azure_functions/` for Azure Durable orchestration tests
- `tests/copilot/` for Copilot integration tests
- `tests/security/` for security-specific tests (hardening, no secrets, etc.)
- `tests/red_team/` for attack simulations

**Naming:**
- `test_<module>.py` format: `test_auth_jwt.py`, `test_download_security.py`
- Test functions: `test_<scenario>`: `test_verify_jwt_missing_kid()`, `test_owner_can_download()`
- Async tests: `async def test_<scenario>(): ... await ...`

**Structure:**
```
tests/
├── backend/
│   ├── conftest.py           # pytest setup for API server
│   ├── test_auth_jwt.py
│   ├── test_download_security.py
│   └── test_job_isolation.py
├── fabric/
│   ├── test_schema_validation.py
│   └── test_comparison_engine.py
├── azure_functions/
│   ├── test_function_app.py
│   └── test_audit_pipeline.py
└── conftest.py               # Root-level pytest config
```

## Test Structure

**Suite Organization:**
```python
# Example: tests/backend/test_auth_jwt.py
import pytest
from fastapi import HTTPException
from unittest.mock import patch
from auth import verify_azure_ad_token

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

**Setup Patterns:**

1. **pytest Fixtures for Temporary Directories:**
```python
@pytest.mark.asyncio
async def test_owner_can_download(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    job_id = _make_job(tmp_path, owner="owner@gerep.fr")
    resp = await api_server.download_fiche_rdv(job_id, "fiche.docx", user_upn="owner@gerep.fr")
    assert isinstance(resp, FileResponse)
```

2. **pytest Fixtures for Configuration Injection:**
```python
# conftest.py — Setup before test collection
import os
import sys
import tempfile

_TEST_ENV_DEFAULTS = {
    "TENANT_ID": os.getenv("TENANT_ID", "test-tenant-00000000-0000-0000-0000-000000000000"),
    "CLIENT_ID": os.getenv("CLIENT_ID", "test-client-00000000-0000-0000-0000-000000000000"),
    "JOBS_BASE_DIR": os.getenv("JOBS_BASE_DIR", os.path.join(os.path.dirname(__file__), "jobs")),
}
for _key, _val in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _val)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
```

3. **Monkeypatch for PYTHONPATH:**
```python
# tests/backend/conftest.py
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
```

4. **Async Test Decorator:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_endpoint():
    # Test async function
    result = await async_function()
    assert result == expected
```

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**

1. **Patch External API Calls:**
```python
from unittest.mock import patch, MagicMock

@patch("process_document_ocr.AzureKeyCredential")
@patch("process_document_ocr.DocumentAnalysisClient")
def test_extract_document_azure_success(mock_client, mock_cred, tmp_path):
    mock_cred.return_value = MagicMock()
    
    mock_poller = MagicMock()
    mock_result = MagicMock()
    mock_result.pages = [1]
    mock_result.key_value_pairs = []
    mock_result.tables = []
    mock_poller.result.return_value = mock_result
    
    mock_instance = mock_client.return_value
    mock_instance.begin_analyze_document.return_value = mock_poller
    
    test_file = tmp_path / "dummy.pdf"
    test_file.write_text("dummy")
    
    result = extract_document_azure(str(test_file))
    assert result["metadata"]["extraction_mode"] == "azure-prebuilt-document"
```

2. **Patch Database Connections:**
```python
@patch("audit_fabric_comparison.get_fabric_connection")
def test_fetch_artus_data_fail_fast_on_missing_db(mock_conn):
    mock_conn.return_value = None
    with pytest.raises(ConnectionError) as exc:
        fetch_artus_data()
    assert "ERREUR CRITIQUE" in str(exc.value)
```

3. **Monkeypatch Environment Variables:**
```python
def test_rate_limit_enforced_per_user(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MAX", "5")
    # Test respects new env var
```

4. **Patch with Side Effects for Return Values:**
```python
def fake(client_name=None, siret=None):
    captured["siret"] = siret
    return {"nom_client": "X", "siret": siret, "numcli": "9", "produits": []}

monkeypatch.setattr(fabric_onelake, "fetch_client_reference", fake)
```

**What to Mock:**
- External API calls: Azure Document Intelligence, Microsoft Graph, Fabric SQL
- Database connections (when testing without real DB)
- HTTP requests: `httpx.get()`, `httpx.post()`
- File I/O for unit tests (use tmp_path for integration tests)
- JWT/JWKS fetching when testing auth logic

**What NOT to Mock:**
- Internal business logic: don't mock `Normalizer.normalize()` when testing `OptimizedMatcher.match_with_index()`
- Data flow validation: test actual dataframe operations
- Schema validation: use real JSON schema for conformance tests
- Security validations: test real path traversal defense with fixtures

## Fixtures and Factories

**Test Data Factories:**
```python
# From tests/backend/test_download_security.py
def _make_job(tmp_path, job_id=VALID_UUID, owner="owner@gerep.fr", with_meta=True):
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "fiche.docx").write_text("contenu")
    if with_meta:
        (job_dir / "meta.json").write_text(json.dumps({"user_upn": owner}))
    return job_id

# Usage in tests
def test_owner_can_download(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    job_id = _make_job(tmp_path, owner="owner@gerep.fr")
    # Test with the prepared fixture
```

**Fixture Imports:**
```python
# conftest.py provides pytest fixtures
# pytest-asyncio provides @pytest.mark.asyncio decorator
# tmp_path is built-in pytest fixture (temporary directory)
# monkeypatch is built-in pytest fixture (env/attribute patching)
```

**Test Data Location:**
- Inline in test functions: `mock_result = MagicMock()` with attributes set
- Temporary files via `tmp_path` fixture: `(tmp_path / "file.txt").write_text(...)`
- Example DataFrames: `pd.DataFrame({"col": [val1, val2]})`

## Coverage

**Requirements:** Not formally enforced (no `--cov-fail-under` in CI)

**View Coverage:**
```bash
pytest --cov=scripts --cov=azure_functions --cov=src --cov-report=html
# Generates htmlcov/index.html
```

**Coverage Report Location:**
- `.coverage` file at repo root (binary report)
- `htmlcov/` directory (if generated) contains detailed HTML report

**Coverage Gaps Known:**
- Azure SDK imports (protected by try/except, skipped on non-Azure env)
- Tkinter UI (`src/main.py`) has limited test coverage (manual UI testing required)
- Error paths in long orchestrations (Durable Functions) hard to test without full stack

## Test Types

**Unit Tests:**
- Scope: Single function/class in isolation
- Mocks: All external dependencies (DB, API, file I/O)
- Location: `tests/backend/test_auth_jwt.py` (auth logic), `tests/fabric/test_schema_validation.py` (audit engine)
- Example: `test_verify_jwt_missing_kid()` tests `verify_azure_ad_token()` with mocked JWT library

**Integration Tests:**
- Scope: Multiple components working together
- Mocks: Only external services (Azure APIs, Fabric); internal calls are real
- Location: `tests/backend/test_download_security.py` (file download with auth + metadata validation)
- Example: `test_owner_can_download()` integrates path validation, IDOR check, metadata loading

**E2E Tests:**
- Framework: Not formally set up
- Approach: Manual testing or CI pipeline tests that deploy and hit live endpoints
- Coverage: Full flow from API request through orchestration to output

**Security-Specific Tests:**
- Location: `tests/security/`, `tests/backend/test_*_security.py`
- Examples:
  - `test_path_traversal.py`: Path traversal blocking (`../../etc/passwd`)
  - `test_no_plaintext_secrets.py`: No hardcoded secrets in code
  - `test_no_dangerous_shell_patterns.py`: No shell metacharacters in subprocess calls
  - `test_safe_filename.py`: Filename sanitization against injection
- Patterns: Adversarial inputs, exploit attempts, invariant validation

## Common Patterns

**Async Testing:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    # Requires pytest-asyncio plugin
    result = await some_async_function()
    assert result == expected_value
    
@pytest.mark.asyncio
async def test_async_with_mock(monkeypatch):
    import asyncio
    
    async def fake_request():
        return {"status": "ok"}
    
    monkeypatch.setattr("module.async_request", fake_request)
    result = await trigger_audit()
    assert result["job_id"]
```

**Error Testing:**
```python
def test_missing_kid_raises_401():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
        with pytest.raises(HTTPException) as exc:
            verify_azure_ad_token(creds)
        assert exc.value.status_code == 401
        assert "kid" in exc.value.detail

def test_invalid_uuid_raises_400(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBS_BASE_DIR", str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        await api_server.download_fiche_rdv("not-a-uuid", "file.docx", user_upn="user")
    assert exc.value.status_code == 400
    assert "UUID" in exc.value.detail
```

**State Management in Tests:**
```python
# Captured state pattern
def test_fetch_reference_prioritises_siret(monkeypatch):
    import fabric_onelake
    captured = {}
    
    def fake(client_name=None, siret=None):
        captured["siret"] = siret
        captured["name"] = client_name
        return {"nom_client": "X", "siret": siret, "numcli": "9", "produits": []}
    
    monkeypatch.setattr(fabric_onelake, "fetch_client_reference", fake)
    fa._fetch_reference({"nom_client": "GEREP", "siret": "39000000000000"})
    
    assert captured["siret"] == "39000000000000"
```

**DataFrame Testing:**
```python
def test_match_client_name_strictness():
    # Create mock dataframe
    df = pd.DataFrame({
        "client_id": [1, 2],
        "nom_client": ["GEREP SA", "BETA Corp"],
        "plafond_hospitalisation": ["1000", "500"]
    })
    
    # Test matching success
    match, score = match_client_name("GEREP SA", df)
    assert match is not None
    assert score >= 85
    
    # Test matching failure
    match_reject, score_reject = match_client_name("Groupe GEREP SA", df)
    assert match_reject is None
    assert score_reject < 85
```

**Class-Based Test Grouping:**
```python
# From tests/backend/test_safe_filename.py
class TestSafeFilename:
    """Tests exhaustifs de la fonction safe_filename()"""
    
    def test_normal_name(self):
        assert safe_filename("Client Alpha") == "Client_Alpha"
    
    def test_path_traversal_dots(self):
        result = safe_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
    
    def test_null_byte(self):
        result = safe_filename("client\x00evil")
        assert "\x00" not in result
```

**Pytest Skip for Optional Dependencies:**
```python
# From tests/fabric/test_schema_validation.py
import pytest

jsonschema = pytest.importorskip("jsonschema")  # Skip test if not installed

def test_schemas_are_valid_jsonschema():
    for name in ("ocr_result.schema.json", ...):
        schema = _load(name)
        jsonschema.Draft202012Validator.check_schema(schema)
```

## Test Execution Flow

**Test Discovery:**
1. pytest collects tests from `tests/` directory
2. `conftest.py` (root) runs first: injects test env vars, adds `scripts/` to PYTHONPATH
3. `tests/backend/conftest.py` runs: adds backend-specific paths
4. Test modules imported
5. Test functions/classes executed

**Fail-Fast Behavior:**
- Configuration validation disabled during pytest collection (`conftest.py` injects defaults)
- `api_server.py` imports succeed without live Azure credentials
- First test failure stops run if `-x` flag used

**Async Test Execution:**
- `pytest-asyncio` provides event loop for `@pytest.mark.asyncio` tests
- Async fixtures (if any) would run before each test

---

*Testing analysis: 2026-06-10*
