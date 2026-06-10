<#
.SYNOPSIS
Construit et déploie la passerelle FastAPI AC360 (App Service Linux Python).

.DESCRIPTION
Package MINIMAL (defense-in-depth : surface d'attaque réduite) — uniquement les
modules réellement importés par api_server au démarrage. Build Oryx distant
(SCM_DO_BUILD_DURING_DEPLOYMENT=true) installe requirements.txt.

IMPORTANT : déployer en .zip (type=zip), JAMAIS un seul fichier (type=static) :
un swap de fichier unique laisse le déploiement incohérent et la Function/le
site ne redémarre pas. Le poller `az webapp deploy` peut afficher un timeout sur
F1 (démarrage lent) alors que le site est déjà sain — vérifier /health.

.NOTES
Pré-requis app settings (déjà posés en staging) :
  AZURE_FUNCTION_URL, AZURE_FUNCTION_KEY (KV ref), AZURE_DURABLE_KEY (KV ref,
  clé système durabletask_extension), TASK_HUB_NAME, CLIENT_ID, TENANT_ID.
#>
param(
    [string]$ResourceGroup = "rg-ac360-staging",
    [string]$AppName = "ac360-gateway-staging",
    [switch]$Deploy
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$pkg = Join-Path $root "gwpkg"

# Modules réellement importés par api_server (chaîne vérifiée) :
# api_server -> planner_integration, generate_fiche_rdv, auth, safe_logger,
#               feature_flags, usage_tracker ; auth -> config ;
#               usage_tracker -> feature_flags, safe_logger.
$modules = @(
    "api_server.py", "auth.py", "config.py",
    "safe_logger.py", "planner_integration.py", "generate_fiche_rdv.py",
    "feature_flags.py", "usage_tracker.py"
)

Remove-Item -Recurse -Force $pkg -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $pkg | Out-Null
foreach ($m in $modules) { Copy-Item (Join-Path $root "scripts\$m") (Join-Path $pkg $m) }

# requirements MINIMAL passerelle (pas de pyodbc/pandas/azure-ai/deltalake :
# non importés → build rapide et fiable).
$req = @"
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
PyJWT>=2.8.0
cryptography>=42.0.0
pydantic>=2.7.0
python-docx>=1.1.0
python-dotenv>=1.0.1
pyyaml>=6.0.1
requests>=2.31.0
"@
[System.IO.File]::WriteAllText((Join-Path $pkg "requirements.txt"), $req)

$zip = Join-Path $root "gateway.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $pkg "*") -DestinationPath $zip -Force
Write-Host "Package construit : $zip ($((Get-Item $zip).Length) octets)" -ForegroundColor Green

if ($Deploy) {
    Write-Host "Déploiement vers $AppName ..." -ForegroundColor Cyan
    az webapp deploy -g $ResourceGroup -n $AppName --src-path $zip --type zip --restart true
    Write-Host "Vérifier : https://$AppName.azurewebsites.net/health" -ForegroundColor Yellow
}
