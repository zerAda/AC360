# Checklist Sécurité SharePoint — Phase 4

## Contexte

Comme l'entreprise n'a pas Microsoft Purview pour ce POC, cette checklist fournit une sécurité de base uniquement avec SharePoint et Microsoft 365.

## ⚠️ Règles de Sécurité Non-Négociables

1. **Jamais contourner les permissions SharePoint**
2. **Jamais copier les documents hors SharePoint**
3. **Jamais indexer dans un outil externe**
4. **Jamais utiliser Azure AI Search**
5. **Jamais supposer qu'un utilisateur peut voir un document**
6. **Toujours tester les réponses avec plusieurs profils**
7. **Toujours demander validation IT avant extension**

## Checklist Avant Déploiement POC

### 1. Vérification des Droits SharePoint

- [ ] Identifier le site SharePoint cible
- [ ] Lister les bibliothèques documentaires
- [ ] Vérifier les droits de chaque bibliothèque
- [ ] Documenter qui a accès à quoi

### 2. Vérification des Groupes SharePoint

- [ ] Identifier les groupes SharePoint existants
- [ ] Mapper les groupes aux utilisateurs
- [ ] Vérifier l'appartenance des pilotes
- [ ] Identifier les groupes à risque

### 3. Vérification des Propriétaires

- [ ] Identifier les propriétaires du site
- [ ] Vérifier qu'ils ont les droits appropriés
- [ ] S'assurer qu'au moins 2 propriétaires

### 4. Vérification des Accès Utilisateurs

- [ ] Lister les commerciaux pilotes
- [ ] Vérifier leurs droits sur chaque dossier
- [ ] Documenter les accès par utilisateur

### 5. Vérification des Liens de Partage

- [ ] Vérifier les liens de partage existants
- [ ] Identifier les liens anonymes
- [ ] Identifier les liens "Anyone"
- [ ] Désactiver ou supprimer les liens trop larges
- [ ] Documenter les liens restants

### 6. Vérification des Dossiers Sensibles

- [ ] Identifier les dossiers confidentiels
- [ ] Restreindre l'accès si nécessaire
- [ ] Exclure ces dossiers du POC

### 7. Vérification des Documents Confidentiels

- [ ] Identifier les documents sensibles
- [ ] Documents financiers sensibles
- [ ] Contrats avec clauses importantes
- [ ] Documents RH ou juridiques
- [ ] **Exclure ces documents du POC**

### 8. Test avec Utilisateur Autorisé

- [ ] Se connecter avec un commercial pilote
- [ ] Vérifier l'accès aux dossiers autorisés
- [ ] Tester l'agent avec questions simples

### 9. Test avec Utilisateur Non-Autorisé

- [ ] Identifier un utilisateur sans accès
- [ ] Tester que l'agent refuse l'accès
- [ ] Vérifier le comportement attendu

### 10. Test avec Manager

- [ ] Tester avec un profil manager
- [ ] Vérifier les accès différents
- [ ] Confirmer le filtrage par permissions

## Règles de Sécurité pour l'Agent

### Instructions à Inclure dans le Prompt

```
Tu ne dois jamais révéler une information provenant d'un document
auquel l'utilisateur n'a pas accès dans SharePoint.
```

### Comportements RequIS

1. **Refuser si pas accès** : Ne pas répondre sur un dossier non accessible
2. **Demander clarification** : Si client ambigu
3. **Citer les sources** : Documents utilisés
4. **Dire "non trouvé"** : Si information manquante

## Matrice de Test Sécurité

| Profil | AccèsDossier | AccèsAttendu | TestRealisé |
|--------|---------------|--------------|------------|
| Commercial A | Client ABC | Oui | [ ] |
| Commercial B | Client ABC, XYZ | Oui | [ ] |
| Commercial C | Client ABC | Oui | [ ] |
| Manager | Tous | Oui (lecture) | [ ] |
| IT Admin | Tous | Oui (admin) | [ ] |
| Commercial SansAcces | Aucun | Non | [ ] |

## Points dAttention

### Signaux dAlerte

1. **Liens de partage "Anyone"** : Supprimer immédiatement
2. **Permissions héritées excessives** : Réduire au minimum
3. **Utilisateurs avec accès non justifie** : Retirer
4. **Documents sensibles accessibles** : Exclure du POC

### Actions Correctives

| Problème | Action | Priorité |
|----------|--------|----------|
| Lien "Anyone" | Supprimer | Critique |
| Permissions trop larges | Réduire | Haute |
| Document confidentiel | Exclure | Haute |
| Accès non justifié | Retirer | Moyenne |

## Validation IT Requise

Avant le déploiement, faire valider par lIT :

1. [ ] Permissions documentées
2. [ ] Groupes vérifiés
3. [ ] Liens de partage nettoyés
4. [ ] Documents sensibles exclus
5. [ ] Tests de permission réussis

---

*Document créé : 2026-04-28 - Sécurité SharePoint Phase 4*