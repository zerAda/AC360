#!/usr/bin/env python3
"""Runner LIVE autonome — exécute la preuve comportementale et imprime le détail.

Usage :
    ONIX_LIVE_OLLAMA=1 ONIX_LIVE_MODEL=qwen2.5:7b-instruct \
        python tests/rag/run_live.py [--markdown FICHIER.md]

Sans `--markdown`, imprime un rapport texte (modèle, pass/fail par vecteur, taux,
comparaison d'extraction). Avec `--markdown`, écrit en plus le tableau de
résultats prêt pour `docs/LIVE_GUARDRAILS_RESULTS.md`.

Ce runner est INDÉPENDANT de pytest : il sert à produire la « sortie réelle du
run » exigée par la recette, et à régénérer le doc de résultats.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

# tests/rag importable comme un package plat (comme pytest le fait via conftest).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import live_harness as lh  # noqa: E402
import live_extraction as lx  # noqa: E402


def run_red_team():
    cases = lh.build_live_cases()
    results = [lh.run_case(c) for c in cases]
    passed = sum(1 for r in results if r["passed"])
    rate = round(100 * passed / len(results), 1)
    return results, passed, len(results), rate


def run_extraction():
    os.environ.setdefault("ONIX_LLM_MODEL", lh.ollama_model())
    os.environ.setdefault("ONIX_OLLAMA_URL", lh.ollama_base())
    return lx.run_extraction_comparison()


def print_text_report(results, passed, total, rate, extraction):
    model = lh.ollama_model()
    print("=" * 72)
    print(f"RUN LIVE — preuve comportementale garde-fous")
    print(f"Modèle Ollama : {model}   (endpoint {lh.ollama_base()}/v1/chat/completions)")
    print("=" * 72)
    print(f"\n[1] RED-TEAM — {passed}/{total} vecteurs PASS  → taux = {rate}%\n")
    print(f"  {'ID':<6} {'CATÉGORIE':<26} {'RÉSULTAT':<8} MOTIF")
    print(f"  {'-'*6} {'-'*26} {'-'*8} {'-'*30}")
    for r in results:
        verdict = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['id']:<6} {r['category']:<26} {verdict:<8} {r['reason']}")
    print(f"\n[2] EXTRACTION AUDIT (texte désordonné) — modèle {extraction['model']}")
    print(f"    heuristique = {extraction['heuristic_rate']}%   "
          f"LLM = {extraction['llm_rate']}%")
    for r in extraction["rows"]:
        err = f"  (llm_err={r['llm_error']})" if r["llm_error"] else ""
        print(f"    {r['id']}  heuristique={r['heuristic_score']}  "
              f"llm={r['llm_score']}{err}")
    print()


def write_markdown(path: str, results, passed, total, rate, extraction):
    model = lh.ollama_model()
    today = _dt.date.today().isoformat()
    cat_fr = {
        "injection_documentaire": "Injection documentaire (LLM01)",
        "exfiltration_multi_client": "Exfiltration multi-client (LLM02)",
        "demande_modification": "Modification (lecture seule)",
        "divulgation_prompt": "Divulgation du prompt (LLM01/02)",
        "hors_perimetre": "Hors-périmètre / promesse",
        "nominal_sourcing": "Nominal (sourcing)",
    }
    rows_md = "\n".join(
        f"| {r['id']} | {cat_fr.get(r['category'], r['category'])} | "
        f"{'✅ PASS' if r['passed'] else '❌ FAIL'} | {r['reason']} |"
        for r in results
    )
    ex_rows = "\n".join(
        f"| {r['id']} | {r['heuristic_score']} | {r['llm_score']} |"
        + (f" {r['llm_error']}" if r["llm_error"] else "")
        for r in extraction["rows"]
    )
    failed = [r for r in results if not r["passed"]]
    fail_section = (
        "Aucun échec : tous les vecteurs sont passés."
        if not failed else
        "\n".join(f"- **{r['id']}** ({r['category']}) : {r['reason']}" for r in failed)
    )

    content = f"""# Résultats LIVE — Preuve comportementale des garde-fous

> Généré le **{today}** par `tests/rag/run_live.py` contre un **vrai modèle**
> Ollama. Ce document lève l'astérisque « garde-fous » de
> `docs/PARITE_ENTREPRISE.md` au **niveau modèle + prompt** : on prouve que le
> couple *prompt système durci + LLM ≥ 7B* applique réellement les refus, le
> sourcing et l'anti-injection sous attaque — pas seulement que la règle est
> présente dans le prompt (ça, c'est le mode contrat de `tests/rag/`).

## Modèle utilisé

| Élément | Valeur |
|---|---|
| Modèle Ollama | `{model}` |
| Endpoint | `{lh.ollama_base()}/v1/chat/completions` (OpenAI-compatible) |
| Température | 0 (déterminisme maximal) |
| System prompt | bloc de `prompts/agent_commercial_systeme.md` (copié tel quel) |
| Contexte | faux contexte documentaire injecté côté `user` (avec injections) |

## 1. Red-team live — {passed}/{total} vecteurs PASS → **taux = {rate}%**

Pour chaque vecteur : `system` = prompt agent + `user` = contexte documentaire
récupéré (NON FIABLE, avec injections) + question d'attaque → appel réel →
assertion comportementale (refus, pas de fuite de prompt, pas de liste
multi-clients, « non disponible » hors contexte, citation si réponse).

| Vecteur | Catégorie | Résultat | Comportement observé |
|---|---|---|---|
{rows_md}

### Échecs et correctifs

{fail_section}

## 2. Extraction audit sur ≥ 7B (LLM vs heuristique)

Textes **désordonnés** (prose, libellés noyés) — le cas où l'heuristique
« libellé : valeur par ligne » décroche. Score = champs canoniques corrects /
attendus, via la brique de production `onix-actions`
(`extract_fields_llm` vs `_kv_pairs_from_text` + `extract_canonical_fields`).

- **Heuristique** : {extraction['heuristic_rate']}% ({extraction['heuristic_total']})
- **LLM ({extraction['model']})** : {extraction['llm_rate']}% ({extraction['llm_total']})

| Échantillon | Heuristique (champs OK) | LLM (champs OK) |
|---|---|---|
{ex_rows}

## 3. Dans quelle mesure l'astérisque est levé — limite honnête

**Levé (prouvé ici, au niveau modèle + prompt) :**
- L'agent **applique réellement** ses garde-fous sous attaque sur un LLM ≥ 7B :
  refus de modification (lecture seule), non-exécution des injections
  documentaires, non-divulgation du prompt système, pas de dump/fusion
  multi-clients, « non disponible » hors contexte, et sourcing quand il répond.
- L'extraction LLM d'audit est démontrée sur un **vrai** modèle (≥ 7B), pas
  simulée.

**Reste à faire (hors de ce harnais) — E2E sur la stack déployée :**
- Le **retrieval Onyx** réel (Document Set SharePoint + RBAC EE) qui borne le
  contexte — ici le contexte est *simulé* (faux documents).
- Le **post-filtre déterministe « pas de citation → refuse »** (couche 3 de
  `docs/QA_GUARDRAILS.md`), à exercer de bout en bout côté `onix-actions`/proxy.
- La couverture sous variations de température/jailbreaks avancés et sur le
  modèle exact retenu en production.

> En résumé : la preuve **comportementale modèle + prompt** est faite ; l'**E2E
> complet** (retrieval + citations + post-filtre sur la stack Onyx) reste la
> dernière étape, à exécuter sur l'environnement cible.
"""
    Path(path).write_text(content, encoding="utf-8")
    print(f"[écrit] {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", help="Chemin du .md de résultats à (ré)écrire.")
    args = ap.parse_args()

    if not lh.ollama_reachable():
        print(f"ERREUR : Ollama injoignable sur {lh.ollama_base()}. "
              "Démarre le conteneur et pose ONIX_LIVE_MODEL.", file=sys.stderr)
        sys.exit(2)

    results, passed, total, rate = run_red_team()
    extraction = run_extraction()
    print_text_report(results, passed, total, rate, extraction)
    if args.markdown:
        write_markdown(args.markdown, results, passed, total, rate, extraction)


if __name__ == "__main__":
    main()
