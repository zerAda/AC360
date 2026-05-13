# PLAN.md — Phase 2: Nettoyage de Données

**Phase:** 2/5 | **Requirements:** 8 | **Status:** Pending

## Goal

Dissocier société/IBAN, filtrer les bordereaux et récaps.

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Société et IBAN séparés | DATA-01, DATA-02 |
| 2 | Correspondance noms PDF/Excel | DATA-03, DATA-04 |
| 3 | Filtres bordereau et récaps | FILT-01, FILT-02, FILT-03, FILT-04 |

## Execution Steps

### Step 1: Dissocier Société et IBAN

1. Identifier le format de concaténation actuel (ex: "SOCIETE IBAN123")
2. Implémenter le parsing pour séparer nom et IBAN
3. Stocker société et IBAN dans des champs distincts
4. Utiliser le nom de société pour la correspondance PDF/Excel

### Step 2: Correspondance Fuzzy des Noms

1. Implémenter une fonction de similarité (Levenshtein, Jaro-Winkler)
2. Définir un seuil de correspondance (ex: 80%)
3. Comparer noms PDF vs noms Excel
4. Loguer les correspondances et non-correspondances

### Step 3: Filtrer les Lignes "Bordereau"

1. Identifier les patterns "bordereau" dans les données
2. Exclure ces lignes avant l'analyse
3. S'assurer qu'elles n'apparaissent pas dans le dashboard
4. Ajouter un log pour tracer les lignes exclues

### Step 4: Filtrer les Récaps/Sommes

1. Identifier les lignes de récap par groupe (somme, total, etc.)
2. Exclure ces lignes agrégées
3. Ne conserver que les lignes de détail
4. Vérifier que les totaux Excel restent cohérents

### Step 5: Validation du Nettoyage

1. Comparer les données avant/après nettoyage
2. Vérifier que les bons éléments sont exclus
3. Vérifier que les éléments utiles sont conservés

## Success Criteria

- [ ] Société et IBAN sont séparés
- [ ] Les noms de société sont comparés même s'ils diffèrent
- [ ] Lignes "bordereau" exclues
- [ ] Lignes de récap/sommes exclues
- [ ] Seules les données détaillées sont prises en compte

## Blockers

- Besoin d'exemples de données pour ajuster les seuils fuzzy
- Besoin de confirmer les patterns "bordereau" utilisés

---

*Plan created: 2026-04-28*
