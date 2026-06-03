<#
.SYNOPSIS
Orchestrateur global pour exécuter le pipeline d'audit documentaire (Phases 3, 4 et 5).

.DESCRIPTION
Ce script enchaîne les différentes étapes métier :
1. (Phase 3) Extraction OCR via Azure Document Intelligence.
2. (Phase 4) Croisement avec la base de données Fabric (Artus) pour trouver les écarts.
3. (Phase 5) Clôture : Alertes Teams et archivage sécurisé du document.

.PARAMETER DocumentPath
Chemin du document PDF à auditer.

.PARAMETER Upn
Identifiant de l'utilisateur déclencheur (UPN Azure AD).

.PARAMETER JobDir
Répertoire de travail isolé pour ce job (UUID).

.EXAMPLE
.\run_audit_pipeline.ps1 -DocumentPath "C:\AC360_Docs\mon_contrat.pdf" -JobDir "C:\jobs\<uuid>"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$DocumentPath,

    [Parameter(Mandatory=$false)]
    [string]$Upn = "System",

    [Parameter(Mandatory=$false)]
    [string]$JobDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Validation des paramètres d'entrée (sécurité)
# ---------------------------------------------------------------------------
# Refus des chemins UNC (\\serveur\partage)
if ($DocumentPath -match '^\\\\') {
    Write-Error "SÉCURITÉ : Les chemins UNC ne sont pas autorisés (DocumentPath)."
    exit 1
}

# Refus des caractères dangereux dans DocumentPath
$DangerousChars = @(';', '&', '|', '`', '$', '<', '>', '(', ')', '{', '}', '"', "'")
foreach ($char in $DangerousChars) {
    if ($DocumentPath.Contains($char)) {
        Write-Error "SÉCURITÉ : Le chemin du document contient un caractère interdit : '$char'."
        exit 1
    }
}

# Résolution sécurisée du dossier du script (évite les problèmes de CWD)
$ScriptDir = $PSScriptRoot

# Si JobDir non fourni, on crée un sous-dossier UUID dans $ScriptDir
if ([string]::IsNullOrWhiteSpace($JobDir)) {
    $JobDir = Join-Path $ScriptDir ([System.Guid]::NewGuid().ToString())
}
if (-not (Test-Path $JobDir)) {
    New-Item -ItemType Directory -Path $JobDir -Force | Out-Null
}

# Fichiers temporaires isolés dans le répertoire de job
$OcrResultFile   = Join-Path $JobDir "temp_ocr_result.json"
$AuditResultJson = Join-Path $JobDir "final_audit_report.json"
$AuditResultCsv  = Join-Path $JobDir "final_audit_report.csv"

# Log structuré JSON
$LogFile = Join-Path $JobDir "pipeline.log.json"

function Write-JsonLog {
    param([string]$Phase, [string]$Status, [string]$Message)
    $Entry = @{
        timestamp = (Get-Date -Format "o")
        phase     = $Phase
        status    = $Status
        message   = $Message
        upn       = $Upn
        job_dir   = $JobDir
    } | ConvertTo-Json -Compress
    Add-Content -Path $LogFile -Value $Entry -Encoding UTF8
    Write-Host $Entry
}

try {
    Write-JsonLog -Phase "INIT" -Status "START" -Message "Démarrage du pipeline AC360 pour : $DocumentPath"

    # Vérification du document
    if (-not (Test-Path $DocumentPath -ErrorAction Stop)) {
        Write-JsonLog -Phase "INIT" -Status "ERROR" -Message "Document introuvable : $DocumentPath"
        exit 1
    }

    # -----------------------------------------------------------------------
    # PHASE 3 : OCR AZURE
    # -----------------------------------------------------------------------
    Write-JsonLog -Phase "PHASE3_OCR" -Status "START" -Message "Extraction OCR via Azure Document Intelligence"
    & python (Join-Path $ScriptDir "process_document_ocr.py") $DocumentPath --output $OcrResultFile -ErrorAction Stop
    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Phase "PHASE3_OCR" -Status "ERROR" -Message "L'extraction OCR a échoué. Code : $LASTEXITCODE"
        exit 1
    }
    Write-JsonLog -Phase "PHASE3_OCR" -Status "SUCCESS" -Message "OCR terminé -> $OcrResultFile"

    # -----------------------------------------------------------------------
    # PHASE 4 : AUDIT FABRIC
    # -----------------------------------------------------------------------
    Write-JsonLog -Phase "PHASE4_FABRIC" -Status "START" -Message "Audit & Croisement avec Microsoft Fabric"
    & python (Join-Path $ScriptDir "audit_fabric_comparison.py") $OcrResultFile --out-json $AuditResultJson --out-csv $AuditResultCsv -ErrorAction Stop
    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Phase "PHASE4_FABRIC" -Status "ERROR" -Message "L'audit Fabric a échoué. Code : $LASTEXITCODE"
        exit 1
    }
    Write-JsonLog -Phase "PHASE4_FABRIC" -Status "SUCCESS" -Message "Rapport -> $AuditResultJson"

    # -----------------------------------------------------------------------
    # PHASE 6 : CONTRÔLE JURIDIQUE & FIC
    # -----------------------------------------------------------------------
    Write-JsonLog -Phase "PHASE6_FIC" -Status "START" -Message "Complétude Juridique & Génération de la FIC"
    $FicOutput = & python (Join-Path $ScriptDir "generate_fic_draft.py") $AuditResultJson --output-dir $JobDir -ErrorAction Stop
    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Phase "PHASE6_FIC" -Status "WARNING" -Message "La génération de la FIC a échoué."
    }

    $FicGeneratedPath = ""
    foreach ($line in $FicOutput) {
        Write-Host $line
        if ($line -match "^FIC_GENERATED_PATH=(.*)$") {
            $FicGeneratedPath = $matches[1]
        }
    }

    # -----------------------------------------------------------------------
    # PHASE 5 : POST-AUDIT (ALERTES & NETTOYAGE)
    # -----------------------------------------------------------------------
    Write-JsonLog -Phase "PHASE5_POST" -Status "START" -Message "Clôture, Alertes Teams et Sécurité RGPD"

    $postAuditArgs = @(
        (Join-Path $ScriptDir "post_audit_workflow.py"),
        $AuditResultJson,
        $DocumentPath
    )
    if (-not [string]::IsNullOrWhiteSpace($FicGeneratedPath)) {
        $postAuditArgs += @("--fic-file", $FicGeneratedPath)
    }
    & python @postAuditArgs

    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Phase "PHASE5_POST" -Status "ERROR" -Message "Le Post-Audit a rencontré un problème. Code : $LASTEXITCODE"
        exit 1
    }
    Write-JsonLog -Phase "PHASE5_POST" -Status "SUCCESS" -Message "Post-audit terminé."

    # -----------------------------------------------------------------------
    # Nettoyage des fichiers temporaires du job
    # -----------------------------------------------------------------------
    if (Test-Path $OcrResultFile)   { Remove-Item $OcrResultFile   -ErrorAction Stop }
    if (Test-Path $AuditResultJson) { Remove-Item $AuditResultJson -ErrorAction Stop }
    if (Test-Path $AuditResultCsv)  { Remove-Item $AuditResultCsv  -ErrorAction Stop }

    Write-JsonLog -Phase "DONE" -Status "SUCCESS" -Message "Pipeline terminé avec succès."

} catch {
    $ErrMsg = $_.Exception.Message
    Write-JsonLog -Phase "FATAL" -Status "ERROR" -Message "Exception fatale : $ErrMsg"
    exit 1
}
