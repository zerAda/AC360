# AC360 — Stratégie d'environnements (DEV / TEST / UAT / PROD)

> **Objet** : définir la stratégie multi-environnements AC360, côté **Power
> Platform** (Copilot Studio) **et** côté **Azure**, ainsi que l'isolation des
> données, la gestion des solutions managed/unmanaged, les connection references,
> les environment variables, les identités (Workload Identity Federation /
> identités managées) et la promotion entre environnements.
>
> **État de référence (honnêteté)** : à ce jour, **seul l'environnement
> `staging` Azure existe réellement** (`rg-ac360-staging`, France Central,
> tiers gratuits/dev — PROUVÉ et vérifié E2E le 2026-06-09/10). Les
> environnements **DEV / TEST / UAT / PROD restent À CRÉER**. **Aucun
> environnement de production n'existe.** Ce document ne décrit donc pas un
> existant complet : c'est la **cible** à mettre en place. **Ne jamais qualifier
> l'ensemble de « production ready ».**

## Légende de statut

| Statut | Signification |
|---|---|
| **PROUVÉ** | Existe et a été vérifié par commande/observation. |
| **DOCUMENTÉ MAIS NON PROUVÉ** | Conception définie, cohérente avec les outils, **non encore instanciée**. |
| **À CRÉER / À VALIDER EN ENVIRONNEMENT RÉEL** | N'existe pas encore ; à provisionner et à vérifier. |

---

## 1. Tableau des environnements (cible)

| Environnement | Rôle | Power Platform (Copilot Studio) | Azure (Resource Group) | Données lues par le bot | Solution | Statut |
|---|---|---|---|---|---|---|
| **DEV** | Développement, itération | Env. Dataverse **DEV** (unmanaged) | `rg-ac360-dev` *(à créer)* | **AUCUNE donnée réelle** — fixtures/jeux fictifs uniquement | **Unmanaged** | À CRÉER |
| **TEST** | Intégration, tests auto, red team | Env. **TEST** (managed) | `rg-ac360-test` *(à créer)* | Données **anonymisées/synthétiques** | **Managed** | À CRÉER |
| **UAT** | Recette métier (équipes commerciales) | Env. **UAT** (managed) | `rg-ac360-uat` *(à créer)* | Sous-ensemble **maîtrisé** (idéalement anonymisé ; sinon périmètre restreint + consentement) | **Managed** | À CRÉER |
| **PROD** | Production | Env. **PROD** (managed) | `rg-ac360-prod` *(à créer)* | Données **réelles** (SharePoint + OneLake, **lecture seule**) | **Managed** | À CRÉER |
| **(staging)** | Pré-prod technique existante | *(import Copilot à câbler)* | **`rg-ac360-staging`** (France Central) | E2E réalisé sur données **réelles** SharePoint + Fabric (lecture seule) | — | **PROUVÉ (existe)** |

> **Note sur `staging`** : il s'agit de l'environnement **technique Azure** déjà
> en ligne. Il a servi à prouver la chaîne de bout en bout. Il ne se substitue
> pas à la cible ALM ci-dessus : selon le choix d'équipe, `staging` pourra être
> **renommé/repositionné** comme `UAT` ou `PROD`, ou rester un banc technique. Ce
> choix est **À VALIDER**.

---

## 2. Mapping des ressources Azure par environnement

Modèle de nommage cible (aligné sur l'existant `ac360-*-staging`) :

| Ressource | DEV (à créer) | TEST (à créer) | UAT (à créer) | PROD (à créer) | Staging (existe — PROUVÉ) |
|---|---|---|---|---|---|
| Resource Group | `rg-ac360-dev` | `rg-ac360-test` | `rg-ac360-uat` | `rg-ac360-prod` | `rg-ac360-staging` |
| Passerelle App Service | `ac360-gateway-dev` | `ac360-gateway-test` | `ac360-gateway-uat` | `ac360-gateway-prod` | `ac360-gateway-staging` (F1) |
| Plan App Service | F1/B1 | B1 | B1/S1 | **S1+ (slots)** | `ac360-gw-plan` (F1) |
| Function App | `ac360-func-dev` | `ac360-func-test` | `ac360-func-uat` | `ac360-func-prod` | `ac360-func-staging` (Consumption) |
| Storage (Durable) | dédié | dédié | dédié | dédié | `ac360stagingstore` |
| Document Intelligence (OCR) | F0 | F0/S0 | S0 | **S0** | `ac360-docintel-staging` (F0) |
| Key Vault | `ac360-kv-dev` | `ac360-kv-test` | `ac360-kv-uat` | `ac360-kv-prod` | `ac360-kv-staging` (RBAC, rétention 90 j) |
| Application Insights | par env | par env | par env | par env | `ac360-func-staging` |
| Fabric / OneLake | Workspace **DEV** (fictif) | Workspace test/anonymisé | Workspace maîtrisé | Workspace **PROD** (réel) | Workspace `GEREP_Fabric_DEV` / `Lakehouse_Gold` |

**Recommandations de tiers par environnement** (cible, **À VALIDER** côté coût) :

- **DEV/TEST** : tiers gratuits/bas (F1/F0/Consumption) pour limiter le coût.
- **UAT/PROD** : tiers payants pour la **fiabilité** et surtout les
  **slots de déploiement** (App Service **S1+**) permettant un rollback par
  *swap* near-instant (impossible sur F1). Le tier F1 actuel **n'a pas de slot**.
- OCR : passage **F0 → S0** nécessaire en UAT/PROD (volume/SLA). En staging,
  l'OCR est **maintenu en F0** volontairement (coût).

> **Isolation stricte** : un environnement = **un RG**, **un Key Vault**, **un
> jeu d'identités managées**, **un workspace Fabric**. Aucune ressource partagée
> entre environnements (évite qu'un changement DEV n'impacte PROD).

---

## 3. Isolation des données — règle non négociable

> **Le bot ne lit JAMAIS de données réelles en DEV.**

| Environnement | Source SharePoint | Source OneLake / Fabric | Règle |
|---|---|---|---|
| **DEV** | Site SharePoint **de test** avec documents **fictifs** | Workspace/Lakehouse **fictif** (données synthétiques) | **Interdiction** de pointer DEV vers des données clientes réelles. |
| **TEST** | Site de test, données **anonymisées** | Tables anonymisées/synthétiques | Anonymisation requise. |
| **UAT** | Sous-ensemble **maîtrisé** | Sous-ensemble maîtrisé | Idéalement anonymisé ; sinon périmètre restreint, accès tracé, base légale validée. |
| **PROD** | SharePoint réel (**lecture seule**) | OneLake réel (**lecture seule**) | Aucune écriture. Moindre privilège (cf. §5). |

**Garanties techniques déjà en place (PROUVÉ en staging)** :

- Le pipeline est **fail-closed** : aucune donnée fabriquée, PII masquée
  (`[PII_MASQUÉE]`), pas de divulgation de secret, signalement propre des
  prérequis manquants.
- **Lecture seule** côté données : SharePoint via Graph (`Sites.Selected`),
  OneLake via un **rôle d'accès aux données en lecture seule** (DefaultReader /
  ReadAll au niveau item) — **aucun accès en écriture**.
- L'isolation **logique** par flags (kill-switch) permet de couper une source
  (OCR/RAG/audit) sans redéploiement.

> **À VALIDER EN ENVIRONNEMENT RÉEL** : la séparation **physique** des sources
> par environnement (sites SharePoint et workspaces Fabric distincts par env)
> n'est pas encore instanciée puisque DEV/TEST/UAT/PROD restent à créer.

---

## 4. Solutions Power Platform — managed vs unmanaged

**Source de vérité du bot** : `src/copilot/AC360/**` — **39 fichiers `.mcs.yml`**
(dont `agent.mcs.yml`, `settings.mcs.yml`, `connectionreferences.mcs.yml`, topics,
actions, knowledge). **Il n'existe pas** de `.mcs/botdefinition.json`.

| Environnement | Type de solution | Justification |
|---|---|---|
| **DEV** | **Unmanaged** | Seul environnement où l'on **modifie** la solution (édition de topics, etc.). |
| **TEST / UAT / PROD** | **Managed** | Solutions **verrouillées** (pas d'édition in-place), traçabilité des versions, rollback par réimport. |

**Règles** :

1. On **développe uniquement en DEV** (unmanaged). On **n'édite jamais** une
   solution managed en aval.
2. Chaque promotion = **export DEV → import managed** dans l'environnement cible.
3. Le **versioning** de la solution est incrémenté à chaque export (cf.
   `RELEASE_CHECKLIST.md`), et chaque `.zip` exporté est **archivé** comme point de
   restauration (cf. `ROLLBACK_PLAN.md`).
4. Le **rollback** d'un environnement aval = **réimport du `.zip` managé de la
   version précédente** (Copilot Studio ne garantit pas un retour arrière in-place
   fiable). Voir `docs/production/ROLLBACK_RUNBOOK.md` §7.

**Statut** : la **mécanique** managed/unmanaged est standard Power Platform
(DOCUMENTÉ) ; sa mise en œuvre **pour AC360 across environments** est **À CRÉER**.

---

## 5. Identités, secrets et fédération (Workload Identity Federation)

### 5.1 Identités managées (runtime Azure) — PROUVÉ en staging

| Identité | Usage | Droits (staging, moindre privilège) |
|---|---|---|
| MI **Function** `ac360-func-staging` | Accès SharePoint (Graph) + OneLake + Key Vault | Graph **`Sites.Selected`** ; **Key Vault Secrets User** ; Fabric **Viewer** + **rôle données OneLake lecture seule** sur `Lakehouse_Gold`. |
| MI **Passerelle** `ac360-gateway-staging` | Résolution des secrets Key Vault | **Key Vault Secrets User** (réf. `@Microsoft.KeyVault(...)`). |

- **Aucune clé en clair** dans les app settings : `AZURE_OCR_KEY`,
  `AZURE_FUNCTION_KEY`, `AZURE_DURABLE_KEY` sont des **références Key Vault**
  résolues via MI.
- Secrets stockés dans `ac360-kv-staging` (RBAC, rétention 90 j) :
  `ocr-key`, `function-key`, + clé système Durable.

### 5.2 Service principals / CI/CD — Workload Identity Federation (cible)

Pour la **promotion automatisée** entre environnements (pipelines), la cible est
d'utiliser **Workload Identity Federation (OIDC)** plutôt que des **secrets de
service principal** :

| Acteur | Mécanisme cible | Pourquoi |
|---|---|---|
| Pipeline CI/CD (déploiement Azure) | **WIF / OIDC** (fédération depuis le runner vers Entra) | **Pas de secret de SP** stocké ; jetons éphémères. |
| Déploiement solution Power Platform | SP **dédié par environnement** (ou WIF si supporté par l'outillage) | Isolation par env, moindre privilège. |
| Connexions runtime (SharePoint, OneLake) | **Identités managées** (cf. 5.1) | Pas de credentials applicatifs à gérer. |

**Principe** : **un service principal / une identité par environnement**, avec des
droits **limités au RG de cet environnement**. Jamais un SP unique tous
environnements.

**Statut** : identités managées staging = **PROUVÉ** ; **WIF/OIDC pour CI/CD** et
**SP par environnement** = **DOCUMENTÉ MAIS NON PROUVÉ / À CRÉER** (pas de pipeline
multi-env encore en place).

> **Contrainte de droits connue (staging)** : l'opérateur GEREP dispose de
> **Fabric Admin** + **Power Platform Admin** mais **pas** de Global/Application
> Admin → la création d'**App Registration Entra** (auth API) nécessite un
> **Global Admin**. Ce point de gouvernance des identités est à anticiper pour
> chaque environnement.

---

## 6. Connection References

Définies dans `src/copilot/AC360/connectionreferences.mcs.yml`. Elles **ne portent
pas** les credentials : elles sont **reliées par environnement** à une connexion
concrète lors de l'import.

| Connection Reference | DEV | TEST | UAT | PROD |
|---|---|---|---|---|
| SharePoint | Compte/site **DEV (fictif)** | Compte **TEST** | Compte **UAT** | Compte/service **PROD** |
| WorkIQ SharePoint MCP | Reconnexion DEV | Reconnexion TEST | Reconnexion UAT | Reconnexion PROD |
| WorkIQ User MCP | Reconnexion DEV | Reconnexion TEST | Reconnexion UAT | Reconnexion PROD |

**Règles** :

- À chaque import managed, **reconnecter** toutes les connection references vers
  les connexions de l'environnement (statut « vert ») **avant** publication.
- Convention de nommage recommandée : `CR_<Service>_<ENV>` (ex.
  `CR_SharePoint_UAT`).
- Une connection reference d'un environnement **ne doit jamais** pointer vers les
  données d'un autre environnement.

**Statut** : **À CRÉER** (les connexions par environnement n'existent pas encore).

---

## 7. Environment variables (Power Platform) et app settings (Azure)

### 7.1 Environment variables Power Platform (par environnement)

| Variable | DEV | TEST | UAT | PROD |
|---|---|---|---|---|
| `ENVIRONMENT_NAME` | DEV | TEST | UAT | PROD |
| `SHAREPOINT_SITE_URL` | site fictif DEV | site TEST | site UAT | site PROD |
| `API_BASE_URL` (passerelle) | `https://ac360-gateway-dev...` | `...-test...` | `...-uat...` | `...-prod...` |

### 7.2 App settings Azure (passerelle / Function) — par environnement

Repris du modèle **staging** (PROUVÉ), à **dupliquer par environnement** avec des
valeurs propres :

- Passerelle : `AZURE_FUNCTION_HOST`, `AZURE_FUNCTION_URL`,
  `AZURE_FUNCTION_KEY` (KV ref), `AZURE_DURABLE_KEY` (KV ref, clé système
  `durabletask_extension`), `TASK_HUB_NAME`, `CLIENT_ID`, `TENANT_ID`.
- Function : `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY` (KV ref),
  `TASK_HUB_NAME`, `JOBS_BASE_DIR`, `SCM_DO_BUILD_DURING_DEPLOYMENT=true`,
  `AzureWebJobsStorage`, + (à câbler) `FABRIC_SQL_ENDPOINT`, `FABRIC_DATABASE`,
  `SHAREPOINT_DRIVE_ID`.
- **Kill-switch / flags** (cf. `scripts/feature_flags.py`), présents dans chaque
  environnement : `AC360_GLOBAL_ENABLED`, `AC360_OCR_ENABLED`,
  `AC360_RAG_ENABLED`, `AC360_EMAIL_DRAFT_ENABLED`, `AC360_AUDIT_ENABLED`,
  `AC360_BLOCKED_USERS_HASHED`, `AC360_BLOCKED_TEAMS`.

> **Règle secrets** : les vraies clés **toujours** en Key Vault (réf.
> `@Microsoft.KeyVault(...)`), jamais en clair, **par environnement** (un KV par
> env). Identifiants non secrets (`CLIENT_ID`, `TENANT_ID`, URLs, `TASK_HUB_NAME`)
> peuvent rester en app settings.

---

## 8. Promotion entre environnements

Flux cible (à industrialiser ; pour l'instant **DOCUMENTÉ MAIS NON PROUVÉ**) :

```
        ┌────────┐   export      ┌────────┐   promote     ┌────────┐   promote   ┌────────┐
        │  DEV   │ ─ unmanaged ─▶ │  TEST  │ ─ managed ───▶ │  UAT   │ ─ managed ─▶ │  PROD  │
        │unmanaged│   .zip        │managed │   .zip        │managed │   .zip      │managed │
        └────────┘               └────────┘               └────────┘             └────────┘
   Code/topics édités ici    Tests auto + red team    Recette métier         Données réelles
   Données FICTIVES          Données anonymisées       commerciaux            (lecture seule)
```

Pour **chaque** promotion, deux volets **synchronisés** :

1. **Power Platform** : export DEV (incrément de version) → import managed cible →
   reconnexion connection references → environment variables → publication →
   smoke tests. (cf. `RELEASE_CHECKLIST.md`, `DEPLOYMENT_RUNBOOK.md`)
2. **Azure** : déploiement passerelle (`scripts/build_gateway.ps1`,
   **`--type zip`** Oryx, **jamais `--type static`**) + backend Functions
   (`azure_functions/build_package.ps1` + `config-zip --build-remote true`) →
   vérification `/health`, `401` sans jeton, `200/202` avec jeton, statut
   d'orchestration.

**Portes de promotion (gates)** — repris des runbooks existants, **à exécuter par
environnement** :

- TEST → UAT : tests d'acceptation, red team, gate sécurité OK.
- UAT → PROD : sign-off Product Owner + RSSI (+ DSI pour PROD), DLP active,
  vérifications spécifiques PROD (contrôle d'accès par groupe AD, topics sensibles
  désactivés le cas échéant).

**Rollback de promotion** : voir `docs/production/ROLLBACK_RUNBOOK.md` et
`docs/alm/ROLLBACK_PLAN.md`.

---

## 9. Synthèse des statuts et travaux à mener

| Élément | Statut |
|---|---|
| Environnement **staging Azure** (RG, passerelle, Function, OCR F0, KV, MI) | **PROUVÉ (existe, vérifié E2E)** |
| Kill-switch / feature flags (mécanique) | **PROUVÉ (tests)** |
| Lecture seule SharePoint + OneLake (moindre privilège) | **PROUVÉ (staging)** |
| Environnements **DEV / TEST / UAT / PROD** (Power Platform + Azure) | **À CRÉER** |
| Solutions **managed** par environnement + cycle de promotion | DOCUMENTÉ MAIS NON PROUVÉ |
| **WIF/OIDC** pour CI/CD, **SP par environnement** | À CRÉER |
| Connexions / connection references par environnement | À CRÉER |
| Slots de déploiement (rollback par swap) en UAT/PROD | À CRÉER (impossible sur F1) |
| Séparation **physique** des données par environnement | À VALIDER EN ENVIRONNEMENT RÉEL |

> **Aucun environnement de production n'existe à ce jour.** Ce document est la
> **feuille de route d'isolation et de promotion** : il décrit ce qui est prouvé
> (staging) et ce qui reste à créer. Ne pas le présenter comme un état « prêt pour
> la production ».

---

*Stratégie d'environnements AC360 — à réviser à chaque création d'environnement et
à chaque évolution des identités/connexions.*
