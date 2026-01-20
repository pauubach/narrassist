"""
Detector de violaciones de focalizacion.

Detecta cuando el texto viola la focalizacion declarada:
- Acceso a mente de personaje no declarado
- Pensamientos en focalizacion externa
- Cambios de focalizador sin marca
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any, Set

from .declaration import (
    FocalizationType,
    FocalizationDeclaration,
    FocalizationDeclarationService,
)

logger = logging.getLogger(__name__)


# Verbos que implican acceso mental
MENTAL_ACCESS_VERBS = {
    # Pensamiento
    'pensar': ['penso', 'pensaba', 'piensa', 'pensando'],
    'creer': ['creyo', 'creia', 'cree', 'creyendo'],
    'imaginar': ['imagino', 'imaginaba', 'imagina'],
    'recordar': ['recordo', 'recordaba', 'recuerda'],
    'olvidar': ['olvido', 'olvidaba', 'olvida'],
    'saber': ['sabia', 'supo', 'sabe'],
    'conocer': ['conocia', 'conocio', 'conoce'],
    # Emociones internas
    'sentir': ['sintio', 'sentia', 'siente'],
    'temer': ['temio', 'temia', 'teme'],
    'desear': ['deseo', 'deseaba', 'desea'],
    'esperar': ['espero', 'esperaba', 'espera'],
    'querer': ['quiso', 'queria', 'quiere'],
    'odiar': ['odio', 'odiaba', 'odia'],
    'amar': ['amo', 'amaba', 'ama'],
    # Percepcion interna
    'comprender': ['comprendio', 'comprendia', 'comprende'],
    'entender': ['entendio', 'entendia', 'entiende'],
    'notar': ['noto', 'notaba', 'nota'],
}

# Patrones que indican acceso mental
MENTAL_ACCESS_PATTERNS = [
    r'(\w+)\s+(penso|pensaba|creyo|creia|sabia|recordo|imagino|sintio|sentia|temia|deseaba)',
    r'en\s+la\s+mente\s+de\s+(\w+)',
    r'(\w+)\s+se\s+pregunt[oa]',
    r'para\s+(\w+),?\s+(era|fue|parecia)\s+claro',
    r'(\w+)\s+no\s+podia\s+creer',
    r'(\w+)\s+se\s+dio\s+cuenta',
]


class ViolationType(Enum):
    """Tipos de violacion de focalizacion."""
    FORBIDDEN_MIND_ACCESS = "forbidden_mind_access"  # Acceso a mente no permitida
    THOUGHT_IN_EXTERNAL = "thought_in_external"  # Pensamiento en focalizacion externa
    INCONSISTENT_PERCEPTION = "inconsistent_perception"  # Percepcion imposible
    UNMARKED_FOCALIZER_CHANGE = "unmarked_focalizer_change"  # Cambio sin marca
    OMNISCIENT_LEAK = "omniscient_leak"  # Informacion que no puede saber


class ViolationSeverity(Enum):
    """Severidad de la violacion."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class FocalizationViolation:
    """Una violacion de focalizacion detectada."""

    violation_type: ViolationType
    severity: ViolationSeverity

    chapter: int
    scene: Optional[int]
    position: int

    # Contexto
    text_excerpt: str
    entity_involved: Optional[int] = None  # ID de entidad que causa la violacion
    entity_name: Optional[str] = None

    # Explicacion
    explanation: str = ""
    declared_focalizer: Optional[str] = None
    suggestion: str = ""

    confidence: float = 0.5

    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        return {
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "chapter": self.chapter,
            "scene": self.scene,
            "position": self.position,
            "text_excerpt": self.text_excerpt[:200] if self.text_excerpt else "",
            "entity_involved": self.entity_involved,
            "entity_name": self.entity_name,
            "explanation": self.explanation,
            "declared_focalizer": self.declared_focalizer,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
        }


class FocalizationViolationDetector:
    """Detector de violaciones de focalizacion."""

    def __init__(
        self,
        declaration_service: FocalizationDeclarationService,
        entities: List[Any]
    ):
        """
        Inicializa el detector.

        Args:
            declaration_service: Servicio de declaraciones de focalizacion
            entities: Lista de entidades del proyecto
        """
        self.declaration_service = declaration_service
        self.entities: Dict[int, Any] = {}
        self.entity_names: Dict[str, int] = {}

        for e in entities:
            entity_id = getattr(e, 'id', None)
            if entity_id:
                self.entities[entity_id] = e
                name = getattr(e, 'canonical_name', getattr(e, 'name', '')).lower()
                self.entity_names[name] = entity_id
                # Tambien agregar aliases
                aliases = getattr(e, 'aliases', [])
                for alias in aliases:
                    self.entity_names[alias.lower()] = entity_id

        # Compilar patrones
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compila patrones regex para deteccion."""
        self.mental_patterns = []
        for pattern in MENTAL_ACCESS_PATTERNS:
            self.mental_patterns.append(re.compile(pattern, re.IGNORECASE))

        # Todos los verbos de acceso mental
        self.mental_verbs: Set[str] = set()
        for verb_forms in MENTAL_ACCESS_VERBS.values():
            self.mental_verbs.update(v.lower() for v in verb_forms)

    def detect_violations(
        self,
        project_id: int,
        text: str,
        chapter: int,
        scene: Optional[int] = None
    ) -> List[FocalizationViolation]:
        """
        Detecta violaciones de focalizacion en un texto.

        Args:
            project_id: ID del proyecto
            text: Texto a analizar
            chapter: Numero de capitulo
            scene: Numero de escena (opcional)

        Returns:
            Lista de violaciones detectadas
        """
        violations = []

        # Obtener declaracion de focalizacion
        declaration = self.declaration_service.get_focalization(
            project_id, chapter, scene
        )

        if not declaration:
            # Sin declaracion, no podemos detectar violaciones
            logger.debug(f"No focalization declaration for chapter {chapter}")
            return []

        # Segun el tipo de focalizacion, aplicar diferentes reglas
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
        # ZERO (omnisciente) no tiene violaciones por definicion

        logger.info(f"Detected {len(violations)} focalization violations in chapter {chapter}")
        return violations

    def _check_external_violations(
        self,
        text: str,
        chapter: int,
        scene: Optional[int],
        declaration: FocalizationDeclaration
    ) -> List[FocalizationViolation]:
        """Detecta pensamientos en focalizacion externa."""
        violations = []

        # Buscar cualquier acceso mental
        for pattern in self.mental_patterns:
            for match in pattern.finditer(text):
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
                        "Focalizacion externa declarada pero se accede a pensamientos/emociones"
                    ),
                    declared_focalizer="Ninguno (externa)",
                    suggestion=(
                        "En focalizacion externa, solo se pueden describir acciones "
                        "observables, no pensamientos. Considere reformular o cambiar "
                        "la focalizacion."
                    ),
                    confidence=0.8
                ))

        return violations

    def _check_internal_fixed_violations(
        self,
        text: str,
        chapter: int,
        scene: Optional[int],
        declaration: FocalizationDeclaration
    ) -> List[FocalizationViolation]:
        """Detecta acceso a mentes no permitidas en focalizacion interna fija."""
        violations = []

        if not declaration.focalizer_ids:
            return violations

        focalizer_id = declaration.focalizer_ids[0]
        focalizer_entity = self.entities.get(focalizer_id)
        focalizer_name = "?"
        if focalizer_entity:
            focalizer_name = getattr(
                focalizer_entity, 'canonical_name',
                getattr(focalizer_entity, 'name', '?')
            )

        focalizer_names_lower: Set[str] = {focalizer_name.lower()}
        if focalizer_entity:
            aliases = getattr(focalizer_entity, 'aliases', [])
            focalizer_names_lower.update(a.lower() for a in aliases)

        # Buscar acceso mental a otros personajes
        for pattern in self.mental_patterns:
            for match in pattern.finditer(text):
                # Extraer nombre del personaje (primer grupo de captura)
                groups = match.groups()
                if not groups:
                    continue

                character_name = groups[0].lower()

                # Si es el focalizador, esta permitido
                if character_name in focalizer_names_lower:
                    continue

                # Si es otro personaje conocido, es violacion
                if character_name in self.entity_names:
                    other_id = self.entity_names[character_name]
                    other_entity = self.entities.get(other_id)
                    other_name = character_name.title()
                    if other_entity:
                        other_name = getattr(
                            other_entity, 'canonical_name',
                            getattr(other_entity, 'name', character_name.title())
                        )

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
                            f"la focalizacion esta en '{focalizer_name}'"
                        ),
                        declared_focalizer=focalizer_name,
                        suggestion=(
                            f"Solo podemos conocer los pensamientos de {focalizer_name}. "
                            f"Considere reformular como observacion externa de {other_name} "
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
        declaration: FocalizationDeclaration
    ) -> List[FocalizationViolation]:
        """Detecta cambios no marcados de focalizador."""
        violations = []

        allowed_focalizers = set(declaration.focalizer_ids)
        allowed_names: Set[str] = set()

        for fid in allowed_focalizers:
            entity = self.entities.get(fid)
            if entity:
                name = getattr(entity, 'canonical_name', getattr(entity, 'name', ''))
                allowed_names.add(name.lower())
                aliases = getattr(entity, 'aliases', [])
                for alias in aliases:
                    allowed_names.add(alias.lower())

        for pattern in self.mental_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                if not groups:
                    continue

                character_name = groups[0].lower()

                # Si no esta en la lista de focalizadores permitidos
                if character_name not in allowed_names and character_name in self.entity_names:
                    other_id = self.entity_names.get(character_name)

                    # Construir nombres de focalizadores declarados
                    declared_names = []
                    for fid in allowed_focalizers:
                        entity = self.entities.get(fid)
                        if entity:
                            declared_names.append(getattr(
                                entity, 'canonical_name',
                                getattr(entity, 'name', str(fid))
                            ))

                    violations.append(FocalizationViolation(
                        violation_type=ViolationType.FORBIDDEN_MIND_ACCESS,
                        severity=ViolationSeverity.HIGH,
                        chapter=chapter,
                        scene=scene,
                        position=match.start(),
                        text_excerpt=match.group(0),
                        entity_involved=other_id,
                        entity_name=character_name.title(),
                        explanation=(
                            f"Acceso a mente de '{character_name}' que no esta en la "
                            f"lista de focalizadores declarados"
                        ),
                        declared_focalizer=", ".join(declared_names),
                        suggestion=(
                            f"Anada '{character_name}' a la lista de focalizadores "
                            f"o reformule como observacion externa."
                        ),
                        confidence=0.8
                    ))

        return violations

    def validate_chapter(
        self,
        project_id: int,
        chapter: int,
        text: str,
        scenes: Optional[List[tuple]] = None  # [(scene_num, text), ...]
    ) -> Dict[str, Any]:
        """
        Valida un capitulo completo y devuelve resumen.

        Args:
            project_id: ID del proyecto
            chapter: Numero de capitulo
            text: Texto del capitulo
            scenes: Lista de escenas (opcional)

        Returns:
            Diccionario con resumen de validacion
        """
        all_violations = []

        if scenes:
            for scene_num, scene_text in scenes:
                violations = self.detect_violations(
                    project_id, scene_text, chapter, scene_num
                )
                all_violations.extend(violations)
        else:
            all_violations = self.detect_violations(project_id, text, chapter)

        # Actualizar declaracion con conteo
        declaration = self.declaration_service.get_focalization(project_id, chapter)
        if declaration:
            declaration.violations_count = len(all_violations)
            declaration.is_validated = True

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
        counts: Dict[str, int] = {}
        for v in violations:
            key = v.violation_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_severity(
        self,
        violations: List[FocalizationViolation]
    ) -> Dict[str, int]:
        """Cuenta violaciones por severidad."""
        counts: Dict[str, int] = {}
        for v in violations:
            key = v.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts


def detect_focalization_violations(
    chapters: List[Dict],
    entities: List[Any],
    declarations: List[Dict],
) -> tuple:
    """
    Funcion de conveniencia para detectar violaciones de focalizacion.

    Args:
        chapters: Lista de capitulos con contenido
        entities: Lista de entidades del proyecto
        declarations: Lista de declaraciones de focalizacion

    Returns:
        Tupla de (servicio, lista de violaciones)
    """
    # Crear servicio con declaraciones
    service = FocalizationDeclarationService()

    # Cargar declaraciones
    for dec in declarations:
        foc_type = dec.get("focalization_type")
        if isinstance(foc_type, str):
            foc_type = FocalizationType(foc_type)
        elif foc_type is None:
            foc_type = FocalizationType.ZERO

        service.declare_focalization(
            project_id=dec.get("project_id", 1),
            chapter=dec.get("chapter", 1),
            focalization_type=foc_type,
            focalizer_ids=dec.get("focalizer_ids", []),
            scene=dec.get("scene"),
            notes=dec.get("notes", ""),
        )

    # Crear detector
    detector = FocalizationViolationDetector(service, entities)

    # Detectar violaciones
    all_violations = []
    for chapter in chapters:
        chapter_num = chapter.get("number", 1)
        content = chapter.get("content", "")
        project_id = chapter.get("project_id", 1)

        violations = detector.detect_violations(project_id, content, chapter_num)
        all_violations.extend(violations)

    return service, all_violations
