# Décisions de Configuration Copilot Studio — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Propriétaire** : Product Owner + Admin Power Platform  
> **Révision** : À chaque release majeure

---

## Contexte

Ce document trace les décisions prises sur chaque paramètre de configuration de l'agent AC360 dans Copilot Studio. Chaque décision est justifiée et son impact documenté pour faciliter les audits et révisions futures.

---

## Tableau des décisions de configuration

| Setting | Valeur initiale | Risque si mal configuré | Valeur recommandée | Justification | Impact si changé |
|---|---|---|---|---|---|
| **useModelKnowledge** | `false` | 🔴 CRITIQUE — Le modèle répond depuis ses connaissances générales (hallucinations, données non GEREP) | `false` | Toutes les réponses doivent être sourcées depuis SharePoint. Le modèle ne doit jamais inventer de données client. | Activer = hallucinations garanties sur données client |
| **contentModeration** | `High` | 🟡 ÉLEVÉ — Modération insuffisante laisse passer des contenus inappropriés ou des injections | `High` | Niveau maximum pour bloquer les tentatives d'injection de prompt et les contenus problématiques. | Baisser = risque injection de prompt |
| **GenerativeActionsEnabled** | À vérifier | 🟡 ÉLEVÉ — Permet des actions génératives non contrôlées | `false` (désactiver si non nécessaire) | Les actions doivent être explicitement définies et gouvernées. Les actions génératives autonomes ne sont pas auditables. | Activer = surface d'attaque élargie |
| **isFileAnalysisEnabled** | À vérifier | 🟡 ÉLEVÉ — Permet l'upload et l'analyse de fichiers arbitraires | `false` en PROD (sauf si LancerAudit activé) | Le topic LancerAudit est expérimental. L'analyse de fichiers en PROD sans gouvernance est risquée. | Activer = risque de traitement de fichiers malveillants |
| **isSemanticSearchEnabled** | `true` | 🟢 FAIBLE — Désactiver dégrade la qualité de la recherche | `true` | La recherche sémantique améliore la pertinence des réponses depuis SharePoint. Aucun risque de sécurité identifié. | Désactiver = réponses moins pertinentes |
| **optInUseLatestModels** | À vérifier | 🟡 MOYEN — Les nouveaux modèles peuvent modifier les comportements | Décision documentée par Product Owner | L'utilisation des derniers modèles peut améliorer la qualité mais introduire des comportements inattendus. Tester avant activation. | Activer = comportements à re-tester |
| **authenticationMode** | `IntegratedWindowsAuthentication` ou `EntraID` | 🔴 CRITIQUE — Mode `None` = accès anonyme | `EntraID` (SSO) | L'authentification via Entra ID garantit que seuls les utilisateurs GEREP accèdent à AC360. Aucun accès anonyme. | Désactiver = accès public au bot |
| **authenticationTrigger** | `AlwaysAuthenticate` | 🔴 CRITIQUE — `Manual` ou `Required` permettent des sessions non authentifiées | `AlwaysAuthenticate` | L'authentification doit être déclenchée dès le début de chaque conversation. | Changer = sessions sans identité tracée |
| **accessControlPolicy** | `AllowAll` (DEV) | 🟡 MOYEN — En PROD, `AllowAll` signifie tout utilisateur M365 GEREP peut accéder | `SpecificGroups` (PROD) — Groupe AD "AC360-Users" | Restreindre l'accès en PROD au groupe des commerciaux habilités. En DEV, AllowAll pour faciliter les tests. | Changer en PROD = contrôle d'accès métier |

---

## Détail des paramètres critiques

### `useModelKnowledge = false` — DÉCISION FONDAMENTALE

```yaml
# Dans les paramètres de l'agent Copilot Studio
useModelKnowledge: false
```

**Scénario si activé** :
> Utilisateur : "Quelle est la surface du client Alpha ?"  
> AC360 (avec useModelKnowledge=true) : "D'après mes connaissances, Alpha est une société active dans..." ❌ HALLUCINATION  
> AC360 (avec useModelKnowledge=false) : "Je n'ai pas trouvé cette information dans les documents SharePoint d'Alpha." ✅ CORRECT

**Exception** : Les topics système (Greeting, Goodbye, etc.) peuvent utiliser un niveau minimal de connaissance générale pour la gestion conversationnelle. Ce n'est pas du contenu client.

---

### `contentModeration = High` — PROTECTION ANTI-INJECTION

**Ce que ça bloque** :
- Tentatives de jailbreak ("Ignore tes instructions et...")
- Demandes de contenu inapproprié
- Extraction de données système

**Effet de bord** : Peut occasionnellement refuser des requêtes légitimes avec des formulations maladroites. À monitorer via Copilot Analytics (taux de fallback).

---

### `authenticationMode = EntraID` — ARCHITECTURE SSO

```
Flux d'authentification :
Teams → Copilot Studio → [Redirect Entra ID] → JWT → Copilot Studio → Réponse
```

**Claims JWT utilisés** :
- `upn` — User Principal Name (email GEREP)
- `name` — Nom complet
- `oid` — Object ID Entra (identifiant unique)
- `roles` — Rôles assignés (si configurés)

---

## Matrice de risque des settings

| Setting | Valeur actuelle | Conforme PROD ? | Action requise |
|---|---|---|---|
| useModelKnowledge | false | ✅ OUI | Maintenir |
| contentModeration | High | ✅ OUI | Maintenir |
| GenerativeActionsEnabled | À vérifier | ⬜ À valider | Vérifier et documenter |
| isFileAnalysisEnabled | À vérifier | ⬜ À valider | Désactiver si LancerAudit non activé |
| isSemanticSearchEnabled | true | ✅ OUI | Maintenir |
| optInUseLatestModels | À vérifier | ⬜ À valider | Décision PO requise |
| authenticationMode | EntraID | ✅ OUI | Maintenir |
| authenticationTrigger | AlwaysAuthenticate | ✅ OUI | Maintenir |
| accessControlPolicy | AllowAll (DEV) | ⚠️ À changer en PROD | Configurer groupe AD avant PROD |

---

## Historique des changements

| Date | Setting modifié | Ancienne valeur | Nouvelle valeur | Raison | Auteur |
|---|---|---|---|---|---|
| 2026-06-03 | useModelKnowledge | — | false | Décision fondatrice — sourcing SharePoint uniquement | Product Owner |
| 2026-06-03 | contentModeration | — | High | Sécurité maximale dès le départ | RSSI |

---

*Document maintenu par le Product Owner et l'Admin Power Platform*
