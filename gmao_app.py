import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3
from cryptography.fernet import Fernet
import os
from datetime import datetime, timedelta
import threading
import time

# === Configuration ===
KEY_FILE = 'secret.key'
DB_FILE = 'gmao_encrypted.db'
INITIAL_PASSWORD = 'admin123'
LOW_STOCK_THRESHOLD = 5

# === Encryption Functions ===
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

# === Database Initialization ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Equipment table
    c.execute('''CREATE TABLE IF NOT EXISTS equipements (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero_serie TEXT UNIQUE,
                 marque TEXT,
                 modele TEXT,
                 date_achat TEXT,
                 date_vente TEXT,
                 identifiant_acheteur TEXT,
                 notes TEXT)''')
    
    # Interventions table
    c.execute('''CREATE TABLE IF NOT EXISTS interventions (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 equipement_id INTEGER,
                 date_entree TEXT,
                 date_sortie TEXT,
                 details_reparation TEXT,
                 technicien TEXT,
                 cout REAL,
                 FOREIGN KEY(equipement_id) REFERENCES equipements(id))''')
    
    # Preventive maintenance scheduling
    c.execute('''CREATE TABLE IF NOT EXISTS planification (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 equipement_id INTEGER,
                 date_prevue TEXT,
                 type_maintenance TEXT,
                 technicien TEXT,
                 statut TEXT DEFAULT 'Planifié',
                 notes TEXT,
                 FOREIGN KEY(equipement_id) REFERENCES equipements(id))''')
    
    # Spare parts inventory
    c.execute('''CREATE TABLE IF NOT EXISTS pieces (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nom TEXT,
                 reference TEXT UNIQUE,
                 fournisseur TEXT,
                 prix_unitaire REAL,
                 quantite_stock INTEGER,
                 description TEXT)''')
    
    # Link between interventions and pieces
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

# === Authentication System ===
def authentication():
    def verify_password():
        entered_password = entry_password.get()
        if entered_password == INITIAL_PASSWORD:
            auth_window.destroy()
            open_gmao_interface()
        else:
            messagebox.showerror("Erreur", "Mot de passe incorrect")

    auth_window = tk.Tk()
    auth_window.title("Authentification")
    auth_window.geometry("300x150")
    auth_window.resizable(False, False)
    
    tk.Label(auth_window, text="Mot de passe :", font=("Arial", 12)).pack(pady=10)
    entry_password = tk.Entry(auth_window, show='*', font=("Arial", 12))
    entry_password.pack(pady=5)
    entry_password.focus()
    tk.Button(auth_window, text="Valider", command=verify_password, 
              font=("Arial", 10), bg="#4CAF50", fg="white").pack(pady=10)
    entry_password.bind('<Return>', lambda event: verify_password())
    auth_window.mainloop()

# === Maintenance Reminder System ===
def check_reminders(root):
    def run_check():
        while True:
            try:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                today = datetime.now().date()
                reminder_limit = today + timedelta(days=7)
                
                c.execute('''SELECT e.numero_serie, p.date_prevue, p.type_maintenance 
                             FROM planification p
                             JOIN equipements e ON p.equipement_id = e.id
                             WHERE date_prevue BETWEEN ? AND ? AND statut = 'Planifié' ''', 
                          (str(today), str(reminder_limit)))
                reminders = c.fetchall()
                conn.close()
                
                if reminders:
                    message = "Rappel : Maintenances prévues dans les 7 jours :\n\n"
                    for equipment_serial, date, maintenance_type in reminders:
                        message += f"- Équipement {equipment_serial} : {maintenance_type} prévu le {date}\n"
                    
                    # Show reminder in main thread
                    root.after(0, lambda: messagebox.showinfo("Rappel Maintenance Préventive", message))
            except Exception as e:
                print(f"Error in reminder check: {e}")
            
            # Check once per day
            time.sleep(24 * 60 * 60)
    
    # Start reminder checker in background thread
    reminder_thread = threading.Thread(target=run_check, daemon=True)
    reminder_thread.start()

# === Main GMAO Interface ===
def open_gmao_interface():
    def open_parts_management():
        stock_window = tk.Toplevel(root)
        stock_window.title("📦 Gestion des pièces de rechange")
        stock_window.geometry("1000x600")
        
        # Parts Table
        columns = ("ID", "Nom", "Référence", "Fournisseur", "Prix", "Quantité", "Description")
        tree_parts = ttk.Treeview(stock_window, columns=columns, show="headings", height=18)
        for col in columns:
            tree_parts.heading(col, text=col)
            tree_parts.column(col, width=(50 if col == "ID" else 130))
        tree_parts.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def refresh_stock():
            for item in tree_parts.get_children():
                tree_parts.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, nom, reference, fournisseur, prix_unitaire, quantite_stock, description FROM pieces ORDER BY nom")
            rows = c.fetchall()
            conn.close()
            for row in rows:
                tree_parts.insert("", tk.END, values=row)
        
        def add_part():
            add_window = tk.Toplevel(stock_window)
            add_window.title("Ajouter une pièce")
            add_window.geometry("420x360")
            
            fields = [
                ("Nom *:", "name"),
                ("Référence *:", "ref"),
                ("Fournisseur:", "supplier"),
                ("Prix unitaire:", "price"),
                ("Quantité en stock:", "quantity"),
            ]
            entries = {}
            for i, (label, key) in enumerate(fields):
                tk.Label(add_window, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=6)
                entry = tk.Entry(add_window)
                entry.grid(row=i, column=1, padx=8, pady=6)
                entries[key] = entry
            
            tk.Label(add_window, text="Description:").grid(row=len(fields), column=0, sticky="nw", padx=8, pady=6)
            desc_text = tk.Text(add_window, height=6, width=30)
            desc_text.grid(row=len(fields), column=1, padx=8, pady=6)
            
            def save_part():
                name = entries["name"].get().strip()
                ref = entries["ref"].get().strip()
                supplier = entries["supplier"].get().strip()
                try:
                    price = float(entries["price"].get().strip() or 0)
                    quantity = int(entries["quantity"].get().strip() or 0)
                except ValueError:
                    messagebox.showwarning("Erreur", "Prix ou quantité invalide.")
                    return
                description = desc_text.get("1.0", tk.END).strip()
                
                if not name or not ref:
                    messagebox.showwarning("Attention", "Nom et Référence obligatoires.")
                    return
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute('''INSERT INTO pieces (nom, reference, fournisseur, prix_unitaire, quantite_stock, description)
                                 VALUES (?, ?, ?, ?, ?, ?)''', 
                              (name, ref, supplier, price, quantity, description))
                    conn.commit()
                    messagebox.showinfo("Succès", "Pièce ajoutée avec succès.")
                    add_window.destroy()
                    refresh_stock()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Erreur", "Une pièce avec cette référence existe déjà.")
                finally:
                    conn.close()
            
            tk.Button(add_window, text="Sauvegarder", bg="#4CAF50", fg="white", command=save_part).grid(row=10, column=0, pady=10, padx=8)
            tk.Button(add_window, text="Annuler", bg="#f44336", fg="white", command=add_window.destroy).grid(row=10, column=1, pady=10, padx=8)
        
        def edit_part():
            selected = tree_parts.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une pièce à modifier.")
                return
            
            values = tree_parts.item(selected[0], 'values')
            part_id = values[0]
            
            edit_window = tk.Toplevel(stock_window)
            edit_window.title("Modifier une pièce")
            edit_window.geometry("420x360")
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT nom, reference, fournisseur, prix_unitaire, quantite_stock, description FROM pieces WHERE id=?", (part_id,))
            row = c.fetchone()
            conn.close()
            
            fields = [("Nom:", row[0]), ("Référence:", row[1]), ("Fournisseur:", row[2]), 
                      ("Prix unitaire:", row[3]), ("Quantité:", row[4])]
            entries = {}
            for i, (label, value) in enumerate(fields):
                tk.Label(edit_window, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=6)
                entry = tk.Entry(edit_window)
                entry.grid(row=i, column=1, padx=8, pady=6)
                entry.insert(0, str(value))
                entries[i] = entry
            
            tk.Label(edit_window, text="Description:").grid(row=len(fields), column=0, sticky="nw", padx=8, pady=6)
            desc_text = tk.Text(edit_window, height=6, width=30)
            desc_text.grid(row=len(fields), column=1, padx=8, pady=6)
            desc_text.insert("1.0", row[5] or "")
            
            def save_edits():
                name = entries[0].get().strip()
                reference = entries[1].get().strip()
                supplier = entries[2].get().strip()
                try:
                    price = float(entries[3].get().strip() or 0)
                    quantity = int(entries[4].get().strip() or 0)
                except ValueError:
                    messagebox.showwarning("Erreur", "Prix ou quantité invalide.")
                    return
                description = desc_text.get("1.0", tk.END).strip()
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute('''UPDATE pieces SET nom=?, reference=?, fournisseur=?, prix_unitaire=?, quantite_stock=?, description=? WHERE id=?''',
                              (name, reference, supplier, price, quantity, description, part_id))
                    conn.commit()
                    messagebox.showinfo("Succès", "Pièce modifiée avec succès.")
                    edit_window.destroy()
                    refresh_stock()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Erreur", "Un conflit est survenu lors de la modification.")
                finally:
                    conn.close()
            
            tk.Button(edit_window, text="Sauvegarder", bg="#4CAF50", fg="white", command=save_edits).grid(row=12, column=0, pady=10, padx=8)
            tk.Button(edit_window, text="Annuler", bg="#f44336", fg="white", command=edit_window.destroy).grid(row=12, column=1, pady=10, padx=8)
        
        def delete_part():
            selected = tree_parts.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une pièce à supprimer.")
                return
            
            values = tree_parts.item(selected[0], 'values')
            part_name = values[1]
            
            if not messagebox.askyesno("Confirmation", f"Voulez-vous vraiment supprimer la pièce '{part_name}' ?"):
                return
            
            part_id = values[0]
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM pieces WHERE id=?", (part_id,))
            conn.commit()
            conn.close()
            refresh_stock()
            messagebox.showinfo("Succès", "Pièce supprimée avec succès.")
        
        def check_low_stock():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT nom, quantite_stock FROM pieces WHERE quantite_stock <= ?", (LOW_STOCK_THRESHOLD,))
            low_stock_items = c.fetchall()
            conn.close()
            
            if low_stock_items:
                message = "ALERTE STOCK FAIBLE :\n\n"
                for name, quantity in low_stock_items:
                    message += f"- {name} (stock: {quantity})\n"
                messagebox.showwarning("Stock Faible", message)
            else:
                messagebox.showinfo("Stock", "Tous les articles ont un niveau de stock suffisant.")
        
        # Action buttons
        button_frame = tk.Frame(stock_window)
        button_frame.pack(fill=tk.X, pady=6)
        tk.Button(button_frame, text="➕ Ajouter une pièce", command=add_part, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=6)
        tk.Button(button_frame, text="✏️ Modifier", command=edit_part, bg="#FFC107").pack(side=tk.LEFT, padx=6)
        tk.Button(button_frame, text="🗑 Supprimer", command=delete_part, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=6)
        tk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_stock, bg="#FF9800").pack(side=tk.LEFT, padx=6)
        tk.Button(button_frame, text="🔔 Vérifier stock faible", command=check_low_stock, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=6)
        
        refresh_stock()
        check_low_stock()  # Initial check
    
    # Main search functionality
    def search_equipment():
        serial_number = entry_serial.get().strip()
        if not serial_number:
            messagebox.showwarning("Attention", "Veuillez saisir un numéro de série")
            return
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM equipements WHERE numero_serie=?", (serial_number,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            create_equipment_form(serial_number)
        else:
            show_equipment_history(result[0], serial_number)
    
    def create_equipment_form(serial_number):
        def save_equipment():
            brand = entry_brand.get().strip()
            model = entry_model.get().strip()
            purchase_date = entry_purchase_date.get().strip()
            sale_date = entry_sale_date.get().strip()
            buyer_id = entry_buyer.get().strip()
            notes = text_notes.get("1.0", tk.END).strip()
            
            if not brand or not model:
                messagebox.showwarning("Attention", "Marque et Modèle sont obligatoires")
                return
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO equipements 
                          (numero_serie, marque, modele, date_achat, date_vente, identifiant_acheteur, notes) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (serial_number, brand, model, purchase_date, sale_date, buyer_id, notes))
                conn.commit()
                messagebox.showinfo("Succès", "Équipement enregistré avec succès!")
                form_window.destroy()
                c.execute("SELECT id FROM equipements WHERE numero_serie=?", (serial_number,))
                equipement_id = c.fetchone()[0]
                show_equipment_history(equipement_id, serial_number)
            except sqlite3.IntegrityError:
                messagebox.showerror("Erreur", "Numéro de série déjà existant")
            finally:
                conn.close()
        
        form_window = tk.Toplevel(root)
        form_window.title(f"Nouvel Équipement - {serial_number}")
        form_window.geometry("500x600")
        
        main_frame = tk.Frame(form_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Informations de l'Équipement", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        tk.Label(main_frame, text="Marque *:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
        entry_brand = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_brand.grid(row=1, column=1, sticky="ew", pady=5)
        
        tk.Label(main_frame, text="Modèle *:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
        entry_model = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_model.grid(row=2, column=1, sticky="ew", pady=5)
        
        tk.Label(main_frame, text="Date d'achat:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=5)
        entry_purchase_date = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_purchase_date.grid(row=3, column=1, sticky="ew", pady=5)
        entry_purchase_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        tk.Label(main_frame, text="Date de vente:", font=("Arial", 10)).grid(row=4, column=0, sticky="w", pady=5)
        entry_sale_date = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_sale_date.grid(row=4, column=1, sticky="ew", pady=5)
        
        tk.Label(main_frame, text="Identifiant Acheteur:", font=("Arial", 10)).grid(row=5, column=0, sticky="w", pady=5)
        entry_buyer = tk.Entry(main_frame, font=("Arial", 10), width=30)
        entry_buyer.grid(row=5, column=1, sticky="ew", pady=5)
        
        tk.Label(main_frame, text="Notes:", font=("Arial", 10)).grid(row=6, column=0, sticky="nw", pady=5)
        text_notes = tk.Text(main_frame, font=("Arial", 10), width=30, height=8)
        text_notes.grid(row=6, column=1, sticky="ew", pady=5)
        
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        tk.Button(button_frame, text="Sauvegarder", command=save_equipment, 
                  font=("Arial", 10), bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Annuler", command=form_window.destroy, 
                  font=("Arial", 10), bg="#f44336", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        entry_brand.focus()
    
    # Maintenance history display
    def show_equipment_history(equipment_id, serial_number):
        history_window = tk.Toplevel(root)
        history_window.title(f"Historique - {serial_number}")
        history_window.geometry("1100x700")
        
        notebook = ttk.Notebook(history_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Equipment Info Tab
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Informations Équipement")
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM equipements WHERE id=?", (equipment_id,))
        equipment = c.fetchone()
        conn.close()
        
        details_frame = tk.Frame(info_frame, padx=20, pady=20)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        info_labels = [
            ("Numéro de série:", equipment[1]),
            ("Marque:", equipment[2]),
            ("Modèle:", equipment[3]),
            ("Date d'achat:", equipment[4]),
            ("Date de vente:", equipment[5]),
            ("Identifiant Acheteur:", equipment[6]),
            ("Notes:", equipment[7])
        ]
        for i, (label, value) in enumerate(info_labels):
            tk.Label(details_frame, text=label, font=("Arial", 10, "bold"), anchor="w").grid(row=i, column=0, sticky="w", pady=5)
            tk.Label(details_frame, text=value or "Non renseigné", font=("Arial", 10), anchor="w").grid(row=i, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Repair History Tab
        repairs_frame = ttk.Frame(notebook)
        notebook.add(repairs_frame, text="Historique des Réparations")
        
        main_repairs_frame = tk.Frame(repairs_frame)
        main_repairs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("ID", "Date Entrée", "Date Sortie", "Technicien", "Coût", "Détails")
        tree = ttk.Treeview(main_repairs_frame, columns=columns, show="headings", height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=(60 if col == "ID" else 140))
        tree.column("Détails", width=260)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(main_repairs_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def refresh_interventions():
            for item in tree.get_children():
                tree.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT id, date_entree, date_sortie, technicien, cout, details_reparation 
                         FROM interventions WHERE equipement_id=? ORDER BY date_entree DESC''', (equipment_id,))
            interventions = c.fetchall()
            conn.close()
            for intervention in interventions:
                tree.insert("", tk.END, values=intervention)
        
        # Temporary pieces storage for new interventions
        selected_pieces = []  # List of dicts: {'piece_id':.., 'name':.., 'price':.., 'qty':.., 'total_cost':..}
        
        def manage_used_pieces(parent_window):
            """Opens window for selecting pieces and quantities.
               Stores selections in selected_pieces list."""
            nonlocal selected_pieces
            pieces_window = tk.Toplevel(parent_window)
            pieces_window.title("Associer des pièces à l'intervention")
            pieces_window.geometry("900x500")
            
            # Left: Available pieces
            left_frame = tk.Frame(pieces_window)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            
            cols = ("ID", "Nom", "Réf", "Prix", "Stock")
            tree_left = ttk.Treeview(left_frame, columns=cols, show="headings", height=15)
            for col in cols:
                tree_left.heading(col, text=col)
                tree_left.column(col, width=(50 if col == "ID" else 120))
            tree_left.pack(fill=tk.BOTH, expand=True)
            
            scroll_left = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=tree_left.yview)
            tree_left.configure(yscrollcommand=scroll_left.set)
            scroll_left.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Right: Selected pieces
            right_frame = tk.Frame(pieces_window)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            
            cols2 = ("Piece ID", "Nom", "Quantité", "Prix unitaire", "Coût total")
            tree_right = ttk.Treeview(right_frame, columns=cols2, show="headings", height=15)
            for col in cols2:
                tree_right.heading(col, text=col)
                tree_right.column(col, width=(80 if col == "Piece ID" else 110))
            tree_right.pack(fill=tk.BOTH, expand=True)
            
            scroll_right = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_right.yview)
            tree_right.configure(yscrollcommand=scroll_right.set)
            scroll_right.pack(side=tk.RIGHT, fill=tk.Y)
            
            def load_pieces_list():
                for item in tree_left.get_children():
                    tree_left.delete(item)
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT id, nom, reference, prix_unitaire, quantite_stock FROM pieces ORDER BY nom")
                rows = c.fetchall()
                conn.close()
                for row in rows:
                    tree_left.insert("", tk.END, values=row)
            
            load_pieces_list()
            
            def select_for_intervention():
                selected = tree_left.selection()
                if not selected:
                    messagebox.showwarning("Attention", "Sélectionnez une pièce à ajouter")
                    return
                values = tree_left.item(selected[0], 'values')
                piece_id, name, ref, price, stock = values
                
                quantity_str = simpledialog.askstring("Quantité", 
                                                      f"Quantité à utiliser pour '{name}' (stock {stock}) :", 
                                                      parent=pieces_window)
                if not quantity_str:
                    return
                
                try:
                    quantity = int(quantity_str)
                    if quantity <= 0:
                        raise ValueError("Quantité doit être positive")
                    if quantity > int(stock):
                        messagebox.showwarning("Stock insuffisant", 
                                              f"Stock disponible: {stock}")
                        return
                except ValueError:
                    messagebox.showwarning("Erreur", "Veuillez entrer un nombre valide")
                    return
                
                # Check if piece already selected
                for item in tree_right.get_children():
                    item_values = tree_right.item(item, 'values')
                    if int(item_values[0]) == int(piece_id):
                        messagebox.showwarning("Doublon", 
                                              f"Pièce '{name}' déjà sélectionnée")
                        return
                
                # Add to selected pieces
                total_cost = quantity * float(price)
                tree_right.insert("", tk.END, values=(piece_id, name, quantity, price, f"{total_cost:.2f}"))
                
                # Store in selected_pieces list
                selected_pieces.append({
                    'piece_id': int(piece_id),
                    'name': name,
                    'price': float(price),
                    'qty': quantity,
                    'total_cost': total_cost
                })
            
            def remove_from_intervention():
                selected = tree_right.selection()
                if not selected:
                    messagebox.showwarning("Attention", "Sélectionnez une pièce à retirer")
                    return
                
                # Remove from tree
                values = tree_right.item(selected[0], 'values')
                piece_id = int(values[0])
                tree_right.delete(selected[0])
                
                # Remove from selected_pieces list (CORRECTION: PAS de restauration automatique du stock)
                nonlocal selected_pieces
                selected_pieces = [p for p in selected_pieces if p['piece_id'] != piece_id]
                # Refresh stock in left panel
                load_pieces_list()
            
            def validate_selection():
                # Validate all pieces have sufficient stock
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                valid = True
                
                for piece in selected_pieces:
                    c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (piece['piece_id'],))
                    stock = c.fetchone()[0]
                    if piece['qty'] > stock:
                        messagebox.showerror("Stock insuffisant", 
                                           f"Stock insuffisant pour '{piece['name']}'")
                        valid = False
                        break
                
                conn.close()
                
                if valid:
                    pieces_window.destroy()
            
            def refresh_pieces_display():
                """Refresh both panels with updated data"""
                load_pieces_list()
                
                # Refresh right panel (selected pieces) to maintain consistency
                for item in tree_right.get_children():
                    tree_right.delete(item)
                for piece in selected_pieces:
                    tree_right.insert("", tk.END, values=(
                        piece['piece_id'], piece['name'], piece['qty'], 
                        f"{piece['price']:.2f}", f"{piece['total_cost']:.2f}"
                    ))
            
            # Buttons
            button_frame = tk.Frame(pieces_window)
            button_frame.pack(fill=tk.X, pady=10)
            
            tk.Button(button_frame, text="→ Ajouter", command=select_for_intervention, 
                     bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)
            tk.Button(button_frame, text="← Retirer", command=remove_from_intervention, 
                     bg="#f44336", fg="white").pack(side=tk.LEFT, padx=10)
            tk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_pieces_display, 
                     bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=10)
            tk.Button(button_frame, text="Valider", command=validate_selection, 
                     bg="#2196F3", fg="white").pack(side=tk.RIGHT, padx=10)
            
            # Initially load pieces
            load_pieces_list()
        
        def view_intervention_details():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une intervention pour voir les détails")
                return
            
            values = tree.item(selected[0], 'values')
            intervention_id = values[0]
            
            details_window = tk.Toplevel(history_window)
            details_window.title(f"Détails de l'intervention #{intervention_id}")
            details_window.geometry("700x500")
            
            # Load intervention data
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT date_entree, date_sortie, technicien, cout, details_reparation 
                         FROM interventions WHERE id=?''', (intervention_id,))
            intervention = c.fetchone()
            
            # Load associated pieces
            c.execute('''SELECT p.nom, ip.quantite_utilisee, p.prix_unitaire, ip.cout_total
                         FROM intervention_pieces ip
                         JOIN pieces p ON ip.piece_id = p.id
                         WHERE ip.intervention_id=?''', (intervention_id,))
            pieces = c.fetchall()
            conn.close()
            
            # Display intervention details
            tk.Label(details_window, text=f"Intervention #{intervention_id}", 
                     font=("Arial", 14, "bold")).pack(pady=10)
            
            details_frame = tk.Frame(details_window)
            details_frame.pack(fill=tk.BOTH, expand=True, padx=20)
            
            # Basic info
            basic_info = [
                ("Date d'entrée:", intervention[0]),
                ("Date de sortie:", intervention[1] or "N/A"),
                ("Technicien:", intervention[2] or "N/A"),
                ("Coût total:", f"{intervention[3]:.2f} €")
            ]
            
            for i, (label, value) in enumerate(basic_info):
                tk.Label(details_frame, text=label, font=("Arial", 10, "bold")).grid(row=i, column=0, sticky="w", pady=3)
                tk.Label(details_frame, text=value, font=("Arial", 10)).grid(row=i, column=1, sticky="w", pady=3, padx=(10, 0))
            
            # Details section
            tk.Label(details_frame, text="Détails:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="nw", pady=(15, 3))
            details_text = tk.Text(details_frame, font=("Arial", 10), width=50, height=6, wrap=tk.WORD)
            details_text.grid(row=4, column=1, pady=(15, 3), padx=(10, 0))
            details_text.insert("1.0", intervention[4] or "")
            details_text.config(state=tk.DISABLED)
            
            # Pieces section
            if pieces:
                tk.Label(details_frame, text="Pièces utilisées:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="w", pady=(15, 3))
                
                # Pieces table
                pieces_cols = ("Nom", "Quantité", "Prix unitaire", "Coût total")
                pieces_tree = ttk.Treeview(details_frame, columns=pieces_cols, show="headings", height=6)
                for col in pieces_cols:
                    pieces_tree.heading(col, text=col)
                    pieces_tree.column(col, width=120)
                pieces_tree.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))
                
                for piece in pieces:
                    pieces_tree.insert("", tk.END, values=piece)
            
            details_frame.columnconfigure(1, weight=1)
        
        def add_intervention():
            nonlocal selected_pieces
            selected_pieces = []  # Reset selections
            
            add_window = tk.Toplevel(history_window)
            add_window.title("Ajouter une intervention")
            add_window.geometry("500x500")
            
            # Form fields
            tk.Label(add_window, text="Date d'entrée *:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            entry_date_in = tk.Entry(add_window, font=("Arial", 10))
            entry_date_in.grid(row=0, column=1, padx=10, pady=5)
            entry_date_in.insert(0, datetime.now().strftime("%Y-%m-%d"))
            
            tk.Label(add_window, text="Date de sortie:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
            entry_date_out = tk.Entry(add_window, font=("Arial", 10))
            entry_date_out.grid(row=1, column=1, padx=10, pady=5)
            
            tk.Label(add_window, text="Technicien:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
            entry_technician = tk.Entry(add_window, font=("Arial", 10))
            entry_technician.grid(row=2, column=1, padx=10, pady=5)
            
            tk.Label(add_window, text="Coût:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=10, pady=5)
            entry_cost = tk.Entry(add_window, font=("Arial", 10))
            entry_cost.grid(row=3, column=1, padx=10, pady=5)
            
            tk.Label(add_window, text="Détails:", font=("Arial", 10)).grid(row=4, column=0, sticky="nw", padx=10, pady=5)
            text_details = tk.Text(add_window, font=("Arial", 10), width=30, height=6)
            text_details.grid(row=4, column=1, padx=10, pady=5)
            
            def save_intervention():
                date_in = entry_date_in.get().strip()
                date_out = entry_date_out.get().strip()
                technician = entry_technician.get().strip()
                cost_str = entry_cost.get().strip()
                details = text_details.get("1.0", tk.END).strip()
                
                # Validate required fields
                if not date_in:
                    messagebox.showwarning("Attention", "Date d'entrée obligatoire")
                    return
                
                try:
                    cost = float(cost_str) if cost_str else 0.0
                except ValueError:
                    messagebox.showwarning("Erreur", "Coût invalide")
                    return
                
                # Validate dates
                try:
                    datetime.strptime(date_in, "%Y-%m-%d")
                    if date_out:
                        datetime.strptime(date_out, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("Erreur", "Format de date invalide (YYYY-MM-DD)")
                    return
                
                # Save intervention to database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''INSERT INTO interventions 
                          (equipement_id, date_entree, date_sortie, details_reparation, technicien, cout) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                          (equipment_id, date_in, date_out, details, technician, cost))
                intervention_id = c.lastrowid
                conn.commit()
                
                # Save pieces usage if any
                total_pieces_cost = 0
                if selected_pieces:
                    for piece in selected_pieces:
                        # Save piece usage
                        c.execute('''INSERT INTO intervention_pieces 
                                  (intervention_id, piece_id, quantite_utilisee, cout_total) 
                                  VALUES (?, ?, ?, ?)''',
                                  (intervention_id, piece['piece_id'], piece['qty'], piece['total_cost']))
                        
                        # Update stock
                        c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (piece['piece_id'],))
                        current_stock = c.fetchone()[0]
                        new_stock = current_stock - piece['qty']
                        c.execute("UPDATE pieces SET quantite_stock=? WHERE id=?", 
                                 (new_stock, piece['piece_id']))
                    
                    # Update intervention cost
                    total_cost = cost + total_pieces_cost
                    c.execute("UPDATE interventions SET cout=? WHERE id=?", (total_cost, intervention_id))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", "Intervention enregistrée avec succès!")
                add_window.destroy()
                refresh_interventions()
            
            # Buttons
            button_frame = tk.Frame(add_window)
            button_frame.grid(row=5, column=0, columnspan=2, pady=20)
            
            tk.Button(button_frame, text="Sélectionner pièces", 
                     command=lambda: manage_used_pieces(add_window), 
                     bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Sauvegarder", 
                     command=save_intervention, 
                     bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Annuler", 
                     command=add_window.destroy, 
                     bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        
        def edit_intervention():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une intervention à modifier")
                return
            
            values = tree.item(selected[0], 'values')
            intervention_id = values[0]
            
            edit_window = tk.Toplevel(history_window)
            edit_window.title("Modifier une intervention")
            edit_window.geometry("500x500")
            
            # Load intervention data
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT date_entree, date_sortie, technicien, cout, details_reparation 
                         FROM interventions WHERE id=?''', (intervention_id,))
            intervention = c.fetchone()
            
            # Load original piece associations
            c.execute('''SELECT ip.piece_id, p.nom, ip.quantite_utilisee, p.prix_unitaire, ip.cout_total
                         FROM intervention_pieces ip
                         JOIN pieces p ON ip.piece_id = p.id
                         WHERE ip.intervention_id=?''', (intervention_id,))
            original_pieces = c.fetchall()
            conn.close()
            
            # CORRECTION: NE PAS restaurer automatiquement le stock au début
            # Le stock sera géré uniquement lors de la sauvegarde
            
            # Form fields
            tk.Label(edit_window, text="Date d'entrée *:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            entry_date_in = tk.Entry(edit_window, font=("Arial", 10))
            entry_date_in.grid(row=0, column=1, padx=10, pady=5)
            entry_date_in.insert(0, intervention[0] or "")
            
            tk.Label(edit_window, text="Date de sortie:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
            entry_date_out = tk.Entry(edit_window, font=("Arial", 10))
            entry_date_out.grid(row=1, column=1, padx=10, pady=5)
            entry_date_out.insert(0, intervention[1] or "")
            
            tk.Label(edit_window, text="Technicien:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
            entry_technician = tk.Entry(edit_window, font=("Arial", 10))
            entry_technician.grid(row=2, column=1, padx=10, pady=5)
            entry_technician.insert(0, intervention[2] or "")
            
            tk.Label(edit_window, text="Coût:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=10, pady=5)
            entry_cost = tk.Entry(edit_window, font=("Arial", 10))
            entry_cost.grid(row=3, column=1, padx=10, pady=5)
            entry_cost.insert(0, intervention[3] or "")
            
            tk.Label(edit_window, text="Détails:", font=("Arial", 10)).grid(row=4, column=0, sticky="nw", padx=10, pady=5)
            text_details = tk.Text(edit_window, font=("Arial", 10), width=30, height=6)
            text_details.grid(row=4, column=1, padx=10, pady=5)
            text_details.insert("1.0", intervention[4] or "")
            
            # Initialize selected_pieces with original pieces
            selected_pieces = []
            for piece in original_pieces:
                piece_dict = {
                    'piece_id': piece[0],
                    'name': piece[1],
                    'qty': piece[2],
                    'price': piece[3],
                    'total_cost': piece[4]
                }
                selected_pieces.append(piece_dict)
            
            def save_edits():
                date_in = entry_date_in.get().strip()
                date_out = entry_date_out.get().strip()
                technician = entry_technician.get().strip()
                cost_str = entry_cost.get().strip()
                details = text_details.get("1.0", tk.END).strip()
                
                # Validate required fields
                if not date_in:
                    messagebox.showwarning("Attention", "Date d'entrée obligatoire")
                    return
                
                try:
                    cost = float(cost_str) if cost_str else 0.0
                except ValueError:
                    messagebox.showwarning("Erreur", "Coût invalide")
                    return
                
                # Validate dates
                try:
                    datetime.strptime(date_in, "%Y-%m-%d")
                    if date_out:
                        datetime.strptime(date_out, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("Erreur", "Format de date invalide (YYYY-MM-DD)")
                    return
                
                # Save intervention changes to database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                
                # CORRECTION: Gérer le stock correctement
                # 1. Restaurer le stock des pièces originales
                for piece in original_pieces:
                    c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (piece[0],))
                    current_stock = c.fetchone()[0]
                    new_stock = current_stock + piece[2]  # Ajouter la quantité utilisée
                    c.execute("UPDATE pieces SET quantite_stock=? WHERE id=?", (new_stock, piece[0]))
                
                # 2. Supprimer les associations originales
                c.execute("DELETE FROM intervention_pieces WHERE intervention_id=?", (intervention_id,))
                
                # Update intervention
                c.execute('''UPDATE interventions SET 
                          date_entree=?, date_sortie=?, details_reparation=?, technicien=?, cout=? 
                          WHERE id=?''',
                          (date_in, date_out, details, technician, cost, intervention_id))
                
                # Save pieces usage if any
                total_pieces_cost = 0
                if selected_pieces:
                    for piece in selected_pieces:
                        # Save piece usage
                        c.execute('''INSERT INTO intervention_pieces 
                                  (intervention_id, piece_id, quantite_utilisee, cout_total) 
                                  VALUES (?, ?, ?, ?)''',
                                  (intervention_id, piece['piece_id'], piece['qty'], piece['total_cost']))
                        
                        # Deduct stock
                        c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (piece['piece_id'],))
                        current_stock = c.fetchone()[0]
                        new_stock = current_stock - piece['qty']
                        c.execute("UPDATE pieces SET quantite_stock=? WHERE id=?", 
                                 (new_stock, piece['piece_id']))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", "Intervention modifiée avec succès!")
                edit_window.destroy()
                refresh_interventions()
            
            def manage_pieces():
                def manage_used_pieces_edit(parent_window):
                    pieces_window = tk.Toplevel(parent_window)
                    pieces_window.title("Gérer les pièces utilisées")
                    pieces_window.geometry("900x500")
                    
                    # Left: All available pieces
                    left_frame = tk.Frame(pieces_window)
                    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
                    
                    cols = ("ID", "Nom", "Réf", "Prix", "Stock")
                    tree_left = ttk.Treeview(left_frame, columns=cols, show="headings", height=15)
                    for col in cols:
                        tree_left.heading(col, text=col)
                        tree_left.column(col, width=(50 if col == "ID" else 120))
                    tree_left.pack(fill=tk.BOTH, expand=True)
                    
                    scroll_left = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=tree_left.yview)
                    tree_left.configure(yscrollcommand=scroll_left.set)
                    scroll_left.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    # Right: Currently selected pieces
                    right_frame = tk.Frame(pieces_window)
                    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)
                    
                    cols2 = ("Piece ID", "Nom", "Quantité", "Prix unitaire", "Coût total")
                    tree_right = ttk.Treeview(right_frame, columns=cols2, show="headings", height=15)
                    for col in cols2:
                        tree_right.heading(col, text=col)
                        tree_right.column(col, width=(80 if col == "Piece ID" else 110))
                    tree_right.pack(fill=tk.BOTH, expand=True)
                    
                    scroll_right = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_right.yview)
                    tree_right.configure(yscrollcommand=scroll_right.set)
                    scroll_right.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    def load_all_pieces():
                        for item in tree_left.get_children():
                            tree_left.delete(item)
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT id, nom, reference, prix_unitaire, quantite_stock FROM pieces ORDER BY nom")
                        rows = c.fetchall()
                        conn.close()
                        for row in rows:
                            tree_left.insert("", tk.END, values=row)
                    
                    def load_selected_pieces():
                        for item in tree_right.get_children():
                            tree_right.delete(item)
                        for piece in selected_pieces:
                            tree_right.insert("", tk.END, values=(
                                piece['piece_id'], piece['name'], piece['qty'], 
                                f"{piece['price']:.2f}", f"{piece['total_cost']:.2f}"
                            ))
                    
                    def add_piece():
                        selected = tree_left.selection()
                        if not selected:
                            messagebox.showwarning("Attention", "Sélectionnez une pièce à ajouter")
                            return
                        values = tree_left.item(selected[0], 'values')
                        piece_id, name, ref, price, stock = values
                        
                        quantity_str = simpledialog.askstring("Quantité", 
                                                              f"Quantité à utiliser pour '{name}' (stock {stock}) :", 
                                                              parent=pieces_window)
                        if not quantity_str:
                            return
                        
                        try:
                            quantity = int(quantity_str)
                            if quantity <= 0:
                                raise ValueError("Quantité doit être positive")
                            if quantity > int(stock):
                                messagebox.showwarning("Stock insuffisant", 
                                                      f"Stock disponible: {stock}")
                                return
                        except ValueError:
                            messagebox.showwarning("Erreur", "Veuillez entrer un nombre valide")
                            return
                        
                        # Check if piece already selected
                        for item in tree_right.get_children():
                            item_values = tree_right.item(item, 'values')
                            if int(item_values[0]) == int(piece_id):
                                messagebox.showwarning("Doublon", 
                                                      f"Pièce '{name}' déjà sélectionnée")
                                return
                        
                        # Add to selected pieces
                        total_cost = quantity * float(price)
                        tree_right.insert("", tk.END, values=(piece_id, name, quantity, price, f"{total_cost:.2f}"))
                        
                        # Update selected_pieces list
                        nonlocal selected_pieces
                        selected_pieces.append({
                            'piece_id': int(piece_id),
                            'name': name,
                            'price': float(price),
                            'qty': quantity,
                            'total_cost': total_cost
                        })
                    
                    def remove_piece():
                        selected = tree_right.selection()
                        if not selected:
                            messagebox.showwarning("Attention", "Sélectionnez une pièce à retirer")
                            return
                        
                        # Remove from tree
                        values = tree_right.item(selected[0], 'values')
                        piece_id = int(values[0])
                        tree_right.delete(selected[0])
                        
                        # Remove from selected_pieces list (CORRECTION: PAS de restauration automatique)
                        nonlocal selected_pieces
                        selected_pieces = [p for p in selected_pieces if p['piece_id'] != piece_id]
                        
                        # Refresh available pieces list
                        load_all_pieces()
                    
                    def save_selection():
                        pieces_window.destroy()
                        
                    def refresh_pieces_display():
                        """Refresh both panels with updated data"""
                        load_all_pieces()
                        
                        # Refresh right panel (selected pieces) to maintain consistency
                        for item in tree_right.get_children():
                            tree_right.delete(item)
                        for piece in selected_pieces:
                            tree_right.insert("", tk.END, values=(
                                piece['piece_id'], piece['name'], piece['qty'], 
                                f"{piece['price']:.2f}", f"{piece['total_cost']:.2f}"
                            ))
                    
                    # Buttons
                    button_frame = tk.Frame(pieces_window)
                    button_frame.pack(fill=tk.X, pady=10)
                    
                    tk.Button(button_frame, text="→ Ajouter", command=add_piece, 
                             bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)
                    tk.Button(button_frame, text="← Retirer", command=remove_piece, 
                             bg="#f44336", fg="white").pack(side=tk.LEFT, padx=10)
                    tk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_pieces_display, 
                             bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=10)
                    tk.Button(button_frame, text="Valider", command=save_selection, 
                             bg="#2196F3", fg="white").pack(side=tk.RIGHT, padx=10)
                    
                    # Load data
                    load_all_pieces()
                    load_selected_pieces()
                
                manage_used_pieces_edit(edit_window)
            
            # Buttons
            button_frame = tk.Frame(edit_window)
            button_frame.grid(row=5, column=0, columnspan=2, pady=20)
            
            tk.Button(button_frame, text="Gérer les pièces", 
                     command=manage_pieces, 
                     bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Sauvegarder", 
                     command=save_edits, 
                     bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Annuler", 
                     command=edit_window.destroy, 
                     bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        
        def delete_intervention():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une intervention à supprimer")
                return
            
            if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette intervention ?"):
                return
            
            values = tree.item(selected[0], 'values')
            intervention_id = values[0]
            
            # Restore stock for all pieces in this intervention
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            
            # Get used pieces
            c.execute("SELECT piece_id, quantite_utilisee FROM intervention_pieces WHERE intervention_id=?", (intervention_id,))
            used_pieces = c.fetchall()
            
            # Restore stock for each piece
            for piece_id, quantity in used_pieces:
                c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (piece_id,))
                current_stock = c.fetchone()[0]
                new_stock = current_stock + quantity
                c.execute("UPDATE pieces SET quantite_stock=? WHERE id=?", (new_stock, piece_id))
            
            # Delete intervention and associated pieces
            c.execute("DELETE FROM intervention_pieces WHERE intervention_id=?", (intervention_id,))
            c.execute("DELETE FROM interventions WHERE id=?", (intervention_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Succès", "Intervention supprimée avec succès!")
            refresh_interventions()
        
        # Buttons for interventions
        btn_frame = tk.Frame(repairs_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="➕ Ajouter Intervention", command=add_intervention, 
                 bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✏️ Modifier", command=edit_intervention, 
                 bg="#FFC107").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="👁 Voir Détails", command=view_intervention_details, 
                 bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑 Supprimer", command=delete_intervention, 
                 bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔄 Rafraîchir", command=refresh_interventions, 
                 bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        
        refresh_interventions()
        
        # Preventive Maintenance Tab
        maintenance_frame = ttk.Frame(notebook)
        notebook.add(maintenance_frame, text="Maintenance Préventive")
        
        main_maint_frame = tk.Frame(maintenance_frame)
        main_maint_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        maint_columns = ("ID", "Date Prévue", "Type", "Technicien", "Statut", "Notes")
        tree_maint = ttk.Treeview(main_maint_frame, columns=maint_columns, show="headings", height=12)
        for col in maint_columns:
            tree_maint.heading(col, text=col)
            tree_maint.column(col, width=(60 if col == "ID" else 140))
        tree_maint.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        maint_scrollbar = ttk.Scrollbar(main_maint_frame, orient=tk.VERTICAL, command=tree_maint.yview)
        tree_maint.configure(yscrollcommand=maint_scrollbar.set)
        maint_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def refresh_maintenance():
            for item in tree_maint.get_children():
                tree_maint.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT id, date_prevue, type_maintenance, technicien, statut, notes 
                         FROM planification WHERE equipement_id=? ORDER BY date_prevue''', (equipment_id,))
            maintenances = c.fetchall()
            conn.close()
            for maintenance in maintenances:
                tree_maint.insert("", tk.END, values=maintenance)
        
        def add_maintenance():
            add_maint_window = tk.Toplevel(history_window)
            add_maint_window.title("Planifier une maintenance")
            add_maint_window.geometry("450x400")
            
            tk.Label(add_maint_window, text="Date prévue *:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            entry_date = tk.Entry(add_maint_window, font=("Arial", 10))
            entry_date.grid(row=0, column=1, padx=10, pady=5)
            entry_date.insert(0, (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))
            
            tk.Label(add_maint_window, text="Type de maintenance *:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
            entry_type = tk.Entry(add_maint_window, font=("Arial", 10))
            entry_type.grid(row=1, column=1, padx=10, pady=5)
            
            tk.Label(add_maint_window, text="Technicien:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
            entry_tech = tk.Entry(add_maint_window, font=("Arial", 10))
            entry_tech.grid(row=2, column=1, padx=10, pady=5)
            
            tk.Label(add_maint_window, text="Statut:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=10, pady=5)
            combo_status = ttk.Combobox(add_maint_window, values=["Planifié", "En cours", "Terminé"], state="readonly")
            combo_status.grid(row=3, column=1, padx=10, pady=5)
            combo_status.set("Planifié")
            
            tk.Label(add_maint_window, text="Notes:", font=("Arial", 10)).grid(row=4, column=0, sticky="nw", padx=10, pady=5)
            text_notes = tk.Text(add_maint_window, font=("Arial", 10), width=30, height=6)
            text_notes.grid(row=4, column=1, padx=10, pady=5)
            
            def save_maintenance():
                date = entry_date.get().strip()
                maint_type = entry_type.get().strip()
                technician = entry_tech.get().strip()
                status = combo_status.get()
                notes = text_notes.get("1.0", tk.END).strip()
                
                if not date or not maint_type:
                    messagebox.showwarning("Attention", "Date et Type sont obligatoires")
                    return
                
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("Erreur", "Format de date invalide (YYYY-MM-DD)")
                    return
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''INSERT INTO planification 
                          (equipement_id, date_prevue, type_maintenance, technicien, statut, notes) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                          (equipment_id, date, maint_type, technician, status, notes))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", "Maintenance planifiée avec succès!")
                add_maint_window.destroy()
                refresh_maintenance()
            
            button_frame = tk.Frame(add_maint_window)
            button_frame.grid(row=5, column=0, columnspan=2, pady=20)
            
            tk.Button(button_frame, text="Sauvegarder", command=save_maintenance, 
                     bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Annuler", command=add_maint_window.destroy, 
                     bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        
        def edit_maintenance():
            selected = tree_maint.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une maintenance à modifier")
                return
            
            values = tree_maint.item(selected[0], 'values')
            maintenance_id = values[0]
            
            edit_maint_window = tk.Toplevel(history_window)
            edit_maint_window.title("Modifier une maintenance")
            edit_maint_window.geometry("450x400")
            
            # Load data
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''SELECT date_prevue, type_maintenance, technicien, statut, notes 
                         FROM planification WHERE id=?''', (maintenance_id,))
            maintenance = c.fetchone()
            conn.close()
            
            tk.Label(edit_maint_window, text="Date prévue *:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            entry_date = tk.Entry(edit_maint_window, font=("Arial", 10))
            entry_date.grid(row=0, column=1, padx=10, pady=5)
            entry_date.insert(0, maintenance[0] or "")
            
            tk.Label(edit_maint_window, text="Type de maintenance *:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
            entry_type = tk.Entry(edit_maint_window, font=("Arial", 10))
            entry_type.grid(row=1, column=1, padx=10, pady=5)
            entry_type.insert(0, maintenance[1] or "")
            
            tk.Label(edit_maint_window, text="Technicien:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
            entry_tech = tk.Entry(edit_maint_window, font=("Arial", 10))
            entry_tech.grid(row=2, column=1, padx=10, pady=5)
            entry_tech.insert(0, maintenance[2] or "")
            
            tk.Label(edit_maint_window, text="Statut:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=10, pady=5)
            combo_status = ttk.Combobox(edit_maint_window, values=["Planifié", "En cours", "Terminé"], state="readonly")
            combo_status.grid(row=3, column=1, padx=10, pady=5)
            combo_status.set(maintenance[3] or "Planifié")
            
            tk.Label(edit_maint_window, text="Notes:", font=("Arial", 10)).grid(row=4, column=0, sticky="nw", padx=10, pady=5)
            text_notes = tk.Text(edit_maint_window, font=("Arial", 10), width=30, height=6)
            text_notes.grid(row=4, column=1, padx=10, pady=5)
            text_notes.insert("1.0", maintenance[4] or "")
            
            def save_edits():
                date = entry_date.get().strip()
                maint_type = entry_type.get().strip()
                technician = entry_tech.get().strip()
                status = combo_status.get()
                notes = text_notes.get("1.0", tk.END).strip()
                
                if not date or not maint_type:
                    messagebox.showwarning("Attention", "Date et Type sont obligatoires")
                    return
                
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("Erreur", "Format de date invalide (YYYY-MM-DD)")
                    return
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''UPDATE planification SET 
                          date_prevue=?, type_maintenance=?, technicien=?, statut=?, notes=? 
                          WHERE id=?''',
                          (date, maint_type, technician, status, notes, maintenance_id))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", "Maintenance modifiée avec succès!")
                edit_maint_window.destroy()
                refresh_maintenance()
            
            button_frame = tk.Frame(edit_maint_window)
            button_frame.grid(row=5, column=0, columnspan=2, pady=20)
            
            tk.Button(button_frame, text="Sauvegarder", command=save_edits, 
                     bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Annuler", command=edit_maint_window.destroy, 
                     bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        
        def delete_maintenance():
            selected = tree_maint.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une maintenance à supprimer")
                return
            
            if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette maintenance ?"):
                return
            
            values = tree_maint.item(selected[0], 'values')
            maintenance_id = values[0]
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM planification WHERE id=?", (maintenance_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Succès", "Maintenance supprimée avec succès!")
            refresh_maintenance()
        
        # Buttons for maintenance
        maint_btn_frame = tk.Frame(maintenance_frame)
        maint_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(maint_btn_frame, text="➕ Planifier Maintenance", command=add_maintenance, 
                 bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(maint_btn_frame, text="✏️ Modifier", command=edit_maintenance, 
                 bg="#FFC107").pack(side=tk.LEFT, padx=5)
        tk.Button(maint_btn_frame, text="🗑 Supprimer", command=delete_maintenance, 
                 bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(maint_btn_frame, text="🔄 Rafraîchir", command=refresh_maintenance, 
                 bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        
        refresh_maintenance()
    
    # Main application window
    root = tk.Tk()
    root.title("🔧 Système GMAO - Gestion de Maintenance Assistée par Ordinateur")
    root.geometry("800x600")
    root.minsize(700, 500)
    
    # Header
    header_frame = tk.Frame(root, bg="#2196F3", padx=20, pady=15)
    header_frame.pack(fill=tk.X)
    tk.Label(header_frame, text="Système GMAO", font=("Arial", 20, "bold"), 
             fg="white", bg="#2196F3").pack()
    
    # Search section
    search_frame = tk.Frame(root, padx=20, pady=20)
    search_frame.pack(fill=tk.X)
    
    tk.Label(search_frame, text="Rechercher un équipement par numéro de série:", 
             font=("Arial", 12)).pack(anchor="w")
    
    search_subframe = tk.Frame(search_frame)
    search_subframe.pack(fill=tk.X, pady=10)
    
    entry_serial = tk.Entry(search_subframe, font=("Arial", 12), width=30)
    entry_serial.pack(side=tk.LEFT, padx=(0, 10))
    entry_serial.focus()
    
    tk.Button(search_subframe, text="🔍 Rechercher", command=search_equipment, 
             font=("Arial", 10), bg="#4CAF50", fg="white", height=1).pack(side=tk.LEFT)
    
    # Stock Management Button
    stock_button_frame = tk.Frame(root)
    stock_button_frame.pack(fill=tk.X, padx=20, pady=10)
    tk.Button(stock_button_frame, text="📦 Gestion des Pièces de Rechange", 
             command=open_parts_management, font=("Arial", 12), 
             bg="#FF9800", fg="white", height=2).pack(fill=tk.X)
    
    # Footer
    footer_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=10)
    footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
    tk.Label(footer_frame, text="Système GMAO v1.0 | Tous droits réservés", 
             font=("Arial", 9), bg="#f0f0f0", fg="#666").pack()
    
    # Handle Enter key in search field
    entry_serial.bind('<Return>', lambda event: search_equipment())
    
    # Initialize reminder system
    check_reminders(root)
    
    # Run main loop
    root.mainloop()

# Initialize database and start application
if __name__ == "__main__":
    init_db()
    authentication()