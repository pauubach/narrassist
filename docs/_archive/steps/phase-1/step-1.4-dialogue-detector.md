# STEP 1.4: Detector de Diálogos

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | S (2-4 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | STEP 1.1 |

---

## Descripción

Detectar intervenciones de diálogo usando los distintos formatos del español: raya (—), comillas latinas («»), y comillas inglesas ("").

---

## Inputs

- Texto plano del documento

---

## Outputs

- `src/narrative_assistant/nlp/dialogue.py`
- Lista de intervenciones con posición
- Soporte para múltiples formatos de diálogo

---

## Implementación

```python
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DialogueSpan:
    text: str
    start_char: int
    end_char: int
    dialogue_type: str  # 'dash', 'guillemets', 'quotes'
    attribution_text: Optional[str] = None

# Patrones de diálogo en español
DIALOGUE_PATTERNS = [
    # Raya española: —Texto— dijo X / —Texto.
    (r'—([^—\n]+)(?:—\s*([^.!?\n]+[.!?]?))?', 'dash'),

    # Comillas latinas: «Texto»
    (r'«([^»]+)»', 'guillemets'),

    # Comillas inglesas: "Texto"
    (r'"([^"]+)"', 'quotes'),

    # Comillas españolas tipográficas: "Texto"
    (r'"([^"]+)"', 'quotes_es'),
]

def detect_dialogues(text: str) -> List[DialogueSpan]:
    """Detecta intervenciones de diálogo en el texto."""
    dialogues = []

    for pattern, dtype in DIALOGUE_PATTERNS:
        for match in re.finditer(pattern, text):
            dialogue_text = match.group(1)
            attribution = match.group(2) if match.lastindex >= 2 else None

            dialogues.append(DialogueSpan(
                text=dialogue_text,
                start_char=match.start(),
                end_char=match.end(),
                dialogue_type=dtype,
                attribution_text=attribution
            ))

    # Ordenar por posición y eliminar duplicados
    dialogues.sort(key=lambda d: d.start_char)
    return _remove_overlapping(dialogues)

def _remove_overlapping(dialogues: List[DialogueSpan]) -> List[DialogueSpan]:
    """Elimina diálogos que se solapan, manteniendo el más largo."""
    result = []
    for d in dialogues:
        if not result or d.start_char >= result[-1].end_char:
            result.append(d)
        elif len(d.text) > len(result[-1].text):
            result[-1] = d
    return result
```

---

## Criterio de DONE

```python
from narrative_assistant.nlp import detect_dialogues

text = '—¿Vienes? —preguntó Juan.\n«Sí» respondió María.'
dialogues = detect_dialogues(text)

assert len(dialogues) >= 2
assert any("Vienes" in d.text for d in dialogues)
assert any("Sí" in d.text for d in dialogues)

print(f"✅ Detectados {len(dialogues)} diálogos")
```

---

## Siguiente

[STEP 2.1: Correferencia Básica](../phase-2/step-2.1-coreference.md)
