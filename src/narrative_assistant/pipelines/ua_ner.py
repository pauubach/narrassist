"""
Mixin de pipeline unificado: Phase 2: NER extraction and temporal markers.

Extraido de unified_analysis.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .unified_analysis import AnalysisContext

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

import unicodedata


def _normalize_key(text: str) -> str:
    """Normaliza un nombre eliminando diacriticos."""
    nfkd = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


logger = logging.getLogger(__name__)


class PipelineNERMixin:
    """
    Mixin: Phase 2: NER extraction and temporal markers.

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    def _phase_2_base_extraction(self, context: AnalysisContext) -> Result[None]:
        """
        Fase 2: NER mejorado con dialogue hints.

        Optimización: Los speaker_hints de diálogos confirman entidades PERSON.
        """
        phase_start = datetime.now()

        try:
            if self.config.run_ner:
                self._run_enhanced_ner(context)

            if self.config.run_temporal:
                self._extract_temporal_markers(context)

            context.phase_times["base_extraction"] = (datetime.now() - phase_start).total_seconds()
            return Result.success(None)

        except Exception as e:
            return Result.failure(
                NarrativeError(
                    message=f"Base extraction failed: {str(e)}", severity=ErrorSeverity.RECOVERABLE
                )
            )

    def _run_enhanced_ner(self, context: AnalysisContext) -> None:
        """
        NER mejorado con speaker hints de diálogos y procesamiento por capítulos.

        Los speaker hints ayudan a:
        1. Confirmar entidades PERSON (boost de confianza)
        2. Descubrir entidades no detectadas por spaCy

        Este método:
        1. Procesa NER capítulo por capítulo (evita cargar todo el texto en spaCy)
        2. Agrupa las menciones por nombre canónico
        3. Crea UNA entidad por nombre único
        4. Guarda TODAS las menciones en entity_mentions

        Optimización de memoria:
        - Documentos con capítulos: procesa cada capítulo por separado
        - Documentos sin capítulos o pequeños (<100k chars): procesa full_text
        - Capítulos muy grandes (>max_chapter_chars_for_chunking): usa chunk_for_spacy()
        """
        try:
            from ..entities.models import Entity, EntityImportance, EntityMention, EntityType
            from ..entities.repository import get_entity_repository
            from ..nlp.ner import NERExtractor
            from ..persistence.chapter import ChapterRepository

            entity_repo = get_entity_repository()

            # Limpiar entidades anteriores antes de re-analizar
            # Esto también elimina las menciones gracias a ON DELETE CASCADE
            deleted_count = entity_repo.delete_entities_by_project(context.project_id)
            if deleted_count > 0:
                logger.info(f"Cleared {deleted_count} previous entities before NER")

            extractor = NERExtractor()

            # Decidir estrategia de procesamiento
            extracted_mentions = self._extract_ner_with_chunking(extractor, context)

            if not extracted_mentions:
                logger.info("No entities extracted from NER")
                return

            if extracted_mentions:
                # Obtener capítulos de la base de datos para mapear posiciones a chapter_id
                chapter_repo = ChapterRepository()
                db_chapters = chapter_repo.get_by_project(context.project_id)

                def find_chapter_id(char_position: int) -> int | None:
                    """Encuentra el chapter_id de la BD dado una posición de carácter."""
                    for ch in db_chapters:
                        if ch.start_char <= char_position < ch.end_char:
                            return ch.id
                    return None

                # Agrupar menciones por nombre canónico (case-insensitive)
                # Cada grupo tendrá: label, todas las menciones, confianza máxima
                from collections import defaultdict

                entity_groups: dict[str, dict] = defaultdict(
                    lambda: {
                        "label": None,
                        "mentions": [],
                        "max_confidence": 0.0,
                        "canonical_text": None,  # Texto original más largo/completo
                        "surface_variants": set(),  # Variantes observadas para aliases
                    }
                )

                for mention in extracted_mentions:
                    raw_canonical = mention.canonical_form or mention.text.strip().lower()
                    # Clave normalizada sin diacríticos para agrupar variantes
                    norm_key = _normalize_key(raw_canonical)
                    group = entity_groups[norm_key]

                    # Guardar el label (todos deberían ser iguales para el mismo nombre)
                    if group["label"] is None:
                        group["label"] = mention.label

                    # Guardar el texto original (preferir el más largo/completo)
                    surface = mention.text.strip()
                    if group["canonical_text"] is None or len(surface) > len(
                        group["canonical_text"]
                    ):
                        group["canonical_text"] = surface

                    # Registrar variante de superficie para aliases
                    group["surface_variants"].add(surface)

                    # Actualizar confianza máxima
                    group["max_confidence"] = max(group["max_confidence"], mention.confidence)

                    # Añadir la mención con su posición
                    group["mentions"].append(
                        {
                            "surface_form": surface,
                            "start_char": mention.start_char,
                            "end_char": mention.end_char,
                            "confidence": mention.confidence,
                            "source": mention.source,
                        }
                    )

                # Boost de confianza para entidades confirmadas por diálogos
                for _position, speaker in context.speaker_hints.items():
                    speaker_key = _normalize_key(speaker)
                    if speaker_key in entity_groups:
                        entity_groups[speaker_key]["max_confidence"] = min(
                            1.0, entity_groups[speaker_key]["max_confidence"] + 0.1
                        )
                        logger.debug(
                            f"Boosted confidence for '{speaker}' from dialogue attribution"
                        )

                # Convertir y persistir entidades
                persisted = []
                total_mentions_saved = 0
                mention_increments: dict[int, int] = {}

                for canonical_name, group in entity_groups.items():
                    # Convertir label a EntityType
                    label = group["label"]
                    label_str = str(label.value if hasattr(label, "value") else label).upper()
                    # Heurística para MISC: si parece nombre propio (2-3 palabras capitalizadas), es CHARACTER
                    canonical_text = group.get("canonical_text") or canonical_name
                    if label_str == "PER":
                        entity_type = EntityType.CHARACTER
                    elif label_str == "LOC":
                        entity_type = EntityType.LOCATION
                    elif label_str == "ORG":
                        entity_type = EntityType.ORGANIZATION
                    elif label_str == "MISC":
                        # Intentar disambiguar MISC: nombres propios → CHARACTER
                        ct_words = canonical_text.split()
                        if 1 <= len(ct_words) <= 3 and all(w[0].isupper() for w in ct_words if w):
                            entity_type = EntityType.CHARACTER
                        else:
                            entity_type = EntityType.CONCEPT
                    else:
                        entity_type = EntityType.CONCEPT

                    # Construir aliases a partir de variantes de superficie observadas
                    final_canonical = group["canonical_text"] or canonical_name
                    aliases = sorted(v for v in group["surface_variants"] if v != final_canonical)

                    # Crear Entity object con el nombre canónico más completo
                    entity = Entity(
                        id=None,
                        project_id=context.project_id,
                        entity_type=entity_type,
                        canonical_name=final_canonical,
                        aliases=aliases,
                        importance=EntityImportance.PRIMARY
                        if group["max_confidence"] > 0.8
                        else EntityImportance.SECONDARY,
                    )

                    try:
                        entity_id = entity_repo.create_entity(entity)
                        if entity_id:
                            entity.id = entity_id
                            persisted.append(entity)

                            # Crear menciones para esta entidad
                            mentions_to_save = []
                            for m in group["mentions"]:
                                chapter_id = find_chapter_id(m["start_char"])

                                # Extraer contexto (50 chars antes y después)
                                context_start = max(0, m["start_char"] - 50)
                                context_end = min(len(context.full_text), m["end_char"] + 50)
                                context_before = context.full_text[context_start : m["start_char"]]
                                context_after = context.full_text[m["end_char"] : context_end]

                                mention = EntityMention(
                                    entity_id=entity_id,
                                    chapter_id=chapter_id,
                                    surface_form=m["surface_form"],
                                    start_char=m["start_char"],
                                    end_char=m["end_char"],
                                    context_before=context_before,
                                    context_after=context_after,
                                    confidence=m["confidence"],
                                    source=m["source"],
                                )
                                mentions_to_save.append(mention)

                            # Guardar menciones en batch
                            if mentions_to_save:
                                saved_count = entity_repo.create_mentions_batch(mentions_to_save)
                                total_mentions_saved += saved_count
                                if saved_count:
                                    mention_increments[entity_id] = (
                                        mention_increments.get(entity_id, 0) + saved_count
                                    )
                                    entity.mention_count = (entity.mention_count or 0) + saved_count
                                    logger.debug(
                                        f"Saved {saved_count} mentions for entity '{entity.canonical_name}'"
                                    )

                    except Exception as e:
                        logger.debug(f"Failed to persist entity '{canonical_name}': {e}")

                if mention_increments:
                    for entity_id, delta in mention_increments.items():
                        try:
                            entity_repo.increment_mention_count(entity_id, delta)
                        except Exception as inc_err:
                            logger.warning(
                                f"Failed to increment mention_count for entity {entity_id}: {inc_err}"
                            )

                context.entities = persisted
                context.entity_map = {e.canonical_name.lower(): e.id for e in persisted}
                context.stats["entities_detected"] = len(persisted)
                context.stats["mentions_saved"] = total_mentions_saved

                logger.info(
                    f"NER: {len(persisted)} entities, {total_mentions_saved} mentions saved"
                )

        except Exception as e:
            logger.warning(f"Enhanced NER failed: {e}")
            context.errors.append(
                NarrativeError(message=f"NER failed: {str(e)}", severity=ErrorSeverity.RECOVERABLE)
            )

    def _extract_ner_with_chunking(self, extractor, context: AnalysisContext) -> list:
        """
        Extrae entidades usando NER con procesamiento por capítulos.

        Estrategia:
        - Si hay capítulos, procesa cada uno por separado para limitar
          el pico de memoria de spaCy (Doc objects son grandes).
        - Ajusta char offsets al texto completo.
        - Para documentos sin capítulos o muy pequeños, procesa de una vez.

        Args:
            extractor: NERExtractor instance
            context: AnalysisContext con full_text y chapters

        Returns:
            Lista de ExtractedEntity con posiciones globales.
        """
        total_chars = len(context.full_text)

        # Documentos pequeños (<100k chars) o sin capítulos: procesar de una vez
        if total_chars < self.config.max_chapter_chars_for_chunking or not context.chapters:
            logger.info(f"NER: processing full text ({total_chars} chars)")
            result = extractor.extract_entities(context.full_text)
            if result.is_success:
                return result.value.entities if hasattr(result.value, "entities") else []
            return []

        # Documentos grandes con capítulos: procesar capítulo por capítulo
        logger.info(
            f"NER: processing {len(context.chapters)} chapters separately "
            f"(total {total_chars} chars) for memory efficiency"
        )

        all_mentions = []
        for ch in context.chapters:
            chapter_content = ch.get("content", "")
            chapter_start = ch.get("start_char", 0)
            chapter_num = ch.get("number", 0)

            if not chapter_content.strip():
                continue

            # Procesar este capítulo
            result = extractor.extract_entities(chapter_content)

            if result.is_success:
                chapter_entities = (
                    result.value.entities if hasattr(result.value, "entities") else []
                )

                # Ajustar posiciones al texto completo (global offsets)
                for entity in chapter_entities:
                    entity.start_char += chapter_start
                    entity.end_char += chapter_start

                all_mentions.extend(chapter_entities)
                logger.debug(
                    f"NER chapter {chapter_num}: "
                    f"{len(chapter_entities)} entities from {len(chapter_content)} chars"
                )
            else:
                logger.warning(f"NER failed for chapter {chapter_num}")

            # Limpiar memoria GPU entre capítulos en sistemas con poca VRAM
            self._clear_gpu_memory_if_needed()

        logger.info(
            f"NER chunked extraction: {len(all_mentions)} total mentions "
            f"from {len(context.chapters)} chapters"
        )
        return all_mentions

    def _extract_temporal_markers(self, context: AnalysisContext) -> None:
        """
        Extraer marcadores temporales del texto.

        Detecta:
        - Fechas absolutas (15 de marzo, 1985)
        - Tiempos relativos (dos días después, la semana anterior)
        - Duraciones (durante tres horas)
        - Secuencias (primero, luego, finalmente)
        """
        try:
            from ..temporal.markers import TemporalMarkerExtractor

            extractor = TemporalMarkerExtractor()

            all_markers = []

            # Extraer por capítulo para contexto
            if context.chapters:
                for ch in context.chapters:
                    chapter_num = ch.get("number", 1)
                    content = ch.get("content", "")
                    start_char = ch.get("start_char", 0)

                    markers = extractor.extract(
                        text=content,
                        chapter_id=chapter_num,
                        offset=start_char,
                    )

                    all_markers.extend(markers)
            else:
                # Sin capítulos, analizar texto completo
                all_markers = extractor.extract(context.full_text)

            context.temporal_markers = [
                m.to_dict() if hasattr(m, "to_dict") else m for m in all_markers
            ]

            context.stats["temporal_markers"] = len(context.temporal_markers)
            logger.info(f"Extracted {len(context.temporal_markers)} temporal markers")

        except ImportError as e:
            logger.debug(f"Temporal marker extractor not available: {e}")
        except Exception as e:
            logger.warning(f"Temporal marker extraction failed: {e}")
