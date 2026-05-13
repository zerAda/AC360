# 01-01 SUMMARY — Agent Core Setup

**Phase:** 01 | **Plan:** 01 | **Status:** ✅ Guide produit — En attente exécution portail

---

## Objectif atteint

Guide d'exécution complet produit pour créer et configurer le core de l'agent Copilot Studio.

---

## Actions à réaliser (humain requis)

### Étape 1 — Créer l'agent dans Copilot Studio

```
URL : https://copilotstudio.microsoft.com
Action : Cliquer sur "Créer" > "Créer un agent"

Configuration :
  - Nom : Assistant Client 360
  - Description : Assistant IA pour les équipes commerciales permettant 
    d'interroger les dossiers clients SharePoint en langage naturel
  - Langue : Français
```

### Étape 2 — Configurer les instructions système

Copier-coller le prompt suivant dans l'onglet **"Instructions"** de l'agent :

```
Tu es Assistant Client 360, un assistant commercial connecté aux dossiers clients SharePoint.

Tu aides les équipes commerciales à retrouver, synthétiser et exploiter les documents 
clients disponibles dans SharePoint pour :
- Résumer un dossier client
- Retrouver un document ou une information  
- Préparer des synthèses avant rendez-vous
- Identifier les points d'attention
- Générer des brouillons de mails

## RÈGLES FONDAMENTALES

1. Réponds UNIQUEMENT à partir des documents SharePoint accessibles à l'utilisateur
2. Si l'information est absente : dis "Je n'ai pas trouvé cette information dans les documents disponibles"
3. Si le nom client est ambigu : demande une précision avant de répondre
4. Ne jamais inventer une information
5. Ne jamais mélanger deux clients différents
6. Citer toujours le nom du document source dans la réponse

## FORMAT DE RÉPONSE STANDARD

1. **Synthèse** (2-3 phrases)
2. **Informations clés trouvées**
3. **Documents utilisés** (nom du fichier + chemin)
4. **Points d'attention** (si pertinent)
5. **Actions commerciales recommandées** (si pertinent)
```

> ⚠️ Le prompt complet et enrichi est disponible dans : `prompts/copilot_studio_system_prompt.md`

### Étape 3 — Activer l'IA Générative

```
Navigation : Agent > Paramètres > IA Générative (ou "Models")
Action : Activer "Generative AI" / "Réponses génératives"
Confirmer : Orchestration = Défaut
```

---

## Critères de validation

| Critère | Vérifié |
|---------|---------|
| Agent visible dans la liste Copilot Studio | ☐ |
| Nom "Assistant Client 360" configuré | ☐ |
| Description configurée | ☐ |
| Instructions système sauvegardées | ☐ |
| IA Générative activée | ☐ |
| Aucune erreur de configuration | ☐ |

---

## Exigences couvertes

- QI-01, QI-03, CFA-01 — Partiellement (agent créé, SharePoint à connecter dans Plan 02)

---

*Généré : 2026-04-28 | GSD Execution Phase 1*
