# functions.py
import os
import sqlite3
from cryptography.fernet import Fernet

# === CONFIGURATION ===
KEY_FILE = 'secret.key'
DB_FILE = 'gmao_encrypted.db'
INITIAL_PASSWORD = 'admin123'  # Default admin password

# === ENCRYPTION UTILITIES ===
def load_key():
    """Load or generate an encryption key."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key

def encrypt_data(data: str) -> bytes:
    """Encrypt plain text data."""
    key = load_key()
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(token: bytes) -> str:
    """Decrypt encrypted data."""
    key = load_key()
    f = Fernet(key)
    return f.decrypt(token).decode()

# === DATABASE INITIALIZATION ===
def init_db():
    """Create or reset the database with necessary tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Drop old tables (optional for reset)
    c.execute("DROP TABLE IF EXISTS equipements")
    c.execute("DROP TABLE IF EXISTS interventions")

    # Create tables
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

# === PASSWORD CHECK ===
def verify_password(password: str) -> bool:
    """Verify if entered password matches admin password."""
    return password == INITIAL_PASSWORD
