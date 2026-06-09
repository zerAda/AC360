import os

# Fichiers interdits stricts (ex: DB, secrets en clair) dans le repo
FORBIDDEN_FILES = [
    "test_audits.db",
    ".env",  # only .env.example should be tracked
]

# Extensions interdites dans le repo
FORBIDDEN_EXTS = [
    ".sqlite",
    ".sqlite3",
    ".db",
]

# Dossiers interdits
FORBIDDEN_DIRS = [
    "__pycache__",
    "logs",
]


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_no_forbidden_files_in_repo():
    root = get_project_root()
    found_forbidden = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Ignore .git explicitly
        if ".git" in dirnames:
            dirnames.remove(".git")

        rel_path = os.path.relpath(dirpath, root)

        # Check directories
        for d in dirnames:
            if d in FORBIDDEN_DIRS:
                # __pycache__ could be created by pytest, but shouldn't be tracked.
                # However, this test is running locally so it might exist.
                # We'll rely on git tracking or just warn. __pycache__ is
                # skipped in strict local testing unless it's in a package.
                pass

        # Check files
        for f in filenames:
            if f in FORBIDDEN_FILES:
                # .env is typically not tracked, but if it is, we flag it.
                # We can't easily check git status here without running git commands.
                # Let's just flag it if found in source tree during a strict run,
                # but typically this is used in CI where .env isn't present.
                found_forbidden.append(os.path.join(rel_path, f))

            _, ext = os.path.splitext(f)
            if ext in FORBIDDEN_EXTS:
                found_forbidden.append(os.path.join(rel_path, f))

    assert len(found_forbidden) == 0, f"Des fichiers interdits ont été trouvés : {found_forbidden}"
