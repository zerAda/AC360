# RGP-05 — Procédure de demande de droits (DSR / Data Subject Request)

**Exigence :** RGP-05 (procédure documentée d'exercice des droits : accès, rectification, effacement, opposition).
**Cadre :** RGPD Art. 15 (accès), Art. 16 (rectification), Art. 17 (effacement), Art. 21 (opposition), Art. 12 (modalités et délais).
**Statut :** procédure documentée (autonome). L'identité du responsable de traitement / DPO est finalisée au sign-off DPO (RGP-02).
**Dernière MAJ :** 2026-06-15.

> Ce document décrit **comment** AC360 satisfait chaque droit de la personne concernée, compte tenu de son architecture **lecture seule** (read-only) et de ses **artefacts éphémères** (TTL 30 jours, RGP-03). Le narratif central est **l'effacement par conception** (« erasure-by-design ») : AC360 ne détient aucun enregistrement canonique de PII client, et ses copies de travail s'auto-effacent.

---

## 1. Principe directeur : AC360 n'est pas le système de référence

AC360 est un **assistant commercial en lecture seule** :

- il **ne modifie ni n'écrit jamais** de données client dans SharePoint ou dans le système ARTUS/Fabric (read-only / lecture seule, garanti par l'architecture — pas d'écriture, OBO honorant les droits SharePoint de l'utilisateur) ;
- les seules données qu'il manipule sont des **copies de travail éphémères** (document téléchargé, sortie OCR, brouillon FIC) supprimées à **30 jours** (RGP-03, fenêtre effective ~37 j) ;
- la seule trace durable est une **piste d'audit à 4 champs sans PII brute** : `user_id_hash` (SHA-256 de l'oid Entra), `document_id`, `ts_utc`, `verdict` (RGP-04 §3 / AUD-07).

**Conséquence opérationnelle majeure :** pour les droits qui portent sur le **contenu** des données client (accès au dossier, rectification d'une information erronée, effacement du dossier source), AC360 **n'est pas le bon point d'entrée** — la demande est routée vers le **système de référence** (SharePoint / ARTUS), qui est le responsable du dossier. AC360 ne peut satisfaire que ce qu'il détient réellement : des artefacts éphémères et une piste d'audit hachée.

## 2. Rôles et responsabilités

| Rôle | Responsabilité dans la procédure DSR |
|------|--------------------------------------|
| **DPO / délégué à la protection des données** | Point de contact officiel ; qualifie la demande, vérifie l'identité, arbitre, signe la réponse. Identité confirmée au sign-off RGP-02. |
| **Opérateur AC360** (single operator) | Exécute les actions techniques côté AC360 : confirmation du TTL, purge ciblée de la piste d'audit Log Analytics si requise, extraction des champs d'audit hachés. |
| **Responsable du système de référence** (SharePoint / ARTUS) | Traite tout ce qui porte sur le **contenu** du dossier client (accès, rectification, effacement de la source). |

## 3. Intake et vérification d'identité (Art. 12)

**Aucune** action d'accès, de rectification ou d'effacement n'est exécutée avant **vérification de l'identité** du demandeur (mitigation T-05-18 — anti-usurpation). Le demandeur est une personne concernée (client assuré) ou son représentant dûment mandaté.

Étapes d'intake :

1. **Réception** de la demande (canal officiel DPO).
2. **Vérification d'identité** proportionnée (Art. 12(6)) — sans collecter plus de PII que nécessaire.
3. **Qualification** du type de droit invoqué (accès / rectification / effacement / opposition).
4. **Localisation de la personne dans AC360** : la piste d'audit ne stocke **pas** l'UPN en clair mais `user_id_hash` (SHA-256 de l'oid Entra de **l'agent interne** ayant lancé l'audit, et non du client). AC360 **ne contient donc aucun identifiant direct du client** : la corrélation à un client se fait via le **système de référence** (le `document_id` pointe vers un document du dossier), pas via la piste d'audit. Ce point est documenté pour éviter toute sur-divulgation (T-05-19).
5. **Inscription** au registre des demandes (§8).

## 4. Délai de réponse (Art. 12(3))

Réponse dans **un (1) mois** à compter de la réception, prorogeable de **deux (2) mois** pour les demandes complexes ou nombreuses, avec information motivée de la personne concernée dans le mois initial. Toute prorogation est tracée au registre (§8).

## 5. Droit d'accès — Art. 15

**Ce qu'AC360 détient réellement :**

- **Artefacts éphémères** (document, OCR, FIC) : présents au maximum ~37 jours (RGP-03 §4). S'ils existent encore au moment de la demande, ils ne sont qu'une **copie** de la source ; l'accès canonique se fait sur la source.
- **Piste d'audit à 4 champs** : `user_id_hash`, `document_id`, `ts_utc`, `verdict` — **aucune PII brute du client** à exporter (RGP-04 §3). Il n'y a donc **rien à divulguer** côté contenu personnel du client dans la piste d'audit.

**Réponse type :** confirmer le traitement (audit de conformité, finalité, base RGP-01), fournir la description des catégories de données et destinataires (registre Art. 30 / RGP-01), **router la demande d'accès au contenu vers le système de référence** (SharePoint / ARTUS) qui détient le dossier. Aucune sur-divulgation au-delà des champs réellement détenus (T-05-19).

## 6. Droit de rectification — Art. 16

AC360 **n'écrit jamais** dans les données client (read-only / lecture seule). Une rectification de contenu (information erronée dans un dossier) **ne peut pas** et **ne doit pas** être faite dans AC360. La demande est **routée vers le système de référence** (SharePoint / ARTUS), seul habilité à corriger la source. Côté AC360, les copies de travail éventuellement présentes seront de toute façon effacées par le TTL (RGP-03) et régénérées à partir de la source corrigée au prochain audit.

## 7. Droit à l'effacement — Art. 17 (effacement par conception)

C'est ici que l'architecture **read-only + éphémère** sert directement la conformité :

1. **Copies de travail (job/OCR/FIC)** — **effacement par conception via le TTL de 30 jours (RGP-03).** Aucune copie AC360 ne persiste au-delà de la fenêtre. Deux points d'application (RGP-03 §3) :
   - cycle de vie Azure Storage `managementPolicies` (`infra/main.bicep`, suppression à `jobRetentionDays` = 30) ;
   - timer Functions `prune_job_artifacts` (FS local `JOBS_BASE_DIR`, suppression âgée à `JOB_RETENTION_DAYS` = 30).
   **Divulgation honnête :** la fenêtre d'effacement **effective est ~37 jours** (30 j de suppression logique + ~7 j de récupérabilité soft-delete/PITR, RGP-03 §4). Ce délai DOIT être communiqué tel quel à la personne concernée.
2. **Piste d'audit (Log Analytics)** — si l'effacement d'un événement d'audit est exigé et juridiquement fondé, l'opérateur utilise le **chemin de purge Log Analytics** (purge API Azure Monitor) comme mécanisme d'effacement délibéré. Rappel : la piste ne contient **pas** de PII brute (hash + doc-id + ts + verdict), ce qui limite fortement la portée de toute demande d'effacement la concernant.
3. **Source (dossier client)** — l'effacement du dossier lui-même relève du **système de référence** (SharePoint / ARTUS) ; la demande y est routée. AC360 n'en détient pas de copie au-delà du TTL.

**Effacement par conception (résumé) :** parce qu'AC360 est en **lecture seule** et que ses artefacts sont **éphémères (TTL 30 j, RGP-03)**, le droit à l'effacement est largement satisfait **automatiquement** ; l'action manuelle ne concerne, le cas échéant, que la purge ciblée de la piste d'audit hachée.

### Droit d'opposition — Art. 21

L'opposition au traitement par AC360 est traitée par le **blocage au niveau fonctionnel** (feature flags : blocage `audit` par utilisateur / équipe / global, `scripts/feature_flags.py`) après qualification par le DPO. AC360 étant read-only et sans décision automatisée à effet juridique (cf. DPIA RGP-02), l'opposition se traduit par la cessation d'usage de l'outil pour le périmètre concerné, la source restant gérée par le système de référence.

## 8. Registre des demandes (request log)

Chaque demande est consignée dans un **registre des demandes de droits** tenu par le DPO :

| Champ | Description |
|-------|-------------|
| Réf. demande | Identifiant interne unique |
| Date de réception | Démarre le délai Art. 12 |
| Type de droit | Accès / rectification / effacement / opposition |
| Identité vérifiée | Oui/Non + méthode (Art. 12(6)) |
| Routage | AC360 / système de référence (SharePoint·ARTUS) |
| Action effectuée | Ex. : confirmation TTL, purge audit, routage source |
| Prorogation | Oui/Non + motif (Art. 12(3)) |
| Date de réponse | Clôture |

Le registre constitue la preuve d'accountability (Art. 5(2)) pour l'audit RGPD.

## 9. Vérification et références croisées

- **RGP-03** — politique de rétention (TTL 30 j, fenêtre effective ~37 j) : socle du droit à l'effacement (§7).
- **RGP-04** — PII-in-logs : confirme l'absence de PII brute dans la piste d'audit (§5, §7.2).
- **RGP-01** — registre Art. 30 : catégories de données / destinataires / délais d'effacement (réponse d'accès §5).
- **RGP-02** — DPIA : risque « exercice des droits » et mesures ; sign-off DPO finalise le responsable de traitement.
- **RGP-06** — résidence EU des données (transferts hors UE : néant).
