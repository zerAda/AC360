<#
.SYNOPSIS
Scan de base des secrets dans le répertoire.
#>
param(
    [string]$Path = ".",
    [switch]$FailOnWarning = $true
)

$Patterns = @(
    "secret\s*[:=]\s*[`"']([^`"']{10,})[`"']",
    "password\s*[:=]\s*[`"']([^`"']{8,})[`"']",
    "bearer\s+([A-Za-z0-9\-\._~\+\/]+=*)",
    "apikey\s*[:=]\s*[`"']([^`"']{10,})[`"']",
    "clientSecret\s*[:=]\s*[`"']([^`"']{10,})[`"']",
    # [PATCH HATER] Détection de secrets à haute entropie (Clés JWT, API Keys aléatoires) peu importe le nom de la variable
    "[`"'][A-Za-z0-9\-\._~\+\/]{40,}[`"']"
)

$Exclude = @("*.db", "*.log", "Archives_Documentaires", "__pycache__", "jobs", ".git")

Write-Host "--- Lancement du scan de secrets ---" -ForegroundColor Cyan
$Found = 0
foreach ($Pattern in $Patterns) {
    # [PATCH HATER] Ajout de *.yml et *.yaml qui sont critiques pour les fuites de secrets
    $Results = Select-String -Path $Path\* -Include *.mcs.yml,*.yaml,*.yml,*.json,*.py,*.ps1,*.env -Exclude $Exclude -Pattern $Pattern -Recurse
    if ($Results) {
        $Found += $Results.Count
        Write-Host "ALERTE: Secret suspect détecté via le pattern '$Pattern'" -ForegroundColor Red
        $Results | Select-Object Path, LineNumber | Format-Table
    }
}

if ($Found -gt 0) {
    Write-Host "ERREUR: $Found secret(s) suspect(s) détecté(s)." -ForegroundColor Red
    if ($FailOnWarning) { exit 1 }
} else {
    Write-Host "SUCCÈS: Aucun secret en clair détecté." -ForegroundColor Green
    exit 0
}
