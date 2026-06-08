# Coding Conventions

**Analysis Date:** 2026-06-08

AC360 is a polyglot project: Python (FastAPI backend + pipeline scripts), PowerShell (release/packaging/orchestration), Copilot Studio YAML (`.mcs.yml` topics/agents), and Azure Functions. Python code lives in `scripts/`; tests in `tests/`. Domain logic is written in French (docstrings, identifiers, user-facing strings, log messages, comments).

## Naming Patterns

**Files:**
- Python modules: lowercase `snake_case`, often verb-noun describing the action — `generate_fiche_rdv.py`, `process_document_ocr.py`, `audit_fabric_comparison.py`, `safe_logger.py`, `api_server.py`.
- PowerShell scripts: `Verb_noun.ps1` / lowercase — `package_release.ps1`, `scan_secrets.ps1`.
- Copilot Studio: PascalCase French topic names with `.mcs.yml` suffix — `Refusmodificationdocument.mcs.yml`, `Escalate.mcs.yml`, `settings.mcs.yml`, `agent.mcs.yml`.
- Test files: `test_*.py` (enforced by `setup.cfg` `python_files = test_*.py`).

**Functions:**
- `snake_case` everywhere — `verify_azure_ad_token`, `safe_filename`, `generate_fiche_rdv`, `run_audit_pipeline`, `log_security`.
- Internal/module-private helpers prefixed with single underscore — `_fetch_jwks`, `_get_public_key`, `_validate_document_id`, `_read_all_topics` (test helper), `_stderr_with_secrets` (test helper).

**Variables:**
- `snake_case` — `unverified_header`, `token_scopes`, `client_name`, `job_id`.
- Module-level mutable caches and constants in `UPPER_SNAKE` or `_UPPER_SNAKE` — `_JWKS_CACHE`, `MAX_LEN`, `_MASK_SECRET`, `_TEST_ENV_DEFAULTS`, `SECRET_PATTERNS`.
- French domain vocabulary appears in identifiers and strings — `safe_name`, `client_inconnu`, `fiche_rdv`, `upn` (user principal name).

**Types:**
- Type hints used on function signatures — `def safe_filename(name: str, max_length: int = 64) -> str:`, `Optional[dict]`, `HTTPAuthorizationCredentials`.
- Pydantic v2 models (`pydantic>=2.7.0`) for request/response schemas in FastAPI.
- No PascalCase classes in the pipeline scripts beyond framework types; test suites use `Test*` classes (e.g. `TestSafeFilename`).

## Code Style

**Formatting:**
- No autoformatter (Black/Ruff) configured. Style is hand-maintained.
- 4-space indentation, double-quoted strings predominate.
- Module-level docstrings (triple-quoted, French) head most files — see `safe_logger.py`, `conftest.py`, `generate_fiche_rdv.py`.

**Linting:**
- flake8, configured in `setup.cfg` `[flake8]`.
- `max-line-length = 120`.
- Ignored rules: `E501` (line length), `W503` (line break before binary operator), `E203` (whitespace before `:`).
- Excludes: `__pycache__`, `.git`, `.venv`, `venv`, `scripts/__pycache__`, `release`, `jobs`.
- CI runs flake8 as **non-blocking** (`continue-on-error: true`, JOB 5 in `.github/workflows/ci.yml`) — lint is informational, not enforced.

## Import Organization

**Order (observed in `scripts/auth.py`, `generate_fiche_rdv.py`):**
1. Stdlib — `os`, `re`, `json`, `uuid`, `unicodedata`, `datetime`, `pathlib`, `typing`.
2. Third-party — `httpx`, `jwt`, `fastapi`, `pydantic`.
3. Local modules (absolute imports against `scripts/` on `sys.path`) — `from config import ...`, `from safe_logger import log_security`, `from generate_fiche_rdv import safe_filename`.

**Path Aliases:**
- No package namespace; `scripts/` is added to `PYTHONPATH` so modules import flat (`import api_server`, `from db_manager import ...`). This is set in `conftest.py`, `tests/backend/conftest.py`, and CI env (`PYTHONPATH: scripts`).
- Optional imports guarded with `try/except ImportError` + availability flag — `DOCX_AVAILABLE` in `generate_fiche_rdv.py`.

## Error Handling

**Patterns:**
- API/auth layer raises `fastapi.HTTPException` with explicit `status_code` and a **French** `detail` message — `auth.py` returns 401/403/503 with messages like `"Token JWT expiré."`, `"Scope manquant : {scope}"`.
- Specific exception types caught before generic ones — `jwt.ExpiredSignatureError`, `jwt.ImmatureSignatureError`, `jwt.InvalidAudienceError`, then `jwt.PyJWTError`.
- Fail-fast on missing config: `config.py` / `api_server.py` raise at import time if `TENANT_ID` / `CLIENT_ID` are absent (tests inject stubs in conftest to bypass).
- Input is validated and sanitized at the boundary — `_validate_document_id` rejects non-UUIDs (400) and unknown IDs (404); `safe_filename` allowlists characters and falls back to `client_inconnu`.
- Library-unavailable conditions raise `ImportError` with an actionable French message (install instructions).

## Logging

**Framework:** stdlib `logging` (logger named `"AC360"`, level INFO) wrapped by `scripts/safe_logger.py`.

**Patterns:**
- **Never log raw input.** All security/audit messages pass through `redact()` before being written — strips ANSI, masks secrets (JWT/Bearer/API keys/connection strings), masks PII (emails, IBAN, long digit sequences), removes control chars (anti log-injection), truncates to `MAX_LEN = 800`.
- Use `log_security(level, message, data=None)` with level strings `"INFO"`, `"WARNING"`, `"ERROR"` (anything else → debug).
- Subprocess stderr/stdout MUST be redacted before persisting to `audit_logs.details` (enforced by `tests/backend/test_safe_logger_redaction.py`).
- Mask markers are cp1252-safe for console — `[SECRET_MASQUÉ]`, `[EMAIL_MASQUÉ]`, `[PII_MASQUÉE]`.

## Comments

**When to Comment:**
- French inline comments explain *why*, especially around security-sensitive steps (`# Sanitisation du nom client avant usage dans le chemin`, `# Interdire '..' explicitement`).
- Security controls reference their requirement IDs — `(P0-05)`, Red-Team IDs `RT-01..RT-20`, baseline sections (`SECURITY_BASELINE.md §6.1`).

**Docstrings:**
- Module-level triple-quoted docstrings (French) describe purpose, rationale, and compliance context.
- Function docstrings describe behaviour and security guarantees as bullet lists.
- No formal JSDoc/Sphinx tooling; free-form French prose.

## Function Design

**Size:** Small, single-responsibility functions. Validation/sanitization isolated into dedicated helpers (`safe_filename`, `_validate_document_id`, `redact`).

**Parameters:** Keyword args with defaults for optionals — `def safe_filename(name, max_length=64)`, `generate_fiche_rdv(client_name, summary, alert_points, job_id=None)`. `job_id` defaults to a fresh `uuid.uuid4()` when `None`.

**Return Values:** Typed returns; auth returns the validated `upn` string. Sanitizers always return a safe non-empty value (fallback constants).

## Module Design

**Exports:** Explicit `__all__` used where the public surface matters — `safe_logger.py` declares `["redact", "MAX_LEN", "logger", "log_security"]`.

**Barrel Files:** Not used. `scripts/__init__.py` exists but modules are imported flat via `PYTHONPATH=scripts`.

## Security-First Conventions (project-specific)

These are enforced by tests and CI, and must be honored by all new code:
- Never set `verify_signature=False` (JWT) — RT-11.
- Never hardcode secrets; read config via `os.getenv(...)` — RT-12, RT-13.
- Never use `Invoke-Expression` in PowerShell; avoid hardcoded `ExecutionPolicy Bypass` reachable from the API — RT-14, RT-15.
- Always sanitize filenames/paths before filesystem use — P0-05 / `safe_filename`.
- Always `redact()` before logging or persisting subprocess output.
- No client data files (`.docx`, `.xlsx`, `.csv`, `.xls`) committed under `scripts/` — RT-20 (RGPD).
- `useModelKnowledge: false` and `contentModeration: High` required in Copilot settings — RT-01, RT-02.

---

*Convention analysis: 2026-06-08*
