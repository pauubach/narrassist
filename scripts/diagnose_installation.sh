#!/usr/bin/env bash
set -euo pipefail

TOOLS_DIR="$HOME/Library/Application Support/Narrative Assistant/tools"
LT_URLS=(
  "https://github.com/languagetool-org/languagetool/releases/download/v6.4/LanguageTool-6.4.zip"
  "https://languagetool.org/download/LanguageTool-6.4.zip"
  "https://www.languagetool.org/download/LanguageTool-6.4.zip"
)
OLLAMA_URL="https://ollama.com/download/Ollama-darwin.zip"

echo "== Sistema =="
uname -a || true
python3 --version || true

echo
echo "== Comprobaciones de red (timeout 10s) =="
for url in "${LT_URLS[@]}"; do
  echo
  echo "Probando: $url"
  if command -v curl >/dev/null 2>&1; then
    curl -I --max-time 10 -sS "$url" | head -n 5 || echo "curl fallo";
  else
    python3 - <<PY
import sys, urllib.request
url = sys.argv[1]
try:
    req=urllib.request.Request(url, headers={"User-Agent":"curl/7.0"})
    r=urllib.request.urlopen(req, timeout=10)
    print('HTTP', r.status)
except Exception as e:
    print('ERR', e)
PY
  fi
done

echo
echo "Probando Ollama URL: $OLLAMA_URL"
if command -v curl >/dev/null 2>&1; then
  curl -I --max-time 10 -sS "$OLLAMA_URL" | head -n 5 || echo "curl fallo";
else
  python3 - <<PY
import sys, urllib.request
url = sys.argv[1]
try:
    req=urllib.request.Request(url, headers={"User-Agent":"curl/7.0"})
    r=urllib.request.urlopen(req, timeout=10)
    print('HTTP', r.status)
except Exception as e:
    print('ERR', e)
PY
fi

echo
echo "== Tools dir =="
if [ -d "$TOOLS_DIR" ]; then
  echo "Existe: $TOOLS_DIR"
  ls -lah "$TOOLS_DIR" || true
else
  echo "No existe: $TOOLS_DIR"
fi

echo
echo "== Buscar archivos parciales de LanguageTool =="
find "$HOME" -maxdepth 3 -type f -name 'LanguageTool-*.zip' -print -exec ls -lh {} \; || true

echo
echo "== Java =="
if command -v java >/dev/null 2>&1; then
  java -version 2>&1 | sed -n '1,3p'
else
  echo "java no en PATH"
fi

if [ -d "$TOOLS_DIR/java" ]; then
  echo "Java local en: $TOOLS_DIR/java"
  ls -lah "$TOOLS_DIR/java" || true
fi

echo
echo "== Ollama =="
if command -v ollama >/dev/null 2>&1; then
  echo "ollama en PATH: $(which ollama)"
  ollama version 2>/dev/null || true
else
  echo "ollama no encontrado en PATH"
fi

echo
echo "Procesos relacionados (ollama, java, Narrative Assistant)"
ps aux | egrep 'ollama|languagetool|Narrative Assistant|narrative_assistant' || true

echo
echo "== Recomendaciones rápidas =="
cat <<EOF
- Si las comprobaciones a los mirrors fallan (timeout o HTTP error), prueba desde este equipo abrir esas URLs en un navegador.
- Puedes ejecutar manualmente la instalación de LanguageTool con:
    python3 scripts/setup_languagetool.py
  y revisar la salida para ver el error concreto.
- Para Ollama en macOS: si tienes Homebrew instalado, ejecutar:
    brew install ollama
  o seguir la instrucción oficial:
    curl -fsSL https://ollama.com/install.sh | sh
- Si tu red usa proxy/empresa, exporta las variables HTTP_PROXY/HTTPS_PROXY antes de ejecutar los scripts.
- Si la app sigue mostrando "sin conexión", pega aquí la salida completa de este script y la salida de la consola de la app (si hay).
EOF

exit 0
