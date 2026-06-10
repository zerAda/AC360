# AC360 — Checklist de Go-Live (conditionnelle)

> **Avertissement.** Cette checklist est une **feuille de route conditionnelle**, pas une autorisation de mise en production. À ce jour (2026-06-10), AC360 n'existe qu'en **staging** (`rg-ac360-staging`, France Central), l'agent Copilot Studio **n'est pas publié** (licence premium / pay-as-you-go requise) et **aucun environnement de production** n'a été provisionné. Le verdict de référence reste **CONDITIONALLY READY — pilote supervisé en staging** (voir `PRODUCTION_READINESS.md`).
>
> Tant que les items marqués **bloquant** ci-dessous ne sont pas cochés, **le Go-Live est No-Go.**

## Légende des statuts

- `[ ]` à faire · `[x]` fait et vérifié
- **PROUVÉ** / **DOCUMENTÉ MAIS NON PROUVÉ** / **ABSENT** / **À VALIDER EN ENVIRONNEMENT RÉEL** (mêmes définitions que `PRODUCTION_READINESS.md`)
- **Resp.** : responsable d'exécution (Owner produit · RSSI · Power Platform Admin · DevSecOps)

---

## Phase 0 — Prérequis structurants (bloquants)

Aucun Go-Live ne démarre tant que cette phase n'est pas complète.

- [ ] **Environnement de production Azure provisionné** (RG dédié, tiers payants : App Service ≥ B1/P, Functions plan adapté, Document Intelligence ≥ S0). — Resp. **DevSecOps** — *Statut : ABSENT (facturable, non fait)* — **bloquant**
- [ ] **Licence Copilot Studio acquise** (premium / pay-as-you-go). — Resp. **Owner produit** — *Statut : ABSENT* — **bloquant**
- [ ] **Application Entra de production** créée (distincte de `AC360-API-staging`, scope `Audit.Trigger`). — Resp. **DevSecOps** — *Statut : ABSENT*
- [ ] **Périmètre pilote nominatif** défini et borné (équipes / utilisateurs). — Resp. **Owner produit** — *Statut : ABSENT*
- [ ] **Décision Go/No-Go formelle** enregistrée (approbation Owner produit, consultation RSSI / Power Platform Admin / DevSecOps). — Resp. **Owner produit (A)** — *Statut : À VALIDER*

---

## Phase 1 — Pré-go-live

### 1.1 Sécurité & réseau

- [ ] **Politique DLP Power Platform** définie et appliquée sur l'environnement cible (cf. `docs/governance/DLP_POLICY_REQUIREMENTS.md`). — Resp. **Power Platform Admin** (A : RSSI) — *Statut : ABSENT* — **bloquant** — À VALIDER EN ENVIRONNEMENT RÉEL
- [ ] **Private Endpoints** instruits/activés pour Key Vault, Storage, Functions, Document Intelligence. — Resp. **DevSecOps** (A : RSSI) — *Statut : ABSENT* — **bloquant selon exigence RSSI**
- [ ] **Microsoft Defender** (for Cloud / plan App Service) arbitré et activé si retenu. — Resp. **DevSecOps** (A : RSSI) — *Statut : ABSENT*
- [ ] **Allowlist IP du backend** mise à jour avec les IP de sortie de production. — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ (en prod)*
- [ ] **Clé de fonction** de production régénérée (ne pas réutiliser la clé staging). — Resp. **DevSecOps** — *Statut : À VALIDER*
- [ ] **Validation CI verte** sur le commit déployé : gitleaks, bandit, pytest (~211), flake8 (0), mypy (clean) — `.github/workflows/ci.yml`. — Resp. **DevSecOps** — *Statut : PROUVÉ (staging/CI), à rejouer sur le commit de release*

### 1.2 Secrets & rotation

- [ ] **Tous les secrets de production en Key Vault** (`0 secret en clair`), via identités managées. — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ (en prod)* — **bloquant**
- [ ] **Rotation initiale des secrets** exécutée selon `docs/security/SECRET_ROTATION.md`. — Resp. **DevSecOps (A)** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] **Audit logging Key Vault** activé sur le coffre de production. — Resp. **DevSecOps** — *Statut : PROUVÉ (staging), à reproduire en prod*

### 1.3 Licences & configuration applicative

- [ ] **Agent Copilot Studio configuré** sur l'environnement de production (connexions, scope, canal restreint). — Resp. **Power Platform Admin** — *Statut : ABSENT*
- [ ] **App settings App Service** renseignés (flags, sinks, budget) — voir Phase 1.4. — Resp. **DevSecOps** — *Statut : À VALIDER*
- [ ] **Grille tarifaire `AC360_RATE_CARD` renseignée** (actuellement **VIDE par défaut**) et **`AC360_BUDGET_EUR` fixé**. — Resp. **Owner produit (A) / DevSecOps (R)** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ* — **bloquant pour validation budget** — À VALIDER EN ENVIRONNEMENT RÉEL

### 1.4 Kill-switch — pré-positionnement

> Variables appliquées via **App Service app settings (admin uniquement)** — `scripts/feature_flags.py` + `scripts/admin_controls.py`.

- [ ] `AC360_GLOBAL_ENABLED` défini (valeur de départ maîtrisée). — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] `AC360_OCR_ENABLED`, `AC360_RAG_ENABLED`, `AC360_EMAIL_DRAFT_ENABLED`, `AC360_AUDIT_ENABLED` positionnés selon le périmètre pilote. — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] `AC360_BLOCKED_USERS_HASHED` / `AC360_BLOCKED_TEAMS` initialisés (au moins vides et documentés). — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] `AC360_ADMIN_ROLE` défini et restreint aux administrateurs habilités. — Resp. **DevSecOps** (C : RSSI) — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*

---

## Phase 2 — Go-Live

### 2.1 Déploiement

- [ ] **Déploiement passerelle FastAPI** (App Service prod) depuis le pipeline. — Resp. **DevSecOps** — *Statut : PROUVÉ en staging, à exécuter en prod*
- [ ] **Déploiement Durable Functions** (plan prod). — Resp. **DevSecOps** — *Statut : PROUVÉ en staging, à exécuter en prod*
- [ ] **Publication de l'agent Copilot Studio** sur canal restreint (pilote). — Resp. **Power Platform Admin** — *Statut : ABSENT (dépend licence)* — **bloquant**
- [ ] **Vérification des identités managées** inter-composants en production. — Resp. **DevSecOps** — *Statut : À VALIDER*

### 2.2 Smoke tests fonctionnels

- [ ] **Synthèse dossier client SharePoint** sur un dossier de test réel. — Resp. **Owner produit / DevSecOps** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*
- [ ] **Préparation de RDV** sur un dossier de test. — Resp. **Owner produit** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*
- [ ] **Audit documentaire OCR** sur un document réel (vérifier passage Document Intelligence). — Resp. **DevSecOps** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*
- [ ] **Brouillon de mail** généré (et **non envoyé** automatiquement). — Resp. **Owner produit** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*
- [ ] **Citations RAG** : vérifier l'exactitude des sources restituées sur un échantillon. — Resp. **Owner produit** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*
- [ ] **Lecture seule OneLake** confirmée (aucune écriture possible). — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*

### 2.3 Vérification kill-switch (en conditions réelles)

- [ ] **Bascule `AC360_GLOBAL_ENABLED` → off** : confirmer l'arrêt effectif du service, puis remise **on**. — Resp. **DevSecOps** (C : RSSI) — *Statut : DOCUMENTÉ MAIS NON PROUVÉ* — **bloquant**
- [ ] **Bascule d'un flag granulaire** (ex. `AC360_OCR_ENABLED` → off) : confirmer que seule la fonction visée est désactivée. — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] **Blocage utilisateur/équipe** : ajouter une entrée à `AC360_BLOCKED_USERS_HASHED` / `AC360_BLOCKED_TEAMS` et confirmer le refus. — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] **Contrôle d'accès admin** : confirmer que seul `AC360_ADMIN_ROLE` peut modifier les contrôles. — Resp. **DevSecOps** (C : RSSI) — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*

### 2.4 Vérification authentification (401 / 403)

- [ ] **Appel sans token** sur la passerelle → **401**. — Resp. **DevSecOps** — *Statut : PROUVÉ en staging, à rejouer en prod*
- [ ] **Token valide mais hors scope** (`Audit.Trigger` absent) → **403**. — Resp. **DevSecOps** — *Statut : PROUVÉ en staging, à rejouer en prod*
- [ ] **Token valide + scope correct** → **2xx** sur un appel nominal. — Resp. **DevSecOps** — *Statut : À VALIDER (prod)*
- [ ] **Accès backend sans clé de fonction / hors allowlist IP** → **rejeté**. — Resp. **DevSecOps** — *Statut : PROUVÉ en staging, à rejouer en prod*

---

## Phase 3 — Post-go-live

### 3.1 Monitoring & observabilité

- [ ] **Usage tracking actif** : `AC360_USAGE_SINK` configuré, événements **hashés** émis (`scripts/usage_tracker.py`). — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ* — À VALIDER EN ENVIRONNEMENT RÉEL
- [ ] **Logs passerelle & Functions** consultables et corrélables. — Resp. **DevSecOps** — *Statut : À VALIDER*
- [ ] **Surveillance des quotas** (Document Intelligence, App Service, Functions) sous trafic réel. — Resp. **DevSecOps** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*
- [ ] **Revue qualité RAG/OCR** sur un échantillon des premiers usages réels. — Resp. **Owner produit** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*

### 3.2 FinOps & alertes budgétaires

- [ ] **`cost_tracker.py` opérationnel** avec grille tarifaire renseignée. — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ* — **bloquant pour validation budget**
- [ ] **Alerte budgétaire** active sur `AC360_BUDGET_EUR` (notification au dépassement de seuils). — Resp. **DevSecOps** (A : Owner produit) — *Statut : ABSENT*
- [ ] **Premier relevé de coûts réels** comparé à l'estimation. — Resp. **Owner produit** — *Statut : À VALIDER EN ENVIRONNEMENT RÉEL*

### 3.3 Support & exploitation

- [ ] **Procédure de support** et canal d'escalade définis pour le pilote. — Resp. **Owner produit** — *Statut : À VALIDER*
- [ ] **Runbook kill-switch** accessible aux administrateurs (qui coupe, comment, dans quels cas). — Resp. **DevSecOps** — *Statut : DOCUMENTÉ MAIS NON PROUVÉ*
- [ ] **Revue d'accès SharePoint** (`Sites.Selected`) planifiée (périodicité définie). — Resp. **RSSI** — *Statut : À VALIDER*
- [ ] **Revue post-pilote** programmée (bilan usage, coûts, incidents) avant tout élargissement. — Resp. **Owner produit (A)** — *Statut : À VALIDER*

---

## Récapitulatif des items bloquants

Le Go-Live reste **No-Go** tant que l'un de ces items n'est pas coché :

- [ ] Environnement de production provisionné (Phase 0) — *ABSENT*
- [ ] Licence Copilot Studio acquise (Phase 0) — *ABSENT*
- [ ] DLP appliquée (Phase 1.1) — *ABSENT*
- [ ] Secrets de production en Key Vault, 0 en clair (Phase 1.2) — *NON PROUVÉ en prod*
- [ ] Grille tarifaire renseignée pour validation budget (Phase 1.3 / 3.2) — *VIDE par défaut*
- [ ] Agent Copilot Studio publié (Phase 2.1) — *ABSENT*
- [ ] Kill-switch démontré en conditions réelles (Phase 2.3) — *NON PROUVÉ*
- [ ] Private Endpoints (Phase 1.1) — *ABSENT, bloquant selon exigence RSSI*

> **Conclusion.** À la date du 2026-06-10, plusieurs items bloquants sont ouverts. La seule action autorisée est la **poursuite du pilote supervisé en staging**. Cette checklist sera réévaluée à chaque levée de prérequis ; aucune date de Go-Live ne doit être engagée tant que la **licence Copilot Studio** et l'**environnement de production** ne sont pas obtenus. Référence d'évaluation : `docs/production/PRODUCTION_READINESS.md`.
