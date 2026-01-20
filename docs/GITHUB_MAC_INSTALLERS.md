# Crear Instaladores para macOS con GitHub Actions (Cuenta Gratuita)

Esta guía explica cómo configurar GitHub Actions para generar instaladores de aplicaciones Tauri para macOS, incluso sin tener acceso a un Mac físico.

## Requisitos Previos

1. **Cuenta de GitHub gratuita** (no requiere plan de pago)
2. **Repositorio en GitHub** (público o privado)
3. **Proyecto Tauri configurado** (ya tenemos esto)

## Limitaciones de la Cuenta Gratuita

| Recurso | Límite Gratuito |
|---------|-----------------|
| Minutos de CI/CD | 2,000 min/mes para repos públicos |
| Minutos de CI/CD | 500 min/mes para repos privados |
| Runners macOS | Disponibles (consumen 10x minutos en privado) |
| Almacenamiento de artefactos | 500 MB |
| Retención de artefactos | 90 días |

> **Nota**: Los repositorios públicos tienen minutos ilimitados para GitHub Actions.

## Configuración Paso a Paso

### 1. Crear el Workflow de GitHub Actions

Crea el archivo `.github/workflows/build-macos.yml`:

```yaml
name: Build macOS Installer

on:
  # Ejecutar manualmente desde la UI de GitHub
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag (e.g., v1.0.0)'
        required: false
        default: 'dev'

  # Ejecutar en push a tags de versión
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: macos-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: aarch64-apple-darwin,x86_64-apple-darwin

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Cache Rust dependencies
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: src-tauri

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[build]"

      - name: Build Python sidecar
        run: python scripts/build_sidecar.py --target macos

      - name: Build Tauri app (Intel + Apple Silicon)
        working-directory: frontend
        run: npm run tauri build -- --target universal-apple-darwin
        env:
          TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
          TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}

      - name: Upload DMG artifact
        uses: actions/upload-artifact@v4
        with:
          name: macos-dmg-${{ github.event.inputs.version || github.ref_name }}
          path: |
            src-tauri/target/universal-apple-darwin/release/bundle/dmg/*.dmg
          retention-days: 30

      - name: Upload app bundle
        uses: actions/upload-artifact@v4
        with:
          name: macos-app-${{ github.event.inputs.version || github.ref_name }}
          path: |
            src-tauri/target/universal-apple-darwin/release/bundle/macos/*.app
          retention-days: 30
```

### 2. Workflow Multiplataforma (Windows + macOS + Linux)

Para generar instaladores de todas las plataformas en un solo workflow:

```yaml
name: Build All Platforms

on:
  workflow_dispatch:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - platform: macos-latest
            target: universal-apple-darwin
            name: macOS
          - platform: windows-latest
            target: x86_64-pc-windows-msvc
            name: Windows
          - platform: ubuntu-22.04
            target: x86_64-unknown-linux-gnu
            name: Linux

    runs-on: ${{ matrix.platform }}
    name: Build ${{ matrix.name }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Linux dependencies
        if: matrix.platform == 'ubuntu-22.04'
        run: |
          sudo apt-get update
          sudo apt-get install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf

      - name: Cache Rust
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: src-tauri

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[build]"

      - name: Build sidecar
        run: python scripts/build_sidecar.py

      - name: Build Tauri
        working-directory: frontend
        run: npm run tauri build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: installer-${{ matrix.name }}
          path: |
            src-tauri/target/release/bundle/**/*.dmg
            src-tauri/target/release/bundle/**/*.app
            src-tauri/target/release/bundle/**/*.msi
            src-tauri/target/release/bundle/**/*.exe
            src-tauri/target/release/bundle/**/*.deb
            src-tauri/target/release/bundle/**/*.AppImage
          retention-days: 30
```

### 3. Crear un Release con los Instaladores

Para publicar automáticamente cuando se crea un tag:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    # ... (usar el job de build anterior)

  release:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: artifacts/**/*
          draft: true
          generate_release_notes: true
```

## Ejecutar el Build Manualmente

1. Ve a tu repositorio en GitHub
2. Haz clic en la pestaña **Actions**
3. Selecciona el workflow **Build macOS Installer** (o el que hayas creado)
4. Haz clic en **Run workflow**
5. Opcionalmente, especifica una versión
6. Haz clic en **Run workflow** (botón verde)

## Descargar los Artefactos

1. Una vez completado el workflow, haz clic en el run
2. En la sección **Artifacts**, verás los instaladores generados
3. Haz clic en cada uno para descargar el ZIP

## Firmar la Aplicación para macOS (Opcional pero Recomendado)

Sin firma, los usuarios verán una advertencia de "desarrollador no identificado". Para firmar:

### Opción A: Sin cuenta de desarrollador de Apple

Los usuarios pueden abrir la app con:
1. Clic derecho en la app → "Abrir"
2. O ejecutar: `xattr -cr /path/to/App.app`

### Opción B: Con cuenta de desarrollador de Apple ($99/año)

1. Genera un certificado en [developer.apple.com](https://developer.apple.com)
2. Exporta el certificado como `.p12`
3. Convierte a base64: `base64 -i certificate.p12 | pbcopy`
4. Añade estos secrets en GitHub:
   - `APPLE_CERTIFICATE`: El certificado en base64
   - `APPLE_CERTIFICATE_PASSWORD`: Contraseña del certificado
   - `APPLE_SIGNING_IDENTITY`: Ej. "Developer ID Application: Tu Nombre (TEAMID)"
   - `APPLE_ID`: Tu Apple ID
   - `APPLE_PASSWORD`: App-specific password
   - `APPLE_TEAM_ID`: Tu Team ID

5. Modifica el workflow para incluir la firma:

```yaml
- name: Import Apple Certificate
  env:
    APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
    APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
  run: |
    echo $APPLE_CERTIFICATE | base64 --decode > certificate.p12
    security create-keychain -p "" build.keychain
    security default-keychain -s build.keychain
    security unlock-keychain -p "" build.keychain
    security import certificate.p12 -k build.keychain -P "$APPLE_CERTIFICATE_PASSWORD" -T /usr/bin/codesign
    security set-key-partition-list -S apple-tool:,apple: -s -k "" build.keychain
```

## Secrets Necesarios

Configura estos secrets en **Settings → Secrets and variables → Actions**:

| Secret | Descripción | Requerido |
|--------|-------------|-----------|
| `TAURI_SIGNING_PRIVATE_KEY` | Clave para firmar actualizaciones de Tauri | Opcional |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Contraseña de la clave | Opcional |
| `APPLE_CERTIFICATE` | Certificado de Apple en base64 | Solo para firma |
| `APPLE_CERTIFICATE_PASSWORD` | Contraseña del certificado | Solo para firma |

## Generar Clave de Firma de Tauri

Si quieres usar el sistema de actualizaciones de Tauri:

```bash
# Instalar tauri-cli si no lo tienes
cargo install tauri-cli

# Generar par de claves
cargo tauri signer generate -w ~/.tauri/myapp.key

# Esto genera:
# - ~/.tauri/myapp.key (privada - NUNCA subir a git)
# - ~/.tauri/myapp.key.pub (pública - incluir en tauri.conf.json)
```

Luego añade la clave privada como secret `TAURI_SIGNING_PRIVATE_KEY`.

## Consejos para Optimizar Minutos

1. **Usa cache agresivamente**: Rust y npm dependencies se cachean
2. **Ejecuta solo cuando necesites**: Usa `workflow_dispatch` para control manual
3. **Considera hacer el repo público**: Minutos ilimitados
4. **Combina jobs**: Un solo job multiplataforma consume menos que 3 separados

## Probar en Mac Físico (Alternativa)

Si tienes acceso temporal a un Mac:

```bash
# Clonar y configurar
git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo

# Instalar dependencias
brew install node rust python@3.11
cd frontend && npm install && cd ..
pip install -e ".[build]"

# Build
python scripts/build_sidecar.py
cd frontend && npm run tauri build

# El instalador estará en:
# src-tauri/target/release/bundle/dmg/
```

## Troubleshooting

### Error: "codesign failed"
- Asegúrate de que el certificado está bien importado
- Verifica que `APPLE_SIGNING_IDENTITY` coincide exactamente

### Error: "notarization failed"
- Verifica que tu Apple ID tiene 2FA habilitado
- Usa una app-specific password, no tu contraseña normal

### El DMG es muy grande
- Revisa que no estás incluyendo archivos innecesarios
- Usa `strip` en los binarios: añade `strip = true` en `Cargo.toml`

### El workflow tarda mucho
- El primer build tarda más (sin cache)
- Builds subsecuentes deberían tardar ~10-15 minutos

## Referencias

- [Tauri GitHub Actions](https://tauri.app/v1/guides/building/cross-platform)
- [GitHub Actions para macOS](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners)
- [Firmar apps para macOS](https://tauri.app/v1/guides/distribution/sign-macos)
