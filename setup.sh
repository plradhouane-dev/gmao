#!/bin/bash

# setup.sh - Script d'installation automatique pour GMAO

echo "🔧 Installation de l'application GMAO..."

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    echo "📥 Téléchargez Python depuis: https://www.python.org/downloads/"
    exit 1
fi

# Afficher la version de Python
python_version=$(python3 --version)
echo "✅ $python_version"

# Vérifier tkinter et sqlite3
echo "🔍 Vérification des modules Python requis..."

if ! python3 -c "import tkinter; import sqlite3" 2>/dev/null; then
    echo "❌ tkinter ou sqlite3 non disponibles"
    echo "💡 Solutions possibles :"
    echo "   Sur Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "   Sur CentOS/RHEL: sudo yum install python3-tkinter"
    echo "   Sur Windows: tkinter est inclus dans l'installation standard"
    exit 1
fi

echo "✅ tkinter et sqlite3 disponibles"

# Créer l'environnement virtuel
echo "📦 Création de l'environnement virtuel..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "❌ Échec de la création de l'environnement virtuel"
    exit 1
fi

# Activer l'environnement virtuel
echo "🚀 Activation de l'environnement virtuel..."
source venv/Scripts/activate

# Mettre à jour pip
echo "📥 Mise à jour de pip..."
pip install --upgrade pip

# Installer les dépendances
if [ -f "requirements.txt" ]; then
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
else
    echo "📦 Installation de cryptography..."
    pip install cryptography
fi

# Vérification finale
echo "✅ Vérification finale de l'installation..."

modules=("tkinter" "sqlite3" "cryptography")
all_good=true

for module in "${modules[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        echo "✅ $module disponible"
    else
        echo "❌ $module non disponible"
        all_good=false
    fi
done

if [ "$all_good" = false ]; then
    echo "❌ Certains modules sont manquants"
    exit 1
fi

echo "🎉 Installation terminée avec succès !"
echo ""
echo "🚀 Pour lancer l'application :"
echo "   ./run.sh"
echo "   OU"
echo "   source venv/Scripts/activate"
echo "   python3 gmao_app.py"