import os
import json
import argparse
import pandas as pd
from thefuzz import fuzz
from dotenv import load_dotenv

# Optional dependencies for Fabric/SQL
try:
    import pyodbc
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("Erreur : pyodbc ou azure-identity manquant. Exécutez 'pip install -r requirements.txt'.")
    exit(1)

load_dotenv()

FABRIC_SQL_ENDPOINT = os.getenv("FABRIC_SQL_ENDPOINT")
FABRIC_DATABASE = os.getenv("FABRIC_DATABASE")

def get_fabric_connection():
    """
    Établit une connexion avec le point de terminaison SQL de Microsoft Fabric
    en utilisant l'authentification Entra ID (Azure AD).
    """
    if not FABRIC_SQL_ENDPOINT or not FABRIC_DATABASE:
        print("[AVERTISSEMENT] Variables FABRIC_SQL_ENDPOINT ou FABRIC_DATABASE manquantes.")
        print("[AVERTISSEMENT] Basculement sur les données de gestion simulées (Fallback).")
        return None

    try:
        credential = DefaultAzureCredential()
        # Scope pour Azure SQL / Fabric
        token = credential.get_token("https://database.windows.net/.default")
        
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={FABRIC_SQL_ENDPOINT},1433;"
            f"Database={FABRIC_DATABASE};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )
        
        # On passe le token d'accès dans les attributs de la connexion ODBC
        # Note: L'attribut 1256 est pour SQL_COPT_SS_ACCESS_TOKEN
        token_bytes = token.token.encode('utf-16-le')
        token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        
        conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
        return conn
    except Exception as e:
        print(f"Erreur de connexion à Fabric : {e}")
        print("Basculement sur les données de gestion simulées (Fallback).")
        return None

def fetch_artus_data(client_name=None):
    """
    Récupère les données de gestion (Artus) stockées dans Fabric.
    """
    conn = get_fabric_connection()
    if conn:
        # Vraie requête sur Fabric avec Prepared Statements (Anti-SQL Injection)
        query = "SELECT client_id, nom_client, plafond_hospitalisation, date_effet FROM Artus_Contrats"
        if client_name:
            query += " WHERE nom_client LIKE ?"
            # Utilisation de pyodbc avec paramètre (le % est ajouté autour de la variable)
            df = pd.read_sql(query, conn, params=[f"%{client_name}%"])
        else:
            df = pd.read_sql(query, conn)
        conn.close()
        return df
    else:
        # FAIL-FAST: On refuse de comparer avec des données factices en production
        raise ConnectionError("[ERREUR CRITIQUE] Impossible de se connecter à la base de données Fabric. L'audit a été interrompu pour des raisons de conformité (Pas de Fallback sur données factices).")

def match_client_name(doc_name, fabric_df):
    """
    Rapproche le nom du client extrait du document avec les noms de la base Fabric.
    Utilise thefuzz pour le fuzzy matching, avec un système de pénalités (Enterprise-grade)
    pour éviter les faux positifs (ex: "GEREP SA" vs "GEREP SAS").
    """
    if fabric_df.empty:
        return None, 0

    best_match = None
    best_score = 0
    
    # Mots de rejet (entités différentes)
    rejet_words = ["banque", "holding", "international", "france", "groupe"]

    for index, row in fabric_df.iterrows():
        fabric_name = str(row['nom_client'])
        
        # Score de base
        score = fuzz.token_sort_ratio(doc_name.lower(), fabric_name.lower())
        
        # Pénalité stricte (Enterprise Grade)
        for word in rejet_words:
            if (word in doc_name.lower()) != (word in fabric_name.lower()):
                score -= 20 # Pénalité très lourde
                
        # Pénalité de longueur
        len_diff = abs(len(doc_name) - len(fabric_name))
        if len_diff > 10:
            score -= 10
            
        if score > best_score:
            best_score = score
            best_match = row

    # Le seuil d'exigence passe de 75% à 85% (Plus strict)
    if best_score >= 85:
        print(f"[MATCHING] Client identifié de manière sécurisée : '{doc_name}' => '{best_match['nom_client']}' (Score: {best_score}%)")
        return best_match, best_score
    else:
        print(f"[ATTENTION] Aucun match suffisamment sûr trouvé pour '{doc_name}' (Meilleur score: {best_score}%)")
        return None, best_score

def perform_audit(ocr_data, artus_df):
    """
    Compare les données OCR du document avec les données de gestion Artus.
    """
    audit_results = []
    
    # 1. Extraction du nom client depuis le document
    doc_client_name = ""
    if "nom_client" in ocr_data.get("fields", {}):
        doc_client_name = ocr_data["fields"]["nom_client"]["value"]
    
    print(f"-> Nom client détecté sur le document : {doc_client_name}")
    
    # 2. Règle d'audit : Fuzzy Matching sur le nom du client
    best_match_row, best_match_score = match_client_name(doc_client_name, artus_df)

    if best_match_row is not None:
        # 3. Comparaison des champs clés (ex: Plafond Hospitalisation)
        doc_plafond = None
        # Parsing dynamique de la structure JSON OCR (Document Intelligence)
        for table in ocr_data.get("tables", []):
            cells = table.get("cells", [])
            for i, cell in enumerate(cells):
                content = str(cell.get("content", "")).lower().strip()
                if "hospitalisation" in content or "chambre" in content:
                    # On suppose que la valeur est dans la colonne voisine (cellule suivante)
                    if i + 1 < len(cells):
                        next_cell_content = str(cells[i + 1].get("content", "")).strip()
                        if next_cell_content:
                            doc_plafond = next_cell_content
                            break
            if doc_plafond:
                break
        
        # Fallback sur les key-value pairs si non trouvé dans un tableau
        if not doc_plafond:
            for kv in ocr_data.get("keyValuePairs", []):
                key = str(kv.get("key", {}).get("content", "")).lower()
                if "hospitalisation" in key:
                    doc_plafond = str(kv.get("value", {}).get("content", "")).strip()
                    break
        
        if doc_plafond:
            artus_plafond = best_match_row['plafond_hospitalisation']
            ecart = doc_plafond != artus_plafond
            
            audit_results.append({
                "champ": "Plafond Hospitalisation",
                "valeur_document": doc_plafond,
                "valeur_gestion_artus": artus_plafond,
                "ecart_detecte": ecart,
                "commentaire": "Écart critique !" if ecart else "Conforme"
            })
            
    else:
        print(f"-> ÉCHEC DE CORRESPONDANCE : Aucun client Fabric ne correspond à {doc_client_name} (Meilleur score: {best_match_score}%)")
        audit_results.append({
            "champ": "nom_client",
            "valeur_document": doc_client_name,
            "valeur_gestion_artus": "NON TROUVÉ",
            "ecart_detecte": True,
            "commentaire": "Fuzzy matching < 75%"
        })

    return {
        "client_document": doc_client_name,
        "meilleur_match_fabric": best_match_row['nom_client'] if best_match_row is not None else None,
        "score_correspondance_nom": best_match_score,
        "motif_operation": "modification de garantie", # Valeur simulée pour illustrer les règles d'Adel
        "details_ecarts": audit_results
    }

def main():
    parser = argparse.ArgumentParser(description="Moteur d'audit comparant les données OCR avec Microsoft Fabric (Artus).")
    parser.add_argument("ocr_file", help="Chemin du fichier JSON généré par l'OCR (Phase 3).")
    parser.add_argument("--out-json", help="Chemin d'export du rapport JSON.", default="audit_report.json")
    parser.add_argument("--out-csv", help="Chemin d'export du rapport CSV.", default="audit_report.csv")
    args = parser.parse_args()

    if not os.path.exists(args.ocr_file):
        print(f"Erreur : Le fichier OCR '{args.ocr_file}' est introuvable.")
        exit(1)

    print(f"--- DÉMARRAGE DE L'AUDIT ---")
    with open(args.ocr_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    # 1. Connexion à Fabric et récupération des données métier
    print("Récupération des données métier depuis Microsoft Fabric...")
    artus_df = fetch_artus_data()
    
    # 2. Exécution des règles d'audit (Fuzzy matching + Comparaison)
    print("Exécution des règles de comparaison (Fuzzy Matching)...")
    rapport = perform_audit(ocr_data, artus_df)

    # 3. Sauvegarde des rapports
    with open(args.out_json, 'w', encoding='utf-8') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=4)
    
    # Export CSV
    if rapport["details_ecarts"]:
        df_export = pd.DataFrame(rapport["details_ecarts"])
        df_export.to_csv(args.out_csv, index=False, encoding='utf-8-sig')
    else:
        # Fichier vide avec en-têtes
        pd.DataFrame(columns=["champ", "valeur_document", "valeur_gestion_artus", "ecart_detecte", "commentaire"]).to_csv(args.out_csv, index=False)
        
    print(f"--- AUDIT TERMINÉ ---")
    print(f"Rapports générés : {args.out_json} et {args.out_csv}")

if __name__ == "__main__":
    main()
