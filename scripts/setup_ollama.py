#!/usr/bin/env python3
"""
Script para instalar y configurar Ollama con los modelos LLM necesarios.

Uso:
    python scripts/setup_ollama.py

Esto instalará Ollama (si no está presente) y descargará los modelos:
    - llama3.2 (3B) - Modelo rápido, buena calidad general
    - qwen2.5 (7B) - Excelente para español (opcional)

El análisis de comportamiento de personajes funciona con modelos locales,
sin necesidad de conexión a internet una vez instalado.
"""

import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent

# Modelos a descargar por defecto
DEFAULT_MODELS = ["llama3.2"]  # Modelo base, rápido
OPTIONAL_MODELS = ["qwen2.5", "mistral"]  # Opcionales para más precisión

# URLs de descarga de Ollama
OLLAMA_URLS = {
    "Windows": "https://ollama.com/download/OllamaSetup.exe",
    "Darwin": "https://ollama.com/download/Ollama-darwin.zip",
    "Linux": "https://ollama.com/install.sh",
}


def is_ollama_installed() -> bool:
    """Verifica si Ollama está instalado."""
    return shutil.which("ollama") is not None


def is_ollama_running() -> bool:
    """Verifica si el servidor Ollama está corriendo."""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def get_installed_models() -> list[str]:
    """Obtiene la lista de modelos instalados en Ollama."""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return [m.get("name", "").split(":")[0] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def download_file(url: str, dest: Path, desc: str = "Descargando"):
    """Descarga un archivo con barra de progreso."""
    print(f"{desc}: {url}")
    print(f"Destino: {dest}")

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\r  {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, dest, reporthook)
        print()  # Nueva línea después de la barra de progreso
        return True
    except Exception as e:
        print(f"\nError descargando: {e}")
        return False


def install_ollama_windows():
    """Instala Ollama en Windows."""
    print("\n" + "=" * 60)
    print("INSTALANDO OLLAMA EN WINDOWS")
    print("=" * 60)

    # Descargar instalador
    installer_path = Path(os.environ.get("TEMP", "/tmp")) / "OllamaSetup.exe"

    print("\nDescargando instalador de Ollama...")
    if not download_file(OLLAMA_URLS["Windows"], installer_path, "Descargando Ollama"):
        print("Error: No se pudo descargar el instalador.")
        print("Por favor, descarga manualmente desde: https://ollama.com/download")
        return False

    print("\nEjecutando instalador...")
    print("(Se abrirá el instalador de Ollama, sigue las instrucciones)")

    try:
        # Ejecutar instalador
        subprocess.run([str(installer_path)], check=True)
        print("\nInstalación de Ollama completada.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error durante la instalación: {e}")
        return False
    except FileNotFoundError:
        print("Error: No se encontró el instalador.")
        return False


def install_ollama_linux():
    """Instala Ollama en Linux."""
    print("\n" + "=" * 60)
    print("INSTALANDO OLLAMA EN LINUX")
    print("=" * 60)

    print("\nEjecutando script de instalación de Ollama...")

    try:
        # Descargar y ejecutar script de instalación
        result = subprocess.run(
            ["curl", "-fsSL", "https://ollama.com/install.sh"],
            capture_output=True,
            text=True,
            check=True
        )

        # Ejecutar el script
        subprocess.run(
            ["sh", "-c", result.stdout],
            check=True
        )

        print("\nInstalación de Ollama completada.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error durante la instalación: {e}")
        print("Por favor, instala manualmente desde: https://ollama.com/download")
        return False


def install_ollama_macos():
    """Instala Ollama en macOS."""
    print("\n" + "=" * 60)
    print("INSTALANDO OLLAMA EN MACOS")
    print("=" * 60)

    # Verificar si está disponible via Homebrew
    if shutil.which("brew"):
        print("\nInstalando via Homebrew...")
        try:
            subprocess.run(["brew", "install", "ollama"], check=True)
            print("\nInstalación de Ollama completada.")
            return True
        except subprocess.CalledProcessError:
            pass

    print("\nPor favor, descarga Ollama manualmente desde:")
    print("  https://ollama.com/download")
    print("\nO instala con Homebrew: brew install ollama")
    return False


def start_ollama_service():
    """Inicia el servicio de Ollama."""
    if is_ollama_running():
        print("Ollama ya está corriendo.")
        return True

    print("\nIniciando servicio Ollama...")

    system = platform.system()

    try:
        if system == "Windows":
            # En Windows, iniciar como proceso en segundo plano
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            # En Linux/macOS
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        # Esperar a que inicie
        for i in range(30):
            time.sleep(1)
            if is_ollama_running():
                print("Servicio Ollama iniciado correctamente.")
                return True
            print(f"\rEsperando que Ollama inicie... ({i+1}/30s)", end="", flush=True)

        print("\nAdvertencia: Ollama no respondió en 30 segundos.")
        return False

    except FileNotFoundError:
        print("Error: Comando 'ollama' no encontrado.")
        return False
    except Exception as e:
        print(f"Error iniciando Ollama: {e}")
        return False


def download_model(model_name: str) -> bool:
    """Descarga un modelo de Ollama."""
    print(f"\nDescargando modelo: {model_name}")
    print("(Esto puede tardar varios minutos dependiendo del tamaño del modelo)")

    try:
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(f"  {line.strip()}")

        process.wait()

        if process.returncode == 0:
            print(f"Modelo {model_name} instalado correctamente.")
            return True
        else:
            print(f"Error instalando modelo {model_name}.")
            return False

    except FileNotFoundError:
        print("Error: Comando 'ollama' no encontrado.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Configura Ollama y descarga los modelos necesarios."""
    print("=" * 60)
    print("CONFIGURACIÓN DE OLLAMA PARA NARRATIVE ASSISTANT")
    print("=" * 60)
    print("\nOllama permite ejecutar modelos LLM localmente para")
    print("análisis de comportamiento de personajes sin conexión a internet.")
    print()

    system = platform.system()
    print(f"Sistema operativo: {system}")

    # Paso 1: Verificar/Instalar Ollama
    if is_ollama_installed():
        print("\n✓ Ollama ya está instalado.")
    else:
        print("\n✗ Ollama no está instalado.")

        response = input("\n¿Deseas instalar Ollama ahora? (S/n): ").strip().lower()
        if response == "n":
            print("\nInstalación cancelada.")
            print("Puedes instalar Ollama manualmente desde: https://ollama.com/download")
            sys.exit(1)

        # Instalar según el sistema operativo
        success = False
        if system == "Windows":
            success = install_ollama_windows()
        elif system == "Linux":
            success = install_ollama_linux()
        elif system == "Darwin":
            success = install_ollama_macos()
        else:
            print(f"Sistema operativo no soportado: {system}")
            sys.exit(1)

        if not success:
            print("\nNo se pudo completar la instalación de Ollama.")
            sys.exit(1)

        # Verificar de nuevo
        if not is_ollama_installed():
            print("\nAdvertencia: Ollama no está en el PATH.")
            print("Puede que necesites reiniciar la terminal o el sistema.")
            sys.exit(1)

    # Paso 2: Iniciar servicio
    print("\n" + "-" * 40)
    print("INICIANDO SERVICIO OLLAMA")
    print("-" * 40)

    if not start_ollama_service():
        print("\nNo se pudo iniciar el servicio de Ollama.")
        print("Intenta ejecutar manualmente: ollama serve")
        sys.exit(1)

    # Paso 3: Verificar modelos instalados
    print("\n" + "-" * 40)
    print("VERIFICANDO MODELOS")
    print("-" * 40)

    installed_models = get_installed_models()
    print(f"\nModelos instalados: {installed_models if installed_models else 'Ninguno'}")

    # Paso 4: Descargar modelos necesarios
    models_to_download = []

    for model in DEFAULT_MODELS:
        if model not in installed_models:
            models_to_download.append(model)

    if models_to_download:
        print(f"\nModelos a descargar: {models_to_download}")

        for model in models_to_download:
            if not download_model(model):
                print(f"\nError descargando {model}. Continuando...")
    else:
        print("\nTodos los modelos necesarios ya están instalados.")

    # Paso 5: Preguntar por modelos opcionales
    print("\n" + "-" * 40)
    print("MODELOS OPCIONALES")
    print("-" * 40)
    print("\nModelos opcionales para mayor precisión en análisis:")
    print("  - qwen2.5 (7B): Excelente para textos en español")
    print("  - mistral (7B): Mayor calidad general")
    print("\nEstos modelos son más grandes y lentos, pero más precisos.")

    response = input("\n¿Descargar modelos opcionales? (s/N): ").strip().lower()
    if response == "s":
        for model in OPTIONAL_MODELS:
            if model not in installed_models:
                download_model(model)

    # Resumen final
    print("\n" + "=" * 60)
    print("CONFIGURACIÓN COMPLETADA")
    print("=" * 60)

    final_models = get_installed_models()
    print(f"\nModelos disponibles: {final_models}")

    print("\nOllama está configurado y listo para usar.")
    print("El análisis de comportamiento de personajes ahora funcionará")
    print("completamente offline.")

    print("\nPara verificar el estado de Ollama:")
    print("  ollama list    # Ver modelos instalados")
    print("  ollama serve   # Iniciar servidor (si no está corriendo)")

    print("\nPara descargar más modelos:")
    print("  ollama pull llama3.2")
    print("  ollama pull qwen2.5")
    print("  ollama pull mistral")


if __name__ == "__main__":
    main()
