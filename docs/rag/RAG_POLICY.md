# Politique RAG Enterprise — AC360

> **Version** : 1.0  
> **Date** : 2026-06-03  
> **Approbateurs** : RSSI + DPO + Product Owner  
> **Révision** : Semestrielle ou après tout incident RAG

---

## Définition

Le RAG (Retrieval-Augmented Generation) est le mécanisme par lequel AC360 récupère des informations depuis des sources documentaires pour enrichir ses réponses. Cette politique définit les règles d'usage de ce mécanisme.

---

## 1. Sources autorisées

### Source principale et unique autorisée

```
Site SharePoint : gerep75008.sharepoint.com
Site : /sites/dev-assistant-client-360
Bibliothèque : /Dossiers_Clients_POC
Scope : Bibliothèque complète (selon droits utilisateur)
```

| Source | Statut | Justification |
|---|---|---|
| SharePoint `/sites/dev-assistant-client-360/Dossiers_Clients_POC` | ✅ AUTORISÉE | Source de vérité des données client GEREP |
| Autres sites SharePoint GEREP (si nécessaire) | ⚠️ Sur approbation | À valider par le Product Owner + RSSI |

---

## 2. Sources interdites

| Source | Statut | Raison |
|---|---|---|
| **Web public** | ❌ INTERDITE | Données non vérifiées, hors périmètre GEREP, risque hallucination |
| **Connaissances générales du modèle** | ❌ INTERDITE | `useModelKnowledge = false` — données non sourcées |
| **Outlook / Boîtes mail** | ❌ INTERDITE | Données personnelles, hors gouvernance documentaire |
| **OneDrive personnel** | ❌ INTERDITE | Documents non gouvernés, hors périmètre GEREP |
| **Microsoft Fabric** | ❌ INTERDITE (sauf action validée) | Accès uniquement via identité managée/service principal si activé — approbation RSSI requise |
| **Autres SharePoint** | ❌ INTERDITE par défaut | Approbation Product Owner + RSSI requise |
| **Fichiers uploadés localement** | ❌ INTERDITE en PROD | Réservé au topic expérimental LancerAudit (non activé PROD) |

---

## 3. Comportement si aucune source disponible

**Règle fondamentale** : AC360 ne doit JAMAIS inventer ou extrapoler des informations client.

Si aucun document correspondant n'est trouvé dans SharePoint :

```
✅ Réponse correcte :
"Je n'ai pas trouvé d'information sur [nom du client / sujet] dans les documents 
disponibles dans SharePoint. Vérifiez que le dossier est bien accessible ou 
contactez votre gestionnaire de comptes."

❌ Réponse incorrecte :
"D'après ce que je sais, le client Alpha est dans le secteur..."
→ INTERDIT — données non sourcées
```

---

## 4. Citations obligatoires

**Toute réponse AC360 incluant des données client DOIT citer sa source.**

### Format de citation obligatoire

```
📄 Source : [Nom du fichier] — Section "[Titre de la section]"
   Dernière modification : [Date si disponible]
```

### Niveaux de confiance

| Niveau | Label | Description | Comportement AC360 |
|---|---|---|---|
| 🟢 **CONFIRMÉ** | Information trouvée dans le document | Source claire et explicite dans le document | Répondre avec citation |
| 🟡 **INCERTAIN** | Information partielle ou implicite | Information déduite du contexte, non explicitement écrite | Répondre avec nuance + citation + avertissement |
| 🔴 **ABSENT** | Information non trouvée | Aucun document ne contient cette information | Répondre avec message de non-disponibilité |

---

## 5. Gestion des conflits entre sources

Si deux documents SharePoint contiennent des informations contradictoires sur le même client :

```
✅ Comportement correct :
"J'ai trouvé des informations contradictoires sur ce sujet :
- Document A (date X) indique : [info 1]
- Document B (date Y) indique : [info 2]
Je vous recommande de vérifier avec votre gestionnaire de comptes lequel est à jour."

❌ Comportement incorrect :
- Choisir arbitrairement une source sans le signaler
- Synthétiser sans signaler le conflit
```

---

## 6. Un seul client par réponse

**AC360 ne doit jamais agréger des données de plusieurs clients dans une même réponse.**

| Demande | Comportement |
|---|---|
| "Donne-moi le dossier Alpha" | ✅ Réponse sur Alpha uniquement |
| "Compare Alpha et Beta" | ❌ Refus — Répondre : "Je ne compare pas les dossiers de plusieurs clients pour des raisons de confidentialité" |
| "Qui paie le plus chez nous ?" | ❌ Refus — Répondre : "Je n'effectue pas d'analyse agrégée sur l'ensemble des clients" |
| "Résume Alpha et Beta ensemble" | ❌ Refus |

---

## 7. Format standard des réponses

### Réponse commerciale standard

```markdown
## Dossier [Nom Client] — [Type de demande]

**Synthèse** : [2-3 phrases résumant l'essentiel]

**Détails** :
- [Point 1]
- [Point 2]
- [Point 3]

**Points d'attention** : [Si applicable]
- 🔴 [Point critique]
- 🟡 [Point important]

**Sources** :
📄 [Nom du fichier] — Section "[Section]" ([Date si disponible])
📄 [Nom du fichier] — Section "[Section]" ([Date si disponible])
```

### Réponse juridique standard

```markdown
## Éléments juridiques — [Nom Client]

⚠️ **Important** : Les informations suivantes sont extraites des documents SharePoint à titre indicatif. Elles ne constituent pas un avis juridique. Pour toute décision juridique, consultez le service juridique GEREP.

**Clause identifiée** : [Texte extrait]

📄 Source : [Nom du fichier] — Article/Section [X]
```

### Réponse "Source absente"

```markdown
Je n'ai pas trouvé d'information sur **[sujet/client]** dans les documents disponibles.

**Ce que vous pouvez faire** :
1. Vérifier que le dossier du client est bien déposé dans SharePoint
2. Contacter votre gestionnaire de comptes
3. Reformuler votre question avec un autre terme

**Sources consultées** : Dossiers_Clients_POC — Site dev-assistant-client-360
```

---

## 8. Confidentialité et isolation

- **Isolation par utilisateur** : AC360 accède uniquement aux documents que l'utilisateur est autorisé à voir dans SharePoint
- **Pas de mémorisation entre sessions** : Aucun contenu de dossier client n'est persisté entre les conversations
- **Pas de cross-contamination** : Les informations d'un client ne peuvent pas « contaminer » la réponse d'un autre client dans des sessions différentes

---

## 9. Gouvernance RAG

| Contrôle | Responsable | Fréquence |
|---|---|---|
| Vérification des sources autorisées | Admin Power Platform | À chaque modification de knowledge source |
| Test de comportement "source absente" | QA | Avant chaque release |
| Test d'isolation client | QA + RSSI | Avant chaque release |
| Audit des citations en réponse | Product Owner | Mensuel (sample review) |
| Revue de la politique RAG | RSSI + DPO | Semestriel |

---

*Document approuvé par : [RSSI — à signer] [DPO — à signer] — Date : [À compléter]*
