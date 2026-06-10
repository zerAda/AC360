#!/usr/bin/env python3
"""validate_copilot_yaml.py — Validates all Copilot Studio YAML files in AC360.

Two checks are performed for every ``*.yml`` under ``src/copilot/AC360`` :
  1. YAML well-formedness (the file parses and is not empty).
  2. Anti-"silent RAG" — every ``SearchAndSummarizeContent`` node must guard its
     generated answer with an ``IsBlank()`` ``ConditionGroup`` that has an
     ``elseActions`` fallback, otherwise a blank search result is never surfaced
     to the user (silent failure / missing display).
"""
import sys
import yaml
from pathlib import Path

COPILOT_ROOT = Path(__file__).parent.parent / "src" / "copilot" / "AC360"

RAG_KIND = "SearchAndSummarizeContent"
CONDITION_KIND = "ConditionGroup"

# Hôtes de passerelle morts / placeholder : une action HTTP qui les vise échoue
# à l'exécution (DNS/404). Le seul hôte de passerelle déployé est
# ac360-gateway-staging. Anti-régression sur des URLs hardcodées erronées.
KNOWN_BAD_GATEWAY_HOSTS = ("ac360-api.azurewebsites.net",)
# Marqueurs de « topic stub » : une rubrique métier qui annonce une
# fonctionnalité « bientôt disponible » au lieu de l'exécuter = non câblée.
STUB_MARKERS = ("en cours de déploiement", "bientôt disponible", "coming soon")
# Artefacts « POC » qui n'ont pas leur place dans un produit premium : le mot
# « POC » dans un texte utilisateur, et les faux clients de test ALPHA/BETA/GAMMA
# (polluent le NLU + non professionnels). Vérifié dans les textes et triggers.
POC_MARKERS = ("dans ce poc", "client alpha", "client beta", "client gamma")
# Default variable a SearchAndSummarizeContent node writes to when no explicit
# `variable:` is declared. Copilot Studio binds the generated answer to
# Topic.Answer implicitly, so we must reason about it the same way.
DEFAULT_RAG_VARIABLE = "Topic.Answer"


def _walk_actions(actions):
    """Recursively yield every action dict within an AdaptiveDialog action list,
    descending into ConditionGroup ``conditions[].actions`` and ``elseActions``."""
    for act in actions or []:
        if not isinstance(act, dict):
            continue
        yield act
        for cond in act.get("conditions", []) or []:
            if isinstance(cond, dict):
                yield from _walk_actions(cond.get("actions"))
        yield from _walk_actions(act.get("elseActions"))
        # Defensive: some action kinds may nest a plain `actions` list.
        if act.get("kind") != CONDITION_KIND:
            yield from _walk_actions(act.get("actions"))


def find_silent_rag(data):
    """Return a list of (variable, issue) tuples describing silent-RAG problems.

    A ``SearchAndSummarizeContent`` node produces an answer variable — either its
    explicit ``variable:`` or, when that key is absent, the implicit
    ``Topic.Answer``. The answer is considered safely surfaced only when a
    ``ConditionGroup`` tests ``IsBlank(<variable>)`` AND provides an
    ``elseActions`` branch (so the blank case still sends a message). Anything
    else is a silent failure / missing display. An empty list means OK.
    """
    issues = []
    if not isinstance(data, dict):
        return issues
    begin = data.get("beginDialog")
    if not isinstance(begin, dict):
        return issues

    all_actions = list(_walk_actions(begin.get("actions")))

    # Every variable produced by a RAG node (explicit or implicit Topic.Answer).
    rag_vars = []
    for act in all_actions:
        if act.get("kind") == RAG_KIND:
            rag_vars.append(act.get("variable") or DEFAULT_RAG_VARIABLE)

    for var in rag_vars:
        guarded = False
        has_fallback = False
        for act in all_actions:
            if act.get("kind") != CONDITION_KIND:
                continue
            conds = act.get("conditions", []) or []
            if not any(
                isinstance(c, dict) and var in str(c.get("condition", ""))
                for c in conds
            ):
                continue
            guarded = True
            if act.get("elseActions"):  # non-empty list
                has_fallback = True
        if not guarded:
            issues.append(
                (var, "réponse RAG produite mais jamais protégée par une condition "
                      "IsBlank() (silent RAG)")
            )
        elif not has_fallback:
            issues.append(
                (var, "condition IsBlank() sans branche elseActions — un résultat "
                      "vide n'affiche aucun message (échec silencieux)")
            )
    return issues


def find_wiring_issues(data):
    """Détecte les défauts de câblage end-to-end : action HTTP vers un hôte mort
    et topic « stub » (annonce au lieu d'exécuter). Liste vide = OK."""
    issues = []
    if not isinstance(data, dict):
        return issues
    begin = data.get("beginDialog")
    if not isinstance(begin, dict):
        return issues
    # Triggers : pas de faux client de test / marqueur POC.
    intent = begin.get("intent") or {}
    for tq in intent.get("triggerQueries", []) or []:
        low = str(tq).lower()
        for m in POC_MARKERS:
            if m in low:
                issues.append(f"trigger contient un artefact POC/test : « {tq} »")
    for act in _walk_actions(begin.get("actions")):
        kind = act.get("kind")
        if kind == "HttpRequestAction":
            url = str(act.get("url", ""))
            for bad in KNOWN_BAD_GATEWAY_HOSTS:
                if bad in url:
                    issues.append(f"HttpRequestAction vise un hôte mort/placeholder : {bad}")
        elif kind == "SendActivity":
            text = str(act.get("activity", "")).lower()
            for marker in STUB_MARKERS:
                if marker in text:
                    issues.append(f"texte de stub détecté (« {marker} ») — fonctionnalité non câblée ?")
            for m in POC_MARKERS:
                if m in text:
                    issues.append(f"texte utilisateur contient un artefact POC/test : « {m} »")
    return issues


def validate_all():
    ok, ko = [], []
    rag_ko = []  # (filename, variable, issue)
    wiring_ko = []  # (filename, issue)
    if not COPILOT_ROOT.exists():
        print(f"[ECHEC] Le répertoire {COPILOT_ROOT} n'existe pas.")
        sys.exit(1)

    for yml_file in sorted(COPILOT_ROOT.rglob("*.yml")):
        try:
            with open(yml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None:
                ko.append((yml_file.name, "Fichier vide ou non YAML"))
            else:
                ok.append(yml_file.name)
                for var, issue in find_silent_rag(data):
                    rag_ko.append((yml_file.name, var, issue))
                for issue in find_wiring_issues(data):
                    wiring_ko.append((yml_file.name, issue))
        except yaml.YAMLError as e:
            ko.append((yml_file.name, str(e)[:120]))
        except Exception as e:
            ko.append((yml_file.name, f"Erreur lecture: {e}"))

    print("\n=== Validation YAML Copilot Studio ===")
    print(f"Répertoire : {COPILOT_ROOT}")
    print("")
    for name in ok:
        print(f"  [OK]  {name}")
    for name, err in ko:
        print(f"  [KO]  {name} -> {err}")
    print("")
    print(f"Résultat YAML : {len(ok)} OK / {len(ko)} KO")

    print("")
    print("=== Contrôle anti-silent-RAG ===")
    if rag_ko:
        for name, var, issue in rag_ko:
            print(f"  [KO]  {name} ({var}) -> {issue}")
    else:
        print("  [OK]  Aucune topic RAG silencieuse détectée.")
    print("")
    print(f"Résultat RAG : {len(rag_ko)} KO")

    print("")
    print("=== Contrôle câblage end-to-end (hôte mort / topic stub) ===")
    if wiring_ko:
        for name, issue in wiring_ko:
            print(f"  [KO]  {name} -> {issue}")
    else:
        print("  [OK]  Aucun hôte mort ni topic stub détecté.")
    print("")
    print(f"Résultat câblage : {len(wiring_ko)} KO")

    if ko or rag_ko or wiring_ko:
        print("\n[ECHEC] Validation Copilot Studio en échec.")
        sys.exit(1)
    elif not ok:
        print("\n[ECHEC] Aucun fichier YAML analysé. Le répertoire est vide ou introuvable.")
        sys.exit(1)
    else:
        print("\n[SUCCES] Tous les fichiers YAML sont valides et sans silent-RAG.")
        sys.exit(0)


if __name__ == "__main__":
    validate_all()
