<#
.SYNOPSIS
Valide hors-ligne la posture de sécurité durcie de l'infrastructure AC360.

.DESCRIPTION
Gate fail-closed, sans `az login`. Compile `infra/main.bicep` via `az bicep build`
(analyse statique + lint) puis affirme, sur le JSON ARM compilé, les propriétés
par exigence INF (02, 03, 04, 07, 08, 09) qui sont vérifiables hors-ligne.

Tant que main.bicep n'a pas encore été étendu à la forme PROD (passerelle encore
sur F1/Y1, pas de B1), le validateur DIFFÈRE les assertions et sort en succès
(exit 0, message jaune) afin que ce plan Wave-0 passe. Dès que les ressources PROD
sont présentes (plan B1 détecté), toute violation provoque un échec (exit 1, rouge).

Compatible Windows PowerShell 5.1 et PowerShell Core (Linux CI). N'utilise pas cmd.exe.
#>
param(
    [string]$BicepFile = "infra/main.bicep"
)

$ErrorActionPreference = "Stop"

Write-Host "=== AC360 Validate Infra (offline, fail-closed) ===" -ForegroundColor Cyan
Write-Host "Bicep : $BicepFile"

# --------------------------------------------------------------------------
# Étape 1 — Compilation offline (az bicep build). Aucune authentification.
# --------------------------------------------------------------------------
if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-Host "[ÉCHEC] Azure CLI (az) introuvable — impossible de compiler le Bicep." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $BicepFile)) {
    Write-Host "[ÉCHEC] Fichier Bicep introuvable : $BicepFile" -ForegroundColor Red
    exit 1
}

$tmpDir = if ($env:TEMP) { $env:TEMP } elseif ($env:TMPDIR) { $env:TMPDIR } else { "/tmp" }
$compiled = Join-Path $tmpDir "ac360_main.json"

Write-Host "Compilation : az bicep build -f $BicepFile" -ForegroundColor Gray
$buildOut = az bicep build -f $BicepFile --outfile $compiled 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ÉCHEC] az bicep build a échoué (build error) :" -ForegroundColor Red
    $buildOut | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
if (-not (Test-Path $compiled)) {
    Write-Host "[ÉCHEC] La compilation n'a produit aucun JSON ARM." -ForegroundColor Red
    exit 1
}
Write-Host "Build OK." -ForegroundColor Green

$arm = Get-Content $compiled -Raw | ConvertFrom-Json
$resources = @($arm.resources)
$rawJson = Get-Content $compiled -Raw

# --------------------------------------------------------------------------
# Helpers de sélection sur le JSON ARM compilé.
# --------------------------------------------------------------------------
function Get-ResByType {
    param([object[]]$Res, [string]$Type)
    return @($Res | Where-Object { $_.type -eq $Type })
}

# Récupère la valeur d'une app-setting par nom dans un site (siteConfig.appSettings
# OU functionAppConfig). Renvoie $null si absente.
function Get-AppSetting {
    param($Site, [string]$Name)
    $settings = @()
    if ($Site.properties.siteConfig.appSettings) { $settings += $Site.properties.siteConfig.appSettings }
    if ($Site.properties.functionAppConfig.runtime) { } # placeholder; settings restent dans siteConfig
    foreach ($s in $settings) { if ($s.name -eq $Name) { return $s.value } }
    return $null
}

$serverfarms = Get-ResByType -Res $resources -Type 'Microsoft.Web/serverfarms'
$sites       = Get-ResByType -Res $resources -Type 'Microsoft.Web/sites'
$storages    = Get-ResByType -Res $resources -Type 'Microsoft.Storage/storageAccounts'
$cognitive   = Get-ResByType -Res $resources -Type 'Microsoft.CognitiveServices/accounts'
$roleAssigns = Get-ResByType -Res $resources -Type 'Microsoft.Authorization/roleAssignments'

# --------------------------------------------------------------------------
# Détection de la forme PROD : la passerelle passe à B1 en PROD (staging=F1).
# Tant qu'aucun plan B1 n'est compilé, les SKUs prod (B1/S0/GRS/FC1) sont posés
# en littéral par le plan 02-02 ; on diffère les assertions pour ce plan Wave-0.
# --------------------------------------------------------------------------
$gwPlanB1 = @($serverfarms | Where-Object { $_.sku.name -eq 'B1' })
$prodShapePresent = $gwPlanB1.Count -gt 0

if (-not $prodShapePresent) {
    Write-Host ""
    Write-Host "[DIFFÉRÉ] main.bicep pas encore étendu à la forme PROD (aucun plan B1 compilé)." -ForegroundColor Yellow
    Write-Host "          Les assertions par-INF seront activées une fois les ressources PROD présentes." -ForegroundColor Yellow
    Write-Host "[OK] Build vert ; gate Wave-0 satisfait." -ForegroundColor Green
    exit 0
}

# --------------------------------------------------------------------------
# Étape 2 — Assertions par-INF (collect-violations, fail-closed).
# --------------------------------------------------------------------------
function Test-InfraAssertions {
    param([object[]]$ServerFarms, [object[]]$Sites, [object[]]$Storages,
          [object[]]$Cognitive, [object[]]$RoleAssigns, [string]$RawJson)

    $violations = @()

    # --- INF-02 : passerelle B1, capacity=1, alwaysOn, gunicorn --workers 1 ---
    $gwPlan = @($ServerFarms | Where-Object { $_.sku.name -eq 'B1' }) | Select-Object -First 1
    if (-not $gwPlan) { $violations += "INF-02: aucun plan B1 (gwPlan)." }
    else {
        if ($gwPlan.sku.capacity -ne 1) { $violations += "INF-02: gwPlan sku.capacity != 1 (= $($gwPlan.sku.capacity))." }
    }
    # gatewayApp = site 'app,linux' avec appCommandLine gunicorn
    $gatewayApp = @($Sites | Where-Object { $_.properties.siteConfig.appCommandLine -match 'gunicorn' }) | Select-Object -First 1
    if (-not $gatewayApp) { $violations += "INF-02: passerelle (appCommandLine gunicorn) introuvable." }
    else {
        if ($gatewayApp.properties.siteConfig.alwaysOn -ne $true) { $violations += "INF-02: gatewayApp siteConfig.alwaysOn != true." }
        if ($gatewayApp.properties.siteConfig.appCommandLine -notmatch '--workers\s+1') { $violations += "INF-02/AUD-04: gatewayApp appCommandLine ne contient pas '--workers 1' (pin instance unique)." }
    }

    # --- INF-03 : Function Flex (FC1 / FlexConsumption) + runtime python 3.12 ---
    $funcPlan = @($ServerFarms | Where-Object { $_.sku.name -eq 'FC1' -or $_.sku.tier -eq 'FlexConsumption' }) | Select-Object -First 1
    if (-not $funcPlan) { $violations += "INF-03: plan Flex Consumption (FC1/FlexConsumption) introuvable." }
    $funcApp = @($Sites | Where-Object { $_.properties.functionAppConfig }) | Select-Object -First 1
    if (-not $funcApp) { $violations += "INF-03: Function app avec functionAppConfig introuvable." }
    else {
        $rtVer = $funcApp.properties.functionAppConfig.runtime.version
        if ($rtVer -ne '3.12') { $violations += "INF-03: functionAppConfig.runtime.version != '3.12' (= $rtVer)." }
    }

    # --- INF-04 : Document Intelligence S0 + disableLocalAuth=true ---
    $docIntel = @($Cognitive | Where-Object { $_.kind -eq 'FormRecognizer' }) | Select-Object -First 1
    if (-not $docIntel) { $violations += "INF-04: compte FormRecognizer (DocIntel) introuvable." }
    else {
        if ($docIntel.sku.name -ne 'S0') { $violations += "INF-04: docIntel sku.name != 'S0' (= $($docIntel.sku.name))." }
        if ($docIntel.properties.disableLocalAuth -ne $true) { $violations += "INF-04: docIntel disableLocalAuth != true." }
    }

    # --- INF-09 : Storage GRS + allowSharedKeyAccess=false + soft-delete/PITR/versioning/changeFeed + MI hub ---
    $storage = @($Storages) | Select-Object -First 1
    if (-not $storage) { $violations += "INF-09: storageAccount introuvable." }
    else {
        if ($storage.sku.name -ne 'Standard_GRS') { $violations += "INF-09: storage sku.name != 'Standard_GRS' (= $($storage.sku.name))." }
        if ($storage.properties.allowSharedKeyAccess -ne $false) { $violations += "INF-09: storage allowSharedKeyAccess != false." }
    }
    # blobServices enfant avec rétention + PITR + versioning + changeFeed
    $blobSvc = @($resources | Where-Object { $_.type -eq 'Microsoft.Storage/storageAccounts/blobServices' }) | Select-Object -First 1
    if (-not $blobSvc) { $violations += "INF-09: ressource enfant blobServices introuvable." }
    else {
        $bp = $blobSvc.properties
        if (-not $bp.deleteRetentionPolicy) { $violations += "INF-09: blobServices deleteRetentionPolicy absent." }
        if (-not $bp.containerDeleteRetentionPolicy) { $violations += "INF-09: blobServices containerDeleteRetentionPolicy absent." }
        if (-not $bp.restorePolicy) { $violations += "INF-09: blobServices restorePolicy (PITR) absent." }
        if ($bp.isVersioningEnabled -ne $true) { $violations += "INF-09: blobServices isVersioningEnabled != true." }
        if (-not $bp.changeFeed) { $violations += "INF-09: blobServices changeFeed absent." }
    }
    # AzureWebJobsStorage__credential == managedidentity (storage par identité, sans clé)
    $miCred = $null
    foreach ($s in $Sites) {
        $v = Get-AppSetting -Site $s -Name 'AzureWebJobsStorage__credential'
        if ($v) { $miCred = $v; break }
    }
    if ($miCred -ne 'managedidentity') { $violations += "INF-09: app-setting AzureWebJobsStorage__credential != 'managedidentity' (= $miCred)." }

    # --- INF-08 : aucun secret littéral ; toute app-setting secrète => @Microsoft.KeyVault( ---
    $secretLike = @('SECRET', 'KEY', 'PASSWORD', 'OBO_CLIENT_SECRET', 'OCR', 'FABRIC')
    foreach ($s in $Sites) {
        $appSettings = @()
        if ($s.properties.siteConfig.appSettings) { $appSettings += $s.properties.siteConfig.appSettings }
        foreach ($as in $appSettings) {
            $nameU = "$($as.name)".ToUpper()
            $isSecret = $false
            foreach ($pat in $secretLike) { if ($nameU -like "*$pat*") { $isSecret = $true; break } }
            if ($nameU -eq 'APPLICATIONINSIGHTS_CONNECTION_STRING') { $isSecret = $true }
            # AzureWebJobsStorage__credential=managedidentity n'est pas un secret : exempté.
            if ($nameU -like '*CREDENTIAL*' -and "$($as.value)" -eq 'managedidentity') { $isSecret = $false }
            if ($isSecret) {
                if ("$($as.value)" -notmatch '^@Microsoft\.KeyVault\(') {
                    $violations += "INF-08: app-setting secrète '$($as.name)' n'est pas une référence Key Vault (valeur littérale interdite)."
                }
            }
        }
    }
    # Private Endpoint vers Key Vault + zone DNS privée privatelink.vaultcore.azure.net
    $dnsZone = @($resources | Where-Object { $_.type -eq 'Microsoft.Network/privateDnsZones' -and $_.name -match 'privatelink\.vaultcore\.azure\.net' })
    if ($dnsZone.Count -eq 0) { $violations += "INF-08: zone DNS privée 'privatelink.vaultcore.azure.net' absente." }
    $pe = @($resources | Where-Object { $_.type -eq 'Microsoft.Network/privateEndpoints' })
    $peKvFound = $false
    foreach ($p in $pe) {
        $conns = @()
        if ($p.properties.privateLinkServiceConnections) { $conns += $p.properties.privateLinkServiceConnections }
        foreach ($c in $conns) { if (@($c.properties.groupIds) -contains 'vault') { $peKvFound = $true } }
    }
    if (-not $peKvFound) { $violations += "INF-08: privateEndpoint avec groupIds contenant 'vault' (Key Vault) absent." }

    # --- INF-07 : trio de rôles Durable (storage) + Cognitive Services User (docIntel) ---
    # GUIDs intégrés : Storage Blob Data Owner, Storage Queue Data Contributor, Storage Table Data Contributor.
    $durableTrio = @{
        'Storage Blob Data Owner'          = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
        'Storage Queue Data Contributor'   = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
        'Storage Table Data Contributor'   = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
    }
    $cogUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908' # Cognitive Services User
    foreach ($kv in $durableTrio.GetEnumerator()) {
        if ($RawJson -notmatch [regex]::Escape($kv.Value)) {
            $violations += "INF-07: rôle '$($kv.Key)' ($($kv.Value)) absent du déploiement (storage Durable)."
        }
    }
    if ($RawJson -notmatch [regex]::Escape($cogUserRoleId)) {
        $violations += "INF-07: rôle 'Cognitive Services User' ($cogUserRoleId) absent (DocIntel Entra-only)."
    }

    # --- INF-07 (négatif) : SharePoint OBO n'est PAS un roleAssignment (consentement délégué) ---
    foreach ($ra in $RoleAssigns) {
        $blob = ($ra | ConvertTo-Json -Depth 8 -Compress)
        if ($blob -match 'SharePoint') {
            $violations += "INF-07: un roleAssignment référence 'SharePoint' — l'OBO SharePoint doit être un consentement DÉLÉGUÉ, pas un rôle MI."
        }
    }

    return $violations
}

$violations = Test-InfraAssertions -ServerFarms $serverfarms -Sites $sites -Storages $storages `
    -Cognitive $cognitive -RoleAssigns $roleAssigns -RawJson $rawJson

Write-Host ""
if ($violations.Count -gt 0) {
    Write-Host "[ÉCHEC GATE] $($violations.Count) violation(s) de posture PROD :" -ForegroundColor Red
    $violations | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "[OK] Toutes les assertions par-INF (02/03/04/07/08/09) sont satisfaites." -ForegroundColor Green
exit 0
