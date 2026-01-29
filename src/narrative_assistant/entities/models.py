"""
Modelos de datos para entidades narrativas.

Define las estructuras para:
- Entidades (personajes, lugares, organizaciones)
- Menciones de entidades en el texto
- Historial de fusiones
- Sugerencias de fusión
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EntityType(Enum):
    """
    Tipos de entidades narrativas.

    Cada tipo puede tener atributos específicos que el sistema
    verificará por consistencia a lo largo del texto.
    """

    # === Seres vivos ===
    CHARACTER = "character"  # Personaje humano
    ANIMAL = "animal"  # Animal (mascota, caballo, lobo)
    CREATURE = "creature"  # Criatura fantástica/monstruo (dragón, elfo)

    # === Lugares ===
    LOCATION = "location"  # Lugar genérico (bosque, playa)
    BUILDING = "building"  # Edificio/estructura (castillo, taberna, puente)
    REGION = "region"  # Región geográfica (reino, país, continente)

    # === Objetos ===
    OBJECT = "object"  # Objeto relevante (espada, anillo, carta, libro)
    VEHICLE = "vehicle"  # Vehículo (barco, carruaje, nave espacial)

    # === Grupos ===
    ORGANIZATION = "organization"  # Organización formal (gremio, ejército, iglesia)
    FACTION = "faction"  # Facción/grupo informal (rebeldes, los del norte)
    FAMILY = "family"  # Familia/linaje/casa noble (los García, Casa Stark)

    # === Temporales ===
    EVENT = "event"  # Evento importante (La Gran Guerra, la boda)
    TIME_PERIOD = "time_period"  # Período temporal (Era Oscura, el reinado de X)

    # === Conceptuales ===
    CONCEPT = "concept"  # Concepto abstracto (profecía, maldición, ley)
    RELIGION = "religion"  # Religión/culto (los Siete, culto al Señor de la Luz)
    MAGIC_SYSTEM = "magic_system"  # Sistema mágico/poder (la Fuerza, magia de sangre)

    # === Culturales ===
    WORK = "work"  # Obra mencionada (libro, canción, leyenda, cuadro)
    TITLE = "title"  # Título/rango (Rey del Norte, Gran Maestre)
    LANGUAGE = "language"  # Idioma/dialecto (Alto Valyrio, élfico)
    CUSTOM = "custom"  # Costumbre/tradición (el Día del Nombre, el torneo)


class EntityImportance(Enum):
    """Nivel de importancia de una entidad (genérico para todos los tipos)."""

    PRINCIPAL = "principal"  # Importancia máxima (protagonista, lugar central, objeto clave)
    HIGH = "high"  # Importancia alta (co-protagonistas, lugares principales)
    MEDIUM = "medium"  # Importancia media (secundarios recurrentes, lugares frecuentes)
    LOW = "low"  # Importancia baja (personajes menores, menciones ocasionales)
    MINIMAL = "minimal"  # Importancia mínima (solo mencionado una vez)

    # Aliases para compatibilidad con valores antiguos en la DB
    SECONDARY = "secondary"  # Alias for MEDIUM (deprecated)
    PRIMARY = "primary"  # Alias for HIGH (deprecated)

    @classmethod
    def _missing_(cls, value):
        """Manejar valores antiguos de la DB."""
        # Mapeo de valores antiguos a nuevos
        legacy_mapping = {
            "secondary": cls.MEDIUM,
            "primary": cls.HIGH,
            "main": cls.PRINCIPAL,
            "critical": cls.PRINCIPAL,  # Migración de valor antiguo
            "minor": cls.LOW,
            "background": cls.MINIMAL,
        }
        if isinstance(value, str):
            return legacy_mapping.get(value.lower(), cls.MEDIUM)
        return cls.MEDIUM


@dataclass
class EntityMention:
    """
    Una mención de una entidad en el texto.

    Attributes:
        id: ID único de la mención
        entity_id: ID de la entidad a la que pertenece
        surface_form: Texto tal como aparece ("el doctor", "Juan")
        start_char: Posición de inicio
        end_char: Posición de fin
        chapter_id: ID del capítulo (opcional)
        context_before: Contexto previo (para visualización)
        context_after: Contexto posterior
        confidence: Confianza de la detección (0.0-1.0)
        source: Origen de la detección (ner, coref, manual, gazetteer)
    """

    id: Optional[int] = None
    entity_id: int = 0
    surface_form: str = ""
    start_char: int = 0
    end_char: int = 0
    chapter_id: Optional[int] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    confidence: float = 1.0
    source: str = "ner"
    metadata: Optional[str] = None  # JSON con datos adicionales (voting_detail para coref)

    @property
    def char_span(self) -> tuple[int, int]:
        """Retorna el span de caracteres."""
        return (self.start_char, self.end_char)

    @property
    def metadata_dict(self) -> Optional[dict]:
        """Deserializa metadata JSON a diccionario."""
        if not self.metadata:
            return None
        try:
            import json
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "surface_form": self.surface_form,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "chapter_id": self.chapter_id,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "confidence": self.confidence,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_row(cls, row) -> "EntityMention":
        """Crea instancia desde fila de SQLite."""
        # Acceso seguro a 'metadata' (puede no existir en BD antiguas)
        metadata = None
        try:
            metadata = row["metadata"]
        except (IndexError, KeyError):
            pass
        return cls(
            id=row["id"],
            entity_id=row["entity_id"],
            surface_form=row["surface_form"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            chapter_id=row["chapter_id"],
            context_before=row["context_before"],
            context_after=row["context_after"],
            confidence=row["confidence"],
            source=row["source"],
            metadata=metadata,
        )


@dataclass
class Entity:
    """
    Una entidad narrativa (personaje, lugar, etc.).

    Attributes:
        id: ID único
        project_id: ID del proyecto al que pertenece
        entity_type: Tipo de entidad
        canonical_name: Nombre canónico (preferido)
        aliases: Lista de nombres alternativos
        importance: Nivel de importancia
        description: Descripción opcional
        first_appearance_char: Posición de primera aparición
        mention_count: Número total de menciones
        merged_from_ids: IDs de entidades fusionadas en esta
        is_active: Si la entidad está activa (no eliminada)
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
    """

    id: Optional[int] = None
    project_id: int = 0
    entity_type: EntityType = EntityType.CHARACTER
    canonical_name: str = ""
    aliases: list[str] = field(default_factory=list)
    importance: EntityImportance = EntityImportance.MEDIUM
    description: Optional[str] = None
    first_appearance_char: Optional[int] = None
    mention_count: int = 0
    merged_from_ids: list[int] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def all_names(self) -> list[str]:
        """Retorna todos los nombres (canónico + aliases)."""
        return [self.canonical_name] + self.aliases

    def has_alias(self, name: str) -> bool:
        """Verifica si un nombre es alias de esta entidad."""
        name_lower = name.lower()
        return any(n.lower() == name_lower for n in self.all_names)

    def add_alias(self, name: str) -> bool:
        """
        Añade un alias si no existe.

        Returns:
            True si se añadió, False si ya existía
        """
        if not self.has_alias(name) and name.lower() != self.canonical_name.lower():
            self.aliases.append(name)
            return True
        return False

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "entity_type": self.entity_type.value,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "importance": self.importance.value,
            "description": self.description,
            "first_appearance_char": self.first_appearance_char,
            "mention_count": self.mention_count,
            "merged_from_ids": self.merged_from_ids,
            "is_active": self.is_active,
        }

    @classmethod
    def from_row(cls, row) -> "Entity":
        """Crea instancia desde fila de SQLite."""
        # Parsear aliases y merged_from_ids desde JSON
        aliases = []
        if row["merged_from_ids"]:
            try:
                merged_data = json.loads(row["merged_from_ids"])
                # El campo puede contener aliases además de IDs
                if isinstance(merged_data, dict):
                    aliases = merged_data.get("aliases", [])
                    merged_from = merged_data.get("merged_ids", [])
                else:
                    merged_from = merged_data
            except json.JSONDecodeError:
                merged_from = []
        else:
            merged_from = []

        return cls(
            id=row["id"],
            project_id=row["project_id"],
            entity_type=EntityType(row["entity_type"]),
            canonical_name=row["canonical_name"],
            aliases=aliases,
            importance=EntityImportance(row["importance"]),
            description=row["description"],
            first_appearance_char=row["first_appearance_char"],
            mention_count=row["mention_count"],
            merged_from_ids=merged_from,
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            updated_at=datetime.fromisoformat(row["updated_at"])
            if row["updated_at"]
            else None,
        )


@dataclass
class MergeHistory:
    """
    Registro de una fusión de entidades.

    Attributes:
        id: ID del registro
        project_id: ID del proyecto
        result_entity_id: ID de la entidad resultante
        source_entity_ids: IDs de las entidades fusionadas
        source_snapshots: Snapshots de las entidades antes de fusionar
        canonical_name_before: Nombres canónicos originales
        merged_at: Fecha de la fusión
        merged_by: Quién realizó la fusión (user, auto)
        undone_at: Fecha si se deshizo la fusión
        note: Nota del usuario
    """

    id: Optional[int] = None
    project_id: int = 0
    result_entity_id: int = 0
    source_entity_ids: list[int] = field(default_factory=list)
    source_snapshots: list[dict] = field(default_factory=list)
    canonical_name_before: list[str] = field(default_factory=list)
    merged_at: Optional[datetime] = None
    merged_by: str = "user"
    undone_at: Optional[datetime] = None
    note: Optional[str] = None

    @property
    def is_undone(self) -> bool:
        """Retorna si la fusión fue deshecha."""
        return self.undone_at is not None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "result_entity_id": self.result_entity_id,
            "source_entity_ids": self.source_entity_ids,
            "source_snapshots": self.source_snapshots,
            "canonical_name_before": self.canonical_name_before,
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "merged_by": self.merged_by,
            "undone_at": self.undone_at.isoformat() if self.undone_at else None,
            "note": self.note,
        }


@dataclass
class MergeSuggestion:
    """
    Sugerencia de fusión de entidades.

    Attributes:
        entity1: Primera entidad
        entity2: Segunda entidad
        similarity: Score de similaridad (0.0-1.0)
        reason: Razón de la sugerencia
        evidence: Evidencia adicional
    """

    entity1: Entity
    entity2: Entity
    similarity: float
    reason: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "entity1": self.entity1.to_dict(),
            "entity2": self.entity2.to_dict(),
            "similarity": self.similarity,
            "reason": self.reason,
            "evidence": self.evidence,
        }
