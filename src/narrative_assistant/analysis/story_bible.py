"""
Story Bible - Vista wiki consolidada de entidades del manuscrito.

Agrega toda la información disponible sobre cada entidad en una
ficha completa tipo "biblia de la historia":

- Datos básicos (nombre, tipo, aliases, importancia)
- Atributos extraídos (físicos, psicológicos, etc.)
- Relaciones con otras entidades
- Timeline de apariciones por capítulo
- Estado vital (vivo/muerto, eventos de muerte)
- Resumen de conocimiento inter-personajes
- Perfil de voz (si es personaje con diálogos)
- Arco emocional resumido

Inspirado en Sudowrite's Story Bible y Scrivener's Character Sheets.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EntityBibleEntry:
    """Entrada de la biblia para una entidad."""
    # Datos básicos
    entity_id: int = 0
    canonical_name: str = ""
    entity_type: str = ""
    importance: str = ""
    aliases: list[str] = field(default_factory=list)
    description: str = ""

    # Presencia en el texto
    mention_count: int = 0
    first_chapter: Optional[int] = None
    last_chapter: Optional[int] = None
    chapters_present: list[int] = field(default_factory=list)

    # Atributos agrupados por categoría
    attributes: dict[str, list[dict]] = field(default_factory=dict)

    # Relaciones con otras entidades
    relationships: list[dict] = field(default_factory=list)

    # Estado vital
    vital_status: Optional[dict] = None

    # Perfil de voz (solo personajes)
    voice_profile: Optional[dict] = None

    # Arco emocional resumido
    emotional_arc: Optional[dict] = None

    # Conocimiento inter-personaje
    knowledge_summary: Optional[dict] = None

    # Notas del usuario (manual)
    user_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type,
            "importance": self.importance,
            "aliases": self.aliases,
            "description": self.description,
            "mention_count": self.mention_count,
            "first_chapter": self.first_chapter,
            "last_chapter": self.last_chapter,
            "chapters_present": self.chapters_present,
            "attributes": self.attributes,
            "relationships": self.relationships,
            "vital_status": self.vital_status,
            "voice_profile": self.voice_profile,
            "emotional_arc": self.emotional_arc,
            "knowledge_summary": self.knowledge_summary,
            "user_notes": self.user_notes,
        }


@dataclass
class StoryBible:
    """Biblia completa de la historia."""
    project_id: int = 0
    project_name: str = ""
    entries: list[EntityBibleEntry] = field(default_factory=list)
    # Estadísticas globales
    total_characters: int = 0
    total_locations: int = 0
    total_organizations: int = 0
    total_objects: int = 0
    total_other: int = 0

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "entries": [e.to_dict() for e in self.entries],
            "stats": {
                "total_characters": self.total_characters,
                "total_locations": self.total_locations,
                "total_organizations": self.total_organizations,
                "total_objects": self.total_objects,
                "total_other": self.total_other,
            },
        }


class StoryBibleBuilder:
    """
    Construye la Story Bible agregando datos de múltiples fuentes.

    Uso:
        builder = StoryBibleBuilder(project_id)
        bible = builder.build()
    """

    def __init__(self, project_id: int):
        self.project_id = project_id

    def build(
        self,
        include_voice: bool = True,
        include_emotions: bool = True,
        include_knowledge: bool = True,
        include_vital: bool = True,
        entity_id: Optional[int] = None,
    ) -> StoryBible:
        """
        Construye la Story Bible completa o para una entidad.

        Args:
            include_voice: Incluir perfiles de voz
            include_emotions: Incluir arcos emocionales
            include_knowledge: Incluir conocimiento inter-personaje
            include_vital: Incluir estado vital
            entity_id: Si se especifica, solo construye para esta entidad

        Returns:
            StoryBible con las entradas construidas
        """
        bible = StoryBible(project_id=self.project_id)

        # Cargar entidades
        entities = self._load_entities(entity_id)
        if not entities:
            return bible

        # Cargar datos en bulk para eficiencia
        all_mentions = self._load_all_mentions(entity_id)
        all_attributes = self._load_all_attributes(entity_id)
        all_relationships = self._load_relationships()
        voice_profiles = self._load_voice_profiles() if include_voice else {}
        vital_data = self._load_vital_status() if include_vital else {}

        for entity in entities:
            entry = self._build_entry(
                entity=entity,
                mentions=all_mentions.get(entity.id, []),
                attributes=all_attributes.get(entity.id, []),
                relationships=all_relationships,
                voice_profile=voice_profiles.get(entity.id),
                vital_status=vital_data.get(entity.id),
            )
            bible.entries.append(entry)

            # Contar por tipo
            etype = str(getattr(entity, "entity_type", "")).upper()
            if etype in ("CHARACTER", "PERSON", "PER"):
                bible.total_characters += 1
            elif etype in ("LOCATION", "LOC", "GPE", "PLACE"):
                bible.total_locations += 1
            elif etype in ("ORGANIZATION", "ORG"):
                bible.total_organizations += 1
            elif etype in ("OBJECT", "MISC"):
                bible.total_objects += 1
            else:
                bible.total_other += 1

        # Ordenar: personajes primero, luego por importancia y menciones
        importance_order = {"protagonist": 0, "main": 1, "secondary": 2, "minor": 3, "mentioned": 4}
        bible.entries.sort(key=lambda e: (
            0 if e.entity_type.upper() in ("CHARACTER", "PERSON", "PER") else 1,
            importance_order.get(e.importance.lower(), 5),
            -e.mention_count,
        ))

        return bible

    def _build_entry(
        self,
        entity,
        mentions: list,
        attributes: list,
        relationships: list,
        voice_profile: Optional[dict],
        vital_status: Optional[dict],
    ) -> EntityBibleEntry:
        """Construye una entrada de la biblia para una entidad."""
        entry = EntityBibleEntry(
            entity_id=entity.id,
            canonical_name=entity.canonical_name,
            entity_type=str(getattr(entity, "entity_type", "UNKNOWN")),
            importance=str(getattr(entity, "importance", "unknown")),
            aliases=list(entity.aliases) if entity.aliases else [],
            description=getattr(entity, "description", "") or "",
            mention_count=len(mentions),
        )

        # Capítulos donde aparece
        chapters = sorted(set(
            m.chapter_id for m in mentions
            if hasattr(m, "chapter_id") and m.chapter_id is not None
        ))
        entry.chapters_present = chapters
        if chapters:
            entry.first_chapter = chapters[0]
            entry.last_chapter = chapters[-1]

        # Atributos agrupados por categoría
        grouped_attrs: dict[str, list[dict]] = {}
        for attr in attributes:
            cat = str(getattr(attr, "category", "other"))
            if cat not in grouped_attrs:
                grouped_attrs[cat] = []
            grouped_attrs[cat].append({
                "key": getattr(attr, "key", ""),
                "value": getattr(attr, "value", ""),
                "confidence": getattr(attr, "confidence", 0.5),
                "chapter": getattr(attr, "chapter", None),
                "source_text": getattr(attr, "source_text", "")[:100] if getattr(attr, "source_text", "") else "",
            })
        entry.attributes = grouped_attrs

        # Relaciones (filtrar las que incluyen esta entidad)
        entity_rels = []
        for rel in relationships:
            source_id = rel.get("source_entity_id") or rel.get("entity_a_id", 0)
            target_id = rel.get("target_entity_id") or rel.get("entity_b_id", 0)

            if source_id == entity.id:
                entity_rels.append({
                    "related_entity_id": target_id,
                    "related_entity_name": rel.get("target_name") or rel.get("entity_b_name", ""),
                    "relation_type": rel.get("relation_type", ""),
                    "strength": rel.get("strength", ""),
                    "valence": rel.get("valence", ""),
                    "description": rel.get("description", ""),
                    "direction": "outgoing",
                })
            elif target_id == entity.id:
                entity_rels.append({
                    "related_entity_id": source_id,
                    "related_entity_name": rel.get("source_name") or rel.get("entity_a_name", ""),
                    "relation_type": rel.get("relation_type", ""),
                    "strength": rel.get("strength", ""),
                    "valence": rel.get("valence", ""),
                    "description": rel.get("description", ""),
                    "direction": "incoming",
                })
        entry.relationships = entity_rels

        # Vital status
        if vital_status:
            entry.vital_status = vital_status

        # Voice profile
        if voice_profile:
            entry.voice_profile = voice_profile

        return entry

    def _load_entities(self, entity_id: Optional[int] = None) -> list:
        """Carga entidades del proyecto."""
        try:
            from ..entities.repository import get_entity_repository
            repo = get_entity_repository()
            if entity_id:
                entity = repo.get_entity(entity_id)
                return [entity] if entity else []
            return repo.get_entities_by_project(self.project_id, active_only=True)
        except Exception as e:
            logger.warning(f"Error loading entities: {e}")
            return []

    def _load_all_mentions(self, entity_id: Optional[int] = None) -> dict:
        """Carga menciones agrupadas por entity_id."""
        result: dict[int, list] = {}
        try:
            from ..entities.repository import get_entity_repository
            repo = get_entity_repository()
            if entity_id:
                mentions = repo.get_mentions_by_entity(entity_id)
                result[entity_id] = mentions
            else:
                entities = repo.get_entities_by_project(self.project_id, active_only=True)
                for entity in entities:
                    mentions = repo.get_mentions_by_entity(entity.id)
                    result[entity.id] = mentions
        except Exception as e:
            logger.warning(f"Error loading mentions: {e}")
        return result

    def _load_all_attributes(self, entity_id: Optional[int] = None) -> dict:
        """Carga atributos agrupados por entity_id."""
        result: dict[int, list] = {}
        try:
            from ..nlp.attributes import get_attribute_extractor
            extractor = get_attribute_extractor()
            if entity_id:
                attrs = extractor.get_attributes_for_entity(entity_id)
                result[entity_id] = attrs
            else:
                from ..entities.repository import get_entity_repository
                repo = get_entity_repository()
                entities = repo.get_entities_by_project(self.project_id, active_only=True)
                for entity in entities:
                    attrs = extractor.get_attributes_for_entity(entity.id)
                    result[entity.id] = attrs
        except Exception as e:
            logger.debug(f"Error loading attributes: {e}")
        return result

    def _load_relationships(self) -> list[dict]:
        """Carga relaciones del proyecto."""
        try:
            from ..analysis.relationship_clustering import RelationshipClusteringEngine
            engine = RelationshipClusteringEngine(self.project_id)
            relations = engine.get_all_relations()
            return [r.to_dict() if hasattr(r, "to_dict") else r for r in relations]
        except Exception as e:
            logger.debug(f"Error loading relationships: {e}")
            return []

    def _load_voice_profiles(self) -> dict:
        """Carga perfiles de voz indexados por entity_id."""
        profiles: dict[int, dict] = {}
        try:
            from ..voice.profiles import VoiceProfiler
            profiler = VoiceProfiler()
            # El profiler necesita datos de diálogo, simplificar
            # Retornar dict vacío si no hay datos pre-calculados
        except Exception as e:
            logger.debug(f"Error loading voice profiles: {e}")
        return profiles

    def _load_vital_status(self) -> dict:
        """Carga estado vital indexado por entity_id."""
        vital: dict[int, dict] = {}
        try:
            from ..analysis.vital_status import VitalStatusAnalyzer
            analyzer = VitalStatusAnalyzer(self.project_id)
            reports = analyzer.get_all_reports()
            for report in reports:
                if hasattr(report, "entity_id") and hasattr(report, "to_dict"):
                    vital[report.entity_id] = report.to_dict()
        except Exception as e:
            logger.debug(f"Error loading vital status: {e}")
        return vital
