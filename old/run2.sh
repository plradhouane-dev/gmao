#!/bin/bash

# run.sh - Script de lancement de l'application GMAO

echo "🚀 Lancement de l'application GMAO..."

# Vérifier les modules requis
echo "🔍 Vérification des prérequis système..."

if ! python3 -c "import tkinter; import sqlite3" 2>/dev/null; then
    echo "❌ tkinter ou sqlite3 non disponibles"
    echo "💡 Ces modules font partie de Python standard."
    echo "   Sur Linux: sudo apt-get install python3-tk"
    exit 1
fi

echo "✅ tkinter et sqlite3 disponibles"

# Vérifier si l'environnement virtuel est activé
if [ -z "$VIRTUAL_ENV" ]; then
    echo "📦 Activation de l'environnement virtuel..."
    
    if [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        echo "❌ Environnement virtuel non trouvé. Exécutez d'abord setup.sh"
        exit 1
    fi
fi

# Vérifier cryptography
if ! python3 -c "import cryptography" 2>/dev/null; then
    echo "❌ cryptography manquant. Exécutez setup.sh"
    exit 1
fi

echo "✅ cryptography disponible"

# Vérifier si le fichier principal existe
if [ ! -f "gmao_app.py" ]; then
    echo "❌ Fichier gmao_app.py introuvable"
    exit 1
fi

# Lancer l'application
echo "✅ Démarrage de l'interface GMAO..."
echo "🔐 Mot de passe par défaut: admin123"
echo ""

python3 main.py