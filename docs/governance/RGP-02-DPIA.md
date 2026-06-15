# RGP-02 — Analyse d'impact relative à la protection des données (DPIA) — BROUILLON

**Exigence :** RGP-02 (DPIA + évaluation EDPB/WP248 « ≥2-of-9 » → DPIA requise).
**Statut :** **BROUILLON autonome** — finalisation et **signature DPO = porte dure (hard gate) avant la Phase 6** (cf. §8, Plan 05-07).
**Cadre :** RGPD art. 35 ; lignes directrices **EDPB/WP248 rev.01** (9 critères, seuil « ≥2-of-9 ») ; méthodologie CNIL.
**Dernière MAJ :** 2026-06-15.

> ⚠️ **Ce document est un BROUILLON.** Il est rédigé de façon autonome à partir des sources existantes du dépôt (RGP-03, RGP-04, SEC-01..SEC-05, SECURITY_POSTURE.md). Il **n'est pas finalisé** : la signature du DPO (§8) est l'unique gate externe et **doit** intervenir avant la Phase 6.

---

## 1. Description du traitement

| Élément | Description |
|---------|-------------|
| **Nom du traitement** | AC360 — audit de conformité documentaire des dossiers clients assurance |
| **Responsable de traitement** | **[À confirmer par le DPO]** (entité juridique exploitant AC360) |
| **DPO** | **[À confirmer par le DPO]** — nom & contact |
| **Finalité** | Audit de **conformité** (lecture seule) de documents clients : extraction de champs par **OCR** (Azure Document Intelligence), comparaison au référentiel **Fabric/ARTUS**, production d'un verdict (CONFORME / ECART / INCERTAIN / CLIENT_NON_TROUVE) et d'un **brouillon FIC** soumis à revue humaine |
| **Base légale** | **[À confirmer par le DPO]** (intérêt légitime / exécution contrat assurance) |
| **Nature** | Assistant **read-only** sur Microsoft Teams (Copilot Studio) + backend FastAPI / Azure Durable Functions |
| **Personnes concernées** | Clients de l'assurance (personnes physiques figurant dans les documents audités) |
| **Catégories de données** | PII d'identité et **données financières** captées par OCR (potentiellement IBAN, n° de contrat, montants, éventuellement identifiants nationaux selon le document source) |
| **Volume / échelle** | 20–100 utilisateurs internes ; volume de la base clients **[À confirmer par le DPO]** (critère 5 « large scale », cf. §2) |
| **Localisation / résidence** | UE (France Central / West Europe) — voir `docs/governance/RGP-06-data-residency.md` (résidence M365/Fabric/Power Platform vérifiable par l'opérateur) |

---

## 2. Évaluation EDPB/WP248 — les 9 criteria (« ≥2-of-9 »)

<!-- Source : EDPB/WP248 rev.01 (https://ec.europa.eu/newsroom/article29/items/611236/en) ; méthodologie CNIL. Seuil EDPB : « ≥2-of-9 → DPIA requise ». -->

Évaluation des **9 criteria** EDPB/WP248 appliqués à AC360. Le seuil EDPB est **≥2-of-9** : si **au moins deux** critères s'appliquent, une DPIA est requise.

| # | Critère EDPB/WP248 | Applicable à AC360 ? | Justification |
|---|--------------------|----------------------|---------------|
| 1 | Évaluation / scoring | PARTIAL | L'audit produit un verdict de conformité (CONFORME/ECART/INCERTAIN) — scoring de **documents**, pas profilage de personnes |
| 2 | Décision automatisée à effet juridique/similaire | NO | Lecture seule ; le FIC est un **brouillon pour revue humaine** ; aucune décision automatisée affectant la personne concernée |
| 3 | Surveillance systématique | NO | Audit **à la demande**, par document, et non surveillance d'individus |
| 4 | Données sensibles / hautement personnelles | **YES** | Les documents clients assurance contiennent de la PII (identité, données financières, potentiellement IBAN/identifiant national captés par OCR) |
| 5 | Large scale (grande échelle) | PARTIAL | 20–100 utilisateurs internes ; volume de la base clients **à confirmer avec le DPO** (peut basculer en YES) |
| 6 | Croisement / combinaison de jeux de données | **YES** | Les champs extraits par OCR sont **comparés/croisés** au référentiel Fabric/ARTUS |
| 7 | Personnes vulnérables | NO | Clients assurance, et non enfants / employés-en-tant-que-sujets |
| 8 | Technologie innovante | **YES** | Audit documentaire par **LLM/Copilot Studio + OCR** = solution organisationnelle/technique novatrice |
| 9 | Empêche l'exercice d'un droit / l'accès à un service | NO | Assistant en lecture seule ; ne conditionne pas l'accès du client à un service |

**Résultat : ≥2 criteria atteints (4, 6, 8 fermement ; 1 et 5 PARTIAL) → DPIA requise et justifiée.** Le présent brouillon constitue la DPIA. La **signature DPO** est la porte dure (§8).

> **Points DPO (checkpoints) :** le critère **5 « large scale »** et l'**identité exacte du responsable de traitement** sont **confirmables par le DPO** (cf. RESEARCH Assumptions Log A3). Si le critère 5 bascule en YES, la conclusion (DPIA requise) est inchangée mais le profil de risque s'alourdit.

---

## 3. Nécessité et proportionnalité

- **Finalité légitime et bornée :** audit de conformité documentaire en **lecture seule** ; aucune écriture ni action sur les données SharePoint (cf. SEC-02 contrôle « lecture seule »).
- **Minimisation :** seuls les champs nécessaires à l'audit sont extraits ; les artefacts (téléchargements, OCR, brouillons FIC) sont **éphémères** et supprimés à **30 jours** (RGP-03).
- **Pas de réutilisation secondaire :** les données ne servent qu'à l'audit demandé ; pas de profilage de personnes, pas de décision automatisée (critère 2 = NO).
- **Périmètre d'accès :** OBO user-delegated — l'IA **ne voit jamais** un document que l'utilisateur n'aurait pas le droit d'ouvrir lui-même (SEC-02 contrôle OBO ; garde IDOR autoritaire `owner_hash`).
- **Proportionnalité :** le bénéfice (fiabilité et traçabilité de l'audit de conformité) est proportionné au traitement, compte tenu des mesures de réduction du risque (§5).

---

## 4. Description des risques pour les personnes concernées

| Risque | Source | Gravité initiale |
|--------|--------|------------------|
| Divulgation de PII via OCR | Captation OCR de données d'identité/financières | Élevée |
| Divulgation de PII dans les journaux/télémétrie | Logs/traces applicatifs (LLM02 OWASP) | Élevée |
| Hallucination / sortie non fondée | LLM (Copilot Studio) | Moyenne |
| Accès non autorisé aux jobs d'autrui (IDOR) | Endpoint d'audit/statut | Élevée |
| Sur-rétention de PII | Conservation excessive des artefacts | Moyenne |
| Accès au-delà des droits de l'utilisateur | Token Graph trop large | Élevée |

---

## 5. Mesures de réduction du risque (narratif read-only / éphémère / haché)

Le socle de réduction du risque d'AC360 repose sur l'architecture **read-only + no-write + artefacts éphémères (TTL 30 jours) + piste d'audit hachée**, complété par les contrôles de sécurité existants. Chaque mesure renvoie à sa preuve.

| Risque | Mesure de réduction | Source / preuve |
|--------|---------------------|-----------------|
| Divulgation PII via OCR | OCR sur **endpoint privé** Document Intelligence + `disableLocalAuth` ; artefacts éphémères supprimés à 30 j | RGP-03 ; SEC-01 (dataflow) ; SECURITY_POSTURE.md |
| Divulgation PII dans logs/télémétrie | **Surface de redaction unique** (`safe_logger.redact` + `RedactingSpanProcessor`) avant tout export ; rétention courte EU **90 jours** ; piste d'audit à **4 champs hachés** (`user_id_hash` SHA-256, sans PII brute) | **RGP-04** ; SEC-03 (LLM02) |
| Hallucination / sortie non fondée | `useModelKnowledge=false` ; `contentModeration` **High** ; gate validateur ; FIC = **brouillon revue humaine** ; validation JSON-schema de la sortie | SEC-03 (LLM01/LLM05) ; GUARDRAILS_VALIDATION.md |
| IDOR (accès aux jobs d'autrui) | Garde **IDOR autoritaire** `_assert_durable_owner` (`owner_hash = hash_id(oid)`), mismatch → 403 | **SEC-02** ; SECURITY_POSTURE.md §3 |
| Sur-rétention de PII | **TTL 30 jours** appliqué à deux points (Storage `managementPolicies` + timer Functions `prune_job_artifacts`) | **RGP-03** §2-§3 |
| Accès au-delà des droits | **OBO user-delegated** : le download honore le RBAC SharePoint propre de l'utilisateur ; token Graph **jamais persisté** | **SEC-02** contrôle OBO |
| Authentification | Entra ID **SSO**, **JWT RS256** via JWKS (anti alg-confusion), identité `oid` immuable | **SEC-02** ; SEC-01 |
| Résidence des données | Hébergement **UE** (France Central / West Europe) ; pas de transfert hors UE | **RGP-06** ; SEC-01 |

**Mesures organisationnelles :** revues bimestrielles de red-teaming, rotation semestrielle des secrets, registre des risques acceptés (SEC-05), posture de dépendances (SEC-04 — Dependabot actif).

---

## 6. Fenêtre d'effacement effective (divulgation honnête)

Conformément à RGP-03 §4, la suppression à **30 jours** n'est **pas** un effacement définitif immédiat : les durcissements INF-09 (soft-delete blob 7 j, soft-delete conteneur 7 j, versioning + PITR 6 j) prolongent la **récupérabilité effective** à **≈ 30 + 7 ≈ 37 jours**. C'est un **arbitrage assumé** sécurité-opérationnelle ↔ minimisation, déclaré honnêtement ici (et dans RGP-01 / RGP-05). Cette fenêtre **doit** être confirmée acceptable par le DPO (§8).

---

## 7. Risques résiduels et hypothèses à confirmer par le DPO

- **Risque résiduel — journal d'audit non-WORM :** la piste d'audit est **append-only + rétention + RBAC + resource-lock**, mais **PAS WORM / pas d'immuabilité table** (cadre honnête de `SECURITY_POSTURE.md` §7). Porté ici comme **hypothèse DPIA à confirmer par le DPO**.
- **Risque résiduel — fenêtre d'effacement ~37 j** (cf. §6) : récupérabilité soft-delete au-delà des 30 j nominaux.
- **Hypothèse — critère 5 « large scale » :** volume de la base clients à confirmer (peut alourdir le profil de risque).
- **Hypothèse — identité du responsable de traitement et base légale :** à confirmer par le DPO (§1).

**Risque résiduel global (avant signature DPO) : ACCEPTABLE sous réserve** de confirmation des hypothèses ci-dessus et des mesures §5 effectivement déployées (vérification opérateur post-déploiement).

---

## 8. Sign-off DPO (HARD GATE avant Phase 6)

> **PORTE DURE.** Ce DPIA est un **brouillon autonome**. Sa **finalisation et sa signature par le DPO** constituent **le gate externe bloquant avant la Phase 6** (traité au **Plan 05-07**, checkpoint `checkpoint:human-verify`, `gate=blocking`). AC360 **ne doit pas** passer en Phase 6 / production avec un DPIA non signé.

| Action DPO | Statut |
|------------|--------|
| Confirmer l'identité du responsable de traitement + DPO (§1) | ☐ En attente |
| Confirmer la base légale (§1) | ☐ En attente |
| Trancher le critère 5 « large scale » (§2) | ☐ En attente |
| Accepter la fenêtre d'effacement ~37 j (§6) | ☐ En attente |
| Accepter le risque résiduel « audit non-WORM » (§7) | ☐ En attente |
| **Signature DPIA (RGP-02)** | ☐ **En attente — hard gate** |

**Nom du DPO :** _________________________  **Date :** ____________  **Signature :** ____________

---

## 9. Références croisées

- `docs/governance/RGP-01-record-of-processing.md` — registre Art. 30 (mêmes finalités/catégories/mesures).
- `docs/governance/RGP-03-retention-policy.md` — source canonique de la rétention (30 j / ~37 j effectifs).
- `docs/governance/RGP-04-pii-in-logs-statement.md` — PII dans les journaux, redaction, rétention 90 j.
- `docs/security/SEC-01-architecture-dataflow.md` … `SEC-05-accepted-risk-register.md` — contrôles de sécurité (mesures de réduction du risque).
- `docs/security/SECURITY_POSTURE.md` §7 — cadrage honnête « append-only ≠ WORM ».
