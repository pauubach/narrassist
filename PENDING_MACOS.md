# Tareas pendientes que requieren macOS

Estas tareas no se pueden completar sin acceso a hardware macOS real.

## 1. Hardened Runtime + Entitlements

- Activar `hardenedRuntime: true` en `src-tauri/tauri.conf.json` (sección `bundle > macOS`)
- Crear archivo `src-tauri/Entitlements.plist` con los permisos necesarios:
  - `com.apple.security.cs.allow-unsigned-executable-memory` (para Python embebido)
  - `com.apple.security.cs.disable-library-validation` (para cargar dylibs de Python)
  - `com.apple.security.files.user-selected.read-write` (acceso a archivos del usuario)
- Verificar que la app arranca correctamente con hardened runtime activado

## 2. Firma y notarización en CI

- Configurar secrets en GitHub Actions:
  - `APPLE_CERTIFICATE` (p12 base64)
  - `APPLE_CERTIFICATE_PASSWORD`
  - `APPLE_SIGNING_IDENTITY`
  - `APPLE_ID` + `APPLE_PASSWORD` (o App-Specific Password)
  - `APPLE_TEAM_ID`
- Añadir paso de `codesign` y `xcrun notarytool submit` en `build-release.yml` job `build-macos`
- Verificar que el DMG pasa Gatekeeper (`spctl --assess`)

## 3. Validación del build macOS en hardware real

- Instalar el DMG generado por CI en una Mac limpia
- Verificar:
  - La app arranca sin warnings de Gatekeeper
  - Python embebido (Framework) funciona correctamente
  - Los modelos NLP se descargan al primer uso
  - Ollama se conecta correctamente
  - El análisis de documentos funciona end-to-end
