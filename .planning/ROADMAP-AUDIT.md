# ROADMAP.md — Application d'Audit

**Phases:** 5 | **Requirements:** 22 | **All v1 requirements covered** ✓

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-------------------|
| 1 | UI/UX et Contrôle Audit | Bouton annuler + barre progression | 5 | 4 |
| 2 | Nettoyage de Données | Dissocier société/IBAN, filtres | 8 | 5 |
| 3 | Optimisation Performance | Algorithmes rapides | 3 | 3 |
| 4 | Corrections Écarts | Correspondance Excel/Dashboard | 3 | 3 |
| 5 | Post-Audit | Vidage fichiers + reset | 3 | 3 |

---

## Phase 1: UI/UX et Contrôle Audit

**Goal:** Ajouter le bouton d'annulation et la barre de progression

**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05

**Success Criteria:**

1. Bouton "Annuler" visible et fonctionnel pendant l'audit
2. L'audit s'arrête proprement quand on clique annuler
3. Barre de progression visible avec % d'avancement
4. Progression mise à jour en temps réel
5. Message de confirmation à la fin

---

## Phase 2: Nettoyage de Données

**Goal:** Dissocier société/IBAN, filtrer bordereaux et récaps

**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, FILT-01, FILT-02, FILT-03, FILT-04

**Success Criteria:**

1. Société et IBAN sont séparés avant traitement
2. Les noms de société sont comparés même s'ils diffèrent légèrement
3. Lignes "bordereau" exclues de l'analyse
4. Lignes de récap/sommes Excel exclues
5. Seules les données détaillées sont prises en compte

---

## Phase 3: Optimisation Performance

**Goal:** Accélérer le traitement avec des algorithmes optimisés

**Requirements:** PERF-01, PERF-02, PERF-03

**Success Criteria:**

1. Temps de traitement réduit de manière significative
2. L'interface reste réactive pendant l'audit
3. Pas de surcharge mémoire sur gros volumes

---

## Phase 4: Corrections Écarts

**Goal:** Corriger le total d'écart pour qu'il corresponde entre Excel et Dashboard

**Requirements:** MATCH-01, MATCH-02, MATCH-03

**Success Criteria:**

1. Total écart Excel = Total écran Dashboard
2. Écarts cohérents entre les deux vues
3. Pas de données manquantes ou dupliquées

---

## Phase 5: Post-Audit

**Goal:** Vider les fichiers et permettre un nouvel audit

**Requirements:** POST-01, POST-02, POST-03

**Success Criteria:**

1. PDF uploadés supprimés après audit
2. Excel uploadés supprimés après audit
3. Nouvel audit peut être lancé proprement

---

## Phase Dependencies

```
Phase 1 (UI/UX) ──┬──> Phase 2 (Nettoyage données)
                  │         │
                  │         └─> Phase 3 (Optimisation)
                  │                 │
                  ├────────────────> Phase 4 (Corrections)
                  │                         │
                  └────────────────────────> Phase 5 (Post-Audit)
```

## Coverage

- **v1 requirements:** 22 total
- **Mapped to phases:** 22
- **Unmapped:** 0 ✓

---

*Roadmap created: 2026-04-28*
*Last updated: 2026-04-28 after audit roadmap creation*
