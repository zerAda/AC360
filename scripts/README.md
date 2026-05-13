# Scripts README

## Overview

This folder contains read-only templates for SharePoint inventory and permissions review.

## Contents

| Script | Description |
|--------|-------------|
| `sharepoint_inventory_readonly_template.ps1` | Template to inventory SharePoint sites |
| `sharepoint_permissions_review_readonly_template.ps1` | Template to export permissions |

## Important Rules

- **ALL SCRIPTS ARE READ-ONLY**
- **NO script should modify any data**
- **NO script should change permissions**
- **NO script should download documents**
- **Use at your own risk**
- **Test in dev environment first**

## Prerequisites

- PowerShell 5.1 or later
- PnP PowerShell module: `Install-Module -Name PnP.PowerShell`
- SharePoint read permissions

## Usage

1. Open PowerShell as Administrator
2. Modify the configuration variables at the top of each script
3. Run the script
4. Review the export file

## Support

These are templates provided as-is. Modify for your environment.

---

*Document created : 2026-04-28 - Scripts README*