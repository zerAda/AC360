import os
import re

# Patterns simplifiés pour le test
SECRET_PATTERNS = [
    re.compile(r"secret\s*[:=]\s*[`\"']([^`\"']{10,})[`\"']", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*[`\"']([^`\"']{8,})[`\"']", re.IGNORECASE),
    re.compile(r"bearer\s+([A-Za-z0-9\-\._~\+\/]+=*)", re.IGNORECASE),
    re.compile(r"apikey\s*[:=]\s*[`\"']([^`\"']{10,})[`\"']", re.IGNORECASE)
]

ALLOWED_EXTENSIONS = {".py", ".json", ".yml", ".ps1"}
EXCLUDED_DIRS = {".git", "__pycache__", "jobs", "Archives_Documentaires",
                 ".mypy_cache", ".pytest_cache", ".venv", "venv", "node_modules"}


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_no_plaintext_secrets():
    root = get_project_root()
    found_secrets = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Exclude directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        for f in filenames:
            _, ext = os.path.splitext(f)
            if ext.lower() not in ALLOWED_EXTENSIONS:
                continue

            filepath = os.path.join(dirpath, f)
            rel_path = os.path.relpath(filepath, root)

            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()
                    for pattern in SECRET_PATTERNS:
                        if pattern.search(content):
                            # Skip placeholders like ${SECRET} or variables
                            # Basic check for now
                            if "${" not in content and "<" not in content:
                                found_secrets.append(rel_path)
            except Exception:
                pass  # ignore read errors on binary/weird files

    # On autorise le fichier de test lui-même et les mocks/exemples
    found_secrets = [
        f for f in found_secrets
        if not f.endswith("test_no_plaintext_secrets.py") and not f.endswith(".example")
    ]

    assert len(found_secrets) == 0, f"Des potentiels secrets ont été trouvés dans : {found_secrets}"
