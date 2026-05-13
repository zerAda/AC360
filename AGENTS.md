# AGENTS.md — Application d'Audit PDF/Excel

## Project Context

Application d'audit automatisée qui compare des bordereaux de virements bancaires (PDF) avec des fichiers Excel de suivi des règlements. L'application identifie les écarts entre les deux sources.

**Source de vérité :** PDF (bordereau bancaire)  
**Langue :** Français  
**Seuil correspondance noms :** 75% (fuzzy matching)  
**Formule écart :** Écart = Montant Excel − Montant PDF

## Architecture

```
Utilisateur → Interface (UI/UX)
    ↓
Upload PDF + Excel
    ↓
Parser PDF (extraire IBAN + Nom + Montant)
Parser Excel (extraire Société + Montant)
    ↓
Filtrer (exclure bordereaux, récaps, totaux)
    ↓
Normaliser les noms (supprimer accents, préfixes, suffixes)
    ↓
Correspondance par nom (fuzzy, seuil 75%)
    ↓
Calculer Écart = Excel − PDF (pour chaque match)
    ↓
Afficher Résultats (tableau + résumé)
    ↓
Nettoyage (vider fichiers, réinitialiser)
```

## Technology Stack

- **Language :** [À compléter selon l'existant]
- **PDF Parsing :** [À compléter]
- **Excel Parsing :** [À compléter]
- **UI Framework :** [À compléter]
- **Fuzzy Matching :** difflib.SequenceMatcher (Python) ou équivalent

## Key Files

| File | Purpose |
|------|---------|
| `.planning/PROJECT.md` | Contexte projet |
| `.planning/REQUIREMENTS.md` | 22 exigences v1 |
| `.planning/ROADMAP.md` | 5 phases |
| `.planning/STATE.md` | État courant |
| `.planning/phases/01-ui-ux/PLAN.md` | Phase 1 : UI/UX |
| `.planning/phases/02-data-cleaning/PLAN.md` | Phase 2 : Nettoyage données |
| `.planning/phases/03-performance/PLAN.md` | Phase 3 : Performance |
| `.planning/phases/04-corrections/PLAN.md` | Phase 4 : Calcul écarts |
| `.planning/phases/05-post-audit/PLAN.md` | Phase 5 : Post-audit |

## Data Format

### PDF (Bordereau de virements)
```
Format ligne : [IBAN 27 caractères] [Nom Société]
Exemple : FR76 30003031800002003128252 Sté LAVOLLE CHIMIE
```

### Excel (Suivi règlements)
```
Colonnes : ID | ID+Nom | Prénom | Société | Type | Montant | Statut | Date | Assureur | Commentaires | Code
Exemple : 180024504 | 89959 DEMOUGE | Catherine | ADP GSI FRANCE | IJ | 1 384,39 € | Suite | 17/04/26 | AXA | Contrôle PBE | SA
```

## GSD Workflow

1. **Phase 1** : UI/UX — Bouton annuler + barre progression
2. **Phase 2** : Nettoyage — IBAN/Nom + filtres
3. **Phase 3** : Performance — Algorithmes optimisés
4. **Phase 4** : Écarts — Calcul et correspondance
5. **Phase 5** : Post-Audit — Vidage et réinitialisation

**Current Phase :** Phase 1

## Commands

```
# Voir le plan de la phase courante
cat .planning/phases/01-ui-ux/PLAN.md

# Voir tous les plans
ls .planning/phases/*/

# Voir l'état du projet
cat .planning/STATE.md
```

## Notes

- Les noms de société peuvent différer entre PDF et Excel (préfixes/suffixes)
- Les lignes "bordereau" dans Excel sont des tests de calcul des gestionnaires
- Les lignes "Total" dans le PDF sont des agrégats à exclure
- Le total du bordereau test (N° 10686) est de 92 361,39 € pour 51 virements

---

*AGENTS.md updated: 2026-04-29*
