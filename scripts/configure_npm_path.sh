#!/bin/bash
# Script para añadir Node.js/npm al PATH de Git Bash
# Ejecutar con: bash scripts/configure_npm_path.sh

echo "========================================"
echo " Configurando npm en Git Bash"
echo "========================================"
echo ""

# Detectar ubicación de Node.js
NODE_PATH_COMMON="/c/Program Files/nodejs"
NODE_PATH_ALT="/c/Program Files (x86)/nodejs"
NODE_PATH_USER="$HOME/AppData/Local/Programs/nodejs"

NODE_PATH=""

if [ -d "$NODE_PATH_COMMON" ]; then
    NODE_PATH="$NODE_PATH_COMMON"
elif [ -d "$NODE_PATH_ALT" ]; then
    NODE_PATH="$NODE_PATH_ALT"
elif [ -d "$NODE_PATH_USER" ]; then
    NODE_PATH="$NODE_PATH_USER"
else
    echo "[ERROR] Node.js no encontrado en ubicaciones comunes"
    echo ""
    echo "Ubicaciones verificadas:"
    echo "  - $NODE_PATH_COMMON"
    echo "  - $NODE_PATH_ALT"
    echo "  - $NODE_PATH_USER"
    echo ""
    echo "Solución manual:"
    echo "  1. Encuentra donde está instalado Node.js:"
    echo "     where node (en PowerShell)"
    echo "  2. Añade al PATH en ~/.bashrc:"
    echo "     export PATH=\"/c/ruta/a/nodejs:\$PATH\""
    exit 1
fi

echo "[OK] Node.js encontrado en: $NODE_PATH"
echo ""

# Verificar si ya está en el PATH
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "[OK] npm ya está disponible (versión $NPM_VERSION)"
    echo ""
    echo "No es necesario configurar PATH."
    exit 0
fi

# Añadir a ~/.bashrc si no existe
if grep -q "$NODE_PATH" ~/.bashrc 2>/dev/null; then
    echo "[INFO] PATH ya está configurado en ~/.bashrc"
else
    echo "[1/2] Añadiendo Node.js al PATH en ~/.bashrc..."
    echo "" >> ~/.bashrc
    echo "# Node.js / npm (añadido $(date +%Y-%m-%d))" >> ~/.bashrc
    echo "export PATH=\"$NODE_PATH:\$PATH\"" >> ~/.bashrc
    echo "[OK] PATH añadido a ~/.bashrc"
fi

# Cargar en la sesión actual
echo "[2/2] Cargando PATH en la sesión actual..."
export PATH="$NODE_PATH:$PATH"

# Verificar
if command -v npm &> /dev/null; then
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    echo ""
    echo "========================================"
    echo " ✓ Configuración completada"
    echo "========================================"
    echo ""
    echo "Node.js: $NODE_VERSION"
    echo "npm: $NPM_VERSION"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Reinicia la terminal (o ejecuta: source ~/.bashrc)"
    echo "  2. Verifica: npm --version"
    echo "  3. Instala dependencias: cd frontend && npm install"
    echo "  4. Configura tests: npm run test:setup (próximamente)"
    echo ""
else
    echo ""
    echo "[ERROR] npm aún no está disponible"
    echo ""
    echo "Solución:"
    echo "  1. Cierra TODAS las terminales"
    echo "  2. Abre una nueva terminal"
    echo "  3. Ejecuta: npm --version"
    echo ""
fi
