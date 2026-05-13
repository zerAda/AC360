# KPI de Succès — Phase 8

## Vue d'Ensemble

Ce document définit les KPI simples pour mesurer le succès du POC.

## KPI Techniques

### KPI-1 : Taux de Réponses Utiles

| Métrique | Définition | Cible |
|---------|------------|-------|
| Taux de réponses utiles | (Réponses utiles / Total réponses) × 100 | > 80% |

**Mesure** : Manuel, noter les réponses utiles vs inutiles

### KPI-2 : Taux de Réponses Sourcées

| Métrique | Définition | Cible |
|---------|------------|-------|
| Taux de réponses sourcées | (Réponses avec sources / Total réponses) × 100 | > 90% |

**Mesure** : Vérifier que les sources sont citées

### KPI-3 : Taux de Réponses Incorrectes

| Métrique | Définition | Cible |
|---------|------------|-------|
| Taux de réponses incorrectes | (Réponses incorrectes / Total réponses) × 100 | < 5% |

**Mesure** : Manual review des réponses

### KPI-4 : Taux de "Non Trouvé" Correct

| Métrique | Définition | Cible |
|---------|------------|-------|
| Taux de "non trouvé" correct | ("Non trouvé" appropriés / Total requêtes sans réponse) × 100 | > 95% |

**Mesure** : Vérifier que l'agent dit correctement "je n'ai pas trouvé"

### KPI-5 : Respect des Permissions

| Métrique | Définition | Cible |
|---------|------------|-------|
| Absence de fuite documentaire | (Requêtes bloquées correctement / Requêtes non autorisées) × 100 | 100% |

**Mesure** : Test avec utilisateurs sans accès

### KPI-6 : Non-Mélange entre Clients

| Métrique | Définition | Cible |
|---------|------------|-------|
| Pas de mélange entre clients | (Réponses sur un seul client / Total réponses multi-dossiers) × 100 | 100% |

**Mesure** : Vérifier que les réponses ne mélangent pas les clients

## KPI Métier

### KPI-7 : Temps de Préparation Avant POC

| Métrique | Définition | Mesure |
|---------|------------|-------|
| Temps moyen preparation dossier | Minutes pour préparer un dossier client | Mesurer manuellement 3 préparation avant POC |

**Mesure** : Chronométrer 3 commerciaux sur 3 dossiers

### KPI-8 : Temps de Préparation Après POC

| Métrique | Définition | Mesure |
|---------|------------|-------|
| Temps moyen avec agent | Minutes pour préparer un dossier avec l'agent | Mesurer avec l'agent après |

**Mesure** : Chronométrer avec l'agent pour mêmes dossiers

### KPI-9 : Gain de Temps

| Métrique | Définition | Cible |
|---------|------------|-------|
| Gain de temps | (Temps avant - Temps après) / Temps avant × 100 | > 50% |

**Mesure** : Calcul automatique

### KPI-10 : Satisfaction Commercial

| Métrique | Définition | Cible |
|---------|------------|-------|
| Note de satisfaction | Note sur 5 des commerciaux pilotes | > 4/5 |

**Mesure** : Enquête rapide après 2 semaines

## KPI Documents

### KPI-11 : Couverture Documentaire

| Métrique | Définition | Cible |
|---------|------------|-------|
| Documents accessibles | Dossiers avec accès OK | 100% |

**Mesure** : Vérifier l'accès aux 10-20 dossiers

### KPI-12 : Sources Retrouvées

| Métrique | Définition | Cible |
|---------|------------|-------|
| Sources citables | Questions avec sources citables | > 80% |

**Mesure** : Audit des réponses

## Tableau Récapitulatif

| KPI | Métrique | Cible | Methode |
|----|---------|-------|----------|
| KPI-1 | Taux réponses utiles | > 80% | Manuel |
| KPI-2 | Taux réponses sourcées | > 90% | Manuel |
| KPI-3 | Taux réponses incorrectes | < 5% | Manuel |
| KPI-4 | Taux "non trouvé" correct | > 95% | Manuel |
| KPI-5 | Absence de fuite | 100% | Test |
| KPI-6 | Non-mélange | 100% | Test |
| KPI-7 | Temps avant POC | Baseline | Chrono |
| KPI-8 | Temps après POC | - | Chrono |
| KPI-9 | Gain de temps | > 50% | Calcul |
| KPI-10 | Satisfaction | > 4/5 | Enquête |
| KPI-11 | Documents accessibles | 100% | Audit |
| KPI-12 | Sources citables | > 80% | Audit |

---

## Méthode de Mesure Simple

### Avant POC (J0)

1. **Sélectionner 3 commerciaux**
2. **Sélectionner 3 dossiers clients**
3. **Chronométrer la préparation** : "Prépare-moi un résumé pour le client X"
4. **Noter le temps moyen** : ex. 45 minutes

### Pendant POC (Semaine 2)

1. **Utiliser l'agent** sur les mêmes 3 dossiers
2. **Chronométrer avec agent** :poser les mêmes questions
3. **Noter le temps moyen** : ex. 10 minutes
4. **Calculer le gain** : (45-10)/45 = 77%

### Après POC (Semaine 2+)

1. **Enquête rapide** : "Notez votre satisfaction sur 5"
2. **Compiler les KPI**
3. **Préparer la décision go/no-go

---

*Document créé : 2026-04-28 - KPI Succès Phase 8*