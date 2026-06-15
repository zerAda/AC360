# =============================================================================
# Diagnostic matériel (Windows / PowerShell) : CPU, RAM, GPU + aptitude Docker.
# Imprime un VERDICT et les valeurs .env recommandées. Lecture seule.
#   Exécution :  powershell -ExecutionPolicy Bypass -File .\scripts\detect-hardware.ps1
# =============================================================================

function Line { Write-Host ("-" * 64) }

$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1)
$cpuName  = $cpu.Name
$cpuCores = $cpu.NumberOfLogicalProcessors
$ramGB    = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)

# GPU
$gpuKind = "none"; $gpuName = ""; $vramGB = 0
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    $gpuKind = "nvidia"
    $gpuName = (& nvidia-smi --query-gpu=name --format=csv,noheader | Select-Object -First 1)
    $vramMB  = (& nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | Select-Object -First 1)
    if ($vramMB) { $vramGB = [math]::Round([int]$vramMB / 1024) }
} else {
    $vc = Get-CimInstance Win32_VideoController | Select-Object -First 1
    if ($vc) {
        $gpuName = $vc.Name
        if ($vc.Name -match "NVIDIA") { $gpuKind = "nvidia" }
        elseif ($vc.Name -match "AMD|Radeon") { $gpuKind = "amd" }
        else { $gpuKind = "intel" }
    }
}

# Docker
$dockerOK = "non"
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info *> $null; if ($LASTEXITCODE -eq 0) { $dockerOK = "oui" }
}

# Recommandation
$profile = "CPU"; $model = "llama3.2:3b"; $heap = "1g"
$osLimit = "2g"; $infer = "4g"; $bg = "5g"; $ollama = "6g"; $gpuHint = ""
if ($gpuKind -eq "nvidia" -and $vramGB -ge 8) {
    $profile = "GPU NVIDIA (via WSL2)"
    if ($vramGB -ge 16) { $model = "qwen2.5:14b-instruct" } else { $model = "llama3.1:8b" }
    $gpuHint = "Lancer avec le profil GPU : make up GPU=1 (Docker Desktop + backend WSL2 + pilotes NVIDIA)."
} elseif ($ramGB -lt 12) {
    $profile = "CPU (RAM limitée)"; $model = "llama3.2:1b"
    $heap = "512m"; $osLimit = "1g"; $infer = "3g"; $bg = "3g"; $ollama = "3g"
} elseif ($ramGB -ge 24) {
    $profile = "CPU (confortable)"; $model = "qwen2.5:7b-instruct"
    $heap = "2g"; $osLimit = "3g"; $infer = "5g"; $bg = "6g"; $ollama = "8g"
}

Line; Write-Host "  DIAGNOSTIC MATÉRIEL — AC360 stack IA locale" -ForegroundColor Cyan; Line
Write-Host "  OS            : Windows"
Write-Host "  CPU           : $cpuName ($cpuCores threads)"
Write-Host "  RAM totale    : $ramGB Go"
if ($gpuName) { Write-Host "  GPU           : $gpuName" } else { Write-Host "  GPU           : aucun" }
if ($vramGB -gt 0) { Write-Host "  VRAM          : $vramGB Go" }
Write-Host "  Docker        : $dockerOK"
Line
Write-Host "  NOTE Windows : le GPU NVIDIA n'est exploitable par Docker que via le"
Write-Host "  backend WSL2 (Docker Desktop) avec les pilotes NVIDIA pour WSL installés."
Line
Write-Host "  VERDICT : profil recommandé = $profile" -ForegroundColor Green
$keepAlive = if ($ramGB -ge 12) { "-1" } else { "5m" }
$nPar      = if ($ramGB -ge 16) { 2 } else { 1 }
$maxLoad   = if ($ramGB -ge 16) { 2 } else { 1 }
Write-Host "  Valeurs à reporter dans .env :"
Write-Host ""
Write-Host "    OLLAMA_MODELS_TO_PULL=$model nomic-embed-text"
Write-Host "    OLLAMA_FLASH_ATTENTION=1"
Write-Host "    OLLAMA_KV_CACHE_TYPE=q8_0"
Write-Host "    OLLAMA_KEEP_ALIVE=$keepAlive"
Write-Host "    OLLAMA_NUM_PARALLEL=$nPar"
Write-Host "    OLLAMA_MAX_LOADED_MODELS=$maxLoad"
Write-Host "    OLLAMA_CPU_LIMIT=$cpuCores"
Write-Host "    OPENSEARCH_HEAP=$heap"
Write-Host "    OPENSEARCH_MEM_LIMIT=$osLimit"
Write-Host "    INFERENCE_MEM_LIMIT=$infer"
Write-Host "    BACKGROUND_MEM_LIMIT=$bg"
Write-Host "    OLLAMA_MEM_LIMIT=$ollama"
if ($gpuHint) { Write-Host ""; Write-Host "  $gpuHint" }
Line
Write-Host "  NB : sous WSL2 vous pouvez utiliser directement 'make tune' (écrit .env)."
Write-Host "  Étapes (depuis selfhost/) : make secrets ; make up ; make verify"
