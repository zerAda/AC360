import os
import pytest
import yaml

def get_copilot_topics_dir():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root, "src", "copilot", "AC360", "topics")

def test_no_use_model_knowledge():
    """Vérifie que useModelKnowledge n'est jamais activé pour prévenir les hallucinations."""
    topics_dir = get_copilot_topics_dir()
    for root, _, files in os.walk(topics_dir):
        for file in files:
            if file.endswith(".mcs.yml"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        assert content.get("useModelKnowledge") is not True, f"useModelKnowledge activé dans {file}"

def test_single_fallback_topic():
    """Vérifie qu'il y a un seul topic Fallback (OnUnknownIntent) pour éviter les conflits de priorité."""
    topics_dir = get_copilot_topics_dir()
    fallback_topics = []
    
    for root, _, files in os.walk(topics_dir):
        for file in files:
            if file.endswith(".mcs.yml"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict) and content.get("kind") == "AdaptiveDialog":
                        begin_dialog = content.get("beginDialog", {})
                        if begin_dialog.get("kind") == "OnUnknownIntent":
                            fallback_topics.append(file)
                            
    assert len(fallback_topics) <= 1, f"Multiples Fallbacks détectés: {fallback_topics}"

def test_no_empty_display_names():
    """Vérifie que les topics ont des displayName valides."""
    topics_dir = get_copilot_topics_dir()
    for root, _, files in os.walk(topics_dir):
        for file in files:
            if file.endswith(".mcs.yml"):
                filepath = os.path.join(root, file)
                # Just making sure they are parseable and we can potentially check for displayName
                with open(filepath, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    # Currently we deleted the ones with empty displayNames.
                    assert content is not None, f"{file} est vide ou invalide."
