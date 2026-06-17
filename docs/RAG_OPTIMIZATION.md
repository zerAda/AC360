# Optimisation RAG & Ollama — audit de consultant (onix entreprise)

> Audit en profondeur (4 angles : retrieval/embeddings, génération/`num_ctx`/reranker/éval,
> inférence Ollama **mesurée**, scale/observabilité). Vérité-terrain : tag Onyx **v4.1.1**
> (valeurs citées du code) + **mesures réelles** sur 4 vCPU / 15,7 Go / sans GPU.
> Objectif : maximiser la **qualité RAG** sur corpus **français** et la **capacité** entreprise.

## Verdict
Infra/sécurité/HA = excellentes. Le **RAG tourne avec les défauts d'Onyx, non adaptés au FR**, et un `num_ctx` non maîtrisé. **~80 % du gain = réglages** (Onyx Search Settings + provider LLM) — pas du code.

## État des lieux (code v4.1.1)
| Sujet | Défaut réel (preuve) | Conséquence FR |
|---|---|---|
| Embedding | `nomic-ai/nomic-embed-text-v1` 768d **anglo**, dans le **model-server Onyx** (`model_configs.py:15`) | recall FR dégradé |
| `nomic-embed-text` tiré dans Ollama | **IGNORÉ** par le retrieval (Ollama = chat only ; issue #6189 *not planned*) | dépendance inutile |
| `num_ctx` | non défini → Ollama **4096**, **divisé par `NUM_PARALLEL`** → ~2048 utile (mesuré : prompt 3000 tok → **2035 ingérés**) | **troncature silencieuse** |
| Reranker | **OFF** (`DEFAULT_CROSS_ENCODER_MODEL_NAME=None`) | précision sous-optimale |
| Analyseur BM25 | **global `english`** (`OPENSEARCH_TEXT_ANALYZER`) | pas de stemming FR |
| Chunks → LLM | `MAX_CHUNKS_FED_TO_CHAT=25`, chunk 512/overlap 0, multipass OFF en CPU | 25×512≈12,8k tok : sature `num_ctx` |
| Hybride | α=0.5 ; `NUM_RETURNED_HITS=50` | OK, à calibrer |

## Deux interactions critiques (pièges)
1. **`num_ctx` × `MAX_CHUNKS_FED_TO_CHAT`** : prompt 6-7k + 25×512≈12,8k ≈ **19k tok** → intenable en CPU. Solution : **reranker → `MAX_CHUNKS_FED_TO_CHAT=8`** (≈4k) **+ `num_ctx=12288`**.
2. **`num_ctx` × `NUM_PARALLEL`** : Ollama **divise** le contexte par le nb de slots. Pour 8192 *utile/req* à NP=2 → fixer **`num_ctx=16384`** (ou NP=1 pour la qualité mono-utilisateur). RAM KV ≈ `num_ctx × NUM_PARALLEL`.

## Plan priorisé

### P0 — Quick-wins (réglages Onyx/`.env`, ~1-2 h)
| # | Action | Valeur exacte |
|---|---|---|
| 1 | Fixer `num_ctx` (Onyx « Max Input Tokens » ou Modelfile `PARAMETER num_ctx`) + RAM | **12288** (7B) / **8192** (3b) ; `OLLAMA_MEM_LIMIT` **7-8 Go** ; NP=2 voulant 8192 utile → 16384 |
| 2 | `MAX_CHUNKS_FED_TO_CHAT` ↓ | **8** (avec reranker) |
| 3 | Embedding FR multilingue (Search Settings → Self-hosted ; **re-index complet**) | `intfloat/multilingual-e5-large` (1024d) ou `BAAI/bge-m3` |
| 4 | Activer reranker (Search Settings) | `BAAI/bge-reranker-v2-m3` (ou `mxbai-rerank-xsmall` si 16 Go) ; retrieve 30-50 → top-n 8 |
| 5 | Analyseur BM25 FR (**re-index**) | `OPENSEARCH_TEXT_ANALYZER=french` |
| 6 | Modèle + température | `qwen2.5:7b-instruct` (Q4_K_M CPU / **Q5_K_M** GPU) ; `temperature 0.2` |
| 7 | Clarifier/retirer `nomic` Ollama | non utilisé par le retrieval ; garder seulement comme juge RAGAS |

> ⚠️ Embedder + analyseur changent → **2 ré-index** : les faire **ensemble**. Passer hors-`nomic` **désactive les large-chunks** d'Onyx → compenser par le reranker.

### P1 — Structurel (jours)
8. **Éval RAGAS local** (juge Ollama + golden set FR) : `make rag-eval`, faithfulness ≥0.90 / context-precision ≥0.70 / answer-relevancy ≥0.85, gate CI.
9. **Observabilité qualité** sur `access-gateway` (`/metrics` : taux no-context, citation, hit-rate, **P95 e2e**, feedback pouce) + scrape api/model-server/ollama.
10. **Scaler Ollama en K8s** (`replicaCount:1` = SPOF de débit) ; injecter le tuning Ollama dans `deploy/k8s/.../ollama.yaml` (aujourd'hui défauts incohérents).
11. **Fraîcheur** : Prune SharePoint **30 j → 1-3 j**.
12. **OpenSearch k-NN** : RAM hors-heap ≈ **18 Go/shard** pour 5 M vecteurs 768d.

## Capacité MESURÉE (4 vCPU, sans GPU)
| Modèle | tok/s mono | agrégé (NP=2) | Réponse ~300 tok | Users interactifs |
|---|---|---|---|---|
| `qwen2.5:7b` Q4_K_M | **5,8** | ~7,4 | ~52 s (mono) / ~80 s (2) | **1** (2-3 sporadiques) |
| `llama3.2:3b` | ~12-14 | ~12-14 | ~25 s | 2-3 |
| `llama3.2:1b` | ~15,5 | ~26 | ~12 s | 4-5 |

**Sur CPU, `num_ctx` n'ajoute pas de latence (mémoire only).** `NUM_PARALLEL ≈ vCPU/2` (max utile 2 à 4 vCPU). **Au-delà de ~3 users sur 7B : seul un GPU débloque** (→ qwen2.5:14b, NP=4, 30-60+ tok/s).

## Quantification (réf. 7B)
| Quant | Perte PPL | Reco |
|---|---|---|
| Q4_K_M | +1,68 % | **CPU** (vitesse prime) |
| Q5_K_M | +0,39 % | **sweet spot GPU/≥32 Go** |
| Q6_K/Q8_0 | +0,13 / +0,03 % | GPU avec VRAM |

## Sources
Onyx : `model_configs.py`, `chat_configs.py`, `shared_configs/configs.py`, `search_nlp_models.py`, issues #6189/#9364, docs/admins/advanced_configs/search_configs · Ollama : FAQ, PR #14120 (num_ctx ÷ parallel), docs/context-length · FR : MTEB-French (2405.20468), Gaperon (2510.25771) · quant : llama.cpp eval (2601.14277), discussion #2094 · RAGAS : Langfuse×Ragas.
