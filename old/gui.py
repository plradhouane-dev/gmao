import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from functions import ajouter_intervention, charger_historique, get_intervention_details, DB_FILE
import sqlite3


def ouvrir_interface_principale():
    """Launch the main GMAO interface."""

    root = tk.Tk()
    root.title("GMAO - Gestion de Maintenance")
    root.geometry("1100x600")
    root.resizable(False, False)

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both")

    # ==============================
    # TAB 1: Ajouter une intervention
    # ==============================
    frame_ajouter = ttk.Frame(notebook, padding=15)
    notebook.add(frame_ajouter, text="Nouvelle intervention")

    ttk.Label(frame_ajouter, text="ID Équipement :").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    entry_equipement_id = ttk.Entry(frame_ajouter)
    entry_equipement_id.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(frame_ajouter, text="Date d'entrée (YYYY-MM-DD) :").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    entry_date_entree = ttk.Entry(frame_ajouter)
    entry_date_entree.insert(0, datetime.now().strftime("%Y-%m-%d"))
    entry_date_entree.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(frame_ajouter, text="Date de sortie (YYYY-MM-DD) :").grid(row=2, column=0, padx=5, pady=5, sticky="e")
    entry_date_sortie = ttk.Entry(frame_ajouter)
    entry_date_sortie.grid(row=2, column=1, padx=5, pady=5)

    ttk.Label(frame_ajouter, text="Technicien :").grid(row=3, column=0, padx=5, pady=5, sticky="e")
    entry_technicien = ttk.Entry(frame_ajouter)
    entry_technicien.grid(row=3, column=1, padx=5, pady=5)

    ttk.Label(frame_ajouter, text="Coût (€) :").grid(row=4, column=0, padx=5, pady=5, sticky="e")
    entry_cout = ttk.Entry(frame_ajouter)
    entry_cout.grid(row=4, column=1, padx=5, pady=5)

    ttk.Label(frame_ajouter, text="Détails de la réparation :").grid(row=5, column=0, padx=5, pady=5, sticky="ne")
    text_details = tk.Text(frame_ajouter, width=40, height=5)
    text_details.grid(row=5, column=1, padx=5, pady=5)

    def on_ajouter_intervention():
        equipement_id = entry_equipement_id.get().strip()
        date_entree = entry_date_entree.get().strip()
        date_sortie = entry_date_sortie.get().strip()
        technicien = entry_technicien.get().strip()
        cout = entry_cout.get().strip()
        details = text_details.get("1.0", "end").strip()

        if not equipement_id or not date_entree:
            messagebox.showwarning("Champs manquants", "Veuillez saisir l'ID équipement et la date d'entrée.")
            return

        try:
            cout = float(cout) if cout else 0.0
        except ValueError:
            messagebox.showerror("Erreur", "Le coût doit être un nombre.")
            return

        try:
            ajouter_intervention(equipement_id, date_entree, date_sortie, details, technicien, cout)
            messagebox.showinfo("Succès", "Intervention ajoutée avec succès.")
            rafraichir_historique()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "L'équipement ID n'existe pas dans la base.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    ttk.Button(frame_ajouter, text="Ajouter l'intervention", command=on_ajouter_intervention).grid(
        row=6, column=1, pady=10
    )

    # ==============================
    # TAB 2: Historique des interventions
    # ==============================
    frame_historique = ttk.Frame(notebook, padding=15)
    notebook.add(frame_historique, text="Historique des interventions")

    colonnes = ("ID", "Numéro de série", "Marque", "Modèle", "Date entrée",
                "Date sortie", "Détails", "Technicien", "Coût")

    tree_historique = ttk.Treeview(frame_historique, columns=colonnes, show="headings", height=20)
    for col in colonnes:
        tree_historique.heading(col, text=col)
        tree_historique.column(col, width=120)
    tree_historique.pack(expand=True, fill="both", pady=10)

    scroll_y = ttk.Scrollbar(frame_historique, orient="vertical", command=tree_historique.yview)
    tree_historique.configure(yscroll=scroll_y.set)
    scroll_y.pack(side="right", fill="y")

    def rafraichir_historique():
        for item in tree_historique.get_children():
            tree_historique.delete(item)
        for row in charger_historique():
            tree_historique.insert("", "end", values=row)

    rafraichir_historique()

    # ==============================
    # Popup Details on Double Click
    # ==============================
    def afficher_details_intervention(event):
        selected_item = tree_historique.selection()
        if not selected_item:
            return
        intervention_id = tree_historique.item(selected_item, "values")[0]
        details = get_intervention_details(intervention_id)

        if not details:
            messagebox.showerror("Erreur", "Aucune donnée trouvée.")
            return

        (iid, numero_serie, marque, modele, date_entree, date_sortie,
         details_reparation, technicien, cout) = details

        popup = tk.Toplevel(root)
        popup.title(f"Détails Intervention #{iid}")
        popup.geometry("500x450")
        popup.resizable(False, False)

        ttk.Label(popup, text=f"Équipement : {numero_serie} ({marque} {modele})",
                  font=("Segoe UI", 10, "bold")).pack(pady=5)
        ttk.Label(popup, text=f"Date d'entrée : {date_entree}").pack()
        ttk.Label(popup, text=f"Date de sortie : {date_sortie}").pack()
        ttk.Label(popup, text=f"Technicien : {technicien}").pack()
        ttk.Label(popup, text=f"Coût : {cout} €").pack(pady=5)
        ttk.Label(popup, text="Détails de la réparation :", font=("Segoe UI", 10, "bold")).pack(pady=5)

        text_popup = tk.Text(popup, wrap="word", width=55, height=10)
        text_popup.pack(padx=10, pady=5)
        text_popup.insert("1.0", details_reparation)
        text_popup.config(state="disabled")

        ttk.Button(popup, text="Fermer", command=popup.destroy).pack(pady=10)

    tree_historique.bind("<Double-1>", afficher_details_intervention)

    root.mainloop()
