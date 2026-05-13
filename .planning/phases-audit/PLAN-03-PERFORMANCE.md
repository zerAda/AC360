# PLAN.md — Phase 3: Optimisation Performance

**Phase:** 3/5 | **Requirements:** 3 | **Status:** Pending

## Goal

Accélérer le traitement avec des algorithmes optimisés.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Algorithme de traitement optimisé | PERF-01 |
| 2 | Traitement asynchrone/non-bloquant | PERF-02 |
| 3 | Gestion mémoire optimisée | PERF-03 |

## Execution Steps

### Step 1: Profiler le Code Actuel

1. Identifier les goulots d'étranglement (boucles lentes, lectures répétées)
2. Mesurer le temps par étape (lecture PDF, lecture Excel, comparaison)
3. Identifier les fonctions les plus lentes

### Step 2: Optimiser la Lecture des Fichiers

1. Lire les fichiers une seule fois en mémoire
2. Utiliser des structures de données adaptées (DataFrame, dict indexé)
3. Éviter les lectures répétées du disque

### Step 3: Optimiser l'Algorithme de Comparaison

1. Utiliser des index (IBAN, date, montant) pour accélérer la recherche
2. Réduire la complexité O(n²) → O(n log n) ou O(n)
3. Utiliser des sets/dictionnaires pour la recherche rapide
4. Regrouper les comparaisons par IBAN ou par société

### Step 4: Traitement Asynchrone/Threading

1. Déplacer le traitement lourd dans un thread séparé
2. Mettre à jour l'UI depuis le thread principal
3. Permettre l'annulation propre du thread

### Step 5: Optimisation Mémoire

1. Traiter les fichiers par chunks si trop volumineux
2. Libérer la mémoire des objets intermédiaires
3. Éviter de garder tout en mémoire si possible

### Step 6: Mesurer les Gains

1. Mesurer le temps avant/après optimisation
2. Vérifier que les résultats sont identiques
3. Documenter les gains de performance

## Algorithmes Recommandés

| Problème | Solution | Complexité |
|----------|----------|------------|
| Recherche correspondance | Index par IBAN + dict | O(n) |
| Comparaison noms | Pre-filter + fuzzy | O(n) |
| Lecture Excel | pandas read_excel (vectorisé) | O(n) |
| Filtrage | Boolean mask (vectorisé) | O(n) |

## Success Criteria

- [ ] Temps de traitement réduit significativement
- [ ] Interface reste réactive
- [ ] Pas de surcharge mémoire
- [ ] Résultats identiques à l'ancien algorithme

## Blockers

(None identified)

---

*Plan created: 2026-04-28*
