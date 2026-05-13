"""
Application d'Audit PDF/Excel - Interface Utilisateur
Phase 1: UI/UX et Contrôle Audit + Phase 5: Post-Audit
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import glob

from core import (
    PDFParser, ExcelParser, Filters, 
    OptimizedMatcher, EcartCalculator, Normalizer, ResultExporter, AuditHistory
)


class AuditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Application d'Audit PDF/Excel")
        self.root.geometry("1200x800")
        
        self.pdf_path = tk.StringVar()
        self.excel_path = tk.StringVar()
        self.should_cancel = False
        self.audit_thread = None
        
        # Phase 7: Stocker les résultats pour l'export
        self.last_resultats = []
        self.last_stats = {}
        
        # Phase 8: Historique des audits
        self.history = AuditHistory()
        
        self.build_ui()
    
    def build_ui(self):
        main = ttk.Frame(self.root, padding="20")
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(10, weight=1)
        
        # Fichiers
        ttk.Label(main, text="Fichiers", font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        ttk.Label(main, text="PDF:").grid(row=1, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.pdf_path, width=60).grid(
            row=1, column=1, sticky="ew", padx=5)
        ttk.Button(main, text="Parcourir", command=self.select_pdf).grid(row=1, column=2)
        
        ttk.Label(main, text="Excel:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(main, textvariable=self.excel_path, width=60).grid(
            row=2, column=1, sticky="ew", padx=5)
        ttk.Button(main, text="Parcourir", command=self.select_excel).grid(row=2, column=2)
        
        # Contrôles
        ctrl = ttk.Frame(main)
        ctrl.grid(row=3, column=0, columnspan=3, pady=20)
        
        self.btn_start = ttk.Button(ctrl, text="Lancer l'audit", 
                                     command=self.start_audit, width=20)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_cancel = ttk.Button(ctrl, text="Annuler", 
                                      command=self.cancel_audit, width=20, state='disabled')
        self.btn_cancel.pack(side="left", padx=5)
        
        self.btn_reset = ttk.Button(ctrl, text="Nouvel audit", 
                                     command=self.reset_all, width=20)
        self.btn_reset.pack(side="left", padx=5)
        
        # Phase 7: Boutons d'export
        self.btn_export_excel = ttk.Button(ctrl, text="Exporter Excel", 
                                            command=self.export_excel, width=20, state='disabled')
        self.btn_export_excel.pack(side="left", padx=5)
        
        self.btn_export_csv = ttk.Button(ctrl, text="Exporter CSV", 
                                          command=self.export_csv, width=20, state='disabled')
        self.btn_export_csv.pack(side="left", padx=5)
        
        self.btn_export_pdf = ttk.Button(ctrl, text="Exporter PDF", 
                                          command=self.export_pdf, width=20, state='disabled')
        self.btn_export_pdf.pack(side="left", padx=5)
        
        # Phase 8: Bouton Historique
        self.btn_history = ttk.Button(ctrl, text="Historique", 
                                       command=self.show_history, width=20)
        self.btn_history.pack(side="left", padx=5)
        
        # Phase 9: Bouton Mode Batch
        self.btn_batch = ttk.Button(ctrl, text="Mode Batch", 
                                     command=self.show_batch_window, width=20)
        self.btn_batch.pack(side="left", padx=5)
        
        # Progression
        ttk.Label(main, text="Progression:", font=('Arial', 10, 'bold')).grid(
            row=4, column=0, sticky="w", pady=(10, 0))
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main, variable=self.progress_var, 
                                             maximum=100, length=600)
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.lbl_progress = ttk.Label(main, text="0% - Prêt")
        self.lbl_progress.grid(row=6, column=0, columnspan=3, sticky="w")
        
        self.lbl_detail = ttk.Label(main, text="")
        self.lbl_detail.grid(row=7, column=0, columnspan=3, sticky="w")
        
        # Résumé
        self.frame_summary = ttk.LabelFrame(main, text="Résumé", padding="10")
        self.frame_summary.grid(row=8, column=0, columnspan=3, sticky="ew", pady=10)
        self.frame_summary.grid_remove()
        
        self.lbl_summary = ttk.Label(self.frame_summary, text="")
        self.lbl_summary.pack(anchor="w")
        
        # Tableau
        ttk.Label(main, text="Résultats:", font=('Arial', 10, 'bold')).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(10, 0))
        
        tree_frame = ttk.Frame(main)
        tree_frame.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        cols = ('societe', 'iban', 'pdf', 'excel', 'ecart', 'statut')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=15)
        
        for col in cols:
            self.tree.heading(col, text=col.upper())
        
        self.tree.column('societe', width=250)
        self.tree.column('iban', width=200)
        self.tree.column('pdf', width=100, anchor='e')
        self.tree.column('excel', width=100, anchor='e')
        self.tree.column('ecart', width=100, anchor='e')
        self.tree.column('statut', width=120)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
    
    def select_pdf(self):
        path = filedialog.askopenfilename(title="PDF", filetypes=[("PDF", "*.pdf")])
        if path:
            self.pdf_path.set(path)
    
    def select_excel(self):
        path = filedialog.askopenfilename(title="Excel", 
                                           filetypes=[("Excel", "*.xlsx *.xls")])
        if path:
            self.excel_path.set(path)
    
    def update_progress(self, value, detail=""):
        self.progress_var.set(value)
        self.lbl_progress.config(text=f"{value:.0f}%")
        if detail:
            self.lbl_detail.config(text=detail)
        self.root.update_idletasks()
    
    def start_audit(self):
        if not self.pdf_path.get() or not self.excel_path.get():
            messagebox.showwarning("Attention", "Veuillez sélectionner les deux fichiers")
            return
        
        self.should_cancel = False
        self.btn_start.config(state='disabled')
        self.btn_cancel.config(state='normal')
        self.tree.delete(*self.tree.get_children())
        self.frame_summary.grid_remove()
        
        self.audit_thread = threading.Thread(target=self.run_audit, daemon=True)
        self.audit_thread.start()
    
    def cancel_audit(self):
        self.should_cancel = True
        self.lbl_detail.config(text="Annulation demandée...")
    
    def run_audit(self):
        import time
        import gc
        debut = time.time()
        
        try:
            # FIX PERF-03: Nettoyer mémoire avant audit
            gc.collect()
            
            # Phase 6: Parsing PDF robuste avec pdfplumber
            self.update_progress(10, "Analyse du PDF...")
            
            pdf_data = PDFParser.parse_file(self.pdf_path.get())
            pdf_data = Filters.filter_pdf(pdf_data)
            
            self.update_progress(30, f"{len(pdf_data)} virements trouvés dans le PDF")
            
            if self.should_cancel:
                self.on_cancelled()
                return
            
            # Phase 2: Parsing Excel
            self.update_progress(40, "Lecture de l'Excel...")
            df_excel = ExcelParser.parse(self.excel_path.get())
            df_excel = Filters.filter_excel(df_excel)
            
            excel_data = df_excel.to_dict('records')
            
            self.update_progress(60, f"{len(excel_data)} lignes trouvées dans Excel")
            
            if self.should_cancel:
                self.on_cancelled()
                return
            
            # Phase 3: Correspondance optimisée
            self.update_progress(70, "Correspondance des sociétés...")
            correspondances, sans_corr = OptimizedMatcher.match_with_index(pdf_data, excel_data)
            
            self.update_progress(85, f"{len(correspondances)} correspondances trouvées")
            
            if self.should_cancel:
                self.on_cancelled()
                return
            
            # Phase 4: Calcul des écarts
            self.update_progress(90, "Calcul des écarts...")
            resultats, total_ecart = EcartCalculator.calculer_ecarts(correspondances)
            stats = EcartCalculator.calculer_statistiques(resultats)
            
            self.update_progress(100, "Audit terminé!")
            
            # FIX PERF-01: Benchmark performance
            duree = time.time() - debut
            print(f"[BENCHMARK] Audit terminé en {duree:.2f} secondes ({len(resultats)} sociétés)")
            if duree > 30:
                print(f"[BENCHMARK] ATTENTION: Temps > 30s ({duree:.2f}s)")
            
            # Affichage
            self.root.after(0, lambda: self.show_results(resultats, stats, duree))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erreur", str(e)))
            self.root.after(0, self.reset_ui)
    
    def on_cancelled(self):
        self.root.after(0, lambda: self.lbl_detail.config(text="Audit annulé"))
        self.root.after(0, self.reset_ui)
    
    def show_results(self, resultats, stats, duree=0):
        # Phase 7: Stocker les résultats pour l'export
        self.last_resultats = resultats
        self.last_stats = stats
        
        # Phase 8: Sauvegarder dans l'historique
        try:
            pdf_name = os.path.basename(self.pdf_path.get())
            excel_name = os.path.basename(self.excel_path.get())
            self.history.save_audit(pdf_name, excel_name, stats, resultats)
        except Exception as e:
            print(f"[HISTORIQUE] Erreur sauvegarde: {e}")
        
        # Activer les boutons d'export
        self.btn_export_excel.config(state='normal')
        self.btn_export_csv.config(state='normal')
        self.btn_export_pdf.config(state='normal')
        
        # Remplir le tableau
        for r in resultats:
            tag = ''
            if r['statut'] == 'OK':
                tag = 'ok'
            elif 'Excès' in r['statut']:
                tag = 'exces'
            else:
                tag = 'manque'
            
            self.tree.insert('', 'end', values=(
                r['societe'],
                r['iban'],
                f"{r['montant_pdf']:.2f} €",
                f"{r['montant_excel']:.2f} €",
                f"{r['ecart']:.2f} €",
                r['statut']
            ), tags=(tag,))
        
        # Configurer couleurs
        self.tree.tag_configure('ok', background='#d4edda')
        self.tree.tag_configure('exces', background='#fff3cd')
        self.tree.tag_configure('manque', background='#f8d7da')
        
        # Résumé
        texte = (
            f"Sociétés: {stats['total_societes']} | "
            f"OK: {stats['societes_ok']} | "
            f"Écarts: {stats['societes_ecart']} | "
            f"Total écart: {stats['total_ecart']:.2f} € | "
            f"Temps: {duree:.1f}s"
        )
        self.lbl_summary.config(text=texte)
        self.frame_summary.grid()
        
        self.reset_ui()
    
    def reset_ui(self):
        self.btn_start.config(state='normal')
        self.btn_cancel.config(state='disabled')
    
    def _safe_delete_file(self, path):
        """Supprime un fichier de manière sécurisée (uniquement s'il est dans le répertoire du projet)."""
        if not path or not os.path.exists(path):
            return
        try:
            # Sécurité: ne supprimer que si le fichier est dans le répertoire de l'application
            work_dir = os.path.abspath(os.path.dirname(__file__))
            file_abs = os.path.abspath(path)
            if file_abs.startswith(work_dir):
                os.remove(file_abs)
                print(f"[POST-AUDIT] Fichier supprimé: {file_abs}")
        except Exception as e:
            print(f"[POST-AUDIT] Erreur suppression {path}: {e}")
    
    def show_batch_window(self):
        """Phase 9: Fenêtre de mode batch pour traiter plusieurs couples PDF/Excel."""
        win = tk.Toplevel(self.root)
        win.title("Mode Batch")
        win.geometry("700x500")
        
        ttk.Label(win, text="File d'attente d'audits", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Liste des couples
        list_frame = ttk.Frame(win)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.batch_listbox = tk.Listbox(list_frame, height=10)
        self.batch_listbox.pack(side="left", fill="both", expand=True)
        
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.batch_listbox.yview)
        self.batch_listbox.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        
        # Boutons
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        
        self.batch_items = []
        
        def add_couple():
            pdf = filedialog.askopenfilename(title="PDF", filetypes=[("PDF", "*.pdf")], parent=win)
            if not pdf:
                return
            excel = filedialog.askopenfilename(title="Excel", filetypes=[("Excel", "*.xlsx *.xls")], parent=win)
            if not excel:
                return
            self.batch_items.append((pdf, excel))
            self.batch_listbox.insert('end', f"{os.path.basename(pdf)} + {os.path.basename(excel)}")
        
        def remove_couple():
            sel = self.batch_listbox.curselection()
            if sel:
                idx = sel[0]
                self.batch_listbox.delete(idx)
                self.batch_items.pop(idx)
        
        def run_batch():
            if not self.batch_items:
                messagebox.showwarning("Attention", "Aucun couple à traiter", parent=win)
                return
            
            win.destroy()
            self.batch_thread = threading.Thread(target=self.run_batch_processing, daemon=True)
            self.batch_thread.start()
        
        ttk.Button(btn_frame, text="Ajouter couple", command=add_couple).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Supprimer", command=remove_couple).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Lancer le batch", command=run_batch).pack(side="left", padx=5)
    
    def run_batch_processing(self):
        """Phase 9: Traite séquentiellement tous les couples de la file d'attente."""
        import time
        total_items = len(self.batch_items)
        all_results = []
        
        for idx, (pdf_path, excel_path) in enumerate(self.batch_items):
            if self.should_cancel:
                break
            
            self.root.after(0, lambda i=idx+1, t=total_items: 
                self.update_progress(int((i-1)/t*100), f"Batch {i}/{t}: {os.path.basename(pdf_path)}")
            )
            
            try:
                pdf_data = PDFParser.parse_file(pdf_path)
                pdf_data = Filters.filter_pdf(pdf_data)
                
                df_excel = ExcelParser.parse(excel_path)
                df_excel = Filters.filter_excel(df_excel)
                excel_data = df_excel.to_dict('records')
                
                correspondances, sans_corr = OptimizedMatcher.match_with_index(pdf_data, excel_data)
                resultats, total_ecart = EcartCalculator.calculer_ecarts(correspondances)
                stats = EcartCalculator.calculer_statistiques(resultats)
                
                all_results.append({
                    'pdf': os.path.basename(pdf_path),
                    'excel': os.path.basename(excel_path),
                    'stats': stats,
                    'resultats': resultats
                })
                
                # Sauvegarder dans l'historique
                try:
                    self.history.save_audit(os.path.basename(pdf_path), os.path.basename(excel_path), stats, resultats)
                except:
                    pass
                    
            except Exception as e:
                print(f"[BATCH] Erreur sur {pdf_path}: {e}")
                all_results.append({
                    'pdf': os.path.basename(pdf_path),
                    'excel': os.path.basename(excel_path),
                    'error': str(e)
                })
        
        self.root.after(0, lambda: self.show_batch_results(all_results))
    
    def show_batch_results(self, all_results):
        """Phase 9: Affiche le rapport consolidé du batch."""
        win = tk.Toplevel(self.root)
        win.title("Résultats du Batch")
        win.geometry("800x500")
        
        ttk.Label(win, text="Rapport consolidé du batch", font=('Arial', 12, 'bold')).pack(pady=10)
        
        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ('pdf', 'excel', 'societes', 'ok', 'ecarts', 'total_ecart', 'statut')
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
        
        for col in cols:
            tree.heading(col, text=col.upper())
        
        tree.column('pdf', width=150)
        tree.column('excel', width=150)
        tree.column('societes', width=80, anchor='center')
        tree.column('ok', width=60, anchor='center')
        tree.column('ecarts', width=60, anchor='center')
        tree.column('total_ecart', width=100, anchor='e')
        tree.column('statut', width=100)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        for r in all_results:
            if 'error' in r:
                tree.insert('', 'end', values=(r['pdf'], r['excel'], '-', '-', '-', '-', 'ERREUR'))
            else:
                s = r['stats']
                tree.insert('', 'end', values=(
                    r['pdf'], r['excel'], s['total_societes'], s['societes_ok'],
                    s['societes_ecart'], f"{s['total_ecart']:.2f} €", 'OK'
                ))
        
        self.reset_ui()
        self.batch_items = []
    
    def show_history(self):
        """Phase 8: Afficher la fenêtre d'historique des audits."""
        win = tk.Toplevel(self.root)
        win.title("Historique des audits")
        win.geometry("900x500")
        
        ttk.Label(win, text="Audits précédents", font=('Arial', 12, 'bold')).pack(pady=10)
        
        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ('date', 'pdf', 'excel', 'total', 'ok', 'ecarts', 'total_ecart')
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
        
        tree.heading('date', text='DATE')
        tree.heading('pdf', text='PDF')
        tree.heading('excel', text='EXCEL')
        tree.heading('total', text='SOCIÉTÉS')
        tree.heading('ok', text='OK')
        tree.heading('ecarts', text='ÉCARTS')
        tree.heading('total_ecart', text='TOTAL ÉCART')
        
        tree.column('date', width=140)
        tree.column('pdf', width=150)
        tree.column('excel', width=150)
        tree.column('total', width=80, anchor='center')
        tree.column('ok', width=60, anchor='center')
        tree.column('ecarts', width=60, anchor='center')
        tree.column('total_ecart', width=100, anchor='e')
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        try:
            audits = self.history.get_audits()
            for a in audits:
                tree.insert('', 'end', values=(
                    a['date'][:19],
                    a['pdf_name'] or '',
                    a['excel_name'] or '',
                    a['total_societes'],
                    a['societes_ok'],
                    a['societes_ecart'],
                    f"{a['total_ecart']:.2f} €"
                ))
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger l'historique:\n{e}", parent=win)
    
    def export_excel(self):
        if not self.last_resultats:
            messagebox.showwarning("Attention", "Aucun résultat à exporter")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Exporter vers Excel"
        )
        if path:
            try:
                ResultExporter.export_excel(self.last_resultats, self.last_stats, path)
                messagebox.showinfo("Export", f"Résultats exportés vers:\n{path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Export Excel échoué:\n{e}")
    
    def export_csv(self):
        if not self.last_resultats:
            messagebox.showwarning("Attention", "Aucun résultat à exporter")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Exporter vers CSV"
        )
        if path:
            try:
                ResultExporter.export_csv(self.last_resultats, path)
                messagebox.showinfo("Export", f"Résultats exportés vers:\n{path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Export CSV échoué:\n{e}")
    
    def export_pdf(self):
        if not self.last_resultats:
            messagebox.showwarning("Attention", "Aucun résultat à exporter")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Exporter vers PDF"
        )
        if path:
            try:
                ResultExporter.export_pdf(self.last_resultats, self.last_stats, path)
                messagebox.showinfo("Export", f"Résultats exportés vers:\n{path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Export PDF échoué:\n{e}")
    
    def reset_all(self):
        """Phase 5: Post-Audit - Réinitialisation complète + suppression fichiers uploadés"""
        # FIX POST-01/02: Supprimer les fichiers uploadés
        self._safe_delete_file(self.pdf_path.get())
        self._safe_delete_file(self.excel_path.get())
        
        self.pdf_path.set("")
        self.excel_path.set("")
        self.progress_var.set(0)
        self.lbl_progress.config(text="0% - Prêt")
        self.lbl_detail.config(text="")
        self.tree.delete(*self.tree.get_children())
        self.frame_summary.grid_remove()
        self.should_cancel = False
        
        # Phase 7: Désactiver les boutons d'export
        self.btn_export_excel.config(state='disabled')
        self.btn_export_csv.config(state='disabled')
        self.btn_export_pdf.config(state='disabled')
        self.last_resultats = []
        self.last_stats = {}
        
        messagebox.showinfo("Nouvel audit", "Prêt pour un nouvel audit")


def main():
    root = tk.Tk()
    app = AuditApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
