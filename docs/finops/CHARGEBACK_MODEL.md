# Modèle de refacturation (chargeback) — AC360

> **Version** : 1.0
> **Date** : 2026-06-10
> **Propriétaire** : Admin Power Platform + FinOps / Contrôle de gestion
> **Révision** : Mensuelle
> **Statut global des montants** : **A_VALIDER** tant que la grille tarifaire réelle Microsoft n'est pas injectée (voir §3 et §8).

---

## 0. Avertissement d'honnêteté (à lire en premier)

Ce document décrit **comment** AC360 répartit ses coûts, **pas combien** ils valent.

- **Aucun prix unitaire n'est inventé dans ce dépôt.** La grille tarifaire par défaut (`DEFAULT_RATE_CARD` dans `scripts/cost_tracker.py`) vaut **`0.0` pour tous les postes**.
- Les prix réels Microsoft (Copilot Studio, Document Intelligence, Fabric/OneLake, Application Insights, connecteurs premium, Power Automate…) **ne figurent pas dans le repo**. Tant qu'ils ne sont pas fournis via la variable d'environnement `AC360_RATE_CARD`, **tout montant unitaire et tout coût refacturé est marqué `A_VALIDER`**.
- Par conséquent, **aucun chiffre € de ce document ne doit être facturé à un commercial, une équipe ou un client** avant la validation décrite au §8.

---

## 1. Objectif

Permettre une **refacturation interne (chargeback) ou une simple allocation analytique (showback)** de la consommation AC360 selon quatre dimensions :

1. **Commercial** — identifié par `commercial_id_hash` (jamais en clair).
2. **Équipe** — identifiée par `team_id` (non hashé : c'est un libellé d'organisation, pas une PII).
3. **Client** — identifié par `client_id_hash` (jamais en clair).
4. **Cas d'usage** — identifié par `use_case` (ex. `audit_documentaire`, `redaction_email`, `recherche_rag`).

Le modèle s'appuie sur les événements de coût (`cost_event`) produits par `scripts/cost_tracker.py` et corrélés aux événements d'usage (`usage_event`) produits par `scripts/usage_tracker.py`.

---

## 2. Source de données

| Source | Fichier | Schéma | Rôle |
|---|---|---|---|
| Événements de coût | `scripts/cost_tracker.py` (`estimate_cost`) | `schemas/cost_event.schema.json` | Montant estimé par poste et par dimension |
| Événements d'usage | `scripts/usage_tracker.py` (`build_usage_event`) | `schemas/usage_event.schema.json` | Volumétrie (messages, pages, documents, actions) par dimension |
| Grille tarifaire | env `AC360_RATE_CARD` (JSON) résolvable depuis Key Vault / app settings | — | Prix unitaire € par `cost_center` (vide par défaut) |
| Budget | env `AC360_BUDGET_EUR`, `AC360_BUDGET_WARN_PCT` | — | Seuils d'alerte budgétaire (sans blocage) |

**Dimensions transportées par `cost_event`** (cf. schéma) : `cost_center`, `quantity`, `unit`, `unit_cost_eur`, `estimated_cost_eur`, `cost_source`, `commercial_id_hash`, `team_id`, `client_id_hash`, `use_case`, `environment`, `timestamp_utc`.

---

## 3. Postes de coût (`cost_center`)

Les neuf postes ci-dessous sont les **seuls** définis dans `COST_CENTERS` (`scripts/cost_tracker.py`). Pour chacun : source de mesure de la **quantité**, méthode d'estimation du **coût**, niveau de confiance, emplacement dashboard, alerte associée.

> Colonne « Coût unitaire » : **toujours `A_VALIDER`** ici, car `unit_cost_eur = 0.0` par défaut. Elle ne devient `PARAMETRABLE` qu'une fois `AC360_RATE_CARD` renseignée, puis `REEL_MESURE` après rapprochement avec la facture Microsoft réelle.

| `cost_center` | Unité (`unit`) | Source de mesure de la quantité | Méthode d'estimation du coût | Coût unitaire | Confiance quantité | Dashboard | Alerte liée |
|---|---|---|---|---|---|---|---|
| `copilot_studio_message` | `message` | Compteur d'événements `message_sent` / `message_received` (usage_tracker) | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME — Copilot Studio n'expose pas un décompte facturable fiable côté repo | FinOps → Coûts par poste | Budget (≥80 % / ≥100 %) |
| `copilot_studio_action` | `action` | Compteur d'événements `backend_action_called` (champ `action_name`) | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME | FinOps → Coûts par poste | Budget |
| `ocr_document_intelligence` | `page` ou `document` | `page_count` / `document_count` des événements `ocr_completed` (OCR Document Intelligence **F0**) | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME — le palier réel F0/F1 doit être confirmé | FinOps → OCR | Taux d'échec OCR ; Budget |
| `fabric_onelake` | `gb` ou `request` | Volume lu / nombre de requêtes RAG (`rag_search_executed`) sur OneLake **lecture seule** | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME — Fabric facture par capacité, pas par requête : modèle d'allocation à définir | FinOps → Fabric | Pics de consommation |
| `backend_api` | `request` | Nombre d'appels à la passerelle FastAPI (Application Insights `requests`) | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME | FinOps → Backend | Latence p95 ; erreurs 5xx |
| `storage` | `gb` | Volume stocké (SharePoint / stockage Functions / blobs intermédiaires) | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME | FinOps → Stockage | — |
| `application_insights` | `gb` | Volume de données ingérées dans Application Insights / Log Analytics | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME — dépend de la rétention configurée | FinOps → Observabilité | Pics d'ingestion |
| `power_automate` | `run` | Nombre d'exécutions de flux Power Automate | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME | FinOps → Automatisation | — |
| `premium_connector` | `request` | Nombre d'appels via connecteur premium | `quantity × unit_cost_eur` | **A_VALIDER** | ESTIME | FinOps → Connecteurs | — |

### Qualification de chaque montant (`cost_source`)

Tout `cost_event` porte un champ `cost_source` (cf. `schemas/cost_event.schema.json`) :

| `cost_source` | Signification | Quand l'attend-on ? |
|---|---|---|
| `REEL_MESURE` | Montant rapproché d'une facture réelle | Après réconciliation facture Microsoft (objectif cible) |
| `ESTIME` | Estimation à partir d'un tarif fourni | Phase intermédiaire |
| `PARAMETRABLE` | Tarif fourni via `AC360_RATE_CARD` (et `unit_cost_eur > 0`) | Dès qu'une grille est injectée |
| `A_VALIDER` | **Aucun tarif fourni → montant `0.0`** | **État par défaut actuel** |

> Comportement exact (`estimate_cost`) : `cost_source = "PARAMETRABLE"` si `unit_cost_eur > 0`, sinon `"A_VALIDER"`. Le passage à `REEL_MESURE` est une décision **humaine** de rapprochement comptable, hors code.

---

## 4. Méthode d'agrégation (clé de répartition)

La refacturation est une **agrégation des `cost_event` par dimension**, sur une période donnée.

```
coût_refacturé(dimension, période)
    = Σ  estimated_cost_eur   pour tous les cost_event où
         dimension ∈ {commercial_id_hash, team_id, client_id_hash, use_case}
         ET timestamp_utc ∈ période
         ET environment = "prod"   (la refacturation ne porte que sur la prod)
```

Pour chaque poste : `estimated_cost_eur = round(unit_cost_eur × quantity, 6)`.

### Clés de répartition supportées

| Clé primaire | Champ source | Usage typique |
|---|---|---|
| Par commercial | `commercial_id_hash` | Pilotage individuel / coaching coût |
| Par équipe | `team_id` | Refacturation à un centre de coût d'équipe |
| Par client | `client_id_hash` | Allocation analytique à un dossier client |
| Par cas d'usage | `use_case` | Mesure de la rentabilité d'un scénario |

Les clés sont **combinables** (ex. coût par `team_id` × `use_case`). Les événements sans dimension renseignée (`null`) sont agrégés dans un seau **« non alloué »** explicite — ils ne sont jamais répartis arbitrairement.

---

## 5. Fréquence

| Activité | Fréquence | Responsable |
|---|---|---|
| Émission des `cost_event` | Temps réel (best-effort, à chaque consommation) | Système (cost_tracker / usage_tracker) |
| Agrégation chargeback | **Mensuelle** (clôture) ; vue glissante quotidienne possible | FinOps |
| Rapprochement facture Microsoft → `REEL_MESURE` | Mensuelle, après réception facture | Contrôle de gestion |
| Révision de la grille `AC360_RATE_CARD` | À chaque évolution tarifaire Microsoft | Admin Power Platform |

---

## 6. Restitution (dashboards)

- **FinOps → Coûts par poste** : somme `estimated_cost_eur` par `cost_center`, avec ventilation du `cost_source` (part `A_VALIDER` vs `PARAMETRABLE` vs `REEL_MESURE`).
- **FinOps → Par dimension** : top commerciaux (hash), top équipes, top clients (hash), top cas d'usage.
- **FinOps → Budget** : consommation cumulée vs `AC360_BUDGET_EUR`, jauge à `AC360_BUDGET_WARN_PCT` (défaut 80 %).

> **Tant que les montants sont `A_VALIDER`, les dashboards doivent afficher la volumétrie (messages, pages, documents, actions, runs) comme indicateur principal**, et le coût € uniquement en colonne secondaire estampillée « À VALIDER EN ENVIRONNEMENT RÉEL ».

---

## 7. Articulation avec le budget (rappel : aucun blocage automatique)

La refacturation **n'est pas** un mécanisme de contrôle. Le suivi budgétaire est porté par `check_budget()` (`scripts/cost_tracker.py`) :

| Niveau retourné | Condition | Effet |
|---|---|---|
| `unknown` | Aucun budget configuré (`AC360_BUDGET_EUR` absent ou ≤ 0) | Aucun |
| `ok` | `ratio < AC360_BUDGET_WARN_PCT` | Aucun |
| `warning` | `ratio ≥ AC360_BUDGET_WARN_PCT` (défaut **80 %**) | Émission `budget_warning_triggered` ; notification |
| `exceeded` | `ratio ≥ 100 %` | Notification ; **décision de blocage = humaine** (kill-switch admin) |

`check_budget()` **ne bloque jamais** (no auto-block). Le blocage éventuel (`user_blocked`, `bot_emergency_stopped`) est une **décision administrateur** via kill-switch, tracée comme événement d'usage.

---

## 8. Procédure de validation des montants (sortir de `A_VALIDER`)

1. Récupérer les **tarifs réels** Microsoft (devis / facture / Azure Pricing) pour chaque `cost_center` applicable.
2. Construire le JSON `AC360_RATE_CARD`, ex. :
   ```json
   {"copilot_studio_message": 0.000, "ocr_document_intelligence": 0.000, "fabric_onelake": 0.000}
   ```
   (Valeurs `0.000` ci-dessus = **placeholders** : à remplacer par les vrais prix ; aucune valeur n'est suggérée ici.)
3. Injecter `AC360_RATE_CARD` via Key Vault / app settings (sans redéploiement). Les postes renseignés passent de `A_VALIDER` à `PARAMETRABLE`.
4. **Rapprocher** mensuellement le total estimé avec la facture Microsoft réelle ; les postes validés passent à `REEL_MESURE` (étape comptable, hors code).

> Une valeur invalide dans `AC360_RATE_CARD` est **ignorée proprement** par `load_rate_card()` (jamais de substitution par un prix arbitraire).

---

## 9. Limites et précautions

- **Anonymisation = pas de réidentification commerciale directe.** Les identifiants commercial/client sont des **hash SHA-256** (`hash_id`, normalisation `strip().lower()`). La correspondance hash → personne **n'est pas dans le repo** : elle suppose une **table de correspondance gérée séparément par l'admin**, sous contrôle d'accès. Sans elle, le chargeback est **anonyme** par construction.
- **Tokens estimés.** Les compteurs `estimated_tokens_input` / `estimated_tokens_output` sont **estimés** — Copilot Studio n'expose pas les tokens réels. Ils ne doivent pas servir de base de refacturation à l'unité de token.
- **Fabric facturé à la capacité.** `fabric_onelake` est lu en **lecture seule** ; Microsoft Fabric facture généralement par **capacité réservée**, pas par requête. La clé de répartition par requête est une **approximation d'allocation** à valider (`A_VALIDER`).
- **OCR F0.** Le palier **F0** de Document Intelligence a des limites propres ; le modèle de coût page/document doit être confirmé sur l'abonnement réel.
- **Best-effort.** L'émission des événements ne casse jamais le métier (exceptions avalées) : une consommation isolée peut manquer en cas d'incident de sink → le chargeback est **indicatif**, pas un journal comptable certifié.
- **Périmètre prod.** Seuls les `cost_event` `environment = "prod"` doivent être refacturés ; `dev` / `test` / `uat` / `staging` sont exclus.

---

## 10. Références

- `scripts/cost_tracker.py` — postes, grille, `estimate_cost`, `check_budget`
- `scripts/usage_tracker.py` — volumétrie par dimension
- `schemas/cost_event.schema.json` — contrat du `cost_event`
- `schemas/usage_event.schema.json` — contrat du `usage_event`
- `docs/observability/ALERTING_RULES.md` — règles d'alerte (budget, OCR, latence, RAG, anomalies)
- `docs/observability/LOGGING_POLICY.md` — politique de journalisation et anonymisation
