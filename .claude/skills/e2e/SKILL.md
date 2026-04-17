---
name: e2e
description: "Ejecuta los tests end-to-end con Playwright (Tauri/Electron o web). Puede usar el MCP de Playwright para navegación interactiva si los tests fallan y hay que depurar. Invocar cuando el usuario diga 'corre e2e', 'tests de playwright', 'prueba el flujo de X', 'qué falla en e2e'."
---

# /e2e — Tests end-to-end con Playwright

## Cuándo usar

- Validar flujos completos antes de una release (export, import, análisis).
- Cuando un test unitario pasa pero el flujo real parece roto.
- Para reproducir un bug reportado por el usuario paso a paso.
- Antes de `/ship` si hay cambios en componentes de workflow crítico.

## Argumentos

- (sin args) — todos los tests e2e
- `<spec>` — archivo o patrón específico, p.ej. `export-import-editorial`, `analysis-flow`
- `--headed` — modo visible (útil para debug)
- `--debug` — tras un fallo, usar MCP Playwright para inspección interactiva
- `--ui` — abrir Playwright UI (interactivo, requiere display)

## Flujo

### Paso 1 — Verificar que hay servidor disponible

Los tests e2e de Tauri requieren que la app esté corriendo o que el test levante el servidor internamente. Verificar el `playwright.config.ts`:

```bash
cat /Users/PABLO/repos/narrassist/frontend/playwright.config.ts 2>/dev/null | head -40
```

### Paso 2 — Ejecutar tests

```bash
cd /Users/PABLO/repos/narrassist/frontend && npx playwright test <spec> 2>&1
```

Con flags opcionales según argumentos:
- `--headed` → `npx playwright test --headed`
- `--debug` → `npx playwright test --debug`

### Paso 3 — Parsear resultado

Del output de Playwright extraer:
- Tests pasados / fallados / skipped
- Para cada fallo: nombre del test + mensaje de error + paso donde falló

### Paso 4 — Si hay fallos: investigar con MCP Playwright

Si se pasó `--debug` o el usuario quiere investigar interactivamente:

```
mcp__playwright__browser_navigate(url: "http://localhost:5173")
mcp__playwright__browser_snapshot()  # accesibility snapshot del DOM
```

Navegar el flujo fallido manualmente:
```
mcp__playwright__browser_click(element: "<selector>")
mcp__playwright__browser_fill_form(fields: {...})
mcp__playwright__browser_take_screenshot()
```

Usar `mcp__playwright__browser_console_messages()` para capturar errores JS que no aparecen en el output de Playwright.

### Paso 5 — Output

```
## E2E Results — <fecha>

| Test | Estado | Duración |
|------|--------|----------|
| export-import-editorial.spec.ts > flujo completo | ✅ | 8.2s |
| export-advanced.spec.ts > exportar DOCX con capítulos | ❌ | 12.1s |
| analysis-flow.spec.ts > análisis spaCy | ✅ | 15.4s |

### Fallos

#### export-advanced.spec.ts > exportar DOCX con capítulos
Error: locator('[data-test="export-format-select"]') not found
Paso: seleccionar formato DOCX
Screenshot: (ver arriba)

Causa probable: el selector cambió en el último refactor (buscar `data-test="export-format"` en ExportDialog.vue)
```

### Paso 6 — Proponer fix (si es obvio)

Si el fallo es un selector roto o una regresión de CSS, identificar el archivo y línea. No arreglar directamente — proponer el fix y esperar OK del usuario (puede ser una regresión real que hay que investigar).
