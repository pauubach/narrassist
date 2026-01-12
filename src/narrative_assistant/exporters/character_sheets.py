"""
Exportador de Fichas de Personaje.

Genera fichas completas de personajes con:
- Información básica (nombre, aliases, tipo)
- Atributos físicos y psicológicos extraídos
- Menciones en el texto (capítulos, frecuencia)
- Relaciones con otros personajes
- Diálogos (si disponible)

Formatos:
- JSON: Estructurado, programáticamente procesable
- Markdown: Legible para humanos, incluye en informes
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
from collections import defaultdict

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from ..entities.models import Entity, EntityType, EntityImportance
from ..entities.repository import get_entity_repository
from ..nlp.attributes import ExtractedAttribute, AttributeKey, AttributeCategory

logger = logging.getLogger(__name__)


@dataclass
class AttributeInfo:
    """Información de un atributo de personaje."""

    category: str  # "physical", "psychological", etc.
    key: str  # "eye_color", "height", etc.
    value: str  # "azules", "alto", etc.
    confidence: float
    first_mentioned_chapter: Optional[int]
    occurrences: int = 1
    excerpts: list[str] = field(default_factory=list)


@dataclass
class MentionInfo:
    """Información de menciones del personaje."""

    total_mentions: int
    chapters: list[int]  # Capítulos donde aparece
    mention_frequency: dict[int, int]  # {chapter_id: count}
    first_appearance_chapter: Optional[int]
    last_appearance_chapter: Optional[int]


@dataclass
class CharacterSheet:
    """
    Ficha completa de un personaje.

    Incluye toda la información extraída del análisis.
    """

    # Identidad
    entity_id: int
    canonical_name: str
    aliases: list[str]
    entity_type: str
    importance: str

    # Atributos extraídos
    physical_attributes: list[AttributeInfo]
    psychological_attributes: list[AttributeInfo]
    other_attributes: list[AttributeInfo]

    # Menciones
    mentions: MentionInfo

    # Relaciones (placeholder para futura implementación)
    relationships: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    project_id: int = 0
    confidence_score: float = 0.0  # Score promedio de todos los atributos

    def to_dict(self) -> dict[str, Any]:
        """Convierte la ficha a diccionario."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convierte la ficha a JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Genera ficha en formato Markdown legible."""
        lines = []

        # Header
        lines.append(f"# {self.canonical_name}")
        lines.append("")

        # Metadata básica
        if self.aliases:
            lines.append(f"**También conocido como:** {', '.join(self.aliases)}")
        lines.append(f"**Tipo:** {self.entity_type}")
        lines.append(f"**Importancia:** {self.importance}")
        lines.append(f"**Confianza del análisis:** {self.confidence_score:.0%}")
        lines.append("")

        # Menciones
        lines.append("## Apariciones")
        lines.append(f"- **Total de menciones:** {self.mentions.total_mentions}")
        if self.mentions.first_appearance_chapter:
            lines.append(f"- **Primera aparición:** Capítulo {self.mentions.first_appearance_chapter}")
        if self.mentions.last_appearance_chapter:
            lines.append(f"- **Última aparición:** Capítulo {self.mentions.last_appearance_chapter}")
        if self.mentions.chapters:
            chapters_str = ", ".join(str(c) for c in sorted(self.mentions.chapters))
            lines.append(f"- **Aparece en capítulos:** {chapters_str}")
        lines.append("")

        # Atributos físicos
        if self.physical_attributes:
            lines.append("## Atributos Físicos")
            for attr in sorted(self.physical_attributes, key=lambda a: -a.confidence):
                lines.append(f"- **{attr.key.replace('_', ' ').title()}:** {attr.value} "
                             f"(confianza: {attr.confidence:.0%})")
                if attr.first_mentioned_chapter:
                    lines.append(f"  - Mencionado en cap. {attr.first_mentioned_chapter}")
                if attr.excerpts:
                    lines.append(f"  - _\"{attr.excerpts[0]}\"_")
            lines.append("")

        # Atributos psicológicos
        if self.psychological_attributes:
            lines.append("## Atributos Psicológicos")
            for attr in sorted(self.psychological_attributes, key=lambda a: -a.confidence):
                lines.append(f"- **{attr.key.replace('_', ' ').title()}:** {attr.value} "
                             f"(confianza: {attr.confidence:.0%})")
            lines.append("")

        # Otros atributos
        if self.other_attributes:
            lines.append("## Otros Atributos")
            for attr in sorted(self.other_attributes, key=lambda a: -a.confidence):
                lines.append(f"- **{attr.key.replace('_', ' ').title()}:** {attr.value}")
            lines.append("")

        # Relaciones (futuro)
        if self.relationships:
            lines.append("## Relaciones")
            for rel in self.relationships:
                lines.append(f"- {rel}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"_Ficha generada automáticamente por Narrative Assistant_")

        return "\n".join(lines)


def _group_attributes_by_category(
    attributes: list[ExtractedAttribute],
) -> tuple[list[AttributeInfo], list[AttributeInfo], list[AttributeInfo]]:
    """
    Agrupa atributos por categoría.

    Returns:
        (physical, psychological, other)
    """
    physical = []
    psychological = []
    other = []

    # Agrupar por (category, key, value) para combinar duplicados
    attr_map: dict[tuple[str, str, str], AttributeInfo] = {}

    for attr in attributes:
        key_tuple = (attr.category.value, attr.key.value, attr.value)

        if key_tuple in attr_map:
            # Incrementar occurrences y añadir excerpt
            existing = attr_map[key_tuple]
            existing.occurrences += 1
            if attr.source_text and attr.source_text not in existing.excerpts:
                existing.excerpts.append(attr.source_text[:100])
        else:
            # Nuevo atributo
            attr_info = AttributeInfo(
                category=attr.category.value,
                key=attr.key.value,
                value=attr.value,
                confidence=attr.confidence,
                first_mentioned_chapter=attr.chapter_id,
                excerpts=[attr.source_text[:100]] if attr.source_text else [],
            )
            attr_map[key_tuple] = attr_info

    # Clasificar por categoría
    for attr_info in attr_map.values():
        if attr_info.category == AttributeCategory.PHYSICAL.value:
            physical.append(attr_info)
        elif attr_info.category == AttributeCategory.PSYCHOLOGICAL.value:
            psychological.append(attr_info)
        else:
            other.append(attr_info)

    return physical, psychological, other


def export_character_sheet(
    entity: Entity,
    attributes: list[ExtractedAttribute],
    project_id: int,
) -> CharacterSheet:
    """
    Genera una ficha de personaje desde una entidad y sus atributos.

    Args:
        entity: Entidad del personaje
        attributes: Lista de atributos extraídos
        project_id: ID del proyecto

    Returns:
        Ficha de personaje completa
    """
    # Filtrar atributos de esta entidad
    entity_attrs = [
        a for a in attributes
        if a.entity_name == entity.canonical_name
    ]

    # Agrupar por categoría
    physical, psychological, other = _group_attributes_by_category(entity_attrs)

    # Calcular menciones (simplificado - en el futuro usar menciones reales de BD)
    chapters_with_attrs = set(
        a.chapter_id for a in entity_attrs
        if a.chapter_id is not None
    )
    mention_frequency = defaultdict(int)
    for attr in entity_attrs:
        if attr.chapter_id:
            mention_frequency[attr.chapter_id] += 1

    mentions = MentionInfo(
        total_mentions=len(entity_attrs),
        chapters=sorted(list(chapters_with_attrs)),
        mention_frequency=dict(mention_frequency),
        first_appearance_chapter=min(chapters_with_attrs) if chapters_with_attrs else None,
        last_appearance_chapter=max(chapters_with_attrs) if chapters_with_attrs else None,
    )

    # Calcular confianza promedio
    if entity_attrs:
        confidence_score = sum(a.confidence for a in entity_attrs) / len(entity_attrs)
    else:
        confidence_score = 0.0

    # Crear ficha
    sheet = CharacterSheet(
        entity_id=entity.id or 0,
        canonical_name=entity.canonical_name,
        aliases=entity.aliases or [],
        entity_type=entity.entity_type.value,
        importance=entity.importance.value,
        physical_attributes=physical,
        psychological_attributes=psychological,
        other_attributes=other,
        mentions=mentions,
        project_id=project_id,
        confidence_score=confidence_score,
    )

    return sheet


def export_all_character_sheets(
    project_id: int,
    attributes: list[ExtractedAttribute],
    output_dir: Path,
    format: str = "both",  # "json", "markdown", "both"
) -> Result[list[Path]]:
    """
    Exporta fichas de todos los personajes del proyecto.

    Args:
        project_id: ID del proyecto
        attributes: Lista de todos los atributos extraídos
        output_dir: Directorio de salida
        format: Formato de exportación

    Returns:
        Result con lista de archivos creados
    """
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        entity_repo = get_entity_repository()
        entities = entity_repo.get_by_project(project_id)

        if not entities:
            logger.warning(f"No entities found for project {project_id}")
            return Result.success([])

        # Filtrar solo personajes
        characters = [
            e for e in entities
            if e.entity_type == EntityType.CHARACTER
        ]

        if not characters:
            logger.warning(f"No characters found for project {project_id}")
            return Result.success([])

        exported_files = []

        for entity in characters:
            # Generar ficha
            sheet = export_character_sheet(entity, attributes, project_id)

            # Nombre de archivo seguro
            safe_name = "".join(
                c if c.isalnum() or c in (' ', '-', '_') else '_'
                for c in entity.canonical_name
            ).strip().replace(' ', '_').lower()

            # Exportar según formato
            if format in ("json", "both"):
                json_path = output_dir / f"{safe_name}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(sheet.to_json())
                exported_files.append(json_path)
                logger.info(f"Exported JSON sheet: {json_path}")

            if format in ("markdown", "both"):
                md_path = output_dir / f"{safe_name}.md"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(sheet.to_markdown())
                exported_files.append(md_path)
                logger.info(f"Exported Markdown sheet: {md_path}")

        logger.info(f"Exported {len(characters)} character sheets to {output_dir}")
        return Result.success(exported_files)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to export character sheets: {str(e)}",
            severity=ErrorSeverity.ERROR,
            user_message=f"Error exportando fichas de personaje: {str(e)}",
        )
        logger.error(f"Error exporting character sheets: {e}", exc_info=True)
        return Result.failure(error)
