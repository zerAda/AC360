"""
Application d'Audit PDF/Excel - Core Module
Phases 2-4: Nettoyage, Optimisation, Calcul des Écarts

Décisions validées:
- Langue: Français
- Seuil fuzzy: 75%
- Source de vérité: PDF
- Écart = Excel - PDF
"""

import re
import unicodedata
from difflib import SequenceMatcher


# ============================================================
# PHASE 2: NETTOYAGE DE DONNÉES
# ============================================================

class Normalizer:
    """Normalise les noms de société pour la comparaison."""
    
    PREFIXES = ['Sté ', 'SOCIÉTÉ ', 'SOCIETE ', 'STÉ ', 'STE ', 'Société ']
    SUFFIXES = [' SAS', ' SNC', ' SA', ' SARL', ' SASU', ' SC', ' EURL']
    
    @staticmethod
    def normalize(nom):
        if not nom:
            return ""
        nom = str(nom).strip()
        for prefix in Normalizer.PREFIXES:
            if nom.startswith(prefix):
                nom = nom[len(prefix):]
        for suffix in Normalizer.SUFFIXES:
            if nom.endswith(suffix):
                nom = nom[:-len(suffix)]
        nom = unicodedata.normalize('NFKD', nom).encode('ASCII', 'ignore').decode('ASCII')
        nom = nom.upper().strip()
        nom = re.sub(r'\s+', ' ', nom)
        return nom


class PDFParser:
    """Parse les bordereaux de virements PDF."""
    
    # Phase 6: Pattern pour détecter les montants (ex: 1 234,56 ou 1234,56)
    MONTANT_PATTERN = re.compile(r'([\d\s]+[,\.]\d{2})')
    
    @staticmethod
    def parse_file(file_path):
        """Phase 6: Extraction robuste avec pdfplumber.
        
        Parse un fichier PDF bancaire et extrait les virements avec
        IBAN, nom et montant déjà associés.
        """
        try:
            import pdfplumber
        except ImportError:
            raise Exception(
                "pdfplumber requis. Installez: pip install pdfplumber"
            )
        
        resultats = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                lignes = text.split('\n')
                for i, ligne in enumerate(lignes):
                    ligne = ligne.strip()
                    if not ligne:
                        continue
                    
                    # Filtres: exclure totaux, headers, etc.
                    if ligne.startswith('Total') or ligne.startswith('Bordereau N°'):
                        continue
                    if ligne.startswith('Réf. Vir.') or ('Type d' in ligne and 'opération' in ligne):
                        continue
                    
                    # Détecter IBAN (commence par FR + 25 caractères)
                    if not ligne.startswith('FR') or len(ligne) < 30:
                        continue
                    
                    iban = ligne[0:27].strip()
                    if not re.match(r'^FR\d{2}\s', iban):
                        continue
                    
                    # Extraire le nom (reste après IBAN)
                    reste = ligne[28:].strip()
                    
                    # Chercher le montant sur cette ligne
                    montant = PDFParser._extract_montant_from_line(reste)
                    
                    # Si pas trouvé, chercher sur la ligne suivante
                    if montant is None and i + 1 < len(lignes):
                        montant = PDFParser._extract_montant_from_line(lignes[i + 1])
                    
                    # Nettoyer le nom (enlever le montant s'il est dans la même ligne)
                    nom = PDFParser._clean_nom(reste)
                    
                    resultats.append({
                        'iban': iban,
                        'nom': nom,
                        'nom_normalise': Normalizer.normalize(nom),
                        'montant': montant if montant is not None else 0.0,
                        'source': 'PDF',
                        'page': page_num
                    })
        
        return resultats
    
    @staticmethod
    def _extract_montant_from_line(line):
        """Extrait un montant d'une ligne de texte.
        
        Formats supportés: 1 234,56 | 1234,56 | 1 234.56 | 1234.56
        """
        if not line:
            return None
        
        # Chercher un pattern de montant
        match = PDFParser.MONTANT_PATTERN.search(line)
        if not match:
            return None
        
        montant_str = match.group(1)
        
        # Normaliser: enlever les espaces, remplacer virgule par point
        montant_str = montant_str.replace(' ', '').replace(',', '.')
        
        try:
            return float(montant_str)
        except ValueError:
            return None
    
    @staticmethod
    def _clean_nom(reste):
        """Nettoie le nom en enlevant le montant s'il est dans la même ligne."""
        if not reste:
            return ""
        # Enlever le montant trouvé par le pattern
        nom = PDFParser.MONTANT_PATTERN.sub('', reste).strip()
        # Nettoyer les séparateurs restants
        nom = re.sub(r'[\s\-–—]+$', '', nom).strip()
        return nom
    
    @staticmethod
    def parse_content(text_content):
        """DEPRECATED — Utilisez parse_file() avec pdfplumber.
        
        Gardé pour compatibilité avec les tests existants.
        """
        lignes = text_content.split('\n')
        resultats = []
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne:
                continue
            if ligne.startswith('Total') or ligne.startswith('Bordereau N°'):
                continue
            if ligne.startswith('Réf. Vir.') or 'Type d' in ligne and 'opération' in ligne:
                continue
            if not ligne.startswith('FR') or len(ligne) < 30:
                continue
            iban = ligne[0:27].strip()
            nom = ligne[28:].strip()
            if not re.match(r'^FR\d{2}\s', iban):
                continue
            resultats.append({
                'iban': iban,
                'nom': nom,
                'nom_normalise': Normalizer.normalize(nom),
                'montant': 0.0,
                'source': 'PDF'
            })
        return resultats
    
    @staticmethod
    def extract_amounts(text_content):
        """DEPRECATED — Les montants sont maintenant extraits avec parse_file()."""
        lignes = text_content.split('\n')
        montants = []
        for ligne in lignes:
            ligne = ligne.strip().replace(',', '.').replace(' ', '')
            if re.match(r'^\d+\.\d{2}$', ligne):
                try:
                    montants.append(float(ligne))
                except:
                    pass
        return montants


class ExcelParser:
    """Parse les fichiers Excel."""
    
    # Phase 10: Mots-clés pour la détection automatique des colonnes
    SOCIETE_KEYWORDS = ['societe', 'société', 'company', 'nom', 'name', 'client', 'raison sociale']
    MONTANT_KEYWORDS = ['montant', 'amount', 'prix', 'price', 'total', 'verse', 'reglement', 'règlement']
    
    @staticmethod
    def detect_columns(df):
        """Phase 10: Détecte automatiquement les colonnes Société et Montant."""
        import pandas as pd
        societe_col = None
        montant_col = None
        
        # Normaliser les noms de colonnes
        cols_lower = {str(c).lower().strip(): c for c in df.columns}
        
        # Chercher par mots-clés
        for keyword in ExcelParser.SOCIETE_KEYWORDS:
            for lower_col, original_col in cols_lower.items():
                if keyword in lower_col and societe_col is None:
                    societe_col = original_col
                    break
            if societe_col:
                break
        
        for keyword in ExcelParser.MONTANT_KEYWORDS:
            for lower_col, original_col in cols_lower.items():
                if keyword in lower_col and montant_col is None:
                    montant_col = original_col
                    break
            if montant_col:
                break
        
        # Fallback: première colonne texte pour société, première numérique pour montant
        if societe_col is None:
            for c in df.columns:
                if df[c].dtype == 'object' and df[c].notna().any():
                    sample = str(df[c].dropna().iloc[0])
                    if len(sample) > 2 and not sample.replace(' ', '').isdigit():
                        societe_col = c
                        break
        
        if montant_col is None:
            for c in df.columns:
                try:
                    pd.to_numeric(df[c].astype(str).str.replace('€', '').str.replace(' ', '').str.replace(',', '.'), errors='coerce')
                    if df[c].notna().any():
                        montant_col = c
                        break
                except:
                    continue
        
        return societe_col, montant_col
    
    @staticmethod
    def parse(file_path):
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            
            # Phase 10: Détection automatique des colonnes
            societe_col, montant_col = ExcelParser.detect_columns(df)
            
            if societe_col:
                df['societe'] = df[societe_col]
            elif 'Société' in df.columns:
                df['societe'] = df['Société']
            
            if montant_col:
                df['montant'] = df[montant_col]
            elif 'Montant' in df.columns:
                df['montant'] = df['Montant']
            
            if 'montant' in df.columns:
                df['montant'] = df['montant'].astype(str).str.replace('€', '').str.replace(' ', '').str.replace(',', '.')
                df['montant'] = pd.to_numeric(df['montant'], errors='coerce')
            
            if 'societe' in df.columns:
                df['nom_normalise'] = df['societe'].apply(Normalizer.normalize)
            
            return df
        except ImportError:
            raise Exception("pandas requis. Installez: pip install pandas openpyxl")


class Filters:
    """Filtres pour les données."""
    
    @staticmethod
    def filter_pdf(data):
        return [item for item in data 
                if item.get('nom') 
                and not item.get('nom', '').startswith('Total')]
    
    @staticmethod
    def filter_excel(df):
        df = df[df['societe'].notna()]
        # FIX FILT-01: Exclure bordereau + récap/sommes (avec normalisation pour accents)
        df['__norm__'] = df['societe'].apply(Normalizer.normalize)
        df = df[~df['__norm__'].str.contains('BORDEREAU', na=False)]
        df = df[~df['__norm__'].str.contains('TOTAL|SOMME|RECAP|RECEIPT', na=False)]
        df = df[df['montant'] != 0]
        df = df[~df['societe'].str.contains('^0,00', na=False)]
        df = df.drop(columns=['__norm__'])
        return df


# ============================================================
# PHASE 2 (suite): CORRESPONDANCE FUZZY
# ============================================================

class FuzzyMatcher:
    SEUIL = 0.75
    
    @staticmethod
    def match(nom_pdf, nom_excel, seuil=None):
        if seuil is None:
            seuil = FuzzyMatcher.SEUIL
        pdf_norm = Normalizer.normalize(nom_pdf)
        excel_norm = Normalizer.normalize(nom_excel)
        if not pdf_norm or not excel_norm:
            return False, 0.0
        ratio = SequenceMatcher(None, pdf_norm, excel_norm).ratio()
        return ratio >= seuil, ratio


# ============================================================
# PHASE 3: OPTIMISATION O(n)
# ============================================================

class OptimizedMatcher:
    @staticmethod
    def match_with_index(pdf_data, excel_data):
        excel_index = {}
        for item in excel_data:
            nom_norm = item.get('nom_normalise', '')
            if nom_norm:
                excel_index[nom_norm] = item
        
        correspondances = []
        sans_correspondance = []
        
        for pdf_item in pdf_data:
            nom_pdf_norm = pdf_item.get('nom_normalise', '')
            if nom_pdf_norm in excel_index:
                correspondances.append({
                    'pdf': pdf_item,
                    'excel': excel_index[nom_pdf_norm],
                    'nom': pdf_item.get('nom', ''),
                    'fuzzy': False,
                    'ratio': 1.0
                })
            else:
                meilleur_match, ratio = None, 0.0
                for excel_item in excel_data:
                    nom_excel = excel_item.get('societe', '')
                    match, r = FuzzyMatcher.match(pdf_item.get('nom', ''), nom_excel)
                    if match and r > ratio:
                        ratio = r
                        meilleur_match = excel_item
                if meilleur_match:
                    correspondances.append({
                        'pdf': pdf_item,
                        'excel': meilleur_match,
                        'nom': pdf_item.get('nom', ''),
                        'fuzzy': True,
                        'ratio': ratio
                    })
                else:
                    sans_correspondance.append(pdf_item)
        
        return correspondances, sans_correspondance


# ============================================================
# PHASE 4: CALCUL DES ÉCARTS
# ============================================================

class ResultExporter:
    """Phase 7: Exporte les résultats d'audit vers Excel, CSV ou PDF."""
    
    @staticmethod
    def export_excel(resultats, stats, file_path):
        import pandas as pd
        df = pd.DataFrame(resultats)
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Résultats', index=False)
            stats_df = pd.DataFrame([stats])
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
    
    @staticmethod
    def export_csv(resultats, file_path):
        import pandas as pd
        df = pd.DataFrame(resultats)
        df.to_csv(file_path, index=False, sep=';', encoding='utf-8-sig')
    
    @staticmethod
    def export_pdf(resultats, stats, file_path):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Rapport d'Audit PDF/Excel", ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"Societes: {stats['total_societes']} | OK: {stats['societes_ok']} | Ecarts: {stats['societes_ecart']} | Total ecart: {stats['total_ecart']:.2f} EUR", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        headers = ['Societe', 'IBAN', 'Montant PDF', 'Montant Excel', 'Ecart', 'Statut']
        col_widths = [50, 45, 30, 30, 25, 25]
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 8, h, border=1)
        pdf.ln()
        
        pdf.set_font("Arial", "", 9)
        for r in resultats:
            pdf.cell(col_widths[0], 7, r['societe'][:25], border=1)
            pdf.cell(col_widths[1], 7, r['iban'][:20], border=1)
            pdf.cell(col_widths[2], 7, f"{r['montant_pdf']:.2f}", border=1)
            pdf.cell(col_widths[3], 7, f"{r['montant_excel']:.2f}", border=1)
            pdf.cell(col_widths[4], 7, f"{r['ecart']:.2f}", border=1)
            pdf.cell(col_widths[5], 7, r['statut'], border=1)
            pdf.ln()
        
        pdf.output(file_path)


class AuditHistory:
    """Phase 8: Gère l'historique des audits dans une base SQLite."""
    
    def __init__(self, db_path="audits.db"):
        import sqlite3
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    pdf_name TEXT,
                    excel_name TEXT,
                    total_societes INTEGER,
                    societes_ok INTEGER,
                    societes_ecart INTEGER,
                    total_ecart REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_id INTEGER NOT NULL,
                    societe TEXT,
                    iban TEXT,
                    montant_pdf REAL,
                    montant_excel REAL,
                    ecart REAL,
                    statut TEXT,
                    FOREIGN KEY (audit_id) REFERENCES audits(id)
                )
            """)
            conn.commit()
    
    def save_audit(self, pdf_name, excel_name, stats, resultats):
        import sqlite3
        from datetime import datetime
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO audits (date, pdf_name, excel_name, total_societes, societes_ok, societes_ecart, total_ecart)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), pdf_name, excel_name,
                 stats.get('total_societes', 0), stats.get('societes_ok', 0),
                 stats.get('societes_ecart', 0), stats.get('total_ecart', 0.0))
            )
            audit_id = cursor.lastrowid
            for r in resultats:
                conn.execute(
                    """INSERT INTO results (audit_id, societe, iban, montant_pdf, montant_excel, ecart, statut)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (audit_id, r.get('societe', ''), r.get('iban', ''),
                     r.get('montant_pdf', 0.0), r.get('montant_excel', 0.0),
                     r.get('ecart', 0.0), r.get('statut', ''))
                )
            conn.commit()
            return audit_id
    
    def get_audits(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM audits ORDER BY date DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_audit_results(self, audit_id):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM results WHERE audit_id = ? ORDER BY id",
                (audit_id,)
            )
            return [dict(row) for row in cursor.fetchall()]


class EcartCalculator:
    @staticmethod
    def calculer_ecarts(correspondances):
        resultats = []
        total_ecart = 0.0
        total_pdf = 0.0
        total_excel = 0.0
        
        for match in correspondances:
            pdf = match['pdf']
            excel = match['excel']
            m_pdf = float(pdf.get('montant', 0) or 0)
            m_excel = float(excel.get('montant', 0) or 0)
            total_pdf += m_pdf
            total_excel += m_excel
            ecart = m_excel - m_pdf
            total_ecart += ecart
            
            if ecart > 0:
                statut, desc = "Excès Excel", f"+{ecart:.2f} €"
            elif ecart < 0:
                statut, desc = "Manque Excel", f"{ecart:.2f} €"
            else:
                statut, desc = "OK", "Parfait"
            
            resultats.append({
                'societe': match.get('nom', ''),
                'iban': pdf.get('iban', ''),
                'montant_pdf': m_pdf,
                'montant_excel': m_excel,
                'ecart': ecart,
                'statut': statut,
                'fuzzy': match.get('fuzzy', False),
                'ratio': match.get('ratio', 1.0)
            })
        
        # FIX CALC-05: Vérifier cohérence du total
        expected_total = total_excel - total_pdf
        if abs(total_ecart - expected_total) > 0.01:
            print(f"AVERTISSEMENT: Incohérence totale - Calculé: {total_ecart:.2f}, Attendu: {expected_total:.2f}")
        
        return resultats, total_ecart
    
    @staticmethod
    def calculer_statistiques(resultats):
        total = len(resultats)
        ok = sum(1 for r in resultats if r['statut'] == 'OK')
        ecarts = sum(1 for r in resultats if r['ecart'] != 0)
        total_ecart = sum(r['ecart'] for r in resultats)
        ecart_positifs = [r['ecart'] for r in resultats if r['ecart'] > 0]
        ecart_negatifs = [r['ecart'] for r in resultats if r['ecart'] < 0]
        
        return {
            'total_societes': total,
            'societes_ok': ok,
            'societes_ecart': ecarts,
            'total_ecart': total_ecart,
            'ecart_moyen': total_ecart / ecarts if ecarts > 0 else 0,
            'ecart_max': max(ecart_positifs) if ecart_positifs else 0,
            'ecart_min': min(ecart_negatifs) if ecart_negatifs else 0,
        }
