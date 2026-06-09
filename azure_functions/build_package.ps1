<#
.SYNOPSIS
Assemble le package de déploiement de la Function Durable AC360.

Vendorise les modules `scripts/` importés par le pipeline (le runtime Functions
n'a pas accès à ../scripts), puis produit un .zip prêt pour
`az functionapp deployment source config-zip`.

.EXAMPLE
  pwsh azure_functions/build_package.ps1
  az functionapp deployment source config-zip -g <rg> -n <app> --src azure_functions/.build/ac360_func.zip
#>
param([string]$OutZip)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot                    # azure_functions/
$root = Split-Path -Parent $here         # racine du dépôt
if (-not $OutZip) { $OutZip = Join-Path $here ".build/ac360_func.zip" }

$build = Join-Path $here ".build/pkg"
if (Test-Path $build) { Remove-Item -Recurse -Force $build }
New-Item -ItemType Directory -Force -Path $build | Out-Null

# 1. Contenu de la Function (entrée + config + code partagé).
Copy-Item (Join-Path $here "host.json") $build
Copy-Item (Join-Path $here "function_app.py") $build
Copy-Item (Join-Path $here "requirements.txt") $build
Copy-Item (Join-Path $here "shared") $build -Recurse

# 2. Vendoring des modules Python de scripts/ requis au runtime.
$mods = @(
    "fabric_audit_engine.py", "safe_logger.py", "config.py", "db_manager.py",
    "process_document_ocr.py", "audit_fabric_comparison.py", "generate_fic_draft.py"
)
foreach ($m in $mods) {
    Copy-Item (Join-Path $root "scripts/$m") $build
}

# 3. Nettoyage des caches éventuels.
Get-ChildItem $build -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 4. Zip (contenu à la racine de l'archive).
$zipDir = Split-Path -Parent $OutZip
New-Item -ItemType Directory -Force -Path $zipDir | Out-Null
if (Test-Path $OutZip) { Remove-Item -Force $OutZip }
Compress-Archive -Path (Join-Path $build "*") -DestinationPath $OutZip -Force

Write-Host "Package créé : $OutZip" -ForegroundColor Green
Get-ChildItem $build | Select-Object Name | Format-Table -AutoSize
