"""
Generador de Guía de Estilo Automática.

Analiza el manuscrito y genera una guía de estilo con:
- Decisiones de grafía (José/Jose, María/Maria)
- Lista de entidades canónicas (nombres, lugares, organizaciones)
- Términos específicos y neologismos
- Convenciones de mayúsculas y acentuación

Útil para:
- Mantener consistencia durante la edición
- Onboarding de nuevos correctores
- Referencia rápida del mundo narrativo
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
from collections import Counter, defaultdict

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from ..entities.models import Entity, EntityType
from ..entities.repository import get_entity_repository

logger = logging.getLogger(__name__)


@dataclass
class SpellingDecision:
    """Decisión de grafía para una entidad o término."""

    canonical_form: str  # Forma canónica elegida
    variants: list[str]  # Variantes encontradas
    frequency: dict[str, int]  # Frecuencia de cada variante
    recommendation: str  # "canonical" o "variant_allowed"
    notes: str = ""  # Notas adicionales


@dataclass
class EntityListing:
    """Listado de una entidad en la guía."""

    type: str  # "CHARACTER", "LOCATION", "ORGANIZATION"
    canonical_name: str
    aliases: list[str]
    importance: str
    first_mention_chapter: Optional[int] = None
    description: str = ""  # Descripción breve (opcional)


@dataclass
class StyleGuide:
    """
    Guía de estilo completa del manuscrito.
    """

    # Metadata del proyecto
    project_name: str
    project_id: int
    generated_date: str

    # Decisiones de grafía
    spelling_decisions: list[SpellingDecision]

    # Entidades del mundo narrativo
    characters: list[EntityListing]
    locations: list[EntityListing]
    organizations: list[EntityListing]

    # Términos especiales (placeholder para futuro)
    special_terms: list[str] = field(default_factory=list)

    # Estadísticas
    total_entities: int = 0
    total_spelling_variants: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convierte la guía a diccionario."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convierte la guía a JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Genera guía de estilo en formato Markdown."""
        lines = []

        # Header
        lines.append(f"# Guía de Estilo - {self.project_name}")
        lines.append("")
        lines.append(f"**Generado:** {self.generated_date}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Tabla de contenidos
        lines.append("## Tabla de Contenidos")
        lines.append("")
        lines.append("1. [Decisiones de Grafía](#decisiones-de-grafía)")
        lines.append("2. [Personajes](#personajes)")
        lines.append("3. [Ubicaciones](#ubicaciones)")
        lines.append("4. [Organizaciones](#organizaciones)")
        if self.special_terms:
            lines.append("5. [Términos Especiales](#términos-especiales)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Decisiones de grafía
        lines.append("## Decisiones de Grafía")
        lines.append("")
        if self.spelling_decisions:
            lines.append("| Forma Canónica | Variantes Encontradas | Frecuencia | Recomendación |")
            lines.append("|----------------|----------------------|------------|---------------|")
            for decision in sorted(self.spelling_decisions, key=lambda d: -sum(d.frequency.values())):
                variants_str = ", ".join(decision.variants) if decision.variants else "ninguna"
                freq_total = sum(decision.frequency.values())
                recommendation = "✓ Usar forma canónica" if decision.recommendation == "canonical" else "⚠ Variantes permitidas"
                lines.append(f"| **{decision.canonical_form}** | {variants_str} | {freq_total} | {recommendation} |")
            lines.append("")
            if any(d.notes for d in self.spelling_decisions):
                lines.append("### Notas:")
                for decision in self.spelling_decisions:
                    if decision.notes:
                        lines.append(f"- **{decision.canonical_form}:** {decision.notes}")
                lines.append("")
        else:
            lines.append("_No se detectaron variaciones de grafía._")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Personajes
        lines.append("## Personajes")
        lines.append("")
        if self.characters:
            # Agrupar por importancia (5 niveles: critical, high, medium, low, minimal)
            critical = [c for c in self.characters if c.importance == "critical"]
            high_importance = [c for c in self.characters if c.importance == "high"]
            medium_importance = [c for c in self.characters if c.importance == "medium"]
            low_importance = [c for c in self.characters if c.importance == "low"]
            minimal_importance = [c for c in self.characters if c.importance == "minimal"]

            # Protagonistas principales (critical + high)
            protagonists = critical + high_importance
            if protagonists:
                lines.append("### Protagonistas")
                lines.append("")
                for char in sorted(protagonists, key=lambda c: c.canonical_name):
                    lines.append(f"#### {char.canonical_name}")
                    if char.aliases:
                        lines.append(f"**También:** {', '.join(char.aliases)}")
                    if char.first_mention_chapter:
                        lines.append(f"**Primera mención:** Capítulo {char.first_mention_chapter}")
                    if char.description:
                        lines.append(f"{char.description}")
                    lines.append("")

            if medium_importance:
                lines.append("### Personajes Secundarios")
                lines.append("")
                for char in sorted(medium_importance, key=lambda c: c.canonical_name):
                    lines.append(f"- **{char.canonical_name}**")
                    if char.aliases:
                        lines.append(f"  - También: {', '.join(char.aliases)}")
                lines.append("")

            # Menores (low + minimal)
            minor_chars = low_importance + minimal_importance
            if minor_chars:
                lines.append("### Personajes Menores")
                lines.append("")
                minor_names = [c.canonical_name for c in sorted(minor_chars, key=lambda c: c.canonical_name)]
                lines.append(", ".join(minor_names))
                lines.append("")
        else:
            lines.append("_No se detectaron personajes._")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Ubicaciones
        lines.append("## Ubicaciones")
        lines.append("")
        if self.locations:
            for loc in sorted(self.locations, key=lambda l: l.canonical_name):
                lines.append(f"- **{loc.canonical_name}**")
                if loc.aliases:
                    lines.append(f"  - También: {', '.join(loc.aliases)}")
            lines.append("")
        else:
            lines.append("_No se detectaron ubicaciones._")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Organizaciones
        lines.append("## Organizaciones")
        lines.append("")
        if self.organizations:
            for org in sorted(self.organizations, key=lambda o: o.canonical_name):
                lines.append(f"- **{org.canonical_name}**")
                if org.aliases:
                    lines.append(f"  - También: {', '.join(org.aliases)}")
            lines.append("")
        else:
            lines.append("_No se detectaron organizaciones._")
            lines.append("")

        # Términos especiales
        if self.special_terms:
            lines.append("---")
            lines.append("")
            lines.append("## Términos Especiales")
            lines.append("")
            for term in sorted(self.special_terms):
                lines.append(f"- {term}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("_Guía generada automáticamente por Narrative Assistant_")
        lines.append("")
        lines.append(f"**Total de entidades:** {self.total_entities}")
        lines.append(f"**Variaciones de grafía detectadas:** {self.total_spelling_variants}")

        return "\n".join(lines)


def _detect_spelling_variants(entities: list[Entity]) -> list[SpellingDecision]:
    """
    Detecta variaciones de grafía en nombres de entidades.

    Por ejemplo:
    - María / Maria (con/sin acento)
    - José / Jose
    - Dr. Pérez / Doctor Pérez / Pérez
    """
    decisions = []

    for entity in entities:
        all_forms = [entity.canonical_name] + (entity.aliases or [])

        # Agrupar formas similares (simplificado - normalizar acentos)
        import unicodedata

        def normalize(s: str) -> str:
            """Normaliza string quitando acentos."""
            return ''.join(
                c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn'
            ).lower()

        # Contar frecuencias (simplificado - en realidad debería contar en el texto)
        frequency = {form: 1 for form in all_forms}

        # Detectar variantes
        variants = []
        for alias in (entity.aliases or []):
            if normalize(alias) == normalize(entity.canonical_name):
                # Misma palabra, diferente acentuación
                variants.append(alias)

        if variants:
            decision = SpellingDecision(
                canonical_form=entity.canonical_name,
                variants=variants,
                frequency=frequency,
                recommendation="canonical",
                notes=f"Se encontraron {len(variants)} variante(s) de grafía. Se recomienda usar siempre la forma canónica."
            )
            decisions.append(decision)

    return decisions


def generate_style_guide(
    project_id: int,
    project_name: str,
) -> Result[StyleGuide]:
    """
    Genera una guía de estilo completa para un proyecto.

    Args:
        project_id: ID del proyecto
        project_name: Nombre del proyecto

    Returns:
        Result con StyleGuide completa
    """
    try:
        from datetime import datetime

        entity_repo = get_entity_repository()
        entities = entity_repo.get_by_project(project_id)

        if not entities:
            logger.warning(f"No entities found for project {project_id}")

        # Separar por tipo
        characters = [e for e in entities if e.entity_type == EntityType.CHARACTER]
        locations = [e for e in entities if e.entity_type == EntityType.LOCATION]
        organizations = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]

        # Detectar decisiones de grafía
        spelling_decisions = _detect_spelling_variants(entities)

        # Crear listados
        character_listings = [
            EntityListing(
                type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in characters
        ]

        location_listings = [
            EntityListing(
                type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in locations
        ]

        organization_listings = [
            EntityListing(
                type=e.entity_type.value,
                canonical_name=e.canonical_name,
                aliases=e.aliases or [],
                importance=e.importance.value,
            )
            for e in organizations
        ]

        # Crear guía
        style_guide = StyleGuide(
            project_name=project_name,
            project_id=project_id,
            generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            spelling_decisions=spelling_decisions,
            characters=character_listings,
            locations=location_listings,
            organizations=organization_listings,
            total_entities=len(entities),
            total_spelling_variants=len(spelling_decisions),
        )

        logger.info(f"Generated style guide for project {project_id}")
        return Result.success(style_guide)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to generate style guide: {str(e)}",
            severity=ErrorSeverity.ERROR,
            user_message=f"Error generando guía de estilo: {str(e)}",
        )
        logger.error(f"Error generating style guide: {e}", exc_info=True)
        return Result.failure(error)


def export_style_guide(
    style_guide: StyleGuide,
    output_path: Path,
    format: str = "both",  # "json", "markdown", "both"
) -> Result[list[Path]]:
    """
    Exporta la guía de estilo a archivo.

    Args:
        style_guide: Guía de estilo generada
        output_path: Path base (sin extensión)
        format: Formato de exportación

    Returns:
        Result con lista de archivos creados
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        exported_files = []

        if format in ("json", "both"):
            json_path = output_path.with_suffix(".json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(style_guide.to_json())
            exported_files.append(json_path)
            logger.info(f"Exported style guide JSON: {json_path}")

        if format in ("markdown", "both"):
            md_path = output_path.with_suffix(".md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(style_guide.to_markdown())
            exported_files.append(md_path)
            logger.info(f"Exported style guide Markdown: {md_path}")

        return Result.success(exported_files)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to export style guide: {str(e)}",
            severity=ErrorSeverity.ERROR,
            user_message=f"Error exportando guía de estilo: {str(e)}",
        )
        logger.error(f"Error exporting style guide: {e}", exc_info=True)
        return Result.failure(error)
