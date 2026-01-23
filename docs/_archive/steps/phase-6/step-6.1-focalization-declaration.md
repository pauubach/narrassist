# STEP 6.1: Sistema de Declaración de Focalización

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P3 (Experimental) |
| **Prerequisitos** | STEP 1.2 |

---

## Descripción

Permitir al usuario **declarar** la focalización de cada capítulo/escena. La detección automática de focalización es extremadamente difícil y propensa a errores, por lo que el enfoque es:

1. El usuario declara la focalización
2. El sistema detecta **violaciones** a esa declaración

---

## Tipos de Focalización (Genette)

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `zero` | Omnisciente, acceso a todo | "Juan pensó... María sabía..." |
| `internal_fixed` | Un personaje, su mente | "Juan pensó..." (solo Juan) |
| `internal_variable` | Cambia entre personajes | Cap 1: Juan / Cap 2: María |
| `internal_multiple` | Varios simultáneos | Mismo evento desde varias perspectivas |
| `external` | Solo observable, sin mentes | "Juan frunció el ceño" (no "pensó") |

---

## Inputs

- Estructura de capítulos/escenas
- Entidades de tipo personaje

---

## Outputs

- `src/narrative_assistant/focalization/declaration.py`
- Sistema de declaración
- Persistencia en base de datos
- API para consulta y modificación

---

## Modelo de Datos

```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class FocalizationType(Enum):
    ZERO = "zero"                    # Omnisciente
    INTERNAL_FIXED = "internal_fixed"  # Un solo personaje
    INTERNAL_VARIABLE = "internal_variable"  # Cambia por escena
    INTERNAL_MULTIPLE = "internal_multiple"  # Varios simultáneos
    EXTERNAL = "external"            # Solo observable

@dataclass
class FocalizationDeclaration:
    id: int
    project_id: int
    chapter: int
    scene: Optional[int]  # None = todo el capítulo

    focalization_type: FocalizationType
    focalizer_ids: List[int]  # IDs de personajes focalizadores

    # Metadata
    declared_at: datetime
    declared_by: str  # 'user' o 'system_suggestion'
    notes: str = ""

    # Validación
    is_validated: bool = False
    violations_count: int = 0

@dataclass
class FocalizationScope:
    """Define el alcance de una focalización."""
    start_chapter: int
    start_scene: Optional[int]
    end_chapter: int
    end_scene: Optional[int]

    def contains(self, chapter: int, scene: Optional[int] = None) -> bool:
        """Verifica si una posición está dentro del alcance."""
        if chapter < self.start_chapter or chapter > self.end_chapter:
            return False
        if chapter == self.start_chapter and scene is not None:
            if self.start_scene is not None and scene < self.start_scene:
                return False
        if chapter == self.end_chapter and scene is not None:
            if self.end_scene is not None and scene > self.end_scene:
                return False
        return True
```

---

## Implementación

```python
from typing import List, Optional, Dict
from datetime import datetime

class FocalizationDeclarationService:
    def __init__(self, repository: 'Repository'):
        self.repo = repository

    def declare_focalization(
        self,
        project_id: int,
        chapter: int,
        focalization_type: FocalizationType,
        focalizer_ids: List[int],
        scene: Optional[int] = None,
        notes: str = ""
    ) -> FocalizationDeclaration:
        """Declara la focalización de un capítulo/escena."""
        # Validar que los focalizadores existen
        for fid in focalizer_ids:
            entity = self.repo.get_entity(fid)
            if not entity:
                raise ValueError(f"Entity {fid} not found")
            if entity.entity_type != 'person':
                raise ValueError(f"Entity {fid} is not a person")

        # Validar coherencia tipo-focalizadores
        self._validate_focalization_type(focalization_type, focalizer_ids)

        declaration = FocalizationDeclaration(
            id=0,  # Se asigna al guardar
            project_id=project_id,
            chapter=chapter,
            scene=scene,
            focalization_type=focalization_type,
            focalizer_ids=focalizer_ids,
            declared_at=datetime.now(),
            declared_by='user',
            notes=notes,
            is_validated=False,
            violations_count=0
        )

        return self.repo.save_focalization(declaration)

    def _validate_focalization_type(
        self,
        foc_type: FocalizationType,
        focalizer_ids: List[int]
    ) -> None:
        """Valida coherencia entre tipo y focalizadores."""
        if foc_type == FocalizationType.ZERO:
            # Omnisciente: no necesita focalizadores específicos
            pass
        elif foc_type == FocalizationType.INTERNAL_FIXED:
            if len(focalizer_ids) != 1:
                raise ValueError("Internal fixed requires exactly 1 focalizer")
        elif foc_type == FocalizationType.INTERNAL_VARIABLE:
            if len(focalizer_ids) < 1:
                raise ValueError("Internal variable requires at least 1 focalizer")
        elif foc_type == FocalizationType.INTERNAL_MULTIPLE:
            if len(focalizer_ids) < 2:
                raise ValueError("Internal multiple requires at least 2 focalizers")
        elif foc_type == FocalizationType.EXTERNAL:
            if focalizer_ids:
                raise ValueError("External focalization should not have focalizers")

    def get_focalization(
        self,
        project_id: int,
        chapter: int,
        scene: Optional[int] = None
    ) -> Optional[FocalizationDeclaration]:
        """Obtiene la focalización declarada para una posición."""
        # Buscar declaración específica para escena
        if scene is not None:
            declaration = self.repo.get_focalization(project_id, chapter, scene)
            if declaration:
                return declaration

        # Buscar declaración para capítulo completo
        return self.repo.get_focalization(project_id, chapter, None)

    def get_all_declarations(
        self,
        project_id: int
    ) -> List[FocalizationDeclaration]:
        """Obtiene todas las declaraciones de un proyecto."""
        return self.repo.get_all_focalizations(project_id)

    def update_focalization(
        self,
        declaration_id: int,
        focalization_type: Optional[FocalizationType] = None,
        focalizer_ids: Optional[List[int]] = None,
        notes: Optional[str] = None
    ) -> FocalizationDeclaration:
        """Actualiza una declaración existente."""
        declaration = self.repo.get_focalization_by_id(declaration_id)
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")

        if focalization_type is not None:
            ids = focalizer_ids if focalizer_ids is not None else declaration.focalizer_ids
            self._validate_focalization_type(focalization_type, ids)
            declaration.focalization_type = focalization_type

        if focalizer_ids is not None:
            ftype = focalization_type if focalization_type is not None else declaration.focalization_type
            self._validate_focalization_type(ftype, focalizer_ids)
            declaration.focalizer_ids = focalizer_ids

        if notes is not None:
            declaration.notes = notes

        # Resetear validación al modificar
        declaration.is_validated = False
        declaration.violations_count = 0

        return self.repo.save_focalization(declaration)

    def delete_focalization(self, declaration_id: int) -> bool:
        """Elimina una declaración."""
        return self.repo.delete_focalization(declaration_id)

    def suggest_focalization(
        self,
        project_id: int,
        chapter: int,
        text: str,
        entities: List['Entity']
    ) -> Dict[str, any]:
        """Sugiere posible focalización basándose en el texto."""
        # Heurísticas simples para sugerir
        suggestions = {
            'suggested_type': None,
            'suggested_focalizers': [],
            'confidence': 0.0,
            'evidence': []
        }

        text_lower = text.lower()

        # Buscar verbos de pensamiento/percepción
        thought_verbs = ['pensó', 'sintió', 'sabía', 'recordó', 'imaginó', 'temía']
        perception_verbs = ['vio', 'oyó', 'escuchó', 'notó', 'percibió']

        thought_mentions = []
        for verb in thought_verbs + perception_verbs:
            if verb in text_lower:
                thought_mentions.append(verb)

        # Si no hay verbos de pensamiento, podría ser externa
        if not thought_mentions:
            suggestions['suggested_type'] = FocalizationType.EXTERNAL
            suggestions['confidence'] = 0.4
            suggestions['evidence'].append("No se detectan verbos de pensamiento/percepción")
            return suggestions

        # Buscar qué personajes tienen acceso mental
        characters_with_thoughts = set()
        for entity in entities:
            if entity.entity_type != 'person':
                continue
            name = entity.canonical_name.lower()
            # Buscar patrón "Nombre pensó/sintió..."
            for verb in thought_verbs:
                pattern = f"{name}.*{verb}|{verb}.*{name}"
                if re.search(pattern, text_lower):
                    characters_with_thoughts.add(entity.id)
                    suggestions['evidence'].append(f"'{entity.canonical_name}' + '{verb}'")

        if len(characters_with_thoughts) == 0:
            suggestions['suggested_type'] = FocalizationType.ZERO
            suggestions['confidence'] = 0.3
            suggestions['evidence'].append("Verbos de pensamiento sin sujeto claro identificado")
        elif len(characters_with_thoughts) == 1:
            suggestions['suggested_type'] = FocalizationType.INTERNAL_FIXED
            suggestions['suggested_focalizers'] = list(characters_with_thoughts)
            suggestions['confidence'] = 0.6
        else:
            suggestions['suggested_type'] = FocalizationType.INTERNAL_VARIABLE
            suggestions['suggested_focalizers'] = list(characters_with_thoughts)
            suggestions['confidence'] = 0.5

        return suggestions

    def generate_summary(self, project_id: int) -> str:
        """Genera resumen de focalización del proyecto."""
        declarations = self.get_all_declarations(project_id)

        if not declarations:
            return "No hay declaraciones de focalización registradas."

        lines = [
            "# Resumen de Focalización",
            "",
            f"Total de declaraciones: {len(declarations)}",
            "",
            "| Capítulo | Escena | Tipo | Focalizador(es) | Validado |",
            "|----------|--------|------|-----------------|----------|",
        ]

        for dec in sorted(declarations, key=lambda d: (d.chapter, d.scene or 0)):
            scene_str = str(dec.scene) if dec.scene else "-"
            focalizers = ", ".join(str(fid) for fid in dec.focalizer_ids) or "N/A"
            validated = "✓" if dec.is_validated else "✗"

            lines.append(
                f"| {dec.chapter} | {scene_str} | {dec.focalization_type.value} | "
                f"{focalizers} | {validated} |"
            )

        return "\n".join(lines)

import re  # Necesario para suggest_focalization
```

---

## Criterio de DONE

```python
from narrative_assistant.focalization import (
    FocalizationDeclarationService,
    FocalizationType
)

# Mock repository
class MockRepo:
    def __init__(self):
        self.focalizations = {}
        self.counter = 0

    def get_entity(self, eid):
        class E:
            entity_type = 'person'
        return E()

    def save_focalization(self, dec):
        self.counter += 1
        dec.id = self.counter
        self.focalizations[dec.id] = dec
        return dec

    def get_focalization(self, pid, ch, sc):
        for f in self.focalizations.values():
            if f.project_id == pid and f.chapter == ch and f.scene == sc:
                return f
        return None

    def get_all_focalizations(self, pid):
        return [f for f in self.focalizations.values() if f.project_id == pid]

service = FocalizationDeclarationService(MockRepo())

# Declarar focalización interna fija
dec1 = service.declare_focalization(
    project_id=1,
    chapter=1,
    focalization_type=FocalizationType.INTERNAL_FIXED,
    focalizer_ids=[1],  # Personaje con ID 1
    notes="Capítulo desde el punto de vista de Juan"
)

assert dec1.id == 1
assert dec1.focalization_type == FocalizationType.INTERNAL_FIXED
assert dec1.focalizer_ids == [1]

# Declarar focalización omnisciente
dec2 = service.declare_focalization(
    project_id=1,
    chapter=2,
    focalization_type=FocalizationType.ZERO,
    focalizer_ids=[]
)

# Obtener focalización
foc = service.get_focalization(project_id=1, chapter=1)
assert foc.focalization_type == FocalizationType.INTERNAL_FIXED

# Generar resumen
summary = service.generate_summary(project_id=1)
assert "INTERNAL_FIXED" in summary

print(f"✅ Sistema de declaración funcionando")
print(summary)
```

---

## Siguiente

[STEP 6.2: Violaciones de Focalización](./step-6.2-focalization-violations.md)
