#!/bin/bash
# Launcher para backend con Python embebido en macOS/Linux
# Este script inicia el servidor FastAPI usando Python embebido/portable

set -e

# Obtener el directorio de este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Paths relativos
PYTHON_EMBED="$SCRIPT_DIR/python-embed"
BACKEND_DIR="$SCRIPT_DIR/backend"
MAIN_PY="$BACKEND_DIR/api-server/main.py"

# Detectar sistema operativo y configurar Python
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: usar Python.framework o python3 link
    if [ -f "$PYTHON_EMBED/python3" ]; then
        PYTHON_CMD="$PYTHON_EMBED/python3"
    elif [ -f "$PYTHON_EMBED/Python.framework/Versions/Current/bin/python3" ]; then
        PYTHON_CMD="$PYTHON_EMBED/Python.framework/Versions/Current/bin/python3"
    else
        echo "ERROR: Python embebido no encontrado en $PYTHON_EMBED"
        exit 1
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux: usar python3 portable o del sistema
    if [ -f "$PYTHON_EMBED/python3" ]; then
        PYTHON_CMD="$PYTHON_EMBED/python3"
    else
        # Fallback a Python del sistema
        PYTHON_CMD="python3"
    fi
else
    echo "ERROR: Sistema operativo no soportado: $OSTYPE"
    exit 1
fi

# Verificar que Python existe
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "ERROR: Python no encontrado en $PYTHON_CMD"
    exit 1
fi

# Verificar que backend existe
if [ ! -f "$MAIN_PY" ]; then
    echo "ERROR: Backend no encontrado en $MAIN_PY"
    exit 1
fi

# Cambiar al directorio del backend
cd "$BACKEND_DIR/api-server"

# Set PYTHONPATH to include backend directories
export PYTHONPATH="$BACKEND_DIR:$BACKEND_DIR/api-server:$PYTHONPATH"

# Ejecutar main.py directamente
exec "$PYTHON_CMD" "$MAIN_PY"
