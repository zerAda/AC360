# Performance — exploiter au mieux la machine (sans la faire tomber)

Objectif : **maximum de débit/qualité** pour le matériel réellement présent, en
gardant une **marge OS** (utiliser 100 % de la RAM → gel / OOM, inacceptable).
Tout est calibré automatiquement par `make tune` ; ce document explique *quoi* et
*pourquoi*, avec les compromis (pas de réglage « magique »).

## 1. Auto-tuning : la voie recommandée

```bash
make tune     # détecte CPU/RAM/GPU et ÉCRIT les valeurs optimales dans .env
make secrets  # (si pas déjà fait)
make up       # + GPU=1 si GPU NVIDIA, + PERF=1 si machine confortable
make verify
```

`make tune` choisit notamment :
- le **plus gros modèle qui tient** (RAM dispo ou VRAM) ;
- les **limites mémoire** proportionnelles à la RAM (heap OpenSearch, model-server, etc.) ;
- les **réglages perf Ollama** ci-dessous ;
- la **réserve OS** (≈ RAM/8, plancher 2 Go) pour ne jamais saturer la machine.

> `make tune` ne touche **pas** vos secrets ; il ne modifie que les clés de réglage.

## 2. Les réglages Ollama qui comptent vraiment

| Variable | Effet | Compromis |
|---|---|---|
| `OLLAMA_FLASH_ATTENTION=1` | Attention plus rapide, **−30 à −50 % de mémoire de contexte (KV)**. | Léger sur certains modèles ; bénéfice surtout GPU, neutre/positif en CPU. |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | Quantifie le cache KV → **moitié de RAM/VRAM de contexte** (permet + de contexte ou + gros modèle). | `q8_0` quasi sans perte ; `q4_0` plus agressif. **Actif seulement si Flash Attention = 1.** |
| `OLLAMA_KEEP_ALIVE=-1` | Modèle **toujours chargé** → zéro latence de rechargement. | Occupe la RAM en permanence. `make tune` met `-1` si RAM ≥ ~12 Go, sinon `5m`. |
| `OLLAMA_NUM_PARALLEL` | Requêtes concurrentes par modèle (débit multi-utilisateur). | Chaque requête = un slot KV en plus → coût RAM/VRAM. |
| `OLLAMA_MAX_LOADED_MODELS` | Garde chat **et** embeddings chargés ensemble. | +RAM. `2` si RAM ≥ ~16 Go. |

Sources : [Ollama FAQ](https://docs.ollama.com/faq) · [Ollama — Troubleshooting & Performance](https://deepwiki.com/ollama/ollama/6.4-troubleshooting-and-performance) · [KV cache quantization](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/).

> Sur **CPU**, le nombre de threads est auto-détecté par Ollama (= cœurs physiques),
> ce qui est optimal : on **ne** force **pas** `num_thread` (le forcer dégrade souvent).

## 3. Choix du modèle (qualité vs vitesse)

`make tune` retient le plus gros modèle « raisonnable » :

| Ressource | Modèle retenu | Note |
|---|---|---|
| GPU VRAM ≥ 24 Go | `qwen2.5:32b-instruct` | Excellente qualité FR. |
| GPU VRAM ≥ 12 Go / CPU RAM ≥ 24 Go | `qwen2.5:14b-instruct` | Très bon compromis. |
| GPU VRAM ≥ 8 / CPU RAM ≥ 12 | `llama3.1:8b` | Rapide, solide. |
| CPU RAM 7-12 | `qwen2.5:7b-instruct` | — |
| Plus petit | `llama3.2:3b` (ou `:1b`) | Postes contraints. |

> En **CPU**, un modèle plus gros = plus « intelligent » mais **plus lent**
> (tokens/s). Au-delà de 14B en CPU pur, la latence devient inconfortable :
> `make tune` plafonne donc à 14B en CPU (32B reste possible manuellement).

## 4. Onyx — débit d'indexation

- `make up PERF=1` rétablit un **model-server d'indexation dédié** : l'indexation
  ne se dispute plus les ressources avec l'inférence (≈ +3-5 Go RAM). Recommandé
  par `make tune` si RAM ≥ 32 Go (ou GPU + 24 Go).
- `OPENSEARCH_HEAP` ≈ 20 % de la RAM (plafond 8 Go) ; conteneur = 2× le heap.

## 5. GPU NVIDIA

`make up GPU=1` (nécessite `nvidia-container-toolkit`). Le GPU décuple le débit et
permet de plus gros modèles. Sur **macOS**, Docker n'accède pas au GPU → pour
exploiter Metal, lancer **Ollama en natif** (cf. `RUNBOOK.md` §8). Sur **Windows**,
le GPU passe par le backend **WSL2** de Docker Desktop.

## 6. Hygiène hôte

- Linux : `vm.max_map_count >= 262144` (OpenSearch) — vérifié par `make verify`.
- Disque **SSD/NVMe** fortement recommandé (index OpenSearch + I/O modèles).
- Surveiller en direct : `make stats`. Si un service est bridé, relancer `make tune`
  (RAM ajoutée ?) ou ajuster les `*_MEM_LIMIT` dans `.env`.

## 7. Ce qu'on ne fait PAS (anti-cargo-cult)

- Pas de suppression des **limites mémoire** : elles évitent l'OOM-kill de l'hôte
  (on les dimensionne large, on ne les retire pas).
- Pas de `num_thread` forcé en CPU (l'auto-détection d'Ollama est meilleure).
- Pas de `q4_0` par défaut (perte de qualité) : `q8_0` est le bon compromis.
