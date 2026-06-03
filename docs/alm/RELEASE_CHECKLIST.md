# Checklist de Release — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **À compléter avant chaque déploiement en PROD**  
> **Exécutant** : Admin Power Platform + DEV  
> **Approbateur final** : RSSI + DSI

---

## Instructions

Pour chaque release, copier ce template et le remplir. Archiver le document complété dans le système de ticketing GEREP avec la référence de la release.

**Release** : _______________  
**Version** : _______________  
**Date** : _______________  
**Exécutant** : _______________

---

## 🔴 Gate 1 — Security (Sécurité)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 1.1 | Scan gitleaks exécuté → exit code 0 | | ☐ |
| 1.2 | Aucun secret en clair dans les YAML ou scripts | | ☐ |
| 1.3 | `.env` dans `.gitignore` — non commité | | ☐ |
| 1.4 | `Archives_Documentaires/` absent du package | | ☐ |
| 1.5 | `*.db`, `*.sqlite` absents du package | | ☐ |
| 1.6 | `matrice_classement_clients.xlsx` absent du package | | ☐ |
| 1.7 | `jobs/` absent du package | | ☐ |
| 1.8 | Rotation des secrets vérifiée (< 90 jours) | | ☐ |

**Résultat Gate 1** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ EXCEPTION (justifier ci-dessous)

> Exception / commentaire : _______________

---

## 🟠 Gate 2 — Copilot Studio (Configuration)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 2.1 | `useModelKnowledge = false` confirmé | | ☐ |
| 2.2 | `contentModeration = High` confirmé | | ☐ |
| 2.3 | `authenticationMode = EntraID` configuré | | ☐ |
| 2.4 | `authenticationTrigger = AlwaysAuthenticate` configuré | | ☐ |
| 2.5 | `accessControlPolicy = SpecificGroups` configuré (PROD) | | ☐ |
| 2.6 | Topic `LancerAudit` désactivé | | ☐ |
| 2.7 | Topics désactivés (`Clarificationclient__K_`, etc.) absents | | ☐ |
| 2.8 | Topic `Search` — doublon examiné et décision documentée | | ☐ |
| 2.9 | Validate YAML exécuté → exit code 0 | | ☐ |

**Résultat Gate 2** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ EXCEPTION

> Exception / commentaire : _______________

---

## 🟡 Gate 3 — RAG (Sources et comportement)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 3.1 | URL SharePoint source correcte pour l'environnement cible | | ☐ |
| 3.2 | Permissions SharePoint testées (utilisateur non admin) | | ☐ |
| 3.3 | Comportement "source absente" validé (pas d'hallucination) | | ☐ |
| 3.4 | Citations obligatoires présentes dans les réponses | | ☐ |
| 3.5 | Un seul client par réponse (multi-client refusé) | | ☐ |
| 3.6 | Connaissances générales non utilisées (réponse hors SharePoint = refus) | | ☐ |

**Résultat Gate 3** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ EXCEPTION

> Exception / commentaire : _______________

---

## 🔵 Gate 4 — API Python (si activée)

> ⚠️ Remplir uniquement si le topic `LancerAudit` est activé (non recommandé en PROD v1)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 4.1 | Validation JWT côté API (RS256 / JWKS Entra ID) | | ☐ |
| 4.2 | Test path traversal (`../../../etc/passwd`) → rejeté | | ☐ |
| 4.3 | Test JWT invalide → 401 retourné | | ☐ |
| 4.4 | Suppression automatique des fichiers temporaires (24h) | | ☐ |
| 4.5 | TLS 1.2+ configuré sur Azure App Service | | ☐ |
| 4.6 | Pas de données client dans les logs Application Insights | | ☐ |

**Résultat Gate 4** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ N/A (API non activée)

---

## 🟢 Gate 5 — DLP (Data Loss Prevention)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 5.1 | Politique DLP configurée dans l'environnement PROD | | ☐ |
| 5.2 | SharePoint classé "Business" dans la DLP | | ☐ |
| 5.3 | Teams classé "Business" dans la DLP | | ☐ |
| 5.4 | Connecteur HTTP bloqué (sauf exception approuvée) | | ☐ |
| 5.5 | OneDrive personnel bloqué | | ☐ |
| 5.6 | WorkIQ connectors — décision DLP documentée | | ☐ |
| 5.7 | Audit logs DLP actifs | | ☐ |

**Résultat Gate 5** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ EXCEPTION

---

## 🟣 Gate 6 — QA (Tests qualité)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 6.1 | Acceptance Test Matrix complétée (20/20 cas) | [X/20] | ☐ |
| 6.2 | Red Team 20 prompts exécutés — tous PASSÉ | [X/20] | ☐ |
| 6.3 | Smoke tests post-déploiement TEST réussis (5/5) | [X/5] | ☐ |
| 6.4 | Tests effectués avec un utilisateur non-admin | | ☐ |
| 6.5 | Aucune régression par rapport à la version précédente | | ☐ |

**Résultat Gate 6** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ EXCEPTION

---

## ⚙️ Gate 7 — Observabilité (Monitoring)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 7.1 | Copilot Analytics actif dans l'environnement cible | | ☐ |
| 7.2 | Alertes configurées (taux erreur >5%, latence >5s) | | ☐ |
| 7.3 | Application Insights configuré (si API activée) | | ☐ |
| 7.4 | Aucun log de données client identifié | | ☐ |
| 7.5 | Dashboard de monitoring accessible à l'équipe | | ☐ |

**Résultat Gate 7** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ N/A

---

## 📊 Gate 8 — Business (Validation métier)

| # | Critère | Résultat | Validé |
|---|---|---|---|
| 8.1 | UAT validé par l'équipe commerciale (sign-off Product Owner) | | ☐ |
| 8.2 | Script de démo testé et fonctionnel | | ☐ |
| 8.3 | Équipe support formée sur les incidents courants | | ☐ |
| 8.4 | Communication aux utilisateurs préparée | | ☐ |
| 8.5 | Guide utilisateur disponible (si applicable) | | ☐ |
| 8.6 | Procédure de rollback testée et documentée | | ☐ |

**Résultat Gate 8** : ☐ PASS &nbsp;&nbsp; ☐ FAIL &nbsp;&nbsp; ☐ EXCEPTION

---

## Résumé des gates

| Gate | Résultat | Commentaires |
|---|---|---|
| 1 — Security | ☐ PASS / ☐ FAIL | |
| 2 — Copilot | ☐ PASS / ☐ FAIL | |
| 3 — RAG | ☐ PASS / ☐ FAIL | |
| 4 — API | ☐ PASS / ☐ FAIL / ☐ N/A | |
| 5 — DLP | ☐ PASS / ☐ FAIL | |
| 6 — QA | ☐ PASS / ☐ FAIL | |
| 7 — Observabilité | ☐ PASS / ☐ FAIL / ☐ N/A | |
| 8 — Business | ☐ PASS / ☐ FAIL | |

---

## Décision finale

| Décision | Signataire | Date |
|---|---|---|
| ☐ **GO** — Tous les gates requis sont PASS | | |
| ☐ **NO-GO** — Un ou plusieurs gates FAIL (voir ci-dessous) | | |
| ☐ **GO CONDITIONNEL** — Exceptions acceptées et documentées | | |

**Motif de NO-GO / Exceptions** :

> _______________

**Approbations** :
- Product Owner : _______________ Date : _______________
- RSSI : _______________ Date : _______________
- DSI : _______________ Date : _______________

---

*Template v1.0 — Projet AC360 — GEREP Digital*
