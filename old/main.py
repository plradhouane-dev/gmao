# === main.py ===
from functions import init_db
from gui import authentification



if __name__ == '__main__':
    # Initialize encrypted database structure
    init_db()
    # Launch authentication window
    authentification()
