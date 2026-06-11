"""Garde-fou : le validateur exige modération High sur chaque nœud RAG et rejette
les artefacts dev/POC dans les instructions de nœud (anti-régression)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import validate_copilot_yaml as v  # noqa: E402


def _topic(level="High", instr="Tu es Assistant Client 360."):
    node = {"kind": "SearchAndSummarizeContent", "variable": "Topic.Answer",
            "additionalInstructions": instr}
    if level is not None:
        node["moderationLevel"] = level
    return {"beginDialog": {"kind": "OnRecognizedIntent", "actions": [node]}}


def test_high_moderation_passes():
    assert v.find_rag_node_issues(_topic("High")) == []


def test_medium_moderation_flagged():
    issues = v.find_rag_node_issues(_topic("Medium"))
    assert any("Medium" in i for i in issues)


def test_low_moderation_flagged():
    assert any("Low" in i for i in v.find_rag_node_issues(_topic("Low")))


def test_missing_moderation_flagged():
    assert any("sans moderationLevel" in i for i in v.find_rag_node_issues(_topic(None)))


def test_dev_artifact_in_instructions_flagged():
    issues = v.find_rag_node_issues(_topic("High", "Tu es Assistant Client 360 - DEV."))
    assert any("dev/POC" in i for i in issues)


def test_real_tree_all_high_and_clean():
    # L'arbre réel doit passer le contrôle (tous les nœuds RAG en High, sans dev/POC).
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "src" / "copilot" / "AC360"
    total = 0
    for yml in root.rglob("*.yml"):
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        issues = v.find_rag_node_issues(data)
        assert issues == [], f"{yml.name}: {issues}"
        total += 1
    assert total > 20  # garde-fou : l'arbre a bien été parcouru
