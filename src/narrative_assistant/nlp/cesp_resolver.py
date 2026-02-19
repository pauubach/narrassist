"""
CESP: Cascading Extraction with Syntactic Priority
===================================================

Arquitectura de extracción de atributos en cascada con prioridad sintáctica.
Combina múltiples extractores y resuelve conflictos usando evidencia sintáctica
como criterio principal.

Esta arquitectura fue diseñada por un panel de expertos en NLP para resolver
el problema de asignación incorrecta de atributos (ej: "ojos azules de Pedro"
asignados a Juan por proximidad).

Principios clave:
1. Los extractores regex/embeddings DETECTAN pero NO ASIGNAN
2. Solo DependencyExtractor asigna usando evidencia sintáctica
3. LLM es árbitro para conflictos, no extractor principal
4. Deduplicación elimina falsos positivos

Autor: Narrative Assistant (basado en diseño del panel de expertos)
Versión: 1.0.0
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Protocol,
)

# Configuración del logger
logger = logging.getLogger("cesp")


# =============================================================================
# ENUMERACIONES Y CONSTANTES
# =============================================================================


class ExtractorType(Enum):
    """Tipos de extractores disponibles en el sistema."""

    DEPENDENCY = auto()  # Extractor basado en dependencias sintácticas
    REGEX = auto()  # Extractor basado en expresiones regulares
    EMBEDDINGS = auto()  # Extractor basado en embeddings semánticos
    LLM = auto()  # Extractor basado en LLM


class ConflictStatus(Enum):
    """Estado de conflicto de una extracción."""

    CONFIRMED = "confirmed"  # Sintaxis clara, directo a salida
    UNANIMOUS = "unanimous"  # Todos los extractores coinciden
    CONFLICT = "conflict"  # Hay desacuerdo, requiere arbitraje


class AssignmentSource(Enum):
    """Fuente de la asignación de un atributo a una entidad."""

    EXPLICIT_SUBJECT = "nsubj"  # Sujeto explícito (nsubj)
    GENITIVE = "genitive"  # Genitivo "de X"
    IMPLICIT_SUBJECT = "inherited"  # Sujeto tácito heredado
    PROXIMITY = "proximity"  # Asignación por proximidad
    LLM_ARBITRATION = "llm_arbitration"  # Decidido por LLM


# Constantes de confianza base
CONFIDENCE_EXPLICIT_SUBJECT = 0.92
CONFIDENCE_GENITIVE = 0.92  # "ojos azules de Pedro"
CONFIDENCE_IMPLICIT_SUBJECT = 0.78
CONFIDENCE_PROXIMITY_MIN = 0.55
CONFIDENCE_PROXIMITY_MAX = 0.70
CONFIDENCE_LLM_ARBITRATION = 0.82
UNANIMOUS_BOOST = 0.10
DEDUPLICATION_THRESHOLD = 0.15


# =============================================================================
# ESTRUCTURAS DE DATOS
# =============================================================================


@dataclass(frozen=True)
class EntityMention:
    """
    Representa una mención de entidad en el texto.

    Attributes:
        entity_id: Identificador único de la entidad
        text: Texto de la mención
        start: Posición inicial en el texto
        end: Posición final en el texto
        sentence_idx: Índice de la oración donde aparece
        entity_type: Tipo de entidad (PERSON, LOCATION, etc.)
    """

    entity_id: str
    text: str
    start: int
    end: int
    sentence_idx: int
    entity_type: str = "PERSON"


@dataclass
class AttributeCandidate:
    """
    Candidato de atributo extraído por un extractor.

    Attributes:
        attribute_type: Tipo de atributo (color_ojos, edad, profesion, etc.)
        value: Valor del atributo
        text_evidence: Fragmento de texto que evidencia el atributo
        sentence_idx: Índice de la oración origen
        start: Posición inicial en el texto
        end: Posición final en el texto
        extractor_type: Tipo de extractor que lo detectó
        assigned_entity_id: ID de entidad asignada (puede ser None)
        assignment_source: Fuente de la asignación
        base_confidence: Confianza base del extractor
        syntactic_evidence: Evidencia sintáctica (relación de dependencia)
        is_dubious: Marca si la asignación es dudosa
        metadata: Metadatos adicionales
    """

    attribute_type: str
    value: str
    text_evidence: str
    sentence_idx: int
    start: int
    end: int
    extractor_type: ExtractorType
    assigned_entity_id: str | None = None
    assignment_source: AssignmentSource | None = None
    base_confidence: float = 0.5
    syntactic_evidence: str | None = None
    is_dubious: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def unique_key(self) -> tuple[str, str, int]:
        """Clave única para deduplicación: (tipo, valor, oración)."""
        return (self.attribute_type, self.value.lower().strip(), self.sentence_idx)

    @property
    def fingerprint(self) -> str:
        """Huella digital del candidato para comparaciones."""
        key_str = f"{self.attribute_type}:{self.value}:{self.sentence_idx}"
        return hashlib.md5(key_str.encode()).hexdigest()[:8]


@dataclass
class ResolvedAttribute:
    """
    Atributo final resuelto y asignado.

    Attributes:
        attribute_type: Tipo de atributo
        value: Valor del atributo
        entity_id: ID de la entidad a la que se asigna
        final_confidence: Confianza final después de resolución
        conflict_status: Estado de conflicto original
        assignment_source: Fuente de la asignación
        is_dubious: Si la asignación tiene incertidumbre
        contributing_extractors: Extractores que contribuyeron
        text_evidence: Evidencia textual
        sentence_idx: Índice de oración origen
        resolution_notes: Notas del proceso de resolución
    """

    attribute_type: str
    value: str
    entity_id: str
    final_confidence: float
    conflict_status: ConflictStatus
    assignment_source: AssignmentSource
    is_dubious: bool = False
    contributing_extractors: frozenset[ExtractorType] = field(default_factory=frozenset)
    text_evidence: str = ""
    sentence_idx: int = 0
    resolution_notes: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Resultado de un extractor individual."""

    extractor_type: ExtractorType
    candidates: list[AttributeCandidate]
    processing_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


# =============================================================================
# INTERFACES / PROTOCOLOS
# =============================================================================


class BaseExtractor(ABC):
    """Interfaz base para todos los extractores."""

    @property
    @abstractmethod
    def extractor_type(self) -> ExtractorType:
        """Retorna el tipo de extractor."""
        pass

    @abstractmethod
    def extract(self, text: str, entity_mentions: list[EntityMention]) -> list[AttributeCandidate]:
        """
        Extrae candidatos de atributos del texto.

        Args:
            text: Texto completo a analizar
            entity_mentions: Lista de menciones de entidades detectadas

        Returns:
            Lista de candidatos de atributos
        """
        pass


class LLMProvider(Protocol):
    """Protocolo para proveedores de LLM."""

    def query(self, prompt: str, context: str, options: list[str] | None = None) -> str | None:
        """
        Consulta al LLM con una pregunta específica.

        Args:
            prompt: Pregunta a realizar
            context: Contexto relevante
            options: Opciones válidas de respuesta

        Returns:
            Respuesta del LLM o None si no disponible
        """
        ...

    def is_available(self) -> bool:
        """Verifica si el LLM está disponible."""
        ...


# =============================================================================
# RESOLUCIÓN DE CONFLICTOS
# =============================================================================


class ConflictResolver:
    """
    Resuelve conflictos entre candidatos de diferentes extractores.

    Implementa la lógica de:
    - confirmed: sintaxis clara → directo a salida
    - unanimous: todos coinciden → boost +10%
    - conflict: LLM como árbitro
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        """
        Inicializa el resolutor de conflictos.

        Args:
            llm_provider: Proveedor de LLM para arbitraje (opcional)
        """
        self._llm = llm_provider

    def classify_conflict_status(self, candidates: list[AttributeCandidate]) -> ConflictStatus:
        """
        Clasifica el estado de conflicto de un grupo de candidatos.

        Args:
            candidates: Candidatos que refieren al mismo atributo

        Returns:
            Estado de conflicto
        """
        if not candidates:
            return ConflictStatus.CONFLICT

        # Verificar si hay evidencia sintáctica clara
        syntactic_candidates = [
            c
            for c in candidates
            if c.extractor_type == ExtractorType.DEPENDENCY
            and c.assignment_source
            in (AssignmentSource.EXPLICIT_SUBJECT, AssignmentSource.GENITIVE)
        ]

        if syntactic_candidates:
            logger.debug("[ConflictResolver] CONFIRMED - evidencia sintáctica clara")
            return ConflictStatus.CONFIRMED

        # Verificar unanimidad
        assigned_entities = {
            c.assigned_entity_id for c in candidates if c.assigned_entity_id is not None
        }

        if len(assigned_entities) == 1:
            logger.debug("[ConflictResolver] UNANIMOUS - todos coinciden")
            return ConflictStatus.UNANIMOUS

        logger.debug("[ConflictResolver] CONFLICT - desacuerdo entre extractores")
        return ConflictStatus.CONFLICT

    def resolve(
        self, candidates: list[AttributeCandidate], entity_mentions: list[EntityMention], text: str
    ) -> tuple[str, float, AssignmentSource, list[str]] | None:
        """
        Resuelve el conflicto y determina la asignación final.

        Args:
            candidates: Candidatos en conflicto
            entity_mentions: Menciones de entidades disponibles
            text: Texto original para contexto

        Returns:
            Tupla (entity_id, confidence, source, notes) o None
        """
        status = self.classify_conflict_status(candidates)
        notes: list[str] = []

        if status == ConflictStatus.CONFIRMED:
            # Usar el candidato con evidencia sintáctica
            best = self._get_best_syntactic_candidate(candidates)
            notes.append(f"Resuelto por evidencia sintáctica: {best.syntactic_evidence}")
            return (best.assigned_entity_id, best.base_confidence, best.assignment_source, notes)  # type: ignore[return-value]

        elif status == ConflictStatus.UNANIMOUS:
            # Boost de confianza por unanimidad
            best = max(candidates, key=lambda c: c.base_confidence)
            boosted_confidence = min(1.0, best.base_confidence + UNANIMOUS_BOOST)
            notes.append(
                f"Boost por unanimidad: {best.base_confidence:.2f} → {boosted_confidence:.2f}"
            )
            return (  # type: ignore[return-value]
                best.assigned_entity_id,
                boosted_confidence,
                best.assignment_source or AssignmentSource.PROXIMITY,
                notes,
            )

        else:  # CONFLICT
            return self._resolve_conflict_with_arbitration(candidates, entity_mentions, text, notes)

    def _get_best_syntactic_candidate(
        self, candidates: list[AttributeCandidate]
    ) -> AttributeCandidate:
        """Obtiene el mejor candidato con evidencia sintáctica."""
        syntactic = [
            c
            for c in candidates
            if c.extractor_type == ExtractorType.DEPENDENCY
            and c.assignment_source
            in (AssignmentSource.EXPLICIT_SUBJECT, AssignmentSource.GENITIVE)
        ]
        return max(syntactic, key=lambda c: c.base_confidence)

    def _resolve_conflict_with_arbitration(
        self,
        candidates: list[AttributeCandidate],
        entity_mentions: list[EntityMention],
        text: str,
        notes: list[str],
    ) -> tuple[str, float, AssignmentSource, list[str]] | None:
        """
        Resuelve conflicto usando LLM o fallback heurístico.
        """
        # Intentar arbitraje con LLM
        if self._llm and self._llm.is_available():
            result = self._llm_arbitration(candidates, entity_mentions, text)
            if result:
                entity_id, confidence = result
                notes.append("Resuelto por arbitraje LLM")
                return (entity_id, confidence, AssignmentSource.LLM_ARBITRATION, notes)
        else:
            notes.append("LLM no disponible, usando fallback heurístico")

        # Fallback: priorizar candidatos con evidencia más fuerte
        return self._heuristic_fallback(candidates, entity_mentions, notes)

    def _llm_arbitration(
        self, candidates: list[AttributeCandidate], entity_mentions: list[EntityMention], text: str
    ) -> tuple[str, float] | None:
        """
        Usa LLM para arbitrar el conflicto.

        Genera una pregunta específica y concisa para el LLM.
        """
        if not candidates:
            return None

        # Construir pregunta específica
        attr_type = candidates[0].attribute_type
        attr_value = candidates[0].value

        entity_names = [e.text for e in entity_mentions]
        context = candidates[0].text_evidence

        prompt = (
            f"En el siguiente texto, ¿a qué personaje pertenece el atributo "
            f"'{attr_type}' con valor '{attr_value}'?\n\n"
            f'Texto: "{context}"\n\n'
            f"Opciones: {', '.join(entity_names)}\n\n"
            f"Responde SOLO con el nombre del personaje."
        )

        logger.debug(f"[LLM Arbitration] Prompt: {prompt[:100]}...")

        response = self._llm.query(prompt=prompt, context=context, options=entity_names)  # type: ignore[union-attr]

        if response:
            # Buscar la entidad mencionada en la respuesta
            response_lower = response.lower().strip()
            for entity in entity_mentions:
                if entity.text.lower() in response_lower:
                    logger.info(f"[LLM Arbitration] Resultado: {entity.entity_id}")
                    return (entity.entity_id, CONFIDENCE_LLM_ARBITRATION)

        return None

    def _heuristic_fallback(
        self,
        candidates: list[AttributeCandidate],
        entity_mentions: list[EntityMention],
        notes: list[str],
    ) -> tuple[str, float, AssignmentSource, list[str]] | None:
        """
        Fallback heurístico cuando no hay LLM.

        Prioriza:
        1. Candidatos con evidencia sintáctica parcial
        2. Candidatos del DependencyExtractor
        3. Mayor confianza base
        """
        if not candidates:
            notes.append("No hay candidatos para asignar")
            return None

        # Ordenar por prioridad
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (
                c.extractor_type == ExtractorType.DEPENDENCY,
                c.assignment_source == AssignmentSource.IMPLICIT_SUBJECT,
                c.base_confidence,
            ),
            reverse=True,
        )

        best = sorted_candidates[0]

        if best.assigned_entity_id:
            notes.append(f"Fallback heurístico: mejor candidato de {best.extractor_type.name}")
            return (
                best.assigned_entity_id,
                best.base_confidence * 0.9,  # Penalizar ligeramente por incertidumbre
                best.assignment_source or AssignmentSource.PROXIMITY,
                notes,
            )

        notes.append("No se encontró candidato válido")
        return None


# =============================================================================
# DEDUPLICADOR
# =============================================================================


class AttributeDeduplicator:
    """
    Deduplica atributos resueltos agrupando por clave única.

    Criterios:
    - Agrupa por (tipo_atributo, valor, oración_origen, entidad)
    - Prioriza mayor confianza
    - Elimina duplicados con diferencia > threshold

    IMPORTANTE: Esta es la clave para eliminar falsos positivos como
    asignar "ojos azules de Pedro" tanto a Pedro como a Juan.
    """

    def __init__(self, confidence_threshold: float = DEDUPLICATION_THRESHOLD):
        """
        Inicializa el deduplicador.

        Args:
            confidence_threshold: Diferencia mínima para considerar duplicado
        """
        self._threshold = confidence_threshold

    def deduplicate(self, attributes: list[ResolvedAttribute]) -> list[ResolvedAttribute]:
        """
        Deduplica lista de atributos resueltos.

        Estrategia principal para eliminar falsos positivos:
        Si el mismo atributo (tipo+valor+oración) está asignado a
        múltiples entidades, conservar SOLO el de mayor confianza.

        Args:
            attributes: Lista de atributos a deduplicar

        Returns:
            Lista deduplicada
        """
        if not attributes:
            return []

        # PASO 1: Agrupar por (tipo, valor, oración) SIN considerar entidad
        # Esto detecta duplicados donde el mismo atributo fue asignado a múltiples entidades
        attr_groups: dict[tuple[str, str, int], list[ResolvedAttribute]] = defaultdict(list)

        for attr in attributes:
            key = (attr.attribute_type, attr.value.lower().strip(), attr.sentence_idx)
            attr_groups[key].append(attr)

        logger.debug(
            f"[Deduplicator] {len(attributes)} atributos → {len(attr_groups)} grupos únicos"
        )

        deduplicated: list[ResolvedAttribute] = []

        for key, group in attr_groups.items():
            attr_type, value, sent_idx = key

            if len(group) == 1:
                # Solo un candidato, conservar
                deduplicated.append(group[0])
            else:
                # MÚLTIPLES candidatos para el mismo atributo
                # Esto es el caso "ojos azules de Pedro" asignado a Pedro Y Juan

                # Ordenar por:
                # 1. Prioridad de fuente de asignación (genitivo/nsubj > proximity)
                # 2. Confianza
                sorted_group = sorted(
                    group,
                    key=lambda a: (self._source_priority(a.assignment_source), a.final_confidence),
                    reverse=True,
                )

                best = sorted_group[0]

                # Log de eliminación de falsos positivos
                eliminated = list(sorted_group[1:])
                for elim in eliminated:
                    if elim.entity_id != best.entity_id:
                        logger.info(
                            f"[Deduplicator] ELIMINANDO FALSO POSITIVO: "
                            f"{attr_type}='{value}' asignado a {elim.entity_id} "
                            f"(correcto: {best.entity_id}, source={best.assignment_source.value})"
                        )

                # Añadir nota sobre deduplicación
                best.resolution_notes.append(
                    f"Deduplicado: {len(eliminated)} candidatos eliminados"
                )

                deduplicated.append(best)

        return deduplicated

    def _source_priority(self, source: AssignmentSource) -> int:
        """
        Devuelve prioridad numérica para la fuente de asignación.

        Mayor número = mayor prioridad.
        """
        priorities = {
            AssignmentSource.GENITIVE: 100,  # "de Pedro" - más confiable
            AssignmentSource.EXPLICIT_SUBJECT: 90,  # nsubj explícito
            AssignmentSource.LLM_ARBITRATION: 80,  # LLM decidió
            AssignmentSource.IMPLICIT_SUBJECT: 50,  # sujeto tácito
            AssignmentSource.PROXIMITY: 10,  # menos confiable
        }
        return priorities.get(source, 0)


# =============================================================================
# ORQUESTADOR PRINCIPAL: CESPAttributeResolver
# =============================================================================


class CESPAttributeResolver:
    """
    Resolutor de atributos CESP (Cascading Extraction with Syntactic Priority).

    Orquesta el flujo completo de:
    1. Detección (múltiples extractores)
    2. Asignación con prioridad sintáctica
    3. Resolución de conflictos
    4. Deduplicación final (CLAVE para eliminar falsos positivos)

    Ejemplo de uso:
    ```python
    resolver = CESPAttributeResolver(llm_provider=ollama_provider)

    results = resolver.resolve(
        candidates=all_candidates,  # De todos los extractores
        entity_mentions=[EntityMention(entity_id="pedro_1", text="Pedro", ...)],
        text="Pedro tiene los ojos azules. Juan lo mira."
    )

    for attr in results:
        print(f"{attr.entity_id}: {attr.attribute_type}={attr.value} "
              f"(conf={attr.final_confidence:.2f})")
    ```
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        confidence_threshold: float = DEDUPLICATION_THRESHOLD,
    ):
        """
        Inicializa el resolutor CESP.

        Args:
            llm_provider: Proveedor de LLM para arbitraje (opcional)
            confidence_threshold: Umbral para deduplicación
        """
        self._llm = llm_provider
        self._conflict_resolver = ConflictResolver(llm_provider)
        self._deduplicator = AttributeDeduplicator(confidence_threshold)

        logger.info(f"[CESP] Inicializado, LLM={'disponible' if llm_provider else 'no disponible'}")

    def resolve(
        self, candidates: list[AttributeCandidate], entity_mentions: list[EntityMention], text: str
    ) -> list[ResolvedAttribute]:
        """
        Resuelve atributos y los asigna a entidades.

        Ejecuta el pipeline CESP:
        1. Agrupa candidatos por atributo
        2. Resuelve conflictos
        3. Deduplica eliminando falsos positivos

        Args:
            candidates: Candidatos de todos los extractores
            entity_mentions: Menciones de entidades detectadas
            text: Texto original

        Returns:
            Lista de atributos resueltos y deduplicados
        """
        logger.info(
            f"[CESP] Resolviendo {len(candidates)} candidatos, {len(entity_mentions)} entidades"
        )

        if not candidates:
            logger.warning("[CESP] No hay candidatos")
            return []

        # =====================================================================
        # PASO 1: Asegurar que todos los candidatos tengan asignación
        # =====================================================================
        assigned_candidates = self._ensure_assignments(candidates, entity_mentions, text)

        # =====================================================================
        # PASO 2: Agrupar por atributo y resolver conflictos
        # =====================================================================
        resolved_attributes = self._resolve_by_group(assigned_candidates, entity_mentions, text)
        logger.info(f"[CESP] Conflictos resueltos: {len(resolved_attributes)} atributos")

        # =====================================================================
        # PASO 3: DEDUPLICACIÓN (elimina falsos positivos)
        # =====================================================================
        final_attributes = self._deduplicator.deduplicate(resolved_attributes)
        logger.info(f"[CESP] Después de deduplicar: {len(final_attributes)} atributos")

        return final_attributes

    def _ensure_assignments(
        self, candidates: list[AttributeCandidate], entity_mentions: list[EntityMention], text: str
    ) -> list[AttributeCandidate]:
        """
        Asegura que todos los candidatos tengan una entidad asignada.

        Los candidatos del DependencyExtractor ya tienen asignación.
        Los de Regex/Embeddings se asignan por proximidad.
        """
        assigned: list[AttributeCandidate] = []

        for candidate in candidates:
            if candidate.assigned_entity_id is not None:
                assigned.append(candidate)
            else:
                # Necesita asignación por proximidad
                updated = self._assign_by_proximity(candidate, entity_mentions)
                if updated.assigned_entity_id:
                    assigned.append(updated)
                else:
                    logger.debug(
                        f"[CESP] Descartando candidato sin asignación posible: "
                        f"{candidate.attribute_type}='{candidate.value}'"
                    )

        return assigned

    def _assign_by_proximity(
        self, candidate: AttributeCandidate, entity_mentions: list[EntityMention]
    ) -> AttributeCandidate:
        """
        Asigna entidad a un candidato usando proximidad textual.
        """
        if not entity_mentions:
            return candidate

        # Buscar en misma oración
        same_sentence = [e for e in entity_mentions if e.sentence_idx == candidate.sentence_idx]

        if same_sentence:
            # Ordenar por proximidad (preferir ANTES del atributo)
            def proximity_score(entity: EntityMention) -> tuple[int, int]:
                """
                Prioriza entidades ANTES del atributo.
                Returns: (is_before, -distance)
                """
                distance = candidate.start - entity.end
                is_before = 1 if distance > 0 else 0
                return (is_before, -abs(distance))

            closest = max(same_sentence, key=proximity_score)
            distance = abs(closest.start - candidate.start)

            # Calcular confianza
            max_distance = 150
            normalized_dist = min(distance / max_distance, 1.0)
            confidence = CONFIDENCE_PROXIMITY_MAX - (
                normalized_dist * (CONFIDENCE_PROXIMITY_MAX - CONFIDENCE_PROXIMITY_MIN)
            )

            return AttributeCandidate(
                attribute_type=candidate.attribute_type,
                value=candidate.value,
                text_evidence=candidate.text_evidence,
                sentence_idx=candidate.sentence_idx,
                start=candidate.start,
                end=candidate.end,
                extractor_type=candidate.extractor_type,
                assigned_entity_id=closest.entity_id,
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=confidence,
                syntactic_evidence=candidate.syntactic_evidence,
                is_dubious=True,
                metadata={
                    **candidate.metadata,
                    "proximity_distance": distance,
                    "proximity_entity": closest.text,
                },
            )

        # Buscar en oración anterior (sujeto tácito)
        prev_sentence = [e for e in entity_mentions if e.sentence_idx == candidate.sentence_idx - 1]

        if prev_sentence:
            last_entity = prev_sentence[-1]
            return AttributeCandidate(
                attribute_type=candidate.attribute_type,
                value=candidate.value,
                text_evidence=candidate.text_evidence,
                sentence_idx=candidate.sentence_idx,
                start=candidate.start,
                end=candidate.end,
                extractor_type=candidate.extractor_type,
                assigned_entity_id=last_entity.entity_id,
                assignment_source=AssignmentSource.IMPLICIT_SUBJECT,
                base_confidence=CONFIDENCE_IMPLICIT_SUBJECT,
                syntactic_evidence=candidate.syntactic_evidence,
                is_dubious=True,
                metadata={
                    **candidate.metadata,
                    "inherited_from_sentence": candidate.sentence_idx - 1,
                },
            )

        return candidate

    def _resolve_by_group(
        self, candidates: list[AttributeCandidate], entity_mentions: list[EntityMention], text: str
    ) -> list[ResolvedAttribute]:
        """
        Agrupa candidatos por atributo y resuelve conflictos.
        """
        # Agrupar por (tipo, valor, oración, entidad)
        groups: dict[tuple[str, str, int, str], list[AttributeCandidate]] = defaultdict(list)

        for candidate in candidates:
            if candidate.assigned_entity_id:
                key = (
                    candidate.attribute_type,
                    candidate.value.lower().strip(),
                    candidate.sentence_idx,
                    candidate.assigned_entity_id,
                )
                groups[key].append(candidate)

        resolved: list[ResolvedAttribute] = []

        for key, group in groups.items():
            attr_type, value, sent_idx, entity_id = key

            # Clasificar y resolver
            status = self._conflict_resolver.classify_conflict_status(group)

            resolution = self._conflict_resolver.resolve(group, entity_mentions, text)

            if resolution:
                resolved_entity_id, confidence, source, notes = resolution

                is_dubious = (
                    source in (AssignmentSource.IMPLICIT_SUBJECT, AssignmentSource.PROXIMITY)
                    or status == ConflictStatus.CONFLICT
                )

                contributing = frozenset(c.extractor_type for c in group)

                resolved_attr = ResolvedAttribute(
                    attribute_type=attr_type,
                    value=value,
                    entity_id=resolved_entity_id,
                    final_confidence=confidence,
                    conflict_status=status,
                    assignment_source=source,
                    is_dubious=is_dubious,
                    contributing_extractors=contributing,
                    text_evidence=group[0].text_evidence,
                    sentence_idx=sent_idx,
                    resolution_notes=notes,
                )
                resolved.append(resolved_attr)

        return resolved

    def get_statistics(self, results: list[ResolvedAttribute]) -> dict[str, Any]:
        """
        Genera estadísticas del proceso de resolución.
        """
        if not results:
            return {"total": 0}

        stats = {
            "total": len(results),
            "by_status": defaultdict(int),
            "by_source": defaultdict(int),
            "by_type": defaultdict(int),
            "dubious_count": 0,
            "avg_confidence": 0.0,
        }

        total_conf = 0.0

        for attr in results:
            stats["by_status"][attr.conflict_status.value] += 1  # type: ignore[index]
            stats["by_source"][attr.assignment_source.value] += 1  # type: ignore[index]
            stats["by_type"][attr.attribute_type] += 1  # type: ignore[index]

            if attr.is_dubious:
                stats["dubious_count"] += 1  # type: ignore[operator]

            total_conf += attr.final_confidence

        stats["avg_confidence"] = total_conf / len(results)

        # Convertir defaultdicts
        stats["by_status"] = dict(stats["by_status"])  # type: ignore[call-overload]
        stats["by_source"] = dict(stats["by_source"])  # type: ignore[call-overload]
        stats["by_type"] = dict(stats["by_type"])  # type: ignore[call-overload]

        return stats


# =============================================================================
# ADAPTADOR PARA INTEGRACIÓN CON SISTEMA EXISTENTE
# =============================================================================


def create_candidates_from_extraction_results(
    extraction_results: list[dict[str, Any]],
    extractor_type: ExtractorType,
    entity_lookup: dict[str, EntityMention],
) -> list[AttributeCandidate]:
    """
    Convierte resultados del sistema existente a AttributeCandidate.

    Args:
        extraction_results: Resultados del extractor existente
        extractor_type: Tipo de extractor
        entity_lookup: Diccionario entity_id -> EntityMention

    Returns:
        Lista de AttributeCandidate
    """
    candidates = []

    for result in extraction_results:
        # Determinar la fuente de asignación basándose en metadata
        assignment_source = None
        if result.get("syntactic_relation") == "nsubj":
            assignment_source = AssignmentSource.EXPLICIT_SUBJECT
        elif result.get("syntactic_relation") == "genitive":
            assignment_source = AssignmentSource.GENITIVE
        elif result.get("from_context"):
            assignment_source = AssignmentSource.IMPLICIT_SUBJECT

        candidate = AttributeCandidate(
            attribute_type=result.get("type", "unknown"),
            value=result.get("value", ""),
            text_evidence=result.get("evidence", ""),
            sentence_idx=result.get("sentence_idx", 0),
            start=result.get("start", 0),
            end=result.get("end", 0),
            extractor_type=extractor_type,
            assigned_entity_id=result.get("entity_id"),
            assignment_source=assignment_source,
            base_confidence=result.get("confidence", 0.5),
            syntactic_evidence=result.get("syntactic_evidence"),
            is_dubious=result.get("is_dubious", False),
            metadata=result.get("metadata", {}),
        )
        candidates.append(candidate)

    return candidates
