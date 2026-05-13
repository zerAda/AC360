# Risques et Mitigations — Phase Complémentaire

## Vue d'Ensemble

Document listant les risques identifiés et leurs mitigations.

---

## Matrice des Risques

### Risque 1 : Permissions SharePoint Trop Larges

| Aspect | Détail |
|--------|---------|
| Description | Des utilisateurs ont potentiellement trop de droits sur les dossiers |
| Probabilité | Haute |
| Impact | Moyen - Fuite potentielle d'informations |
| Mitigation | Checklist sécurité Phase 4 |
| Statut | À vérifier |

### Risque 2 : Documents Non Structurés

| Aspect | Détail |
|--------|---------|
| Description | Les noms de fichiers ne suivent pas de convention |
| Probabilité | Haute |
| Impact | Moyen - Réponses moins précises |
| Mitigation | Nettoyage léger Phase 3 |
| Statut | À gérer |

### Risque 3 : Mauvaise Compréhension des Questions

| Aspect | Détail |
|--------|---------|
| Description | L'agent peut mal interpréter les questions |
| Probabilité | Moyenne |
| Impact | Moyen - Réponses inexactes |
| Mitigation | Prompt système détaillé, tests |
| Statut | Mitigé |

### Risque 4 : Mélange Entre Clients

| Aspect | Détail |
|--------|---------|
| Description | L'agent pourrait mélanger deux clients |
| Probabilité | Faible |
| Impact | Critique - Confusion totale |
| Mitigation | Instructions claires dans prompt |
| Statut | Mitigé |

### Risque 5 : Information Manquante

| Aspect | Détail |
|--------|---------|
| Description | L'information n'existe pas dans SharePoint |
| Probabilité | Haute |
| Impact | Faible - Réponse "non trouvé" acceptable |
| Mitigation | Instructions pour dire "non trouvé" |
| Statut | Accepté |

### Risque 6 : Fuite Documentaire

| Aspect | Détail |
|--------|---------|
| Description | Un utilisateur voit un document auquel il ne devrait pas avoir accès |
| Probabilité | Faible |
| Impact | Critique - Violation de données |
| Mitigation | Tests permissions, validation IT |
| Statut | Mitigé |

### Risque 7 : Temps de Développement

| Aspect | Détail |
|--------|---------|
| Description | Le POC prend plus de temps que prévu |
| Probabilité | Moyenne |
| Impact | Moyen - Dépassement calendrier |
| Mitigation | Plan serré, ressources dédiées |
| Statut | À监督er |

### Risque 8 : Réponse Lente

| Aspect | Détail |
|--------|---------|
| Description | Les réponses prennent trop de temps |
| Probabilité | Faible |
| Impact | Moyen - Expérience utilisateur dégradée |
| Mitigation | Limiter le nombre de documents |
| Statut | À vérifier |

---

## Plan de Mitigation

### Actions Immédiates (Avant Jour 1)

1. Valider les permissions SharePoint
2. Identifier les documents sensibles
3.Sélectionner les pilotes apropriers

### Actions Semaine 1

1. Nettoyer les dossiers prioritaires
2. Préparer les questions de test
3. Configurer l'agent

### Actions Semaine 2

1. Tester avec plusieurs profils
2. Collecter les retours
3. Ajustements si besoin

---

*Document créé : 2026-04-28 - Risques et Mitigations*