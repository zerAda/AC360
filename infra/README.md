# AC360 — Infrastructure as Code (`infra/`)

Codifie la **posture de sécurité durcie vérifiée en live** (2026-06-11) pour empêcher
la dérive de configuration — notamment la régression `httpsOnly` déjà observée après
un redéploiement.

| Fichier | Rôle |
|---|---|
| `main.bicep` | Définition des ressources + propriétés de sécurité (compile : `az bicep build` ✅) |
| `staging.parameters.json` | Valeurs d'environnement (à compléter, voir ci-dessous) |

## Posture codifiée (= état live prouvé)

- App Service + Function : `httpsOnly=true`, TLS **1.2**, FTPS **Disabled**, identité **SystemAssigned**.
- Function : **ingress verrouillé** aux IP sortantes de la passerelle (`Allow` + `Deny all` implicite).
- Key Vault : **RBAC**, **purge protection**, soft-delete 90 j ; MI en *Key Vault Secrets User* uniquement.
- Storage : pas de blob public, TLS 1.2.
- Document Intelligence : `disableLocalAuth` paramétrable (Entra-only).

## ⚠️ Avant tout `apply` — règle absolue : `what-if` d'abord

Les tableaux `gatewayOutboundIps` et `keyVaultSecretsReaderPrincipalIds` sont **vides**
par défaut. **Ne pas appliquer tel quel** : un déploiement avec `gatewayOutboundIps`
vide **retirerait le verrou d'ingress** de la Function. Renseignez-les depuis le live :

```bash
# IP sortantes de la passerelle (à autoriser sur la Function)
az webapp show -g rg-ac360-staging -n ac360-gateway-staging \
  --query possibleOutboundIpAddresses -o tsv

# principalId des identités managées (lecture secrets KV)
az webapp identity show -g rg-ac360-staging -n ac360-func-staging --query principalId -o tsv
az webapp identity show -g rg-ac360-staging -n ac360-gateway-staging --query principalId -o tsv
```

Puis **toujours** prévisualiser le diff avant d'appliquer :

```bash
az deployment group what-if -g rg-ac360-staging \
  -f infra/main.bicep -p @infra/staging.parameters.json
```

N'appliquer (`az deployment group create ...`) qu'après revue du `what-if`.

## Durcissements réseau (PROD / fenêtre de maintenance)

Non activés par défaut car ils exigent l'intégration VNet des apps et risquent une
coupure du staging vivant :

- `keyVaultPublicNetworkAccess: Disabled` **après** Private Endpoint + VNet integration
  (sinon les références Key Vault des apps cassent).
- `docIntelDisableLocalAuth: true` **après** avoir accordé à la MI Function le rôle
  *Cognitive Services User* sur la ressource OCR et retiré `AZURE_OCR_KEY` des app
  settings (le code OCR supporte déjà la Managed Identity).

Cf. `docs/security/SECURITY_AUDIT_STAGING.md` § « Résiduels infra ».
