# STEP 6.2: Detector de Violaciones de Focalización

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | L (6-8 horas) |
| **Prioridad** | P3 (Experimental) |
| **Prerequisitos** | STEP 6.1, STEP 2.1 |

---

## Descripción

Detectar cuando el texto viola la focalización declarada. Por ejemplo:
- Focalización interna en Juan, pero el texto describe los pensamientos de María
- Focalización externa, pero aparecen verbos de pensamiento
- Cambio de focalizador sin cambio de escena declarado

---

## Inputs

- Declaraciones de focalización (STEP 6.1)
- Texto procesado con entidades
- Verbos de percepción/pensamiento detectados

---

## Outputs

- `src/narrative_assistant/focalization/violations.py`
- Alertas de violación de focalización
- Contexto y explicación
- Sugerencias de corrección

---

## Tipos de Violaciones

| Tipo | Descripción | Severidad |
|------|-------------|-----------|
| `forbidden_mind_access` | Acceso a mente de personaje no declarado | Alta |
| `thought_in_external` | Pensamiento en focalización externa | Alta |
| `inconsistent_perception` | Percepción imposible para el focalizador | Media |
| `unmarked_focalizer_change` | Cambio de focalizador sin marca | Media |
| `omniscient_leak` | Información que el focalizador no puede saber | Media |

---

## Patrones de Detección

```python
# Verbos que implican acceso mental
MENTAL_ACCESS_VERBS = {
    # Pensamiento
    'pensar': ['pensó', 'pensaba', 'piensa', 'pensando'],
    'creer': ['creyó', 'creía', 'cree', 'creyendo'],
    'imaginar': ['imaginó', 'imaginaba', 'imagina'],
    'recordar': ['recordó', 'recordaba', 'recuerda'],
    'olvidar': ['olvidó', 'olvidaba', 'olvida'],
    'saber': ['sabía', 'supo', 'sabe'],
    'conocer': ['conocía', 'conoció', 'conoce'],

    # Emociones internas
    'sentir': ['sintió', 'sentía', 'siente'],
    'temer': ['temió', 'temía', 'teme'],
    'desear': ['deseó', 'deseaba', 'desea'],
    'esperar': ['esperó', 'esperaba', 'espera'],
    'querer': ['quiso', 'quería', 'quiere'],
    'odiar': ['odió', 'odiaba', 'odia'],
    'amar': ['amó', 'amaba', 'ama'],

    # Percepción interna
    'comprender': ['comprendió', 'comprendía', 'comprende'],
    'entender': ['entendió', 'entendía', 'entiende'],
    'darse cuenta': ['se dio cuenta', 'se daba cuenta'],
    'notar': ['notó', 'notaba', 'nota'],  # Puede ser externo también
}

# Patrones que indican acceso mental
MENTAL_ACCESS_PATTERNS = [
    r'(\w+)\s+(pensó|pensaba|creyó|creía|sabía|recordó|imaginó|sintió|sentía|temía|deseaba)',
    r'en\s+la\s+mente\s+de\s+(\w+)',
    r'(\w+)\s+se\s+pregunt[óa]',
    r'para\s+(\w+),?\s+(era|fue|parecía)\s+claro',
    r'(\w+)\s+no\s+podía\s+creer',
    r'(\w+)\s+se\s+dio\s+cuenta',
]
```

---

## Implementación

```python
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

class ViolationType(Enum):
    FORBIDDEN_MIND_ACCESS = "forbidden_mind_access"
    THOUGHT_IN_EXTERNAL = "thought_in_external"
    INCONSISTENT_PERCEPTION = "inconsistent_perception"
    UNMARKED_FOCALIZER_CHANGE = "unmarked_focalizer_change"
    OMNISCIENT_LEAK = "omniscient_leak"

class ViolationSeverity(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class FocalizationViolation:
    violation_type: ViolationType
    severity: ViolationSeverity

    chapter: int
    scene: Optional[int]
    position: int

    # Contexto
    text_excerpt: str
    entity_involved: Optional[int]  # ID de entidad que causa la violación
    entity_name: Optional[str]

    # Explicación
    explanation: str
    declared_focalizer: Optional[str]
    suggestion: str

    confidence: float

class FocalizationViolationDetector:
    def __init__(
        self,
        declaration_service: 'FocalizationDeclarationService',
        entities: List['Entity']
    ):
        self.declaration_service = declaration_service
        self.entities = {e.id: e for e in entities}
        self.entity_names = {}
        for e in entities:
            self.entity_names[e.canonical_name.lower()] = e.id
            for alias in getattr(e, 'aliases', []):
                self.entity_names[alias.lower()] = e.id

        # Compilar patrones
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compila patrones regex para detección."""
        self.mental_patterns = []
        for pattern in MENTAL_ACCESS_PATTERNS:
            self.mental_patterns.append(re.compile(pattern, re.IGNORECASE))

        # Todos los verbos de acceso mental
        self.mental_verbs = set()
        for verb_forms in MENTAL_ACCESS_VERBS.values():
            self.mental_verbs.update(v.lower() for v in verb_forms)

    def detect_violations(
        self,
        project_id: int,
        text: str,
        chapter: int,
        scene: Optional[int] = None
    ) -> List[FocalizationViolation]:
        """Detecta violaciones de focalización en un texto."""
        violations = []

        # Obtener declaración de focalización
        declaration = self.declaration_service.get_focalization(
            project_id, chapter, scene
        )

        if not declaration:
            # Sin declaración, no podemos detectar violaciones
            return []

        # Según el tipo de focalización, aplicar diferentes reglas
        if declaration.focalization_type == FocalizationType.EXTERNAL:
            violations.extend(self._check_external_violations(
                text, chapter, scene, declaration
            ))
        elif declaration.focalization_type == FocalizationType.INTERNAL_FIXED:
            violations.extend(self._check_internal_fixed_violations(
                text, chapter, scene, declaration
            ))
        elif declaration.focalization_type == FocalizationType.INTERNAL_VARIABLE:
            violations.extend(self._check_internal_variable_violations(
                text, chapter, scene, declaration
            ))
        # ZERO (omnisciente) no tiene violaciones por definición

        return violations

    def _check_external_violations(
        self,
        text: str,
        chapter: int,
        scene: Optional[int],
        declaration: 'FocalizationDeclaration'
    ) -> List[FocalizationViolation]:
        """Detecta pensamientos en focalización externa."""
        violations = []

        # Buscar cualquier acceso mental
        for pattern in self.mental_patterns:
            for match in pattern.finditer(text):
                # Verificar que es realmente un pensamiento
                context = text[max(0, match.start()-50):match.end()+50]

                violations.append(FocalizationViolation(
                    violation_type=ViolationType.THOUGHT_IN_EXTERNAL,
                    severity=ViolationSeverity.HIGH,
                    chapter=chapter,
                    scene=scene,
                    position=match.start(),
                    text_excerpt=match.group(0),
                    entity_involved=None,
                    entity_name=None,
                    explanation=(
                        "Focalización externa declarada pero se accede a pensamientos/emociones"
                    ),
                    declared_focalizer="Ninguno (externa)",
                    suggestion=(
                        "En focalización externa, solo se pueden describir acciones "
                        "observables, no pensamientos. Considere reformular o cambiar "
                        "la focalización."
                    ),
                    confidence=0.8
                ))

        return violations

    def _check_internal_fixed_violations(
        self,
        text: str,
        chapter: int,
        scene: Optional[int],
        declaration: 'FocalizationDeclaration'
    ) -> List[FocalizationViolation]:
        """Detecta acceso a mentes no permitidas en focalización interna fija."""
        violations = []

        if not declaration.focalizer_ids:
            return violations

        focalizer_id = declaration.focalizer_ids[0]
        focalizer_entity = self.entities.get(focalizer_id)
        focalizer_name = focalizer_entity.canonical_name if focalizer_entity else "?"
        focalizer_names_lower = {focalizer_name.lower()}
        if focalizer_entity and hasattr(focalizer_entity, 'aliases'):
            focalizer_names_lower.update(a.lower() for a in focalizer_entity.aliases)

        # Buscar acceso mental a otros personajes
        for pattern in self.mental_patterns:
            for match in pattern.finditer(text):
                # Extraer nombre del personaje (primer grupo de captura)
                groups = match.groups()
                if not groups:
                    continue

                character_name = groups[0].lower()

                # Si es el focalizador, está permitido
                if character_name in focalizer_names_lower:
                    continue

                # Si es otro personaje conocido, es violación
                if character_name in self.entity_names:
                    other_id = self.entity_names[character_name]
                    other_entity = self.entities.get(other_id)
                    other_name = other_entity.canonical_name if other_entity else character_name

                    violations.append(FocalizationViolation(
                        violation_type=ViolationType.FORBIDDEN_MIND_ACCESS,
                        severity=ViolationSeverity.HIGH,
                        chapter=chapter,
                        scene=scene,
                        position=match.start(),
                        text_excerpt=match.group(0),
                        entity_involved=other_id,
                        entity_name=other_name,
                        explanation=(
                            f"Acceso a los pensamientos de '{other_name}' cuando "
                            f"la focalización está en '{focalizer_name}'"
                        ),
                        declared_focalizer=focalizer_name,
                        suggestion=(
                            f"Solo podemos conocer los pensamientos de {focalizer_name}. "
                            f"Considere reformular como observación externa de {other_name} "
                            f"o mostrar lo que {focalizer_name} infiere de su comportamiento."
                        ),
                        confidence=0.85
                    ))

        return violations

    def _check_internal_variable_violations(
        self,
        text: str,
        chapter: int,
        scene: Optional[int],
        declaration: 'FocalizationDeclaration'
    ) -> List[FocalizationViolation]:
        """Detecta cambios no marcados de focalizador."""
        violations = []

        allowed_focalizers = set(declaration.focalizer_ids)
        allowed_names = set()
        for fid in allowed_focalizers:
            entity = self.entities.get(fid)
            if entity:
                allowed_names.add(entity.canonical_name.lower())
                for alias in getattr(entity, 'aliases', []):
                    allowed_names.add(alias.lower())

        # Rastrear qué focalizador está activo
        current_focalizer = None
        last_position = 0

        for pattern in self.mental_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                if not groups:
                    continue

                character_name = groups[0].lower()

                # Si no está en la lista de focalizadores permitidos
                if character_name not in allowed_names and character_name in self.entity_names:
                    violations.append(FocalizationViolation(
                        violation_type=ViolationType.FORBIDDEN_MIND_ACCESS,
                        severity=ViolationSeverity.HIGH,
                        chapter=chapter,
                        scene=scene,
                        position=match.start(),
                        text_excerpt=match.group(0),
                        entity_involved=self.entity_names.get(character_name),
                        entity_name=character_name.title(),
                        explanation=(
                            f"Acceso a mente de '{character_name}' que no está en la "
                            f"lista de focalizadores declarados"
                        ),
                        declared_focalizer=", ".join(
                            self.entities[fid].canonical_name
                            for fid in allowed_focalizers
                            if fid in self.entities
                        ),
                        suggestion=(
                            f"Añada '{character_name}' a la lista de focalizadores "
                            f"o reformule como observación externa."
                        ),
                        confidence=0.8
                    ))

        return violations

    def validate_chapter(
        self,
        project_id: int,
        chapter: int,
        text: str,
        scenes: Optional[List[Tuple[int, str]]] = None  # [(scene_num, text), ...]
    ) -> Dict[str, any]:
        """Valida un capítulo completo y devuelve resumen."""
        all_violations = []

        if scenes:
            for scene_num, scene_text in scenes:
                violations = self.detect_violations(
                    project_id, scene_text, chapter, scene_num
                )
                all_violations.extend(violations)
        else:
            all_violations = self.detect_violations(project_id, text, chapter)

        # Actualizar declaración con conteo
        declaration = self.declaration_service.get_focalization(project_id, chapter)
        if declaration:
            declaration.violations_count = len(all_violations)
            declaration.is_validated = True
            # self.declaration_service.repo.save_focalization(declaration)

        return {
            'chapter': chapter,
            'total_violations': len(all_violations),
            'by_type': self._count_by_type(all_violations),
            'by_severity': self._count_by_severity(all_violations),
            'violations': all_violations
        }

    def _count_by_type(
        self,
        violations: List[FocalizationViolation]
    ) -> Dict[str, int]:
        """Cuenta violaciones por tipo."""
        counts = {}
        for v in violations:
            key = v.violation_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_severity(
        self,
        violations: List[FocalizationViolation]
    ) -> Dict[str, int]:
        """Cuenta violaciones por severidad."""
        counts = {}
        for v in violations:
            key = v.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

# Importar tipos necesarios
from narrative_assistant.focalization.declaration import (
    FocalizationType,
    FocalizationDeclaration
)

# Constantes
MENTAL_ACCESS_VERBS = {
    'pensar': ['pensó', 'pensaba', 'piensa'],
    'creer': ['creyó', 'creía', 'cree'],
    'sentir': ['sintió', 'sentía', 'siente'],
    'saber': ['sabía', 'supo', 'sabe'],
    'recordar': ['recordó', 'recordaba', 'recuerda'],
    'temer': ['temió', 'temía', 'teme'],
}

MENTAL_ACCESS_PATTERNS = [
    r'(\w+)\s+(pensó|pensaba|creyó|creía|sabía|recordó|sintió|sentía|temía)',
    r'(\w+)\s+se\s+pregunt[óa]',
    r'para\s+(\w+),?\s+(era|fue)\s+claro',
]
```

---

## Criterio de DONE

```python
from narrative_assistant.focalization import (
    FocalizationDeclarationService,
    FocalizationViolationDetector,
    FocalizationType,
    ViolationType
)

# Setup con mocks
class MockEntity:
    def __init__(self, id, name, aliases=None):
        self.id = id
        self.canonical_name = name
        self.aliases = aliases or []
        self.entity_type = 'person'

entities = [
    MockEntity(1, "Juan"),
    MockEntity(2, "María"),
    MockEntity(3, "Pedro"),
]

# Mock de declaration service
class MockDeclarationService:
    def __init__(self, declaration):
        self.declaration = declaration

    def get_focalization(self, pid, ch, sc=None):
        return self.declaration

# Declaración: focalización interna fija en Juan
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MockDeclaration:
    id = 1
    project_id = 1
    chapter = 1
    scene = None
    focalization_type = FocalizationType.INTERNAL_FIXED
    focalizer_ids = [1]  # Juan
    declared_at = datetime.now()
    declared_by = 'user'
    notes = ""
    is_validated = False
    violations_count = 0

declaration_service = MockDeclarationService(MockDeclaration())
detector = FocalizationViolationDetector(declaration_service, entities)

# Texto con violación: acceso a mente de María
text = """
Juan caminaba por la calle pensando en sus problemas.
María lo vio pasar y sintió una punzada de tristeza.
Ella sabía que algo andaba mal.
"""

violations = detector.detect_violations(
    project_id=1,
    text=text,
    chapter=1
)

# Debe detectar violación: acceso a mente de María
assert len(violations) >= 1
maria_violations = [v for v in violations if v.entity_name and "María" in v.entity_name]
assert len(maria_violations) >= 1
assert maria_violations[0].violation_type == ViolationType.FORBIDDEN_MIND_ACCESS

print(f"✅ Detectadas {len(violations)} violaciones")
for v in violations:
    print(f"  [{v.severity.value}] {v.explanation}")
    print(f"    Sugerencia: {v.suggestion[:80]}...")
```

---

## Siguiente

[STEP 7.1: Motor de Alertas](../phase-7/step-7.1-alert-engine.md)
