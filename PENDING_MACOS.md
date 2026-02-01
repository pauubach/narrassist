# Tareas pendientes que requieren macOS

Estas tareas no se pueden completar sin acceso a hardware macOS real.

## 1. ✅ Hardened Runtime + Entitlements (COMPLETADO)

- ✅ `hardenedRuntime: true` en `src-tauri/tauri.conf.json`
- ✅ `signingIdentity: "-"` (firma ad-hoc, sin Apple Developer Program)
- ✅ `Entitlements.plist` creado con permisos para Python embebido

## 2. Firma y notarización

**NO APLICA** - Sin Apple Developer Program ($99/año), la app no puede ser firmada ni notarizada.

Los usuarios deberán:
- Click derecho → Abrir (primera vez) para bypass de Gatekeeper
- Esto es comportamiento estándar para apps no firmadas

## 3. Validación del build macOS en hardware real

- [ ] Descargar el DMG generado por GitHub Actions
- [ ] Instalar en Mac y verificar:
  - [ ] La app arranca (con bypass de Gatekeeper: click derecho → Abrir)
  - [ ] Python embebido (Framework) funciona correctamente
  - [ ] Los modelos NLP se descargan al primer uso
  - [ ] Ollama se conecta correctamente
  - [ ] El análisis de documentos funciona end-to-end
