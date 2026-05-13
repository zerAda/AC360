# Requirements: Application d'Audit PDF/Excel — v2.0

**Defined:** 2026-04-29 (après v1.0)
**Milestone:** v2.0 — Features Avancées
**Core Value:** Fournir une analyse d'audit fiable et rapide en comparant automatiquement les données PDF et Excel, avec identification précise des écarts sur chaque société.

## v2.0 Requirements

### Extraction PDF Robuste (Phase 6) — ✅ Complete

- [x] **PDF-01**: Remplacer l'extraction texte brute par pdfplumber
- [x] **PDF-02**: Extraire les montants PDF de manière fiable (pattern regex + formats multiples)
- [x] **PDF-03**: Gérer les PDF multi-pages (boucle `for page in pdf.pages`)
- [x] **PDF-04**: Associer correctement chaque IBAN à son montant (extraction en un seul passage)

### Export des Résultats (Phase 7) — ✅ Complete

- [x] **EXP-01**: Exporter les résultats d'audit au format Excel (.xlsx)
- [x] **EXP-02**: Exporter les résultats d'audit au format CSV
- [x] **EXP-03**: Exporter un rapport PDF récapitulatif (tableau + statistiques)
- [x] **EXP-04**: Inclure les sociétés sans correspondance dans l'export

### Historique des Audits (Phase 8) — ✅ Complete

- [x] **HIST-01**: Stocker les résultats d'audit dans une base SQLite locale
- [x] **HIST-02**: Afficher la liste des audits précédents
- [x] **HIST-03**: Pouvoir rouvrir/consulter un audit historique
- [x] **HIST-04**: Comparer deux audits successifs pour détecter les évolutions

### Mode Batch (Phase 9) — ✅ Complete

- [x] **BATCH-01**: Traiter plusieurs couples PDF/Excel en file d'attente
- [x] **BATCH-02**: Afficher une progression globale pour le batch
- [x] **BATCH-03**: Exporter un rapport consolidé de tous les audits du batch
- [x] **BATCH-04**: Gérer les erreurs par fichier (continuer si un fichier est corrompu)

### Détection Automatique (Phase 10) — ✅ Complete

- [x] **AUTO-01**: Détecter automatiquement les colonnes pertinentes dans l'Excel (Société, Montant)
- [x] **AUTO-02**: Détecter automatiquement le format du PDF (couvert par Phase 6 pdfplumber)
- [x] **AUTO-03**: Fallback automatique si la détection par mots-clés échoue

## v1 Requirements (Déjà validés — voir milestones/v1.0-REQUIREMENTS.md)

Toutes les exigences v1 (UI-01 à UI-05, PERF-01 à PERF-03, DATA-01 à DATA-05, FILT-01 à FILT-05, CALC-01 à CALC-06, POST-01 à POST-04) sont satisfaites et archivées dans `.planning/milestones/v1.0-REQUIREMENTS.md`.

## Out of Scope (v2.0)

| Feature | Reason |
|---------|--------|
| Intégration API bancaire | Hors périmètre — PDF manuel |
| Multi-langue | Français uniquement (métier) |
| Modification des données Excel | Audit comparatif uniquement |
| Alertes email/SMS | Pas demandé par le métier |
| Cloud / Synchronisation | Application desktop locale |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PDF-01 | Phase 6 | ⏳ Planned |
| PDF-02 | Phase 6 | ⏳ Planned |
| PDF-03 | Phase 6 | ⏳ Planned |
| PDF-04 | Phase 6 | ⏳ Planned |
| EXP-01 | Phase 7 | ⏳ Planned |
| EXP-02 | Phase 7 | ⏳ Planned |
| EXP-03 | Phase 7 | ⏳ Planned |
| EXP-04 | Phase 7 | ⏳ Planned |
| HIST-01 | Phase 8 | ⏳ Planned |
| HIST-02 | Phase 8 | ⏳ Planned |
| HIST-03 | Phase 8 | ⏳ Planned |
| HIST-04 | Phase 8 | ⏳ Planned |
| BATCH-01 | Phase 9 | ⏳ Planned |
| BATCH-02 | Phase 9 | ⏳ Planned |
| BATCH-03 | Phase 9 | ⏳ Planned |
| BATCH-04 | Phase 9 | ⏳ Planned |
| AUTO-01 | Phase 10 | ⏳ Planned |
| AUTO-02 | Phase 10 | ⏳ Planned |
| AUTO-03 | Phase 10 | ⏳ Planned |

**Coverage:**
- v2 requirements: 19 total
- Satisfied: 0
- Planned: 19
- Unmapped: 0

---
*Requirements defined: 2026-04-29 for v2.0 milestone*
