#!/usr/bin/env python3
"""
Script para instalar y configurar Ollama con los modelos LLM necesarios.

Uso:
    python scripts/setup_ollama.py [--model MODEL] [--force] [--cpu]

Opciones:
    --model MODEL   Modelo a descargar (default: llama3.2)
                    Disponibles: llama3.2, qwen2.5, mistral, gemma2
    --force         Reinstalar Ollama aunque ya esté instalado
    --cpu           Forzar modo CPU (útil en Windows con GPU antigua)
    --silent        Instalación silenciosa (sin preguntas)

Este script usa el nuevo sistema de instalación bajo demanda de Ollama.
El análisis de comportamiento de personajes funciona con modelos locales,
sin necesidad de conexión a internet una vez instalado.
"""

import argparse
import sys
from pathlib import Path

# Añadir src al path para importar narrative_assistant
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def print_header(text: str) -> None:
    """Imprime un header formateado."""
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def print_section(text: str) -> None:
    """Imprime un separador de sección."""
    print()
    print("-" * 40)
    print(text)
    print("-" * 40)


def progress_callback(progress) -> None:
    """Callback para mostrar progreso de descarga."""
    if progress.status == "downloading":
        if progress.total_bytes > 0:
            mb_current = progress.current_bytes / (1024 * 1024)
            mb_total = progress.total_bytes / (1024 * 1024)
            print(f"\r  {progress.percentage:.1f}% ({mb_current:.1f}/{mb_total:.1f} MB)", end="", flush=True)
        else:
            print(f"\r  {progress.percentage:.1f}%", end="", flush=True)
    elif progress.status == "complete":
        print("\n  Completado!")
    elif progress.status == "error":
        print(f"\n  Error: {progress.error}")


def main():
    """Configura Ollama y descarga los modelos necesarios."""
    parser = argparse.ArgumentParser(
        description="Instala y configura Ollama para Narrative Assistant"
    )
    parser.add_argument(
        "--model",
        default="llama3.2",
        choices=["llama3.2", "qwen2.5", "mistral", "gemma2"],
        help="Modelo a descargar (default: llama3.2)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstalar Ollama aunque ya esté instalado"
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Forzar modo CPU"
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Instalación silenciosa"
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Descargar todos los modelos disponibles"
    )

    args = parser.parse_args()

    print_header("CONFIGURACIÓN DE OLLAMA PARA NARRATIVE ASSISTANT")
    print("\nOllama permite ejecutar modelos LLM localmente para")
    print("análisis de comportamiento de personajes sin conexión a internet.")

    # Importar el gestor
    try:
        from narrative_assistant.llm.ollama_manager import (
            get_ollama_manager,
            OllamaStatus,
            AVAILABLE_MODELS,
        )
    except ImportError as e:
        print(f"\nError importando módulo: {e}")
        print("Asegúrate de que el paquete está instalado: pip install -e .")
        sys.exit(1)

    manager = get_ollama_manager()

    # Información del sistema
    print(f"\nSistema operativo: {manager.platform.value}")

    # Paso 1: Verificar/Instalar Ollama
    print_section("VERIFICANDO INSTALACIÓN DE OLLAMA")

    if manager.is_installed and not args.force:
        version = manager.get_version() or "desconocida"
        print(f"\n[OK] Ollama ya está instalado (versión: {version})")
    else:
        if manager.is_installed:
            print("\n[!] Reinstalando Ollama...")
        else:
            print("\n[X] Ollama no está instalado")

        if not args.silent:
            response = input("\n¿Deseas instalar Ollama ahora? (S/n): ").strip().lower()
            if response == "n":
                print("\nInstalación cancelada.")
                print("Puedes instalar Ollama manualmente desde: https://ollama.com/download")
                sys.exit(1)

        print("\nInstalando Ollama...")
        success, msg = manager.install_ollama(
            progress_callback=progress_callback,
            silent=args.silent
        )

        if not success:
            print(f"\n[ERROR] {msg}")
            sys.exit(1)

        print(f"\n[OK] {msg}")

    # Paso 2: Iniciar servicio
    print_section("INICIANDO SERVICIO OLLAMA")

    if manager.is_running:
        print("\n[OK] Ollama ya está corriendo")
    else:
        print("\nIniciando servicio Ollama...")
        success, msg = manager.start_service(force_cpu=args.cpu)

        if not success:
            print(f"\n[ERROR] {msg}")
            print("\nIntenta iniciar manualmente:")
            print("  ollama serve")
            sys.exit(1)

        print(f"\n[OK] {msg}")

    # Paso 3: Verificar modelos instalados
    print_section("VERIFICANDO MODELOS")

    downloaded = manager.downloaded_models
    print(f"\nModelos instalados: {downloaded if downloaded else 'Ninguno'}")

    # Mostrar modelos disponibles
    print("\nModelos disponibles:")
    for model in AVAILABLE_MODELS:
        status = "[OK]" if model.name in downloaded else "[--]"
        default = " (default)" if model.is_default else ""
        print(f"  {status} {model.display_name}{default} - {model.size_gb} GB")
        print(f"      {model.description}")

    # Paso 4: Descargar modelo(s)
    print_section("DESCARGANDO MODELOS")

    models_to_download = []

    if args.all_models:
        models_to_download = [m.name for m in AVAILABLE_MODELS if m.name not in downloaded]
    elif args.model not in downloaded:
        models_to_download = [args.model]

    if models_to_download:
        print(f"\nModelos a descargar: {models_to_download}")

        for model in models_to_download:
            model_info = next((m for m in AVAILABLE_MODELS if m.name == model), None)
            if model_info:
                print(f"\nDescargando {model_info.display_name} (~{model_info.size_gb} GB)...")
            else:
                print(f"\nDescargando {model}...")

            success, msg = manager.download_model(model, progress_callback=progress_callback)

            if success:
                print(f"[OK] {msg}")
            else:
                print(f"[ERROR] {msg}")
    else:
        if args.model in downloaded:
            print(f"\n[OK] Modelo {args.model} ya está descargado")
        else:
            print("\nTodos los modelos solicitados ya están instalados.")

    # Paso 5: Preguntar por modelos opcionales (si no es silent)
    if not args.silent and not args.all_models:
        optional_models = [m for m in AVAILABLE_MODELS if m.name not in downloaded and m.name != args.model]

        if optional_models:
            print_section("MODELOS OPCIONALES")
            print("\nModelos opcionales para mayor precisión en análisis:")
            for model in optional_models:
                print(f"  - {model.display_name}: {model.description}")

            response = input("\n¿Descargar modelos opcionales? (s/N): ").strip().lower()
            if response == "s":
                for model in optional_models:
                    print(f"\nDescargando {model.display_name}...")
                    success, msg = manager.download_model(model.name, progress_callback=progress_callback)
                    if success:
                        print(f"[OK] {msg}")
                    else:
                        print(f"[ERROR] {msg}")

    # Resumen final
    print_header("CONFIGURACIÓN COMPLETADA")

    final_models = manager.downloaded_models
    print(f"\nModelos disponibles: {final_models}")

    if final_models:
        print("\nOllama está configurado y listo para usar.")
        print("El análisis de comportamiento de personajes ahora funcionará")
        print("completamente offline.")
    else:
        print("\n[ADVERTENCIA] No hay modelos descargados.")
        print("Usa 'ollama pull llama3.2' para descargar el modelo por defecto.")

    print("\nComandos útiles:")
    print("  ollama list    # Ver modelos instalados")
    print("  ollama serve   # Iniciar servidor (si no está corriendo)")
    print("  ollama pull MODEL  # Descargar un modelo")

    if args.cpu:
        print("\n[NOTA] Ollama está configurado en modo CPU.")
        print("Para usar GPU, reinicia el servicio sin la opción --cpu.")


if __name__ == "__main__":
    main()
