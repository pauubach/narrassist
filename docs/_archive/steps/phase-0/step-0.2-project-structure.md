# STEP 0.2: Estructura del Proyecto

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | S (1-2 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 0.1 |

---

## Descripción

Crear la estructura de directorios del proyecto siguiendo la arquitectura modular definida.

---

## Inputs

- Documento de especificación (este repositorio)

---

## Outputs

- Estructura de directorios creada
- `__init__.py` en cada módulo
- `.gitignore` configurado
- `README.md` básico

---

## Implementación

### Estructura de directorios

```
narrative-assistant/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/
│   └── narrative_assistant/
│       ├── __init__.py
│       ├── cli.py                    # Interfaz de línea de comandos
│       ├── config.py                 # Configuración y constantes
│       │
│       ├── db/                       # Capa de datos
│       │   ├── __init__.py
│       │   ├── schema.sql            # DDL de SQLite
│       │   ├── models.py             # Dataclasses
│       │   └── repository.py         # CRUD operations
│       │
│       ├── parsers/                  # Importación de documentos
│       │   ├── __init__.py
│       │   ├── docx_parser.py
│       │   └── structure_detector.py
│       │
│       ├── nlp/                      # Pipeline NLP
│       │   ├── __init__.py
│       │   ├── pipeline.py
│       │   ├── ner.py
│       │   ├── coref.py
│       │   ├── dialogue.py
│       │   ├── speaker.py
│       │   ├── temporal.py
│       │   └── attributes.py
│       │
│       ├── analysis/                 # Detectores de inconsistencias
│       │   ├── __init__.py
│       │   ├── name_variants.py
│       │   ├── attribute_consistency.py
│       │   ├── repetitions.py
│       │   ├── timeline.py
│       │   ├── voice_profiles.py
│       │   ├── register.py
│       │   └── focalization.py
│       │
│       ├── alerts/                   # Sistema de alertas
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── confidence.py
│       │   └── types.py
│       │
│       └── export/                   # Generación de outputs
│           ├── __init__.py
│           ├── character_sheet.py
│           ├── style_guide.py
│           └── report.py
│
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── sample_novel.docx
│   │   └── known_errors.json
│   ├── test_parsers.py
│   ├── test_nlp.py
│   └── test_analysis.py
│
└── data/
    └── .gitkeep
```

### Script de creación

```bash
#!/bin/bash
# create_structure.sh

mkdir -p src/narrative_assistant/{db,parsers,nlp,analysis,alerts,export}
mkdir -p tests/fixtures
mkdir -p data

# Crear __init__.py
for dir in src/narrative_assistant src/narrative_assistant/{db,parsers,nlp,analysis,alerts,export} tests; do
    touch "$dir/__init__.py"
done

# Crear .gitkeep
touch data/.gitkeep

# Crear .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
.env
*.db
data/*.db
.DS_Store
EOF

echo "✅ Estructura creada"
```

---

## Criterio de DONE

```bash
tree src/
# Debe mostrar la estructura completa
```

O con Python:

```python
from pathlib import Path

required_dirs = [
    "src/narrative_assistant/db",
    "src/narrative_assistant/parsers",
    "src/narrative_assistant/nlp",
    "src/narrative_assistant/analysis",
    "src/narrative_assistant/alerts",
    "src/narrative_assistant/export",
    "tests/fixtures",
]

for d in required_dirs:
    assert Path(d).exists(), f"Falta: {d}"

print("✅ Estructura correcta")
```

---

## Siguiente

[STEP 0.3: Schema de Base de Datos](./step-0.3-database-schema.md)
