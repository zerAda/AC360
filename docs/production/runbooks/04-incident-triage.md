# AC360 — Runbook de triage d'incident (OPS-04)

> Objectif : passer d'une **alerte** à une **première action** correcte en quelques
> minutes, via un arbre de décision `alerte → cause probable → première action` —
> par un seul opérateur.

## Principe

Toutes les alertes AC360 (Plan 03 observability) routent vers l'action group
(email + Teams). Le **premier réflexe** est d'ouvrir le **workbook one-pane**
(dashboard OBS-05) : audits 24h, taux d'erreur, p95 latence, % budget. Il situe
l'incident avant toute action.

Les actions d'escalade renvoient aux autres runbooks :

- **Rollback** → `02-rollback.md` (re-déploiement du tag connu-bon).
- **Rotation de secret** → `03-secret-rotation.md` (si échec d'auth / secret expiré).
- **Kill-switch** → `05-killswitch.md` (couper un poste coûteux ou bloquer un user/team).

## Procédure — Arbre de triage (alerte → cause → première action)

> Toujours commencer par le **workbook one-pane** (24h audits / error rate / p95 / budget %).

| Alerte (Plan 03) | Cause probable | Première action |
|---|---|---|
| **5xx gateway** — metricAlert `gw5xx` | mauvais déploiement récent, dépendance KO, surcharge | Vérifier `/ready` ; y a-t-il eu un deploy récent ? Si oui → **rollback (02)**. Sinon → suivre la ligne dépendance. |
| **Dépendance OCR/Fabric/Graph** — scheduledQueryRules `depFail` | panne downstream, secret expiré, consentement OBO perdu | Tester la dépendance ; si erreur d'auth (401/AADSTS65001) → **rotation (03)** ; sinon attendre/escalader le downstream. |
| **Functions / orchestration** — scheduledQueryRules `funcErr` + metricAlert `func5xx` | erreur d'orchestration, storage Durable, timeout OCR | Consulter les logs Functions + exceptions App Insights ; vérifier le storage Durable ; si timeout OCR récurrent → **kill-switch OCR (05)** le temps de stabiliser. |
| **Disponibilité `/health`** — webtest availability alert | gateway down, TLS, App Service KO | Vérifier `/health` directement + statut App Service ; si la gateway est down après un deploy → **rollback (02)**. |
| **Budget** — Consumption budget (Actual>80% / Forecast>100%) | dérive de consommation (OCR/RAG), pic d'usage | Ouvrir la tuile budget du workbook ; si poste coûteux → **kill-switch OCR/RAG (05)** ou blocage user/team. |

## Procédure — Chronologie de réponse (solo-opérateur)

```text
1. Notification (email/Teams) reçue
2. Ouvrir le workbook one-pane → situer (audits 24h / error rate / p95 / budget %)
3. Identifier la ligne d'alerte dans le tableau ci-dessus
4. Appliquer la PREMIÈRE action (vérif /ready, /health, logs, dépendance)
5. Escalader vers le runbook adéquat :
     - prod dégradée après deploy   → 02-rollback.md
     - échec d'auth / secret expiré → 03-secret-rotation.md
     - poste coûteux / abus user    → 05-killswitch.md
6. Confirmer la résolution (alerte resolved, /health 200, /ready ready)
```

## Vérifications post-action

| Vérif | Attendu |
|---|---|
| Alerte d'origine | resolved (workbook + Azure Monitor) |
| `/health` | 200 |
| `/ready` | 200 ready |
| Action tracée | runbook appliqué noté (rollback / rotation / kill-switch) |

## Dry-run / validation (exerçable hors ligne)

```text
# Marcher l'arbre contre une alerte EXEMPLE, sans Azure live :

Exemple A : "5xx gateway" reçue 5 min après un push prod-20260701-2
  → cause probable : mauvais déploiement
  → première action : /ready KO + deploy récent → ROLLBACK (02) vers prod-20260701-1
  ✓ chemin attendu validé

Exemple B : "Dépendance Graph en échec" + 401 AADSTS65001
  → cause probable : secret OBO expiré / consentement perdu
  → première action : ROTATION (03) du OBO-CLIENT-SECRET
  ✓ chemin attendu validé

Exemple C : "Budget Forecast>100%" en milieu de mois
  → cause probable : dérive OCR/RAG
  → première action : KILL-SWITCH (05) OCR ou blocage user/team
  ✓ chemin attendu validé
```

```powershell
# Confirmer que les 4 types d'alerte Plan 03 existent côté IaC (sans Azure)
Select-String -Path infra/observability.bicep -Pattern "metricAlerts"
Select-String -Path infra/observability.bicep -Pattern "scheduledQueryRules"
Select-String -Path infra/observability.bicep -Pattern "webtests"
```

## Garanties

- **Décision-arbre** : une ligne par alerte → cause → première action (pas d'improvisation).
- **Workbook d'abord** : le one-pane situe l'incident avant toute mutation.
- **Escalade tracée** : chaque branche pointe vers un runbook précis (02 / 03 / 05).
