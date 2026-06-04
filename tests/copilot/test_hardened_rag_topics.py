"""Regression tests for the anti-hallucination guardrails of the two RAG topics
that were hardened to match the other RAG topics (Rsumdossierclient,
Pointsattentionclient, ...).

Asserts both target topics:
  - declare an explicit ``variable: Topic.Answer`` on their RAG node,
  - set ``moderationLevel: High``,
  - display the generated answer (``SendActivity`` referencing ``{Topic.Answer}``),
  - provide an ``elseActions`` fallback for the blank-answer case,
  - and produce no ``find_silent_rag()`` findings.

Also pins the validator behaviour: a ``SearchAndSummarizeContent`` node without an
explicit ``variable:`` is treated as producing the implicit ``Topic.Answer`` and is
flagged when its blank case is unhandled.
"""
import importlib.util
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TOPICS_DIR = REPO_ROOT / "src" / "copilot" / "AC360" / "topics"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_copilot_yaml.py"

TARGET_TOPICS = [
    "Argumentsdevente.mcs.yml",
    "PreparationRDVRenouvellement.mcs.yml",
]


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_copilot_yaml", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _load_topic(name):
    with open(TOPICS_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _all_actions(data):
    return list(validator._walk_actions(data.get("beginDialog", {}).get("actions")))


def _rag_nodes(data):
    return [a for a in _all_actions(data) if a.get("kind") == validator.RAG_KIND]


@pytest.mark.parametrize("topic", TARGET_TOPICS)
def test_rag_node_declares_explicit_answer_variable(topic):
    data = _load_topic(topic)
    rag = _rag_nodes(data)
    assert rag, f"{topic}: aucun nœud SearchAndSummarizeContent trouvé"
    for node in rag:
        assert node.get("variable") == "Topic.Answer", (
            f"{topic}: le nœud RAG doit déclarer explicitement variable: Topic.Answer"
        )


@pytest.mark.parametrize("topic", TARGET_TOPICS)
def test_rag_node_moderation_high(topic):
    data = _load_topic(topic)
    for node in _rag_nodes(data):
        assert node.get("moderationLevel") == "High", (
            f"{topic}: le nœud RAG doit avoir moderationLevel: High"
        )


@pytest.mark.parametrize("topic", TARGET_TOPICS)
def test_answer_is_displayed(topic):
    data = _load_topic(topic)
    displayed = any(
        a.get("kind") == "SendActivity" and "{Topic.Answer}" in str(a.get("activity", ""))
        for a in _all_actions(data)
    )
    assert displayed, (
        f"{topic}: la réponse {{Topic.Answer}} doit être affichée via SendActivity"
    )


@pytest.mark.parametrize("topic", TARGET_TOPICS)
def test_blank_answer_has_fallback(topic):
    data = _load_topic(topic)
    groups = [a for a in _all_actions(data) if a.get("kind") == "ConditionGroup"]
    guarded_with_fallback = any(
        any("Topic.Answer" in str(c.get("condition", "")) for c in (g.get("conditions") or []))
        and g.get("elseActions")
        for g in groups
    )
    assert guarded_with_fallback, (
        f"{topic}: la condition IsBlank(Topic.Answer) doit avoir une branche elseActions"
    )


@pytest.mark.parametrize("topic", TARGET_TOPICS)
def test_no_silent_rag_findings(topic):
    data = _load_topic(topic)
    assert validator.find_silent_rag(data) == [], (
        f"{topic}: find_silent_rag a détecté un problème"
    )


def test_whole_copilot_tree_has_no_silent_rag():
    """The full Copilot tree must be free of silent-RAG topics."""
    findings = []
    for yml in sorted(validator.COPILOT_ROOT.rglob("*.yml")):
        with open(yml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            continue
        for var, issue in validator.find_silent_rag(data):
            findings.append((yml.name, var, issue))
    assert findings == [], f"silent-RAG détecté: {findings}"


def test_validator_detects_implicit_silent_rag():
    """A RAG node WITHOUT explicit variable: whose blank case lacks an elseActions
    fallback must be flagged — the implicit Topic.Answer is now tracked."""
    silent = {
        "beginDialog": {
            "actions": [
                {"kind": "SearchAndSummarizeContent", "id": "x"},  # implicit Topic.Answer
                {
                    "kind": "ConditionGroup",
                    "id": "g",
                    "conditions": [
                        {
                            "condition": "=!IsBlank(Topic.Answer)",
                            "actions": [
                                {"kind": "SendActivity", "activity": "{Topic.Answer}"}
                            ],
                        }
                    ],
                    # no elseActions -> blank result is silent
                },
            ]
        }
    }
    findings = validator.find_silent_rag(silent)
    assert findings, "find_silent_rag doit détecter le silent-RAG implicite (Topic.Answer)"
    assert any(var == "Topic.Answer" for var, _ in findings)


def test_validator_detects_unguarded_rag():
    """A RAG node whose variable is never guarded by an IsBlank() condition is
    silent-RAG."""
    unguarded = {
        "beginDialog": {
            "actions": [
                {"kind": "SearchAndSummarizeContent", "id": "x", "variable": "Topic.Answer"},
            ]
        }
    }
    assert validator.find_silent_rag(unguarded), "RAG non gardé doit être détecté"
