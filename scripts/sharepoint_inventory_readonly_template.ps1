# SharePoint Inventory - Read Only Template

## Script d'Inventaire SharePoint (Template Read-Only)

### Description
Template PowerShell pour inventorier les sites et bibliothèques SharePoint cibles. CE SCRIPT EST READ-ONLY - aucune modification.

### Pré-requis
- Module PnP PowerShell installé : `Install-Module -Name PnP.PowerShell`
- Droits d'administration SharePoint ou lecture sur les sites

### Configuration

```powershell
# === CONFIGURATION À MODIFIER ===
$TenantUrl = "https://contoso.sharepoint.com"  # Modifier avec votre tenant
$SiteUrl = "https://contoso.sharepoint.com/sites/clients"  # Modifier avec votre site
$ExportPath = "C:\_temp\inventory_export.csv"  # Chemin Export
# ==================================
```

### Script Principal

```powershell
# ============================================================
# SharePoint Inventory - Read Only Template
# Objectif : Inventorque les sites et biblis SharePoint
#uteur :
#Date : 2026-04-28
#Mode : READ-ONLY - Aucune modification des donnes
# ============================================================

# Configuration
$TenantUrl = "https://contoso.sharepoint.com"
$SiteUrl = "https://contoso.sharepoint.com/sites/clients"
$ExportPath = "C:\temp\inventory_export.csv"

Write-Host "=== SharePoint Inventory - Read Only ===" -ForegroundColor Cyan
Write-Host "Ce script est en mode READ-ONLY" -ForegroundColor Yellow

# Connexion (sans droit en criture)
$Credential = Get-Credential -Message "Entrez vos identifiants SharePoint"
Connect-PnPTenant -Url $TenantUrl -Credentials $Credential

# Rcuprer les sites
Write-Host "Rcupration des sites..." -ForegroundColor Green
# [PATCH HATER] Correction de la faute de syntaxe fatale et de la mauvaise commande
$Sites = Get-PnPTenantSite | Select-Object Title, Url, Template

# Exporter
$Results = @()
foreach ($Site in $Sites) {
    Write-Host "Analyse : $($Site.Title)"
    $Results += [PSCustomObject]@{
        Title = $Site.Title
        Url = $Site.Url
        Template = $Site.Template
    }
}

# Exporter vers CSV
$Results | Export-Csv -Path $ExportPath -NoTypeInformation
Write-Host "Export termin : $ExportPath" -ForegroundColor Green
```

### LimitationsConnues

- Ncessite le module PnP.PowerShell
- Droits de lecture minimum
- Peut tre long sur gros tenants

---

*Document cr : 2026-04-28 - Template Inventaire*