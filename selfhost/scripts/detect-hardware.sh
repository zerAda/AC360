#!/usr/bin/env bash
# =============================================================================
# Diagnostic matériel (Linux / macOS) : CPU, RAM, GPU et aptitude Docker-GPU.
# Imprime un VERDICT et les valeurs .env recommandées (modèle Ollama, heap, etc.).
# 100 % lecture seule : ne modifie rien. (Windows : voir detect-hardware.ps1)
#
# Pourquoi ce script ? L'assistant ne peut pas inspecter votre poste depuis son
# sandbox cloud : exécutez ceci SUR la machine cible pour calibrer la stack.
# =============================================================================
# Pas de 'set -e' : diagnostic en lecture seule, on ne veut jamais qu'il
# s'interrompe au milieu du rapport si une commande optionnelle échoue.
set -uo pipefail

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
line() { printf -- '----------------------------------------------------------------\n'; }

OS="$(uname -s)"
ARCH="$(uname -m)"
CPU_MODEL="inconnu"; CPU_CORES="?"; RAM_GB=0
GPU_KIND="none"; GPU_NAME=""; VRAM_GB=0
DOCKER_GPU="non"

# ---- CPU / RAM --------------------------------------------------------------
case "$OS" in
  Linux)
    CPU_CORES="$(nproc 2>/dev/null || echo '?')"
    CPU_MODEL="$(sed -n 's/^model name[[:space:]]*: //p' /proc/cpuinfo 2>/dev/null | head -n1)"
    [ -z "$CPU_MODEL" ] && CPU_MODEL="$(uname -p)"
    if [ -r /proc/meminfo ]; then
      kb="$(sed -n 's/^MemTotal:[[:space:]]*\([0-9]*\).*/\1/p' /proc/meminfo)"
      RAM_GB=$(( kb / 1024 / 1024 ))
    fi
    ;;
  Darwin)
    CPU_CORES="$(sysctl -n hw.ncpu 2>/dev/null || echo '?')"
    CPU_MODEL="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple')"
    bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
    RAM_GB=$(( bytes / 1024 / 1024 / 1024 ))
    ;;
  *) echo "OS non géré ($OS). Utilisez detect-hardware.ps1 sous Windows."; exit 1 ;;
esac

# ---- GPU --------------------------------------------------------------------
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_KIND="nvidia"
  GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)"
  vram_mb="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1)"
  [ -n "${vram_mb:-}" ] && VRAM_GB=$(( vram_mb / 1024 ))
elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
  GPU_KIND="apple"
  GPU_NAME="Apple Silicon (GPU Metal intégré)"
elif command -v lspci >/dev/null 2>&1 && lspci 2>/dev/null | grep -qiE 'amd/ati|radeon'; then
  GPU_KIND="amd"
  GPU_NAME="$(lspci 2>/dev/null | grep -iE 'vga|3d|display' | grep -iE 'amd|radeon' | head -n1 | cut -d: -f3-)"
fi

# ---- Docker + aptitude GPU --------------------------------------------------
DOCKER_OK="non"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  DOCKER_OK="oui"
  if [ "$GPU_KIND" = "nvidia" ] && docker info 2>/dev/null | grep -qi 'Runtimes:.*nvidia\|nvidia'; then
    DOCKER_GPU="oui (runtime nvidia détecté)"
  elif [ "$GPU_KIND" = "nvidia" ] && command -v nvidia-ctk >/dev/null 2>&1; then
    DOCKER_GPU="probable (nvidia-ctk présent — vérifier le runtime)"
  fi
fi

# ---- vm.max_map_count (Linux, requis par OpenSearch) ------------------------
MMC_NOTE=""
if [ "$OS" = "Linux" ]; then
  mmc="$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)"
  if [ "${mmc:-0}" -lt 262144 ]; then
    MMC_NOTE="⚠ vm.max_map_count=$mmc (<262144) → OpenSearch peut échouer. Corriger :
     sudo sysctl -w vm.max_map_count=262144
     (persistant : echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-onyx.conf)"
  else
    MMC_NOTE="✓ vm.max_map_count=$mmc (OK pour OpenSearch)"
  fi
fi

# ---- Recommandation ---------------------------------------------------------
REC_PROFILE="CPU"; REC_MODEL="llama3.2:3b"; REC_HEAP="1g"
REC_OS_LIMIT="2g"; REC_INFER="4g"; REC_BG="5g"; REC_OLLAMA="6g"; GPU_HINT=""

if [ "$GPU_KIND" = "nvidia" ] && [ "$VRAM_GB" -ge 8 ]; then
  REC_PROFILE="GPU NVIDIA"
  if   [ "$VRAM_GB" -ge 16 ]; then REC_MODEL="qwen2.5:14b-instruct"
  else REC_MODEL="llama3.1:8b"; fi
  REC_OLLAMA="$(( VRAM_GB > 12 ? 12 : VRAM_GB ))g"
  GPU_HINT="Lancer avec le profil GPU :  make up GPU=1   (nécessite nvidia-container-toolkit)"
elif [ "$RAM_GB" -gt 0 ] && [ "$RAM_GB" -lt 12 ]; then
  REC_PROFILE="CPU (RAM limitée)"; REC_MODEL="llama3.2:1b"
  REC_HEAP="512m"; REC_OS_LIMIT="1g"; REC_INFER="3g"; REC_BG="3g"; REC_OLLAMA="3g"
elif [ "$RAM_GB" -ge 24 ]; then
  REC_PROFILE="CPU (confortable)"; REC_MODEL="qwen2.5:7b-instruct"
  REC_HEAP="2g"; REC_OS_LIMIT="3g"; REC_INFER="5g"; REC_BG="6g"; REC_OLLAMA="8g"
fi

# ---- Rapport ----------------------------------------------------------------
line; bold "  DIAGNOSTIC MATÉRIEL — AC360 stack IA locale"; line
printf "  OS / Arch     : %s / %s\n" "$OS" "$ARCH"
printf "  CPU           : %s (%s cœurs)\n" "${CPU_MODEL:-inconnu}" "$CPU_CORES"
printf "  RAM totale    : %s Go\n" "$RAM_GB"
printf "  GPU           : %s\n" "$([ "$GPU_KIND" = none ] && echo 'aucun GPU dédié détecté' || echo "$GPU_NAME")"
[ "$VRAM_GB" -gt 0 ] && printf "  VRAM          : %s Go\n" "$VRAM_GB"
printf "  Docker        : %s\n" "$DOCKER_OK"
printf "  Docker + GPU  : %s\n" "$DOCKER_GPU"
[ -n "$MMC_NOTE" ] && printf "  OpenSearch    : %s\n" "$MMC_NOTE"
line

# Avertissements ciblés (anti-réserves)
if [ "$GPU_KIND" = "apple" ]; then
  bold "  NOTE macOS / Apple Silicon"
  echo "  Docker Desktop n'accède PAS au GPU (Metal). En conteneur, Ollama tourne"
  echo "  en CPU. Pour exploiter le GPU : installer Ollama en NATIF et brancher Onyx"
  echo "  dessus (cf. docs/RUNBOOK.md § Ollama natif). Sinon, restez en CPU."
  line
fi
if [ "$RAM_GB" -gt 0 ] && [ "$RAM_GB" -lt 16 ]; then
  bold "  ⚠ RAM < 16 Go : stack complète serrée."
  echo "  Le profil ci-dessous réduit l'empreinte. Surveillez la mémoire (make stats)."
  line
fi

bold "  VERDICT : profil recommandé = $REC_PROFILE"
echo "  Valeurs à reporter dans .env :"
echo
printf '    OLLAMA_MODELS_TO_PULL=%s nomic-embed-text\n' "$REC_MODEL"
printf '    OPENSEARCH_HEAP=%s\n'        "$REC_HEAP"
printf '    OPENSEARCH_MEM_LIMIT=%s\n'   "$REC_OS_LIMIT"
printf '    INFERENCE_MEM_LIMIT=%s\n'    "$REC_INFER"
printf '    BACKGROUND_MEM_LIMIT=%s\n'   "$REC_BG"
printf '    OLLAMA_MEM_LIMIT=%s\n'       "$REC_OLLAMA"
[ -n "$GPU_HINT" ] && { echo; printf '  %s\n' "$GPU_HINT"; }
line
echo "  Étapes suivantes :  make secrets  &&  make up  &&  make verify"
