# SharePoint Permissions Review - Read Only Template

## Script de Revue des Permissions (Template Read-Only)

### Description
Template PowerShell pour exporter les permissions SharePoint. CE SCRIPT EST READ-ONLY - aucune modification.

### Pré-requis
- Module PnP PowerShell installé
- Droits Owner ou Admin sur le site

### Configuration

```powershell
# === CONFIGURATION À MODIFIER ===
$TenantUrl = "https://contoso.sharepoint.com"
$SiteUrl = "https://contoso.sharepoint.com/sites/clients"
$OutputPath = "C:\temp\permissions_export.csv"
# ==================================
```

### Script Principal

```powershell
# ============================================================
# SharePoint Permissions Review - Read Only
# Objectif : Exporter les permissions SharePoint
#uteur :
#Date : 2026-04-28
#Mode : READ-ONLY - Aucune modification
# ============================================================

param(
    [string]$SiteUrl = "https://contoso.sharepoint.com/sites/clients",
    [string]$OutputPath = "C:\temp\permissions_export.csv"
)

Write-Host "=== SharePoint Permissions Review - Read Only ===" -ForegroundColor Cyan
Write-Host "Mode : READ-ONLY" -ForegroundColor Yellow

# Connexion
$Credential = Get-Credential -Message "Entrez vos identifiants SharePoint"
Connect-PnPSite -Url $SiteUrl -Credentials $Credential

# Obtenir les droits
Write-Host "Rcupration des groupes et permissions..." -ForegroundColor Green

$Permissions = @()

# Groupes SharePoint
$Groups = Get-PnPGroup
foreach ($Group in $Groups) {
    Write-Host "Groupe : $($Group.Title)"
    $Permissions += [PSCustomObject]@{
        Type = "Groupe"
        Nom = $Group.Title
        Utilisateurs = ($Group.Users | ForEach-Object { $_.Title }) -join ","
    }
}

# Exporter
$Permissions | Export-Csv -Path $OutputPath -NoTypeInformation
Write-Host "Export termin : $OutputPath" -ForegroundColor Green
Write-Host "Merci de vrifier les rsultat" -ForegroundColor Cyan
```

### Checklist Manuelle Complémentaire

#### À faire manuellement :

| Tâche | Action |
|-------|--------|
| [ ] Vérifier les liens de partage | Aller dans SharePoint > Partage |
| [ ] Identifier les liens "Anyone" | Supprimer si trouvés |
| [ ] Vérifier les liens externes | Auditor et nettoyer |
| [ ] Vérifier les permissions héritées | Réduire si trop larges |

---

*Document créé : 2026-04-28 - Template Permissions*