# AC360 — Guide de démo

Deux façons de démontrer AC360. La première **ne coûte rien et ne nécessite aucun
Azure**. La seconde ajoute la vraie brique OCR via le **tier gratuit F0**.

---

## Option A — Démo hors-ligne (0 €, 0 cloud, immédiate)

Montre la valeur réelle du produit : extraction → rapprochement client →
comparaison typée → verdict d'audit → brouillon de FIC.

```bash
python scripts/run_demo.py --fic
```

Sortie attendue (données synthétiques `demo/sample_*.json`) :

```
  AC360 — RAPPORT D'AUDIT (DÉMO)
  Client (document)   : GEREP SA
  Référence Fabric    : GEREP SA
  Score correspondance: 100.0 %
  VERDICT GLOBAL      : >>> ECART <<<
  champ                     document      référence     statut
  plafond_hospitalisation   1 500 €       2000          MISMATCH
  ...
  [FIC] Brouillon généré : demo/out/FIC_Demo_GEREP_SA.docx
```

→ Le produit détecte l'écart de plafond (1 500 € au contrat vs 2 000 en gestion)
et génère un brouillon de Fiche d'Information et de Conseil prêt à relire.

**Variantes :**
```bash
python scripts/run_demo.py --ocr mon_export_ocr.json     # votre propre JSON OCR
python scripts/run_demo.py --reference ma_reference.json # votre propre référence
```

---

## Option B — Démo avec OCR réel (tier gratuit F0)

### 1. Provisionner la ressource gratuite (une fois, 0 €)
```powershell
az provider register --namespace Microsoft.CognitiveServices
# attendre "Registered" :
az provider show -n Microsoft.CognitiveServices --query registrationState -o tsv

az cognitiveservices account create `
  --name ac360-docintel-gerep --resource-group GEREP `
  --kind FormRecognizer --sku F0 --location francecentral --yes `
  --custom-domain ac360-docintel-gerep
```

### 2. Renseigner `.env`
```powershell
$ep  = az cognitiveservices account show --name ac360-docintel-gerep -g GEREP --query properties.endpoint -o tsv
$key = az cognitiveservices account keys list --name ac360-docintel-gerep -g GEREP --query key1 -o tsv
Add-Content .env "AZURE_OCR_ENDPOINT=$ep"
Add-Content .env "AZURE_OCR_KEY=$key"
```

### 3. Lancer la démo sur un vrai PDF
```bash
python scripts/run_demo.py --pdf un_contrat_court.pdf --fic
```

> ⚠️ Limites F0 : seules les **2 premières pages** d'un PDF sont analysées, taille
> max **4 Mo**. Utilisez un document court (1–2 pages) pour la démo. Passage en
> S0 plus tard = `--sku S0`, aucun changement de code.

### Sans installer quoi que ce soit
Vous pouvez aussi montrer la qualité d'extraction directement dans le navigateur :
[Document Intelligence Studio](https://documentintelligence.ai.azure.com/studio).

---

## Ce que la démo prouve

| Capacité | Démontrée |
|---|---|
| Extraction des champs (libellés OCR variés → champs canoniques) | ✅ |
| Rapprochement client (fuzzy matching strict ≥ 85 %) | ✅ |
| Comparaison typée MATCH / MISMATCH / UNCERTAIN / MISSING + confiance | ✅ |
| Verdict d'audit (CONFORME / ECART / INCERTAIN / CLIENT_NON_TROUVE) | ✅ |
| Génération du brouillon de FIC (.docx) | ✅ |
| Sécurité : aucune donnée inventée, refus si client non trouvé | ✅ |

Les fixtures `demo/*.json` sont **synthétiques** — aucune donnée client réelle.
