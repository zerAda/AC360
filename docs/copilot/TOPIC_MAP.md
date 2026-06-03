# Cartographie des Topics — AC360 Copilot Studio

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Source** : Analyse des fichiers YAML `src/copilot/AC360/topics/`  
> **Synchronisation** : À mettre à jour à chaque modification d'un topic

---

## Légende

| Statut | Signification |
|---|---|
| ✅ ACTIF | Topic en production (ou DEV), fonctionnel |
| 🟡 EN_COURS | Topic en développement ou validation |
| 🔴 DÉSACTIVÉ | Topic présent dans les YAML mais désactivé |
| ⚠️ EXPÉRIMENTAL | Fonctionnalité non activée en PROD |
| 🔵 SYSTÈME | Topic système généré par Copilot Studio |
| ⚠️ DOUBLON | Topic potentiellement redondant — décision requise |

---

## Topics Métier Principaux

| Nom (interne) | Intention utilisateur | Triggers (exemples) | Source utilisée | Action appelée | Format sortie | Statut |
|---|---|---|---|---|---|---|
| **Résumé dossier client** (`Rsumdossierclient`) | Obtenir une synthèse complète du dossier d'un client | "Donne-moi le dossier du client Alpha", "Résume le compte de Beta", "Que sais-tu sur le client Gamma ?" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Markdown structuré avec sections (contrats, risques, contacts) + citations | ✅ ACTIF |
| **Recherche document client** (`Recherchedocumentclient`) | Retrouver un document ou une clause spécifique | "Trouve la DDA du client Beta", "Où est la dernière attestation de Alpha ?", "Cherche le contrat RC Pro de Gamma" | SharePoint — Search sémantique | SharePoint Search (knowledge source) | Lien document + extrait de la section pertinente | ✅ ACTIF |
| **Brouillon mail commercial** (`Brouillonmailcommercial`) | Rédiger un e-mail commercial sourcé depuis les données client | "Rédige un mail de suivi pour Alpha", "Prépare un e-mail de renouvellement pour Beta", "Écris un mail de relance pour Gamma" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | E-mail formaté (Objet, Corps, Signature) avec note "à valider" | ✅ ACTIF |
| **Points d'attention client** (`Pointsattentionclient`) | Identifier les alertes et risques prioritaires d'un dossier | "Quels sont les points d'attention pour Alpha ?", "Y a-t-il des alertes sur Beta ?", "Risques à signaler pour Gamma ?" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Liste priorisée (🔴 Critique / 🟡 Important / 🟢 Info) + sources | ✅ ACTIF |
| **Préparation RDV renouvellement** (`PreparationRDVRenouvellement`) | Générer un briefing complet avant un RDV de renouvellement | "Prépare-moi le RDV renouvellement avec Alpha", "Briefing pour le meeting de renouvellement Beta", "Prépare le dossier pour renouveler le contrat de Gamma" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Fiche briefing structurée : contexte, contrats à renouveler, enjeux, questions clés | ✅ ACTIF |
| **Préparation rendez-vous client** (`Prparationrendez-vousclient`) | Préparer tout type de rendez-vous client (pas seulement renouvellement) | "Prépare mon RDV avec Alpha pour vendredi", "Briefing avant la réunion avec Beta", "De quoi dois-je parler avec Gamma ?" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Fiche préparation : contexte, sujets à aborder, documents à avoir, actions passées | ✅ ACTIF |
| **Documents manquants** (`Documentsmanquants`) | Identifier les documents absents dans un dossier client | "Qu'est-ce qui manque dans le dossier Alpha ?", "Quels documents sont manquants pour Beta ?", "Liste les pièces manquantes de Gamma" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Liste des documents manquants + priorité + suggestion d'action | ✅ ACTIF |
| **Arguments de vente** (`Argumentsdevente`) | Générer des arguments commerciaux personnalisés pour un client | "Donne-moi des arguments pour renouveler Alpha", "Comment convaincre Beta de prendre une garantie supplémentaire ?", "Arguments de vente pour Gamma" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Liste d'arguments sourcés + contre-objections anticipées | ✅ ACTIF |
| **Recherche juridique** (`Recherchejuridiquedocumentaire`) | Identifier les éléments réglementaires ou contractuels dans les documents | "Quelle est la clause de résiliation du contrat Alpha ?", "Y a-t-il des obligations DDA dans le dossier Beta ?", "Cherche les clauses d'exclusion pour Gamma" | SharePoint — Dossiers_Clients_POC | WorkIQ SharePoint MCP | Extrait de clause + source + avertissement "indicatif uniquement — consulter un juriste" | ✅ ACTIF |

---

## Topics de Sécurité et Contrôle

| Nom (interne) | Intention utilisateur | Triggers (exemples) | Source utilisée | Action appelée | Format sortie | Statut |
|---|---|---|---|---|---|---|
| **Refus modification document** (`Refusmodificationdocument`) | Bloquer toute demande de modification, suppression ou création de document | "Modifie le contrat de Alpha", "Supprime ce fichier", "Crée une attestation pour Beta" | Aucune — réponse statique | Aucune | Message de refus clair + explication (lecture seule) + alternative suggérée | ✅ ACTIF |
| **Clarification client** (`Clarificationclient`) | Demander à l'utilisateur de préciser le nom du client si ambiguïté | Détection d'ambiguïté dans la demande | Aucune — dialogue | Aucune | Question de clarification structurée | ✅ ACTIF |

---

## Topics Expérimentaux

| Nom (interne) | Intention utilisateur | Triggers (exemples) | Source utilisée | Action appelée | Format sortie | Statut |
|---|---|---|---|---|---|---|
| **Lancer Audit** (`LancerAudit`) | Déclencher un audit automatisé PDF/Excel (bordereau bancaire) | "Lance l'audit du bordereau", "Compare le PDF et l'Excel", "Démarre le contrôle des virements" | Upload utilisateur (PDF + Excel) | API Python (expérimentale) | Rapport d'audit avec écarts | ⚠️ EXPÉRIMENTAL — NON ACTIVÉ EN PROD |

---

## Topics Système (Copilot Studio natif)

| Nom (interne) | Rôle | Comportement attendu | Statut |
|---|---|---|---|
| **ConversationStart** | Message d'accueil au démarrage | Présentation d'AC360 + guide de démarrage | 🔵 SYSTÈME |
| **Greeting** | Réponse aux salutations | Réponse chaleureuse + rappel des capacités | 🔵 SYSTÈME |
| **Goodbye** | Clôture de conversation | Message de fin professionnel | 🔵 SYSTÈME |
| **ThankYou** | Réponse aux remerciements | Réponse positive + invitation à continuer | 🔵 SYSTÈME |
| **Fallback** | Aucun topic correspondant | Message d'incompréhension + suggestions | 🔵 SYSTÈME — À personnaliser GEREP |
| **Escalate** | Demande d'escalade vers humain | Redirection vers le support | 🔵 SYSTÈME |
| **OnError** | Erreur technique | Message d'erreur gracieux + conseils | 🔵 SYSTÈME — À personnaliser |

---

## Topics à surveiller / Doublons

| Nom (interne) | Problème identifié | Décision recommandée | Statut |
|---|---|---|---|
| **Search** | Potentiel doublon avec `Recherchedocumentclient` | Analyser les overlaps — désactiver si redondant | ⚠️ DOUBLON À SURVEILLER |

---

## Topics Désactivés

| Nom (interne) | Raison de désactivation | Action requise | Statut |
|---|---|---|---|
| `Clarificationclient__K_` | Ancienne version — remplacée par version active | Supprimer le fichier YAML | 🔴 DÉSACTIVÉ — À_SUPPRIMER |
| `Rsumdossierclient_iGk` | Ancienne version — remplacée par version active | Supprimer le fichier YAML | 🔴 DÉSACTIVÉ — À_SUPPRIMER |
| `Refusmodificationdocument_kg1` | Ancienne version — remplacée par version active | Supprimer le fichier YAML | 🔴 DÉSACTIVÉ — À_SUPPRIMER |

---

## Matrice de couverture des cas d'usage

| Cas d'usage | Topic principal | Couverture | Gap identifié |
|---|---|---|---|
| Résumé client | Rsumdossierclient | ✅ Couvert | — |
| Préparation RDV | PreparationRDVRenouvellement + Prparationrendez-vousclient | ✅ Couvert | Possible redondance entre les 2 topics |
| Documents manquants | Documentsmanquants | ✅ Couvert | — |
| Brouillon mail | Brouillonmailcommercial | ✅ Couvert | — |
| Points d'attention | Pointsattentionclient | ✅ Couvert | — |
| Recherche documentaire | Recherchedocumentclient | ✅ Couvert | — |
| Arguments de vente | Argumentsdevente | ✅ Couvert | — |
| Audit PDF/Excel | LancerAudit | ⚠️ Expérimental | Non prêt pour PROD |
| Multi-client | Aucun | ❌ Non couvert | Refusé par design |

---

*Mis à jour le 2026-06-03 — Synchroniser avec les YAML après chaque sprint*
