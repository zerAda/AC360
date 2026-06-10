# AC360 — Plan de rollback (stratégique)

> **Objet** : cadre **stratégique** du retour arrière AC360 — versioning,
> rétention des packages, points de restauration, cibles RTO/RPO, et matrice
> *incident → action*. Le **mode opératoire pas-à-pas** est dans
> `docs/production/ROLLBACK_RUNBOOK.md`.
>
> **État de référence (honnêteté)** : seul l'environnement **staging** existe
> (`rg-ac360-staging`, France Central). **Aucun environnement de production
> n'existe.** Les cibles RTO/RPO ci-dessous sont des **objectifs proposés**,
> **À VALIDER EN ENVIRONNEMENT RÉEL** (non mesurés). **Ne jamais qualifier
> l'ensemble de « production ready ».**

## Légende de statut

| Statut | Signification |
|---|---|
| **PROUVÉ** | Vérifié en environnement réel (staging). |
| **DOCUMENTÉ MAIS NON PROUVÉ** | Défini, cohérent avec l'outillage, non rejoué. |
| **À VALIDER EN ENVIRONNEMENT RÉEL** | Dépend de ressources/mesures non encore disponibles. |

---

## 1. Principes directeurs

1. **Réversibilité par conception** : AC360 ne modifie **aucune** donnée métier
   (SharePoint + OneLake en **lecture seule**, pipeline *fail-closed*). Un rollback
   ne porte donc **que sur du code et de la configuration** — **pas** de
   restauration de données applicatives. → Le **RPO de données applicatives AC360
   est sans objet** (le bot n'écrit rien).
2. **Mitigation avant rollback** : le **kill-switch** (flags d'app settings, relus
   à chaud, cf. `scripts/feature_flags.py`) permet de **stopper la consommation en
   < 1 min sans redéploiement**. C'est la **première barrière**.
3. **Chaque release est restaurable** : tout artefact déployé (package passerelle,
   package Function, export de solution Copilot) doit être **versionné et
   conservé** comme **point de restauration**.
4. **Rollback = redéploiement d'un artefact antérieur connu sain**, ou
   reconstruction déterministe depuis le **commit Git** correspondant.
5. **Isolation par environnement** : un rollback dans un environnement n'impacte
   jamais les autres (RG, KV, identités, workspaces distincts — cf.
   `ENVIRONMENT_STRATEGY.md`).

---

## 2. Versioning

| Artefact | Schéma de version | Source d'autorité |
|---|---|---|
| Solution Copilot Studio | **SemVer** `vX.Y.Z`, incrémentée à chaque export | `RELEASE_CHECKLIST.md` / Power Platform |
| Package passerelle (`gateway.zip`) | **Commit Git** (SHA) + tag de release | `scripts/build_gateway.ps1` |
| Package Function (`ac360_func.zip`) | **Commit Git** (SHA) + tag de release | `azure_functions/build_package.ps1` |
| Configuration (app settings) | **Snapshot daté** par environnement | export `az ... appsettings list` |
| Contrat passerelle | champ `version` exposé sur `/health` (ex. `3.0.0`) | `api_server` |

**Règles** :

- Toute mise en production aval (TEST/UAT/PROD) est **taguée** dans Git
  (`ac360-<env>-vX.Y.Z`) afin de pouvoir **reconstruire à l'identique**.
- Le numéro de version de la **solution Copilot** est **incrémenté** à chaque
  export (jamais réutilisé).
- Le `version` de `/health` permet de **vérifier après rollback** quelle version
  est effectivement en ligne.

**Statut** : versioning Copilot/packages = DOCUMENTÉ ; **tag systématique par
release/env** = **À VALIDER** (cycle multi-env non encore en place).

---

## 3. Rétention des packages et points de restauration

> **Constat honnête** : aujourd'hui, les packages sont **reconstruits à la
> demande** depuis Git ; il n'existe **pas encore** de dépôt d'artefacts dédié ni
> de politique de rétention industrialisée. La cible ci-dessous est **À METTRE EN
> PLACE**.

| Point de restauration | Quoi conserver | Où (cible) | Rétention cible (À VALIDER) |
|---|---|---|---|
| **Package passerelle** | `gateway.zip` de chaque release | Dépôt d'artefacts (ex. Azure Storage/Artifacts) | **N-3** versions min. + dernière PROD |
| **Package Function** | `ac360_func.zip` de chaque release | idem | **N-3** versions min. + dernière PROD |
| **Export solution Copilot** | `AC360_vX.Y.Z_<ENV>.zip` (managed) + export unmanaged DEV | Dépôt d'artefacts + Git LFS/release | **N-3** + dernière PROD |
| **Snapshot app settings** | export JSON par env (hors secrets en clair) | Dépôt sécurisé / repo privé | dernier **état sain connu** par env |
| **Commit/tag Git** | source de toute reconstruction | dépôt Git | **permanent** |
| **Secrets** | restent en **Key Vault** (rétention 90 j staging) | `ac360-kv-<env>` | politique KV par env |

**Garde-fous** :

- Conserver **au minimum la dernière version saine connue** de chaque composant à
  tout instant (sinon le rollback dépend uniquement d'une reconstruction Git, plus
  lente et sujette à dérive d'environnement de build).
- Les **secrets ne sont jamais** stockés dans les snapshots de configuration :
  seules les **références Key Vault** le sont.
- Vérifier périodiquement qu'un package archivé **redéploie réellement** (test de
  restauration) — sinon le « point de restauration » est théorique.

**Statut** : **DOCUMENTÉ MAIS NON PROUVÉ** (dépôt d'artefacts et rétention à
créer).

---

## 4. Cibles RTO / RPO

> **Toutes les valeurs ci-dessous sont des CIBLES PROPOSÉES — `À VALIDER EN
> ENVIRONNEMENT RÉEL`.** Aucun rollback n'a encore été **chronométré** ; aucun SLO
> n'est contractualisé.

### 4.1 RTO (temps de retour à un état sain)

| Action | RTO cible (À VALIDER) | Dépendances |
|---|---|---|
| **Kill-switch** (mitigation, pas un rollback complet) | **< 1 min** d'application + délai de redémarrage F1 | Modif app setting (effet immédiat, relu à chaud) ; vérifier `/health`. |
| Rollback **passerelle** par redéploiement ZIP | **À VALIDER** (~ minutes ; F1 lent au démarrage) | Package archivé **ou** reconstruction Git. |
| Rollback **passerelle** par **swap de slot** | **near-instant** (cible UAT/PROD) | **Impossible sur F1** — nécessite tier **S1+** (À CRÉER). |
| Rollback **Functions** par `config-zip` | **À VALIDER** (build distant) | Package archivé **ou** reconstruction Git. |
| Rollback **Copilot** par réimport solution | **À VALIDER** (import 5–15 min + reconnexion CR + republication) | `.zip` managé de la version précédente. |

> **Important** : sur **F1 (staging)**, il n'y a **pas de slot** → pas de rollback
> par *swap*. Le RTO réaliste est celui d'un **redéploiement** + vérification
> `/health` (le poller `az` peut afficher un faux timeout sur F1). Un RTO court de
> type *swap* est **conditionné à un tier payant** en UAT/PROD.

### 4.2 RPO

| Domaine | RPO cible | Justification |
|---|---|---|
| **Données métier AC360** | **Sans objet (0 perte possible)** | Le bot **n'écrit jamais** : SharePoint + OneLake en lecture seule. |
| **Code / configuration** | **= dernier artefact/commit archivé** | Reconstruction déterministe depuis Git ; pas de perte si rétention en place. |
| **Données sources (SharePoint, Fabric)** | **Hors périmètre AC360** | Gérées par leurs plateformes respectives (Microsoft 365 / Fabric), pas par AC360. |

> Le RPO « données » est favorable **par conception** (lecture seule). Le seul RPO
> à gérer est celui des **artefacts/config** : il vaut « dernière version
> archivée », d'où l'importance de la **rétention** (§3).

---

## 5. Matrice incident → action

Priorité d'action : **(1) mitiger** (kill-switch) → **(2) rollback ciblé** →
**(3) post-mortem**.

| # | Incident observé | Action immédiate (mitigation) | Rollback | Décideur | Réf. runbook |
|---|---|---|---|---|---|
| I1 | `/health` KO / passerelle down après déploiement | — (santé ≠ flag) | **Rollback passerelle** (ZIP précédent) | Opérateur | RUNBOOK §5 |
| I2 | `POST /api/audit` échoue (avec jeton valide) | Kill-switch `AC360_AUDIT_ENABLED=false` si dérive | Rollback passerelle et/ou Functions | Opérateur | §5/§6 |
| I3 | **Régression sécurité** (401 cassé, fuite, PII non masquée) | **Kill-switch global** immédiat | **Rollback du composant** sans attendre | Opérateur + RSSI (a posteriori) | §5/§6/§9 |
| I4 | Orchestration Durable systématiquement `Failed` (post-déploiement) | Kill-switch `AC360_AUDIT_ENABLED=false` | **Rollback Functions** (`config-zip` précédent) | Opérateur | §6 |
| I5 | Dérive de **coût/consommation** (OCR/RAG) | **Kill-switch ciblé** (`AC360_OCR_ENABLED` / `AC360_RAG_ENABLED`) | Rollback seulement si causé par un déploiement | Opérateur | §4/§5 |
| I6 | **Comportement anormal de l'agent** (hallucination, refus cassé, accès non prévu) | Dépublier l'agent / désactiver le topic / kill-switch global | **Rollback solution Copilot** (version précédente) | Opérateur (+ PO) | §7 |
| I7 | Mauvaise **valeur d'app setting** déployée | Restaurer le setting (effet immédiat) | Pas de rollback de code si la config corrige | Opérateur | §8 |
| I8 | Compromission suspectée d'un **secret** | Kill-switch global + **rotation du secret en Key Vault** | Réviser/redéployer si nécessaire | RSSI + Opérateur | §4/§8 |
| I9 | Abus par un **utilisateur/équipe** | `AC360_BLOCKED_USERS_HASHED` / `AC360_BLOCKED_TEAMS` | — | Opérateur | §4 |

> **Règle d'or** : pour tout incident **sécurité (I3, I8)**, **mitiger d'abord**
> (kill-switch, réversible et < 1 min), notifier le RSSI, puis exécuter le
> rollback ; la validation a posteriori ne doit pas retarder la coupure.

---

## 6. Gouvernance, déclencheurs et communication (renvoi)

- **Déclencheurs** de rollback, **autorité de décision**, **vérifications
  post-rollback** détaillées et **plan de communication** : voir
  `docs/production/ROLLBACK_RUNBOOK.md` (§2, §3, §9, §10).
- **Cycle de promotion** et **isolation par environnement** : voir
  `docs/alm/ENVIRONMENT_STRATEGY.md`.
- **Procédure de déploiement** et **checklist de release** : voir
  `docs/alm/DEPLOYMENT_RUNBOOK.md` et `docs/alm/RELEASE_CHECKLIST.md`.

---

## 7. Travaux à mener pour rendre ce plan opérant

| Action | Objectif | Statut cible |
|---|---|---|
| Mettre en place un **dépôt d'artefacts** + politique de rétention (§3) | Garantir des points de restauration réels | À CRÉER |
| **Tager** chaque release par environnement dans Git | Reconstruction déterministe | À METTRE EN PLACE |
| Exporter et versionner les **snapshots d'app settings** par env | Rollback de configuration fiable | À METTRE EN PLACE |
| Provisionner un **tier App Service S1+ avec slots** en UAT/PROD | Rollback near-instant par swap | À CRÉER |
| Réaliser un **exercice de rollback (game day)** par composant | Mesurer le **RTO réel**, passer les statuts en **PROUVÉ** | À VALIDER EN ENVIRONNEMENT RÉEL |
| Formaliser **astreinte + chaîne de communication** | Décision et notification sous délai | À DÉFINIR (avant PROD) |
| Définir des **seuils/alertes** (taux d'erreur, coût) déclenchant la matrice §5 | Déclenchement objectivé | À VALIDER |

---

## 8. Synthèse des statuts

| Élément | Statut |
|---|---|
| Réversibilité par conception (lecture seule, fail-closed) | **PROUVÉ (staging)** |
| Kill-switch < 1 min (mécanique des flags) | **PROUVÉ (tests)** |
| Reconstruction des packages depuis Git | **PROUVÉ (scripts existants)** |
| Rollback rejoué (passerelle / Functions / Copilot) | DOCUMENTÉ MAIS NON PROUVÉ |
| Rétention des artefacts / points de restauration | À CRÉER |
| Slots / rollback par swap | À CRÉER (impossible sur F1) |
| **RTO / RPO chiffrés et mesurés** | **À VALIDER EN ENVIRONNEMENT RÉEL** |

> **Aucun environnement de production n'existe à ce jour.** Ce plan fixe le cadre
> et les cibles ; plusieurs éléments restent à instancier et à **prouver par un
> exercice réel** avant toute mise en production. Ne pas présenter l'ensemble comme
> « production ready ».

---

*Plan de rollback AC360 — à réviser après chaque exercice de rollback et chaque
incident, et à mettre à jour dès qu'un environnement DEV/TEST/UAT/PROD est créé.*
