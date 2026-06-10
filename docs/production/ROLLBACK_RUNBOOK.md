# AC360 — Runbook de rollback opérationnel

> **Objet** : procédure pas-à-pas pour revenir à un état antérieur sain de chaque
> composant AC360 en cas d'incident.
> **Périmètre actuel** : environnement **staging uniquement**
> (`rg-ac360-staging`, France Central). **Aucun environnement de production
> n'existe encore** — les procédures ci-dessous sont rédigées pour staging et
> sont **transposables** à un futur PROD une fois celui-ci créé (voir
> `docs/alm/ENVIRONMENT_STRATEGY.md`).
> **À ne jamais écrire/affirmer** : « production ready ». Ce runbook décrit des
> procédures, dont certaines ne sont pas encore exécutées en conditions réelles
> (voir colonne *Statut*).

## Légende de statut (règle d'honnêteté)

| Statut | Signification |
|---|---|
| **PROUVÉ** | Exécuté et vérifié au moins une fois en environnement réel (staging). |
| **DOCUMENTÉ MAIS NON PROUVÉ** | Procédure écrite et cohérente avec les scripts/outils, mais **pas encore rejouée** comme rollback réel. |
| **À VALIDER EN ENVIRONNEMENT RÉEL** | Dépend de ressources ou d'un environnement (slots, PROD, historique de versions) **non encore en place**. |

---

## 1. Vue d'ensemble des composants et de leur mécanisme de retour arrière

| Composant | Ressource staging | Mécanisme de rollback | Mitigation immédiate possible | Statut du rollback |
|---|---|---|---|---|
| Passerelle FastAPI | App Service Linux F1 `ac360-gateway-staging` | Redéploiement ZIP du **package précédent** (Oryx) | Kill-switch (app settings) | DOCUMENTÉ MAIS NON PROUVÉ |
| Backend Durable Functions | Function App Consumption `ac360-func-staging` | `config-zip` du **package précédent** | Kill-switch (app settings) | DOCUMENTÉ MAIS NON PROUVÉ |
| Agent Copilot Studio | Solution Power Platform AC360 | Réimport de la **version de solution précédente** (managed) / dépublication | Désactivation de topic / dépublication | À VALIDER EN ENVIRONNEMENT RÉEL |
| Configuration runtime (flags) | App settings des deux apps | Remise des app settings à l'état antérieur | **Kill-switch < 1 min** | PROUVÉ (mécanisme des flags testé unitairement) |
| OCR Document Intelligence F0 | `ac360-docintel-staging` | Pas de « version » applicative ; coupure via `AC360_OCR_ENABLED` | `AC360_OCR_ENABLED=false` | PROUVÉ (flag) |
| Données Fabric / OneLake | Lecture seule | **Pas de rollback de données** (le bot n'écrit jamais) | Coupure RAG/audit via flags | n/a (lecture seule) |

> **Principe de conception clé** : AC360 ne modifie **aucune** donnée métier
> (SharePoint et OneLake en **lecture seule** ; le pipeline est *fail-closed*).
> Un rollback ne concerne donc **que du code et de la configuration**, jamais une
> restauration de données. Cela réduit fortement le risque (pas de RPO de
> données applicatives à gérer côté AC360).

---

## 2. Déclencheurs de rollback (quand déclencher)

Déclencher un rollback si, après un déploiement ou un changement de configuration,
**un ou plusieurs** des signaux suivants est observé :

| # | Déclencheur | Seuil indicatif (À VALIDER) | Action recommandée |
|---|---|---|---|
| D1 | `GET /health` de la passerelle ne renvoie plus **200** | toute indisponibilité > 5 min | Mitigation kill-switch puis rollback passerelle |
| D2 | `POST /api/audit` avec jeton valide ne renvoie plus **200/202** | taux d'échec anormal sur 15 min | Rollback passerelle et/ou Functions |
| D3 | Régression de sécurité (ex. `POST /api/audit` sans jeton ne renvoie plus **401**, fuite d'info, PII non masquée) | **tout cas avéré** | **Rollback immédiat** + incident sécurité |
| D4 | Orchestration Durable systématiquement en `Failed` après un déploiement backend | > quelques exécutions consécutives | Rollback Functions |
| D5 | Comportement anormal de l'agent (hallucination, accès non prévu, refus cassé) | tout cas avéré | Dépublication / rollback solution Copilot |
| D6 | Explosion de consommation / coût inattendu (OCR, RAG) | alerte coût | **Kill-switch** ciblé (OCR/RAG) immédiat |
| D7 | Échec de smoke tests post-déploiement | tout échec bloquant | Rollback du composant concerné |

> Les seuils ci-dessus sont **À VALIDER EN ENVIRONNEMENT RÉEL** : aucune
> alerting/SLO formel n'est encore câblé. Ils servent de garde-fous de bon sens.

---

## 3. Qui décide (rôles et autorité)

| Décision | Autorité staging (état actuel) | Autorité PROD (à définir) |
|---|---|---|
| Actionner un **kill-switch** (mitigation) | Opérateur AC360 (Power Platform / Fabric Admin) | Astreinte / opérateur habilité |
| Rollback **passerelle / Functions** | Opérateur AC360 ayant l'accès `az` au RG | DSI/RSSI + opérateur (selon gravité) |
| Rollback **Copilot Studio** | Opérateur (Power Platform Admin) | DSI + Product Owner |
| Rollback en cas d'**incident sécurité** (D3) | Opérateur **sans attendre** (réversible), notification immédiate | RSSI décisionnaire, exécution opérateur |

> En staging il n'y a pas encore de chaîne d'astreinte formelle. **À définir avant
> PROD** : qui est joignable, sous quel délai, et qui valide a posteriori.

---

## 4. Mitigation immédiate — KILL-SWITCH (< 1 min, AVANT tout rollback)

Le kill-switch **coupe la consommation sans rien supprimer** ni redéployer. C'est
la **première action** à tenter pour stopper un incident pendant que l'on prépare
un rollback propre.

**Source de vérité** : `scripts/feature_flags.py`. Les flags sont **relus à chaque
appel** (aucun cache) → un changement d'app setting prend effet **immédiatement**,
sans redéploiement. Une valeur inconnue **ne bloque pas par accident** (défaut =
activé). Les utilisateurs bloqués sont identifiés par **hash SHA-256** (aucune PII).

### 4.1 Flags disponibles

| App setting | Effet |
|---|---|
| `AC360_GLOBAL_ENABLED=false` | **Coupure totale** : refuse toutes les fonctionnalités gouvernées. |
| `AC360_OCR_ENABLED=false` | Coupe l'OCR Document Intelligence. |
| `AC360_RAG_ENABLED=false` | Coupe la recherche/RAG. |
| `AC360_EMAIL_DRAFT_ENABLED=false` | Coupe la génération de brouillons d'e-mail. |
| `AC360_AUDIT_ENABLED=false` | Coupe le pipeline d'audit. |
| `AC360_BLOCKED_USERS_HASHED=<hash1,hash2>` | Bloque des utilisateurs précis (hash SHA-256, CSV). |
| `AC360_BLOCKED_TEAMS=<id1,id2>` | Bloque des équipes précises (CSV). |

### 4.2 Commandes (staging)

Coupure globale immédiate sur la passerelle **et** la Function (les deux portent
la logique de flags selon le composant concerné) :

```powershell
# Coupure GLOBALE (mitigation maximale)
az functionapp config appsettings set -g rg-ac360-staging -n ac360-func-staging `
  --settings AC360_GLOBAL_ENABLED=false
az webapp config appsettings set -g rg-ac360-staging -n ac360-gateway-staging `
  --settings AC360_GLOBAL_ENABLED=false

# Coupure CIBLÉE (ex. dérive de coût OCR uniquement)
az functionapp config appsettings set -g rg-ac360-staging -n ac360-func-staging `
  --settings AC360_OCR_ENABLED=false
```

> **Note F1/Consumption** : la modification d'app settings provoque un redémarrage
> applicatif. Sur F1, le redémarrage peut être lent et le poller `az` afficher un
> faux timeout : **vérifier `/health` manuellement** plutôt que de se fier au
> retour de la commande.

**Statut** : la **mécanique** des flags est PROUVÉE (tests
`tests/admin/test_feature_flags.py`, `tests/admin/test_block_consumption.py`,
`tests/backend/test_killswitch_gate.py`). L'**enchaînement opérationnel complet**
(coupure réelle observée côté utilisateur Teams) reste **À VALIDER EN
ENVIRONNEMENT RÉEL**.

### 4.3 Réactivation

Remettre la valeur à `true` (ou supprimer le setting) puis revérifier `/health`
et un smoke test :

```powershell
az webapp config appsettings set -g rg-ac360-staging -n ac360-gateway-staging `
  --settings AC360_GLOBAL_ENABLED=true
```

---

## 5. Rollback — Passerelle FastAPI (`ac360-gateway-staging`)

**Principe** : redéployer le **package ZIP de la version précédente** via Oryx.
Le packaging slim est produit par `scripts/build_gateway.ps1` (6 modules :
`api_server`, `auth`, `config`, `safe_logger`, `planner_integration`,
`generate_fiche_rdv` + `requirements.txt` minimal).

> **RÈGLE ABSOLUE** : déployer en **`--type zip`** (Oryx). **JAMAIS `--type
> static`** (fichier unique) : cela laisse le déploiement incohérent et le site ne
> redémarre pas. Leçon déjà constatée en staging.

### 5.1 Pré-requis

- Disposer du **ZIP de la version cible** (`gateway.zip` archivé, voir
  `ROLLBACK_PLAN.md` §rétention) **ou** être capable de le **reconstruire** depuis
  le commit Git correspondant : `git checkout <tag/commit>` puis
  `pwsh scripts/build_gateway.ps1`.
- Accès `az` au RG `rg-ac360-staging`.

### 5.2 Procédure

```powershell
# Option A — redéployer un package déjà archivé
az webapp deploy -g rg-ac360-staging -n ac360-gateway-staging `
  --src-path <chemin>\gateway_vPRECEDENTE.zip --type zip --restart true

# Option B — reconstruire depuis le commit sain, puis déployer
git checkout <commit_sain>
pwsh scripts/build_gateway.ps1 -Deploy
git checkout main   # revenir sur la branche de travail
```

### 5.3 Vérifications post-rollback

```powershell
# 1) Santé (200 attendu)
curl.exe -s https://ac360-gateway-staging.azurewebsites.net/health
# Attendu : {"status":"healthy","version":"3.0.0","auth":"entra-id-jwt",...}

# 2) Auth toujours active (401 sans jeton)
curl.exe -s -o NUL -w "%{http_code}" -X POST `
  https://ac360-gateway-staging.azurewebsites.net/api/audit
# Attendu : 401
```

> **Rappel F1** : `az webapp deploy` peut afficher un **timeout** alors que le
> site est déjà sain — se fier à `/health`, pas au poller.

**Statut** : DOCUMENTÉ MAIS NON PROUVÉ (le **déploiement** ZIP est PROUVÉ en
staging ; son usage **en tant que rollback** d'une version vers une précédente
n'a pas encore été rejoué).

---

## 6. Rollback — Backend Durable Functions (`ac360-func-staging`)

**Principe** : redéployer le **package de la version précédente** via
`config-zip`. Le package est produit par `azure_functions/build_package.ps1`
(host.json, `function_app.py`, `requirements.txt`, `shared/` + modules vendorisés
depuis `scripts/`).

### 6.1 Pré-requis

- ZIP cible archivé (`azure_functions/.build/ac360_func.zip`) **ou**
  reconstruction depuis le commit sain.
- Accès `az` au RG.

### 6.2 Procédure

```powershell
# Option A — package déjà archivé
az functionapp deployment source config-zip -g rg-ac360-staging -n ac360-func-staging `
  --src <chemin>\ac360_func_vPRECEDENTE.zip --build-remote true

# Option B — reconstruire depuis le commit sain
git checkout <commit_sain>
pwsh azure_functions/build_package.ps1
az functionapp deployment source config-zip -g rg-ac360-staging -n ac360-func-staging `
  --src azure_functions/.build/ac360_func.zip --build-remote true
git checkout main
```

### 6.3 Vérifications post-rollback

```powershell
# 1) Déclenchement (202 + statusQueryGetUri attendu) — via la PASSERELLE
#    (l'ingress de la Function est IP-restreint à la passerelle : defense-in-depth)
#    Utiliser le smoke test d'audit avec un jeton valide.

# 2) Suivi d'une orchestration jusqu'à runtimeStatus = Completed
#    via GET /api/audit/{job_id}/status (passerelle)
```

- Vérifier que les **trois fonctions** sont bien indexées : `http_start`,
  `audit_orchestrator`, `activity_run_audit`.
- Vérifier qu'un audit sur un cas connu se termine en `Completed` (le verdict
  métier peut légitimement être `CLIENT_NON_TROUVE`/`Failed` selon le document —
  l'important est l'absence de crash et le masquage PII `[PII_MASQUÉE]`).

> **Attention `config-zip` / app settings** : ne pas oublier que la chaîne dépend
> d'app settings (`AZURE_FUNCTION_HOST`, `AZURE_DURABLE_KEY` = clé système
> `durabletask_extension`, `TASK_HUB_NAME=ac360funcstaging`, refs Key Vault). Un
> rollback de **code** ne restaure **pas** les app settings : si l'incident venait
> d'un changement de setting, corriger le setting (voir §8).

**Statut** : DOCUMENTÉ MAIS NON PROUVÉ (déploiement `config-zip` PROUVÉ ; usage en
rollback non rejoué).

---

## 7. Rollback — Agent Copilot Studio (solution Power Platform)

**Source de vérité** : `src/copilot/AC360/**` (39 fichiers `.mcs.yml`, incl.
`agent.mcs.yml`, `settings.mcs.yml`, `connectionreferences.mcs.yml`). **Pas** de
`.mcs/botdefinition.json`. La solution se gère **managed** (TEST/UAT/PROD) vs
**unmanaged** (DEV).

### 7.1 Mitigation immédiate (sans rollback de solution)

- **Dépublier** l'agent dans l'environnement concerné (Copilot Studio → Publish →
  état précédent), ou
- **Désactiver un topic** fautif et republier, ou
- Activer le **kill-switch** côté passerelle/Functions si l'incident vient de
  l'appel à l'API (l'agent ne fait alors qu'afficher le message de service
  suspendu).

### 7.2 Rollback de solution

```text
1. Power Platform Admin Center → environnement concerné → Solutions → AC360
2. Importer la VERSION PRÉCÉDENTE de la solution (managed) :
   AC360_v[X.Y.Z-1]_<ENV>.zip   (depuis le dépôt d'artefacts de release)
3. Reconnecter les Connection References (cf. connectionreferences.mcs.yml) :
   SharePoint, WorkIQ SharePoint MCP, WorkIQ User MCP → comptes de l'ENV.
4. Revérifier les Environment Variables de l'ENV (URL passerelle, etc.).
5. Republier l'agent.
6. Smoke tests (cf. §9).
```

> **Important** : Copilot Studio **ne garantit pas** un retour arrière in-place
> fiable d'une solution managed installée. La méthode robuste est de **réimporter
> le .zip de la version précédente**. Conserver donc chaque export de release
> (voir `ROLLBACK_PLAN.md`). En DEV (unmanaged), le retour arrière se fait en
> réimportant l'export non managé correspondant.

**Statut** : **À VALIDER EN ENVIRONNEMENT RÉEL** — aucun environnement Power
Platform DEV/TEST/UAT/PROD dédié AC360 n'est encore formalisé pour le cycle de
release ; la procédure est conforme au modèle ALM mais **non rejouée**.

---

## 8. Rollback de configuration (app settings)

Si l'incident provient d'un **changement d'app setting** (et non du code) :

1. Identifier le setting modifié (comparer avec le dernier état connu sain —
   conserver un export, voir `ROLLBACK_PLAN.md`).
2. Restaurer la valeur antérieure :

```powershell
az webapp config appsettings set -g rg-ac360-staging -n ac360-gateway-staging `
  --settings <CLE>=<valeur_saine>
```

3. Vérifier `/health` puis un smoke test.

> Les **références Key Vault** (`@Microsoft.KeyVault(...)`) ne doivent pas être
> remplacées par des valeurs en clair lors d'un rollback : restaurer la **même
> référence**. Aucune clé en clair ne doit apparaître dans les app settings.

---

## 9. Vérifications post-rollback (checklist commune)

À exécuter après **tout** rollback, quel que soit le composant :

- [ ] `GET /health` → **200** + payload attendu.
- [ ] `POST /api/audit` **sans** jeton → **401** (sécurité non régressée).
- [ ] `POST /api/audit` **avec** jeton valide → **200/202** + `job_id`/`statusQueryGetUri`.
- [ ] `GET /api/audit/{job_id}/status` → **200** + résultat d'orchestration.
- [ ] Accès **direct** à la Function depuis une IP non-passerelle → **403**
      (defense-in-depth toujours en place).
- [ ] Cas *fail-closed* (document inexistant) → `Failed` propre, **PII masquée**
      `[PII_MASQUÉE]`, aucune donnée fabriquée.
- [ ] Smoke tests agent (Copilot) si rollback Copilot : accueil, refus modification
      document, refus injection, pas d'invention (`useModelKnowledge=false`).
- [ ] **Kill-switch remis à OFF** (flags à `true`) si la mitigation avait été
      activée et que l'incident est résolu.
- [ ] Coût/consommation revenus à la normale (si l'incident était un dérapage de
      coût).

---

## 10. Communication

| Moment | Destinataires | Contenu minimal |
|---|---|---|
| Au déclenchement | Opérateur + (si D3 sécurité) RSSI | Composant impacté, déclencheur, mitigation appliquée (kill-switch ?) |
| Pendant | Équipe AC360 | État (mitigé / rollback en cours), ETA |
| Après rollback | Équipe + (si PROD) utilisateurs commerciaux | Service rétabli, périmètre, éventuelle dégradation résiduelle |
| Post-mortem | Opérateur, DSI/RSSI | Cause racine, version revenue, actions de prévention, ticket |

> En staging, la communication reste interne à l'équipe AC360. La chaîne de
> communication **utilisateurs** et **astreinte** est **À DÉFINIR avant PROD**.

---

## 11. Limites connues / points à valider

- Aucun **slot de déploiement** n'existe sur F1 (les slots App Service ne sont pas
  disponibles sur le tier gratuit) → le rollback passerelle se fait par
  **redéploiement** et non par **swap de slot**. Un slot de staging/production
  serait à prévoir sur un tier payant pour un rollback near-instant (**À VALIDER**).
- Le rollback **n'a pas encore été chronométré** → aucun RTO mesuré (voir
  `ROLLBACK_PLAN.md`, cibles **À VALIDER**).
- La **rétention des packages** (gateway.zip / ac360_func.zip / exports Copilot)
  n'est pas encore industrialisée → dépendance à la reconstruction depuis Git.
- Tous les statuts « DOCUMENTÉ MAIS NON PROUVÉ » doivent être convertis en
  « PROUVÉ » via un **exercice de rollback planifié** (game day) avant PROD.

---

*Runbook AC360 — à réviser après chaque incident et après chaque exercice de
rollback. Ne jamais qualifier l'ensemble de « production ready » : décrire l'état
réel, item par item.*
