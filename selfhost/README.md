# AC360 — Stack IA privée auto-hébergée (Onyx + Ollama)

![Déploiement](https://img.shields.io/badge/D%C3%A9ploiement-Docker%20Compose-blue)
![LLM](https://img.shields.io/badge/LLM-Ollama%20local-black)
![RAG](https://img.shields.io/badge/RAG-Onyx%20v4.1.1-green)
![Données](https://img.shields.io/badge/Donn%C3%A9es-100%25%20locales-success)

> Assistant IA **100 % auto-hébergé et souverain** : **Onyx** (recherche RAG +
> chat sur vos documents) propulsé par **Ollama** (LLM exécuté localement).
> **Aucune donnée ne quitte la machine** — aucun appel à un fournisseur cloud,
> aucune télémétrie. Conçu pour un poste local, durci pour un usage exigeant.

Ce module est un **kit clé en main, auto-contenu et épinglé** : un seul fichier
`docker-compose.yml` auditable, images figées, secrets générés localement, et un
`Makefile` qui pilote tout. Pas de `curl | bash`, pas de dépendance cachée.

---

## Architecture

```
        Navigateur (http://localhost:3000)
                │   (lié à 127.0.0.1 uniquement)
                ▼
        ┌───────────────┐
        │     nginx     │  point d'entrée unique, config maison
        └───┬───────┬───┘
            │       │
       /api │       │ /
            ▼       ▼
   ┌────────────┐  ┌────────────┐
   │ api_server │  │ web_server │   (Onyx — FastAPI + Next.js)
   └─────┬──────┘  └────────────┘
         │  réseau Docker privé (ac360-local-ai-net) — rien d'exposé
         ├──────────────┬───────────────┬──────────────┐
         ▼              ▼               ▼              ▼
   ┌──────────┐  ┌────────────┐  ┌───────────┐  ┌──────────┐
   │ Postgres │  │ OpenSearch │  │   MinIO   │  │  Redis   │
   └──────────┘  └────────────┘  └───────────┘  └──────────┘
         │              ▲
         ▼              │ embeddings / reranking
   ┌──────────────┐     │
   │ background   │─────┘   ┌──────────────────────────────┐
   │ (indexation) │         │ inference_model_server       │
   └──────────────┘         └──────────────────────────────┘
                                       
   ┌───────────────────────────────────────────────────────┐
   │  ollama  (LLM LOCAL — http://ollama:11434, INTERNE)    │
   │  aucun port publié sur l'hôte ; modèles dans un volume │
   └───────────────────────────────────────────────────────┘
```

Seul **nginx** publie un port, et **uniquement sur `127.0.0.1`**. Ollama et
toutes les briques de données restent sur le **réseau Docker interne**.

---

## Prérequis

| Élément | Détail |
|---|---|
| Docker | Docker Engine + **Docker Compose v2** (`docker compose`) |
| RAM | **16 Go minimum** (24 Go+ confortable). `make detect` calibre tout. |
| Disque | ~20 Go (images + modèles + index) |
| Linux | `vm.max_map_count >= 262144` (OpenSearch) — voir Dépannage |
| GPU | Optionnel (NVIDIA). Par défaut **CPU**. |

---

## Démarrage rapide (4 étapes)

```bash
cd selfhost

make detect     # 1. Diagnostic CPU/RAM/GPU → valeurs .env recommandées
make secrets    # 2. Crée .env + génère des secrets forts (chmod 600)
make up         # 3. Démarre la stack + pré-télécharge les modèles Ollama
make verify     # 4. Contrôle santé + câblage Onyx↔Ollama + test de génération
```

Puis ouvrez **http://localhost:3000**. Le **premier compte créé devient
administrateur**.

> 1er lancement : prévoir plusieurs minutes (téléchargement des images, des
> modèles Ollama et des modèles d'embedding). `make verify` confirme l'état.

### Connexion Onyx ↔ Ollama (assistant de 1ère connexion)

À la première connexion, Onyx demande le fournisseur de modèle. Renseignez :

| Champ | Valeur |
|---|---|
| Provider | **Ollama** |
| API Base URL | **`http://ollama:11434`** *(nom de service interne, pas `localhost`)* |
| Modèle | `llama3.2:3b` *(ou celui recommandé par `make detect`)* |

Le câblage réseau est déjà en place et **vérifié par `make verify`** : il ne
reste que ces 3 champs. Détails et capture pas-à-pas : [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## Sécurité (résumé)

- **Localhost only** : nginx lié à `127.0.0.1`. Rien d'accessible depuis le réseau.
- **Ollama isolé** : aucun port hôte ; joignable uniquement par Onyx en interne.
- **Secrets** : générés localement, `.env` gitignoré + `chmod 600`. Zéro secret en repo.
- **Surface réduite** : `code-interpreter` (montait le **socket Docker**), `certbot`
  et `mcp_server` **retirés par défaut**.
- **Zéro fuite** : `DISABLE_TELEMETRY=true`, aucun LLM cloud, données 100 % locales.
- **Auth** : comptes locaux (`basic`) ; énumération des comptes réservée aux admins.

Baseline complète et checklist : [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Exploitation

| Action | Commande |
|---|---|
| État des services | `make ps` |
| Consommation ressources | `make stats` |
| Journaux | `make logs` |
| Mettre à jour (tag épinglé) | `make update` |
| Sauvegarder / restaurer | `make backup` / `make restore DIR=backups/…` |
| Tout arrêter | `make down` |
| Profil GPU NVIDIA | `make up GPU=1` |

Runbook détaillé (upgrade, incidents, scaling, Ollama natif) : [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## Arborescence

```
selfhost/
├── docker-compose.yml        # stack complète durcie (fichier unique auditable)
├── docker-compose.gpu.yml    # override GPU NVIDIA (optionnel)
├── env.template              # gabarit → copié en .env (gitignoré)
├── Makefile                  # pilotage une-commande
├── nginx/onyx.conf           # reverse proxy maison (localhost)
├── scripts/
│   ├── detect-hardware.sh    # diagnostic matériel (Linux/macOS)
│   ├── detect-hardware.ps1   # diagnostic matériel (Windows)
│   ├── gen-secrets.sh        # génération des secrets
│   ├── pull-models.sh        # téléchargement des modèles Ollama
│   ├── verify.sh             # vérification de bout en bout
│   └── backup.sh / restore.sh
└── docs/
    ├── ARCHITECTURE.md       # composants, flux, modèle de menace
    ├── SECURITY.md           # baseline + checklist de durcissement
    ├── RUNBOOK.md            # exploitation, upgrade, dépannage, scaling
    └── RGPD.md               # souveraineté & protection des données
```

---

## Lien avec AC360

AC360 (Copilot Studio / Azure / SharePoint) reste la solution d'entreprise
intégrée à Microsoft 365. Cette stack en est le **pendant local et souverain** :
même logique RAG, mais **données et inférence 100 % sur site** — utile pour les
environnements sensibles, les démos hors-ligne, ou les exigences de
non-transfert de données. Voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
