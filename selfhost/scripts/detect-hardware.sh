#!/usr/bin/env bash
# =============================================================================
# Diagnostic + AUTO-TUNING matériel (Linux / macOS) : CPU, RAM, GPU.
#
#   ./detect-hardware.sh            → RAPPORT (lecture seule) + valeurs conseillées
#   ./detect-hardware.sh --apply    → ÉCRIT les valeurs optimales dans .env  (= make tune)
#
# Objectif : exploiter au mieux la machine (gros modèle qui tient, limites
# proportionnelles à la RAM, réglages perf Ollama) TOUT en gardant une marge OS
# (jamais 100 % → sinon gel/OOM). Les secrets ne sont pas touchés.
#
# Pourquoi ? L'assistant ne peut pas inspecter votre poste depuis son sandbox
# cloud : exécutez ceci SUR la machine cible.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

APPLY=0; [ "${1:-}" = "--apply" ] && APPLY=1
ENV_FILE=".env"; TEMPLATE="env.template"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
line() { printf -- '----------------------------------------------------------------\n'; }
clamp() { v=$1; [ "$v" -lt "$2" ] && v=$2; [ "$v" -gt "$3" ] && v=$3; echo "$v"; }

# ---- Détection --------------------------------------------------------------
OS="$(uname -s)"; ARCH="$(uname -m)"
CPU_MODEL="inconnu"; CORES=1; RAM_GB=0
GPU_KIND="none"; GPU_NAME=""; VRAM_GB=0; DOCKER_GPU="non"

case "$OS" in
  Linux)
    CORES="$(nproc 2>/dev/null || echo 1)"
    CPU_MODEL="$(sed -n 's/^model name[[:space:]]*: //p' /proc/cpuinfo 2>/dev/null | head -n1)"
    [ -z "$CPU_MODEL" ] && CPU_MODEL="$(uname -p)"
    kb="$(sed -n 's/^MemTotal:[[:space:]]*\([0-9]*\).*/\1/p' /proc/meminfo 2>/dev/null)"
    [ -n "$kb" ] && RAM_GB=$(( kb / 1024 / 1024 )) ;;
  Darwin)
    CORES="$(sysctl -n hw.ncpu 2>/dev/null || echo 1)"
    CPU_MODEL="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo Apple)"
    bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
    RAM_GB=$(( bytes / 1024 / 1024 / 1024 )) ;;
  *) echo "OS non géré ($OS). Sous Windows : detect-hardware.ps1"; exit 1 ;;
esac
[ "$RAM_GB" -lt 1 ] && RAM_GB=1; [ "$CORES" -lt 1 ] && CORES=1

if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_KIND="nvidia"
  GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)"
  vram_mb="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1)"
  [ -n "${vram_mb:-}" ] && VRAM_GB=$(( vram_mb / 1024 ))
elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
  GPU_KIND="apple"; GPU_NAME="Apple Silicon (GPU Metal — inaccessible depuis Docker)"
elif command -v lspci >/dev/null 2>&1 && lspci 2>/dev/null | grep -qiE 'amd/ati|radeon'; then
  GPU_KIND="amd"; GPU_NAME="$(lspci 2>/dev/null | grep -iE 'vga|3d|display' | grep -iE 'amd|radeon' | head -n1 | cut -d: -f3-)"
fi
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if [ "$GPU_KIND" = nvidia ] && docker info 2>/dev/null | grep -qi 'nvidia'; then DOCKER_GPU="oui"
  elif [ "$GPU_KIND" = nvidia ] && command -v nvidia-ctk >/dev/null 2>&1; then DOCKER_GPU="probable (nvidia-ctk présent)"; fi
fi

# ---- Calcul du profil optimal (marge OS réservée) ---------------------------
RES=$(clamp $(( RAM_GB / 8 )) 2 8)          # RAM réservée à l'OS
AVAIL=$(( RAM_GB - RES )); [ "$AVAIL" -lt 1 ] && AVAIL=1
USE_GPU=0
[ "$GPU_KIND" = nvidia ] && [ "$VRAM_GB" -ge 6 ] && USE_GPU=1

# Choix du plus gros modèle qui tient (use-all-resources, raisonné).
pick_model() {
  if [ "$USE_GPU" = 1 ]; then
    if   [ "$VRAM_GB" -ge 24 ]; then echo "qwen2.5:32b-instruct 24"
    elif [ "$VRAM_GB" -ge 12 ]; then echo "qwen2.5:14b-instruct 14"
    elif [ "$VRAM_GB" -ge 8 ];  then echo "llama3.1:8b 9"
    else echo "llama3.2:3b 5"; fi
  else
    if   [ "$AVAIL" -ge 24 ]; then echo "qwen2.5:14b-instruct 13"
    elif [ "$AVAIL" -ge 12 ]; then echo "llama3.1:8b 9"
    elif [ "$AVAIL" -ge 7 ];  then echo "qwen2.5:7b-instruct 8"
    else echo "llama3.2:3b 5"; fi
  fi
}
read -r MODEL OLLAMA_MEM <<EOF
$(pick_model)
EOF
[ "$USE_GPU" = 1 ] && OLLAMA_MEM=4          # poids en VRAM → peu de RAM hôte

HEAP=$(clamp $(( RAM_GB * 20 / 100 )) 1 8)
OS_MEM=$(clamp $(( HEAP * 2 )) 2 16)
INFER_MEM=$(clamp $(( RAM_GB * 25 / 100 )) 3 8)
BG_MEM=$(clamp $(( RAM_GB * 30 / 100 )) 3 10)
API_MEM=$(clamp $(( RAM_GB * 20 / 100 )) 2 6)
KEEP_ALIVE=$([ "$AVAIL" -ge 12 ] && echo "-1" || echo "5m")    # -1 = toujours chargé
MAXLOAD=$([ "$AVAIL" -ge 16 ] && echo 2 || echo 1)
if [ "$USE_GPU" = 1 ]; then NPAR=$([ "$VRAM_GB" -ge 12 ] && echo 4 || echo 2)
else NPAR=$([ "$AVAIL" -ge 16 ] && echo 2 || echo 1); fi
PERF_OK=$([ "$RAM_GB" -ge 32 ] || { [ "$USE_GPU" = 1 ] && [ "$RAM_GB" -ge 24 ]; } && echo 1 || echo 0)

# ---- Rapport ----------------------------------------------------------------
line; bold "  DIAGNOSTIC & TUNING — AC360 stack IA locale"; line
printf "  OS / Arch     : %s / %s\n" "$OS" "$ARCH"
printf "  CPU           : %s (%s threads)\n" "${CPU_MODEL:-inconnu}" "$CORES"
printf "  RAM totale    : %s Go  (réserve OS %s Go → dispo ~%s Go)\n" "$RAM_GB" "$RES" "$AVAIL"
printf "  GPU           : %s\n" "$([ "$GPU_KIND" = none ] && echo 'aucun GPU dédié' || echo "$GPU_NAME")"
[ "$VRAM_GB" -gt 0 ] && printf "  VRAM          : %s Go\n" "$VRAM_GB"
printf "  Docker + GPU  : %s\n" "$DOCKER_GPU"
if [ "$OS" = Linux ]; then
  mmc="$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)"
  [ "${mmc:-0}" -ge 262144 ] && printf "  OpenSearch    : vm.max_map_count=%s ✓\n" "$mmc" \
    || printf "  OpenSearch    : ⚠ vm.max_map_count=%s (<262144) → sudo sysctl -w vm.max_map_count=262144\n" "$mmc"
fi
line
[ "$GPU_KIND" = apple ] && { bold "  macOS : Docker n'accède pas au GPU → CPU en conteneur."; echo "  Pour le GPU Metal, lancez Ollama en NATIF (cf. docs/RUNBOOK.md)."; line; }
[ "$USE_GPU" = 1 ] && bold "  PROFIL : GPU NVIDIA — lancez : make up GPU=1" || bold "  PROFIL : CPU"
[ "$PERF_OK" = 1 ] && echo "  Ressources confortables → indexation dédiée possible : make up PERF=1"
line

emit() { printf '    %s=%s\n' "$1" "$2"; }
echo "  Réglages optimaux pour CETTE machine :"; echo
emit OLLAMA_MODELS_TO_PULL "$MODEL nomic-embed-text"
emit OLLAMA_FLASH_ATTENTION 1
emit OLLAMA_KV_CACHE_TYPE q8_0
emit OLLAMA_KEEP_ALIVE "$KEEP_ALIVE"
emit OLLAMA_NUM_PARALLEL "$NPAR"
emit OLLAMA_MAX_LOADED_MODELS "$MAXLOAD"
emit OLLAMA_CPU_LIMIT "$CORES"
emit OLLAMA_MEM_LIMIT "${OLLAMA_MEM}g"
emit OPENSEARCH_HEAP "${HEAP}g"
emit OPENSEARCH_MEM_LIMIT "${OS_MEM}g"
emit INFERENCE_MEM_LIMIT "${INFER_MEM}g"
emit BACKGROUND_MEM_LIMIT "${BG_MEM}g"
emit BACKGROUND_CPU_LIMIT "$CORES"
emit API_SERVER_MEM_LIMIT "${API_MEM}g"
line

# ---- Application -------------------------------------------------------------
if [ "$APPLY" != 1 ]; then
  echo "  Pour écrire ces valeurs dans .env :  make tune   (ou ./scripts/detect-hardware.sh --apply)"
  exit 0
fi

[ -f "$ENV_FILE" ] || cp "$TEMPLATE" "$ENV_FILE"
set_force() { # set_force KEY VALUE (remplace ou ajoute ; secrets non touchés)
  if grep -q "^$1=" "$ENV_FILE"; then
    awk -v k="$1" -v v="$2" -F= '$1==k{print k"="v; next}{print}' "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
  else printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"; fi
}
set_force OLLAMA_MODELS_TO_PULL "$MODEL nomic-embed-text"
set_force OLLAMA_FLASH_ATTENTION 1
set_force OLLAMA_KV_CACHE_TYPE q8_0
set_force OLLAMA_KEEP_ALIVE "$KEEP_ALIVE"
set_force OLLAMA_NUM_PARALLEL "$NPAR"
set_force OLLAMA_MAX_LOADED_MODELS "$MAXLOAD"
set_force OLLAMA_CPU_LIMIT "$CORES"
set_force OLLAMA_MEM_LIMIT "${OLLAMA_MEM}g"
set_force OPENSEARCH_HEAP "${HEAP}g"
set_force OPENSEARCH_MEM_LIMIT "${OS_MEM}g"
set_force INFERENCE_MEM_LIMIT "${INFER_MEM}g"
set_force BACKGROUND_MEM_LIMIT "${BG_MEM}g"
set_force BACKGROUND_CPU_LIMIT "$CORES"
set_force API_SERVER_MEM_LIMIT "${API_MEM}g"
[ -f "$ENV_FILE" ] && chmod 600 "$ENV_FILE"
bold "  ✓ .env mis à jour avec le profil optimal."
echo "  Étapes : make secrets (si pas fait)  →  make up$([ "$PERF_OK" = 1 ] && echo ' PERF=1')$([ "$USE_GPU" = 1 ] && echo ' GPU=1')  →  make verify"
