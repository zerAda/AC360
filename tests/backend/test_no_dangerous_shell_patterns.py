import os
import re
import pytest

DANGEROUS_PATTERNS = [
    re.compile(r"Invoke-Expression", re.IGNORECASE),
    re.compile(r"iex\s", re.IGNORECASE)
]

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_no_dangerous_shell_patterns():
    root = get_project_root()
    found_dangerous = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
            
        for f in filenames:
            if f.endswith(".ps1"):
                filepath = os.path.join(dirpath, f)
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()
                    for pattern in DANGEROUS_PATTERNS:
                        if pattern.search(content):
                            found_dangerous.append(f)
                            
    assert len(found_dangerous) == 0, f"Des patterns PowerShell dangereux ont été trouvés dans : {found_dangerous}"
