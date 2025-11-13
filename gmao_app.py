import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3
from cryptography.fernet import Fernet
import os
from datetime import datetime, timedelta
import threading
import time
from functools import partial
import hashlib

# === Global Variables ===
root = None
entry_serial = None
current_user = None

# === Configuration ===
KEY_FILE = 'secret.key'
DB_FILE = 'gmao_encrypted.db'
INITIAL_PASSWORD = 'admin123'
LOW_STOCK_THRESHOLD = 5
MONETARY_SYMBOL = "TND"  # Changed from € to TND

# === Window Manager ===
class WindowManager:
    def __init__(self):
        self.windows = {}
    
    def open_window(self, window_name, create_window_func, *args, **kwargs):
        if window_name in self.windows and self.windows[window_name].winfo_exists():
            # Window already exists, bring it to focus
            self.windows[window_name].lift()
            self.windows[window_name].focus_force()
            return self.windows[window_name]
        else:
            # Create new window
            window = create_window_func(*args, **kwargs)
            self.windows[window_name] = window
            
            # Clean up when window is closed
            def on_close():
                if window_name in self.windows:
                    del self.windows[window_name]
                window.destroy()
            
            window.protocol("WM_DELETE_WINDOW", on_close)
            return window

# Create a global window manager instance
window_manager = WindowManager()

# === Professional UI Theme ===
class ProfessionalTheme:
    # Color Palette
    PRIMARY = "#2c3e50"      # Dark blue-gray
    SECONDARY = "#3498db"     # Blue
    SUCCESS = "#27ae60"       # Green
    WARNING = "#f39c12"       # Orange
    DANGER = "#e74c3c"        # Red
    LIGHT = "#ecf0f1"         # Light gray
    DARK = "#2c3e50"          # Dark
    WHITE = "#ffffff"         # White
    GRAY = "#95a5a6"          # Medium gray
    
    # Fonts
    FONT_FAMILY = "Segoe UI"
    TITLE_FONT = (FONT_FAMILY, 16, "bold")
    SUBTITLE_FONT = (FONT_FAMILY, 12, "bold")
    BODY_FONT = (FONT_FAMILY, 10)
    BUTTON_FONT = (FONT_FAMILY, 10, "bold")
    
    @staticmethod
    def configure_styles():
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure("Primary.TButton", 
                        background=ProfessionalTheme.PRIMARY,
                        foreground=ProfessionalTheme.WHITE,
                        borderwidth=0,
                        focuscolor='none',
                        font=ProfessionalTheme.BUTTON_FONT)
        style.map("Primary.TButton",
                 background=[('active', ProfessionalTheme.SECONDARY)])
        
        style.configure("Success.TButton", 
                        background=ProfessionalTheme.SUCCESS,
                        foreground=ProfessionalTheme.WHITE,
                        borderwidth=0,
                        focuscolor='none',
                        font=ProfessionalTheme.BUTTON_FONT)
        style.map("Success.TButton",
                 background=[('active', '#229954')])
        
        style.configure("Warning.TButton", 
                        background=ProfessionalTheme.WARNING,
                        foreground=ProfessionalTheme.WHITE,
                        borderwidth=0,
                        focuscolor='none',
                        font=ProfessionalTheme.BUTTON_FONT)
        style.map("Warning.TButton",
                 background=[('active', '#e67e22')])
        
        style.configure("Danger.TButton", 
                        background=ProfessionalTheme.DANGER,
                        foreground=ProfessionalTheme.WHITE,
                        borderwidth=0,
                        focuscolor='none',
                        font=ProfessionalTheme.BUTTON_FONT)
        style.map("Danger.TButton",
                 background=[('active', '#c0392b')])
        
        # Configure frame styles
        style.configure("Card.TFrame", 
                        background=ProfessionalTheme.WHITE,
                        relief="raised",
                        borderwidth=1)
        
        # Configure label styles
        style.configure("Title.TLabel", 
                        background=ProfessionalTheme.PRIMARY,
                        foreground=ProfessionalTheme.WHITE,
                        font=ProfessionalTheme.TITLE_FONT)
        
        style.configure("CardTitle.TLabel", 
                        background=ProfessionalTheme.WHITE,
                        foreground=ProfessionalTheme.PRIMARY,
                        font=ProfessionalTheme.SUBTITLE_FONT)
        
        # Configure entry styles
        style.configure("Card.TEntry", 
                        fieldbackground=ProfessionalTheme.WHITE,
                        borderwidth=1,
                        relief="solid")
        
        # Configure treeview styles
        style.configure("Treeview",
                        background=ProfessionalTheme.WHITE,
                        foreground=ProfessionalTheme.DARK,
                        fieldbackground=ProfessionalTheme.WHITE,
                        borderwidth=1,
                        relief="solid")
        style.configure("Treeview.Heading",
                        background=ProfessionalTheme.PRIMARY,
                        foreground=ProfessionalTheme.WHITE,
                        font=ProfessionalTheme.SUBTITLE_FONT)

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

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

# === Database Initialization ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table for multi-user system
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password_hash TEXT,
                 role TEXT DEFAULT 'user',
                 first_login INTEGER DEFAULT 1,
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    
    # Check if admin user exists, create if not
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password_hash, role, first_login) VALUES (?, ?, ?, ?)",
                 ('admin', hash_password(INITIAL_PASSWORD), 'admin', 1))
    
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

# === Password Change Function ===
def force_password_change():
    def save_new_password():
        new_pass = entry_new_password.get()
        confirm_pass = entry_confirm_password.get()
        
        if not new_pass or not confirm_pass:
            messagebox.showerror("Erreur", "Veuillez saisir un mot de passe et le confirmer")
            return
        
        if new_pass != confirm_pass:
            messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas")
            return
        
        if len(new_pass) < 6:
            messagebox.showerror("Erreur", "Le mot de passe doit contenir au moins 6 caractères")
            return
        
        # Update password in database
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE users SET password_hash=?, first_login=0 WHERE id=?",
                  (hash_password(new_pass), current_user['id']))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Succès", "Mot de passe changé avec succès")
        current_user['first_login'] = 0
        password_window.destroy()
        
        # Call open_gmao_interface after a short delay to ensure proper window cleanup
        password_window.after(100, open_gmao_interface)
    
    password_window = tk.Tk()
    password_window.title("Changement de mot de passe")
    password_window.geometry("500x350")  # Increased size
    password_window.minsize(450, 300)     # Set minimum size
    password_window.resizable(True, True)    # Make window resizable
    
    # Center window on screen
    password_window.update_idletasks()
    width = password_window.winfo_width()
    height = password_window.winfo_height()
    x = (password_window.winfo_screenwidth() // 2) - (width // 2)
    y = (password_window.winfo_screenheight() // 2) - (height // 2)
    password_window.geometry(f'{width}x{height}+{x}+{y}')
    
    password_window.configure(bg=ProfessionalTheme.PRIMARY)
    
    # Configure styles
    ProfessionalTheme.configure_styles()
    
    # Main frame with padding that adjusts to window size
    main_frame = tk.Frame(password_window, bg=ProfessionalTheme.PRIMARY)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title
    title_label = tk.Label(main_frame, text="Changement de mot de passe obligatoire", 
                         font=("Segoe UI", 16, "bold"), bg=ProfessionalTheme.PRIMARY, 
                         fg=ProfessionalTheme.WHITE)
    title_label.pack(pady=(30, 20))
    
    # Form with responsive layout
    form_frame = tk.Frame(main_frame, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
    form_frame.pack(fill=tk.BOTH, expand=True, pady=20)
    
    # New password section
    new_pass_frame = tk.Frame(form_frame, bg=ProfessionalTheme.WHITE)
    new_pass_frame.pack(fill=tk.X, padx=30, pady=(20, 5))
    
    tk.Label(new_pass_frame, text="Nouveau mot de passe :", font=("Segoe UI", 12), 
             bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).pack(anchor="w")
    
    entry_new_password = tk.Entry(new_pass_frame, show='*', font=("Segoe UI", 12), 
                                 bd=1, relief="solid", highlightthickness=0)
    entry_new_password.pack(fill=tk.X, pady=(5, 0))
    entry_new_password.focus()
    
    # Confirm password section
    confirm_pass_frame = tk.Frame(form_frame, bg=ProfessionalTheme.WHITE)
    confirm_pass_frame.pack(fill=tk.X, padx=30, pady=(15, 5))
    
    tk.Label(confirm_pass_frame, text="Confirmer le mot de passe :", font=("Segoe UI", 12), 
             bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).pack(anchor="w")
    
    entry_confirm_password = tk.Entry(confirm_pass_frame, show='*', font=("Segoe UI", 12), 
                                     bd=1, relief="solid", highlightthickness=0)
    entry_confirm_password.pack(fill=tk.X, pady=(5, 0))
    
    # Button frame with responsive positioning
    button_frame = tk.Frame(form_frame, bg=ProfessionalTheme.WHITE)
    button_frame.pack(fill=tk.X, padx=30, pady=20)
    
    save_button = tk.Button(button_frame, text="Enregistrer", command=save_new_password, 
                           font=("Segoe UI", 10, "bold"), bg=ProfessionalTheme.SUCCESS, 
                           fg=ProfessionalTheme.WHITE, bd=0, padx=30, pady=10, 
                           activebackground='#229954', cursor="hand2")
    save_button.pack()
    
    # Add some padding at the bottom
    bottom_padding = tk.Frame(form_frame, bg=ProfessionalTheme.WHITE, height=20)
    bottom_padding.pack(fill=tk.X)
    
    # Bind Enter key to save
    entry_new_password.bind('<Return>', lambda event: entry_confirm_password.focus())
    entry_confirm_password.bind('<Return>', lambda event: save_new_password())
    
    # Add window resize handler to adjust font sizes if needed
    def on_resize(event):
        # Optional: Adjust font sizes based on window width
        if event.width < 450:
            title_label.config(font=("Segoe UI", 14, "bold"))
        else:
            title_label.config(font=("Segoe UI", 16, "bold"))
    
    password_window.bind('<Configure>', on_resize)
    
    password_window.mainloop()
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

# === Authentication System ===
def authentication():
    def verify_password():
        username = entry_username.get().strip()
        entered_password = entry_password.get()
        
        if not username or not entered_password:
            messagebox.showerror("Erreur", "Veuillez saisir un nom d'utilisateur et un mot de passe")
            return
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash, role, first_login FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and user[2] == hash_password(entered_password):
            global current_user
            current_user = {
                'id': user[0],
                'username': user[1],
                'role': user[3],
                'first_login': user[4]
            }
            
            auth_window.destroy()
            
            # Check if first login, require password change
            if current_user['first_login']:
                force_password_change()
            else:
                open_gmao_interface()
        else:
            messagebox.showerror("Erreur", "Nom d'utilisateur ou mot de passe incorrect")

    auth_window = tk.Tk()
    auth_window.title("Authentification - GMAO")
    auth_window.geometry("450x400")  # Increased default size
    auth_window.minsize(400, 350)    # Set minimum size
    auth_window.maxsize(600, 500)    # Set maximum size
    auth_window.resizable(True, True)  # Make window resizable
    
    # Center window on screen
    auth_window.update_idletasks()
    width = auth_window.winfo_width()
    height = auth_window.winfo_height()
    x = (auth_window.winfo_screenwidth() // 2) - (width // 2)
    y = (auth_window.winfo_screenheight() // 2) - (height // 2)
    auth_window.geometry(f'{width}x{height}+{x}+{y}')
    
    auth_window.configure(bg=ProfessionalTheme.PRIMARY)
    
    # Configure styles
    ProfessionalTheme.configure_styles()
    
    # Main frame with padding that adjusts to window size
    main_frame = tk.Frame(auth_window, bg=ProfessionalTheme.PRIMARY)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title with dynamic font size based on window size
    title_label = tk.Label(main_frame, text="GMAO System", font=("Segoe UI", 24, "bold"), 
                          bg=ProfessionalTheme.PRIMARY, fg=ProfessionalTheme.WHITE)
    title_label.pack(pady=(30, 10))
    
    subtitle_label = tk.Label(main_frame, text="Gestion de Maintenance Assistée par Ordinateur", 
                             font=("Segoe UI", 10), bg=ProfessionalTheme.PRIMARY, 
                             fg=ProfessionalTheme.LIGHT)
    subtitle_label.pack(pady=(0, 20))
    
    # Login form with responsive layout
    login_frame = tk.Frame(main_frame, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
    login_frame.pack(fill=tk.BOTH, expand=True, pady=20)
    
    # Username section
    username_frame = tk.Frame(login_frame, bg=ProfessionalTheme.WHITE)
    username_frame.pack(fill=tk.X, padx=30, pady=(20, 5))
    
    tk.Label(username_frame, text="Nom d'utilisateur :", font=("Segoe UI", 12), 
             bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).pack(anchor="w")
    
    entry_username = tk.Entry(username_frame, font=("Segoe UI", 12), 
                            bd=1, relief="solid", highlightthickness=0)
    entry_username.pack(fill=tk.X, pady=(5, 0))
    entry_username.insert(0, "admin")  # Default to admin for convenience
    
    # Password section
    password_frame = tk.Frame(login_frame, bg=ProfessionalTheme.WHITE)
    password_frame.pack(fill=tk.X, padx=30, pady=(15, 5))
    
    tk.Label(password_frame, text="Mot de passe :", font=("Segoe UI", 12), 
             bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).pack(anchor="w")
    
    entry_password = tk.Entry(password_frame, show='*', font=("Segoe UI", 12), 
                             bd=1, relief="solid", highlightthickness=0)
    entry_password.pack(fill=tk.X, pady=(5, 0))
    entry_password.focus()
    
    # Button frame with responsive positioning
    button_frame = tk.Frame(login_frame, bg=ProfessionalTheme.WHITE)
    button_frame.pack(fill=tk.X, padx=30, pady=20)
    
    login_button = tk.Button(button_frame, text="Se connecter", command=verify_password, 
                            font=("Segoe UI", 10, "bold"), bg=ProfessionalTheme.PRIMARY, 
                            fg=ProfessionalTheme.WHITE, bd=0, padx=30, pady=10, 
                            activebackground=ProfessionalTheme.SECONDARY,
                            cursor="hand2")  # Add hand cursor
    login_button.pack()
    
    # Add some padding at the bottom
    bottom_padding = tk.Frame(login_frame, bg=ProfessionalTheme.WHITE, height=20)
    bottom_padding.pack(fill=tk.X)
    
    # Bind Enter key to login
    entry_password.bind('<Return>', lambda event: verify_password())
    entry_username.bind('<Return>', lambda event: entry_password.focus())
    
    # Add window resize handler to adjust font sizes if needed
    def on_resize(event):
        # Optional: Adjust font sizes based on window width
        if event.width < 450:
            title_label.config(font=("Segoe UI", 20, "bold"))
            subtitle_label.config(font=("Segoe UI", 9))
        else:
            title_label.config(font=("Segoe UI", 24, "bold"))
            subtitle_label.config(font=("Segoe UI", 10))
    
    auth_window.bind('<Configure>', on_resize)
    
    auth_window.mainloop()

# === Main GMAO Interface ===
def open_gmao_interface():
    global root, entry_serial
    
    # Main application window
    root = tk.Tk()
    root.title(f"🔧 Système GMAO - {current_user['username']}")
    root.geometry("900x700")
    root.minsize(800, 600)
    root.configure(bg=ProfessionalTheme.LIGHT)
    
    # Configure styles
    ProfessionalTheme.configure_styles()
    
    # Header
    header_frame = tk.Frame(root, bg=ProfessionalTheme.PRIMARY, height=70)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    tk.Label(header_frame, text="Système GMAO", font=ProfessionalTheme.TITLE_FONT, 
             fg=ProfessionalTheme.WHITE, bg=ProfessionalTheme.PRIMARY).pack(side=tk.LEFT, padx=20, pady=20)
    
    tk.Label(header_frame, text="Gestion de Maintenance Assistée par Ordinateur", 
             font=ProfessionalTheme.BODY_FONT, fg=ProfessionalTheme.LIGHT, 
             bg=ProfessionalTheme.PRIMARY).pack(side=tk.LEFT, padx=(0, 20), pady=20)
    
    # User info and logout
    user_frame = tk.Frame(header_frame, bg=ProfessionalTheme.PRIMARY)
    user_frame.pack(side=tk.RIGHT, padx=20, pady=15)
    
    tk.Label(user_frame, text=f"Utilisateur: {current_user['username']}", 
             font=ProfessionalTheme.BODY_FONT, fg=ProfessionalTheme.WHITE, 
             bg=ProfessionalTheme.PRIMARY).pack(side=tk.LEFT, padx=(0, 15))
    
    logout_button = tk.Button(user_frame, text="Déconnexion", command=logout, 
                             font=ProfessionalTheme.BODY_FONT, bg=ProfessionalTheme.DANGER, 
                             fg=ProfessionalTheme.WHITE, bd=0, padx=10, pady=5)
    logout_button.pack(side=tk.LEFT)
    
    # Main container
    main_container = tk.Frame(root, bg=ProfessionalTheme.LIGHT)
    main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Search section
    search_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
    search_frame.pack(fill=tk.X, pady=(0, 20))
    
    tk.Label(search_frame, text="Rechercher un équipement par numéro de série:", 
             font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.WHITE, 
             fg=ProfessionalTheme.PRIMARY).pack(anchor="w", padx=20, pady=(20, 10))
    
    search_subframe = tk.Frame(search_frame, bg=ProfessionalTheme.WHITE)
    search_subframe.pack(fill=tk.X, padx=20, pady=(0, 20))
    
    entry_serial = tk.Entry(search_subframe, font=ProfessionalTheme.BODY_FONT, 
                           bd=1, relief="solid", highlightthickness=0)
    entry_serial.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    entry_serial.focus()
    
    # Management buttons frame
    buttons_frame = tk.Frame(main_container, bg=ProfessionalTheme.LIGHT)
    buttons_frame.pack(fill=tk.X, pady=(0, 20))
    
    # Stock Management Button
    ttk.Button(buttons_frame, text="📦 Gestion des Pièces de Rechange", 
              command=open_parts_management, style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
    
    # Profile Management Button (only for admin)
    if current_user['role'] == 'admin':
        ttk.Button(buttons_frame, text="👤 Gestion des Profils", 
                  command=open_profile_management, style="Primary.TButton").pack(side=tk.LEFT)
    
    # Footer
    footer_frame = tk.Frame(root, bg=ProfessionalTheme.PRIMARY, height=40)
    footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
    footer_frame.pack_propagate(False)
    
    tk.Label(footer_frame, text="Système GMAO v1.0 | Tous droits réservés", 
             font=ProfessionalTheme.BODY_FONT, bg=ProfessionalTheme.PRIMARY, 
             fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=10)
    
    # Handle Enter key in search field
    entry_serial.bind('<Return>', lambda event: search_equipment())
    
    # Initialize reminder system
    check_reminders(root)
    
    # Run main loop
    root.mainloop()

def logout():
    global current_user
    current_user = None
    root.destroy()
    authentication()

def open_profile_management():
    def create_profile_window():
        profile_window = tk.Toplevel(root)
        profile_window.title("👤 Gestion des Profils Utilisateurs")
        profile_window.geometry("900x600")
        profile_window.configure(bg=ProfessionalTheme.LIGHT)
        
        # Configure styles
        ProfessionalTheme.configure_styles()
        
        # Header
        header_frame = tk.Frame(profile_window, bg=ProfessionalTheme.PRIMARY, height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="Gestion des Profils Utilisateurs", 
                font=ProfessionalTheme.TITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Main container
        main_container = tk.Frame(profile_window, bg=ProfessionalTheme.LIGHT)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Button frame
        button_frame = tk.Frame(main_container, bg=ProfessionalTheme.LIGHT)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Users Table
        table_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "Nom d'utilisateur", "Rôle", "Première connexion", "Date de création")
        tree_users = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        for col in columns:
            tree_users.heading(col, text=col)
            tree_users.column(col, width=(50 if col == "ID" else 150))
        tree_users.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree_users.yview)
        tree_users.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def refresh_users():
            for item in tree_users.get_children():
                tree_users.delete(item)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, username, role, first_login, created_at FROM users ORDER BY username")
            rows = c.fetchall()
            conn.close()
            for row in rows:
                first_login_text = "Oui" if row[3] else "Non"
                tree_users.insert("", tk.END, values=(row[0], row[1], row[2], first_login_text, row[4]))
        
        def add_user():
            add_window = tk.Toplevel(profile_window)
            add_window.title("Ajouter un utilisateur")
            add_window.geometry("500x400")
            add_window.configure(bg=ProfessionalTheme.LIGHT)
            
            # Header
            header_frame = tk.Frame(add_window, bg=ProfessionalTheme.PRIMARY, height=50)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)
            
            tk.Label(header_frame, text="Ajouter un nouvel utilisateur", 
                    font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                    fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
            
            # Form container
            form_container = tk.Frame(add_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
            form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            fields = [
                ("Nom d'utilisateur *:", "username"),
                ("Mot de passe *:", "password"),
                ("Rôle *:", "role")
            ]
            entries = {}
            for i, (label, key) in enumerate(fields):
                tk.Label(form_container, text=label, font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=i, column=0, sticky="w", padx=20, pady=12)
                
                if key == "role":
                    entry = ttk.Combobox(form_container, values=["admin", "user"], state="readonly")
                    entry.set("user")
                else:
                    entry = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                   bd=1, relief="solid", highlightthickness=0, 
                                   show='*' if key == "password" else None)
                
                entry.grid(row=i, column=1, padx=20, pady=12, sticky="ew")
                entries[key] = entry
            
            def save_user():
                username = entries["username"].get().strip()
                password = entries["password"].get().strip()
                role = entries["role"].get()
                
                if not username or not password:
                    messagebox.showwarning("Attention", "Nom d'utilisateur et mot de passe sont obligatoires")
                    return
                
                if len(password) < 6:
                    messagebox.showwarning("Attention", "Le mot de passe doit contenir au moins 6 caractères")
                    return
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute('''INSERT INTO users (username, password_hash, role, first_login)
                                 VALUES (?, ?, ?, ?)''', 
                              (username, hash_password(password), role, 1))
                    conn.commit()
                    messagebox.showinfo("Succès", "Utilisateur ajouté avec succès.")
                    add_window.destroy()
                    refresh_users()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Erreur", "Un utilisateur avec ce nom existe déjà.")
                finally:
                    conn.close()
            
            button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
            button_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
            
            ttk.Button(button_frame, text="Sauvegarder", command=save_user, 
                      style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Annuler", command=add_window.destroy, 
                      style="Danger.TButton").pack(side=tk.LEFT)
            
            form_container.columnconfigure(1, weight=1)
        
        def reset_password():
            selected = tree_users.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez un utilisateur")
                return
            
            values = tree_users.item(selected[0], 'values')
            user_id = values[0]
            username = values[1]
            
            if username == current_user['username']:
                messagebox.showwarning("Attention", "Vous ne pouvez pas réinitialiser votre propre mot de passe ici")
                return
            
            if not messagebox.askyesno("Confirmation", f"Voulez-vous réinitialiser le mot de passe de '{username}' ?\nL'utilisateur devra le changer à la prochaine connexion."):
                return
            
            # Reset password to initial password and set first_login flag
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE users SET password_hash=?, first_login=1 WHERE id=?",
                     (hash_password(INITIAL_PASSWORD), user_id))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Succès", f"Mot de passe de '{username}' réinitialisé. Le mot de passe temporaire est '{INITIAL_PASSWORD}'")
            refresh_users()
        
        def delete_user():
            selected = tree_users.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez un utilisateur")
                return
            
            values = tree_users.item(selected[0], 'values')
            user_id = values[0]
            username = values[1]
            
            if username == current_user['username']:
                messagebox.showwarning("Attention", "Vous ne pouvez pas supprimer votre propre compte")
                return
            
            if not messagebox.askyesno("Confirmation", f"Voulez-vous vraiment supprimer l'utilisateur '{username}' ?"):
                return
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Succès", f"Utilisateur '{username}' supprimé avec succès")
            refresh_users()
        
        # Add buttons after defining all functions
        ttk.Button(button_frame, text="➕ Ajouter un utilisateur", command=add_user, 
                  style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Réinitialiser mot de passe", command=reset_password, 
                  style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑 Supprimer", command=delete_user, 
                  style="Danger.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_users, 
                  style="Primary.TButton").pack(side=tk.LEFT)
        
        refresh_users()
        
        return profile_window
    
    # Use the window manager to open/create the window
    return window_manager.open_window("profile_management", create_profile_window)

def open_parts_management():
    def create_stock_window():
        stock_window = tk.Toplevel(root)
        stock_window.title("📦 Gestion des pièces de rechange")
        stock_window.geometry("1200x700")
        stock_window.configure(bg=ProfessionalTheme.LIGHT)
        
        # Configure styles
        ProfessionalTheme.configure_styles()
        
        # Header
        header_frame = tk.Frame(stock_window, bg=ProfessionalTheme.PRIMARY, height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="Gestion des Pièces de Rechange", 
                font=ProfessionalTheme.TITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Main container
        main_container = tk.Frame(stock_window, bg=ProfessionalTheme.LIGHT)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Button frame
        button_frame = tk.Frame(main_container, bg=ProfessionalTheme.LIGHT)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Parts Table
        table_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "Nom", "Référence", "Fournisseur", f"Prix ({MONETARY_SYMBOL})", "Quantité", "Description")
        tree_parts = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        for col in columns:
            tree_parts.heading(col, text=col)
            tree_parts.column(col, width=(50 if col == "ID" else 130))
        tree_parts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree_parts.yview)
        tree_parts.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
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
            add_window.geometry("500x500")
            add_window.configure(bg=ProfessionalTheme.LIGHT)
            
            # Header
            header_frame = tk.Frame(add_window, bg=ProfessionalTheme.PRIMARY, height=50)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)
            
            tk.Label(header_frame, text="Ajouter une nouvelle pièce", 
                    font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                    fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
            
            # Form container
            form_container = tk.Frame(add_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
            form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            fields = [
                ("Nom *:", "name"),
                ("Référence *:", "ref"),
                ("Fournisseur:", "supplier"),
                (f"Prix unitaire ({MONETARY_SYMBOL}):", "price"),
                ("Quantité en stock:", "quantity"),
            ]
            entries = {}
            for i, (label, key) in enumerate(fields):
                tk.Label(form_container, text=label, font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=i, column=0, sticky="w", padx=20, pady=12)
                entry = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                               bd=1, relief="solid", highlightthickness=0)
                entry.grid(row=i, column=1, padx=20, pady=12, sticky="ew")
                entries[key] = entry
            
            tk.Label(form_container, text="Description:", font=ProfessionalTheme.BODY_FONT, 
                    bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                row=len(fields), column=0, sticky="nw", padx=20, pady=12)
            desc_text = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                               bd=1, relief="solid", highlightthickness=0, height=6)
            desc_text.grid(row=len(fields), column=1, padx=20, pady=12, sticky="ew")
            
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
            
            button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
            button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
            
            ttk.Button(button_frame, text="Sauvegarder", command=save_part, 
                      style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Annuler", command=add_window.destroy, 
                      style="Danger.TButton").pack(side=tk.LEFT)
            
            form_container.columnconfigure(1, weight=1)
        
        def edit_part():
            selected = tree_parts.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une pièce à modifier.")
                return
            
            values = tree_parts.item(selected[0], 'values')
            part_id = values[0]
            
            edit_window = tk.Toplevel(stock_window)
            edit_window.title("Modifier une pièce")
            edit_window.geometry("500x500")
            edit_window.configure(bg=ProfessionalTheme.LIGHT)
            
            # Header
            header_frame = tk.Frame(edit_window, bg=ProfessionalTheme.PRIMARY, height=50)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)
            
            tk.Label(header_frame, text="Modifier une pièce", 
                    font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                    fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
            
            # Form container
            form_container = tk.Frame(edit_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
            form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT nom, reference, fournisseur, prix_unitaire, quantite_stock, description FROM pieces WHERE id=?", (part_id,))
            row = c.fetchone()
            conn.close()
            
            fields = [("Nom:", row[0]), ("Référence:", row[1]), ("Fournisseur:", row[2]), 
                      (f"Prix unitaire ({MONETARY_SYMBOL}):", row[3]), ("Quantité:", row[4])]
            entries = {}
            for i, (label, value) in enumerate(fields):
                tk.Label(form_container, text=label, font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=i, column=0, sticky="w", padx=20, pady=12)
                entry = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                               bd=1, relief="solid", highlightthickness=0)
                entry.grid(row=i, column=1, padx=20, pady=12, sticky="ew")
                entry.insert(0, str(value))
                entries[i] = entry
            
            tk.Label(form_container, text="Description:", font=ProfessionalTheme.BODY_FONT, 
                    bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                row=len(fields), column=0, sticky="nw", padx=20, pady=12)
            desc_text = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                               bd=1, relief="solid", highlightthickness=0, height=6)
            desc_text.grid(row=len(fields), column=1, padx=20, pady=12, sticky="ew")
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
            
            button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
            button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
            
            ttk.Button(button_frame, text="Sauvegarder", command=save_edits, 
                      style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Annuler", command=edit_window.destroy, 
                      style="Danger.TButton").pack(side=tk.LEFT)
            
            form_container.columnconfigure(1, weight=1)
        
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
        
        # Add buttons after defining all functions
        ttk.Button(button_frame, text="➕ Ajouter une pièce", command=add_part, 
                  style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✏️ Modifier", command=edit_part, 
                  style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑 Supprimer", command=delete_part, 
                  style="Danger.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_stock, 
                  style="Primary.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔔 Vérifier stock faible", command=check_low_stock, 
                  style="Warning.TButton").pack(side=tk.LEFT)
        
        refresh_stock()
        check_low_stock()  # Initial check
        
        return stock_window
    
    # Use the window manager to open/create the window
    return window_manager.open_window("parts_management", create_stock_window)

# Main search functionality
def search_equipment():
    global entry_serial
    
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
    def create_form_window():
        form_window = tk.Toplevel(root)
        form_window.title(f"Nouvel Équipement - {serial_number}")
        form_window.geometry("600x700")
        form_window.configure(bg=ProfessionalTheme.LIGHT)
        
        # Header
        header_frame = tk.Frame(form_window, bg=ProfessionalTheme.PRIMARY, height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text=f"Nouvel Équipement - {serial_number}", 
                font=ProfessionalTheme.TITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Form container
        form_container = tk.Frame(form_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
        form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(form_container, text="Informations de l'Équipement", 
                font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.WHITE, 
                fg=ProfessionalTheme.PRIMARY).grid(row=0, column=0, columnspan=2, pady=(20, 20))
        
        tk.Label(form_container, text="Marque *:", font=ProfessionalTheme.BODY_FONT, 
                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
            row=1, column=0, sticky="w", padx=20, pady=12)
        entry_brand = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                              bd=1, relief="solid", highlightthickness=0)
        entry_brand.grid(row=1, column=1, padx=20, pady=12, sticky="ew")
        
        tk.Label(form_container, text="Modèle *:", font=ProfessionalTheme.BODY_FONT, 
                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
            row=2, column=0, sticky="w", padx=20, pady=12)
        entry_model = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                              bd=1, relief="solid", highlightthickness=0)
        entry_model.grid(row=2, column=1, padx=20, pady=12, sticky="ew")
        
        tk.Label(form_container, text="Date d'achat:", font=ProfessionalTheme.BODY_FONT, 
                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
            row=3, column=0, sticky="w", padx=20, pady=12)
        entry_purchase_date = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0)
        entry_purchase_date.grid(row=3, column=1, padx=20, pady=12, sticky="ew")
        entry_purchase_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        tk.Label(form_container, text="Date de vente:", font=ProfessionalTheme.BODY_FONT, 
                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
            row=4, column=0, sticky="w", padx=20, pady=12)
        entry_sale_date = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                  bd=1, relief="solid", highlightthickness=0)
        entry_sale_date.grid(row=4, column=1, padx=20, pady=12, sticky="ew")
        
        tk.Label(form_container, text="Identifiant Acheteur:", font=ProfessionalTheme.BODY_FONT, 
                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
            row=5, column=0, sticky="w", padx=20, pady=12)
        entry_buyer = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                              bd=1, relief="solid", highlightthickness=0)
        entry_buyer.grid(row=5, column=1, padx=20, pady=12, sticky="ew")
        
        tk.Label(form_container, text="Notes:", font=ProfessionalTheme.BODY_FONT, 
                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
            row=6, column=0, sticky="nw", padx=20, pady=12)
        text_notes = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                            bd=1, relief="solid", highlightthickness=0, height=8)
        text_notes.grid(row=6, column=1, padx=20, pady=12, sticky="ew")
        
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
        
        button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Sauvegarder", command=save_equipment, 
                  style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Annuler", command=form_window.destroy, 
                  style="Danger.TButton").pack(side=tk.LEFT)
        
        form_container.columnconfigure(1, weight=1)
        entry_brand.focus()
        
        return form_window
    
    # Use the window manager to open/create the window
    return window_manager.open_window(f"equipment_form_{serial_number}", create_form_window)

# Maintenance history display
def show_equipment_history(equipment_id, serial_number):
    def create_history_window():
        history_window = tk.Toplevel(root)
        history_window.title(f"Historique - {serial_number}")
        history_window.geometry("1200x800")
        history_window.configure(bg=ProfessionalTheme.LIGHT)
        
        # Configure styles
        ProfessionalTheme.configure_styles()
        
        # Header
        header_frame = tk.Frame(history_window, bg=ProfessionalTheme.PRIMARY, height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text=f"Historique - {serial_number}", 
                font=ProfessionalTheme.TITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Main container
        main_container = tk.Frame(history_window, bg=ProfessionalTheme.LIGHT)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Equipment Info Tab
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Informations Équipement")
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM equipements WHERE id=?", (equipment_id,))
        equipment = c.fetchone()
        conn.close()
        
        details_frame = tk.Frame(info_frame, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
            tk.Label(details_frame, text=label, font=ProfessionalTheme.SUBTITLE_FONT, 
                    bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY, 
                    anchor="w").grid(row=i, column=0, sticky="w", pady=10, padx=20)
            tk.Label(details_frame, text=value or "Non renseigné", font=ProfessionalTheme.BODY_FONT, 
                    bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK, 
                    anchor="w").grid(row=i, column=1, sticky="w", pady=10, padx=(20, 20))
        
        # Repair History Tab
        repairs_frame = ttk.Frame(notebook)
        notebook.add(repairs_frame, text="Historique des Réparations")
        
        # Button frame
        button_frame = tk.Frame(repairs_frame, bg=ProfessionalTheme.LIGHT)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Table frame
        table_frame = tk.Frame(repairs_frame, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ("ID", "Date Entrée", "Date Sortie", "Technicien", f"Coût ({MONETARY_SYMBOL})", "Détails")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=(60 if col == "ID" else 140))
        tree.column("Détails", width=260)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
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
            # Check if a pieces window for this parent already exists
            for child in parent_window.winfo_children():
                if isinstance(child, tk.Toplevel) and hasattr(child, 'pieces_selection'):
                    child.lift()
                    child.focus_force()
                    return
            
            # Create new window
            pieces_window = tk.Toplevel(parent_window)
            pieces_window.title("Associer des pièces à l'intervention")
            pieces_window.geometry("900x500")
            pieces_window.configure(bg=ProfessionalTheme.LIGHT)
            
            # Add a custom attribute to identify this window type
            pieces_window.pieces_selection = True
            
            # Header
            header_frame = tk.Frame(pieces_window, bg=ProfessionalTheme.PRIMARY, height=50)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)
            
            tk.Label(header_frame, text="Associer des pièces à l'intervention", 
                    font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                    fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
            
            # Main container
            main_container = tk.Frame(pieces_window, bg=ProfessionalTheme.LIGHT)
            main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Left: Available pieces
            left_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            
            tk.Label(left_frame, text="Pièces disponibles", font=ProfessionalTheme.SUBTITLE_FONT, 
                    bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY).pack(pady=10)
            
            cols = ("ID", "Nom", "Réf", f"Prix ({MONETARY_SYMBOL})", "Stock")
            tree_left = ttk.Treeview(left_frame, columns=cols, show="headings", height=15)
            for col in cols:
                tree_left.heading(col, text=col)
                tree_left.column(col, width=(50 if col == "ID" else 120))
            tree_left.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
            
            # Right: Selected pieces
            right_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            
            tk.Label(right_frame, text="Pièces sélectionnées", font=ProfessionalTheme.SUBTITLE_FONT, 
                    bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY).pack(pady=10)
            
            cols2 = ("Piece ID", "Nom", "Quantité", f"Prix unitaire ({MONETARY_SYMBOL})", f"Coût total ({MONETARY_SYMBOL})")
            tree_right = ttk.Treeview(right_frame, columns=cols2, show="headings", height=15)
            for col in cols2:
                tree_right.heading(col, text=col)
                tree_right.column(col, width=(80 if col == "Piece ID" else 110))
            tree_right.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
            
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
                
                # Remove from selected_pieces list
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
            
            # Middle button container
            middle_container = tk.Frame(main_container, bg=ProfessionalTheme.LIGHT)
            middle_container.pack(side=tk.LEFT, fill=tk.Y, padx=10)
            
            # Add piece button
            ttk.Button(middle_container, text="→ Ajouter", command=select_for_intervention, 
                      style="Success.TButton").pack(pady=5)
            
            # Remove piece button
            ttk.Button(middle_container, text="← Retirer", command=remove_from_intervention, 
                      style="Danger.TButton").pack(pady=5)
            
            # Bottom button container
            bottom_container = tk.Frame(pieces_window, bg=ProfessionalTheme.LIGHT)
            bottom_container.pack(fill=tk.X, padx=20, pady=(0, 20))
            
            ttk.Button(bottom_container, text="Valider", command=validate_selection, 
                      style="Primary.TButton").pack(side=tk.RIGHT)
            
            # Initially load pieces
            load_pieces_list()
        
        def view_intervention_details():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une intervention pour voir les détails")
                return
            
            values = tree.item(selected[0], 'values')
            intervention_id = values[0]
            
            # Check if details window already exists
            if f"intervention_details_{intervention_id}" in window_manager.windows:
                window_manager.windows[f"intervention_details_{intervention_id}"].lift()
                window_manager.windows[f"intervention_details_{intervention_id}"].focus_force()
                return
            
            def create_details_window():
                details_window = tk.Toplevel(history_window)
                details_window.title(f"Détails de l'intervention #{intervention_id}")
                details_window.geometry("700x500")
                details_window.configure(bg=ProfessionalTheme.LIGHT)
                
                # Header
                header_frame = tk.Frame(details_window, bg=ProfessionalTheme.PRIMARY, height=50)
                header_frame.pack(fill=tk.X)
                header_frame.pack_propagate(False)
                
                tk.Label(header_frame, text=f"Détails de l'intervention #{intervention_id}", 
                        font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                        fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
                
                # Details container
                details_container = tk.Frame(details_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                details_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
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
                basic_info = [
                    ("Date d'entrée:", intervention[0]),
                    ("Date de sortie:", intervention[1] or "N/A"),
                    ("Technicien:", intervention[2] or "N/A"),
                    (f"Coût total ({MONETARY_SYMBOL}):", f"{intervention[3]:.2f} {MONETARY_SYMBOL}")
                ]
                
                for i, (label, value) in enumerate(basic_info):
                    tk.Label(details_container, text=label, font=ProfessionalTheme.SUBTITLE_FONT, 
                            bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY, 
                            anchor="w").grid(row=i, column=0, sticky="w", pady=10, padx=20)
                    tk.Label(details_container, text=value, font=ProfessionalTheme.BODY_FONT, 
                            bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK, 
                            anchor="w").grid(row=i, column=1, sticky="w", pady=10, padx=(20, 20))
                
                # Details section
                tk.Label(details_container, text="Détails:", font=ProfessionalTheme.SUBTITLE_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY, 
                        anchor="nw").grid(row=4, column=0, sticky="nw", pady=10, padx=20)
                details_text = tk.Text(details_container, font=ProfessionalTheme.BODY_FONT, 
                                      width=50, height=6, wrap=tk.WORD, bd=1, relief="solid", 
                                      highlightthickness=0)
                details_text.grid(row=4, column=1, pady=10, padx=(20, 20))
                details_text.insert("1.0", intervention[4] or "")
                details_text.config(state=tk.DISABLED)
                
                # Pieces section
                if pieces:
                    tk.Label(details_container, text="Pièces utilisées:", font=ProfessionalTheme.SUBTITLE_FONT, 
                            bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY, 
                            anchor="w").grid(row=5, column=0, sticky="w", pady=10, padx=20)
                    
                    # Pieces table
                    pieces_frame = tk.Frame(details_container, bg=ProfessionalTheme.WHITE)
                    pieces_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 20), padx=20)
                    
                    pieces_cols = ("Nom", "Quantité", f"Prix unitaire ({MONETARY_SYMBOL})", f"Coût total ({MONETARY_SYMBOL})")
                    pieces_tree = ttk.Treeview(pieces_frame, columns=pieces_cols, show="headings", height=6)
                    for col in pieces_cols:
                        pieces_tree.heading(col, text=col)
                        pieces_tree.column(col, width=120)
                    pieces_tree.pack(fill=tk.BOTH, expand=True)
                    
                    for piece in pieces:
                        pieces_tree.insert("", tk.END, values=piece)
                
                details_container.columnconfigure(1, weight=1)
                
                return details_window
            
            window_manager.open_window(f"intervention_details_{intervention_id}", create_details_window)
        
        def add_intervention():
            nonlocal selected_pieces
            selected_pieces = []  # Reset selections
            
            def create_add_window():
                add_window = tk.Toplevel(history_window)
                add_window.title("Ajouter une intervention")
                add_window.geometry("600x600")
                add_window.configure(bg=ProfessionalTheme.LIGHT)
                
                # Header
                header_frame = tk.Frame(add_window, bg=ProfessionalTheme.PRIMARY, height=50)
                header_frame.pack(fill=tk.X)
                header_frame.pack_propagate(False)
                
                tk.Label(header_frame, text="Ajouter une intervention", 
                        font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                        fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
                
                # Form container
                form_container = tk.Frame(add_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
                # Form fields
                tk.Label(form_container, text="Date d'entrée *:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=0, column=0, sticky="w", padx=20, pady=12)
                entry_date_in = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                       bd=1, relief="solid", highlightthickness=0)
                entry_date_in.grid(row=0, column=1, padx=20, pady=12, sticky="ew")
                entry_date_in.insert(0, datetime.now().strftime("%Y-%m-%d"))
                
                tk.Label(form_container, text="Date de sortie:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=1, column=0, sticky="w", padx=20, pady=12)
                entry_date_out = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                        bd=1, relief="solid", highlightthickness=0)
                entry_date_out.grid(row=1, column=1, padx=20, pady=12, sticky="ew")
                
                tk.Label(form_container, text="Technicien:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=2, column=0, sticky="w", padx=20, pady=12)
                entry_technician = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                          bd=1, relief="solid", highlightthickness=0)
                entry_technician.grid(row=2, column=1, padx=20, pady=12, sticky="ew")
                
                tk.Label(form_container, text=f"Coût ({MONETARY_SYMBOL}):", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=3, column=0, sticky="w", padx=20, pady=12)
                entry_cost = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0)
                entry_cost.grid(row=3, column=1, padx=20, pady=12, sticky="ew")
                
                tk.Label(form_container, text="Détails:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=4, column=0, sticky="nw", padx=20, pady=12)
                text_details = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0, height=6)
                text_details.grid(row=4, column=1, padx=20, pady=12, sticky="ew")
                
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
                        total_cost = cost + sum(p['total_cost'] for p in selected_pieces)
                        c.execute("UPDATE interventions SET cout=? WHERE id=?", (total_cost, intervention_id))
                    
                    conn.commit()
                    conn.close()
                    
                    messagebox.showinfo("Succès", "Intervention enregistrée avec succès!")
                    add_window.destroy()
                    refresh_interventions()
                
                # Buttons
                button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
                button_frame.grid(row=5, column=0, columnspan=2, pady=20)
                
                ttk.Button(button_frame, text="Sélectionner pièces", 
                          command=lambda: manage_used_pieces(add_window), 
                          style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
                ttk.Button(button_frame, text="Sauvegarder", 
                          command=save_intervention, 
                          style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
                ttk.Button(button_frame, text="Annuler", 
                          command=add_window.destroy, 
                          style="Danger.TButton").pack(side=tk.LEFT)
                
                form_container.columnconfigure(1, weight=1)
                
                return add_window
            
            window_manager.open_window(f"add_intervention_{equipment_id}", create_add_window)
        
        def edit_intervention():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une intervention à modifier")
                return
            
            values = tree.item(selected[0], 'values')
            intervention_id = values[0]
            
            def create_edit_window():
                edit_window = tk.Toplevel(history_window)
                edit_window.title("Modifier une intervention")
                edit_window.geometry("600x600")
                edit_window.configure(bg=ProfessionalTheme.LIGHT)
                
                # Header
                header_frame = tk.Frame(edit_window, bg=ProfessionalTheme.PRIMARY, height=50)
                header_frame.pack(fill=tk.X)
                header_frame.pack_propagate(False)
                
                tk.Label(header_frame, text="Modifier une intervention", 
                        font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                        fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
                
                # Form container
                form_container = tk.Frame(edit_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
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
                
                # Form fields
                tk.Label(form_container, text="Date d'entrée *:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=0, column=0, sticky="w", padx=20, pady=12)
                entry_date_in = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                       bd=1, relief="solid", highlightthickness=0)
                entry_date_in.grid(row=0, column=1, padx=20, pady=12, sticky="ew")
                entry_date_in.insert(0, intervention[0] or "")
                
                tk.Label(form_container, text="Date de sortie:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=1, column=0, sticky="w", padx=20, pady=12)
                entry_date_out = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                        bd=1, relief="solid", highlightthickness=0)
                entry_date_out.grid(row=1, column=1, padx=20, pady=12, sticky="ew")
                entry_date_out.insert(0, intervention[1] or "")
                
                tk.Label(form_container, text="Technicien:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=2, column=0, sticky="w", padx=20, pady=12)
                entry_technician = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                          bd=1, relief="solid", highlightthickness=0)
                entry_technician.grid(row=2, column=1, padx=20, pady=12, sticky="ew")
                entry_technician.insert(0, intervention[2] or "")
                
                tk.Label(form_container, text=f"Coût ({MONETARY_SYMBOL}):", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=3, column=0, sticky="w", padx=20, pady=12)
                entry_cost = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0)
                entry_cost.grid(row=3, column=1, padx=20, pady=12, sticky="ew")
                entry_cost.insert(0, intervention[3] or "")
                
                tk.Label(form_container, text="Détails:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=4, column=0, sticky="nw", padx=20, pady=12)
                text_details = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0, height=6)
                text_details.grid(row=4, column=1, padx=20, pady=12, sticky="ew")
                text_details.insert("1.0", intervention[4] or "")
                
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
                    
                    # Restore stock for original pieces
                    for piece in original_pieces:
                        c.execute("SELECT quantite_stock FROM pieces WHERE id=?", (piece[0],))
                        current_stock = c.fetchone()[0]
                        new_stock = current_stock + piece[2]  # Add back the quantity
                        c.execute("UPDATE pieces SET quantite_stock=? WHERE id=?", (new_stock, piece[0]))
                    
                    # Delete original piece associations
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
                        # Check if a pieces window for this parent already exists
                        for child in parent_window.winfo_children():
                            if isinstance(child, tk.Toplevel) and hasattr(child, 'pieces_selection_edit'):
                                child.lift()
                                child.focus_force()
                                return
                        
                        # Create new window
                        pieces_window = tk.Toplevel(parent_window)
                        pieces_window.title("Gérer les pièces utilisées")
                        pieces_window.geometry("900x500")
                        pieces_window.configure(bg=ProfessionalTheme.LIGHT)
                        
                        # Add a custom attribute to identify this window type
                        pieces_window.pieces_selection_edit = True
                        
                        # Header
                        header_frame = tk.Frame(pieces_window, bg=ProfessionalTheme.PRIMARY, height=50)
                        header_frame.pack(fill=tk.X)
                        header_frame.pack_propagate(False)
                        
                        tk.Label(header_frame, text="Gérer les pièces utilisées", 
                                font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                                fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
                        
                        # Main container
                        main_container = tk.Frame(pieces_window, bg=ProfessionalTheme.LIGHT)
                        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                        
                        # Left: All available pieces
                        left_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
                        
                        tk.Label(left_frame, text="Pièces disponibles", font=ProfessionalTheme.SUBTITLE_FONT, 
                                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY).pack(pady=10)
                        
                        cols = ("ID", "Nom", "Réf", f"Prix ({MONETARY_SYMBOL})", "Stock")
                        tree_left = ttk.Treeview(left_frame, columns=cols, show="headings", height=15)
                        for col in cols:
                            tree_left.heading(col, text=col)
                            tree_left.column(col, width=(50 if col == "ID" else 120))
                        tree_left.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
                        
                        # Right: Currently selected pieces
                        right_frame = tk.Frame(main_container, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
                        
                        tk.Label(right_frame, text="Pièces sélectionnées", font=ProfessionalTheme.SUBTITLE_FONT, 
                                bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.PRIMARY).pack(pady=10)
                        
                        cols2 = ("Piece ID", "Nom", "Quantité", f"Prix unitaire ({MONETARY_SYMBOL})", f"Coût total ({MONETARY_SYMBOL})")
                        tree_right = ttk.Treeview(right_frame, columns=cols2, show="headings", height=15)
                        for col in cols2:
                            tree_right.heading(col, text=col)
                            tree_right.column(col, width=(80 if col == "Piece ID" else 110))
                        tree_right.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
                        
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
                            
                            # Remove from selected_pieces list
                            nonlocal selected_pieces
                            selected_pieces = [p for p in selected_pieces if p['piece_id'] != piece_id]
                            
                            # Refresh available pieces list
                            load_all_pieces()
                        
                        def save_selection():
                            pieces_window.destroy()
                            
                        # Middle button container
                        middle_container = tk.Frame(main_container, bg=ProfessionalTheme.LIGHT)
                        middle_container.pack(side=tk.LEFT, fill=tk.Y, padx=10)
                        
                        # Add piece button
                        ttk.Button(middle_container, text="→ Ajouter", command=add_piece, 
                                  style="Success.TButton").pack(pady=5)
                        
                        # Remove piece button
                        ttk.Button(middle_container, text="← Retirer", command=remove_piece, 
                                  style="Danger.TButton").pack(pady=5)
                        
                        # Bottom button container
                        bottom_container = tk.Frame(pieces_window, bg=ProfessionalTheme.LIGHT)
                        bottom_container.pack(fill=tk.X, padx=20, pady=(0, 20))
                        
                        ttk.Button(bottom_container, text="Valider", command=save_selection, 
                                  style="Primary.TButton").pack(side=tk.RIGHT)
                        
                        # Load data
                        load_all_pieces()
                        load_selected_pieces()
                    
                    manage_used_pieces_edit(edit_window)
                
                # Buttons
                button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
                button_frame.grid(row=5, column=0, columnspan=2, pady=20)
                
                ttk.Button(button_frame, text="Gérer les pièces", 
                          command=manage_pieces, 
                          style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
                ttk.Button(button_frame, text="Sauvegarder", 
                          command=save_edits, 
                          style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
                ttk.Button(button_frame, text="Annuler", 
                          command=edit_window.destroy, 
                          style="Danger.TButton").pack(side=tk.LEFT)
                
                form_container.columnconfigure(1, weight=1)
                
                return edit_window
            
            window_manager.open_window(f"edit_intervention_{intervention_id}", create_edit_window)
        
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
        
        # Add buttons after defining all functions
        ttk.Button(button_frame, text="➕ Ajouter Intervention", command=add_intervention, 
                  style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✏️ Modifier", command=edit_intervention, 
                  style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="👁 Voir Détails", command=view_intervention_details, 
                  style="Primary.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑 Supprimer", command=delete_intervention, 
                  style="Danger.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_interventions, 
                  style="Primary.TButton").pack(side=tk.LEFT)
        
        refresh_interventions()
        
        # Preventive Maintenance Tab
        maintenance_frame = ttk.Frame(notebook)
        notebook.add(maintenance_frame, text="Maintenance Préventive")
        
        # Button frame
        button_frame = tk.Frame(maintenance_frame, bg=ProfessionalTheme.LIGHT)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Table frame
        table_frame = tk.Frame(maintenance_frame, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        maint_columns = ("ID", "Date Prévue", "Type", "Technicien", "Statut", "Notes")
        tree_maint = ttk.Treeview(table_frame, columns=maint_columns, show="headings", height=12)
        for col in maint_columns:
            tree_maint.heading(col, text=col)
            tree_maint.column(col, width=(60 if col == "ID" else 140))
        tree_maint.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        maint_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree_maint.yview)
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
            def create_add_maint_window():
                add_maint_window = tk.Toplevel(history_window)
                add_maint_window.title("Planifier une maintenance")
                add_maint_window.geometry("500x500")
                add_maint_window.configure(bg=ProfessionalTheme.LIGHT)
                
                # Header
                header_frame = tk.Frame(add_maint_window, bg=ProfessionalTheme.PRIMARY, height=50)
                header_frame.pack(fill=tk.X)
                header_frame.pack_propagate(False)
                
                tk.Label(header_frame, text="Planifier une maintenance", 
                        font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                        fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
                
                # Form container
                form_container = tk.Frame(add_maint_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
                tk.Label(form_container, text="Date prévue *:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=0, column=0, sticky="w", padx=20, pady=12)
                entry_date = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                    bd=1, relief="solid", highlightthickness=0)
                entry_date.grid(row=0, column=1, padx=20, pady=12, sticky="ew")
                entry_date.insert(0, (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))
                
                tk.Label(form_container, text="Type de maintenance *:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=1, column=0, sticky="w", padx=20, pady=12)
                entry_type = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                    bd=1, relief="solid", highlightthickness=0)
                entry_type.grid(row=1, column=1, padx=20, pady=12, sticky="ew")
                
                tk.Label(form_container, text="Technicien:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=2, column=0, sticky="w", padx=20, pady=12)
                entry_tech = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0)
                entry_tech.grid(row=2, column=1, padx=20, pady=12, sticky="ew")
                
                tk.Label(form_container, text="Statut:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=3, column=0, sticky="w", padx=20, pady=12)
                combo_status = ttk.Combobox(form_container, values=["Planifié", "En cours", "Terminé"], state="readonly")
                combo_status.grid(row=3, column=1, padx=20, pady=12, sticky="ew")
                combo_status.set("Planifié")
                
                tk.Label(form_container, text="Notes:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=4, column=0, sticky="nw", padx=20, pady=12)
                text_notes = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                                   bd=1, relief="solid", highlightthickness=0, height=6)
                text_notes.grid(row=4, column=1, padx=20, pady=12, sticky="ew")
                
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
                
                button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
                button_frame.grid(row=5, column=0, columnspan=2, pady=20)
                
                ttk.Button(button_frame, text="Sauvegarder", command=save_maintenance, 
                          style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
                ttk.Button(button_frame, text="Annuler", command=add_maint_window.destroy, 
                          style="Danger.TButton").pack(side=tk.LEFT)
                
                form_container.columnconfigure(1, weight=1)
                
                return add_maint_window
            
            window_manager.open_window(f"add_maintenance_{equipment_id}", create_add_maint_window)
        
        def edit_maintenance():
            selected = tree_maint.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une maintenance à modifier")
                return
            
            values = tree_maint.item(selected[0], 'values')
            maintenance_id = values[0]
            
            def create_edit_maint_window():
                edit_maint_window = tk.Toplevel(history_window)
                edit_maint_window.title("Modifier une maintenance")
                edit_maint_window.geometry("500x500")
                edit_maint_window.configure(bg=ProfessionalTheme.LIGHT)
                
                # Header
                header_frame = tk.Frame(edit_maint_window, bg=ProfessionalTheme.PRIMARY, height=50)
                header_frame.pack(fill=tk.X)
                header_frame.pack_propagate(False)
                
                tk.Label(header_frame, text="Modifier une maintenance", 
                        font=ProfessionalTheme.SUBTITLE_FONT, bg=ProfessionalTheme.PRIMARY, 
                        fg=ProfessionalTheme.WHITE).pack(side=tk.LEFT, padx=20, pady=12)
                
                # Form container
                form_container = tk.Frame(edit_maint_window, bg=ProfessionalTheme.WHITE, relief="raised", bd=1)
                form_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
                # Load data
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''SELECT date_prevue, type_maintenance, technicien, statut, notes 
                             FROM planification WHERE id=?''', (maintenance_id,))
                maintenance = c.fetchone()
                conn.close()
                
                tk.Label(form_container, text="Date prévue *:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=0, column=0, sticky="w", padx=20, pady=12)
                entry_date = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                    bd=1, relief="solid", highlightthickness=0)
                entry_date.grid(row=0, column=1, padx=20, pady=12, sticky="ew")
                entry_date.insert(0, maintenance[0] or "")
                
                tk.Label(form_container, text="Type de maintenance *:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=1, column=0, sticky="w", padx=20, pady=12)
                entry_type = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                    bd=1, relief="solid", highlightthickness=0)
                entry_type.grid(row=1, column=1, padx=20, pady=12, sticky="ew")
                entry_type.insert(0, maintenance[1] or "")
                
                tk.Label(form_container, text="Technicien:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=2, column=0, sticky="w", padx=20, pady=12)
                entry_tech = tk.Entry(form_container, font=ProfessionalTheme.BODY_FONT, 
                                     bd=1, relief="solid", highlightthickness=0)
                entry_tech.grid(row=2, column=1, padx=20, pady=12, sticky="ew")
                entry_tech.insert(0, maintenance[2] or "")
                
                tk.Label(form_container, text="Statut:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=3, column=0, sticky="w", padx=20, pady=12)
                combo_status = ttk.Combobox(form_container, values=["Planifié", "En cours", "Terminé"], state="readonly")
                combo_status.grid(row=3, column=1, padx=20, pady=12, sticky="ew")
                combo_status.set(maintenance[3] or "Planifié")
                
                tk.Label(form_container, text="Notes:", font=ProfessionalTheme.BODY_FONT, 
                        bg=ProfessionalTheme.WHITE, fg=ProfessionalTheme.DARK).grid(
                    row=4, column=0, sticky="nw", padx=20, pady=12)
                text_notes = tk.Text(form_container, font=ProfessionalTheme.BODY_FONT, 
                                   bd=1, relief="solid", highlightthickness=0, height=6)
                text_notes.grid(row=4, column=1, padx=20, pady=12, sticky="ew")
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
                
                button_frame = tk.Frame(form_container, bg=ProfessionalTheme.WHITE)
                button_frame.grid(row=5, column=0, columnspan=2, pady=20)
                
                ttk.Button(button_frame, text="Sauvegarder", command=save_edits, 
                          style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
                ttk.Button(button_frame, text="Annuler", command=edit_maint_window.destroy, 
                          style="Danger.TButton").pack(side=tk.LEFT)
                
                form_container.columnconfigure(1, weight=1)
                
                return edit_maint_window
            
            window_manager.open_window(f"edit_maintenance_{maintenance_id}", create_edit_maint_window)
        
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
        
        # Add buttons after defining all functions
        ttk.Button(button_frame, text="➕ Planifier Maintenance", command=add_maintenance, 
                  style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✏️ Modifier", command=edit_maintenance, 
                  style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑 Supprimer", command=delete_maintenance, 
                  style="Danger.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Rafraîchir", command=refresh_maintenance, 
                  style="Primary.TButton").pack(side=tk.LEFT)
        
        refresh_maintenance()
        
        return history_window
    
    # Use the window manager to open/create the window
    return window_manager.open_window(f"equipment_history_{equipment_id}", create_history_window)

# Initialize database and start application
if __name__ == "__main__":
    init_db()
    authentication()