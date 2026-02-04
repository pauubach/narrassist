#!/usr/bin/env python3
"""
Script para descargar modelos NLP bajo demanda.

Este script descarga los modelos NLP necesarios y los guarda en el
directorio de cache del usuario (~/.narrative_assistant/models/).

Uso:
    python scripts/download_models.py              # Descargar todos los modelos
    python scripts/download_models.py --force      # Re-descargar aunque existan
    python scripts/download_models.py --spacy      # Solo modelo spaCy
    python scripts/download_models.py --embeddings # Solo modelo embeddings
    python scripts/download_models.py --status     # Ver estado de modelos

Modelos descargados:
    ~/.narrative_assistant/models/spacy/es_core_news_lg/
    ~/.narrative_assistant/models/embeddings/paraphrase-multilingual-MiniLM-L12-v2/

Variables de entorno:
    NA_MODELS_DIR: Directorio alternativo para modelos (default: ~/.narrative_assistant/models/)

Una vez descargados, el proyecto funcionará 100% offline.
"""

import argparse
import sys
from pathlib import Path

# Añadir src al path para importar el paquete
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def create_progress_callback(model_name: str):
    """Crea un callback de progreso con tqdm."""
    try:
        from tqdm import tqdm

        pbar = None
        last_percent = 0

        def callback(message: str, percent: float):
            nonlocal pbar, last_percent

            if pbar is None:
                pbar = tqdm(
                    total=100,
                    desc=model_name,
                    unit="%",
                    bar_format="{l_bar}{bar}| {n:.0f}/{total:.0f}% [{elapsed}<{remaining}]",
                )

            # Actualizar barra
            increment = int(percent * 100) - last_percent
            if increment > 0:
                pbar.update(increment)
                last_percent = int(percent * 100)

            # Actualizar descripción
            if message:
                pbar.set_description(f"{model_name}: {message}")

            # Cerrar si completado
            if percent >= 1.0:
                pbar.close()
                pbar = None
                last_percent = 0

        return callback

    except ImportError:
        # Sin tqdm, usar print simple
        def callback(message: str, percent: float):
            print(f"  [{int(percent * 100):3d}%] {message}")

        return callback


def show_status():
    """Muestra el estado de todos los modelos."""
    from narrative_assistant.core.model_manager import get_model_manager

    print("\n" + "=" * 60)
    print("ESTADO DE MODELOS NLP")
    print("=" * 60)

    manager = get_model_manager()
    status = manager.get_all_models_status()

    print(f"\nDirectorio de modelos: {manager.models_dir}")
    print()

    for model_name, info in status.items():
        icon = "[OK]" if info["installed"] else "[  ]"
        size = f"~{info['size_mb']} MB"

        print(f"  {icon} {info['display_name']}")
        print(f"        Nombre: {model_name}")
        print(f"        Tamaño: {size}")

        if info["installed"]:
            print(f"        Ruta: {info['path']}")
        else:
            print("        Estado: No instalado")
        print()


def download_models(
    force: bool = False,
    download_spacy: bool = True,
    download_embeddings: bool = True,
):
    """Descarga los modelos especificados."""
    from narrative_assistant.core.model_manager import (
        ModelType,
        get_model_manager,
    )

    print("\n" + "=" * 60)
    print("DESCARGA DE MODELOS NLP")
    print("=" * 60)

    manager = get_model_manager()
    print(f"\nDirectorio de destino: {manager.models_dir}")

    if force:
        print("Modo: Re-descarga forzada")
    print()

    success_count = 0
    error_count = 0

    # Descargar spaCy
    if download_spacy:
        print("\n" + "-" * 40)
        print("Modelo spaCy (es_core_news_lg)")
        print("-" * 40)

        callback = create_progress_callback("spaCy")
        result = manager.ensure_model(
            ModelType.SPACY, force_download=force, progress_callback=callback
        )

        if result.is_success:
            print(f"\n  Instalado en: {result.value}")
            success_count += 1
        else:
            print(f"\n  ERROR: {result.error.message if result.error else 'Desconocido'}")
            error_count += 1

    # Descargar embeddings
    if download_embeddings:
        print("\n" + "-" * 40)
        print("Modelo Embeddings (paraphrase-multilingual-MiniLM-L12-v2)")
        print("-" * 40)

        callback = create_progress_callback("Embeddings")
        result = manager.ensure_model(
            ModelType.EMBEDDINGS, force_download=force, progress_callback=callback
        )

        if result.is_success:
            print(f"\n  Instalado en: {result.value}")
            success_count += 1
        else:
            print(f"\n  ERROR: {result.error.message if result.error else 'Desconocido'}")
            error_count += 1

    # Resumen
    print("\n" + "=" * 60)
    if error_count == 0:
        print("DESCARGA COMPLETADA")
    else:
        print("DESCARGA COMPLETADA CON ERRORES")
    print("=" * 60)

    print(f"\nModelos instalados: {success_count}")
    if error_count > 0:
        print(f"Errores: {error_count}")

    print(f"\nDirectorio: {manager.models_dir}")
    print("\nEstructura:")
    print("  ~/.narrative_assistant/")
    print("  └── models/")
    print("      ├── spacy/")
    print("      │   └── es_core_news_lg/")
    print("      └── embeddings/")
    print("          └── paraphrase-multilingual-MiniLM-L12-v2/")
    print()

    if error_count == 0:
        print("El proyecto ahora funcionará 100% offline.")
    else:
        print("Algunos modelos no se pudieron descargar.")
        print("Verifica tu conexión a internet e intenta nuevamente.")

    return error_count == 0


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Descarga modelos NLP para Narrative Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/download_models.py              # Descargar todos
  python scripts/download_models.py --force      # Re-descargar
  python scripts/download_models.py --spacy      # Solo spaCy
  python scripts/download_models.py --status     # Ver estado

Variables de entorno:
  NA_MODELS_DIR    Directorio alternativo para modelos
        """,
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Re-descargar modelos aunque ya existan",
    )

    parser.add_argument(
        "--spacy",
        action="store_true",
        help="Descargar solo modelo spaCy",
    )

    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Descargar solo modelo embeddings",
    )

    parser.add_argument(
        "--status",
        "-s",
        action="store_true",
        help="Mostrar estado de modelos instalados",
    )

    args = parser.parse_args()

    # Si se pide status, mostrar y salir
    if args.status:
        show_status()
        return 0

    # Determinar qué modelos descargar
    download_spacy = True
    download_embeddings = True

    if args.spacy or args.embeddings:
        # Si se especifica alguno, descargar solo los especificados
        download_spacy = args.spacy
        download_embeddings = args.embeddings

    # Verificar dependencias
    try:
        import spacy
        import sentence_transformers
    except ImportError as e:
        print(f"Error: Dependencias no instaladas: {e}")
        print("Ejecutar primero: pip install -e .")
        return 1

    # Descargar modelos
    success = download_models(
        force=args.force,
        download_spacy=download_spacy,
        download_embeddings=download_embeddings,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
