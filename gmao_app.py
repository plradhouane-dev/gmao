import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from cryptography.fernet import Fernet
import os
from datetime import datetime

# === CONFIGURATION ===
KEY_FILE = 'secret.key'
DB_FILE = 'gmao_encrypted.db'
INITIAL_PASSWORD = 'admin123'  # Mot de passe administrateur par défaut (à changer)

# === FONCTIONS DE CHIFFREMENT ===
def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key

def encrypt_data(data):
    key = load_key()
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(token):
    key = load_key()
    f = Fernet(key)
    return f.decrypt(token).decode()

# === INITIALISATION DE LA BASE DE DONNÉES CHIFFRÉE ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS equipements (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero_serie TEXT UNIQUE,
                 marque TEXT,
                 modele TEXT,
                 date_achat TEXT,
                 date_vente TEXT,
                 identifiant_acheteur TEXT,
                 notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS interventions (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 equipement_id INTEGER,
                 date_entree TEXT,
                 date_sortie TEXT,
                 details_reparation TEXT,
                 technicien TEXT,
                 cout REAL,
                 FOREIGN KEY(equipement_id) REFERENCES equipements(id))''')
    conn.commit()
    conn.close()

# === AUTHENTIFICATION ===
def authentification():
    def verifier():
        mdp = entry_mdp.get()
        if mdp == INITIAL_PASSWORD:
            fenetre_auth.destroy()
            ouvrir_gmao()
        else:
            messagebox.showerror("Erreur", "Mot de passe incorrect")

    fenetre_auth = tk.Tk()
    fenetre_auth.title("Authentification")
    fenetre_auth.geometry("300x150")

    tk.Label(fenetre_auth, text="Mot de passe :", font=("Arial", 12)).pack(pady=10)
    entry_mdp = tk.Entry(fenetre_auth, show='*', font=("Arial", 12))
    entry_mdp.pack(pady=5)
    entry_mdp.focus()

    tk.Button(fenetre_auth, text="Valider", command=verifier, font=("Arial", 10), bg="#4CAF50", fg="white").pack(pady=10)
    entry_mdp.bind('<Return>', lambda event: verifier())

    fenetre_auth.mainloop()

# === INTERFACE GMAO ===
def ouvrir_gmao():
    def rechercher():
        numero_serie = entry_numero.get().strip()
        if not numero_serie:
            messagebox.showwarning("Attention", "Veuillez saisir un numéro de série")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM equipements WHERE numero_serie=?", (numero_serie,))
        result = c.fetchone()
        conn.close()

        if not result:
            ouvrir_formulaire(numero_serie)
        else:
            afficher_historique(result[0], numero_serie)

    def ouvrir_formulaire(numero_serie):
        def sauvegarder():
            marque = entry_marque.get().strip()
            modele = entry_modele.get().strip()
            date_achat = entry_date_achat.get().strip()
            date_vente = entry_date_vente.get().strip()
            identifiant_acheteur = entry_acheteur.get().strip()
            notes = text_notes.get("1.0", tk.END).strip()

            if not marque or not modele:
                messagebox.showwarning("Attention", "Marque et Modèle sont obligatoires")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO equipements 
                          (numero_serie, marque, modele, date_achat, date_vente, identifiant_acheteur, notes) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (numero_serie, marque, modele, date_achat, date_vente, identifiant_acheteur, notes))
                conn.commit()
                messagebox.showinfo("Succès", "Équipement enregistré avec succès!")
                fenetre_formulaire.destroy()
                c.execute("SELECT id FROM equipements WHERE numero_serie=?", (numero_serie,))
                equipement_id = c.fetchone()[0]
                afficher_historique(equipement_id, numero_serie)
            except sqlite3.IntegrityError:
                messagebox.showerror("Erreur", "Numéro de série déjà existant")
            finally:
                conn.close()

        fenetre_formulaire = tk.Toplevel()
        fenetre_formulaire.title(f"Nouvel Équipement - {numero_serie}")
        fenetre_formulaire.geometry("500x600")

        main_frame = tk.Frame(fenetre_formulaire, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Informations de l'Équipement", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        tk.Label(main_frame, text="Marque *:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
        entry_marque = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_marque.grid(row=1, column=1, sticky="ew", pady=5)

        tk.Label(main_frame, text="Modèle *:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
        entry_modele = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_modele.grid(row=2, column=1, sticky="ew", pady=5)

        tk.Label(main_frame, text="Date d'achat:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=5)
        entry_date_achat = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_date_achat.grid(row=3, column=1, sticky="ew", pady=5)
        entry_date_achat.insert(0, datetime.now().strftime("%Y-%m-%d"))

        tk.Label(main_frame, text="Date de vente:", font=("Arial", 10)).grid(row=4, column=0, sticky="w", pady=5)
        entry_date_vente = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_date_vente.grid(row=4, column=1, sticky="ew", pady=5)

        tk.Label(main_frame, text="Identifiant Acheteur:", font=("Arial", 10)).grid(row=5, column=0, sticky="w", pady=5)
        entry_acheteur = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_acheteur.grid(row=5, column=1, sticky="ew", pady=5)

        tk.Label(main_frame, text="Notes:", font=("Arial", 10)).grid(row=6, column=0, sticky="nw", pady=5)
        text_notes = tk.Text(main_frame, font=("Arial", 10), width=30, height=8)
        text_notes.grid(row=6, column=1, sticky="ew", pady=5)

        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)

        tk.Button(button_frame, text="Sauvegarder", command=sauvegarder,
                 font=("Arial", 10), bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Annuler", command=fenetre_formulaire.destroy,
                 font=("Arial", 10), bg="#f44336", fg="white", width=15).pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1)
        entry_marque.focus()

    def afficher_historique(equipement_id, numero_serie):
        def ajouter_intervention():
            def sauvegarder_intervention():
                date_entree = entry_date_entree.get().strip()
                date_sortie = entry_date_sortie.get().strip()
                details = text_details.get("1.0", tk.END).strip()
                technicien = entry_technicien.get().strip()
                cout_text = entry_cout.get().strip()

                if not date_entree:
                    messagebox.showwarning("Attention", "La date d'entrée est obligatoire")
                    return

                try:
                    cout = float(cout_text) if cout_text else 0.0
                except ValueError:
                    messagebox.showwarning("Attention", "Le coût doit être un nombre valide")
                    return

                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''INSERT INTO interventions 
                          (equipement_id, date_entree, date_sortie, details_reparation, technicien, cout) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                          (equipement_id, date_entree, date_sortie, details, technicien, cout))
                conn.commit()
                conn.close()

                messagebox.showinfo("Succès", "Intervention enregistrée!")
                fenetre_intervention.destroy()
                rafraichir_tableau()

            fenetre_intervention = tk.Toplevel()
            fenetre_intervention.title("Nouvelle Intervention")
            fenetre_intervention.geometry("500x400")

            main_frame = tk.Frame(fenetre_intervention, padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            tk.Label(main_frame, text="Nouvelle Intervention", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

            tk.Label(main_frame, text="Date d'entrée *:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
            entry_date_entree = tk.Entry(main_frame, font=("Arial", 10))
            entry_date_entree.grid(row=1, column=1, sticky="ew", pady=5)
            entry_date_entree.insert(0, datetime.now().strftime("%Y-%m-%d"))

            tk.Label(main_frame, text="Date de sortie:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
            entry_date_sortie = tk.Entry(main_frame, font=("Arial", 10))
            entry_date_sortie.grid(row=2, column=1, sticky="ew", pady=5)

            tk.Label(main_frame, text="Technicien:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=5)
            entry_technicien = tk.Entry(main_frame, font=("Arial", 10))
            entry_technicien.grid(row=3, column=1, sticky="ew", pady=5)

            tk.Label(main_frame, text="Coût:", font=("Arial", 10)).grid(row=4, column=0, sticky="w", pady=5)
            entry_cout = tk.Entry(main_frame, font=("Arial", 10))
            entry_cout.grid(row=4, column=1, sticky="ew", pady=5)

            tk.Label(main_frame, text="Détails de réparation:", font=("Arial", 10)).grid(row=5, column=0, sticky="nw", pady=5)
            text_details = tk.Text(main_frame, font=("Arial", 10), width=30, height=8)
            text_details.grid(row=5, column=1, sticky="ew", pady=5)

            button_frame = tk.Frame(main_frame)
            button_frame.grid(row=6, column=0, columnspan=2, pady=20)

            tk.Button(button_frame, text="Sauvegarder", command=sauvegarder_intervention,
                     font=("Arial", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Annuler", command=fenetre_intervention.destroy,
                     font=("Arial", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

            main_frame.columnconfigure(1, weight=1)

        def rafraichir_tableau():
            for item in tree.get_children():
                tree.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT date_entree, date_sortie, technicien, cout, details_reparation 
                         FROM interventions WHERE equipement_id=? ORDER BY date_entree DESC''', (equipement_id,))
            interventions = c.fetchall()
            conn.close()
            for intervention in interventions:
                tree.insert("", tk.END, values=intervention)

        def voir_detail():
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showwarning("Attention", "Veuillez sélectionner une intervention.")
                return

            values = tree.item(selected_item, 'values')
            details_complets = values[4]

            fenetre_detail = tk.Toplevel()
            fenetre_detail.title("Détail complet de l'intervention")
            fenetre_detail.geometry("600x400")

            tk.Label(fenetre_detail, text="Détails de la réparation :", font=("Arial", 12, "bold")).pack(pady=10)
            text_zone = tk.Text(fenetre_detail, font=("Arial", 10), wrap="word", height=15)
            text_zone.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            text_zone.insert(tk.END, details_complets)
            text_zone.config(state=tk.DISABLED)

            tk.Button(fenetre_detail, text="Fermer", command=fenetre_detail.destroy,
                      font=("Arial", 10), bg="#f44336", fg="white").pack(pady=10)

        fenetre_historique = tk.Toplevel()
        fenetre_historique.title(f"Historique - {numero_serie}")
        fenetre_historique.geometry("900x700")

        notebook = ttk.Notebook(fenetre_historique)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        frame_info = ttk.Frame(notebook)
        notebook.add(frame_info, text="Informations Équipement")

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM equipements WHERE id=?", (equipement_id,))
        equipement = c.fetchone()

        info_frame = tk.Frame(frame_info, padx=20, pady=20)
        info_frame.pack(fill=tk.BOTH, expand=True)

        infos = [
            ("Numéro de série:", equipement[1]),
            ("Marque:", equipement[2]),
            ("Modèle:", equipement[3]),
            ("Date d'achat:", equipement[4]),
            ("Date de vente:", equipement[5]),
            ("Identifiant Acheteur:", equipement[6]),
            ("Notes:", equipement[7])
        ]

        for i, (label, value) in enumerate(infos):
            tk.Label(info_frame, text=label, font=("Arial", 10, "bold"), anchor="w").grid(row=i, column=0, sticky="w", pady=5)
            tk.Label(info_frame, text=value or "Non renseigné", font=("Arial", 10), anchor="w").grid(row=i, column=1, sticky="w", pady=5)

        frame_repairs = ttk.Frame(notebook)
        notebook.add(frame_repairs, text="Historique des Réparations")

        main_repair_frame = tk.Frame(frame_repairs)
        main_repair_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        table_frame = tk.Frame(main_repair_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Date Entrée", "Date Sortie", "Technicien", "Coût", "Détails")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.column("Détails", width=200)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        c.execute('''SELECT date_entree, date_sortie, technicien, cout, details_reparation 
                     FROM interventions WHERE equipement_id=? ORDER BY date_entree DESC''', (equipement_id,))
        interventions = c.fetchall()
        conn.close()

        for intervention in interventions:
            tree.insert("", tk.END, values=intervention)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = tk.Frame(main_repair_frame)
        button_frame.pack(fill=tk.X, pady=10)

        tk.Button(button_frame, text="➕ Ajouter Nouvelle Intervention", command=ajouter_intervention,
                 font=("Arial", 10), bg="#2196F3", fg="white", width=25).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="🔄 Rafraîchir", command=rafraichir_tableau,
                 font=("Arial", 10), bg="#FF9800", fg="white", width=15).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="👁 Voir Détails", command=voir_detail,
                 font=("Arial", 10), bg="#9C27B0", fg="white", width=15).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="❌ Fermer", command=fenetre_historique.destroy,
                 font=("Arial", 10), bg="#f44336", fg="white", width=15).pack(side=tk.RIGHT, padx=5)

    root = tk.Tk()
    root.title("GMAO - Gestion de Maintenance")
    root.geometry("400x200")

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(main_frame, text="Recherche d'Équipement", font=("Arial", 16, "bold")).pack(pady=(0, 20))
    tk.Label(main_frame, text="Numéro de série:", font=("Arial", 12)).pack(pady=5)
    entry_numero = tk.Entry(main_frame, font=("Arial", 12))
    entry_numero.pack(pady=5)
    entry_numero.focus()

    tk.Button(main_frame, text="Rechercher", command=rechercher,
             font=("Arial", 12), bg="#4CAF50", fg="white").pack(pady=10)

    root.mainloop()

# === LANCEMENT ===
if __name__ == "__main__":
    init_db()
    authentification()
