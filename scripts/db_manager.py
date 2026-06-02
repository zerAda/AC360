import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__line__ if '__line__' in locals() else __file__)), '..', 'database', 'ac360_tracking.db')

def init_db():
    """Initialise la base de données SQLite et crée les tables si elles n'existent pas."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fic_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            client_name TEXT NOT NULL,
            motif_operation TEXT,
            is_eligible BOOLEAN,
            status_text TEXT,
            user_principal_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            document_id TEXT,
            action TEXT,
            status TEXT,
            details TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def log_fic_generation(client_name, motif_operation, is_eligible, status_text, upn="system"):
    """Insère un log de génération FIC de manière transactionnelle."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO fic_tracking (client_name, motif_operation, is_eligible, status_text, user_principal_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (client_name, motif_operation, is_eligible, status_text, upn))
    
    conn.commit()
    conn.close()
    print(f"[DB] Tracé en base de données : FIC pour {client_name} (Éligible: {is_eligible})")

def log_audit_action(document_id, action, status, details=""):
    """Enregistre un événement d'audit système."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audit_logs (document_id, action, status, details)
        VALUES (?, ?, ?, ?)
    ''', (document_id, action, status, details))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de données initialisée avec succès.")
