#!/usr/bin/env python3
"""validate_copilot_yaml.py — Validates Copilot Studio YAML files for AC360."""
import sys
import yaml
from pathlib import Path

COPILOT_ROOT = Path(__file__).parent.parent / "src" / "copilot" / "AC360"

RAG_KIND = "SearchAndSummarizeContent"
CONDITION_KIND = "ConditionGroup"

KNOWN_BAD_GATEWAY_HOSTS = ("ac360-api.azurewebsites.net",)
STUB_MARKERS = ("en cours de déploiement", "bientôt disponible", "coming soon")
POC_MARKERS = ("dans ce poc", "client alpha", "client beta", "client gamma")
DEFAULT_RAG_VARIABLE = "Topic.Answer"

# Modération exigée sur chaque nœud RAG (cohérence avec settings.mcs.yml
# contentModeration: High — pas de point bas sur les topics à fort trafic).
RAG_REQUIRED_MODERATION = "High"
# Artefacts dev/POC interdits dans les instructions de nœud d'un produit premium.
DEV_ARTIFACT_MARKERS = ("- dev", "dans ce poc", "client alpha", "client beta", "client gamma")


def _walk_actions(actions):
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
    issues = []
    if not isinstance(data, dict):
        return issues
    begin = data.get("beginDialog")
    if not isinstance(begin, dict):
        return issues
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


def find_rag_node_issues(data):
    """Pour chaque SearchAndSummarizeContent : modération High exigée (cohérent
    avec settings contentModeration: High) et aucune trace dev/POC dans les
    instructions de nœud. Liste vide = OK."""
    issues = []
    if not isinstance(data, dict):
        return issues
    begin = data.get("beginDialog")
    if not isinstance(begin, dict):
        return issues
    for act in _walk_actions(begin.get("actions")):
        if act.get("kind") != RAG_KIND:
            continue
        level = str(act.get("moderationLevel", "")).strip()
        if not level:
            issues.append("SearchAndSummarizeContent sans moderationLevel explicite "
                          "(exiger High)")
        elif level != RAG_REQUIRED_MODERATION:
            issues.append(f"SearchAndSummarizeContent en moderationLevel '{level}' "
                          f"(exigé : {RAG_REQUIRED_MODERATION})")
        instr = str(act.get("additionalInstructions", "")).lower()
        for m in DEV_ARTIFACT_MARKERS:
            if m in instr:
                issues.append(f"instructions de nœud : artefact dev/POC « {m} »")
    return issues


def validate_all():
    ok, ko = [], []
    rag_ko = []  # (filename, variable, issue)
    wiring_ko = []  # (filename, issue)
    moderation_ko = []  # (filename, issue)
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
                for issue in find_rag_node_issues(data):
                    moderation_ko.append((yml_file.name, issue))
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

    print("")
    print("=== Contrôle modération RAG (High) + artefacts dev/POC ===")
    if moderation_ko:
        for name, issue in moderation_ko:
            print(f"  [KO]  {name} -> {issue}")
    else:
        print("  [OK]  Tous les nœuds RAG en modération High, sans artefact dev/POC.")
    print("")
    print(f"Résultat modération : {len(moderation_ko)} KO")

    if ko or rag_ko or wiring_ko or moderation_ko:
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
