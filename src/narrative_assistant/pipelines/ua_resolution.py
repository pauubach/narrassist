"""
Mixin de pipeline unificado: Phase 3: Coreference, entity fusion, dialogue attribution.

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

logger = logging.getLogger(__name__)


class PipelineResolutionMixin:
    """
    Mixin: Phase 3: Coreference, entity fusion, dialogue attribution.

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    if TYPE_CHECKING:
        from .unified_analysis import UnifiedConfig

        config: UnifiedConfig

    def _phase_3_resolution(self, context: AnalysisContext) -> Result[None]:
        """
        Fase 3: Correferencias, fusión de entidades, atribución de diálogos.
        """
        phase_start = datetime.now()

        try:
            # 3.1 Correferencias
            if self.config.run_coreference and context.entities:
                self._run_coreference(context)
                self._persist_coref_voting_details(context)

            # 3.2 Fusión de entidades
            if self.config.run_entity_fusion and context.entities:
                self._run_entity_fusion(context)

            # 3.3 Atribución de diálogos (usa correferencias)
            if self.config.run_dialogue_detection and context.dialogues:
                self._attribute_dialogues(context)

            context.phase_times["resolution"] = (datetime.now() - phase_start).total_seconds()
            return Result.success(None)

        except Exception as e:
            return Result.failure(
                NarrativeError(
                    message=f"Resolution failed: {str(e)}", severity=ErrorSeverity.RECOVERABLE
                )
            )

    def _run_coreference(self, context: AnalysisContext) -> None:
        """Ejecutar resolución de correferencias."""
        try:
            from ..nlp.coreference_resolver import (
                CorefConfig,
                build_pronoun_resolution_map,
                resolve_coreferences_voting,
            )

            # Preparar datos de capítulos para correferencia
            chapters_data = None
            if context.chapters:
                chapters_data = [
                    {
                        "number": ch["number"],
                        "content": ch["content"],
                        "start_char": ch["start_char"],
                        "end_char": ch["end_char"],
                    }
                    for ch in context.chapters
                ]

            coref_config = CorefConfig(
                use_llm_for_coref=self.config.use_llm,
            )

            result = resolve_coreferences_voting(
                context.full_text,
                chapters=chapters_data,
                config=coref_config,
            )

            if result.chains:
                context.coreference_chains = result.chains

                # Crear mapa de menciones a entidades
                for chain in result.chains:
                    entity_name = chain.main_mention
                    for mention in chain.mentions:
                        context.mention_to_entity[mention.text.lower()] = entity_name

                # Reusar mapa de pronombres por posición para desambiguación contextual.
                context.pronoun_resolution_map = build_pronoun_resolution_map(result)

                context.stats["coreference_chains"] = len(result.chains)

                # Almacenar detalles de votación para exposición en API
                if hasattr(result, "voting_details") and result.voting_details:
                    context.coref_voting_details = result.voting_details

        except Exception as e:
            logger.warning(f"Coreference resolution failed: {e}")

    def _persist_coref_voting_details(self, context: AnalysisContext) -> None:
        """Persiste los detalles de votación de correferencia como menciones con metadata."""
        if not context.coref_voting_details or not context.coreference_chains:
            return

        try:
            import json

            from ..entities.models import EntityMention
            from ..entities.repository import get_entity_repository

            entity_repo = get_entity_repository()

            # Mapear nombres de entidad a entity_id
            entity_name_to_id: dict[str, int] = {}
            for entity in context.entities:
                entity_name_to_id[entity.canonical_name.lower()] = entity.id
                for alias in entity.aliases or []:
                    entity_name_to_id[alias.lower()] = entity.id

            mentions_to_save = []
            saved_count = 0
            mention_increments: dict[int, int] = {}
            entity_lookup = {e.id: e for e in context.entities if getattr(e, "id", None)}

            for (start, end), detail in context.coref_voting_details.items():
                # Buscar entity_id del antecedente resuelto
                resolved_lower = detail.resolved_to.lower()
                entity_id = entity_name_to_id.get(resolved_lower)

                if not entity_id:
                    continue

                # Buscar chapter_id
                chapter_id = None
                if context.chapters:
                    for ch in context.chapters:
                        ch_start = ch.get("start_char", 0)
                        ch_end = ch.get("end_char", len(context.full_text))
                        if ch_start <= start < ch_end:
                            chapter_id = ch.get("db_id")
                            break

                # Extraer contexto
                ctx_start = max(0, start - 50)
                ctx_end = min(len(context.full_text), end + 50)

                # Serializar voting detail como metadata
                metadata_json = json.dumps(detail.to_dict(), ensure_ascii=False)

                mention = EntityMention(
                    entity_id=entity_id,
                    chapter_id=chapter_id,
                    surface_form=detail.anaphor_text,
                    start_char=start,
                    end_char=end,
                    context_before=context.full_text[ctx_start:start],
                    context_after=context.full_text[end:ctx_end],
                    confidence=detail.final_score,
                    source="coref",
                    metadata=metadata_json,
                )
                mentions_to_save.append(mention)

            if mentions_to_save:
                saved_count = entity_repo.create_mentions_batch(mentions_to_save)
                if saved_count:
                    for mention in mentions_to_save:
                        mention_increments[mention.entity_id] = (
                            mention_increments.get(mention.entity_id, 0) + 1
                        )
                        entity_obj = entity_lookup.get(mention.entity_id)
                        if entity_obj:
                            entity_obj.mention_count = (entity_obj.mention_count or 0) + 1
                    logger.info(f"Coref voting: {saved_count} mentions with voting metadata saved")

            if mention_increments:
                for entity_id, delta in mention_increments.items():
                    try:
                        entity_repo.increment_mention_count(entity_id, delta)
                    except Exception as inc_err:
                        logger.warning(
                            f"Failed to increment mention_count after coref for entity {entity_id}: {inc_err}"
                        )

        except Exception as e:
            logger.warning(f"Failed to persist coref voting details: {e}")

    def _run_entity_fusion(self, context: AnalysisContext) -> None:
        """Ejecutar fusión de entidades similares."""
        try:
            from ..entities.fusion import run_automatic_fusion

            # Pasar cadenas de correferencia para mejorar las sugerencias de fusión
            # Esto permite fusionar casos como "el Magistral" ↔ "Fermín" que
            # tienen baja similaridad textual pero son la misma persona según correferencia
            coref_chains = getattr(context, "coreference_chains", None)

            result = run_automatic_fusion(
                context.project_id,
                session_id=context.session_id,
                coreference_chains=coref_chains,
            )

            if result.is_success:
                merged_count = result.value or 0
                context.stats["entities_merged"] = merged_count

                # Recargar entidades
                if merged_count > 0:
                    from ..entities.repository import get_entity_repository

                    entity_repo = get_entity_repository()
                    context.entities = entity_repo.get_entities_by_project(context.project_id)
                    context.entity_map = {e.canonical_name.lower(): e.id for e in context.entities}

        except Exception as e:
            logger.warning(f"Entity fusion failed: {e}")

    def _attribute_dialogues(self, context: AnalysisContext) -> None:
        """
        Atribuir diálogos a personajes usando múltiples estrategias:
        1. Detección explícita (verbo de habla + nombre)
        2. Correferencias (si hay pronombre, resolver a entidad)
        3. Alternancia (A habla, B responde, probablemente A sigue)
        4. Proximidad (personaje mencionado cerca del diálogo)
        """
        try:
            from types import SimpleNamespace

            from ..entities.repository import get_entity_repository
            from ..voice.speaker_attribution import SpeakerAttributor

            # Filtrar entidades de tipo personaje
            character_entities = [
                e
                for e in context.entities
                if hasattr(e, "entity_type")
                and (
                    (
                        e.entity_type.value
                        if hasattr(e.entity_type, "value")
                        else str(e.entity_type)
                    ).upper()
                    in ("CHARACTER", "PERSON", "PER")
                )
            ]

            if not character_entities:
                logger.debug("No character entities found, skipping speaker attribution")
                return

            # Crear atribuidor con entidades completas (necesita .id, .canonical_name, .aliases)
            attributor = SpeakerAttributor(entities=character_entities)

            # Cargar menciones de entidades para resolución por proximidad
            entity_mentions: list[tuple[int, int, int]] = []
            try:
                entity_repo = get_entity_repository()
                for entity in character_entities:
                    mentions = entity_repo.get_mentions_by_entity(entity.id)
                    for mention in mentions:
                        entity_mentions.append((entity.id, mention.start_char, mention.end_char))
            except Exception as e:
                logger.debug(f"Could not load entity mentions: {e}")

            def _normalize_name(value: str) -> str:
                return " ".join((value or "").strip().lower().split())

            # Índice de nombres/aliases para mapear resoluciones de coref a entidades reales.
            canonical_by_norm: dict[str, tuple[str, int | None]] = {}
            for entity in character_entities:
                entity_id = getattr(entity, "id", None)
                canonical_name = getattr(entity, "canonical_name", None) or getattr(
                    entity, "name", ""
                )
                canonical_name = (canonical_name or "").strip()
                if canonical_name:
                    canonical_by_norm[_normalize_name(canonical_name)] = (
                        canonical_name,
                        entity_id,
                    )
                for alias in getattr(entity, "aliases", []) or []:
                    alias_norm = _normalize_name(alias)
                    if alias_norm and alias_norm not in canonical_by_norm:
                        canonical_by_norm[alias_norm] = (canonical_name or alias, entity_id)

            def _resolve_to_character(name: str) -> tuple[str, int | None]:
                normalized = _normalize_name(name)
                if not normalized:
                    return name, None

                direct = canonical_by_norm.get(normalized)
                if direct:
                    return direct

                # Fallback tolerante para casos "Don Ramiro" vs "Ramiro Estébanez".
                for key, resolved in canonical_by_norm.items():
                    if normalized in key or key in normalized:
                        return resolved

                return name, None

            pronoun_resolution_map: dict[tuple[int, int], str] = (
                getattr(context, "pronoun_resolution_map", {}) or {}
            )
            pronoun_hints = {
                "el",
                "él",
                "ella",
                "ellos",
                "ellas",
                "le",
                "les",
                "lo",
                "la",
                "los",
                "las",
                "su",
                "sus",
            }

            def _resolve_pronoun_near_dialogue(dialogue_data: dict) -> str | None:
                if not pronoun_resolution_map:
                    return None

                start = int(dialogue_data.get("start_char", 0) or 0)
                end = int(dialogue_data.get("end_char", start) or start)
                best_name: str | None = None
                best_distance: int | None = None

                for (m_start, m_end), resolved_name in pronoun_resolution_map.items():
                    if not resolved_name:
                        continue

                    if start <= m_start <= end or start <= m_end <= end:
                        distance = 0
                    elif end < m_start <= end + 120:
                        distance = m_start - end
                    elif start - 120 <= m_end < start:
                        distance = start - m_end
                    else:
                        continue

                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        best_name = resolved_name

                return best_name

            # Convertir diálogos dict a objetos para compatibilidad con getattr()
            dialogue_objects = []
            for d in context.dialogues:
                dialogue_objects.append(
                    SimpleNamespace(
                        text=d.get("text", ""),
                        start_char=d.get("start_char", 0),
                        end_char=d.get("end_char", 0),
                        chapter=d.get("chapter", 1),
                        attribution_text=d.get("attribution_text", ""),
                        speaker_hint=d.get("speaker_hint", ""),
                    )
                )

            # Atribuir diálogos
            attributions = attributor.attribute_dialogues(
                dialogues=dialogue_objects,
                entity_mentions=entity_mentions if entity_mentions else None,
                full_text=context.full_text,
            )

            # Mapear resultados de vuelta a los dicts de context.dialogues
            attr_by_start = {a.start_char: a for a in attributions}
            for dialogue in context.dialogues:
                start = dialogue.get("start_char", -1)
                attr = attr_by_start.get(start)
                if attr and attr.speaker_name:
                    dialogue["resolved_speaker"] = attr.speaker_name
                    dialogue["attribution_confidence"] = attr.confidence.value
                    dialogue["attribution_method"] = attr.attribution_method.value
                    if attr.speaker_id is not None:
                        dialogue["speaker_id"] = attr.speaker_id

            # Resolver con correferencias para los no atribuidos
            for dialogue in context.dialogues:
                if not dialogue.get("resolved_speaker"):
                    speaker = (dialogue.get("speaker_hint") or "").strip()
                    if speaker:
                        speaker_lower = _normalize_name(speaker)
                        resolved_name: str | None = None
                        method = "hint_only"

                        if speaker_lower in context.mention_to_entity:
                            resolved_name = context.mention_to_entity[speaker_lower]
                            method = "coreference"
                        elif speaker_lower in pronoun_hints:
                            resolved_name = _resolve_pronoun_near_dialogue(dialogue)
                            if resolved_name:
                                method = "coreference_pronoun"

                        canonical_name, speaker_id = _resolve_to_character(resolved_name or speaker)
                        dialogue["resolved_speaker"] = canonical_name
                        dialogue["attribution_method"] = method
                        if speaker_id is not None:
                            dialogue["speaker_id"] = speaker_id
                        if method.startswith("coreference"):
                            dialogue["attribution_confidence"] = dialogue.get(
                                "attribution_confidence", "medium"
                            )

            # Aplicar correcciones del usuario (override con máxima confianza)
            try:
                from ..persistence.database import get_database

                db = get_database()
                corrections = db.fetchall(
                    """
                    SELECT sc.chapter_number, sc.dialogue_start_char, sc.dialogue_end_char,
                           sc.corrected_speaker_id, e.name as corrected_speaker_name
                    FROM speaker_corrections sc
                    JOIN entities e ON e.id = sc.corrected_speaker_id
                    WHERE sc.project_id = ?
                    """,
                    (context.project_id,),
                )

                corrections_applied = 0
                for corr in corrections:
                    for dialogue in context.dialogues:
                        if (
                            dialogue.get("chapter") == corr["chapter_number"]
                            and dialogue.get("start_char") == corr["dialogue_start_char"]
                            and dialogue.get("end_char") == corr["dialogue_end_char"]
                        ):
                            dialogue["resolved_speaker"] = corr["corrected_speaker_name"]
                            dialogue["speaker_id"] = corr["corrected_speaker_id"]
                            dialogue["attribution_confidence"] = "high"
                            dialogue["attribution_method"] = "user_correction"
                            corrections_applied += 1
                            break

                if corrections_applied > 0:
                    logger.info(f"Applied {corrections_applied} user speaker corrections")
            except Exception as e:
                logger.debug(f"Could not apply speaker corrections: {e}")

            # Estadísticas
            attributed = sum(1 for d in context.dialogues if d.get("resolved_speaker"))
            context.stats["dialogues_attributed"] = attributed
            context.stats["dialogues_total"] = len(context.dialogues)

        except ImportError:
            # Fallback al método básico
            for dialogue in context.dialogues:
                speaker = dialogue.get("speaker_hint", "")
                if speaker:
                    speaker_lower = speaker.lower()
                    if speaker_lower in context.mention_to_entity:
                        resolved = context.mention_to_entity[speaker_lower]
                        dialogue["resolved_speaker"] = resolved
                    else:
                        dialogue["resolved_speaker"] = speaker
        except Exception as e:
            logger.warning(f"Advanced dialogue attribution failed: {e}")
