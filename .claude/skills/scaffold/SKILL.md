---
name: scaffold
description: "Genera boilerplate para un nuevo router FastAPI o componente Vue siguiendo los patrones exactos del proyecto (Result pattern, type hints, validate_file, PrimeVue). Invocar cuando el usuario diga 'crea un nuevo router para X', 'scaffold un componente Vue de Y', 'añade un endpoint para Z', 'nuevo módulo NLP para W'."
---

# /scaffold — Boilerplate desde patrones del proyecto

## Cuándo usar

- Añadir un nuevo router FastAPI (endpoint + esquemas Pydantic).
- Crear un nuevo componente Vue desde cero (con props, emits, composable).
- Iniciar un nuevo módulo NLP (parser, analyzer, extractor).
- Crear un nuevo test file con fixtures correctas desde el primer momento.

## Argumentos

- `router <nombre>` — nuevo router FastAPI en `api-server/routers/`
- `vue <nombre>` — nuevo componente Vue en `frontend/src/components/`
- `nlp <nombre>` — nuevo módulo NLP en `src/narrative_assistant/nlp/`
- `parser <nombre>` — nuevo parser en `src/narrative_assistant/parsers/`
- `test <módulo>` — nuevo archivo de test con fixtures apropiadas

## Flujo

### Paso 1 — Leer un ejemplo hermano

Antes de generar, leer el ejemplo más cercano del mismo tipo:

**Router FastAPI:** leer un router existente en `api-server/routers/` (preferir el más corto/reciente).
**Componente Vue:** leer el componente más similar en `frontend/src/components/`.
**Módulo NLP:** leer `src/narrative_assistant/nlp/ner.py` o el más similar al propósito.
**Parser:** leer `src/narrative_assistant/parsers/docx_parser.py` (el más completo).

### Paso 2 — Scaffold backend (router FastAPI)

Patrón canónico:

```python
"""Router para <descripción>."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from narrative_assistant.core.result import Result
# ... imports específicos

router = APIRouter(prefix="/api/<nombre>", tags=["<nombre>"])


class <Nombre>Request(BaseModel):
    """<descripción del request>."""
    # campos con type hints


class <Nombre>Response(BaseModel):
    """<descripción del response>."""
    success: bool
    data: <Tipo> | None = None
    error: str | None = None


@router.post("/")
async def <acción>_<nombre>(request: <Nombre>Request) -> <Nombre>Response:
    """<descripción>."""
    result: Result[<Tipo>] = await <servicio>.<método>(request.<campo>)
    if result.is_failure:
        return <Nombre>Response(success=False, error=str(result.error))
    return <Nombre>Response(success=True, data=result.value)
```

Luego añadir el router al main FastAPI app (`api-server/main.py` o equivalente):
```python
from routers import <nombre>
app.include_router(<nombre>.router)
```

### Paso 3 — Scaffold frontend (componente Vue)

Patrón canónico:

```vue
<template>
  <div class="<nombre-kebab>">
    <!-- template -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
// PrimeVue imports solo lo que se usa
import Button from 'primevue/button'

// Props
const props = defineProps<{
  // props con tipos exactos
}>()

// Emits
const emit = defineEmits<{
  // eventos
}>()

// Estado local
</script>
```

Reglas frontend (ver `.claude/rules/frontend-vue.md`):
- No `v-html` con datos de manuscritos.
- Nombres de componentes en PascalCase.
- `data-test="<nombre>"` en elementos interactivos para e2e.
- `aria-label` en botones sin texto visible.

### Paso 4 — Scaffold módulo NLP

```python
"""<Descripción del módulo>."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from narrative_assistant.core.result import Result

logger = logging.getLogger(__name__)


@dataclass
class <Nombre>Result:
    """Resultado de <operación>."""
    # campos


class <Nombre>Analyzer:
    """<Descripción>."""

    def analyze(self, text: str) -> Result[<Nombre>Result]:
        """<Descripción>.
        
        Args:
            text: Texto a analizar.
            
        Returns:
            Result con <Nombre>Result o error.
        """
        # implementación
```

### Paso 5 — Scaffold test

```python
"""Tests para <módulo>."""
import pytest
from narrative_assistant.<módulo> import <Clase>


class Test<Clase>:
    """Tests para <Clase>."""

    def test_<caso_feliz>(self) -> None:
        """<descripción>."""
        # arrange
        # act
        # assert

    def test_<edge_case>(self) -> None:
        """<descripción>."""
        # arrange
        # act
        # assert
```

Si el módulo usa spaCy → usar `shared_spacy_nlp` fixture de `conftest.py`.

### Paso 6 — Verificar

Tras generar, ejecutar `/check` para confirmar que el scaffold pasa lint y tipos desde el primer commit.
