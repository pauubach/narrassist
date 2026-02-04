#!/bin/bash
# Script para generar claves de firma de Tauri
# Ejecutar en Mac o Linux (no funciona en Windows)

set -e

echo "=== Generando claves de firma de Tauri ==="
echo ""

# Verificar que cargo está instalado
if ! command -v cargo &> /dev/null; then
    echo "ERROR: Rust/Cargo no está instalado"
    echo "Instalar con: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# Instalar tauri-cli si no existe
if ! cargo tauri --version &> /dev/null; then
    echo "Instalando tauri-cli..."
    cargo install tauri-cli
fi

# Crear directorio para las claves
mkdir -p ~/.tauri-keys

# Generar claves
echo ""
echo "Generando par de claves..."
echo "IMPORTANTE: Guarda la contraseña que introduzcas!"
echo ""

cargo tauri signer generate -w ~/.tauri-keys/narrative-assistant.key

echo ""
echo "=== Claves generadas ==="
echo ""
echo "Archivo de clave privada: ~/.tauri-keys/narrative-assistant.key"
echo "Archivo de clave pública: ~/.tauri-keys/narrative-assistant.key.pub"
echo ""
echo "=== Para configurar en GitHub ==="
echo ""
echo "1. Copia el contenido de la clave privada:"
echo "   cat ~/.tauri-keys/narrative-assistant.key"
echo ""
echo "2. Ve a: https://github.com/TU_USUARIO/TU_REPO/settings/secrets/actions"
echo ""
echo "3. Añade estos secrets:"
echo "   - TAURI_SIGNING_PRIVATE_KEY: (contenido de narrative-assistant.key)"
echo "   - TAURI_SIGNING_PRIVATE_KEY_PASSWORD: (la contraseña que pusiste)"
echo ""
echo "4. Copia la clave pública para tauri.conf.json:"
echo "   cat ~/.tauri-keys/narrative-assistant.key.pub"
echo ""
