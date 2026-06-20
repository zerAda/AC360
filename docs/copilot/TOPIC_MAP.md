# AC360 — Cartographie end-to-end (intent → topic → backend → outil)

> **Réécrit le 2026-06-10** après audit de câblage. Remplace la version du
> 2026-06-03 devenue **inexacte** (elle attribuait la recherche aux MCP alors
> que c'est `SearchAndSummarizeContent` natif, et décrivait `LancerAudit` comme
> un upload PDF/Excel expérimental). Source de vérité : les `.mcs.yml` réels +
> les routes de `scripts/api_server.py`.

## Comment lire la chaîne

```
Utilisateur (chat) → Topic (.mcs.yml) → mécanisme → backend → outil/donnée
```

Deux mécanismes coexistent (orchestration **générative désactivée** :
`settings.mcs.yml → GenerativeActionsEnabled: false` → tout passe par des topics) :

- **RAG natif** : `SearchAndSummarizeContent` sur la knowledge SharePoint
  (`Dossiers_Clients_POC`) → réponse sourcée, citations natives.
- **Action HTTP** : `HttpRequestAction` → **passerelle** `ac360-gateway-staging`
  (auth `System.User.AccessToken`) → Azure Function / Graph.

## Sécurité d'accès — superposition RBAC SharePoint

Les deux chemins lisent SharePoint **avec l'identité de l'utilisateur**, jamais au
nom du bot :

| Chemin | Identité | Trimming RBAC |
|---|---|---|
| RAG natif (`SearchAndSummarizeContent`) | utilisateur (auth intégrée) | ✅ natif Graph |
| Audit (`/api/audit`) | utilisateur via **On-Behalf-Of** | ✅ `download_as_user` côté Function |

Flux audit : token utilisateur (aud = passerelle) → la passerelle fait l'**échange
OBO** (`scripts/graph_obo.py`) → token Graph délégué → pré-vérification d'accès au
bord (`_assert_user_can_access_document`, échec rapide 403/404) → la Function
télécharge **au nom de l'utilisateur** (`X-MS-Graph-Token`). Aucun jeton n'est
persisté dans l'état Durable (seul un chemin local transite). Pas d'accès → 403,
l'audit ne démarre pas. `AC360_REQUIRE_OBO=true` ferme la porte si OBO absent.

## Routes passerelle (vérité — `api_server.py`)

| Route | Méthode | Appelée par (topic) |
|---|---|---|
| `/api/documents/resolve` | POST | **LancerAudit** ✅ (résolution en langage naturel, as-user/OBO) |
| `/api/audit` | POST | **LancerAudit** ✅ (câblé ce jour) |
| `/api/audit/{job}/status` | GET | **LancerAudit** + **StatutAudit** ✅ |
| `/api/planner/task` | POST | **CreerRelancePlanner** ✅ |
| `/api/generate-fiche-rdv` | POST | **GenererFicheRDV** ✅ |
| `/api/download/{job}/{file}` | GET | ⚠️ **aucun topic** (orphelin partiel — le fichier FIC est généré mais pas proposé au téléchargement) |
| `/health` | GET | supervision |

## Topics RAG (SearchAndSummarizeContent → SharePoint) — `PROUVÉ` (YAML valide, anti-silent-RAG)

| Topic | Intention | Mécanisme | Sortie |
|---|---|---|---|
| `Rsumdossierclient` | Résumé client | RAG natif | Synthèse + sources |
| `Recherchedocumentclient` | Retrouver un document | RAG natif | Extrait + source |
| `Documentsmanquants` | Pièces manquantes | RAG natif | Liste priorisée |
| `Pointsattentionclient` | Alertes / risques | RAG natif | Liste 🔴🟡🟢 |
| `Brouillonmailcommercial` | Brouillon mail | RAG natif | Mail (à valider, pas d'envoi auto) |
| `Argumentsdevente` | Arguments sourcés | RAG natif | Liste sourcée |
| `Recherchejuridiquedocumentaire` | Clause/obligation | RAG natif | Extrait + avertissement juridique |
| `PreparationRDVRenouvellement` / `Prparationrendez-vousclient` | Briefing RDV | RAG natif | Fiche briefing |
| `AnalyseConcurrence`, `ComparaisonTarifaireConcurrents`, `AnalyseGapCouverture`, `AlertesRenouvellement`, `SuiviSinistralite`, `TableauDeBordPortefeuille` | Analyses portefeuille | RAG natif | Synthèses sourcées |

> Tous ces topics suivent le **gold pattern** (cf. `Rsumdossierclient`) :
> `SearchAndSummarizeContent` → `ConditionGroup IsBlank(Topic.Answer)` →
> affichage **ou** fallback explicite. Aucune réponse silencieuse.

## Topics ACTION (HTTP → passerelle → backend) — câblage corrigé ce jour

| Topic | Route | Backend → outil | Statut |
|---|---|---|---|
| **LancerAudit** | POST `/api/audit` puis GET `/status` | Durable Function → OCR F0 + Fabric OneLake (lecture seule) → verdict | ✅ **câblé** (était un stub « en cours de déploiement ») |
| **StatutAudit** (nouveau) | GET `/api/audit/{job}/status` | relecture verdict orchestration async | ✅ nouveau |
| **CreerRelancePlanner** | POST `/api/planner/task` | Graph → Microsoft Planner | ✅ (hôte corrigé) |
| **GenererFicheRDV** | POST `/api/generate-fiche-rdv` | génération FIC (.docx) | ✅ (hôte corrigé) ; corps encore générique (cf. résiduel) |

## Topics sécurité / contrôle — `PROUVÉ`

`Refusmodificationdocument` (refuse modif/suppression — lecture seule),
`Clarificationclient` (lève l'ambiguïté multi-client). Conformes à la policy
RAG de `agent.mcs.yml` (anti-injection, anti-promesse, lecture seule).

## Topics système

`ConversationStart`, `Greeting`, `Goodbye`, `ThankYou`, `Fallback`, `Escalate`,
`OnError`, `MultipleTopicsMatched`, `ResetConversation`, `StartOver`, `Signin`,
`EndofConversation` — flux conversationnel natif.

## MCP & connecteurs

> **Mise à jour (2026-06-19, commit `5f18cfa` — durcissement F1)** : les trois
> connecteurs MCP **Work IQ Preview** (`shared_workiqsharepoint`,
> `shared_a365copilotchatmcp`, `shared_a365memcp`) ont été **SUPPRIMÉS**. Aucun
> topic ne les appelait ; ils constituaient une surface latente d'accès
> cross-tenant (`mcp_m365copilot` pouvait atteindre du contenu hors du site
> scopé `Dossiers_Clients_POC`, `mcp_MeServer` les données M365 de l'utilisateur).
> `connectionreferences.mcs.yml` est désormais **vide** (`connectionReferences: []`)
> et le dossier `actions/` ne contient plus de connecteur. Suppression vérifiée en
> source et redéployée sur le **brouillon** de l'agent.

> **Décision d'architecture** : la recherche documentaire passe par le **RAG natif
> SharePoint** (sourcé, citations, sécurisé par la policy), pas par des connecteurs
> MCP. Aucune source non gouvernée n'est sur le chemin critique.

## Couverture des cas d'usage (réelle)

| Cas d'usage | Topic | Câblage E2E |
|---|---|---|
| Résumé / recherche / docs manquants / points d'attention / mail / arguments / RDV / analyses | RAG natif | ✅ PROUVÉ (YAML) |
| **Audit documentaire (OCR + Fabric)** | LancerAudit + StatutAudit | ✅ **câblé ce jour** (passerelle déployée + E2E backend prouvé) |
| Relance Planner | CreerRelancePlanner | ✅ |
| Génération FIC | GenererFicheRDV | ✅ (corps à enrichir) |
| Multi-client | — | ❌ refusé **par design** (sécurité) |

## Pré-requis runtime — `À VALIDER EN ENVIRONNEMENT RÉEL`

1. **🔴 CRITIQUE — Audience du jeton (make-or-break).** Les actions HTTP envoient
   `="Bearer " & System.User.AccessToken`. Pour que la passerelle accepte le jeton
   ET que l'OBO fonctionne, ce jeton DOIT avoir **aud = app passerelle** et le
   scope `api://5399f31e-c4d5-46db-b620-033e59abda84/Audit.Trigger`.
   Or `settings.mcs.yml` est en `authenticationMode: Integrated` (« Authenticate
   with Microsoft »), où `System.User.AccessToken` n'est **pas** garanti de porter
   une audience custom. Action requise côté tenant : configurer l'**auth Entra ID
   de l'agent** (SSO) pour exposer/demander ce scope (Expose an API + consentement
   délégué). Sinon → 401 systématique, l'audit ne marche jamais. **À VALIDER.**
2. **OBO délégué** : l'app passerelle doit avoir la permission **déléguée**
   `Files.Read.All` (ou `Sites.Read.All`) **consentie**, plus `OBO_CLIENT_SECRET`.
   Sans cela, l'échange OBO échoue (et avec `AC360_REQUIRE_OBO=true`, l'audit est
   refusé proprement). **À VALIDER.**
3. **URL passerelle** : l'hôte **staging** est codé en dur dans les topics.
   **Recommandation prod** : variable d'environnement Power Platform
   (`Env.<gatewayBaseUrl>`) pour porter dev/staging/prod sans réédition.

## Résiduels (non bloquants)

- ✅ **Rendu du verdict** : corrigé — le statut est mis à plat côté passerelle
  (`verdict`/`client`/`score` au premier niveau) et les topics affichent une fiche
  lisible (plus de JSON brut).
- ✅ **UX identifiant document** : corrigé — `LancerAudit` demande désormais une
  recherche en langage naturel (« contrat GEREP »), résolue par
  `/api/documents/resolve` (Graph search **au nom de l'utilisateur** via OBO,
  filtre extensions auditables, tri récence, choix par numéro si plusieurs).
  Plus aucun GUID demandé au commercial.
- `/api/download/{job}/{file}` : non surfacé par un topic (FIC générée mais pas
  proposée en téléchargement dans le chat ; un lien chat ne peut pas porter le
  bearer — nécessite un lien pré-signé ou une remise via Graph).
- `GenererFicheRDV` : corps de requête générique (`summary`/`alert_points`
  placeholders) — à alimenter depuis une synthèse préalable.
