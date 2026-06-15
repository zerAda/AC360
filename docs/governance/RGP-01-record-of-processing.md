# RGP-01 — Registre des activités de traitement (Art. 30) — BROUILLON

**Exigence :** RGP-01 (registre des activités de traitement au sens de l'**Art. 30(1)** RGPD).
**Statut :** **BROUILLON autonome** — les champs « responsable de traitement / DPO » sont **finalisés par le DPO** (cf. §8, Plan 05-07, hard gate avant Phase 6).
**Cadre :** RGPD **Art. 30(1)** (https://gdpr-info.eu/art-30-gdpr/).
**Dernière MAJ :** 2026-06-15.

> ⚠️ **Ce document est un BROUILLON.** Les sept champs statutaires de l'**Art. 30** sont pré-remplis à partir des sources du dépôt. L'identité du responsable de traitement / DPO et la base légale sont marquées **[À confirmer par le DPO]** et finalisées au Plan 05-07.

---

## Champs statutaires Art. 30(1)

### 1. Responsable de traitement / représentant / DPO — nom & contact

| Rôle | Identité & contact |
|------|--------------------|
| **Responsable de traitement (controller)** | **[À confirmer par le DPO]** |
| Représentant (le cas échéant) | **[À confirmer par le DPO]** |
| **Délégué à la protection des données (DPO)** | **[À confirmer par le DPO]** — nom, email, téléphone |

*Base légale du traitement :* **[À confirmer par le DPO]** (intérêt légitime / exécution du contrat d'assurance).

### 2. Finalités du traitement

Audit de **conformité documentaire** des dossiers clients assurance, en **lecture seule** : extraction de champs par OCR (Azure Document Intelligence), comparaison au référentiel **Fabric/ARTUS**, production d'un verdict (CONFORME / ECART / INCERTAIN / CLIENT_NON_TROUVE) et d'un **brouillon FIC** soumis à revue humaine. Aucune décision automatisée à effet juridique.

### 3. Catégories de personnes concernées & de données personnelles

| Personnes concernées | Catégories de données personnelles |
|----------------------|------------------------------------|
| Clients de l'assurance (personnes physiques figurant dans les documents audités) | Données d'**identité** et données **financières** captées par OCR : nom, références de contrat, montants, potentiellement **IBAN** et identifiants nationaux selon le document source |

### 4. Catégories de destinataires

**Équipe commerciale interne uniquement** (20–100 utilisateurs). **Aucune divulgation externe.** Sous-traitants techniques = services Microsoft Azure / M365 hébergeant le traitement (Copilot Studio, Azure Functions, Document Intelligence, Fabric, Application Insights), dans le cadre des accords de sous-traitance applicables.

### 5. Transferts vers des pays tiers

**AUCUN.** Hébergement en **Union européenne** (France Central / West Europe). La confirmation de la résidence des composants M365 / Fabric / Power Platform relève des checkpoints opérateur — voir `docs/governance/RGP-06-data-residency.md` (residency). Pas de transfert hors UE prévu.

### 6. Délais d'effacement envisagés

| Catégorie d'artefact | Délai | Source canonique |
|----------------------|-------|------------------|
| Artefacts job / OCR / brouillons FIC | **30 jours** (fenêtre d'effacement **effective ≈ 37 jours** via soft-delete/versioning, divulgation honnête) | `docs/governance/RGP-03-retention-policy.md` §2-§4 |
| Journaux / télémétrie (Log Analytics) | **90 jours** (rétention courte EU délibérée) | `docs/governance/RGP-04-pii-in-logs-statement.md` §4 |
| Piste d'audit (4 champs hachés, sans PII brute) | rétention du workspace (cf. RGP-04) ; option par-table DPO | RGP-04 §3-§4 |

### 7. Description générale des mesures de sécurité techniques & organisationnelles (**Art. 32**)

Mesures **Art. 32** existantes (Phases 1–4), documentées et tracées dans le Security Evidence Pack (SEC-01..SEC-05) :

- **Authentification :** Entra ID **SSO**, **JWT RS256** via JWKS (anti alg-confusion), identité `oid` immuable — *SEC-02*.
- **Autorisation / accès :** **OBO user-delegated** (RBAC SharePoint honoré, token Graph jamais persisté), garde **IDOR autoritaire** `owner_hash`, **lecture seule** — *SEC-02*.
- **Minimisation / rétention :** TTL **30 jours** (Storage `managementPolicies` + timer Functions) — *RGP-03*.
- **Confidentialité des journaux :** redaction PII/secrets via surface unique (`safe_logger.redact` + `RedactingSpanProcessor`) — *RGP-04*.
- **Protection des secrets :** Managed Identity + Key Vault ; endpoints privés (Document Intelligence) ; TLS 1.2.
- **Anti-hallucination :** `useModelKnowledge=false`, `contentModeration` High, gate validateur, validation JSON-schema — *SEC-03*.

Références : `docs/security/SEC-01-architecture-dataflow.md`, `SEC-02-authn-authz.md`, `SEC-03-threat-coverage-matrix.md`, `SEC-04-dependency-posture.md`, `SEC-05-accepted-risk-register.md`.

---

## 8. Finalisation DPO (hard gate avant Phase 6)

> **PORTE DURE.** Les champs « responsable de traitement / représentant / DPO » (§1) et la base légale sont **complétés et validés par le DPO** au **Plan 05-07** (checkpoint `checkpoint:human-verify`, `gate=blocking`). Le registre Art. 30 n'est **réputé final** qu'après cette finalisation. AC360 ne doit pas passer en Phase 6 avec un registre non finalisé.

| Action DPO | Statut |
|------------|--------|
| Compléter §1 (responsable / DPO / représentant) | ☐ En attente |
| Confirmer la base légale | ☐ En attente |
| Valider les catégories de données/destinataires | ☐ En attente |
| **Finalisation du registre (RGP-01)** | ☐ **En attente — hard gate** |

**Nom du DPO :** _________________________  **Date :** ____________  **Signature :** ____________
