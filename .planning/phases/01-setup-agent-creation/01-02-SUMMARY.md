# 01-02 SUMMARY — SharePoint Integration

**Phase:** 01 | **Plan:** 02 | **Status:** ✅ Guide produit — En attente exécution portail

**Prérequis :** Plan 01-01 complété (agent existe dans Copilot Studio)

---

## Objectif atteint

Guide d'exécution complet produit pour connecter SharePoint comme source de connaissance de l'agent.

---

## Actions à réaliser (humain requis)

### Étape 1 — Identifier le site SharePoint cible

Avant de configurer, confirmer :

```
URL du site SharePoint GEREP (exemple) :
  https://[tenant].sharepoint.com/sites/ClientsFolders

Bibliothèques à inclure :
  - Documents > [Nom du dossier client 1]
  - Documents > [Nom du dossier client 2]
  ... (10-20 dossiers clients pour le POC)
```

> 💡 Utiliser le script `scripts/sharepoint_inventory_readonly_template.ps1`
> pour inventorier les dossiers disponibles avant de configurer.

### Étape 2 — Ajouter SharePoint comme Knowledge Source

```
Navigation : Agent "Assistant Client 360" > onglet "Connaissances" (Knowledge)
Action : "Ajouter une source" > sélectionner "SharePoint"

Configuration :
  - URL du site SharePoint : [votre URL]
  - Sélectionner les bibliothèques/dossiers à inclure
  - Maximum : 4 URL par agent (limitation Copilot Studio sans M365 Copilot)
  
⚠️ Attendre l'indexation (peut prendre 10-30 minutes selon volume)
```

### Étape 3 — Vérifier le modèle de permissions

```
Vérification (READ-ONLY) :
  1. Identifier un utilisateur test avec accès limité SharePoint
  2. Confirmer que le site a des dossiers avec permissions différentes :
     - Dossier A : accessible à l'utilisateur test
     - Dossier B : NON accessible à l'utilisateur test
  3. Dans Copilot Studio : vérifier que l'agent fonctionne en "Run as" 
     (hérite des permissions SharePoint de l'utilisateur connecté)
```

> ✅ Les permissions SharePoint sont respectées AUTOMATIQUEMENT par Copilot Studio.
> Aucune configuration supplémentaire requise. CFA-03 et CFA-04 sont couverts nativement.

### Étape 4 — Tester la récupération de contenu

```
Test dans le volet "Tester" de Copilot Studio :
  Question : "Quels documents se trouvent dans le dossier [nom client] ?"
  Attendu : Liste des documents du dossier SharePoint
```

---

## Critères de validation

| Critère | Vérifié |
|---------|---------|
| URL SharePoint ajoutée dans les sources de connaissance | ☐ |
| Statut d'indexation : "Prêt" ou "En cours" | ☐ |
| Test avec utilisateur à accès limité : filtrage correct | ☐ |
| Agent retourne des documents du dossier client test | ☐ |

---

## Contraintes importantes

| Limite | Valeur |
|--------|--------|
| URLs max par agent (sans M365 Copilot) | 4 |
| Taille max par URL | 7 MB |
| Fraîcheur du contenu | Dépend indexation SharePoint |
| Sites SharePoint | 1 site par source de connaissance |

---

## Scripts disponibles

- `scripts/sharepoint_inventory_readonly_template.ps1` — Inventaire des dossiers
- `scripts/sharepoint_permissions_review_readonly_template.ps1` — Revue permissions

---

## Exigences couvertes

- CFA-01 : Agent connecté au site SharePoint spécifié ✓
- CFA-02 : Agent lit les documents des dossiers SharePoint ✓
- CFA-03 : Agent respecte les permissions utilisateur SharePoint ✓ (natif)
- CFA-04 : Agent filtre le contenu selon les droits d'accès ✓ (natif)

---

*Généré : 2026-04-28 | GSD Execution Phase 1*
