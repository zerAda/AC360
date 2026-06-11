"""Wave 6 — garde anti-régression sur les VRAIES règles de sécurité du bot.

Les règles anti-injection / sourcing / refus vivent dans le *system prompt*
(`agent.mcs.yml → instructions`). Les tests red-team historiques balayaient les
topics et ne lisaient JAMAIS ce fichier : une garde pouvait être supprimée du
prompt système sans qu'aucun test ne casse. Ce test ferme cette lacune.
"""
import os

import pytest
import yaml

_AGENT = os.path.join(os.path.dirname(__file__), "..", "..",
                      "src", "copilot", "AC360", "agent.mcs.yml")


def _instructions() -> str:
    with open(_AGENT, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return (data.get("instructions") or "").lower()


# Règle -> sous-chaîne probante attendue dans le system prompt.
REQUIRED_RULES = {
    "refus_connaissances_generales": "connaissances générales",
    "sourcing_citations_obligatoires": "cite",
    "non_confirmation_ressource_inaccessible": "n'a pas accès",
    "anti_melange_clients": "deux clients",
    "contenu_document_non_fiable": "non fiable",
    "anti_revelation_prompt_systeme": "prompt système",
    "refus_avis_juridique_definitif": "juridique",
    "refus_promesse_commerciale_non_sourcee": "promesse",
    "lecture_seule_pas_de_modif_suppression": "supprimes",
}


@pytest.mark.parametrize("rule,needle", sorted(REQUIRED_RULES.items()))
def test_agent_guardrail_present_in_system_prompt(rule, needle):
    instructions = _instructions()
    assert needle in instructions, (
        f"Règle de sécurité « {rule} » absente du system prompt agent.mcs.yml "
        f"(sous-chaîne attendue : '{needle}'). Une garde a-t-elle été supprimée ?")


def test_system_prompt_is_non_trivial():
    # Un prompt vidé/raccourci doit faire échouer le gate.
    assert len(_instructions()) > 500
