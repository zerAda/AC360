# Guide Administrateur — AC360 Assistant Commercial Client 360

> **Version :** 2.1.0 | **Date :** Juin 2026 | **Public :** DSI / Équipe IT GEREP

---

## 🏗️ Architecture du Projet

AC360 est un assistant d'entreprise bâti sur l'architecture suivante :

1. **Microsoft Copilot Studio** : Le moteur conversationnel hébergé sur le tenant Power Platform GEREP. Gère les topics, l'orchestration RAG et l'interface Teams.
2. **SharePoint Online** : La source de connaissances unique (Knowledge Source). Les documents commerciaux y sont indexés.
3. **Backend API (FastAPI / Python)** : Gère les tâches avancées hors RAG standard (pipeline OCR, intégration Microsoft Fabric, génération de fichiers Word locaux).
4. **Authentification** : Microsoft Entra ID (Integrated Auth) sans token pass-through manuel, géré de façon native par Teams.

---

## 🚀 Déploiement et Cycle de Vie (ALM)

Le bot est stocké localement sous forme de code YAML et poussé vers Copilot Studio à l'aide de Microsoft Power Platform CLI (`pac`).

### Pré-requis
- Power Platform CLI installé (`dotnet tool install --global Microsoft.PowerApps.CLI.Tool`)
- Droit "System Customizer" ou "Environment Maker" sur l'environnement Power Platform.

### Déployer les mises à jour
Utilisez le script PowerShell fourni dans `scripts/sync_copilot.ps1`.

1. **Synchroniser depuis le cloud vers Git (Pull)**
   ```powershell
   .\scripts\sync_copilot.ps1 -Mode Pull
   ```

2. **Déployer de Git vers Copilot Studio (Push)**
   ```powershell
   .\scripts\sync_copilot.ps1 -Mode Push
   ```
   > ⚠️ Le script s'occupe de mettre à jour le workspace PAC (`src/copilot-workspace/AC360`). Vous devez ensuite vous rendre sur le portail Copilot Studio pour cliquer manuellement sur le bouton **Publier** (bug connu du PAC CLI v2.8.1).

---

## 🔒 Gestion des Secrets et Environnement

L'API Backend nécessite un fichier `.env` à la racine (voir `.env.example`).

| Variable | Description | Criticité |
|---|---|---|
| `TENANT_ID` | Identifiant du Tenant Azure AD | Obligatoire (Fail-fast si absent) |
| `CLIENT_ID` | Client ID de l'App Registration | Obligatoire |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | Clé pour le monitoring Azure | Recommandé |
| `JOBS_BASE_DIR` | Dossier de traitement local | Défaut: `./jobs` |

> 🚫 Ne commitez jamais le `.env` dans Git.
> 🚫 `scan_secrets.ps1` est exécuté lors de l'intégration pour prévenir les fuites de clés.

---

## 📊 Application Insights (Monitoring)

Le backend API est instrumenté pour envoyer ses télémétries à **Azure Application Insights**.
L'intégration s'effectue via un Middleware FastAPI qui logue la durée des requêtes, les codes HTTP et les exceptions.

**Pour l'activer :**
1. Créez une instance Application Insights dans Azure.
2. Copiez la clé d'instrumentation (Instrumentation Key).
3. Ajoutez-la dans le `.env` : `APPINSIGHTS_INSTRUMENTATIONKEY=votre-cle-ici`.
4. (Optionnel) Configurez également Application Insights dans Copilot Studio (Paramètres -> Analytique).

---

## 🛡️ Sécurité & Audits

AC360 a passé un audit de sécurité hostile (Juin 2026 - Score 96/100).
Voici les points de conception de sécurité clés :

- **Knowledge RAG** : `useModelKnowledge` est à `false`. Le bot ne peut pas répondre à partir de modèles génériques ou d'Internet. Il est limité à SharePoint.
- **Data Loss Prevention** : Les connecteurs personnalisés (ex: WorkIQ) ont été supprimés en l'absence de politique DLP stricte.
- **Authentification Backend** : Le backend vérifie systématiquement le token JWT via les clés publiques Microsoft (`/discovery/v2.0/keys`).
- **Prévention Path Traversal** : L'API n'accepte que des UUID v4 en paramètre de document, et valide le chemin résolu avec `os.path.commonpath`.

---

## 🆘 Troubleshooting

**Problème : Les tests locaux (Pytest) crashent au démarrage.**
Solution : Utilisez le lanceur PowerShell ou définissez manuellement `TENANT_ID` et `CLIENT_ID` avant l'exécution. `config.py` fait un fail-fast si ces variables manquent.

**Problème : Le bot répond qu'il ne trouve pas de document pour un client, pourtant le document est sur SharePoint.**
Solution : Le bot ne recherche que les documents auxquels l'utilisateur a accès. Demandez à l'utilisateur de vérifier s'il peut ouvrir le document dans son navigateur. Les indexations SharePoint peuvent parfois prendre quelques minutes.

**Problème : L'API renvoie une erreur 429 Rate Limit.**
Solution : Le rate limiter in-memory bloque les appels excessifs (ex: > 10 audits / heure / utilisateur) pour protéger le pipeline OCR. Ajustez `_RATE_LIMIT_MAX` dans `api_server.py` si nécessaire.
