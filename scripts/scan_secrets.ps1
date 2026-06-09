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

# Chemins exclus (artefacts, dossiers non pertinents, fixtures de test contenant
# des FAUX secrets volontaires). Les fichiers de test/exemple sont exclus
# uniquement du scan haute-entropie pour éviter les faux positifs.
$ExcludeFragments = @("\.git\", "__pycache__", "\jobs\", "Archives_Documentaires",
                      "\.pytest_cache\", "\.mypy_cache\", "\.planning\", "\.claude\", "\release\")

Write-Host "--- Lancement du scan de secrets ---" -ForegroundColor Cyan

# Énumération récursive correcte (Select-String n'a pas de -Recurse).
$Files = Get-ChildItem -Path $Path -Recurse -File -Include *.yml,*.yaml,*.json,*.py,*.ps1,*.env -ErrorAction SilentlyContinue |
    Where-Object {
        $full = $_.FullName
        -not ($ExcludeFragments | Where-Object { $full -like "*$_*" })
    }

# Allowlist de lignes VÉRIFIÉES bénignes (placeholders, libellés de masquage,
# identifiants/URLs Microsoft, stubs de test). Évite les faux positifs sans
# désactiver la détection d'un vrai secret assigné en clair. La détection par
# entropie est déléguée à gitleaks (.gitleaks.toml) en CI.
$Allowlist = @(
    'MASQU',
    'VOTRE_.*_ICI', 'YOUR_', 'CHANGEME', 'PLACEHOLDER', 'EXEMPLE', 'EXAMPLE', 'A_REMPLIR',
    'ExtensionBundle', 'Microsoft\.Azure', 'Microsoft\.',
    'login\.microsoftonline', 'database\.windows\.net', 'webhooks/durabletask',
    'cognitiveservices\.azure', 'test-tenant', 'test-client', '00000000-0000',
    'vnd\.openxmlformats', 'application/vnd', 'media_type',
    '\$\{', '<[A-Za-z0-9_]+>'
)

function Test-Allowlisted([string]$line) {
    foreach ($a in $Allowlist) { if ($line -match $a) { return $true } }
    return $false
}

$Found = 0
foreach ($Pattern in $Patterns) {
    $scanFiles = $Files
    # Le pattern haute-entropie (dernier) génère des faux positifs sur les
    # fixtures de test/exemples : on l'exclut de ces fichiers.
    if ($Pattern -eq $Patterns[-1]) {
        $scanFiles = $Files | Where-Object {
            $_.FullName -notlike "*\tests\*" -and $_.Name -notlike "*.example"
        }
    }
    $Results = $scanFiles | Select-String -Pattern $Pattern |
        Where-Object { -not (Test-Allowlisted $_.Line) }
    if ($Results) {
        $Found += @($Results).Count
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
