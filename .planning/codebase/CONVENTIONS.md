# Coding Conventions

**Analysis Date:** 2026-06-11

## Naming Patterns

**Files:**
- Module names: lowercase with underscores, matching function/class names they contain (`api_server.py`, `safe_logger.py`, `auth.py`)
- Test files: `test_<module>.py` (e.g., `test_auth_jwt.py`, `test_safe_logger_redaction.py`)
- Configuration: `conftest.py` for pytest fixtures and setup at each directory level

**Functions:**
- Use snake_case for all function names: `verify_azure_ad_token()`, `normalize_amount()`, `extract_canonical_fields()`
- Private/internal functions: prefix with underscore: `_truthy()`, `_norm_key()`, `_fetch_jwks()`, `_jwks_cache_valid()`
- Async functions use same convention: `async def trigger_audit()`, `async def test_rate_limit_enforced_per_user()`

**Variables:**
- Module-level constants: UPPERCASE with underscores: `JWKS_TTL_SECONDS`, `_RATE_LIMIT_MAX`, `FEATURE_ENV`, `_MASK_SECRET`
- Regular variables: snake_case: `tenant_id`, `job_id`, `user_upn`, `document_id`
- Temporary/loop variables: lowercase: `f`, `m`, `c` (when iterating, reuse patterns from codebase)
- Private module state: underscore prefix: `_JWKS_CACHE`, `_JWKS_CACHE_TS`, `_rate_limit_store`

**Types:**
- Type hints use snake_case for generics and proper capitalization for classes: `Dict[str, List[str]]`, `Optional[str]`, `BaseModel`, `HTTPException`
- Dataclass names: PascalCase: `AppConfig`, `AuditRequest`, `DocumentResolveRequest`

## Code Style

**Formatting:**
- Line length: maximum 120 characters (configured in `setup.cfg` `[flake8]`)
- Indentation: 4 spaces
- Use `from __future__ import annotations` for forward-compatible type hints (present in 9 core modules)

**Linting:**
- Tool: flake8 (configured in `setup.cfg`)
- Ignored rules: E203, W503, W504, E402, E741
- Excludes: `__pycache__`, `.git`, `.venv`, jobs, `.pytest_cache`, `.mypy_cache`, `.planning`, `.claude`

**Type Checking:**
- Tool: mypy (configured in `setup.cfg`)
- Strict typing enforced on core modules only: `scripts/fabric_audit_engine.py`, `scripts/feature_flags.py`, `scripts/usage_tracker.py`, `scripts/cost_tracker.py`, `scripts/admin_controls.py`, `scripts/graph_obo.py`, `azure_functions/shared/audit_pipeline.py`, `azure_functions/shared/sharepoint.py`
- Other modules: ignore missing imports (`ignore_missing_imports = true`)
- Python version: 3.12

## Import Organization

**Order:**
1. `from __future__ import annotations` (when using forward references)
2. Standard library imports: `os`, `sys`, `json`, `re`, `time`, `asyncio`, `uuid`, `urllib.parse`, etc.
3. Type/dataclass imports: `from typing import ...`, `from dataclasses import ...`
4. Third-party frameworks: `fastapi`, `pydantic`, `httpx`, `pytest`
5. Third-party utilities: `pyodbc`, `pandas`, `pyyaml`, `defusedxml`, `cryptography`, `PyJWT`
6. Local imports: `from auth import ...`, `from config import ...`, `from safe_logger import ...`

**Path Aliases:**
- No path aliases configured; imports use relative paths from `scripts/` directory
- Tests add `scripts/` to PYTHONPATH explicitly in conftest.py files to enable absolute imports: `sys.path.insert(0, ...)`
- Fabric SDK integration uses conditional imports to avoid blocking non-Fabric environments

## Error Handling

**Patterns:**
- FastAPI endpoints raise `HTTPException(status_code=..., detail=...)` for HTTP errors (400, 401, 403, 429, 503)
- Custom exceptions: `ConfigurationError` extends `RuntimeError` (in `scripts/config.py`)
- Validation errors: raise `ValueError` with descriptive message (e.g., in sharepoint module for file extension/size)
- Auth failures: raise `HTTPException(401)` with security-appropriate detail message
- Rate limiting violations: raise `HTTPException(429)` with user-friendly message
- JSON parsing errors: handled gracefully with fallback to next parsing attempt (e.g., in `_assert_durable_owner()`)
- Try-except used minimally; prefer explicit validation before operations

**Security Error Logging:**
- All error details logged via `safe_logger.log_security()` to redact secrets/PII before persistence
- Secrets (JWT, API keys, IBAN, emails) masked with placeholders like `[SECRET_MASQUÉ]`, `[EMAIL_MASQUÉ]`, `[PII_MASQUÉE]`
- No control characters (CR/LF) in persisted error details (prevents log injection)

## Logging

**Framework:** Python's standard `logging` module

**Patterns:**
- Module-level logger creation: `logger = logging.getLogger("AC360")` with level `logging.INFO`
- Log redaction MANDATORY: all user-facing or externally observable output routed through `safe_logger.redact()`
- Security events: use `safe_logger.log_security(level, message, data=None)` function
  - Example: `log_security("ERROR", f"Failed to fetch JWKS: {exc}")`
- No plaintext secrets logged anywhere (checked by `tests/security/test_no_plaintext_secrets.py`)
- AppInsights integration: when `APPINSIGHTS_INSTRUMENTATIONKEY` set, telemetry logged via `log_security("INFO", "AppInsights_Telemetry", {...})`

## Comments

**When to Comment:**
- **Docstrings (triple quotes):** Always present on:
  - Module level (first line after imports): explain purpose and design intent
  - Function/method definitions: explain what it does, parameters, return value, raises
  - Class definitions: explain responsibility
- **Inline comments:** Sparingly, for non-obvious logic
  - Example: "Fail-fast at startup: without TENANT_ID/CLIENT_ID, token validation is impossible"
  - Example: "Cache JWKS with TTL (rotation of keys signed by Entra ID). Refresh when TTL exceeded AND on unknown kid (anticipated rotation). Prevents indefinite cache risk."
- **Comment style:** Use English in code comments; French allowed in docstrings for French-centric domain (e.g., "conforme à la Baseline Sécurité")

**JSDoc/TSDoc:**
- Not used; this is Python, uses docstrings instead
- Parameter docs in docstring (numpy/Google style):
  ```python
  def redact(message, max_len=MAX_LEN):
      """Neutralize a message before logging.
      
      Removes ANSI sequences, masks secrets and PII, removes control chars,
      truncates to max_len.
      """
  ```

## Function Design

**Size:** Typically 10–50 lines; split if exceeding 100 lines

**Parameters:**
- Type hints required on all function parameters and return types (enforced by mypy on core modules)
- Use `Optional[Type]` for nullable values, avoid `None` as default for production code
- Keyword-only arguments for named parameters: `def build_usage_event(event_type: str, *, status: str = "ok", ...)`
- No `*args` or `**kwargs` in public APIs; explicit parameters or dataclass models preferred

**Return Values:**
- Always include return type hint
- Consistent return types: don't return `None` mixed with values in same function without clear intent
- On failure, raise exception rather than returning `None` (except for truly optional lookups)

## Module Design

**Exports:**
- Use `__all__` to declare public API: `__all__ = ["redact", "MAX_LEN", "logger", "log_security"]`
- Private module state prefixed with underscore: `_JWKS_CACHE`, `_JWKS_CACHE_TS`, `_ANSI_RE`

**Barrel Files:**
- Not used; imports source modules directly

**Module Patterns:**
- Each module has single clear responsibility (e.g., `safe_logger.py` = redaction, `auth.py` = JWT verification, `feature_flags.py` = feature toggling)
- Initialization logic in `load_*()` functions called at import or startup, never on module import
- Configuration loaded via `config.load_config(require_auth=True)` at app startup (fail-fast pattern)

---

*Convention analysis: 2026-06-11*
