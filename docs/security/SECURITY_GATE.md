# Security Gate — Checklist de Validation AC360

> **À compléter avant tout déploiement en environnement PROD**  
> **Approbateur requis** : RSSI + Admin Power Platform  
> **Date** : _______________  
> **Version release** : _______________  
> **Validé par** : _______________

---

## 🔴 Gate 1 — Secrets & Repo

- [ ] **Aucun secret dans le repo** — scan gitleaks exécuté et retourné exit code 0
  ```bash
  gitleaks detect --source . --verbose
  ```
- [ ] **`.env` absent du repo** (présent dans `.gitignore`)
- [ ] **Aucun token JWT, clé API, webhook en clair** dans les fichiers YAML, Python ou Markdown
- [ ] **Archives_Documentaires/** absent du repo
- [ ] **`jobs/`** absent du repo ou exclu de la release
- [ ] **`*.db`, `*.sqlite`** absents du repo
- [ ] **`matrice_classement_clients.xlsx`** absent du repo

---

## 🟠 Gate 2 — Authentification & Autorisation

- [ ] **JWT vérifié cryptographiquement** — validation RS256 via JWKS Entra ID activée
- [ ] **`authenticationMode`** configuré (EntraID SSO ou Windows Auth)
- [ ] **`authenticationTrigger = AlwaysAuthenticate`** — pas d'accès anonyme
- [ ] **`accessControlPolicy`** configurée selon l'environnement (restreindre en PROD)
- [ ] **App Registration Entra ID** — scopes minimaux (lecture SharePoint uniquement)
- [ ] **MFA obligatoire** selon la politique Entra ID GEREP
- [ ] **Rotation des secrets effectuée** si dernière rotation > 90 jours (voir SECRET_ROTATION.md)

---

## 🟡 Gate 3 — Configuration Copilot Studio

- [ ] **`useModelKnowledge = false`** — connaissances générales du modèle désactivées
- [ ] **`contentModeration = High`** — modération du contenu au niveau maximum
- [ ] **`GenerativeActionsEnabled`** — examiné et justifié (désactiver si non nécessaire)
- [ ] **`isFileAnalysisEnabled`** — examiné et justifié
- [ ] **`optInUseLatestModels`** — décision documentée (voir COPILOT_SETTINGS_DECISIONS.md)
- [ ] **Topics désactivés** confirmés désactivés (Clarificationclient__K_, Rsumdossierclient_iGk, Refusmodificationdocument_kg1)
- [ ] **Topic "LancerAudit"** confirmé NON ACTIVÉ en PROD
- [ ] **Topic "Search"** — doublon examiné et décision prise

---

## 🟢 Gate 4 — DLP & Connecteurs

- [ ] **DLP configurée** dans l'environnement PROD (Power Platform Admin Center)
- [ ] **Connecteurs Business validés** : SharePoint, Teams, Copilot Studio
- [ ] **Connecteurs HTTP bloqués** (sauf approbation explicite RSSI)
- [ ] **WorkIQ SharePoint MCP (Preview)** — gouvernance DLP vérifiée et approbation documentée
- [ ] **WorkIQ User MCP (Preview)** — gouvernance DLP vérifiée et approbation documentée
- [ ] **OneDrive personnel** — bloqué par DLP
- [ ] **Gmail / connecteurs externes** — bloqués par DLP

---

## 🔵 Gate 5 — RAG & Données

- [ ] **Aucune donnée client** dans les logs applicatifs (vérification manuelle)
- [ ] **Permissions SharePoint testées** — utilisateur ne voit que son périmètre
- [ ] **Sources SharePoint** — URL correcte en PROD (pas l'URL DEV)
- [ ] **Un seul client par réponse** — comportement validé en test
- [ ] **Citations obligatoires** — chaque réponse cite le document source
- [ ] **Comportement si source absente** — réponse explicite de non-disponibilité validée

---

## 🟣 Gate 6 — Tests de Sécurité

- [ ] **Test d'injection de prompt** effectué (15 scénarios minimum — voir RED_TEAM_PROMPTS.md)
- [ ] **Refus de modification** documentaire validé (réponse propre, pas d'erreur)
- [ ] **Refus d'agrégation multi-clients** validé
- [ ] **Refus d'avis juridique définitif** validé
- [ ] **Comportement avec JWT invalide** testé — rejet 401 correctement géré
- [ ] **Path traversal sur API** testé (si API Python activée)

---

## ⚙️ Gate 7 — Infrastructure & ALM

- [ ] **`.gitignore`** protège : `*.db`, `*.sqlite`, `.env`, `__pycache__`, `logs/`, `temp_*.json`, `final_audit_report.*`
- [ ] **Séparation DEV/TEST/PROD** confirmée — pas de credentials croisés
- [ ] **Connection References** configurées pour l'environnement PROD
- [ ] **Variables d'environnement** configurées pour PROD
- [ ] **Package release propre** généré et validé (script `package_release.ps1`)
- [ ] **Validate YAML** exécuté — exit code 0 (`validate_copilot_yaml.py`)

---

## 📊 Gate 8 — Observabilité

- [ ] **Copilot Analytics** activé et dashboard configuré
- [ ] **Application Insights** configuré (si API Python activée)
- [ ] **Alertes configurées** : taux d'erreur >5%, latence >5s, échecs auth
- [ ] **Logs DLP** — rétention configurée selon politique GEREP

---

## Résumé Gate

| Gate | Statut | Commentaires | Validé par |
|---|---|---|---|
| 1 — Secrets & Repo | ⬜ Non validé | | |
| 2 — Auth & Autorisation | ⬜ Non validé | | |
| 3 — Config Copilot | ⬜ Non validé | | |
| 4 — DLP & Connecteurs | ⬜ Non validé | | |
| 5 — RAG & Données | ⬜ Non validé | | |
| 6 — Tests Sécurité | ⬜ Non validé | | |
| 7 — Infrastructure | ⬜ Non validé | | |
| 8 — Observabilité | ⬜ Non validé | | |

---

## Décision de déploiement

| Décision | Signataire | Date |
|---|---|---|
| ☐ **AUTORISÉ** — Tous les gates validés | | |
| ☐ **REFUSÉ** — Gates en échec (voir commentaires) | | |
| ☐ **CONDITIONNEL** — Exceptions documentées | | |

**Commentaires / exceptions** :

> _______________________

---

*Template v1.0 — Projet AC360 — GEREP Digital*
