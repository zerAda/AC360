# deploy/azure — onix sur Azure / AKS

Déploiement de la stack onix (Onyx + Ollama + access-gateway + onix-actions) sur
**AKS**, région **France Central**, avec **Postgres + Redis managés**, OpenSearch +
MinIO in-cluster, **Ollama CPU** (GPU ajoutable), **RBAC via access-gateway FOSS**.

| Fichier | Rôle |
|---|---|
| [`../../docs/DEPLOY_AZURE.md`](../../docs/DEPLOY_AZURE.md) | **Runbook** pas-à-pas (az + helm), gotchas, coûts, limites |
| `values-azure.yaml` | Overrides Helm pour `onix-ha` (data-tier managé, Ollama CPU, ACR, télémétrie off) |
| `access-gateway.yaml` | Manifeste K8s de la passerelle RBAC (absente du chart) — Deployment/Service/HPA |
| `setup-entra.sh` | Crée les apps Entra (SSO + Graph groupes + SharePoint) + secrets Key Vault — **à lancer sur votre poste az** |

> ⚠️ IaC non validée dans le sandbox d'audit (ni `az` ni cluster). `helm template`
> + `az deployment ... --what-if` avant prod. Bicep/Terraform = étape suivante.
