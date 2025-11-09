import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3
from cryptography.fernet import Fernet
import os
from datetime import datetime, timedelta

# === CONFIGURATION ===
KEY_FILE = 'secret.key'
DB_FILE = 'gmao_encrypted.db'
INITIAL_PASSWORD = 'admin123'  # Mot de passe administrateur par défaut (à changer)
LOW_STOCK_THRESHOLD = 5  # seuil d'alerte pour réapprovisionnement

# === FONCTIONS DE CHIFFREMENT (utilisées pour clés / exemples) ===
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

# === INITIALISATION DE LA BASE DE DONNÉES ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # equipements
    c.execute('''CREATE TABLE IF NOT EXISTS equipements (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero_serie TEXT UNIQUE,
                 marque TEXT,
                 modele TEXT,
                 date_achat TEXT,
                 date_vente TEXT,
                 identifiant_acheteur TEXT,
                 notes TEXT)''')
    # interventions
    c.execute('''CREATE TABLE IF NOT EXISTS interventions (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 equipement_id INTEGER,
                 date_entree TEXT,
                 date_sortie TEXT,
                 details_reparation TEXT,
                 technicien TEXT,
                 cout REAL,
                 FOREIGN KEY(equipement_id) REFERENCES equipements(id))''')
    # planification
    c.execute('''CREATE TABLE IF NOT EXISTS planification (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 equipement_id INTEGER,
                 date_prevue TEXT,
                 type_maintenance TEXT,
                 technicien TEXT,
                 statut TEXT,
                 notes TEXT,
                 FOREIGN KEY(equipement_id) REFERENCES equipements(id))''')
    # pièces
    c.execute('''CREATE TABLE IF NOT EXISTS pieces (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nom TEXT,
                 reference TEXT UNIQUE,
                 fournisseur TEXT,
                 prix_unitaire REAL,
                 quantite_stock INTEGER,
                 description TEXT)''')
    # liaison intervention ↔ pièces
    c.execute('''CREATE TABLE IF NOT EXISTS intervention_pieces (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 intervention_id INTEGER,
                 piece_id INTEGER,
                 quantite_utilisee INTEGER,
                 cout_total REAL,
                 FOREIGN KEY(intervention_id) REFERENCES interventions(id),
                 FOREIGN KEY(piece_id) REFERENCES pieces(id))''')
    conn.commit()
    conn.close()

# === AUTHENTIFICATION SIMPLE (mot de passe unique) ===
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

# === RAPPEL MAINTENANCE PREVENTIVE ===
def verifier_rappels(root=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    aujourd_hui = datetime.now().date()
    date_limite = aujourd_hui + timedelta(days=7)
    c.execute('''SELECT e.numero_serie, p.date_prevue, p.type_maintenance 
                 FROM planification p
                 JOIN equipements e ON p.equipement_id = e.id
                 WHERE date_prevue BETWEEN ? AND ?''', (aujourd_hui, date_limite))
    alertes = c.fetchall()
    conn.close()
    if alertes:
        msg = "Rappel : Maintenance préventive à venir dans les 7 jours :\n"
        for a in alertes:
            msg += f"- Équipement {a[0]} : {a[2]} prévu le {a[1]}\n"
        messagebox.showinfo("Rappel Maintenance Préventive", msg)
    if root:
        maintenant = datetime.now()
        # planifier rappel au lendemain 9:00
        demain_9h = (maintenant + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        ms_attente = int((demain_9h - maintenant).total_seconds() * 1000)
        root.after(ms_attente, lambda: verifier_rappels(root))

# === INTERFACE GMAO (avec gestion pièces) ===
def ouvrir_gmao():
    # --- Ouvrir gestion pièces (menu) ---
    def ouvrir_gestion_pieces():
        fenetre_stock = tk.Toplevel(root)
        fenetre_stock.title("🧾 Gestion des pièces de rechange")
        fenetre_stock.geometry("900x500")

        # Tableau
        colonnes = ("ID", "Nom", "Référence", "Fournisseur", "Prix", "Quantité", "Description")
        tree_pieces = ttk.Treeview(fenetre_stock, columns=colonnes, show="headings", height=18)
        for col in colonnes:
            tree_pieces.heading(col, text=col)
            # ID petit
            tree_pieces.column(col, width=(50 if col == "ID" else 130))
        tree_pieces.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def rafraichir_stock():
            for it in tree_pieces.get_children():
                tree_pieces.delete(it)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, nom, reference, fournisseur, prix_unitaire, quantite_stock, description FROM pieces ORDER BY nom")
            rows = c.fetchall()
            conn.close()
            for r in rows:
                tree_pieces.insert("", tk.END, values=r)

        def ajouter_piece():
            fenetre_ajout = tk.Toplevel(fenetre_stock)
            fenetre_ajout.title("Ajouter une pièce")
            fenetre_ajout.geometry("420x360")
            fields = [
                ("Nom *:", "nom"),
                ("Référence *:", "ref"),
                ("Fournisseur:", "four"),
                ("Prix unitaire:", "prix"),
                ("Quantité en stock:", "qte"),
            ]
            entries = {}
            for i, (label, key) in enumerate(fields):
                tk.Label(fenetre_ajout, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=6)
                e = tk.Entry(fenetre_ajout)
                e.grid(row=i, column=1, padx=8, pady=6)
                entries[key] = e
            tk.Label(fenetre_ajout, text="Description:").grid(row=len(fields), column=0, sticky="nw", padx=8, pady=6)
            txt_desc = tk.Text(fenetre_ajout, height=6, width=30)
            txt_desc.grid(row=len(fields), column=1, padx=8, pady=6)

            def sauvegarder_piece():
                nom = entries["nom"].get().strip()
                ref = entries["ref"].get().strip()
                four = entries["four"].get().strip()
                try:
                    prix = float(entries["prix"].get().strip() or 0)
                    qte = int(entries["qte"].get().strip() or 0)
                except ValueError:
                    messagebox.showwarning("Erreur", "Prix ou quantité invalide.")
                    return
                desc = txt_desc.get("1.0", tk.END).strip()
                if not nom or not ref:
                    messagebox.showwarning("Attention", "Nom et Référence obligatoires.")
                    return
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute('''INSERT INTO pieces (nom, reference, fournisseur, prix_unitaire, quantite_stock, description)
                                 VALUES (?, ?, ?, ?, ?, ?)''', (nom, ref, four, prix, qte, desc))
                    conn.commit()
                    messagebox.showinfo("Succès", "Pièce ajoutée.")
                    fenetre_ajout.destroy()
                    rafraichir_stock()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Erreur", "Référence déjà existante.")
                finally:
                    conn.close()

            tk.Button(fenetre_ajout, text="Sauvegarder", bg="#4CAF50", fg="white", command=sauvegarder_piece).grid(row=10, column=0, pady=10, padx=8)
            tk.Button(fenetre_ajout, text="Annuler", bg="#f44336", fg="white", command=fenetre_ajout.destroy).grid(row=10, column=1, pady=10, padx=8)

        def modifier_piece():
            sel = tree_pieces.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez une pièce à modifier.")
                return
            vals = tree_pieces.item(sel[0], 'values')
            piece_id = vals[0]
            fenetre_mod = tk.Toplevel(fenetre_stock)
            fenetre_mod.title("Modifier pièce")
            fenetre_mod.geometry("420x360")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT nom, reference, fournisseur, prix_unitaire, quantite_stock, description FROM pieces WHERE id=?", (piece_id,))
            row = c.fetchone()
            conn.close()
            fields = [("Nom:", row[0]), ("Référence:", row[1]), ("Fournisseur:", row[2]), ("Prix unitaire:", row[3]), ("Quantité:", row[4])]
            entries = {}
            for i, (label, value) in enumerate(fields):
                tk.Label(fenetre_mod, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=6)
                e = tk.Entry(fenetre_mod)
                e.grid(row=i, column=1, padx=8, pady=6)
                e.insert(0, str(value))
                entries[i] = e
            tk.Label(fenetre_mod, text="Description:").grid(row=len(fields), column=0, sticky="nw", padx=8, pady=6)
            txt_desc = tk.Text(fenetre_mod, height=6, width=30)
            txt_desc.grid(row=len(fields), column=1, padx=8, pady=6)
            txt_desc.insert("1.0", row[5] or "")

            def sauvegarder_mod():
                nom = entries[0].get().strip()
                ref = entries[1].get().strip()
                four = entries[2].get().strip()
                try:
                    prix = float(entries[3].get().strip() or 0)
                    qte = int(entries[4].get().strip() or 0)
                except ValueError:
                    messagebox.showwarning("Erreur", "Prix ou quantité invalide.")
                    return
                desc = txt_desc.get("1.0", tk.END).strip()
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute('''UPDATE pieces SET nom=?, reference=?, fournisseur=?, prix_unitaire=?, quantite_stock=?, description=? WHERE id=?''',
                              (nom, ref, four, prix, qte, desc, piece_id))
                    conn.commit()
                    messagebox.showinfo("Succès", "Pièce modifiée.")
                    fenetre_mod.destroy()
                    rafraichir_stock()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Erreur", "Référence déjà utilisée par une autre pièce.")
                finally:
                    conn.close()

            tk.Button(fenetre_mod, text="Sauvegarder", bg="#4CAF50", fg="white", command=sauvegarder_mod).grid(row=12, column=0, pady=10, padx=8)
            tk.Button(fenetre_mod, text="Annuler", bg="#f44336", fg="white", command=fenetre_mod.destroy).grid(row=12, column=1, pady=10, padx=8)

        def supprimer_piece():
            sel = tree_pieces.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez une pièce à supprimer.")
                return
            if not messagebox.askyesno("Confirmation", "Voulez-vous supprimer la pièce sélectionnée ?"):
                return
            vals = tree_pieces.item(sel[0], 'values')
            piece_id = vals[0]
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM pieces WHERE id=?", (piece_id,))
            conn.commit()
            conn.close()
            rafraichir_stock()

        def alerte_stock_faible():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT nom, quantite_stock FROM pieces WHERE quantite_stock <= ?", (LOW_STOCK_THRESHOLD,))
            low = c.fetchall()
            conn.close()
            if low:
                msg = "Attention : pièces proche de la rupture :\n"
                for nom, qte in low:
                    msg += f"- {nom} (stock: {qte})\n"
                messagebox.showwarning("Stock faible", msg)

        # boutons
        btn_frame = tk.Frame(fenetre_stock)
        btn_frame.pack(fill=tk.X, pady=6)
        tk.Button(btn_frame, text="➕ Ajouter une pièce", command=ajouter_piece, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="✏️ Modifier", command=modifier_piece, bg="#FFC107").pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="🗑 Supprimer", command=supprimer_piece, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="🔄 Rafraîchir", command=rafraichir_stock, bg="#FF9800").pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="🔔 Alerte stock faible", command=alerte_stock_faible, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=6)

        rafraichir_stock()
        # alerte initiale
        alerte_stock_faible()

    # --- Fonctions principales (recherche, formulaire équipement, historique, etc.) ---
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

        fenetre_formulaire = tk.Toplevel(root)
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
        tk.Button(button_frame, text="Sauvegarder", command=sauvegarder, font=("Arial", 10), bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Annuler", command=fenetre_formulaire.destroy, font=("Arial", 10), bg="#f44336", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        main_frame.columnconfigure(1, weight=1)
        entry_marque.focus()

    # --- HISTORIQUE & INTERVENTIONS (avec gestion pièces) ---
    def afficher_historique(equipement_id, numero_serie):
        fenetre_historique = tk.Toplevel(root)
        fenetre_historique.title(f"Historique - {numero_serie}")
        fenetre_historique.geometry("1000x700")
        notebook = ttk.Notebook(fenetre_historique)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Informations équipement
        frame_info = ttk.Frame(notebook)
        notebook.add(frame_info, text="Informations Équipement")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM equipements WHERE id=?", (equipement_id,))
        equipement = c.fetchone()
        conn.close()
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

        # Historique réparations
        frame_repairs = ttk.Frame(notebook)
        notebook.add(frame_repairs, text="Historique des Réparations")
        main_repair_frame = tk.Frame(frame_repairs)
        main_repair_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("ID", "Date Entrée", "Date Sortie", "Technicien", "Coût", "Détails")
        tree = ttk.Treeview(main_repair_frame, columns=columns, show="headings", height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=(60 if col == "ID" else 140))
        tree.column("Détails", width=260)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(main_repair_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def rafraichir_tableau():
            for item in tree.get_children():
                tree.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT id, date_entree, date_sortie, technicien, cout, details_reparation 
                         FROM interventions WHERE equipement_id=? ORDER BY date_entree DESC''', (equipement_id,))
            interventions = c.fetchall()
            conn.close()
            for intervention in interventions:
                tree.insert("", tk.END, values=intervention)

        # gestion pièces temporaire pour la nouvelle intervention
        pieces_selectionnees = []  # list of dicts: {'piece_id':.., 'nom':.., 'prix':.., 'qte':.., 'cout_total':..}

        def gerer_pieces_utilisees(parent_window):
            """Ouvre une fenêtre permettant de sélectionner pièces et quantités.
               Les choix sont stockés dans pieces_selectionnees (par référence)."""
            nonlocal pieces_selectionnees
            fen = tk.Toplevel(parent_window)
            fen.title("Associer des pièces à l'intervention")
            fen.geometry("800x450")

            # Left: liste pièces disponibles
            left_frame = tk.Frame(fen)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            cols = ("ID", "Nom", "Réf", "Prix", "Stock")
            tree_left = ttk.Treeview(left_frame, columns=cols, show="headings", height=15)
            for ccol in cols:
                tree_left.heading(ccol, text=ccol)
                tree_left.column(ccol, width=(50 if ccol == "ID" else 120))
            tree_left.pack(fill=tk.BOTH, expand=True)
            scroll_left = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=tree_left.yview)
            tree_left.configure(yscrollcommand=scroll_left.set)
            scroll_left.pack(side=tk.RIGHT, fill=tk.Y)

            # Right: pièces sélectionnées
            right_frame = tk.Frame(fen)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            cols2 = ("Piece ID", "Nom", "Quantité", "Prix unitaire", "Coût total")
            tree_right = ttk.Treeview(right_frame, columns=cols2, show="headings", height=15)
            for ccol in cols2:
                tree_right.heading(ccol, text=ccol)
                tree_right.column(ccol, width=(80 if ccol == "Piece ID" else 110))
            tree_right.pack(fill=tk.BOTH, expand=True)
            scroll_right = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_right.yview)
            tree_right.configure(yscrollcommand=scroll_right.set)
            scroll_right.pack(side=tk.RIGHT, fill=tk.Y)

            # load pieces
            def load_pieces_list():
                for it in tree_left.get_children():
                    tree_left.delete(it)
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT id, nom, reference, prix_unitaire, quantite_stock FROM pieces ORDER BY nom")
                rows = c.fetchall()
                conn.close()
                for r in rows:
                    tree_left.insert("", tk.END, values=r)

            load_pieces_list()

            def ajouter_selection():
                sel = tree_left.selection()
                if not sel:
                    messagebox.showwarning("Attention", "Sélectionnez une pièce à ajouter")
                    return
                vals = tree_left.item(sel[0], 'values')
                piece_id, nom, ref, prix, stock = vals
                # demander quantité
                qte_str = simpledialog.askstring("Quantité", f"Quantité à utiliser pour '{nom}' (stock {stock}) :", parent=fen)
                if qte_str is None:
                    return
                try:
                    qte = int(qte_str)
                    if qte <= 0:
                        raise ValueError()
                except ValueError:
                    messagebox.showwarning("Erreur", "Quantité invalide")
                    return
                if qte > int(stock):
                    messagebox.showwarning("Erreur", f"Quantité demandée ({qte}) supérieure au stock ({stock})")
                    return
                cout_total = float(prix) * qte
                # si déjà sélectionnée, incrémenter
                for p in pieces_selectionnees:
                    if p['piece_id'] == piece_id:
                        p['quantite'] += qte
                        p['cout_total'] = p['quantite'] * p['prix']
                        refresh_right()
                        return
                # sinon ajouter
                pieces_selectionnees.append({'piece_id': piece_id, 'nom': nom, 'prix': float(prix), 'quantite': qte, 'cout_total': cout_total})
                refresh_right()

            def supprimer_selection():
                sel = tree_right.selection()
                if not sel:
                    messagebox.showwarning("Attention", "Sélectionnez une pièce dans la liste de droite")
                    return
                vals = tree_right.item(sel[0], 'values')
                piece_id = vals[0]
                pieces_selectionnees[:] = [p for p in pieces_selectionnees if p['piece_id'] != piece_id]
                refresh_right()

            def refresh_right():
                for it in tree_right.get_children():
                    tree_right.delete(it)
                for p in pieces_selectionnees:
                    tree_right.insert("", tk.END, values=(p['piece_id'], p['nom'], p['quantite'], f"{p['prix']:.2f}", f"{p['cout_total']:.2f}"))

            btn_frame = tk.Frame(fen)
            btn_frame.pack(fill=tk.X, pady=6)
            tk.Button(btn_frame, text="➕ Ajouter pièce", command=ajouter_selection, bg="#2196F3").pack(side=tk.LEFT, padx=6)
            tk.Button(btn_frame, text="🗑 Supprimer sélection", command=supprimer_selection, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=6)
            tk.Button(btn_frame, text="✅ Valider & Fermer", command=fen.destroy, bg="#4CAF50", fg="white").pack(side=tk.RIGHT, padx=6)

        def ajouter_intervention():
            # reset selection
            nonlocal pieces_selectionnees
            pieces_selectionnees = []

            fenetre_intervention = tk.Toplevel(fenetre_historique)
            fenetre_intervention.title("Nouvelle Intervention")
            fenetre_intervention.geometry("620x520")
            main_frame_i = tk.Frame(fenetre_intervention, padx=20, pady=20)
            main_frame_i.pack(fill=tk.BOTH, expand=True)
            tk.Label(main_frame_i, text="Nouvelle Intervention", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 20))

            tk.Label(main_frame_i, text="Date d'entrée *:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
            entry_date_entree = tk.Entry(main_frame_i, font=("Arial", 10))
            entry_date_entree.grid(row=1, column=1, sticky="ew", pady=5)
            entry_date_entree.insert(0, datetime.now().strftime("%Y-%m-%d"))

            tk.Label(main_frame_i, text="Date de sortie:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
            entry_date_sortie = tk.Entry(main_frame_i, font=("Arial", 10))
            entry_date_sortie.grid(row=2, column=1, sticky="ew", pady=5)

            tk.Label(main_frame_i, text="Technicien:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=5)
            entry_technicien = tk.Entry(main_frame_i, font=("Arial", 10))
            entry_technicien.grid(row=3, column=1, sticky="ew", pady=5)

            tk.Label(main_frame_i, text="Coût main d'oeuvre:", font=("Arial", 10)).grid(row=4, column=0, sticky="w", pady=5)
            entry_cout_main = tk.Entry(main_frame_i, font=("Arial", 10))
            entry_cout_main.grid(row=4, column=1, sticky="ew", pady=5)
            entry_cout_main.insert(0, "0.0")

            tk.Label(main_frame_i, text="Détails de réparation:", font=("Arial", 10)).grid(row=5, column=0, sticky="nw", pady=5)
            text_details = tk.Text(main_frame_i, font=("Arial", 10), width=50, height=8)
            text_details.grid(row=5, column=1, sticky="ew", pady=5, columnspan=2)

            # Bouton pour gérer pièces
            btn_pieces = tk.Button(main_frame_i, text="🧾 Gérer pièces utilisées", bg="#9C27B0", fg="white",
                                   command=lambda: gerer_pieces_utilisees(fenetre_intervention))
            btn_pieces.grid(row=6, column=0, pady=10)

            lbl_pieces_info = tk.Label(main_frame_i, text="Aucune pièce sélectionnée", anchor="w")
            lbl_pieces_info.grid(row=6, column=1, sticky="w")

            def update_pieces_label():
                if not pieces_selectionnees:
                    lbl_pieces_info.config(text="Aucune pièce sélectionnée")
                else:
                    s = ", ".join([f"{p['nom']} x{p['quantite']}" for p in pieces_selectionnees])
                    lbl_pieces_info.config(text=s[:80] + ("..." if len(s) > 80 else ""))

            # refresh label when fenetre_intervention regains focus
            def on_focus(event=None):
                update_pieces_label()
            fenetre_intervention.bind("<FocusIn>", on_focus)

            def sauvegarder_intervention():
                date_entree = entry_date_entree.get().strip()
                date_sortie = entry_date_sortie.get().strip()
                technicien = entry_technicien.get().strip()
                cout_main_text = entry_cout_main.get().strip()
                details = text_details.get("1.0", tk.END).strip()
                if not date_entree:
                    messagebox.showwarning("Attention", "Date d'entrée obligatoire")
                    return
                try:
                    cout_main = float(cout_main_text) if cout_main_text else 0.0
                except ValueError:
                    messagebox.showwarning("Attention", "Coût principal invalide")
                    return
                # Vérifier stocks suffisants pour toutes les pièces sélectionnées
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                for p in pieces_selectionnees:
                    c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (p['piece_id'],))
                    row = c.fetchone()
                    if not row:
                        conn.close()
                        messagebox.showerror("Erreur", f"La pièce {p['nom']} n'existe plus.")
                        return
                    stock = row[0]
                    if p['quantite'] > stock:
                        conn.close()
                        messagebox.showerror("Erreur", f"Stock insuffisant pour {p['nom']} (stock: {stock}, demandé: {p['quantite']}).")
                        return
                # Tout ok -> insérer intervention
                c.execute('''INSERT INTO interventions (equipement_id, date_entree, date_sortie, details_reparation, technicien, cout)
                             VALUES (?, ?, ?, ?, ?, ?)''', (equipement_id, date_entree, date_sortie, details, technicien, 0.0))
                intervention_id = c.lastrowid
                total_pieces_cost = 0.0
                # insérer intervention_pieces et décrémenter stock
                for p in pieces_selectionnees:
                    piece_id = p['piece_id']
                    qte = p['quantite']
                    prix = p['prix']
                    cout_total = round(prix * qte, 2)
                    total_pieces_cost += cout_total
                    c.execute('''INSERT INTO intervention_pieces (intervention_id, piece_id, quantite_utilisee, cout_total)
                                 VALUES (?, ?, ?, ?)''', (intervention_id, piece_id, qte, cout_total))
                    # décrémenter stock
                    c.execute("UPDATE pieces SET quantite_stock = quantite_stock - ? WHERE id=?", (qte, piece_id))
                # mettre à jour cout total de l'intervention = main d'oeuvre + pièces
                cout_total_interv = round(cout_main + total_pieces_cost, 2)
                c.execute("UPDATE interventions SET cout = ? WHERE id=?", (cout_total_interv, intervention_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Succès", f"Intervention enregistrée.\nCoût total = {cout_total_interv:.2f} (dont pièces : {total_pieces_cost:.2f})")
                fenetre_intervention.destroy()
                rafraichir_tableau()
                # alerte stock faible après mise à jour
                check_low_stock_and_alert()

            tk.Button(main_frame_i, text="Sauvegarder", command=sauvegarder_intervention, font=("Arial", 10), bg="#4CAF50", fg="white").grid(row=7, column=0, pady=10)
            tk.Button(main_frame_i, text="Annuler", command=fenetre_intervention.destroy, font=("Arial", 10), bg="#f44336", fg="white").grid(row=7, column=1, pady=10)

        def voir_detail_intervention():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez une intervention.")
                return
            vals = tree.item(sel[0], 'values')
            intervention_id = vals[0]
            fen_det = tk.Toplevel(fenetre_historique)
            fen_det.title("Détails de l'intervention")
            fen_det.geometry("700x500")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT date_entree, date_sortie, technicien, cout, details_reparation FROM interventions WHERE id=?", (intervention_id,))
            row = c.fetchone()
            c.execute('''SELECT p.nom, ip.quantite_utilisee, ip.cout_total FROM intervention_pieces ip
                         JOIN pieces p ON ip.piece_id = p.id
                         WHERE ip.intervention_id=?''', (intervention_id,))
            pieces_used = c.fetchall()
            conn.close()
            tk.Label(fen_det, text=f"Date entrée: {row[0]}").pack(anchor="w", padx=10, pady=4)
            tk.Label(fen_det, text=f"Date sortie: {row[1]}").pack(anchor="w", padx=10, pady=4)
            tk.Label(fen_det, text=f"Technicien: {row[2]}").pack(anchor="w", padx=10, pady=4)
            tk.Label(fen_det, text=f"Coût total: {row[3]:.2f}").pack(anchor="w", padx=10, pady=4)
            tk.Label(fen_det, text="Détails:").pack(anchor="w", padx=10, pady=4)
            txt = tk.Text(fen_det, height=6, width=80)
            txt.pack(padx=10, pady=4)
            txt.insert("1.0", row[4] or "")
            txt.config(state=tk.DISABLED)
            tk.Label(fen_det, text="Pièces utilisées:").pack(anchor="w", padx=10, pady=6)
            for p in pieces_used:
                tk.Label(fen_det, text=f"- {p[0]} x{p[1]} (coût: {p[2]:.2f})").pack(anchor="w", padx=20)

        btn_frame = tk.Frame(main_repair_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="➕ Ajouter Intervention", command=ajouter_intervention, font=("Arial", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="👁 Voir Détail", command=voir_detail_intervention, font=("Arial", 10), bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔄 Rafraîchir", command=rafraichir_tableau, font=("Arial", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)

        rafraichir_tableau()

        # Planification (comme avant)
        frame_planif = ttk.Frame(notebook)
        notebook.add(frame_planif, text="Planification Préventive")
        tree_planif = ttk.Treeview(frame_planif, columns=("Date prévue", "Type", "Technicien", "Statut", "Notes"), show="headings", height=15)
        for col in ("Date prévue", "Type", "Technicien", "Statut", "Notes"):
            tree_planif.heading(col, text=col)
            tree_planif.column(col, width=150)
        tree_planif.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar_p = ttk.Scrollbar(frame_planif, orient=tk.VERTICAL, command=tree_planif.yview)
        tree_planif.configure(yscrollcommand=scrollbar_p.set)
        scrollbar_p.pack(side=tk.RIGHT, fill=tk.Y)

        def rafraichir_planif():
            for item in tree_planif.get_children():
                tree_planif.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT id, date_prevue, type_maintenance, technicien, statut, notes 
                         FROM planification WHERE equipement_id=? ORDER BY date_prevue DESC''', (equipement_id,))
            rows = c.fetchall()
            conn.close()
            for r in rows:
                tree_planif.insert("", tk.END, iid=r[0], values=r[1:])

        def ajouter_planif():
            fenetre_planif = tk.Toplevel(fenetre_historique)
            fenetre_planif.title("Nouvelle tâche préventive")
            fenetre_planif.geometry("400x400")
            tk.Label(fenetre_planif, text="Date prévue *:", font=("Arial", 10)).pack(pady=5)
            entry_date = tk.Entry(fenetre_planif)
            entry_date.pack(pady=5)
            entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
            tk.Label(fenetre_planif, text="Type de maintenance:", font=("Arial", 10)).pack(pady=5)
            entry_type = tk.Entry(fenetre_planif)
            entry_type.pack(pady=5)
            tk.Label(fenetre_planif, text="Technicien:", font=("Arial", 10)).pack(pady=5)
            entry_tech = tk.Entry(fenetre_planif)
            entry_tech.pack(pady=5)
            tk.Label(fenetre_planif, text="Statut:", font=("Arial", 10)).pack(pady=5)
            entry_statut = tk.Entry(fenetre_planif)
            entry_statut.pack(pady=5)
            tk.Label(fenetre_planif, text="Notes:", font=("Arial", 10)).pack(pady=5)
            text_notes_p = tk.Text(fenetre_planif, height=4)
            text_notes_p.pack(pady=5)

            def sauvegarder_planif():
                date_p = entry_date.get().strip()
                type_m = entry_type.get().strip()
                tech = entry_tech.get().strip()
                statut = entry_statut.get().strip()
                notes = text_notes_p.get("1.0", tk.END).strip()
                if not date_p:
                    messagebox.showwarning("Attention", "Date prévue obligatoire")
                    return
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''INSERT INTO planification (equipement_id, date_prevue, type_maintenance, technicien, statut, notes)
                             VALUES (?, ?, ?, ?, ?, ?)''', (equipement_id, date_p, type_m, tech, statut, notes))
                conn.commit()
                conn.close()
                messagebox.showinfo("Succès", "Tâche préventive ajoutée")
                fenetre_planif.destroy()
                rafraichir_planif()

            tk.Button(fenetre_planif, text="Sauvegarder", command=sauvegarder_planif, font=("Arial", 10), bg="#4CAF50", fg="white").pack(pady=10)
            tk.Button(fenetre_planif, text="Annuler", command=fenetre_planif.destroy, font=("Arial", 10), bg="#f44336", fg="white").pack(pady=5)

        btn_frame_p = tk.Frame(frame_planif)
        btn_frame_p.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame_p, text="➕ Ajouter Planification", command=ajouter_planif, font=("Arial", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame_p, text="🔄 Rafraîchir", command=rafraichir_planif, font=("Arial", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)

        rafraichir_planif()

    # helper: check low stock and alert
    def check_low_stock_and_alert():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT nom, quantite_stock FROM pieces WHERE quantite_stock <= ?", (LOW_STOCK_THRESHOLD,))
        low = c.fetchall()
        conn.close()
        if low:
            msg = "Attention : pièces proche de la rupture :\n"
            for nom, qte in low:
                msg += f"- {nom} (stock: {qte})\n"
            messagebox.showwarning("Stock faible", msg)

    # --- fenêtre principale ---
    root = tk.Tk()
    root.title("GMAO - Gestion de Maintenance")
    root.geometry("420x260")

    # menu: accès gestion pièces
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)
    stock_menu = tk.Menu(menu_bar, tearoff=0)
    stock_menu.add_command(label="🧾 Gestion des pièces", command=ouvrir_gestion_pieces)
    menu_bar.add_cascade(label="Stock", menu=stock_menu)

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(main_frame, text="Recherche d'Équipement", font=("Arial", 16, "bold")).pack(pady=(0, 12))
    tk.Label(main_frame, text="Numéro de série:", font=("Arial", 12)).pack(pady=5)
    entry_numero = tk.Entry(main_frame, font=("Arial", 12))
    entry_numero.pack(pady=5)
    entry_numero.focus()
    tk.Button(main_frame, text="Rechercher", command=rechercher, font=("Arial", 12), bg="#4CAF50", fg="white").pack(pady=10)

    # Vérifier les rappels à l'ouverture et planifier les suivants
    root.after(500, lambda: verifier_rappels(root))
    # Vérifier stock faible à l'ouverture
    root.after(1000, check_low_stock_and_alert)

    root.mainloop()

# === LANCEMENT ===
if __name__ == "__main__":
    init_db()
    authentification()
