import os
import json
import shutil
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")


def send_teams_alert(report_data):
    """
    Envoie une notification sur un canal Microsoft Teams via Webhook.
    """
    if not TEAMS_WEBHOOK_URL:
        print("[WARNING] Aucun TEAMS_WEBHOOK_URL configuré. Impossible d'envoyer l'alerte Teams.")
        return

    # Préparation des faits (détails des écarts)
    facts = []
    for ecart in report_data.get("details_ecarts", []):
        if ecart.get("ecart_detecte"):
            facts.append({
                "name": ecart.get("champ"),
                "value": f"Document: {ecart.get('valeur_document')} | Fabric: {ecart.get('valeur_gestion_artus')}"
            })

    # Si aucun écart explicite, on vérifie quand même si l'audit global a
    # échoué (ex: client non trouvé).
    if not facts and report_data.get("score_correspondance_nom", 0) < 85:
        facts.append({
            "name": "Correspondance Client",
            "value": "Échec d'identification du client dans Fabric (< 85%)"
        })

    # Message adaptatif (MessageCard simple) pour Teams
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "E81123",
        "summary": "ALERTE : Écarts détectés lors de l'Audit Documentaire AC360",
        "sections": [{
            "activityTitle": "🚨 ALERTE : Écarts détectés lors de l'Audit",
            "activitySubtitle": f"Client détecté : {report_data.get('client_document', 'Inconnu')}",
            "facts": facts,
            "markdown": True
        }]
    }

    try:
        response = requests.post(TEAMS_WEBHOOK_URL, json=payload,
                                 headers={"Content-Type": "application/json"}, timeout=15)
        response.raise_for_status()
        print("[SUCCÈS] Alerte Teams envoyée avec succès.")
    except Exception as e:
        print(f"[ERREUR] Échec de l'envoi de l'alerte Teams : {e}")


def archive_and_cleanup(source_file, target_folder="Archives_Documentaires/Erreurs_Audit"):
    """
    Déplace le fichier analysé vers une zone d'archive, pour qu'un humain puisse l'auditer,
    puis s'assure qu'il est supprimé de son emplacement temporaire d'origine.
    """
    if not os.path.exists(source_file):
        print(f"[WARNING] Le fichier source {source_file} n'existe plus.")
        return

    try:
        from config import load_config
        JOBS_BASE_DIR = load_config().jobs_base_dir
    except Exception:
        JOBS_BASE_DIR = os.path.abspath("jobs")

    resolved_source = os.path.abspath(source_file)
    base_resolved = os.path.abspath(JOBS_BASE_DIR)

    try:
        common = os.path.commonpath([resolved_source, base_resolved])
        if common != base_resolved:
            print(f"[ERREUR SÉCURITÉ] Tentative de Path Traversal : suppression interdite hors de {base_resolved}")
            return
    except ValueError:
        print("[ERREUR SÉCURITÉ] Tentative de Path Traversal : chemins incompatibles")
        return

    # Création du dossier d'archivage s'il n'existe pas localement
    # (Dans un contexte complet, on pourrait uploader sur SharePoint via Graph API ou PnP)
    os.makedirs(target_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.basename(source_file)
    archive_path = os.path.join(target_folder, f"ARCHIVE_{timestamp}_{file_name}")

    try:
        # Copie vers l'archive sécurisée
        shutil.copy2(source_file, archive_path)
        print(f"[ARCHIVAGE] Fichier copié dans l'archive sécurisée : {archive_path}")

        # Nettoyage sécurisé du fichier source temporaire
        os.remove(source_file)
        print(f"[NETTOYAGE] Fichier temporaire original supprimé : {source_file}")

    except Exception as e:
        print(f"[ERREUR] Problème lors de l'archivage ou de la suppression : {e}")


def main():
    parser = argparse.ArgumentParser(description="Workflow de clôture de l'Audit AC360 (Alertes & Nettoyage).")
    parser.add_argument("report_json", help="Chemin vers le fichier audit_report.json (Phase 4).")
    parser.add_argument("source_file", help="Chemin du document PDF d'origine ayant généré le rapport.")
    parser.add_argument("--fic-file", help="Chemin du document brouillon FIC (.docx) généré.", default=None)
    args = parser.parse_args()

    if not os.path.exists(args.report_json):
        print(f"[ERREUR] Fichier de rapport d'audit introuvable : {args.report_json}")
        exit(1)

    print("--- DÉMARRAGE DU POST-AUDIT ---")

    # Lecture du rapport d'audit
    with open(args.report_json, 'r', encoding='utf-8') as f:
        report_data = json.load(f)

    # 1. Vérification des écarts et Alertes Teams
    has_ecart = False
    for ecart in report_data.get("details_ecarts", []):
        if ecart.get("ecart_detecte"):
            has_ecart = True
            break

    # Si le client n'a pas été trouvé, c'est aussi un écart grave
    if report_data.get("score_correspondance_nom", 0) < 85:
        has_ecart = True

    if has_ecart:
        print("Écart(s) détecté(s) ! Préparation de l'alerte Teams...")
        send_teams_alert(report_data)

        # 2. Archivage humain
        print("Déplacement du document litigieux vers l'Archive pour inspection humaine...")
        archive_and_cleanup(args.source_file, target_folder="Archives_Documentaires/Erreurs_Audit")
    else:
        print("Aucun écart critique détecté. Le document est conforme.")
        # Nettoyage classique (poubelle) sans archivage d'erreur
        print("Suppression du document temporaire conforme...")
        if os.path.exists(args.source_file):
            os.remove(args.source_file)

    # 3. Nettoyage de la FIC (RGPD Anti-Leak)
    if args.fic_file and os.path.exists(args.fic_file):
        print(f"Nettoyage RGPD : Suppression du brouillon local {args.fic_file}")
        try:
            os.remove(args.fic_file)
            print("[SÉCURITÉ] FIC locale supprimée (Anti-Data Leak).")
        except Exception as e:
            print(f"[ERREUR SÉCURITÉ] Impossible de supprimer la FIC : {e}")

    print("--- PROCESSUS D'AUDIT COMPLET TERMINÉ ---")


if __name__ == "__main__":
    main()
