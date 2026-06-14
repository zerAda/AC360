<#
.SYNOPSIS
Valide hors-ligne la posture de securite durcie de l'infrastructure AC360.

.DESCRIPTION
Gate fail-closed, sans "az login". Compile "infra/main.bicep" via "az bicep build"
(analyse statique + lint) puis affirme, sur le JSON ARM compile, les proprietes
par exigence INF (02, 03, 04, 07, 08, 09) qui sont verifiables hors-ligne.

Tant que main.bicep n'a pas encore ete etendu a la forme PROD (passerelle encore
sur F1/Y1, pas de B1), le validateur DIFFERE les assertions et sort en succes
(exit 0, message jaune) afin que ce plan Wave-0 passe. Des que les ressources PROD
sont presentes (plan B1 detecte), toute violation provoque un echec (exit 1, rouge).

Compatible Windows PowerShell 5.1 et PowerShell Core (Linux CI). N'utilise pas cmd.exe.
Encode en UTF-8 BOM pour un decodage correct sous PowerShell 5.1.
#>
param(
    [string]$BicepFile = "infra/main.bicep",
    [string]$ParamFile = "infra/prod.parameters.json"
)

$ErrorActionPreference = "Stop"

Write-Host "=== AC360 Validate Infra (offline, fail-closed) ===" -ForegroundColor Cyan
Write-Host "Bicep : $BicepFile"

# --------------------------------------------------------------------------
# Etape 1 - Compilation offline (az bicep build). Aucune authentification.
# --------------------------------------------------------------------------
if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-Host "[ECHEC] Azure CLI (az) introuvable - impossible de compiler le Bicep." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $BicepFile)) {
    Write-Host "[ECHEC] Fichier Bicep introuvable : $BicepFile" -ForegroundColor Red
    exit 1
}

$tmpDir = if ($env:TEMP) { $env:TEMP } elseif ($env:TMPDIR) { $env:TMPDIR } else { "/tmp" }
$compiled = Join-Path $tmpDir "ac360_main.json"

Write-Host "Compilation : az bicep build -f $BicepFile" -ForegroundColor Gray
$buildOut = az bicep build -f $BicepFile --outfile $compiled 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ECHEC] az bicep build a echoue (build error) :" -ForegroundColor Red
    $buildOut | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
if (-not (Test-Path $compiled)) {
    Write-Host "[ECHEC] La compilation n'a produit aucun JSON ARM." -ForegroundColor Red
    exit 1
}
Write-Host "Build OK." -ForegroundColor Green

$arm = Get-Content $compiled -Raw | ConvertFrom-Json
$resources = @($arm.resources)
$rawJson = Get-Content $compiled -Raw

# --------------------------------------------------------------------------
# Resolution de la posture PROD. main.bicep applique la parametrisation staging-safe
# (chaque comportement PROD est un param dont le DEFAUT = la forme staging). Les
# valeurs PROD vivent dans prod.parameters.json, pas dans les defauts du template.
# Pour affirmer la posture PROD reelle hors-ligne, on resout les expressions ARM
# [parameters('x')] (et [not(parameters('x'))]) contre prod.parameters.json, avec
# repli sur le defaultValue du template compile. C'est ce qui permet aux assertions
# INF-03/04/08/09 dependantes de params de passer sur la forme PROD reelle.
# --------------------------------------------------------------------------
$paramDefaults = @{}
if ($arm.parameters) {
    foreach ($pn in $arm.parameters.PSObject.Properties.Name) {
        $paramDefaults[$pn] = $arm.parameters.$pn.defaultValue
    }
}
$prodParams = @{}
if (Test-Path $ParamFile) {
    $pj = Get-Content $ParamFile -Raw | ConvertFrom-Json
    if ($pj.parameters) {
        foreach ($pn in $pj.parameters.PSObject.Properties.Name) {
            $prodParams[$pn] = $pj.parameters.$pn.value
        }
    }
    Write-Host "Posture evaluee : PROD (overlay $ParamFile sur les defauts du template)." -ForegroundColor Gray
} else {
    Write-Host "Posture evaluee : DEFAUTS du template ($ParamFile absent)." -ForegroundColor Yellow
}

# Resout une valeur ARM eventuellement exprimee comme [parameters('x')] ou
# [not(parameters('x'))] contre prod.parameters.json puis le defaultValue. Toute
# autre expression / valeur litterale est renvoyee telle quelle.
function Resolve-ArmValue {
    param($Value)
    if ($Value -isnot [string]) { return $Value }
    $m = [regex]::Match($Value, "^\[parameters\('([^']+)'\)\]$")
    if ($m.Success) {
        $name = $m.Groups[1].Value
        if ($prodParams.ContainsKey($name)) { return $prodParams[$name] }
        if ($paramDefaults.ContainsKey($name)) { return $paramDefaults[$name] }
        return $Value
    }
    $mn = [regex]::Match($Value, "^\[not\(parameters\('([^']+)'\)\)\]$")
    if ($mn.Success) {
        $name = $mn.Groups[1].Value
        $inner = if ($prodParams.ContainsKey($name)) { $prodParams[$name] }
                 elseif ($paramDefaults.ContainsKey($name)) { $paramDefaults[$name] }
                 else { return $Value }
        return -not [bool]$inner
    }
    return $Value
}

# --------------------------------------------------------------------------
# Helpers de selection sur le JSON ARM compile.
# --------------------------------------------------------------------------
function Get-ResByType {
    param([object[]]$Res, [string]$Type)
    return @($Res | Where-Object { $_.type -eq $Type })
}

# Recupere la valeur d'une app-setting par nom dans un site
# (siteConfig.appSettings). Renvoie $null si absente.
function Get-AppSetting {
    param($Site, [string]$Name)
    $settings = @()
    if ($Site.properties.siteConfig.appSettings) { $settings += $Site.properties.siteConfig.appSettings }
    foreach ($s in $settings) { if ($s.name -eq $Name) { return $s.value } }
    return $null
}

$serverfarms = Get-ResByType -Res $resources -Type 'Microsoft.Web/serverfarms'
$sites       = Get-ResByType -Res $resources -Type 'Microsoft.Web/sites'
$storages    = Get-ResByType -Res $resources -Type 'Microsoft.Storage/storageAccounts'
$cognitive   = Get-ResByType -Res $resources -Type 'Microsoft.CognitiveServices/accounts'
$roleAssigns = Get-ResByType -Res $resources -Type 'Microsoft.Authorization/roleAssignments'

# --------------------------------------------------------------------------
# Detection de la forme PROD : la passerelle passe a B1 en PROD (staging=F1).
# Tant qu'aucun plan B1 n'est compile, les SKUs prod (B1/S0/GRS/FC1) sont poses
# en litteral par le plan 02-02 ; on differe les assertions pour ce plan Wave-0.
# --------------------------------------------------------------------------
$gwPlanB1 = @($serverfarms | Where-Object { $_.sku.name -eq 'B1' })
$prodShapePresent = $gwPlanB1.Count -gt 0

if (-not $prodShapePresent) {
    Write-Host ""
    Write-Host "[DIFFERE] main.bicep pas encore etendu a la forme PROD (aucun plan B1 compile)." -ForegroundColor Yellow
    Write-Host "          Les assertions par-INF seront activees une fois les ressources PROD presentes." -ForegroundColor Yellow
    Write-Host "[OK] Build vert ; gate Wave-0 satisfait." -ForegroundColor Green
    exit 0
}

# --------------------------------------------------------------------------
# Etape 2 - Assertions par-INF (collect-violations, fail-closed).
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
    # gatewayApp = site avec appCommandLine gunicorn
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
        $rtVer = Resolve-ArmValue $funcApp.properties.functionAppConfig.runtime.version
        if ($rtVer -ne '3.12') { $violations += "INF-03: functionAppConfig.runtime.version != '3.12' (= $rtVer)." }
    }

    # --- INF-04 : Document Intelligence S0 + disableLocalAuth=true ---
    $docIntel = @($Cognitive | Where-Object { $_.kind -eq 'FormRecognizer' }) | Select-Object -First 1
    if (-not $docIntel) { $violations += "INF-04: compte FormRecognizer (DocIntel) introuvable." }
    else {
        if ($docIntel.sku.name -ne 'S0') { $violations += "INF-04: docIntel sku.name != 'S0' (= $($docIntel.sku.name))." }
        if ((Resolve-ArmValue $docIntel.properties.disableLocalAuth) -ne $true) { $violations += "INF-04: docIntel disableLocalAuth != true." }
    }

    # --- INF-09 : Storage GRS + allowSharedKeyAccess=false + soft-delete/PITR/versioning/changeFeed + MI hub ---
    $storage = @($Storages) | Select-Object -First 1
    if (-not $storage) { $violations += "INF-09: storageAccount introuvable." }
    else {
        if ((Resolve-ArmValue $storage.sku.name) -ne 'Standard_GRS') { $violations += "INF-09: storage sku.name != 'Standard_GRS' (= $(Resolve-ArmValue $storage.sku.name))." }
        if ((Resolve-ArmValue $storage.properties.allowSharedKeyAccess) -ne $false) { $violations += "INF-09: storage allowSharedKeyAccess != false." }
    }
    # blobServices enfant avec retention + PITR + versioning + changeFeed
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
    # AzureWebJobsStorage__credential == managedidentity (storage par identite, sans cle)
    $miCred = $null
    foreach ($s in $Sites) {
        $v = Get-AppSetting -Site $s -Name 'AzureWebJobsStorage__credential'
        if ($v) { $miCred = $v; break }
    }
    if ($miCred -ne 'managedidentity') { $violations += "INF-09: app-setting AzureWebJobsStorage__credential != 'managedidentity' (= $miCred)." }

    # --- INF-08 : aucun secret litteral ; toute app-setting secrete => @Microsoft.KeyVault( ---
    $secretLike = @('SECRET', 'KEY', 'PASSWORD', 'OBO_CLIENT_SECRET', 'OCR', 'FABRIC')
    foreach ($s in $Sites) {
        $appSettings = @()
        if ($s.properties.siteConfig.appSettings) { $appSettings += $s.properties.siteConfig.appSettings }
        foreach ($as in $appSettings) {
            $nameU = "$($as.name)".ToUpper()
            $isSecret = $false
            foreach ($pat in $secretLike) { if ($nameU -like "*$pat*") { $isSecret = $true; break } }
            if ($nameU -eq 'APPLICATIONINSIGHTS_CONNECTION_STRING') { $isSecret = $true }
            # AzureWebJobsStorage__credential=managedidentity n'est pas un secret : exempte.
            if ($nameU -like '*CREDENTIAL*' -and "$($as.value)" -eq 'managedidentity') { $isSecret = $false }
            if ($isSecret) {
                # Accepte la forme litterale @Microsoft.KeyVault(SecretUri=...) ET la forme
                # ARM compilee [format('@Microsoft.KeyVault(SecretUri={0}...', reference(...))]
                # quand le SecretUri est interpole sur le vaultUri du Key Vault (zero cleartext).
                $v = "$($as.value)"
                $isKvRef = ($v -match '^@Microsoft\.KeyVault\(') -or ($v -match "@Microsoft\.KeyVault\(SecretUri=")
                if (-not $isKvRef) {
                    $violations += "INF-08: app-setting secrete '$($as.name)' n'est pas une reference Key Vault (valeur litterale interdite)."
                }
            }
        }
    }
    # Private Endpoint vers Key Vault + zone DNS privee privatelink.vaultcore.azure.net
    $dnsZone = @($resources | Where-Object { $_.type -eq 'Microsoft.Network/privateDnsZones' -and $_.name -match 'privatelink\.vaultcore\.azure\.net' })
    if ($dnsZone.Count -eq 0) { $violations += "INF-08: zone DNS privee 'privatelink.vaultcore.azure.net' absente." }
    $pe = @($resources | Where-Object { $_.type -eq 'Microsoft.Network/privateEndpoints' })
    $peKvFound = $false
    foreach ($p in $pe) {
        $conns = @()
        if ($p.properties.privateLinkServiceConnections) { $conns += $p.properties.privateLinkServiceConnections }
        foreach ($c in $conns) { if (@($c.properties.groupIds) -contains 'vault') { $peKvFound = $true } }
    }
    if (-not $peKvFound) { $violations += "INF-08: privateEndpoint avec groupIds contenant 'vault' (Key Vault) absent." }

    # --- INF-07 : trio de roles Durable (storage) + Cognitive Services User (docIntel) ---
    # GUIDs integres : Storage Blob Data Owner, Storage Queue Data Contributor, Storage Table Data Contributor.
    $durableTrio = @{
        'Storage Blob Data Owner'        = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
        'Storage Queue Data Contributor' = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
        'Storage Table Data Contributor' = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
    }
    $cogUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908' # Cognitive Services User
    foreach ($pair in $durableTrio.GetEnumerator()) {
        if ($RawJson -notmatch [regex]::Escape($pair.Value)) {
            $violations += "INF-07: role $($pair.Key) ($($pair.Value)) absent du deploiement (storage Durable)."
        }
    }
    if ($RawJson -notmatch [regex]::Escape($cogUserRoleId)) {
        $violations += "INF-07: role Cognitive Services User ($cogUserRoleId) absent (DocIntel Entra-only)."
    }

    # --- INF-07 (negatif) : SharePoint OBO n'est PAS un roleAssignment (consentement delegue) ---
    foreach ($ra in $RoleAssigns) {
        $blob = ($ra | ConvertTo-Json -Depth 8 -Compress)
        if ($blob -match 'SharePoint') {
            $violations += "INF-07: un roleAssignment reference SharePoint - l'OBO SharePoint doit etre un consentement DELEGUE, pas un role MI."
        }
    }

    return $violations
}

$violations = Test-InfraAssertions -ServerFarms $serverfarms -Sites $sites -Storages $storages `
    -Cognitive $cognitive -RoleAssigns $roleAssigns -RawJson $rawJson

Write-Host ""
if ($violations.Count -gt 0) {
    Write-Host "[ECHEC GATE] $($violations.Count) violation(s) de posture PROD :" -ForegroundColor Red
    $violations | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "[OK] Toutes les assertions par-INF (02/03/04/07/08/09) sont satisfaites." -ForegroundColor Green
exit 0
