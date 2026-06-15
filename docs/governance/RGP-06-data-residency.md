# RGP-06 — Confirmation de résidence des données (EU data residency)

**Exigence :** RGP-06 (confirmation que les données client résident en UE ; transferts hors UE = néant).
**Statut :** **partiel** — résidence des ressources pilotées par Bicep **vérifiable maintenant** ; résidence des surfaces tenant-level (M365 / Fabric / Power Platform) = **point de contrôle opérateur** (agrège Phase 2, Plan 02-06 ; confirmée au Plan 05-07).
**Dernière MAJ :** 2026-06-15.

> ⚠️ La résidence UE **ne peut pas** être affirmée à partir des seules valeurs Bicep `location` (RESEARCH Pitfall 5). Ce document **sépare explicitement** ce qui est prouvé par l'IaC de ce qui exige une vérification opérateur dans le tenant GEREP live. **Les lignes du second tableau ne sont PAS affirmées comme confirmées.**

---

## 1. Exigence de résidence

Les documents client traités par AC360 contiennent de la **PII** (identité, données financières, potentiellement IBAN/numéros captés par OCR). La conformité RGPD/CNIL impose que ces données et leur télémétrie résident en **Union européenne** et qu'aucun **transfert hors UE** ne survienne sans base légale. AC360 vise la résidence **France Central** (primaire), avec **West Europe** comme unique repli EU autorisé pour Document Intelligence (dispo S0).

## 2. Vérifiable maintenant — valeurs Bicep `location`

Toutes les ressources Azure déclarées dans l'IaC héritent de `param location` (`infra/main.bicep:15`, défaut `resourceGroup().location`), fixé à **`francecentral`** dans `infra/prod.parameters.json`. Document Intelligence utilise `docIntelLocation` (`infra/main.bicep:41`), également **`francecentral`** en prod (repli EU `westeurope` documenté). Ces valeurs sont **vérifiables offline** (`az bicep build` + lecture des paramètres).

| Composant | Ressource Bicep | Région (valeur `location`) | Comment c'est confirmé |
|-----------|-----------------|----------------------------|------------------------|
| App Service gateway (FastAPI) | `gatewayApp` `Microsoft.Web/sites` (main.bicep:463) | `location` = **francecentral** | `infra/prod.parameters.json` `location: francecentral` |
| Plan App Service gateway | `gwPlan` `Microsoft.Web/serverfarms` (main.bicep:398) | `location` = **francecentral** | idem |
| Azure Functions (Flex) | `functionApp` `Microsoft.Web/sites` (main.bicep:412) | `location` = **francecentral** | idem |
| Plan Functions | `funcPlan` `Microsoft.Web/serverfarms` (main.bicep:366) | `location` = **francecentral** | idem |
| Azure Storage (état Durable + artefacts) | `storage` `Microsoft.Storage/storageAccounts` (main.bicep:177) | `location` = **francecentral** | idem ; `storageSku: Standard_GRS` (réplication **intra-EU**, paire France) |
| Key Vault | `keyVault` `Microsoft.KeyVault/vaults` (main.bicep:248) | `location` = **francecentral** | idem |
| Document Intelligence (OCR) | `docIntel` `Microsoft.CognitiveServices/accounts` (main.bicep:319) | `docIntelLocation` = **francecentral** (repli EU **westeurope**) | `infra/prod.parameters.json` `docIntelLocation: francecentral` ; repli locké EU (Plan 02-06 Checkpoint 1) |
| Log Analytics workspace | `law` `Microsoft.OperationalInsights/workspaces` (observability.bicep:57) | `location` (threadé) = **francecentral** | rétention 90 j EU (RGP-04 §4) |
| Application Insights (workspace-based) | `appi` (observability.bicep:251) | `location` = **francecentral** ; gouverné par le workspace | RGP-04 §4 |

**Conclusion du tableau :** **toutes** les ressources pilotées par Bicep sont en **région EU (France Central)**, avec Storage en GRS intra-EU et DocIntel borné à un repli EU. Résidence Azure-IaC = **confirmée maintenant**.

## 3. Point de contrôle opérateur (tenant live) — NON confirmé ici

Les surfaces suivantes **ne sont pas déclarées dans Bicep** : leur résidence dépend de la configuration du **tenant GEREP live** et constitue un **point de contrôle opérateur**. Ces lignes **agrègent le checkpoint de résidence de la Phase 2 (Plan 02-06, Checkpoint 1)** et sont **confirmées au Plan 05-07** — elles ne doivent **pas** être lues comme confirmées.

| Surface tenant-level | Pourquoi hors Bicep | Statut | Confirmation |
|----------------------|---------------------|--------|--------------|
| **M365 tenant geo** | Géolocalisation du tenant M365/SharePoint définie au niveau tenant | **À confirmer (opérateur)** | Agrège Phase 2 / Plan 02-06 Checkpoint 1 (« M365 tenant geo = EU : ____ ») → Plan 05-07 |
| **Fabric — région de capacité** | Capacité Fabric/OneLake (système de référence ARTUS) provisionnée hors IaC | **À confirmer (opérateur)** | Agrège Phase 2 / Plan 02-06 Checkpoint 1 (« Fabric capacity region = EU : ____ ») → Plan 05-07 |
| **Power Platform / Copilot Studio — région de l'environnement** | Région de l'environnement Copilot Studio définie dans Power Platform, hors Azure Bicep | **À confirmer (opérateur)** | Agrège Phase 2 / Plan 02-06 Checkpoint 1 (« Power Platform environment region = EU : ____ ») → Plan 05-07 |
| **Webtest — `Locations` de disponibilité** | Id de localisation `emea-nl-ams-azr` / `emea-fr-pra-edge` (observability.bicep:265) marqués **`[ASSUMED]`** EU dans l'IaC | **À confirmer (opérateur)** `[ASSUMED]` | Vérification des Id de localisation EU exacts au provisioning (Plan 02-06 Task 4 / A2) → Plan 05-07 |

> Tant que ces quatre lignes ne sont pas cochées par l'opérateur contre le tenant GEREP live, la résidence EU **globale** d'AC360 reste **partiellement non prouvée**. Ne pas les présenter comme « confirmées » dans le dossier RGPD (mitigation T-05-20 — éviter d'affirmer la résidence à partir de Bicep seul).

## 4. Transferts hors UE

**Néant** sur le périmètre Azure-IaC (tout en France Central / repli West Europe). Les transferts hors UE potentiels ne pourraient provenir que des surfaces tenant-level du §3 si elles étaient configurées hors UE — d'où l'obligation du point de contrôle opérateur avant go-live. Le registre Art. 30 (RGP-01, champ « transferts pays tiers ») renvoie à ce document.

## 5. Conclusion

- **Vérifiable maintenant :** résidence **EU (France Central)** confirmée pour **toutes** les ressources Azure pilotées par Bicep (gateway, Functions, Storage GRS intra-EU, Key Vault, Document Intelligence, Log Analytics, Application Insights).
- **En attente opérateur :** résidence des **quatre surfaces tenant-level** — M365 tenant geo, région de capacité Fabric, région de l'environnement Power Platform/Copilot Studio, et les `Locations` `[ASSUMED]` du webtest — agrégées depuis la **Phase 2 (Plan 02-06)** et **confirmées au Plan 05-07**.

## 6. Références croisées

- `infra/main.bicep`, `infra/observability.bicep`, `infra/prod.parameters.json` — valeurs `location`.
- **Phase 2 / Plan 02-06** — `02-06-SUMMARY.md` Checkpoint 1 (EU residency + France Central availability).
- **RGP-04 §4** — rétention Log Analytics 90 j, région EU.
- **RGP-01** — registre Art. 30, champ transferts pays tiers (= néant).
- STATE.md §Blockers — blocker résidence EU (Fabric / M365 / Power Platform) à lever par l'opérateur.
