#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-/Applications/Narrative Assistant.app}"
LABEL="NarrativeAssistant"

if [ ! -e "$APP_PATH" ]; then
  echo "App no encontrada en: $APP_PATH"
  exit 2
fi

echo "Ruta de la app: $APP_PATH"

echo "--- ATTRIBUTES (com.apple.quarantine) ---"
if xattr -p com.apple.quarantine "$APP_PATH" 2>/dev/null; then
  echo "(La app tiene el atributo com.apple.quarantine)"
else
  echo "(No hay atributo com.apple.quarantine en el paquete principal)"
fi

echo "--- REMOVING quarantine recursively ---"
if sudo xattr -r -d com.apple.quarantine "$APP_PATH"; then
  echo "Atributo com.apple.quarantine eliminado (recursivo)."
else
  echo "No se pudo eliminar com.apple.quarantine en todos los ficheros. Continua." >&2
fi

echo "--- ASSESS Gatekeeper ---"
SPCTL_OUT=$(spctl --assess --type execute -v "$APP_PATH" 2>&1 || true)
echo "$SPCTL_OUT"

if echo "$SPCTL_OUT" | grep -q "accepted"; then
  echo "Gatekeeper: aceptada. Prueba a abrir la app (Control‑clic → Abrir si hace falta)."
  exit 0
fi

if echo "$SPCTL_OUT" | grep -q "rejected"; then
  echo "Gatekeeper: rechazada. Intentando añadir excepción con spctl..."
  if sudo spctl --add --label "$LABEL" "$APP_PATH"; then
    echo "Añadida la app con etiqueta $LABEL. Habilitando etiqueta..."
    sudo spctl --enable --label "$LABEL" || true
    echo "Re-evaluando..."
    spctl --assess --type execute -v "$APP_PATH" 2>&1 || true
    echo "Si sigue rechazando, prueba abrirla desde Finder con Control‑clic → Abrir, o revisa Preferencias del Sistema → Seguridad y privacidad → General para permitirla." 
    exit 0
  else
    echo "spctl --add falló. Puede que la app requiera firma/notarización." >&2
  fi
fi

cat <<'EOF'
Si la app sigue bloqueada, opciones adicionales:
- Abrir con Control‑clic → Abrir en Finder y pulsar "Abrir".
- Copiar la app fuera del volumen (por ejemplo desde un .dmg) con:
    sudo ditto "<origen>" "/Applications/Narrative Assistant.app"
  y luego volver a ejecutar este script.
- Como último recurso (temporal), puedes desactivar Gatekeeper:
    sudo spctl --master-disable
  abrir la app, y luego reactivar:
    sudo spctl --master-enable
  NO se recomienda a largo plazo.
EOF

exit 1
