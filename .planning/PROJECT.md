# Application d'Audit PDF/Excel

## What This Is

Application d'audit automatisée qui compare des données bancaires (fichiers PDF de bordereaux de virements) avec des données de suivi interne (fichiers Excel). L'application identifie les écarts entre les deux sources pour réconcilier les transactions de prévoyance.

L'application lit les PDF de bordereaux de virements bancaires et les compare aux Excel de suivi des règlements pour détecter les montants manquants ou en excès.

## Core Value

Fournir une analyse d'audit fiable et rapide en comparant automatiquement les données PDF et Excel, avec identification précise des écarts sur chaque société.

## Requirements

### Validated (v1.0)

- ✓ Bouton pour annuler l'audit en cours — v1.0
- ✓ Barre de progression affichant le % d'avancement — v1.0
- ✓ L'audit peut être interrompu à tout moment — v1.0
- ✓ Vidage des fichiers PDF et Excel après audit terminé — v1.0
- ✓ Algorithmes optimisés (traitement en < 30s pour 50+ virements) — v1.0
- ✓ Dissociation nom société et IBAN — v1.0
- ✓ Gérer les différences de nom entre PDF et Excel — v1.0
- ✓ Ignorer les lignes de récap/sommes par groupe Excel — v1.0
- ✓ Ignorer les lignes contenant "bordereau" — v1.0
- ✓ Total d'écart Excel cohérent avec Dashboard — v1.0
- ✓ Source de vérité : PDF (seuil fuzzy 75%) — v1.0
- ✓ Interface utilisateur en français — v1.0

### Active (v2.0)

- [ ] Export des résultats d'audit (PDF, Excel, CSV)
- [ ] Historique des audits précédents
- [ ] Mode batch (traitement de plusieurs audits en file d'attente)
- [ ] Détection automatique des colonnes Excel
- [ ] Comparaison multi-PDF (plusieurs bordereaux)

### Out of Scope

- Intégration avec d'autres sources de données (CRM, ERP)
- Modification des fichiers source originaux
- Historique multi-audits (un audit à la fois) — *revisité: v2.0 inclura historique*
- Support multi-langue (français uniquement)

## Context

Les gestionnaires de prévoyance utilisent des bordereaux de virements bancaires (PDF) et des fichiers Excel de suivi. Le processus manuel de comparaison est long et sujet aux erreurs. Les PDF contiennent les virements réels effectués par la banque, tandis que les Excel contiennent le suivi interne des règlements.

**v1.0 shipped with:**
- ~550 LOC Python (Tkinter UI + core logic)
- Tech stack: Python 3, Tkinter, pandas, openpyxl, difflib
- Performance: O(n) matching avec index de noms normalisés
- 28/28 v1 requirements satisfied

**Known issues:**
- Extraction PDF dépend de pdftotext ou lecture texte brute — besoin d'une bibliothèque PDF robuste
- Association montants PDF par position dans le texte — fragile si format change
- Sociétés sans correspondance non affichées dans le tableau

## Constraints

- **Langue :** Français uniquement
- **Source de vérité :** PDF (bordereau bancaire)
- **Seuil correspondance noms :** 75% (fuzzy matching)
- **Tech Stack :** Python + Tkinter
- **Performance :** < 30 secondes pour 50+ virements
- **Sécurité :** Ne jamais supprimer les fichiers source originaux (uniquement les copies uploadées dans le répertoire projet)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Source de vérité = PDF | Le PDF est le bordereau bancaire officiel | ✅ Validated v1.0 |
| Seuil fuzzy = 75% | Valide par le métier pour tolérer les variantes de noms | ✅ Validated v1.0 |
| Écart = Excel − PDF | Montre si Excel a plus ou moins que la réalité bancaire | ✅ Validated v1.0 |
| Interface en français | Utilisateurs francophones | ✅ Validated v1.0 |
| Exclure lignes "bordereau" | Ce sont des tests/calculs des gestionnaires | ✅ Validated v1.0 |
| Algorithme O(n) avec index | Performance critique pour 50+ virements | ✅ Validated v1.0 |
| Suppression sécurisée des fichiers | Ne pas supprimer les fichiers utilisateur originaux | ✅ Validated v1.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2026-04-29 after v1.0 milestone completion*
