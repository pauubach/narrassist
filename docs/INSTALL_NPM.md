# Instalación de Node.js/npm para Frontend Testing

**Fecha**: 2026-02-22
**Requisito**: Frontend unit testing bloqueado sin npm

---

## Opción 1: Script Automático (Windows PowerShell)

### Paso 1: Ejecutar Script de Instalación

```powershell
# Desde el directorio raíz del proyecto
powershell -ExecutionPolicy Bypass -File scripts\install_nodejs.ps1
```

El script:
- ✅ Descarga Node.js LTS (v20.11.0)
- ✅ Instala automáticamente
- ✅ Verifica la instalación
- ✅ Muestra próximos pasos

### Paso 2: Reiniciar Terminal

**IMPORTANTE**: Debes cerrar y reabrir VS Code / terminal para que el PATH se actualice.

### Paso 3: Verificar

```bash
node --version  # Debería mostrar v20.x.x
npm --version   # Debería mostrar 10.x.x
```

---

## Opción 2: Instalación Manual

### Windows

1. **Descargar Node.js**:
   - Visita https://nodejs.org/
   - Descarga la versión **LTS** (Recommended For Most Users)
   - Ejecuta el instalador `.msi`

2. **Instalar**:
   - Acepta todas las opciones por defecto
   - **IMPORTANTE**: Marca la casilla "Automatically install the necessary tools" si aparece

3. **Verificar**:
   ```bash
   node --version
   npm --version
   ```

4. **Si no funciona en Git Bash**:
   - Cierra TODAS las ventanas de terminal/PowerShell/Git Bash
   - Abre una nueva terminal
   - Si sigue sin funcionar, añade manualmente al PATH:
     ```
     C:\Program Files\nodejs\
     ```

### Linux/macOS

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS (Homebrew)
brew install node@20

# Verificar
node --version
npm --version
```

---

## Opción 3: nvm (Node Version Manager) - Recomendado

### Windows (nvm-windows)

```powershell
# 1. Descargar nvm-windows desde:
# https://github.com/coreybutler/nvm-windows/releases

# 2. Instalar la última versión (nvm-setup.exe)

# 3. Cerrar y reabrir terminal

# 4. Instalar Node.js LTS
nvm install 20
nvm use 20

# 5. Verificar
node --version
npm --version
```

### Linux/macOS (nvm)

```bash
# Instalar nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Recargar shell
source ~/.bashrc  # o ~/.zshrc

# Instalar Node.js LTS
nvm install 20
nvm use 20

# Verificar
node --version
npm --version
```

---

## Post-Instalación: Configurar Frontend Testing

### Paso 1: Instalar Dependencias Frontend

```bash
cd frontend
npm install
```

### Paso 2: Instalar Herramientas de Testing

```bash
# Vitest + Vue Test Utils
npm install -D vitest @vue/test-utils @vitest/ui happy-dom

# TypeScript support
npm install -D @types/node

# Coverage
npm install -D @vitest/coverage-v8
```

### Paso 3: Verificar Setup

```bash
# Ejecutar tests (debería mostrar 0 tests por ahora)
npm run test

# O con UI
npm run test:ui
```

---

## Troubleshooting

### npm no encontrado en Git Bash

**Problema**: `npm: command not found` en Git Bash después de instalar Node.js

**Soluciones**:

1. **Reiniciar TODA la terminal**:
   - Cierra VS Code completamente
   - Cierra todas las ventanas de Git Bash
   - Abre una nueva ventana

2. **Verificar PATH manualmente**:
   ```bash
   echo $PATH | grep -i nodejs
   ```
   Si no aparece, añadir a `~/.bashrc`:
   ```bash
   export PATH="/c/Program Files/nodejs:$PATH"
   ```

3. **Usar PowerShell en su lugar**:
   ```powershell
   # En VS Code, abre PowerShell terminal
   cd frontend
   npm install
   npm run test
   ```

### Permisos denegados (Linux/macOS)

**Problema**: `EACCES: permission denied`

**Solución**: Usar nvm en lugar de instalación global, o:
```bash
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /usr/local/lib/node_modules
```

### Versión antigua de npm

**Problema**: npm < 9.0.0

**Solución**:
```bash
npm install -g npm@latest
```

---

## Próximos Pasos (Después de Instalar npm)

1. ✅ **Instalar Node.js/npm** (esta guía)
2. ⏭️ **Configurar Vitest** (ver `docs/FRONTEND_TESTING_SETUP.md`)
3. ⏭️ **Crear tests de DocumentViewer** (15 tests)
4. ⏭️ **Crear tests de ProjectSummary** (12 tests)
5. ⏭️ **Crear tests de transformers** (10 tests)

---

## Referencias

- **Frontend Testing Setup**: `docs/FRONTEND_TESTING_SETUP.md`
- **Script de instalación**: `scripts/install_nodejs.ps1`
- **Node.js Downloads**: https://nodejs.org/
- **nvm-windows**: https://github.com/coreybutler/nvm-windows

---

**Generado**: 2026-02-22
**Autor**: Claude Sonnet 4.5
