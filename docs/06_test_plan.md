# Plan de Test — Phase 7

## Vue d'Ensemble

Ce plan contient 24 cas de test répartis en 10 catégories pour valider l'agent Assistant Client 360.

## Grille de Test

### Catégorie 1 : Résumé Client (3 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-01 | "Résume-moi le dossier du client ABC" | Résumé avec infos clés | Résumé cohérent,信息来源 | Haute |
| TC-02 | "Donne-moi une vue d'ensemble du client XYZ" | Vue d'ensemble structurée | Structure respectée | Moyenne |
| TC-03 | "Quelles sont les informations importantes sur ce client ?" | Liste des points importants | Points pertinents | Haute |

### Catégorie 2 : Recherche de Document (3 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-04 | "Quel est le dernier contrat pour ce client ?" | Nom du fichier, date | Fichier correct | Haute |
| TC-05 | "Trouve-moi la dernière proposition commerciale" | Fichier identificé | Trouvé | Haute |
| TC-06 | "Liste tous les documents du dossier" | Liste des fichiers | Liste complète | Moyenne |

### Catégorie 3 : Recherche d'Information dans Contrat (3 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-07 | "Quelle est la durée du contrat ?" | Durée trouvée | Information correcte | Haute |
| TC-08 | "Y a-t-il une clause de résiliation ?" | Clause identifié | Réponse exacte | Haute |
| TC-09 | "Quel est le montant du contrat ?" | Montant trouvé | Chiffre correct | Haute |

### Catégorie 4 : Préparation Rendez-Vous (3 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-10 | "Prépare-moi une synthèse avant mon rendez-vous" | Synthèse structurée | Complete | Haute |
| TC-11 | "Prépare-moi un briefing avant la réunion" | Briefing utilisable | Utilisable | Haute |
| TC-12 | "Que dois-je savoir avant de rencontrer ce client ?" | Points clés | Pertinent | Moyenne |

### Catégorie 5 : Génération Mail Commercial (2 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-13 | "Rédige-moi un mail de suivi" | Brouillon de mail | Cohérent | Moyenne |
| TC-14 | "Prépare un mail pour le renouvellement" | Mail structuré | Adéquat | Moyenne |

### Catégorie 6 : Absence d'Information (3 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-15 | "Quel est le chiffre d'affaires ?" | "Information non trouvée" | Dit clairement | Haute |
| TC-16 | "Qui est le décideur ?" | "Non disponible" | Dit clairement | Haute |
| TC-17 | "Quelle est la marge ?" | "Information manquante" | Dit clairement | Haute |

### Catégorie 7 : Client Ambigu (2 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-18 | "Résume le dossier Alpha" | Demande précision | Demande clarification | Haute |
| TC-19 | "Infos sur client Test" | Liste options | Clarifie | Haute |

### Catégorie 8 : Test Permissions (2 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-20 | [User sans accès] "Dossier client ABC" | Refus ou "non trouvé" | Refuse correctement | Critique |
| TC-21 | [User avec accès partiel] "Dossier XYZ" | Acceso受限 | Filtrage respecté | Critique |

### Catégorie 9 : Test Non-Régression (2 tests)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-22 | Question sans rapport avec dossiers | "Je n'ai pas compris" | Pas d'invention | Haute |
| TC-23 | Question sur un autre système | Indique hors périmètre | Respecte scope | Haute |

### Catégorie 10 : Qualité des Sources (1 test)

| ID | Question Utilisateur | Résultat Attendu | Critère Succès | Criticité |
|----|-------------------|------------------|-----------------|---------------|----------|
| TC-24 | Toutes questions | Sources citables | Sources cites | Haute |

---

## Méthode de Test

### Preparation

1. Identifier 3 utilisateurs de test
2. Préparer les questions listées
3. Préparer les Accessoires attendues
4. Documenter les droits de test

### Exécution

1. Exécuter chaque test
2. Noter la réponse
3. Comparer avec attendu
4. Marquer succès/échec

### Reporting

1. Compiler results
2. Identifier les échecs
3. Proposer corrections
4.Signer le rapport

---

## Critères de Succès Globaux

- Taux de réussite global : > 80%
- Toutes les criticités HAUTEs doivent passer
- Aucune information inventée
- Sources toujours citées (quand disponibles)

---

*Document créé : 2026-04-28 - Plan de Test Phase 7*