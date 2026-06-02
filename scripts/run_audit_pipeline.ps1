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

.EXAMPLE
.\run_audit_pipeline.ps1 -DocumentPath "C:\temp\mon_contrat.pdf"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$DocumentPath,
    
    [Parameter(Mandatory=$false)]
    [string]$Upn = "System"
)

# Résolution sécurisée du dossier du script (évite les problèmes de CWD)
$ScriptDir = $PSScriptRoot

# Fichiers temporaires générés par le pipeline
$OcrResultFile = Join-Path $ScriptDir "temp_ocr_result.json"
$AuditResultJson = Join-Path $ScriptDir "final_audit_report.json"
$AuditResultCsv = Join-Path $ScriptDir "final_audit_report.csv"

Write-Host "=========================================" -ForegroundColor Magenta
Write-Host " DÉMARRAGE DU PIPELINE AC360 (Lancé par: $Upn)" -ForegroundColor Magenta
Write-Host "=========================================" -ForegroundColor Magenta

# Vérification du document
if (-not (Test-Path $DocumentPath)) {
    Write-Host "ERREUR : Le document '$DocumentPath' est introuvable." -ForegroundColor Red
    exit 1
}

# --- PHASE 3 : OCR AZURE ---
Write-Host "`n>>> [PHASE 3] Extraction OCR via Azure Document Intelligence..." -ForegroundColor Cyan
python (Join-Path $ScriptDir "process_document_ocr.py") $DocumentPath --output $OcrResultFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR : L'extraction OCR a échoué. Arrêt du pipeline." -ForegroundColor Red
    exit 1
}

# --- PHASE 4 : AUDIT FABRIC ---
Write-Host "`n>>> [PHASE 4] Audit & Croisement avec Microsoft Fabric..." -ForegroundColor Cyan
python (Join-Path $ScriptDir "audit_fabric_comparison.py") $OcrResultFile --out-json $AuditResultJson --out-csv $AuditResultCsv
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR : L'audit Fabric a échoué. Arrêt du pipeline." -ForegroundColor Red
    exit 1
}

# --- PHASE 6 : CONTRÔLE JURIDIQUE & FIC ---
Write-Host "`n>>> [PHASE 6] Complétude Juridique & Génération de la FIC..." -ForegroundColor Cyan
$ClientNameFallback = "CLIENT_INCONNU"
if (Test-Path $AuditResultJson) {
    $AuditData = Get-Content $AuditResultJson | ConvertFrom-Json
    if ($AuditData.client_document) { $ClientNameFallback = $AuditData.client_document }
}

# Génération de la FIC Word et capture du chemin
$FicOutput = python (Join-Path $ScriptDir "generate_fic_draft.py") $AuditResultJson --output-dir $ScriptDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING : La génération de la FIC a échoué." -ForegroundColor Yellow
}
$FicGeneratedPath = ""
foreach ($line in $FicOutput) {
    Write-Host $line
    if ($line -match "^FIC_GENERATED_PATH=(.*)$") {
        $FicGeneratedPath = $matches[1]
    }
}

# --- PHASE 5 : POST-AUDIT (ALERTES & NETTOYAGE) ---
Write-Host "`n>>> [PHASE 5] Clôture, Alertes Teams et Sécurité RGPD..." -ForegroundColor Cyan
$PostAuditCmd = "python `"$($ScriptDir)\post_audit_workflow.py`" `"$AuditResultJson`" `"$DocumentPath`""
if (-not [string]::IsNullOrWhiteSpace($FicGeneratedPath)) {
    $PostAuditCmd += " --fic-file `"$FicGeneratedPath`""
}
Invoke-Expression $PostAuditCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR : Le Post-Audit a rencontré un problème." -ForegroundColor Red
    exit 1
}

# Nettoyage des JSON temporaires
if (Test-Path $OcrResultFile) { Remove-Item $OcrResultFile }
if (Test-Path $AuditResultJson) { Remove-Item $AuditResultJson }
if (Test-Path $AuditResultCsv) { Remove-Item $AuditResultCsv }

Write-Host "`n=========================================" -ForegroundColor Magenta
Write-Host " PIPELINE TERMINÉ AVEC SUCCÈS ! " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Magenta
