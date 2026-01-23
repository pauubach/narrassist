# STEP 0.1: Configuración del Entorno

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | S (2-4 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | Ninguno |

---

## Descripción

Configurar el entorno de desarrollo Python con todas las dependencias necesarias para el sistema de análisis narrativo.

---

## Inputs

- Python 3.11+ instalado
- pip/uv disponible
- 16GB RAM mínimo

---

## Outputs

- `pyproject.toml` con dependencias
- Modelo spaCy descargado (`es_core_news_lg`)
- Script de verificación de entorno
- Benchmark de memoria con documento de 100k palabras

---

## Implementación

### pyproject.toml

```toml
[project]
name = "narrative-assistant"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "spacy>=3.7.0",
    "coreferee>=1.4.0",
    "sentence-transformers>=2.2.0",
    "python-docx>=1.1.0",
    "sqlite-utils>=3.35",
    "rich>=13.0.0",
    "typer>=0.9.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.1.0"]
```

### Comandos post-instalación

```bash
# Instalar dependencias
pip install -e .

# Descargar modelo spaCy
python -m spacy download es_core_news_lg

# Instalar modelo de correferencia
python -m coreferee install es
```

### Script de verificación

```python
# verify_environment.py
import sys

def verify():
    print("Verificando entorno...")

    # Python version
    assert sys.version_info >= (3, 11), "Requiere Python 3.11+"
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")

    # spaCy
    import spacy
    nlp = spacy.load("es_core_news_lg")
    print("✅ spaCy con es_core_news_lg")

    # Coreferee
    import coreferee
    nlp.add_pipe('coreferee')
    print("✅ Coreferee instalado")

    # Sentence Transformers
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("✅ Sentence Transformers")

    # python-docx
    from docx import Document
    print("✅ python-docx")

    # Test NER
    doc = nlp("Juan García vive en Madrid.")
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    assert any(label == "PER" for _, label in entities), "NER no detecta personas"
    print("✅ NER funcional")

    print("\n🎉 Entorno configurado correctamente")

if __name__ == "__main__":
    verify()
```

---

## Criterio de DONE

```python
import spacy
nlp = spacy.load("es_core_news_lg")
doc = nlp("Juan tiene ojos verdes.")
assert any(ent.label_ == "PER" for ent in doc.ents)
print("✅ Entorno configurado correctamente")
```

---

## Advertencias

⚠️ **Memoria**: 16GB puede no ser suficiente si se cargan simultáneamente:
- spaCy con modelo grande (~500MB)
- Embeddings (~400MB)
- LLM local (si se usa)

**Recomendación**: Ejecutar benchmark de memoria antes de continuar.

---

## Siguiente

[STEP 0.2: Estructura del Proyecto](./step-0.2-project-structure.md)
