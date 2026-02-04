# Estado de macOS

## ✅ Completado

- **Hardened Runtime + Entitlements**: Configurado en `tauri.conf.json` y `Entitlements.plist`
- **Firma ad-hoc**: `signingIdentity: "-"` permite que la app funcione sin certificado
- **Python Framework Embedding**: Script de parcheo para rutas relativas implementado

## 🐛 Bug Crítico Encontrado y Solucionado

### Problema
El backend no arrancaba en macOS porque el ejecutable `python3` embebido tenía rutas absolutas hardcodeadas:

```bash
# Error:
dyld: Library not loaded: /Library/Frameworks/Python.framework/Versions/3.12/Python
```

**Causa raíz:**
- El .pkg oficial de Python instala el framework con rutas absolutas en los binarios
- Al extraer y embebed el framework, estas rutas apuntaban a ubicaciones inexistentes
- Los ejecutables necesitaban ser parcheados con `install_name_tool` para usar rutas relativas

### Solución Implementada

**Nuevo script:** [`scripts/patch_macos_python.py`](scripts/patch_macos_python.py)

El script parchea automáticamente:
1. La librería `Python.framework/Versions/3.12/Python` - ID cambiado a `@rpath`
2. Los ejecutables `python3` - rutas cambiadas a `@executable_path`
3. Todos los módulos `.so` en `lib-dynload/` - rutas relativas a `@loader_path`
4. Las bibliotecas `.dylib` - IDs y dependencias actualizadas
5. Añade RPATHs necesarios a los ejecutables
6. Re-firma con ad-hoc signing (`codesign -s -`)

**Integración:**
- `download_python_embed.py` llama automáticamente al script de parcheo
- GitHub Actions ejecuta el parcheo como paso explícito

**Archivos modificados:**
- ✅ `scripts/patch_macos_python.py` (nuevo)
- ✅ `scripts/download_python_embed.py` (actualizado)
- ✅ `.github/workflows/build-release.yml` (actualizado)

## ⛔ No aplicable (requiere Apple Developer Program $99/año)

- Firma con certificado de Apple
- Notarización
- Bypass automático de Gatekeeper

**Limitación permanente:** Los usuarios deberán hacer "click derecho → Abrir" la primera vez.

## 🔲 Siguiente: Validación del build corregido

- [ ] Rebuildd el DMG con el fix aplicado
- [ ] Descargar e instalar en Mac (click derecho → Abrir)
- [ ] Verificar:
  - [ ] La app arranca correctamente
  - [ ] **Python embebido funciona sin errores dyld**
  - [ ] Backend inicia y responde en http://localhost:8008
  - [ ] Los modelos NLP se descargan al primer uso
  - [ ] Ollama se conecta correctamente
  - [ ] El análisis de documentos funciona end-to-end
