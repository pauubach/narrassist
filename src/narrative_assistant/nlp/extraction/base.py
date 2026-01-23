# -*- coding: utf-8 -*-
"""
Interfaces base para el sistema de extracción de atributos.

Define los contratos que deben implementar todos los extractores,
así como las estructuras de datos compartidas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, Any


class ExtractionMethod(Enum):
    """Métodos de extracción disponibles."""
    REGEX = "regex"
    DEPENDENCY = "dependency"
    SEMANTIC_LLM = "semantic_llm"
    EMBEDDINGS = "embeddings"


class AttributeType(Enum):
    """Tipos de atributos que podemos extraer."""
    # Físicos
    EYE_COLOR = "eye_color"
    HAIR_COLOR = "hair_color"
    HAIR_TYPE = "hair_type"  # largo, corto, rizado
    HEIGHT = "height"  # alto, bajo
    BUILD = "build"  # delgado, fornido
    AGE = "age"
    SKIN = "skin"
    DISTINCTIVE_FEATURE = "distinctive_feature"  # Para fantasy/sci-fi

    # Ubicación
    LOCATION = "location"

    # Otros
    PROFESSION = "profession"
    PERSONALITY = "personality"
    OTHER = "other"


@dataclass
class ExtractedAttribute:
    """
    Un atributo extraído por un extractor individual.

    Attributes:
        entity_name: Nombre de la entidad a la que pertenece el atributo
        attribute_type: Tipo de atributo (eye_color, height, etc.)
        value: Valor del atributo ("azules", "alto", etc.)
        confidence: Confianza de la extracción (0.0-1.0)
        source_text: Texto fuente de donde se extrajo
        extraction_method: Método usado para extraer
        chapter: Número de capítulo (opcional)
        is_negated: Si el atributo está negado ("no tenía ojos azules")
        is_metaphor: Si es parte de una metáfora
        raw_evidence: Evidencia original sin procesar
    """
    entity_name: str
    attribute_type: AttributeType
    value: str
    confidence: float
    source_text: str
    extraction_method: ExtractionMethod
    chapter: Optional[int] = None
    is_negated: bool = False
    is_metaphor: bool = False
    raw_evidence: Optional[str] = None

    def __post_init__(self):
        """Validar y normalizar valores."""
        # Normalizar valor
        if self.value:
            self.value = self.value.strip().lower()

        # Asegurar confianza en rango válido
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class ExtractionContext:
    """
    Contexto para la extracción de atributos.

    Proporciona toda la información necesaria para que un extractor
    realice su trabajo.

    Attributes:
        text: Texto a analizar
        entity_names: Nombres de entidades conocidas
        entity_mentions: Lista de menciones con posiciones (name, start, end)
        chapter: Número de capítulo (opcional)
        previous_attributes: Atributos ya extraídos (para contexto)
        genre_hint: Pista de género literario
        doc: Documento spaCy pre-procesado (opcional, para reutilizar)
    """
    text: str
    entity_names: list[str]
    entity_mentions: Optional[list[tuple[str, int, int]]] = None  # (name, start, end)
    chapter: Optional[int] = None
    previous_attributes: Optional[list[ExtractedAttribute]] = None
    genre_hint: Optional[str] = None  # "fantasy", "sci-fi", "realistic"
    doc: Optional[Any] = None  # spaCy Doc pre-procesado

    def __post_init__(self):
        """Inicializar valores por defecto."""
        if self.previous_attributes is None:
            self.previous_attributes = []

        # Normalizar nombres de entidades
        self.entity_names = [name.strip() for name in self.entity_names if name.strip()]


@dataclass
class ExtractionResult:
    """
    Resultado de un extractor individual.

    Attributes:
        attributes: Lista de atributos extraídos
        confidence: Confianza general de este extractor para este texto
        method: Método de extracción usado
        errors: Errores ocurridos durante la extracción
        metadata: Metadatos adicionales del proceso
    """
    attributes: list[ExtractedAttribute]
    confidence: float
    method: ExtractionMethod
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """True si no se extrajeron atributos."""
        return len(self.attributes) == 0

    @property
    def has_errors(self) -> bool:
        """True si hubo errores."""
        return len(self.errors) > 0


@dataclass
class AggregatedAttribute:
    """
    Atributo final después de agregación de múltiples extractores.

    Representa el resultado de combinar extracciones de diferentes
    métodos usando votación ponderada.

    Attributes:
        entity_name: Nombre de la entidad
        attribute_type: Tipo de atributo
        value: Valor final (consenso)
        final_confidence: Confianza después de agregación
        sources: Lista de (método, confianza) de cada fuente
        consensus_level: Nivel de consenso ("unanimous", "majority", "single")
        chapter: Capítulo donde se encontró
        is_negated: Si está negado
    """
    entity_name: str
    attribute_type: AttributeType
    value: str
    final_confidence: float
    sources: list[tuple[ExtractionMethod, float]]
    consensus_level: str  # "unanimous", "majority", "contested", "single"
    chapter: Optional[int] = None
    is_negated: bool = False

    @property
    def source_count(self) -> int:
        """Número de extractores que encontraron este atributo."""
        return len(self.sources)

    @property
    def is_high_confidence(self) -> bool:
        """True si tiene alta confianza (>0.8)."""
        return self.final_confidence >= 0.8

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "entity_name": self.entity_name,
            "attribute_type": self.attribute_type.value,
            "value": self.value,
            "confidence": self.final_confidence,
            "sources": [(m.value, c) for m, c in self.sources],
            "consensus_level": self.consensus_level,
            "chapter": self.chapter,
            "is_negated": self.is_negated,
        }


class AttributeExtractorProtocol(Protocol):
    """
    Protocolo que deben implementar todos los extractores.

    Permite duck typing para extractores sin herencia.
    """

    @property
    def method(self) -> ExtractionMethod:
        """Método de extracción que usa este extractor."""
        ...

    @property
    def supported_attributes(self) -> set[AttributeType]:
        """Tipos de atributos que puede extraer."""
        ...

    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """Extrae atributos del contexto dado."""
        ...

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Retorna confianza (0-1) de que puede manejar el contexto.

        Útil para el router de complejidad.
        """
        ...


class BaseExtractor(ABC):
    """
    Clase base abstracta para todos los extractores.

    Implementa funcionalidad común y define la interfaz que
    deben seguir todos los extractores.
    """

    @property
    @abstractmethod
    def method(self) -> ExtractionMethod:
        """Método de extracción que usa este extractor."""
        pass

    @property
    @abstractmethod
    def supported_attributes(self) -> set[AttributeType]:
        """Tipos de atributos que puede extraer."""
        pass

    @abstractmethod
    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extrae atributos del contexto.

        Args:
            context: Contexto con texto y entidades

        Returns:
            ExtractionResult con atributos extraídos
        """
        pass

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Evalúa capacidad de manejar el contexto.

        Por defecto, todos los extractores pueden intentar (0.5).
        Subclases pueden sobrescribir para ser más selectivos.

        Args:
            context: Contexto a evaluar

        Returns:
            Confianza entre 0.0 y 1.0
        """
        return 0.5

    def _create_attribute(
        self,
        entity_name: str,
        attr_type: AttributeType,
        value: str,
        confidence: float,
        source_text: str,
        chapter: Optional[int] = None,
        is_negated: bool = False,
        is_metaphor: bool = False,
    ) -> ExtractedAttribute:
        """
        Helper para crear atributos con valores por defecto.

        Centraliza la creación de ExtractedAttribute.
        """
        return ExtractedAttribute(
            entity_name=entity_name,
            attribute_type=attr_type,
            value=value,
            confidence=confidence,
            source_text=source_text,
            extraction_method=self.method,
            chapter=chapter,
            is_negated=is_negated,
            is_metaphor=is_metaphor,
        )

    def _create_result(
        self,
        attributes: list[ExtractedAttribute],
        errors: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ExtractionResult:
        """
        Helper para crear resultados.

        Calcula confianza automáticamente basándose en atributos.
        """
        if attributes:
            avg_confidence = sum(a.confidence for a in attributes) / len(attributes)
        else:
            avg_confidence = 0.0

        return ExtractionResult(
            attributes=attributes,
            confidence=avg_confidence,
            method=self.method,
            errors=errors or [],
            metadata=metadata or {},
        )
