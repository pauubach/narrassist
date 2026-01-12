#!/usr/bin/env python3
"""
Script para descargar modelos NLP y guardarlos localmente.

Uso:
    python scripts/download_models.py

Esto descargará los modelos y los guardará en:
    models/spacy/es_core_news_lg/
    models/embeddings/paraphrase-multilingual-MiniLM-L12-v2/

Una vez descargados, el proyecto funcionará 100% offline.
"""

import shutil
import sys
from pathlib import Path

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


def download_spacy_model():
    """Descarga el modelo spaCy y lo guarda localmente."""
    import spacy
    from spacy.cli import download

    model_name = "es_core_news_lg"
    target_dir = MODELS_DIR / "spacy" / model_name

    print(f"\n{'='*60}")
    print(f"Descargando modelo spaCy: {model_name}")
    print(f"{'='*60}")

    if target_dir.exists():
        print(f"El modelo ya existe en {target_dir}")
        response = input("¿Sobrescribir? (s/N): ").strip().lower()
        if response != "s":
            print("Omitiendo spaCy...")
            return
        shutil.rmtree(target_dir)

    # Descargar modelo
    print(f"Descargando {model_name}...")
    download(model_name)

    # Encontrar dónde se instaló
    nlp = spacy.load(model_name)
    model_path = Path(nlp.path)
    print(f"Modelo instalado en: {model_path}")

    # Copiar a directorio local
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"Copiando a {target_dir}...")
    shutil.copytree(model_path, target_dir)

    print(f"Modelo spaCy guardado en: {target_dir}")


def download_embeddings_model():
    """Descarga el modelo de embeddings y lo guarda localmente."""
    from sentence_transformers import SentenceTransformer

    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    target_dir = MODELS_DIR / "embeddings" / model_name

    print(f"\n{'='*60}")
    print(f"Descargando modelo embeddings: {model_name}")
    print(f"{'='*60}")

    if target_dir.exists():
        print(f"El modelo ya existe en {target_dir}")
        response = input("¿Sobrescribir? (s/N): ").strip().lower()
        if response != "s":
            print("Omitiendo embeddings...")
            return
        shutil.rmtree(target_dir)

    # Descargar modelo
    print(f"Descargando {model_name}...")
    model = SentenceTransformer(model_name)

    # Guardar localmente
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"Guardando en {target_dir}...")
    model.save(str(target_dir))

    print(f"Modelo embeddings guardado en: {target_dir}")


def main():
    """Descarga todos los modelos."""
    print("=" * 60)
    print("DESCARGA DE MODELOS NLP PARA USO OFFLINE")
    print("=" * 60)
    print(f"Directorio de destino: {MODELS_DIR}")
    print()

    # Verificar dependencias
    try:
        import spacy
        import sentence_transformers
    except ImportError as e:
        print(f"Error: Dependencias no instaladas: {e}")
        print("Ejecutar primero: pip install -e .")
        sys.exit(1)

    # Descargar modelos
    try:
        download_spacy_model()
        download_embeddings_model()
    except Exception as e:
        print(f"\nError descargando modelos: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("DESCARGA COMPLETADA")
    print("=" * 60)
    print(f"\nModelos guardados en: {MODELS_DIR}")
    print("\nEstructura:")
    print("  models/")
    print("  ├── spacy/")
    print("  │   └── es_core_news_lg/")
    print("  └── embeddings/")
    print("      └── paraphrase-multilingual-MiniLM-L12-v2/")
    print()
    print("El proyecto ahora funcionará 100% offline.")
    print("Puedes copiar la carpeta completa a otra máquina.")


if __name__ == "__main__":
    main()
