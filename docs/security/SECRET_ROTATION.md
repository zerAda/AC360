# Procédure de Rotation des Secrets — AC360

> **Classification** : Confidentiel — Accès restreint RSSI + Admin  
> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Fréquence de révision** : Trimestrielle

---

## Vue d'ensemble

La rotation régulière des secrets limite l'impact d'une compromission non détectée. Elle s'applique à tous les secrets utilisés par le projet AC360.

---

## Inventaire des secrets

| Secret | Localisation | Rotation | Dernier changement | Prochain changement |
|---|---|---|---|---|
| `AZURE_OCR_KEY` | Azure Key Vault → Variable Power Platform | 90 jours | À compléter | À compléter |
| `ENTRA_CLIENT_SECRET` | Azure Key Vault → Variable Power Platform | 90 jours | À compléter | À compléter |
| `TEAMS_WEBHOOK_URL` | Variable d'environnement Power Platform | Si compromis | À compléter | N/A (événement) |
| Certificats TLS (API Python) | Azure App Service | 1 an | À compléter | À compléter |

---

## Procédure générale de rotation

### Étape 1 : Créer le nouveau secret (SANS révoquer l'ancien)

```powershell
# Exemple pour AZURE_OCR_KEY via Azure CLI
az cognitiveservices account keys regenerate `
  --name <nom-ressource-cognitive> `
  --resource-group <resource-group> `
  --key-name key1
```

> ⚠️ Conserver l'ancien secret actif jusqu'à la fin de la procédure pour éviter toute interruption de service.

### Étape 2 : Mettre à jour Azure Key Vault

```powershell
az keyvault secret set `
  --vault-name <nom-key-vault> `
  --name "AZURE-OCR-KEY" `
  --value "<nouvelle-valeur>"
```

### Étape 3 : Mettre à jour les variables d'environnement Power Platform

1. Ouvrir **Power Platform Admin Center**
2. Sélectionner l'environnement cible (DEV / TEST / PROD)
3. Aller dans **Variables d'environnement**
4. Mettre à jour la valeur de la variable correspondante
5. Sauvegarder

### Étape 4 : Redéployer / Republier l'agent Copilot Studio

```
1. Ouvrir Copilot Studio → Agent AC360
2. Aller dans Paramètres → Connexions
3. Vérifier que les connexions sont actives
4. Republier l'agent (Publish → Publish now)
5. Valider avec un test smoke rapide
```

### Étape 5 : Invalider l'ancien secret

```powershell
# Supprimer l'ancienne clé Cognitive Services
az cognitiveservices account keys regenerate `
  --name <nom-ressource-cognitive> `
  --resource-group <resource-group> `
  --key-name key2
```

### Étape 6 : Documenter

- Mettre à jour ce tableau avec la date de rotation
- Notifier le RSSI par email
- Archiver la preuve dans le système de ticketing GEREP

---

## Procédure spécifique : `AZURE_OCR_KEY`

**Rotation tous les 90 jours**

| Étape | Action | Qui |
|---|---|---|
| 1 | Générer nouvelle clé dans Azure Cognitive Services | Admin Azure |
| 2 | Stocker dans Key Vault (`AZURE-OCR-KEY`) | Admin Azure |
| 3 | Mettre à jour variable env Power Platform (DEV → TEST → PROD) | Admin Power Platform |
| 4 | Tester l'API OCR avec un document de test | QA |
| 5 | Invalider l'ancienne clé | Admin Azure |
| 6 | Mettre à jour ce document | RSSI |

---

## Procédure spécifique : `ENTRA_CLIENT_SECRET`

**Rotation tous les 90 jours**

| Étape | Action | Qui |
|---|---|---|
| 1 | Ouvrir Entra ID → App Registrations → AC360 | Admin Entra ID |
| 2 | Créer un nouveau Client Secret (expiration 90 jours) | Admin Entra ID |
| 3 | Stocker dans Key Vault (`ENTRA-CLIENT-SECRET`) | Admin Azure |
| 4 | Mettre à jour les Connection References Power Platform | Admin Power Platform |
| 5 | Tester l'authentification SSO | QA |
| 6 | Supprimer l'ancien secret dans Entra ID | Admin Entra ID |
| 7 | Mettre à jour ce document | RSSI |

> ⚠️ **Impact** : La rotation du Client Secret nécessite une republication de l'agent Copilot Studio et une reconnexion des connecteurs.

---

## Procédure spécifique : `TEAMS_WEBHOOK_URL`

**Rotation si compromis uniquement**

| Étape | Action | Qui |
|---|---|---|
| 1 | Désactiver l'ancien webhook dans Teams Admin | Admin Teams |
| 2 | Créer un nouveau webhook entrant dans Teams | Admin Teams |
| 3 | Mettre à jour la variable Power Platform | Admin Power Platform |
| 4 | Tester l'envoi d'une notification de test | QA |
| 5 | Mettre à jour ce document | RSSI |

---

## Procédure d'urgence — Secret potentiellement compromis

> 🚨 **Si un secret a pu être exposé (commit public, log visible, screenshot partagé), activer immédiatement :**

1. **Révoquer IMMÉDIATEMENT** l'ancien secret (sans attendre la rotation propre)
2. **Générer et déployer** le nouveau secret en urgence
3. **Notifier le RSSI** : rssi@gerep.fr — sujet : `[URGENT] Secret AC360 potentiellement compromis`
4. **Ouvrir un ticket incident** dans le système GEREP
5. **Analyser l'exposition** : qui avait accès ? Quelles données ont pu être exposées ?
6. **Purger l'historique Git** si le secret a été commité (voir ci-dessous)

---

## Purge d'un secret dans l'historique Git

> ⚠️ **Opération destructive — À effectuer uniquement si un secret a été commité**

```bash
# Installer git-filter-repo
pip install git-filter-repo

# Remplacer le secret dans TOUT l'historique
git filter-repo --replace-text <(echo "VALEUR_SECRET_A_SUPPRIMER==>***REDACTED***")

# Force push sur toutes les branches
git push --force --all
git push --force --tags

# Demander à GitHub/Azure DevOps de purger le cache
# → Contacter l'admin du repo pour activer le cache purge
```

> Après la purge, **tous les clones existants** doivent être re-clonés. Notifier tous les contributeurs.

---

## Calendrier de rotation

| Mois | Action | Responsable |
|---|---|---|
| Janvier | Rotation AZURE_OCR_KEY + ENTRA_CLIENT_SECRET | Admin + RSSI |
| Avril | Rotation AZURE_OCR_KEY + ENTRA_CLIENT_SECRET | Admin + RSSI |
| Juillet | Rotation AZURE_OCR_KEY + ENTRA_CLIENT_SECRET | Admin + RSSI |
| Octobre | Rotation AZURE_OCR_KEY + ENTRA_CLIENT_SECRET | Admin + RSSI |

---

*Document maintenu par le RSSI GEREP — Contact : rssi@gerep.fr*
