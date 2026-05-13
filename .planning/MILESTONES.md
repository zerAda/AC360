# MILESTONES.md — Application d'Audit PDF/Excel

---

## v1.0 — MVP Audit PDF/Excel

**Shipped:** 2026-04-29  
**Status:** ✅ Complete  
**Phases:** 5 | **Plans:** 5 | **Tasks:** ~40  
**Requirements:** 28/28 satisfied

### What Shipped

Application Python avec interface Tkinter permettant de :
1. **Uploader** un PDF de bordereau de virements bancaires + un Excel de suivi des règlements
2. **Parser** et nettoyer les données (IBAN/noms dissociés, filtres bordereau/récap/total, normalisation fuzzy)
3. **Matcher** les sociétés entre PDF et Excel avec algorithme O(n) et fallback fuzzy 75%
4. **Calculer** les écarts (Excel − PDF) avec vérification automatique de cohérence des totaux
5. **Afficher** les résultats dans un tableau coloré (OK/Excès/Manque) avec résumé statistique
6. **Contrôler** l'audit (bouton Annuler, barre de progression temps réel)
7. **Réinitialiser** proprement pour un nouvel audit avec suppression sécurisée des fichiers

### Key Accomplishments

1. **Interface UI/UX complète** — Bouton annuler, barre de progression, messages temps réel, tableau de résultats avec couleurs
2. **Nettoyage de données robuste** — Dissociation IBAN/Nom, normalisation des noms (accents, préfixes, suffixes), filtres multi-critères
3. **Algorithme de matching optimisé** — Recherche O(1) par index de noms normalisés + fallback fuzzy difflib.SequenceMatcher
4. **Calcul d'écarts fiable** — Formule Excel − PDF, statuts OK/Excès/Manque, vérification cohérence totaux
5. **Post-audit sécurisé** — Suppression des fichiers uploadés limitée au répertoire projet, réinitialisation complète de l'UI

### Files Delivered

| File | Phase | Description |
|------|-------|-------------|
| `src/core.py` | 2-4 | Parsing PDF/Excel, filtres, normalisation, matching fuzzy, calcul écarts |
| `src/main.py` | 1, 5 | Interface Tkinter, contrôles audit, progression, post-audit |
| `src/requirements.txt` | — | Dépendances (pandas, openpyxl) |

### Decisions Validated

- ✅ Source de vérité = PDF (bordereau bancaire officiel)
- ✅ Seuil fuzzy = 75% (tolérance aux variantes de noms)
- ✅ Écart = Excel − PDF (montre si Excel a plus ou moins que la banque)
- ✅ Interface en français
- ✅ Exclusion des lignes "bordereau" (tests des gestionnaires)

### Gaps Resolved During Audit

| ID | Description | Resolution |
|----|-------------|------------|
| FILT-01 | Filtre récap/sommes incomplet | Normalisation avant filtre (accents) |
| CALC-05 | Cohérence totaux non vérifiée | Vérification automatique total_pdf vs total_excel |
| PERF-01 | Performance non benchmarkée | time.time() + alerte console si > 30s |
| PERF-03 | Mémoire non optimisée | gc.collect() au début de l'audit |
| POST-01 | Fichiers PDF non supprimés | _safe_delete_file() sécurisé |
| POST-02 | Fichiers Excel non supprimés | _safe_delete_file() sécurisé |

### Tech Debt Carried Forward

- **Medium:** Extraction PDF robuste (besoin de pdfplumber/PyMuPDF), association montants PDF améliorée, affichage sociétés sans correspondance
- **Low:** Export résultats, tests unitaires, logs détaillés

### Archive

- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
- [v1.0-MILESTONE-AUDIT.md](v1.0-MILESTONE-AUDIT.md)

---

*Milestones log started: 2026-04-29*
