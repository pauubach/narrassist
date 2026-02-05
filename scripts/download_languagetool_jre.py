#!/usr/bin/env python3
"""
Script para descargar LanguageTool + OpenJDK JRE portables para Windows y macOS.
Se incluirán en el installer de la aplicación para funcionar 100% offline.

Basado en el patrón de download_python_embed.py

Estructura de descarga:
    src-tauri/binaries/
    ├── java-jre/           # OpenJDK 21 JRE portable
    │   ├── bin/
    │   │   └── java(.exe)
    │   └── lib/
    └── languagetool/       # LanguageTool JAR + libs
        └── LanguageTool-X.X/
            ├── languagetool-server.jar
            └── ...
"""
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

# Versiones
JAVA_VERSION = "21.0.2_13"  # LTS release
LT_VERSION = "6.4"

# URLs de descarga - OpenJDK Temurin (adoptium.net)
# Formato: OpenJDK21U-jre_{arch}_{os}_hotspot_{version}.{ext}
JAVA_URLS = {
    "Windows_x64": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_windows_hotspot_{JAVA_VERSION}.zip",
    "Darwin_arm64": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_aarch64_mac_hotspot_{JAVA_VERSION}.tar.gz",
    "Darwin_x64": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_mac_hotspot_{JAVA_VERSION}.tar.gz",
    "Linux_x64": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_linux_hotspot_{JAVA_VERSION}.tar.gz",
}

# LanguageTool URLs (múltiples mirrors)
LT_URLS = [
    f"https://languagetool.org/download/LanguageTool-{LT_VERSION}.zip",
    f"https://github.com/languagetool-org/languagetool/releases/download/v{LT_VERSION}/LanguageTool-{LT_VERSION}.zip",
]

# Tamaños esperados (aproximados, para verificación)
EXPECTED_SIZES = {
    "java_windows": 50_000_000,   # ~50 MB comprimido
    "java_macos": 45_000_000,     # ~45 MB comprimido
    "languagetool": 180_000_000,  # ~180 MB
}


def get_platform_key() -> str:
    """Determina la clave de plataforma para URLs."""
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        return "Windows_x64"
    elif system == "Darwin":
        if machine in ("arm64", "aarch64"):
            return "Darwin_arm64"
        return "Darwin_x64"
    elif system == "Linux":
        return "Linux_x64"
    else:
        raise RuntimeError(f"Plataforma no soportada: {system} {machine}")


def download_file(url: str, target_path: Path, description: str = "") -> bool:
    """Descarga un archivo con barra de progreso."""
    print(f"Descargando {description or url}...")
    print(f"  URL: {url}")

    try:
        # Hook para mostrar progreso
        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r  Progreso: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")

        urllib.request.urlretrieve(url, target_path, reporthook)
        print()  # Nueva línea después del progreso

        # Verificar tamaño mínimo
        size = target_path.stat().st_size
        if size < 1_000_000:  # Menos de 1MB es sospechoso
            print(f"  [WARN] Archivo muy pequeño: {size} bytes")
            return False

        print(f"  [OK] Descargado: {target_path.name} ({size / (1024*1024):.1f} MB)")
        return True

    except Exception as e:
        print(f"  [ERROR] Fallo descarga: {e}")
        return False


def download_java_jre(target_dir: Path) -> bool:
    """
    Descarga OpenJDK JRE portable para la plataforma actual.

    Args:
        target_dir: Directorio donde extraer (ej: src-tauri/binaries/java-jre)

    Returns:
        True si exitoso
    """
    platform_key = get_platform_key()
    url = JAVA_URLS.get(platform_key)

    if not url:
        print(f"[ERROR] No hay URL de Java para plataforma: {platform_key}")
        return False

    # Crear directorio destino
    target_dir.mkdir(parents=True, exist_ok=True)

    # Determinar extensión
    is_zip = url.endswith(".zip")
    ext = ".zip" if is_zip else ".tar.gz"
    archive_path = target_dir.parent / f"java-jre{ext}"

    # Descargar
    if not download_file(url, archive_path, f"OpenJDK {JAVA_VERSION} JRE"):
        return False

    # Extraer
    print(f"Extrayendo Java JRE a {target_dir}...")
    try:
        if is_zip:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(target_dir.parent)
        else:
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(target_dir.parent)

        # Renombrar directorio extraído (tiene nombre largo como jdk-21.0.2+13-jre)
        extracted_dirs = [d for d in target_dir.parent.iterdir()
                         if d.is_dir() and d.name.startswith("jdk-") and d.name.endswith("-jre")]

        if extracted_dirs:
            extracted_dir = extracted_dirs[0]
            if target_dir.exists():
                shutil.rmtree(target_dir)
            extracted_dir.rename(target_dir)
            print(f"  [OK] Renombrado {extracted_dir.name} → java-jre")

        # Limpiar archivo comprimido
        archive_path.unlink()

        # Verificar que java existe
        java_bin = target_dir / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
        if java_bin.exists():
            print(f"  [OK] Java JRE listo: {java_bin}")

            # En Unix, asegurar permisos de ejecución
            if platform.system() != "Windows":
                os.chmod(java_bin, 0o755)

            return True
        else:
            print(f"  [ERROR] No se encontró binario java en {java_bin}")
            return False

    except Exception as e:
        print(f"  [ERROR] Fallo extracción: {e}")
        return False


def download_languagetool(target_dir: Path) -> bool:
    """
    Descarga LanguageTool desde múltiples mirrors.

    Args:
        target_dir: Directorio donde extraer (ej: src-tauri/binaries/languagetool)

    Returns:
        True si exitoso
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir.parent / f"LanguageTool-{LT_VERSION}.zip"

    # Intentar descargar de múltiples URLs
    downloaded = False
    for url in LT_URLS:
        if download_file(url, zip_path, f"LanguageTool {LT_VERSION}"):
            downloaded = True
            break
        print(f"  Intentando siguiente mirror...")

    if not downloaded:
        print(f"[ERROR] No se pudo descargar LanguageTool de ningún mirror")
        return False

    # Extraer
    print(f"Extrayendo LanguageTool a {target_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(target_dir.parent)

        # Renombrar directorio extraído
        extracted_dir = target_dir.parent / f"LanguageTool-{LT_VERSION}"
        if extracted_dir.exists():
            if target_dir.exists():
                shutil.rmtree(target_dir)
            extracted_dir.rename(target_dir)
            print(f"  [OK] Renombrado LanguageTool-{LT_VERSION} → languagetool")

        # Limpiar zip
        zip_path.unlink()

        # Verificar JAR principal
        server_jar = target_dir / "languagetool-server.jar"
        if server_jar.exists():
            print(f"  [OK] LanguageTool listo: {server_jar}")
            return True
        else:
            print(f"  [ERROR] No se encontró languagetool-server.jar")
            return False

    except Exception as e:
        print(f"  [ERROR] Fallo extracción: {e}")
        return False


def verify_installation(binaries_dir: Path) -> bool:
    """Verifica que Java JRE y LanguageTool estén correctamente instalados."""
    print("\n=== Verificando instalación ===")

    java_dir = binaries_dir / "java-jre"
    lt_dir = binaries_dir / "languagetool"

    errors = []

    # Verificar Java
    java_bin = java_dir / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
    if java_bin.exists():
        print(f"[OK] Java JRE: {java_bin}")

        # Intentar ejecutar java -version
        try:
            result = subprocess.run(
                [str(java_bin), "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            version_line = result.stderr.split('\n')[0] if result.stderr else "unknown"
            print(f"     Version: {version_line}")
        except Exception as e:
            print(f"     [WARN] No se pudo verificar versión: {e}")
    else:
        errors.append(f"Java no encontrado: {java_bin}")

    # Verificar LanguageTool
    lt_jar = lt_dir / "languagetool-server.jar"
    if lt_jar.exists():
        size_mb = lt_jar.stat().st_size / (1024 * 1024)
        print(f"[OK] LanguageTool: {lt_jar} ({size_mb:.1f} MB)")
    else:
        errors.append(f"LanguageTool JAR no encontrado: {lt_jar}")

    # Resumen
    if errors:
        print("\n[ERRORES]")
        for e in errors:
            print(f"  - {e}")
        return False

    print("\n[OK] Instalación verificada correctamente")
    return True


def create_start_script(binaries_dir: Path) -> None:
    """Crea scripts de inicio para LanguageTool."""
    lt_dir = binaries_dir / "languagetool"
    java_dir = binaries_dir / "java-jre"

    if platform.system() == "Windows":
        script_path = lt_dir / "start_lt_embedded.bat"
        script_content = f'''@echo off
REM Script de inicio de LanguageTool con Java embebido
set JAVA_HOME=%~dp0..\\java-jre
set PATH=%JAVA_HOME%\\bin;%PATH%

echo Iniciando LanguageTool server...
"%JAVA_HOME%\\bin\\java.exe" -Xmx512m -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8081 --allow-origin "*"
'''
    else:
        script_path = lt_dir / "start_lt_embedded.sh"
        script_content = f'''#!/bin/bash
# Script de inicio de LanguageTool con Java embebido
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JAVA_HOME="$SCRIPT_DIR/../java-jre"
export PATH="$JAVA_HOME/bin:$PATH"

echo "Iniciando LanguageTool server..."
"$JAVA_HOME/bin/java" -Xmx512m -cp "$SCRIPT_DIR/languagetool-server.jar" org.languagetool.server.HTTPServer --port 8081 --allow-origin "*"
'''

    script_path.write_text(script_content)
    if platform.system() != "Windows":
        os.chmod(script_path, 0o755)
    print(f"[OK] Script de inicio creado: {script_path.name}")


def main():
    """Punto de entrada principal."""
    # Determinar directorio de destino
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    binaries_dir = project_root / "src-tauri" / "binaries"

    print("=" * 60)
    print("Descarga de LanguageTool + Java JRE para embedding")
    print("=" * 60)
    print(f"Plataforma: {platform.system()} {platform.machine()}")
    print(f"Destino: {binaries_dir}")
    print()

    # Crear directorio base
    binaries_dir.mkdir(parents=True, exist_ok=True)

    # Descargar Java JRE
    print("\n--- Paso 1: Java JRE ---")
    java_dir = binaries_dir / "java-jre"
    if java_dir.exists() and (java_dir / "bin").exists():
        print(f"[SKIP] Java JRE ya existe en {java_dir}")
        java_ok = True
    else:
        java_ok = download_java_jre(java_dir)

    if not java_ok:
        print("[FATAL] Fallo descarga de Java JRE")
        sys.exit(1)

    # Descargar LanguageTool
    print("\n--- Paso 2: LanguageTool ---")
    lt_dir = binaries_dir / "languagetool"
    if lt_dir.exists() and (lt_dir / "languagetool-server.jar").exists():
        print(f"[SKIP] LanguageTool ya existe en {lt_dir}")
        lt_ok = True
    else:
        lt_ok = download_languagetool(lt_dir)

    if not lt_ok:
        print("[FATAL] Fallo descarga de LanguageTool")
        sys.exit(1)

    # Crear scripts de inicio
    print("\n--- Paso 3: Scripts de inicio ---")
    create_start_script(binaries_dir)

    # Verificar
    print("\n--- Paso 4: Verificación ---")
    if not verify_installation(binaries_dir):
        sys.exit(1)

    print("\n" + "=" * 60)
    print("[EXITO] LanguageTool + Java JRE listos para embedding")
    print("=" * 60)

    # Mostrar tamaño total
    total_size = sum(
        f.stat().st_size for f in binaries_dir.rglob("*") if f.is_file()
    )
    print(f"Tamaño total binarios: {total_size / (1024*1024):.1f} MB")


if __name__ == "__main__":
    main()
