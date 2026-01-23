# STEP 1.1: Parser DOCX

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 0.3 |

---

## Descripción

Extraer texto de archivos DOCX preservando metadatos de posición y estilos de Word.

---

## Inputs

- Archivos `.docx` de prueba (incluir en `tests/fixtures/`)

---

## Outputs

- `src/narrative_assistant/parsers/docx_parser.py`
- Texto plano con metadatos de posición
- Preservación de estilos (Heading 1, Heading 2, etc.)

---

## Implementación

```python
from dataclasses import dataclass
from pathlib import Path
from docx import Document
from typing import List, Optional

@dataclass
class Paragraph:
    text: str
    style: Optional[str]
    start_char: int
    end_char: int

@dataclass
class ParsedDocument:
    file_path: Path
    text: str  # Texto plano completo
    paragraphs: List[Paragraph]
    word_count: int

def parse_docx(file_path: str | Path) -> ParsedDocument:
    """
    Extrae texto de un archivo DOCX preservando metadatos de posición.

    Args:
        file_path: Ruta al archivo .docx

    Returns:
        ParsedDocument con texto y metadatos
    """
    doc = Document(file_path)
    paragraphs = []
    full_text_parts = []
    current_pos = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        start = current_pos
        end = current_pos + len(text)

        paragraphs.append(Paragraph(
            text=text,
            style=para.style.name if para.style else None,
            start_char=start,
            end_char=end
        ))

        full_text_parts.append(text)
        current_pos = end + 1  # +1 por salto de línea

    full_text = "\n".join(full_text_parts)

    return ParsedDocument(
        file_path=Path(file_path),
        text=full_text,
        paragraphs=paragraphs,
        word_count=len(full_text.split())
    )
```

---

## Criterio de DONE

```python
from narrative_assistant.parsers import parse_docx

result = parse_docx("tests/fixtures/sample_novel.docx")
assert result.text  # Texto extraído
assert result.paragraphs  # Lista de párrafos con posiciones
assert any(p.style == "Heading 1" for p in result.paragraphs)
print("✅ Parser DOCX funcional")
```

---

## Siguiente

[STEP 1.2: Detector de Estructura](./step-1.2-structure-detector.md)
