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


def validate_all():
    ok, ko = [], []
    rag_ko = []  # (filename, variable, issue)
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
        except yaml.YAMLError as e:
            ko.append((yml_file.name, str(e)[:120]))
        except Exception as e:
            ko.append((yml_file.name, f"Erreur lecture: {e}"))

    print(f"\n=== Validation YAML Copilot Studio ===")
    print(f"Répertoire : {COPILOT_ROOT}")
    print(f"")
    for name in ok:
        print(f"  [OK]  {name}")
    for name, err in ko:
        print(f"  [KO]  {name} -> {err}")
    print(f"")
    print(f"Résultat YAML : {len(ok)} OK / {len(ko)} KO")

    print(f"")
    print(f"=== Contrôle anti-silent-RAG ===")
    if rag_ko:
        for name, var, issue in rag_ko:
            print(f"  [KO]  {name} ({var}) -> {issue}")
    else:
        print(f"  [OK]  Aucune topic RAG silencieuse détectée.")
    print(f"")
    print(f"Résultat RAG : {len(rag_ko)} KO")

    if ko or rag_ko:
        print("\n[ECHEC] Validation Copilot Studio en échec.")
        sys.exit(1)
    else:
        print("\n[SUCCES] Tous les fichiers YAML sont valides et sans silent-RAG.")
        sys.exit(0)


if __name__ == "__main__":
    validate_all()
