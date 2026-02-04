#!/usr/bin/env python3
"""
Script de instalación completa de LanguageTool + Java.

Este script instala todo lo necesario para usar LanguageTool:
1. Detecta si Java está instalado
2. Si no está, descarga e instala OpenJDK portable
3. Descarga LanguageTool Server
4. Crea scripts de inicio configurados

NO requiere instalación previa de Java - todo se incluye en el proyecto.

Uso:
    python scripts/setup_languagetool.py

Una vez instalado, iniciar con:
    - Windows: tools\\languagetool\\start_lt.bat
    - Linux/Mac: ./tools/languagetool/start_lt.sh
"""

import os
import sys
import subprocess
import urllib.request
import urllib.parse
import zipfile
import tarfile
import shutil
import time
import platform
from pathlib import Path

# Configuración
LT_VERSION = "6.4"
# URLs de descarga (con mirrors alternativos)
LT_URLS = [
    # GitHub releases suele ser más estable que el sitio web
    f"https://github.com/languagetool-org/languagetool/releases/download/v{LT_VERSION}/LanguageTool-{LT_VERSION}.zip",
    # Sitio oficial
    f"https://languagetool.org/download/LanguageTool-{LT_VERSION}.zip",
    f"https://www.languagetool.org/download/LanguageTool-{LT_VERSION}.zip",
    # Mirror alternativo de la comunidad
    f"https://languagetool.org/download/snapshots/LanguageTool-{LT_VERSION}.zip",
]

# OpenJDK Temurin (Adoptium) - Versiones portables
# https://adoptium.net/temurin/releases/
JAVA_VERSION = "21"  # LTS
JAVA_URLS = {
    "Windows": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_windows_hotspot_21.0.2_13.zip",
    "Linux": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_linux_hotspot_21.0.2_13.tar.gz",
    "Darwin": f"https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_mac_hotspot_21.0.2_13.tar.gz",
}

# Directorios
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
LT_DIR = TOOLS_DIR / "languagetool"
JAVA_DIR = TOOLS_DIR / "java"

# Puerto por defecto
DEFAULT_PORT = 8081


def print_step(msg: str) -> None:
    """Imprimir paso con formato."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def print_info(msg: str) -> None:
    """Imprimir información."""
    print(f"  [INFO] {msg}")


def print_error(msg: str) -> None:
    """Imprimir error."""
    print(f"  [ERROR] {msg}", file=sys.stderr)


def print_success(msg: str) -> None:
    """Imprimir éxito."""
    print(f"  [OK] {msg}")


def get_system() -> str:
    """Obtener sistema operativo."""
    system = platform.system()
    if system not in JAVA_URLS:
        print_error(f"Sistema no soportado: {system}")
        sys.exit(1)
    return system


def get_java_executable() -> Path:
    """Obtener ruta al ejecutable de Java instalado localmente."""
    system = get_system()

    if system == "Windows":
        return JAVA_DIR / "bin" / "java.exe"
    else:
        return JAVA_DIR / "bin" / "java"


def check_local_java() -> bool:
    """Verificar si Java está instalado localmente en tools/java."""
    java_exe = get_java_executable()

    if java_exe.exists():
        try:
            result = subprocess.run(
                [str(java_exe), "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print_success(f"Java local encontrado: {java_exe}")
                return True
        except Exception:
            pass

    return False


def check_system_java() -> bool:
    """Verificar si Java está instalado en el sistema."""
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version_output = result.stderr or result.stdout
            print_info("Java del sistema encontrado:")
            for line in version_output.strip().split("\n")[:2]:
                print(f"    {line}")
            return True
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return False


def download_progress(block_num: int, block_size: int, total_size: int) -> None:
    """Mostrar progreso de descarga."""
    if total_size > 0:
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 // total_size)
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(f"\r  Progreso: {percent:3d}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)


def download_file(url: str, dest: Path, description: str) -> bool:
    """Descargar archivo con progreso y User-Agent."""
    print_info(f"Descargando {description}...")
    print_info(f"URL: {url}")
    print_info(f"Destino: {dest}")

    try:
        # Crear request con User-Agent para evitar bloqueos
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/octet-stream,*/*",
        }
        req = urllib.request.Request(url, headers=headers)

        # Descargar con progreso
        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            block_size = 8192
            downloaded = 0

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = min(100, downloaded * 100 // total_size)
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r  Progreso: {percent:3d}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)

        print()  # Nueva línea después del progreso
        print_success(f"Descarga completada: {dest.name}")
        return True

    except urllib.error.HTTPError as e:
        print()
        print_error(f"Error HTTP {e.code}: {e.reason}")
        if e.code == 403:
            print_info("El servidor bloqueó la descarga directa.")
            print_info("Descarga manual disponible en: https://languagetool.org/download/")
        return False
    except Exception as e:
        print()
        print_error(f"Error descargando: {e}")
        return False


def install_java() -> bool:
    """Descargar e instalar Java portable."""
    print_step(f"Instalando Java {JAVA_VERSION} (OpenJDK Temurin)")

    system = get_system()
    java_url = JAVA_URLS[system]

    # Crear directorio tools
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    # Determinar extensión del archivo
    if system == "Windows":
        archive_name = f"java-{JAVA_VERSION}.zip"
    else:
        archive_name = f"java-{JAVA_VERSION}.tar.gz"

    archive_path = TOOLS_DIR / archive_name

    # Descargar si no existe
    if not archive_path.exists():
        if not download_file(java_url, archive_path, f"OpenJDK {JAVA_VERSION}"):
            return False
    else:
        print_info(f"Archivo ya existe: {archive_path}")

    # Extraer
    print_info("Extrayendo Java...")

    # Limpiar instalación anterior
    if JAVA_DIR.exists():
        shutil.rmtree(JAVA_DIR)

    try:
        if system == "Windows":
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(TOOLS_DIR)
        else:
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(TOOLS_DIR)

        # Encontrar el directorio extraído (tiene nombre con versión)
        extracted_dirs = [d for d in TOOLS_DIR.iterdir()
                        if d.is_dir() and d.name.startswith("jdk-")]

        if not extracted_dirs:
            print_error("No se encontró directorio Java extraído")
            return False

        # Renombrar a 'java' para simplificar
        extracted_dir = extracted_dirs[0]

        # En macOS, el contenido está dentro de Contents/Home
        if system == "Darwin":
            contents_home = extracted_dir / "Contents" / "Home"
            if contents_home.exists():
                shutil.move(str(contents_home), str(JAVA_DIR))
                shutil.rmtree(extracted_dir)
            else:
                extracted_dir.rename(JAVA_DIR)
        else:
            extracted_dir.rename(JAVA_DIR)

        print_success(f"Java instalado en: {JAVA_DIR}")

        # Verificar
        java_exe = get_java_executable()
        if java_exe.exists():
            # Hacer ejecutable en Unix
            if system != "Windows":
                java_exe.chmod(0o755)

            result = subprocess.run(
                [str(java_exe), "-version"],
                capture_output=True,
                text=True
            )
            version_out = result.stderr or result.stdout
            print_info("Versión instalada:")
            for line in version_out.strip().split("\n")[:2]:
                print(f"    {line}")

            return True
        else:
            print_error(f"No se encontró ejecutable: {java_exe}")
            return False

    except Exception as e:
        print_error(f"Error extrayendo Java: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_languagetool() -> Path:
    """Descargar LanguageTool probando múltiples mirrors."""
    print_step(f"Descargando LanguageTool {LT_VERSION}")

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TOOLS_DIR / f"LanguageTool-{LT_VERSION}.zip"

    if zip_path.exists():
        print_info(f"Archivo ya existe: {zip_path}")
        return zip_path

    # Intentar cada URL en orden hasta que una funcione
    for i, url in enumerate(LT_URLS):
        print_info(f"Intentando mirror {i+1}/{len(LT_URLS)}...")
        if download_file(url, zip_path, f"LanguageTool {LT_VERSION}"):
            return zip_path
        else:
            print_info("Probando siguiente mirror...")
            # Eliminar archivo parcial si existe
            if zip_path.exists():
                zip_path.unlink()

    # Si llegamos aquí, ningún mirror funcionó
    print_error("No se pudo descargar LanguageTool de ningún mirror.")
    print_info("Descarga manual disponible en:")
    print_info("  https://languagetool.org/download/")
    print_info("  https://github.com/languagetool-org/languagetool/releases")
    print_info(f"Coloca el archivo en: {zip_path}")
    raise Exception("Error descargando LanguageTool de todos los mirrors")


def extract_languagetool(zip_path: Path) -> Path:
    """Extraer LanguageTool del zip."""
    print_step("Extrayendo LanguageTool")

    # Limpiar instalación anterior
    if LT_DIR.exists():
        print_info(f"Limpiando instalación anterior: {LT_DIR}")
        try:
            shutil.rmtree(LT_DIR)
        except PermissionError:
            # En Windows, a veces los archivos quedan bloqueados
            print_info("Reintentando eliminación con permisos de administrador...")
            import stat
            def remove_readonly(func, path, excinfo):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(LT_DIR, onerror=remove_readonly)

    # También limpiar directorio temporal de extracción anterior
    extract_dir = TOOLS_DIR / f"LanguageTool-{LT_VERSION}"
    if extract_dir.exists():
        print_info(f"Limpiando directorio temporal: {extract_dir}")
        try:
            shutil.rmtree(extract_dir)
        except PermissionError:
            import stat
            def remove_readonly(func, path, excinfo):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(extract_dir, onerror=remove_readonly)

    # Extraer
    print_info(f"Extrayendo a: {TOOLS_DIR}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(TOOLS_DIR)

    # Buscar directorio extraído
    extract_dir = TOOLS_DIR / f"LanguageTool-{LT_VERSION}"
    if not extract_dir.exists():
        # Buscar cualquier directorio LanguageTool
        for d in TOOLS_DIR.iterdir():
            if d.is_dir() and d.name.startswith("LanguageTool"):
                extract_dir = d
                break

    # Renombrar a 'languagetool' usando shutil.move (más robusto en Windows)
    if extract_dir.exists():
        shutil.move(str(extract_dir), str(LT_DIR))
        print_success(f"Extraído a: {LT_DIR}")
    else:
        raise Exception(f"No se encontró el directorio extraído: {extract_dir}")

    return LT_DIR


def create_start_scripts() -> None:
    """Crear scripts de inicio que usan Java disponible (sistema o local)."""
    print_step("Creando scripts de inicio")

    system = get_system()

    # Prioridad: Java del sistema > Java local
    # Esto evita problemas de rutas y usa la versión optimizada del sistema
    use_system_java = check_system_java()
    use_local_java = not use_system_java and check_local_java()

    if use_system_java:
        java_source = "Java del sistema"
    elif use_local_java:
        java_source = "Java local (tools/java)"
    else:
        java_source = "Java (no verificado)"

    print_info(f"Usando: {java_source}")

    # Script para Windows - usa %~dp0 para rutas absolutas
    bat_script = LT_DIR / "start_lt.bat"
    if use_system_java:
        java_cmd_bat = "java"
    else:
        # Ruta absoluta calculada desde el directorio del script
        java_cmd_bat = "%~dp0..\\java\\bin\\java.exe"

    bat_content = f"""@echo off
REM Iniciar servidor LanguageTool
REM Puerto: {DEFAULT_PORT}
REM Java: {java_source}

cd /d "%~dp0"

echo ============================================================
echo   LanguageTool Server - Narrative Assistant
echo ============================================================
echo.
echo Puerto: {DEFAULT_PORT}
echo Java: {java_source}
echo.
echo Para detener: Ctrl+C
echo.

"{java_cmd_bat}" -Xmx512m -cp languagetool-server.jar org.languagetool.server.HTTPServer --port {DEFAULT_PORT} --allow-origin "*"
"""
    bat_script.write_text(bat_content, encoding="utf-8")
    print_success(f"Creado: {bat_script}")

    # Script para Linux/macOS
    sh_script = LT_DIR / "start_lt.sh"
    if use_system_java:
        java_cmd_sh = "java"
    else:
        java_cmd_sh = '"$(dirname "$0")/../java/bin/java"'

    sh_content = f"""#!/bin/bash
# Iniciar servidor LanguageTool
# Puerto: {DEFAULT_PORT}
# Java: {java_source}

cd "$(dirname "$0")"

echo "============================================================"
echo "  LanguageTool Server - Narrative Assistant"
echo "============================================================"
echo ""
echo "Puerto: {DEFAULT_PORT}"
echo "Java: {java_source}"
echo ""
echo "Para detener: Ctrl+C"
echo ""

{java_cmd_sh} -Xmx512m -cp languagetool-server.jar org.languagetool.server.HTTPServer --port {DEFAULT_PORT} --allow-origin "*"
"""
    sh_script.write_text(sh_content, encoding="utf-8")
    sh_script.chmod(0o755)
    print_success(f"Creado: {sh_script}")

    # Script de inicio en background (Windows) - IMPORTANTE: usar variable SET para la ruta
    bg_bat = LT_DIR / "start_lt_background.bat"
    if use_system_java:
        java_set_cmd = "set JAVA_CMD=java"
    else:
        java_set_cmd = "set JAVA_CMD=%~dp0..\\java\\bin\\java.exe"

    bg_content = f"""@echo off
REM Iniciar servidor LanguageTool en background
REM Puerto: {DEFAULT_PORT}

cd /d "%~dp0"
{java_set_cmd}

echo Iniciando LanguageTool Server en background (puerto {DEFAULT_PORT})...
start /B "" "%JAVA_CMD%" -Xmx512m -cp languagetool-server.jar org.languagetool.server.HTTPServer --port {DEFAULT_PORT} --allow-origin "*" > languagetool.log 2>&1
echo Servidor iniciado. Log en: languagetool.log
"""
    bg_bat.write_text(bg_content, encoding="utf-8")
    print_success(f"Creado: {bg_bat}")

    # Script de parada (Windows)
    stop_bat = LT_DIR / "stop_lt.bat"
    stop_content = """@echo off
REM Detener servidor LanguageTool
echo Deteniendo LanguageTool Server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8081 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
echo Servidor detenido.
"""
    stop_bat.write_text(stop_content, encoding="utf-8")
    print_success(f"Creado: {stop_bat}")


def verify_installation() -> bool:
    """Verificar que LanguageTool funciona."""
    print_step("Verificando instalación")

    # Verificar JAR
    jar_file = LT_DIR / "languagetool-server.jar"
    if not jar_file.exists():
        print_error(f"No se encontró: {jar_file}")
        return False
    print_success(f"JAR encontrado: {jar_file}")

    # Determinar Java a usar (prioridad: sistema > local)
    if check_system_java():
        java_cmd = "java"
    else:
        java_exe = get_java_executable()
        java_cmd = str(java_exe) if java_exe.exists() else "java"

    print_info(f"Usando Java: {java_cmd}")
    print_info("Iniciando servidor de prueba...")

    try:
        # Iniciar servidor
        process = subprocess.Popen(
            [java_cmd, "-Xmx512m", "-cp", str(jar_file),
             "org.languagetool.server.HTTPServer",
             "--port", str(DEFAULT_PORT), "--allow-origin", "*"],
            cwd=LT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Esperar a que inicie
        print_info("Esperando que el servidor inicie (5 segundos)...")
        time.sleep(5)

        # Verificar que responde
        try:
            url = f"http://localhost:{DEFAULT_PORT}/v2/languages"
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print_success("Servidor responde correctamente")

                    # Probar análisis
                    check_url = f"http://localhost:{DEFAULT_PORT}/v2/check"
                    data = urllib.parse.urlencode({
                        "text": "Pienso de que vendrá.",
                        "language": "es"
                    }).encode("utf-8")

                    req = urllib.request.Request(check_url, data=data, method="POST")
                    with urllib.request.urlopen(req, timeout=10) as check_response:
                        import json
                        result = json.loads(check_response.read().decode("utf-8"))
                        matches = result.get("matches", [])
                        if matches:
                            print_success(f"Análisis funciona: detectó {len(matches)} error(es)")
                            print_info(f"  Ejemplo: {matches[0].get('message', 'N/A')}")
                        else:
                            print_info("Análisis funciona (sin errores en texto de prueba)")

                    return True

        except urllib.error.URLError as e:
            print_error(f"Error conectando al servidor: {e}")
        finally:
            # Detener servidor
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print_info("Servidor de prueba detenido")

    except Exception as e:
        print_error(f"Error verificando: {e}")
        import traceback
        traceback.print_exc()

    return False


def print_usage() -> None:
    """Imprimir instrucciones de uso."""
    print_step("Instalación completada")

    system = get_system()

    if system == "Windows":
        start_cmd = "tools\\languagetool\\start_lt.bat"
        bg_cmd = "tools\\languagetool\\start_lt_background.bat"
        stop_cmd = "tools\\languagetool\\stop_lt.bat"
    else:
        start_cmd = "./tools/languagetool/start_lt.sh"
        bg_cmd = "(no disponible en Unix - usar nohup o &)"
        stop_cmd = "pkill -f languagetool-server"

    print(f"""
Para usar LanguageTool:

1. Iniciar el servidor:
   {start_cmd}

2. Iniciar en background:
   {bg_cmd}

3. Detener el servidor:
   {stop_cmd}

4. El servidor escuchará en: http://localhost:{DEFAULT_PORT}

5. En Narrative Assistant, el sistema detectará automáticamente
   LanguageTool cuando esté corriendo.

6. Para verificar manualmente:
   curl "http://localhost:{DEFAULT_PORT}/v2/check" -d "language=es" -d "text=Pienso de que vendrá."

Notas:
- LanguageTool requiere ~500 MB de RAM
- Primera carga puede tardar unos segundos
- Si Java no está instalado en el sistema, se instala automáticamente en tools/java/
""")


def main() -> int:
    """Punto de entrada principal."""
    print("\n" + "="*60)
    print("  INSTALADOR DE LANGUAGETOOL + JAVA")
    print("  Narrative Assistant")
    print("="*60)

    try:
        # Paso 1: Verificar/Instalar Java
        print_step("Verificando Java")

        has_local_java = check_local_java()
        has_system_java = check_system_java()

        if has_local_java:
            print_success("Java local ya está instalado (tools/java)")
        elif has_system_java:
            print_success("Java del sistema encontrado - no es necesario instalar")
        else:
            # Solo instalar Java si NO está en el sistema
            print_info("Java no encontrado en el sistema")
            print_info("Instalando Java portable (OpenJDK Temurin)...")
            if not install_java():
                print_error("Error instalando Java")
                print_error("Por favor instala Java manualmente desde: https://adoptium.net/")
                return 1

        # Paso 2: Descargar LanguageTool
        zip_path = download_languagetool()

        # Paso 3: Extraer
        extract_languagetool(zip_path)

        # Paso 4: Crear scripts
        create_start_scripts()

        # Paso 5: Verificar
        if verify_installation():
            print_usage()
            return 0
        else:
            print_error("La verificación falló, pero los archivos están instalados.")
            print_info("Intenta iniciar manualmente el servidor.")
            print_usage()
            return 1

    except KeyboardInterrupt:
        print("\n\nInstalación cancelada por el usuario.")
        return 1
    except Exception as e:
        print_error(f"Error durante la instalación: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
