"""
Mixin de pipeline unificado: Phase 4: Attributes, relationships, interactions, knowledge, voice profiles.

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


class PipelineDeepExtractionMixin:
    """
    Mixin: Phase 4: Attributes, relationships, interactions, knowledge, voice profiles.

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    def _phase_4_deep_extraction(self, context: AnalysisContext) -> Result[None]:
        """
        Fase 4: Atributos, relaciones, conocimiento, voz.

        Parallelizable: Cada extractor es independiente.
        """
        phase_start = datetime.now()

        tasks = []

        if self.config.run_attributes and context.entities:
            tasks.append(("attributes", self._extract_attributes))

        if self.config.run_relationships and context.entities:
            tasks.append(("relationships", self._extract_relationships))

        if self.config.run_interactions and context.entities:
            tasks.append(("interactions", self._extract_interactions))

        if self.config.run_knowledge and context.entities:
            tasks.append(("knowledge", self._extract_knowledge))

        if self.config.run_voice_profiles and context.entities:
            tasks.append(("voice_profiles", self._extract_voice_profiles))

        # Ejecutar en paralelo si está configurado
        if self.config.parallel_extraction and len(tasks) > 1:
            self._run_parallel_tasks(tasks, context)
        else:
            for name, func in tasks:
                try:
                    func(context)
                except Exception as e:
                    logger.warning(f"{name} failed: {e}")

        context.phase_times["deep_extraction"] = (datetime.now() - phase_start).total_seconds()
        return Result.success(None)

    def _extract_attributes(self, context: AnalysisContext) -> None:
        """Extraer atributos de entidades usando el sistema multi-método con votación."""
        try:
            from ..entities.repository import get_entity_repository
            from ..nlp.attributes import get_attribute_extractor

            # Cargar menciones de todas las entidades para resolución de pronombres
            entity_mentions = []
            entity_repo = get_entity_repository()
            for entity in context.entities:
                mentions = entity_repo.get_mentions_by_entity(entity.id)
                for mention in mentions:
                    # Usar el nombre canónico para que _find_nearest_entity lo asocie correctamente
                    entity_mentions.append(
                        (entity.canonical_name, mention.start_char, mention.end_char)
                    )

            logger.debug(
                f"Loaded {len(entity_mentions)} mentions for "
                f"{len(context.entities)} entities for attribute extraction"
            )

            # Usar el extractor de atributos que soporta entity_mentions
            # min_confidence=0.4 para permitir atributos detectados por un solo método
            extractor = get_attribute_extractor(
                use_llm=self.config.use_llm,
                min_confidence=0.4,
            )

            all_attributes = []

            # Procesar por capítulos para mantener información de chapter_id
            if context.chapters:
                for ch in context.chapters:
                    chapter_num = ch.get("number", 1)
                    chapter_content = ch.get("content", "")
                    chapter_start = ch.get("start_char", 0)

                    if not chapter_content:
                        continue

                    # Filtrar menciones que están en este capítulo
                    chapter_mentions = [
                        (name, start - chapter_start, end - chapter_start)
                        for name, start, end in entity_mentions
                        if chapter_start <= start < ch.get("end_char", float("inf"))
                    ]

                    result = extractor.extract_attributes(
                        chapter_content,
                        entity_mentions=chapter_mentions if chapter_mentions else None,
                        chapter_id=chapter_num,
                    )

                    if result.is_success:
                        # Ajustar posiciones al texto completo
                        for attr in result.value.attributes:
                            attr.start_char += chapter_start
                            attr.end_char += chapter_start
                        all_attributes.extend(result.value.attributes)
                        logger.debug(
                            f"Chapter {chapter_num}: {len(result.value.attributes)} attributes"
                        )
            else:
                # Sin capítulos, procesar texto completo
                result = extractor.extract_attributes(
                    context.full_text,
                    entity_mentions=entity_mentions if entity_mentions else None,
                )
                if result.is_success:
                    all_attributes = result.value.attributes

            context.attributes = all_attributes
            context.stats["attributes_extracted"] = len(all_attributes)

            # Persistir
            self._persist_attributes(context)

            logger.info(f"Attribute extraction: {len(all_attributes)} attributes total")

        except Exception as e:
            logger.warning(f"Attribute extraction failed: {e}")

    def _extract_relationships(self, context: AnalysisContext) -> None:
        """Extraer relaciones entre personajes usando clustering multi-técnica."""
        logger.info("[RELATIONSHIPS] Iniciando extracción de relaciones...")
        logger.info(
            f"[RELATIONSHIPS] Entidades disponibles: {len(context.entities) if context.entities else 0}"
        )
        logger.info(
            f"[RELATIONSHIPS] Capítulos disponibles: {len(context.chapters) if context.chapters else 0}"
        )

        if not context.entities:
            logger.warning("[RELATIONSHIPS] Sin entidades - abortando extracción de relaciones")
            return

        if not context.chapters:
            logger.warning("[RELATIONSHIPS] Sin capítulos - abortando extracción de relaciones")
            return

        try:
            from ..analysis.relationship_clustering import (
                RelationshipClusteringEngine,
                extract_cooccurrences_from_chapters,
            )
            from ..nlp.embeddings import get_embeddings_model

            # Obtener modelo de embeddings (opcional)
            embedding_model = None
            try:
                embedding_model = get_embeddings_model()
                logger.debug("[RELATIONSHIPS] Modelo de embeddings cargado")
            except Exception as e:
                logger.debug(f"[RELATIONSHIPS] Embeddings no disponibles: {e}")

            engine = RelationshipClusteringEngine(
                use_embeddings=embedding_model is not None,
                embedding_model=embedding_model,
            )

            # Extraer co-ocurrencias de las menciones de entidades
            if context.chapters and context.entities:
                # Construir lista de menciones para co-ocurrencia
                entity_mentions = []
                entities_with_mentions = 0
                for entity in context.entities:
                    if hasattr(entity, "mentions") and entity.mentions:
                        entities_with_mentions += 1
                        for mention in entity.mentions:
                            entity_mentions.append(
                                {
                                    "entity_id": entity.id,
                                    "entity_name": entity.canonical_name,
                                    "start_char": mention.start_char
                                    if hasattr(mention, "start_char")
                                    else 0,
                                    "end_char": mention.end_char
                                    if hasattr(mention, "end_char")
                                    else 0,
                                }
                            )
                logger.info(
                    f"[RELATIONSHIPS] Entidades con menciones: {entities_with_mentions}/{len(context.entities)}"
                )
                logger.info(
                    f"[RELATIONSHIPS] Total menciones para co-ocurrencia: {len(entity_mentions)}"
                )

                # Preparar datos de capítulos
                chapters_data = [
                    {
                        "chapter_number": ch["number"],
                        "content": ch["content"],
                        "start_char": ch.get("start_char", 0),
                        "end_char": ch.get("end_char", len(ch["content"])),
                    }
                    for ch in context.chapters
                ]

                cooccurrences = extract_cooccurrences_from_chapters(
                    chapters=chapters_data,
                    entity_mentions=entity_mentions,
                    window_chars=500,
                )

                # Añadir co-ocurrencias al engine
                logger.info(f"[RELATIONSHIPS] Co-ocurrencias encontradas: {len(cooccurrences)}")
                for cooc in cooccurrences:
                    e1_name = next(
                        (e.canonical_name for e in context.entities if e.id == cooc.entity1_id),
                        str(cooc.entity1_id),
                    )
                    e2_name = next(
                        (e.canonical_name for e in context.entities if e.id == cooc.entity2_id),
                        str(cooc.entity2_id),
                    )
                    engine.add_cooccurrence(
                        entity1_id=cooc.entity1_id,
                        entity2_id=cooc.entity2_id,
                        entity1_name=e1_name,
                        entity2_name=e2_name,
                        chapter=cooc.chapter,
                        distance_chars=cooc.distance_chars,
                        context=cooc.context,
                    )

            # Ejecutar análisis
            result = engine.analyze()

            context.relationships = result.get("relations", [])
            context.stats["relationships_found"] = len(context.relationships)
            context.stats["character_clusters"] = len(result.get("clusters", []))

            logger.info(f"[RELATIONSHIPS] Relaciones detectadas: {len(context.relationships)}")
            logger.info(
                f"[RELATIONSHIPS] Clusters de personajes: {context.stats.get('character_clusters', 0)}"
            )

        except Exception as e:
            logger.error(f"[RELATIONSHIPS] Error en extracción: {e}", exc_info=True)

    def _extract_interactions(self, context: AnalysisContext) -> None:
        """
        Extraer interacciones entre personajes.

        Detecta:
        - Diálogos entre personajes
        - Acciones físicas (contacto, violencia, etc.)
        - Pensamientos sobre otros personajes
        - Tono de las interacciones (positivo/negativo/neutro)
        """
        if not context.entities or not context.chapters:
            return

        try:
            from ..interactions import (
                InteractionDetector,
                InteractionPatternAnalyzer,
            )

            # Crear lista de personajes conocidos
            character_names = [
                e.canonical_name
                for e in context.entities
                if hasattr(e, "entity_type")
                and str(e.entity_type).upper() in ("CHARACTER", "PERSON", "PER")
            ]

            # Añadir aliases
            character_aliases = {}
            for entity in context.entities:
                if hasattr(entity, "aliases"):
                    for alias in entity.aliases:
                        character_aliases[alias.lower()] = entity.canonical_name

            # Detector de interacciones
            detector = InteractionDetector(
                known_characters=character_names,
                character_aliases=character_aliases,
            )

            all_interactions = []

            # Detectar en cada capítulo
            for ch in context.chapters:
                chapter_num = ch.get("number", 1)
                content = ch.get("content", "")

                if not content:
                    continue

                interactions = detector.detect(
                    text=content,
                    chapter_id=chapter_num,
                )

                all_interactions.extend(interactions)

            # Convertir a diccionarios
            context.interactions = [
                i.to_dict() if hasattr(i, "to_dict") else i for i in all_interactions
            ]

            # Analizar patrones de interacción
            if all_interactions:
                pattern_analyzer = InteractionPatternAnalyzer(
                    interactions=all_interactions,
                    entities=context.entities,
                )

                patterns = pattern_analyzer.analyze()
                context.interaction_patterns = [
                    p.to_dict() if hasattr(p, "to_dict") else p for p in patterns
                ]

            context.stats["interactions_found"] = len(context.interactions)
            context.stats["interaction_patterns"] = len(context.interaction_patterns)

            logger.info(
                f"Interactions: {len(context.interactions)} interactions, "
                f"{len(context.interaction_patterns)} patterns"
            )

        except ImportError as e:
            logger.debug(f"Interactions module not available: {e}")
        except Exception as e:
            logger.warning(f"Interaction extraction failed: {e}")

    def _extract_knowledge(self, context: AnalysisContext) -> None:
        """
        Extraer matriz de conocimiento entre personajes.

        Analiza:
        - Menciones dirigidas (A habla de B)
        - Hechos que A conoce sobre B
        - Opiniones que A tiene de B
        - Intenciones de A respecto a B
        """
        try:
            from ..analysis.character_knowledge import CharacterKnowledgeAnalyzer

            analyzer = CharacterKnowledgeAnalyzer(project_id=context.project_id)

            # Registrar entidades con sus alias
            for entity in context.entities:
                aliases = []
                if hasattr(entity, "aliases") and entity.aliases:
                    aliases = entity.aliases
                analyzer.register_entity(
                    entity_id=entity.id, name=entity.canonical_name, aliases=aliases
                )

            # Analizar diálogos
            for dialogue in context.dialogues:
                speaker_name = dialogue.get("resolved_speaker") or dialogue.get("speaker_hint")
                if speaker_name:
                    # Buscar ID del speaker
                    speaker_id = context.entity_map.get(speaker_name.lower())
                    if speaker_id:
                        # Determinar capítulo del diálogo
                        chapter = 1
                        for ch in context.chapters:
                            if (
                                ch.get("start_char", 0)
                                <= dialogue.get("start_char", 0)
                                <= ch.get("end_char", float("inf"))
                            ):
                                chapter = ch["number"]
                                break

                        analyzer.analyze_dialogue(
                            speaker_id=speaker_id,
                            dialogue_text=dialogue.get("text", ""),
                            chapter=chapter,
                            start_char=dialogue.get("start_char", 0),
                        )

            # Analizar narración por capítulos
            for ch in context.chapters:
                content = ch.get("content", "")
                if content:
                    analyzer.analyze_narration(
                        text=content,
                        chapter=ch["number"],
                        start_char=ch.get("start_char", 0),
                    )
                    analyzer.analyze_intentions(
                        text=content,
                        chapter=ch["number"],
                        start_char=ch.get("start_char", 0),
                    )

            # Construir matriz de conocimiento
            knowledge_matrix = {}
            for e1 in context.entities:
                for e2 in context.entities:
                    if e1.id != e2.id:
                        report = analyzer.get_asymmetry_report(e1.id, e2.id)
                        key = f"{e1.id}_{e2.id}"
                        knowledge_matrix[key] = {
                            "source_id": e1.id,
                            "source_name": e1.canonical_name,
                            "target_id": e2.id,
                            "target_name": e2.canonical_name,
                            "mentions_count": report.a_mentions_b_count,
                            "knowledge_facts": [k.to_dict() for k in report.a_knows_about_b],
                            "opinion": report.a_opinion_of_b.to_dict()
                            if report.a_opinion_of_b
                            else None,
                            "intentions": [i.to_dict() for i in report.a_intentions_toward_b],
                        }

            context.knowledge_matrix = knowledge_matrix
            context.stats["knowledge_relations"] = len(knowledge_matrix)
            context.stats["mentions_found"] = len(analyzer.get_all_mentions())
            context.stats["opinions_detected"] = len(analyzer.get_all_opinions())
            context.stats["intentions_detected"] = len(analyzer.get_all_intentions())

        except Exception as e:
            logger.warning(f"Knowledge extraction failed: {e}")

    def _extract_voice_profiles(self, context: AnalysisContext) -> None:
        """
        Extraer perfiles de comportamiento usando LLM local.

        Usa el motor de inferencia de expectativas para:
        - Analizar rasgos de personalidad
        - Inferir valores y miedos
        - Generar expectativas comportamentales
        """
        if not self.config.use_llm:
            return

        try:
            from ..llm.expectation_inference import (
                ExpectationInferenceEngine,
                InferenceConfig,
                InferenceMethod,
            )

            # Configurar métodos según disponibilidad
            enabled_methods = [InferenceMethod.RULE_BASED]
            if self.config.use_llm:
                enabled_methods.extend(
                    [
                        InferenceMethod.LLAMA3_2,
                        InferenceMethod.MISTRAL,
                        InferenceMethod.QWEN2_5,
                    ]
                )
            enabled_methods.append(InferenceMethod.EMBEDDINGS)

            config = InferenceConfig(
                enabled_methods=enabled_methods,
                min_confidence=self.config.min_confidence,
                min_consensus=0.6,
                prioritize_speed=True,
            )

            engine = ExpectationInferenceEngine(config)

            if not engine.is_available:
                logger.info("No inference methods available for voice profiles")
                return

            # Filtrar entidades de tipo PERSON
            person_entities = [
                e
                for e in context.entities
                if hasattr(e, "entity_type") and str(e.entity_type).upper() == "PERSON"
            ]

            for entity in person_entities:
                # Recopilar muestras de texto relevantes al personaje
                text_samples = []
                chapter_numbers = []

                for ch in context.chapters:
                    content = ch.get("content", "")
                    entity_name = entity.canonical_name

                    # Buscar oraciones que mencionan al personaje
                    if entity_name.lower() in content.lower():
                        # Extraer contexto alrededor de las menciones
                        import re

                        sentences = re.split(r"[.!?]+", content)
                        for sent in sentences:
                            if entity_name.lower() in sent.lower():
                                text_samples.append(sent.strip())
                                chapter_numbers.append(ch["number"])

                        # Limitar muestras por capítulo
                        if len(text_samples) > 50:
                            break

                if not text_samples:
                    continue

                # Obtener atributos existentes del personaje
                existing_attrs = {}
                for attr in context.attributes:
                    if hasattr(attr, "entity_name") and attr.entity_name == entity.canonical_name:
                        key = attr.key.value if hasattr(attr.key, "value") else str(attr.key)
                        existing_attrs[key] = attr.value if hasattr(attr, "value") else str(attr)

                # Analizar personaje
                profile = engine.analyze_character(
                    character_id=entity.id,
                    character_name=entity.canonical_name,
                    text_samples=text_samples[:30],  # Limitar para rendimiento
                    chapter_numbers=chapter_numbers[:30],
                    existing_attributes=existing_attrs if existing_attrs else None,
                )

                if profile:
                    context.voice_profiles[entity.id] = profile.to_dict()

            context.stats["voice_profiles"] = len(context.voice_profiles)

        except ImportError:
            logger.debug("LLM module not available for voice profiles")
        except Exception as e:
            logger.warning(f"Voice profile extraction failed: {e}")
