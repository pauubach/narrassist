# STEP 1.2: Detector de Estructura

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 1.1 |

---

## Descripción

Detectar capítulos y escenas en el documento usando estilos de Word y patrones regex.

---

## Inputs

- `ParsedDocument` de STEP 1.1

---

## Outputs

- `src/narrative_assistant/parsers/structure_detector.py`
- Lista de capítulos con posiciones start/end
- Detección de separadores de escena (`* * *`, `---`, etc.)

---

## Implementación

```python
import re
from typing import List, Optional
from dataclasses import dataclass

# Patrones para detectar inicio de capítulo
CHAPTER_PATTERNS = [
    r'^Capítulo\s+(\d+|[IVXLCDM]+)',  # Capítulo 1, Capítulo IV
    r'^CAPÍTULO\s+(\d+|[IVXLCDM]+)',
    r'^Cap\.\s*(\d+)',
    r'^(\d+)\s*$',  # Solo número
    r'^([IVXLCDM]+)\s*$',  # Solo número romano
]

# Patrones para separadores de escena
SCENE_SEPARATORS = [
    r'^\*\s*\*\s*\*\s*$',  # * * *
    r'^---+\s*$',          # ---
    r'^###\s*$',           # ###
]

@dataclass
class Scene:
    number: int
    start_char: int
    end_char: int

@dataclass
class Chapter:
    number: int
    title: Optional[str]
    start_char: int
    end_char: int
    scenes: List[Scene]

def detect_structure(doc: 'ParsedDocument') -> List[Chapter]:
    """Detecta capítulos y escenas en el documento."""
    chapters = []

    # Primero, detectar por estilos de Word (más fiable)
    heading_paragraphs = [
        p for p in doc.paragraphs
        if p.style and 'Heading' in p.style
    ]

    # Si no hay headings, usar patrones regex
    if not heading_paragraphs:
        heading_paragraphs = [
            p for p in doc.paragraphs
            if any(re.match(pat, p.text, re.IGNORECASE) for pat in CHAPTER_PATTERNS)
        ]

    # Construir capítulos
    for i, para in enumerate(heading_paragraphs):
        next_para = heading_paragraphs[i + 1] if i + 1 < len(heading_paragraphs) else None
        end_char = next_para.start_char if next_para else len(doc.text)

        # Detectar escenas dentro del capítulo
        chapter_text = doc.text[para.start_char:end_char]
        scenes = _detect_scenes(chapter_text, para.start_char)

        chapters.append(Chapter(
            number=i + 1,
            title=para.text,
            start_char=para.start_char,
            end_char=end_char,
            scenes=scenes
        ))

    return chapters

def _detect_scenes(text: str, offset: int) -> List[Scene]:
    """Detecta escenas dentro de un capítulo."""
    scenes = []
    scene_starts = [0]

    for pattern in SCENE_SEPARATORS:
        for match in re.finditer(pattern, text, re.MULTILINE):
            scene_starts.append(match.end())

    scene_starts = sorted(set(scene_starts))

    for i, start in enumerate(scene_starts):
        end = scene_starts[i + 1] if i + 1 < len(scene_starts) else len(text)
        scenes.append(Scene(
            number=i + 1,
            start_char=offset + start,
            end_char=offset + end
        ))

    return scenes
```

---

## Criterio de DONE

```python
from narrative_assistant.parsers import detect_structure

chapters = detect_structure(parsed_doc)
assert len(chapters) > 0
assert all(c.number for c in chapters)
print(f"✅ Detectados {len(chapters)} capítulos")
```

---

## Siguiente

[STEP 1.3: Pipeline NER](./step-1.3-ner-pipeline.md)
