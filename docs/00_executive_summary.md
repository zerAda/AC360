# Executive Summary — POC Assistant Client 360

## Résumé Exécutif

**Projet** : POC Assistant Client 360
**Date** : 28 Avril 2026
**Statut** : Prêt pour validation

---

## Problème

Les commerciaux passent **30-60 minutes** par client pour préparer les rendez-vous. La recherche documentaire dans SharePoint est manuelle et chronophage.

## Solution Proposée

Créer un **agent Copilot Studio** ("Assistant Client 360") connecté aux dossiers SharePoint des clients.

L'agent permet de :
- Résumer un dossier client en quelques secondes
- Retrouver des documents spécifiques
- Préparer des synthèses avant rendez-vous
- Générer des brouillons de mails
- Identifier les points d'attention

## Architecture

**Scénario A uniquement** :
- Copilot Studio comme agent
- SharePoint comme source de connaissance
- Teams ou SharePoint comme interface
- Permissions SharePoint comme sécurité

**Schéma** :
```
Commercial → Teams → Agent Copilot → SharePoint → Réponse
```

## Périmètre POC

| Élément | Quantité |
|---------|----------|
| Dossiers clients | 10-20 |
| Bibliothèques SharePoint | 1-2 |
| Utilisateurs pilotes | 3-5 |
| Cas d'usage | 3-5 |
| Durée | 2 semaines |

## Sécurité

- Permissions SharePoint existantes
- Checklist sécurité SharePoint de base
- Tests de permissions
- Validation IT requise

## Valeur Métier Attendue

| KPI | Avant | Après | Cible |
|----|-------|-------|---------|
| Temps préparation | 45 min | 10 min | -50% |
| Réponses utiles | - | >80% | >80% |
| Satisfaction | - | >4/5 | >4/5 |

## Risques Identifiés

- Permissions SharePoint trop larges
- Documents non structurés
- Mauvaise compréhension des questions
- Information manquante (acceptable)

## Prochaines Étapes

1. Valider ce cadrage (Jour 1)
2. Sélectionner les pilotes et dossiers
3. Vérifier les permissions SharePoint
4. Créer et tester l'agent
5. Publier et collecter les premiers retours
6. Décider go/no-go extension

## Décision Requise

**Go / No-Go** pour lancer le POC ?

**Accepter:**
- [ ] Oui, procéder au POC
- [ ] Non, modifications nécessaires
- [ ] Non, abandonner

---

*Document créé : 2026-04-28 - Executive Summary*