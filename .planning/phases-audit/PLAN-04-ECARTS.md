# PLAN.md — Phase 4: Corrections Écarts

**Phase:** 4/5 | **Requirements:** 3 | **Status:** Pending

## Goal

Corriger le total d'écart pour qu'il corresponde entre Excel et Dashboard.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Total écart Excel = Dashboard | MATCH-01 |
| 2 | Écarts cohérents entre vues | MATCH-02 |
| 3 | Pas de données manquantes/dupliquées | MATCH-03 |

## Execution Steps

### Step 1: Auditer le Calcul Actuel

1. Comparer la logique de calcul dans Excel vs Dashboard
2. Identifier les différences de méthode de calcul
3. Vérifier si les filtres (bordereau, récap) affectent le total

### Step 2: Corriger la Logique de Calcul

1. S'assurer que le même ensemble de données est utilisé des deux côtés
2. Vérifier les arrondis (Excel vs code)
3. Vérifier les signes (+/-) des écarts
4. Vérifier les dates de comparaison

### Step 3: Synchroniser Filtres et Calcul

1. S'assurer que les filtres (bordereau, récap) sont appliqués AVANT le calcul
2. Vérifier que les données exclues ne comptent pas dans le total
3. Recalculer le total après application des filtres

### Step 4: Tests de Réconciliation

1. Prendre un échantillon de données connu
2. Calculer manuellement le total d'écart attendu
3. Comparer avec Excel et Dashboard
4. Ajuster jusqu'à correspondance parfaite

### Step 5: Validation Finale

1. Tester sur plusieurs jeux de données
2. Vérifier la cohérence systématique
3. Documenter la méthode de calcul validée

## Points de Vigilance

| Risque | Vérification |
|--------|-------------|
| Arrondis | Même précision décimale |
| Signes | Écart = PDF - Excel ou Excel - PDF ? |
| Filtres | Appliqués au même moment |
| Doublons | Une seule occurrence par transaction |

## Success Criteria

- [ ] Total écart Excel = Total Dashboard
- [ ] Écarts cohérents entre vues
- [ ] Pas de données manquantes
- [ ] Pas de données dupliquées

## Blockers

- Besoin d'un jeu de test avec total connu
- Besoin de comprendre la formule Excel actuelle

---

*Plan created: 2026-04-28*
