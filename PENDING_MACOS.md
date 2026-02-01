# Estado de macOS

## ✅ Completado

- **Hardened Runtime + Entitlements**: Configurado en `tauri.conf.json` y `Entitlements.plist`
- **Firma ad-hoc**: `signingIdentity: "-"` permite que la app funcione sin certificado

## ⛔ No aplicable (requiere Apple Developer Program $99/año)

- Firma con certificado de Apple
- Notarización
- Bypass automático de Gatekeeper

**Limitación permanente:** Los usuarios deberán hacer "click derecho → Abrir" la primera vez.

## 🔲 Pendiente: Validación del build

- [ ] Descargar el DMG generado por GitHub Actions
- [ ] Instalar en Mac (click derecho → Abrir para bypass Gatekeeper)
- [ ] Verificar:
  - [ ] La app arranca correctamente
  - [ ] Python embebido (Framework) funciona
  - [ ] Los modelos NLP se descargan al primer uso
  - [ ] Ollama se conecta correctamente
  - [ ] El análisis de documentos funciona end-to-end
