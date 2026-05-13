# Script de Démo 10 Minutes

## Vue d'Ensemble

Ce script guide une démonstration de 10 minutes de l'agent Assistant Client 360.

---

## Structure de la Démo

| Minute | Section | Contenu |
|--------|---------|----------|
| 0-1 | Contexte métier | Problème et solution |
| 1-2 | Présentation agent | Déclaration de l'agent |
| 2-3 | Demo 1 | Résumé dossier client |
| 3-4 | Demo 2 | Recherche de contrat |
| 4-5 | Demo 3 | Points d'attention |
| 5-6 | Demo 4 | Génération mail |
| 6-7 | Vérification sources | Démontrer les sources |
| 7-8 | Test information absente | Comportement "non trouvé" |
| 8-9 | Test permission | Gérer les permissions |
| 9-10 | Conclusion | Valeur métier et décision |

---

## Minute 0-1 : Contexte Métier

### Scripts

> "Bonjour, je vais vous présenter le POC Assistant Client 360."
>
> "Contexte : nos commerciaux passent 30-60 minutes par client pour préparer leurs rendez-vous."
>
> "Problème : ils doivent chercher manuellement dans les dossiers SharePoint."
>
> "Solution : un agent Copilot Studio connecté aux dossiers SharePoint."

---

## Minute 1-2 : Présentation de l'Agent

### Scripts

> "Voici l'agent 'Assistant Client 360'."
>
> "Il est publié dans Teams et accessible aux commerciaux."
>
> "L'agent répond uniquement partir des documents SharePoint auxquels l'utilisateur a accès."
>
> "Il cite toujours ses sources."

---

## Minute 2-3 : Démo 1 — Résumé Dossier

### Setup

Sélectionner un dossier client avec plusieurs documents.

### Scripts

> **Question** : "Résume-moi le dossier du client ABC"
>
> **Réponse attendue** :
> - Résumé de 2-3 phrases
> - Liste des documents clés
> - Points importants notés

### Points à démontrer

- Synthèse automatique
- Temps de réponse rapide
- Structure cohérente

---

## Minute 3-4 : Démo 2 — Recherche de Document

### Scripts

> **Question** : "Quel est le dernier contrat disponible pour ce client ?"
>
> **Réponse attendue** :
> - Nom du fichier
> - Date
> - Chemin

### Points à démontrer

- Recherche précise
- Citation du document

---

## Minute 4-5 : Démo 3 — Points d'Attention

### Scripts

> **Question** : "Quels sont les risques ou points d'attention sur ce client ?"
>
> **Réponse attendue** :
> - Points identifiés dans les documents
> - Clauses importantes
> - Échéances

### Points à démontrer

- Extraction automatique
- Pertinence

---

## Minute 5-6 : Démo 4 — Génération Mail

### Scripts

> **Question** : "Rédige-moi un mail de suivi basé sur les documents disponibles"
>
> **Réponse attendue** :
> - Brouillon structuré
> - Références aux documents
> - Ton professionnel

### Points à démontrer

- Génération cohérente
- Utilisable comme base

---

## Minute 6-7 : Vérification des Sources

### Scripts

> "Je vais vous montrer que l'agent cite toujours ses sources."
>
> **Question** : "Résume-moi le dossier" (répéter)
>
> **Montrez** :
> - Les documents listés dans la réponse
> - Lien avec les fichiers réels dans SharePoint

### Points à démontrer

- Traçabilité
- Transparence

---

## Minute 7-8 : Test Information Absente

### Scripts

> **Question** : "Quel est le chiffre d'affaires avec ce client ?"
>
> **Réponse attendue** :
> - "Je n'ai pas trouvé cette information dans les documents disponibles"

### Points à démontrer

- L'agent n'invente pas
- Réponse appropriée

---

## Minute 8-9 : Test Permission

### Setup

Utiliser un second utilisateur sans accès au dossier.

### Scripts

> [En tant qu'utilisateur sans accès] "Résume-moi le dossier ABC"
>
> **Réponse attendue** :
> - Refus ou "non trouvé"
> - L'agent ne révèle pas d'informations

### Points à démontrer

- Sécurité intégrée
- Filtrage par permissions

---

## Minute 9-10 : Conclusion

### Scripts

> "Voici le résumé de la démonstrateur."
>
> "Points clés :
> - Gain de temps : 45 min → 10 min (-78%)
> - 80%+ de réponses useful
> - Sécurité SharePoint intégrée
> - Simple et rapide à déployer"
>
> "Questions ?"
>
> "Décision go/no-go ?"

---

## Checklist Pré-Démo

- [ ] Agent Copilot Studio publié
- [ ] Utilisateurs de test configurés
- [ ] Dossier client de démo identifié
- [ ] Questions préparées
- [ ] Accès double profil testé
- [ ] SharePoint accessible
- [ ] Démonstration réalisée avant

---

*Document créé : 2026-04-28 - Script Démo 10 Minutes*