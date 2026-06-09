"""
Tests Red-Team P0-03 : Topics Copilot Studio ne doivent PAS être silencieux.
Vérifie que chaque topic principal affiche bien Topic.Answer dans son flux de succès.
"""
import os
import yaml
import pytest

TOPICS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "copilot", "AC360", "topics"
)

# Topics principaux qui DOIVENT afficher une réponse
REQUIRED_ANSWER_TOPICS = [
    "Brouillonmailcommercial.mcs.yml",
    "Documentsmanquants.mcs.yml",
    "Pointsattentionclient.mcs.yml",
    "Prparationrendez-vousclient.mcs.yml",
    "Recherchedocumentclient.mcs.yml",
    "Rsumdossierclient.mcs.yml",
    "Argumentsdevente.mcs.yml",
    "AnalyseConcurrence.mcs.yml",
]


def _find_send_activity_in_actions(actions: list) -> bool:
    """Parcourt récursivement les actions pour trouver un SendActivity qui affiche Topic.Answer."""
    for action in actions:
        if not isinstance(action, dict):
            continue
        kind = action.get("kind", "")
        if kind == "SendActivity":
            activity = action.get("activity", "")
            if "Topic.Answer" in str(activity):
                return True
        # Chercher dans les sous-actions (ConditionGroup, etc.)
        for key in ("actions", "elseActions", "conditions"):
            sub = action.get(key, [])
            if isinstance(sub, list):
                if _find_send_activity_in_actions(sub):
                    return True
            elif isinstance(sub, dict):
                # conditions est une liste de dicts avec 'actions'
                for item in sub if isinstance(sub, list) else [sub]:
                    if isinstance(item, dict):
                        inner = item.get("actions", [])
                        if _find_send_activity_in_actions(inner):
                            return True
    return False


@pytest.mark.parametrize("topic_file", REQUIRED_ANSWER_TOPICS)
def test_topic_is_not_silent(topic_file):
    """
    Vérifie qu'un topic principal affiche bien Topic.Answer.
    Un topic silencieux = FAILED : l'utilisateur ne voit jamais la réponse du RAG.
    """
    topic_path = os.path.join(TOPICS_DIR, topic_file)
    assert os.path.exists(topic_path), f"Topic introuvable : {topic_file}"

    # Validation que le YAML est parsable.
    with open(topic_path, "r", encoding="utf-8") as f:
        yaml.safe_load(f)

    # Recherche brute dans le YAML texte (plus fiable que le parsing pour les templates)
    with open(topic_path, "r", encoding="utf-8") as f:
        raw = f.read()

    assert "Topic.Answer" in raw, f"[SILENT] {topic_file} ne contient pas Topic.Answer du tout."

    # Vérifier qu'il y a un SendActivity qui affiche Topic.Answer (pas juste stocké)
    has_display = (
        'activity: "{Topic.Answer}"' in raw
        or "activity: '{Topic.Answer}'" in raw
        or 'activity: "{Topic.Answer}"' in raw
    )  # noqa: W504
    assert has_display, (
        f"[SILENT] {topic_file} stocke Topic.Answer mais ne l'AFFICHE JAMAIS via SendActivity. "
        f"L'utilisateur ne voit pas la réponse."
    )


def test_brouillon_mail_no_mailto():
    """P0-04 : Le topic Brouillonmailcommercial ne doit JAMAIS contenir un lien mailto: automatique."""
    topic_path = os.path.join(TOPICS_DIR, "Brouillonmailcommercial.mcs.yml")
    with open(topic_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # L'instruction qui force la génération d'un lien mailto est interdite
    assert "IMPORTANT : Ajoute systématiquement ce lien" not in raw, (
        "P0-04 OUVERT : Le topic Brouillonmailcommercial contient encore l'instruction "
        "qui force la génération d'un lien mailto: automatique. Risque d'exfiltration de données."
    )
    assert "mailto:" not in raw.lower(), (
        "P0-04 OUVERT : Le topic Brouillonmailcommercial contient un lien mailto: — "
        "vecteur d'exfiltration et risque DLP."
    )
