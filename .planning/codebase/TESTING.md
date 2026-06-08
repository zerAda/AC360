# Testing Patterns

**Analysis Date:** 2026-06-08

AC360's test suite is **security- and governance-focused**. Beyond classic unit tests, large portions are *static-assertion* tests that read source files, PowerShell scripts, and Copilot `.mcs.yml` topics to prove that hardening controls are present and that secrets/PII never leak. The suite is organized by concern: backend, copilot, security, red_team, evaluation.

## Test Framework

**Runner:**
- pytest `>=8.0.0`
- Config: `setup.cfg` (`[tool:pytest]` section)
- async support: `pytest-asyncio>=0.23.0` with `asyncio_mode = auto`

**Key config (`setup.cfg`):**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
log_cli = true
log_cli_level = INFO
addopts = -v --tb=short
```

**Assertion Library:** plain `assert` + `pytest.raises`. No separate assertion lib.

**Run Commands:**
```bash
python -m pytest tests/                 # Run all tests (verbose, short traceback)
python -m pytest tests/security/        # Run only security gate (CI JOB 1, blocking)
python -m pytest tests/backend/ -v      # Backend unit tests
python -m pytest tests/red_team/ -v     # 20-vector red-team static suite
python -m pytest tests/ --junitxml=test-results/results.xml   # CI artifact form
```

> Environment requirement: tests need `TENANT_ID`, `CLIENT_ID` (and other stubs) set, and `scripts/` on `PYTHONPATH`. Both are injected automatically by conftest (see below); CI also sets `PYTHONPATH: scripts` and stub `TENANT_ID`/`CLIENT_ID`.

## Test File Organization

**Location:** Separate `tests/` tree (not co-located with `scripts/`), partitioned by concern:
```
tests/
├── backend/        # FastAPI/auth/pipeline unit + integration (test_auth_jwt, test_path_traversal,
│                   #   test_safe_filename, test_safe_logger_redaction, test_ocr_fabric, test_job_isolation,
│                   #   test_no_dangerous_shell_patterns) + its own conftest.py
├── copilot/        # Copilot Studio topic validation (test_topics_integrity, test_topics_silent_and_security,
│                   #   test_hardened_rag_topics)
├── security/       # Repo-wide static gates (test_no_plaintext_secrets, test_no_forbidden_files) — CI blocking
├── red_team/       # test_red_team_automated.py — 20 attack vectors RT-01..RT-20
└── evaluation/     # Quality/eval harness
```

**Naming:** `test_<subject>.py`; functions `test_<behavior>`; classes `Test<Subject>`.

## Test Structure

**Suite organization** — two dominant styles.

*Function-style (most backend/security/copilot/red-team tests):*
```python
def test_validate_document_id_invalid_uuid():
    with pytest.raises(HTTPException) as exc:
        _validate_document_id("../../../windows/system32/cmd.exe")
    assert exc.value.status_code == 400
    assert "UUID" in exc.value.detail
```

*Class-style (exhaustive parameterized-by-method cases):*
```python
class TestSafeFilename:
    """Tests exhaustifs de la fonction safe_filename() — bloque le Path Traversal."""

    def test_path_traversal_dots(self):
        result = safe_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
```

**Patterns:**
- Exceptions asserted via `with pytest.raises(HTTPException) as exc:` then inspect `exc.value.status_code` / `exc.value.detail`.
- Static-control tests read a file and assert a substring is present/absent, with **rich French failure messages** carrying the requirement ID and the security rationale (e.g. `"RT-11 FAIL : ... auth bypassable."`).
- Red-team tests grouped by attack category with banner comments (`RT-01 à RT-05 : Prompt Injection / Jailbreak`).
- Test docstrings (French) state the control being verified.

## Mocking

**Framework:** `unittest.mock` (`patch`, `MagicMock`).

**Patterns:**
```python
# Patch external/library boundary by target path:
with patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
    ...

# Patch subprocess + filesystem + sink, drive integration, then inspect call args:
fake_proc = MagicMock(); fake_proc.returncode = 1
fake_proc.stderr = _stderr_with_secrets()
fake_log = MagicMock()
with patch("api_server.subprocess.run", return_value=fake_proc), \
     patch("api_server.os.makedirs"), \
     patch("db_manager.log_audit_action", fake_log):
    api_server.run_audit_pipeline(job_id="job-test-0001", doc_path="...", user_principal_name="agent@gerep.fr")
failed_calls = [c for c in fake_log.call_args_list
                if len(c.args) >= 4 and c.args[1] == "END_AUDIT" and c.args[2] == "FAILED"]
```

**What to Mock:**
- Network/identity calls (`jwt` header decode, JWKS fetch).
- Subprocess execution (`api_server.subprocess.run`), filesystem mutations (`os.makedirs`).
- Persistence sinks (`db_manager.log_audit_action`) — assert what *would* be written rather than hitting a DB.

**What NOT to Mock:**
- The unit under test (sanitizers/redactors run for real — `safe_filename`, `redact`).
- File reads against real repo artifacts in static gate tests (the whole point is checking real files).

## Fixtures and Factories

**Test data:** Inline module-level constants for fake secrets/PII, deliberately realistic:
```python
FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.s3cr3t..."
FAKE_SECRET_VALUE = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"
FAKE_EMAIL = "jean.dupont@client-prive.fr"
FAKE_IBAN = "FR7630006000011234567890189"
```
Helper builders (e.g. `_stderr_with_secrets()`) assemble realistic dirty inputs.

**Location / environment fixtures:** No `pytest.fixture`-heavy style; setup happens in `conftest.py` files:
- Root `conftest.py`: injects `_TEST_ENV_DEFAULTS` (TENANT_ID, CLIENT_ID, JOBS_BASE_DIR, AZURE_OCR_KEY, FABRIC_*, REDIS_URL) via `os.environ.setdefault` **before any import**, and prepends `scripts/` to `sys.path`. These are explicitly documented as harmless test stubs with no real Microsoft access.
- `tests/backend/conftest.py`: same pattern scoped to backend, uses `tempfile.gettempdir()` for `JOBS_BASE_DIR`, satisfies `api_server` import-time fail-fast.

> Critical ordering: env injection MUST precede imports because `config.py`/`api_server.py` fail-fast on missing config at import time.

## Coverage

**Requirements:** No coverage threshold enforced (no `coverage`/`pytest-cov` in `requirements.txt`, none in CI). Confidence comes from the breadth of security gates rather than a coverage %.

**View Coverage:** Not configured. Would require adding `pytest-cov` (`python -m pytest --cov=scripts tests/`).

**CI artifact:** JUnit XML uploaded — `test-results/results.xml`, 30-day retention (`.github/workflows/ci.yml` JOB 3).

## Test Types

**Unit Tests (`tests/backend/`):** Pure-function behavior — `safe_filename` (12 path-traversal/injection cases), `redact` (secret/PII masking, control-char stripping, truncation), JWT header validation.

**Integration Tests (`tests/backend/`):** Cross-module flows with boundaries mocked — `run_audit_pipeline` → `log_audit_action` redaction (`test_safe_logger_redaction.py`); OCR/Fabric (`test_ocr_fabric.py`); job isolation (`test_job_isolation.py`).

**Static Security Gates (`tests/security/`, `tests/red_team/`, parts of `tests/copilot/`):** Read repo source/scripts/YAML and assert presence/absence of patterns:
- `test_no_plaintext_secrets.py` — walks the repo (`.py/.json/.yml/.ps1`, excluding `.git`, `__pycache__`, `jobs`, `Archives_Documentaires`), regex-scans for secret patterns, skips placeholders/`.example`.
- `test_no_forbidden_files.py` — forbidden artifacts not committed.
- `test_red_team_automated.py` — 20 vectors: prompt-injection/jailbreak, DLP/cross-client leakage, backend/API (no `verify_signature=False`, no hardcoded secrets, env-based config, no `Invoke-Expression`), governance (.gitignore/.env.example/.gitleaks.toml/scan_secrets.ps1 present, no real GUIDs in examples).

**Copilot Topic Tests (`tests/copilot/`):** Parse every `*.mcs.yml` with `yaml.safe_load` and assert governance invariants — `useModelKnowledge` never `True`, at most one `OnUnknownIntent` fallback, no empty `displayName`, hardened RAG / silent-success / security topics present.

**E2E / Bot loop:** `scripts/ralphe_loop_tester.py` (automated Copilot Studio loop tester) — runtime/manual harness, outside the pytest gate.

## Common Patterns

**Async testing:** Enabled globally via `asyncio_mode = auto` — `async def test_*` functions run without explicit `@pytest.mark.asyncio`.

**Error testing:**
```python
with pytest.raises(HTTPException) as exc:
    verify_azure_ad_token(creds)
assert exc.value.status_code == 401
assert "kid" in exc.value.detail
```

**Negative / absence assertions (security):**
```python
assert FAKE_JWT not in out
assert "\n" not in details          # anti log-injection
assert "verify_signature=False" not in content   # RT-11 auth-bypass guard
```

## CI Pipeline Gates (`.github/workflows/ci.yml`)

1. **Security Scan** (blocking) — Gitleaks 8.18.2 + `pytest tests/security/`.
2. **Validate Copilot YAML** (blocking) — `scripts/validate_copilot_yaml.py`.
3. **Tests** (blocking) — full `pytest tests/` with JUnit XML artifact.
4. **Lint** (non-blocking) — flake8 on `scripts/`.
5. **Package Dry-Run** — `pwsh scripts/package_release.ps1 -DryRun`.
6. **Notify Success** — summary if all pass.

Python 3.12 across all jobs; concurrency cancels stale runs per branch.

---

*Testing analysis: 2026-06-08*
