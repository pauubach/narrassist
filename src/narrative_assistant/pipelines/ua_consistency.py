"""
Mixin de pipeline unificado: Phase 6: Consistency checks (attributes, temporal, focalization, voice, emotional, sentiment).

Extraido de unified_analysis.py para reducir complejidad del monolito.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .unified_analysis import AnalysisContext

from dataclasses import dataclass

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

logger = logging.getLogger(__name__)


@dataclass
class _HeuristicFocalizationViolation:
    """Violación de focalización detectada por heurística (sin DB)."""

    violation_type: str
    declared_focalizer: str
    text_excerpt: str
    explanation: str
    chapter: int
    position: int
    confidence: float = 0.7


class PipelineConsistencyMixin:
    """
    Mixin: Phase 6: Consistency checks (attributes, temporal, focalization, voice, emotional, sentiment).

    Requiere que la clase que hereda tenga:
    - self.config (UnifiedConfig)
    - self._memory_monitor (MemoryMonitor)
    """

    if TYPE_CHECKING:
        from .unified_analysis import UnifiedConfig

        config: UnifiedConfig

    def _phase_6_consistency(self, context: AnalysisContext) -> Result[None]:
        """Fase 6: Análisis de consistencia."""
        phase_start = datetime.now()

        try:
            if self.config.run_consistency and context.attributes:
                self._run_attribute_consistency(context)

            if self.config.run_temporal_consistency and context.temporal_markers:
                self._run_temporal_consistency(context)

            if self.config.run_focalization and context.chapters:
                self._run_focalization_consistency(context)

            if self.config.run_voice_deviations and context.voice_profiles:
                self._run_voice_deviation_detection(context)

            if self.config.run_emotional and context.chapters:
                self._run_emotional_coherence(context)

            if self.config.run_vital_status and context.entities and context.chapters:
                self._run_vital_status_check(context)

            if self.config.run_character_location and context.entities and context.chapters:
                self._run_character_location_check(context)

            if self.config.run_ooc_detection and context.entities and context.chapters:
                self._run_ooc_detection(context)

            if self.config.run_chekhov and context.entities and context.chapters:
                self._run_chekhov_check(context)

            if self.config.run_sentiment and context.chapters:
                self._run_sentiment_analysis(context)

            if self.config.run_character_profiling and context.entities and context.chapters:
                self._run_shallow_character_detection(context)

            context.phase_times["consistency"] = (datetime.now() - phase_start).total_seconds()
            return Result.success(None)

        except Exception as e:
            return Result.failure(
                NarrativeError(
                    message=f"Consistency check failed: {str(e)}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
            )

    def _run_attribute_consistency(self, context: AnalysisContext) -> None:
        """Verificar consistencia de atributos."""
        try:
            from ..analysis.attribute_consistency import AttributeConsistencyChecker

            checker = AttributeConsistencyChecker()
            result = checker.check_consistency(context.attributes)

            if result.is_success and result.value is not None:
                context.inconsistencies = result.value
                context.stats["inconsistencies"] = len(context.inconsistencies)

        except Exception as e:
            logger.warning(f"Attribute consistency check failed: {e}")

    def _run_temporal_consistency(self, context: AnalysisContext) -> None:
        """Verificar consistencia temporal usando marcadores detectados."""
        if not context.temporal_markers:
            return

        try:
            from ..temporal.inconsistencies import (
                TemporalDetectionConfig,
                VotingTemporalChecker,
            )
            from ..temporal.markers import TemporalMarker
            from ..temporal.timeline import TimelineBuilder

            # Filtrar solo TemporalMarker objects (no dicts)
            markers = [m for m in context.temporal_markers if isinstance(m, TemporalMarker)]
            if not markers:
                logger.debug("No TemporalMarker objects available for consistency check")
                return

            # Construir timeline desde marcadores
            builder = TimelineBuilder()
            chapter_data = [
                {
                    "number": ch.get("number", i + 1)
                    if isinstance(ch, dict)
                    else getattr(ch, "chapter_number", i + 1),
                    "title": ch.get("title", "")
                    if isinstance(ch, dict)
                    else getattr(ch, "title", ""),
                    "start_position": ch.get("start_char", 0)
                    if isinstance(ch, dict)
                    else getattr(ch, "start_char", 0),
                    "content": ch.get("content", "")
                    if isinstance(ch, dict)
                    else getattr(ch, "content", ""),
                }
                for i, ch in enumerate(context.chapters)
            ]
            timeline = builder.build_from_markers(markers, chapter_data)

            # Configurar sin LLM por defecto (rápido)
            config = TemporalDetectionConfig(use_llm=self.config.use_llm)

            # Ejecutar verificación con votación
            checker = VotingTemporalChecker(config)
            result = checker.check(
                timeline=timeline,
                markers=markers,
                text=context.full_text,
            )

            if result.inconsistencies:
                context.stats["temporal_inconsistencies"] = len(result.inconsistencies)
                logger.info(f"Found {len(result.inconsistencies)} temporal inconsistencies")

                # Almacenar para generación de alertas
                context.temporal_inconsistencies.extend(result.inconsistencies)

        except ImportError as e:
            logger.debug(f"Temporal inconsistency module not available: {e}")
        except Exception as e:
            logger.warning(f"Temporal consistency check failed: {e}")

    def _run_focalization_consistency(self, context: AnalysisContext) -> None:
        """Verificar violaciones de focalización (DB o heurística)."""
        try:
            from ..focalization.declaration import get_focalization_service
            from ..focalization.violations import FocalizationViolationDetector

            service = get_focalization_service(use_sqlite=True)
            declarations = service.get_all_declarations(context.project_id)

            all_violations = []

            if declarations:
                # DB declarations exist → use formal detector
                detector = FocalizationViolationDetector(service, context.entities)

                for ch in context.chapters:
                    content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""
                    chapter_num = self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or 0

                    if content:
                        violations = detector.detect_violations(
                            project_id=context.project_id,
                            text=content,
                            chapter=chapter_num,
                        )
                        all_violations.extend(violations)
            else:
                # No declarations → heuristic omniscient intrusion detection
                all_violations = self._heuristic_focalization_check(context)

            if all_violations:
                context.stats["focalization_violations"] = len(all_violations)
                logger.info(f"Found {len(all_violations)} focalization violations")

                if not hasattr(context, "focalization_violations"):
                    context.focalization_violations = []
                context.focalization_violations.extend(all_violations)

        except ImportError:
            logger.debug("Focalization module not available")
        except Exception as e:
            logger.warning(f"Focalization consistency check failed: {e}")

    def _heuristic_focalization_check(self, context: AnalysisContext) -> list:
        """
        Detección heurística de intrusiones omniscientes sin declaraciones DB.

        Determina el focalizador global (personaje con más acceso mental en
        toda la obra) y flag a cualquier otro personaje cuya mente se acceda.
        """
        import re

        # Patrones de acceso mental (pensamientos, sentimientos internos)
        MENTAL_ACCESS = re.compile(
            r"\b(?P<name>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+"
            r"(?:pensó|pensaba|sintió|sentía|sabía|supo|recordó|recordaba|"
            r"se\s+preguntó|se\s+preguntaba|temía|temió|deseaba|deseó|"
            r"sospechó|sospechaba|intuía|intuyó|imaginó|imaginaba|"
            r"comprendió|comprendía|entendió|entendía|"
            r"se\s+dijo|se\s+decía|se\s+convenció|creía|creyó|"
            r"quería|echaba\s+de\s+menos|se\s+arrepentía)",
            re.UNICODE,
        )

        # Recoger nombres de entidades
        entity_names: set[str] = set()
        for e in context.entities:
            name = self._get_val(e, "canonical_name") or self._get_val(e, "name") or ""
            if name:
                entity_names.add(name)
                first = name.split()[0]
                if first:
                    entity_names.add(first)

        chapters_data = self._prepare_chapter_data(context)

        # Fase 1: Determinar focalizador global (más accesos mentales en toda la obra)
        global_mental_counts: dict[str, int] = {}
        chapter_mental_data: list[dict] = []

        for ch in chapters_data:
            content = ch["content"]
            chapter_num = ch["number"]
            if not content:
                chapter_mental_data.append({"mentions": {}, "positions": {}})
                continue

            mental_mentions: dict[str, int] = {}
            mental_positions: dict[str, list[tuple[int, str]]] = {}
            for m in MENTAL_ACCESS.finditer(content):
                name = m.group("name")
                if name in entity_names:
                    mental_mentions[name] = mental_mentions.get(name, 0) + 1
                    mental_positions.setdefault(name, []).append(
                        (m.start(), m.group(0))
                    )
                    global_mental_counts[name] = global_mental_counts.get(name, 0) + 1

            chapter_mental_data.append({
                "mentions": mental_mentions,
                "positions": mental_positions,
            })

        if not global_mental_counts:
            logger.info("Heuristic focalization: 0 violations (no mental access found)")
            return []

        # Focalizador global = personaje con más accesos mentales totales
        sorted_global = sorted(global_mental_counts.items(), key=lambda x: -x[1])
        main_focalizer = sorted_global[0][0]
        logger.debug(f"Focalization heuristic: main focalizer = {main_focalizer} ({sorted_global})")

        # Fase 2: Flagear accesos mentales de otros personajes
        violations = []
        for ch, ch_data in zip(chapters_data, chapter_mental_data, strict=True):
            chapter_num = ch["number"]
            for char_name, positions in ch_data["positions"].items():
                if char_name == main_focalizer:
                    continue
                for pos, excerpt in positions:
                    violations.append(
                        _HeuristicFocalizationViolation(
                            violation_type="forbidden_mind_access",
                            declared_focalizer=main_focalizer,
                            text_excerpt=excerpt,
                            explanation=(
                                f"Acceso a pensamientos de {char_name} cuando "
                                f"el focalizador de la obra es {main_focalizer}. "
                                f"Posible intrusión omnisciente."
                            ),
                            chapter=chapter_num,
                            position=ch["start_char"] + pos,
                            confidence=0.7,
                        )
                    )

        logger.info(f"Heuristic focalization: {len(violations)} violations")
        return violations

    def _run_voice_deviation_detection(self, context: AnalysisContext) -> None:
        """
        Detectar desviaciones de comportamiento usando perfiles generados.

        Compara el comportamiento observado contra las expectativas
        para detectar inconsistencias.
        """
        if not context.voice_profiles:
            return

        try:
            from ..llm.expectation_inference import detect_expectation_violations

            for entity in context.entities:
                if entity.id not in context.voice_profiles:
                    continue

                # Analizar cada capítulo buscando violaciones
                for ch in context.chapters:
                    content = ch.get("content", "")
                    if not content:
                        continue

                    violations = detect_expectation_violations(
                        character_id=entity.id,
                        text=content,
                        chapter_number=ch["number"],
                        position=ch.get("start_char", 0),
                    )

                    for violation in violations:
                        context.voice_deviations.append(
                            {
                                "entity_id": entity.id,
                                "entity_name": entity.canonical_name,
                                "chapter": ch["number"],
                                "violation_text": violation.violation_text,
                                "explanation": violation.explanation,
                                "severity": violation.severity.value
                                if hasattr(violation.severity, "value")
                                else str(violation.severity),
                                "expectation": violation.expectation.to_dict()
                                if hasattr(violation.expectation, "to_dict")
                                else str(violation.expectation),
                                "consensus_score": violation.consensus_score,
                                "detection_methods": violation.detection_methods,
                            }
                        )

            context.stats["voice_deviations"] = len(context.voice_deviations)

        except ImportError:
            logger.debug("LLM module not available for voice deviation detection")
        except Exception as e:
            logger.warning(f"Voice deviation detection failed: {e}")

    def _run_emotional_coherence(self, context: AnalysisContext) -> None:
        """
        Verificar coherencia emocional de personajes.

        Detecta inconsistencias entre:
        - Estado emocional declarado ("María estaba furiosa")
        - Comportamiento comunicativo (cómo habla María)
        - Acciones (qué hace María)
        """
        if not context.chapters:
            return

        try:
            from ..analysis.emotional_coherence import (
                EmotionalCoherenceChecker,
                get_emotional_coherence_checker,
            )

            checker = get_emotional_coherence_checker()

            all_incoherences = []

            # Necesitamos diálogos por capítulo
            dialogues_by_chapter: dict[int, list] = {}
            for d in context.dialogues:
                chapter = d.get("chapter", 0)
                if chapter not in dialogues_by_chapter:
                    dialogues_by_chapter[chapter] = []
                dialogues_by_chapter[chapter].append(d)

            # Analizar cada capítulo
            for ch in context.chapters:
                chapter_num = self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or 0
                content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""

                if not content:
                    continue

                chapter_dialogues = dialogues_by_chapter.get(chapter_num, [])
                ch_start = self._get_val(ch, "start_char") or 0

                # Convertir dicts a tuples (speaker, text, start, end)
                # Posiciones relativas al capítulo (extract_declared_emotions es chapter-relative)
                dialogues_tuples = [
                    (
                        d.get("resolved_speaker") or d.get("speaker_hint", ""),
                        d.get("text", ""),
                        d.get("start_char", 0) - ch_start,
                        d.get("end_char", 0) - ch_start,
                    )
                    for d in chapter_dialogues
                ]

                # Normalizar entity names (pueden ser objetos o dicts)
                entity_names = []
                for e in context.entities:
                    n = self._get_val(e, "canonical_name") or self._get_val(e, "name") or str(e)
                    entity_names.append(n)

                # El checker analiza el capítulo completo
                # analyze_chapter() retorna list[EmotionalIncoherence] directamente
                try:
                    result = checker.analyze_chapter(
                        chapter_text=content,
                        chapter_id=chapter_num,
                        dialogues=dialogues_tuples,
                        entity_names=entity_names,
                    )
                except Exception as chapter_err:
                    logger.warning(f"Emotional coherence cap. {chapter_num} failed: {chapter_err}")
                    continue

                # Manejar tanto Result como list directa
                if hasattr(result, "is_success"):
                    incoherences = result.value if result.is_success else []  # type: ignore[union-attr, attr-defined]
                else:
                    incoherences = result if isinstance(result, list) else []

                if incoherences:
                    for incoherence in incoherences:
                        all_incoherences.append(
                            {
                                "entity_name": incoherence.entity_name,
                                "incoherence_type": incoherence.incoherence_type.value,
                                "declared_emotion": incoherence.declared_emotion,
                                "actual_behavior": incoherence.actual_behavior,
                                "declared_text": incoherence.declared_text,
                                "behavior_text": incoherence.behavior_text,
                                "confidence": incoherence.confidence,
                                "explanation": incoherence.explanation,
                                "suggestion": incoherence.suggestion,
                                "chapter_id": incoherence.chapter_id,
                            }
                        )

            if all_incoherences:
                context.emotional_incoherences = all_incoherences
                context.stats["emotional_incoherences"] = len(all_incoherences)
                logger.info(f"Found {len(all_incoherences)} emotional incoherences")

        except ImportError as e:
            logger.debug(f"Emotional coherence module not available: {e}")
        except Exception as e:
            logger.warning(f"Emotional coherence check failed: {e}")

    def _run_sentiment_analysis(self, context: AnalysisContext) -> None:
        """
        Analizar arco emocional de cada capítulo.

        Usa pysentimiento para detectar:
        - Sentimiento general (positivo/negativo/neutro)
        - Emociones primarias (joy, sadness, anger, fear, surprise, disgust)
        - Evolución emocional a lo largo del capítulo
        """
        if not context.chapters:
            return

        try:
            from ..nlp.sentiment import SentimentAnalyzer

            analyzer = SentimentAnalyzer()

            sentiment_arcs = []

            for ch in context.chapters:
                chapter_num = ch.get("number", 0)
                content = ch.get("content", "")

                if not content:
                    continue

                # Analizar arco emocional del capítulo
                arc_result = analyzer.analyze_emotional_arc(  # type: ignore[call-arg]
                    text=content,
                    chapter_id=chapter_num,
                    segment_size=500,  # Dividir en segmentos de ~500 chars
                )

                if hasattr(arc_result, "is_success") and arc_result.is_success and arc_result.value:  # type: ignore[union-attr, attr-defined]
                    arc = arc_result.value  # type: ignore[union-attr, attr-defined]
                    sentiment_arcs.append(
                        {
                            "chapter": chapter_num,
                            "overall_sentiment": arc.overall_sentiment.value,
                            "overall_confidence": arc.overall_confidence,
                            "dominant_emotion": arc.dominant_emotion.value
                            if arc.dominant_emotion
                            else "neutral",
                            "emotion_variance": arc.emotion_variance,
                            "sentiment_shifts": arc.sentiment_shifts,
                            "segments": [
                                {
                                    "position": seg.start_char,
                                    "sentiment": seg.sentiment.value,
                                    "emotion": seg.primary_emotion.value,
                                    "confidence": seg.sentiment_confidence,
                                }
                                for seg in arc.segments[:10]  # Limitar a 10 segmentos
                            ],
                        }
                    )

            if sentiment_arcs:
                context.sentiment_arcs = sentiment_arcs
                context.stats["chapters_with_sentiment"] = len(sentiment_arcs)

                # Estadísticas agregadas
                avg_variance = sum(a["emotion_variance"] for a in sentiment_arcs) / len(
                    sentiment_arcs
                )
                context.stats["avg_emotional_variance"] = round(avg_variance, 3)

                total_shifts = sum(a["sentiment_shifts"] for a in sentiment_arcs)
                context.stats["total_sentiment_shifts"] = total_shifts

                logger.info(f"Sentiment analysis: {len(sentiment_arcs)} chapters analyzed")

        except ImportError as e:
            logger.debug(f"Sentiment analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")

    @staticmethod
    def _get_val(obj, key: str, default=None):
        """Extrae valor de un dict o de un objeto con atributo."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _prepare_chapter_data(self, context: AnalysisContext) -> list[dict]:
        """Normaliza capítulos (dict u objeto) a lista de dicts."""
        chapters_data = []
        for ch in context.chapters:
            num = self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or 0
            content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""
            start = self._get_val(ch, "start_char") or 0
            chapters_data.append({"number": num, "content": content, "start_char": start})
        return chapters_data

    def _prepare_entity_data(self, context: AnalysisContext) -> list[dict]:
        """Normaliza entidades (dict u objeto) a lista de dicts."""
        entities_data = []
        for e in context.entities:
            eid = self._get_val(e, "id") or 0
            name = self._get_val(e, "canonical_name") or str(e)
            aliases = self._get_val(e, "aliases") or []
            etype_raw = self._get_val(e, "entity_type")
            if etype_raw and hasattr(etype_raw, "value"):
                etype = etype_raw.value
            elif etype_raw:
                etype = str(etype_raw)
            else:
                etype = "character"
            entities_data.append({
                "id": eid, "canonical_name": name, "name": name,
                "aliases": aliases, "entity_type": etype,
            })
        return entities_data

    def _run_vital_status_check(self, context: AnalysisContext) -> None:
        """
        Detectar personajes fallecidos que reaparecen.

        Busca menciones de muerte/fallecimiento y luego verifica que el personaje
        no reaparezca activamente (hablando, actuando) después.
        """
        try:
            from ..analysis.vital_status import analyze_vital_status

            chapters_data = self._prepare_chapter_data(context)
            entities_data = self._prepare_entity_data(context)

            result = analyze_vital_status(
                project_id=context.project_id,
                chapters=chapters_data,
                entities=entities_data,
            )

            if result.is_success and result.value is not None:
                context.vital_status_report = result.value
                post_mortem = getattr(result.value, "post_mortem_appearances", [])
                context.stats["vital_status_deaths"] = len(
                    getattr(result.value, "death_events", [])
                )
                context.stats["vital_status_post_mortem"] = len(post_mortem)
                logger.info(
                    f"Vital status: {len(getattr(result.value, 'death_events', []))} deaths, "
                    f"{len(post_mortem)} post-mortem appearances"
                )

        except ImportError as e:
            logger.debug(f"Vital status module not available: {e}")
        except Exception as e:
            logger.warning(f"Vital status check failed: {e}")

    def _run_character_location_check(self, context: AnalysisContext) -> None:
        """
        Detectar ubicaciones imposibles de personajes.

        Busca menciones de personajes en diferentes ubicaciones en el mismo
        período temporal sin transición narrativa.
        """
        try:
            from ..analysis.character_location import analyze_character_locations

            chapters_data = self._prepare_chapter_data(context)
            entities_data = self._prepare_entity_data(context)

            result = analyze_character_locations(
                project_id=context.project_id,
                chapters=chapters_data,
                entities=entities_data,
            )

            if result.is_success and result.value is not None:
                inconsistencies = getattr(result.value, "inconsistencies", [])
                context.location_inconsistencies = inconsistencies
                context.stats["location_inconsistencies"] = len(inconsistencies)
                logger.info(f"Character locations: {len(inconsistencies)} inconsistencies")

        except ImportError as e:
            logger.debug(f"Character location module not available: {e}")
        except Exception as e:
            logger.warning(f"Character location check failed: {e}")

    def _run_ooc_detection(self, context: AnalysisContext) -> None:
        """
        Detectar comportamiento fuera de personaje (OOC).

        Compara el comportamiento establecido (perfil) contra acciones
        y diálogos en cada capítulo.
        """
        try:
            from ..analysis.out_of_character import OutOfCharacterDetector

            detector = OutOfCharacterDetector()

            # Preparar diálogos por capítulo
            chapter_dialogues: dict[int, list] = {}
            for d in context.dialogues:
                ch_num = d.get("chapter", 0)
                if ch_num not in chapter_dialogues:
                    chapter_dialogues[ch_num] = []
                chapter_dialogues[ch_num].append(d)

            # Preparar textos por capítulo
            chapter_texts: dict[int, str] = {}
            for ch in context.chapters:
                ch_num = self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or 0
                ch_content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""
                chapter_texts[ch_num] = ch_content

            # Obtener perfiles si existen
            profiles = []
            if context.voice_profiles:
                # voice_profiles es dict {entity_id: profile}
                profiles = list(context.voice_profiles.values())

            if not profiles:
                # Sin perfiles, construir perfiles básicos desde menciones/atributos
                from ..analysis.character_profiling import CharacterProfiler

                profiler = CharacterProfiler()

                # Preparar menciones desde entidades
                mentions = []
                for e in context.entities:
                    eid = self._get_val(e, "id") or 0
                    ename = self._get_val(e, "canonical_name") or str(e)
                    for ch in context.chapters:
                        ch_num = self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or 0
                        ch_content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""
                        if ename.lower() in ch_content.lower():
                            mentions.append(
                                {
                                    "entity_id": eid,
                                    "entity_name": ename,
                                    "chapter": ch_num,
                                }
                            )

                attrs_data = [
                    a if isinstance(a, dict) else a.to_dict()
                    if hasattr(a, "to_dict") else {"key": str(a)}
                    for a in context.attributes
                ]

                dialogues_data = context.dialogues

                profiles = profiler.build_profiles(
                    mentions=mentions,
                    attributes=attrs_data,
                    dialogues=dialogues_data,
                    chapter_texts=chapter_texts,
                )

            if profiles:
                report = detector.detect(
                    profiles=profiles,
                    chapter_dialogues=chapter_dialogues,
                    chapter_texts=chapter_texts,
                )

                ooc_events = getattr(report, "events", [])
                context.ooc_events = [
                    e.to_dict() if hasattr(e, "to_dict") else e for e in ooc_events
                ]
                context.stats["ooc_events"] = len(ooc_events)
                logger.info(f"OOC detection: {len(ooc_events)} events")

        except ImportError as e:
            logger.debug(f"OOC detection module not available: {e}")
        except Exception as e:
            logger.warning(f"OOC detection failed: {e}")

    def _run_chekhov_check(self, context: AnalysisContext) -> None:
        """
        Detectar personajes/elementos introducidos con detalle que luego desaparecen.

        Basado en el principio de Chekhov: si introduces algo con detalle,
        debe tener relevancia posterior en la narrativa.

        Implementación ligera que no requiere DB: analiza en memoria
        qué personajes secundarios aparecen pocas veces y luego desaparecen.
        """
        try:
            total_chapters = len(context.chapters)
            if total_chapters < 2:
                return

            # Construir mapa de presencia: {entity_name: set(chapter_numbers)}
            presence: dict[str, set[int]] = {}
            intro_chapter: dict[str, int] = {}

            for e in context.entities:
                ename = self._get_val(e, "canonical_name") or str(e)
                etype_raw = self._get_val(e, "entity_type")
                etype = (
                    etype_raw.value if hasattr(etype_raw, "value")
                    else str(etype_raw) if etype_raw else ""
                )

                # Solo personajes
                if etype not in ("character", "person", "PER"):
                    continue

                chapters_present: set[int] = set()
                for ch in context.chapters:
                    ch_num = self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or 0
                    ch_content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""
                    if ename.lower() in ch_content.lower():
                        chapters_present.add(ch_num)

                if chapters_present:
                    presence[ename] = chapters_present
                    intro_chapter[ename] = min(chapters_present)

            # Detectar personajes que desaparecen: aparecen en 1-2 capítulos,
            # se introducen con detalle (tienen atributos), y no llegan al final
            abandoned = []
            last_chapter_num = max(
                (
                    self._get_val(ch, "number") or self._get_val(ch, "chapter_number") or i
                    for i, ch in enumerate(context.chapters)
                ),
                default=total_chapters,
            )

            # Verificar qué personajes tienen atributos (= introducidos con detalle)
            entities_with_attrs: set[str] = set()
            for attr in context.attributes:
                attr_name = (
                    attr.get("entity_name", "")
                    if isinstance(attr, dict)
                    else getattr(attr, "entity_name", "")
                )
                if attr_name:
                    entities_with_attrs.add(attr_name.lower())

            for ename, chapters_set in presence.items():
                last_mention = max(chapters_set)
                # Personaje que desaparece: no aparece en los últimos 40% de capítulos
                disappears_before = last_chapter_num - int(total_chapters * 0.4)

                if (
                    len(chapters_set) <= 2
                    and last_mention <= disappears_before
                    and ename.lower() in entities_with_attrs
                ):
                    abandoned.append(
                        {
                            "entity_name": ename,
                            "introduction_chapter": intro_chapter.get(ename, 0),
                            "last_mention_chapter": last_mention,
                            "chapters_present": sorted(chapters_set),
                            "total_chapters": total_chapters,
                            "description": (
                                f"'{ename}' se introduce con detalle en cap. "
                                f"{intro_chapter.get(ename, '?')} pero desaparece "
                                f"después de cap. {last_mention}"
                            ),
                        }
                    )

            context.chekhov_threads = abandoned
            context.stats["chekhov_threads"] = len(abandoned)
            logger.info(f"Chekhov tracker: {len(abandoned)} abandoned threads")

        except Exception as e:
            logger.warning(f"Chekhov check failed: {e}")

    def _run_shallow_character_detection(self, context: AnalysisContext) -> None:
        """
        Detectar personajes planos: muchas menciones pero pocas dimensiones narrativas.

        Un personaje "plano" tiene presencia cuantitativa (aparece mucho)
        pero poca profundidad (pocos atributos, diálogos, interacciones).
        """
        try:
            total_chapters = len(context.chapters)
            if total_chapters < 2:
                return

            # Contadores por personaje
            mention_counts: dict[str, int] = {}
            attr_counts: dict[str, int] = {}
            dialogue_counts: dict[str, int] = {}
            chapter_counts: dict[str, int] = {}

            # Recoger personajes
            characters: list[str] = []
            for e in context.entities:
                etype_raw = self._get_val(e, "entity_type")
                etype = (
                    etype_raw.value if hasattr(etype_raw, "value")
                    else str(etype_raw) if etype_raw else ""
                )
                if etype not in ("character", "person", "PER"):
                    continue
                ename = self._get_val(e, "canonical_name") or str(e)
                characters.append(ename)
                mention_counts[ename] = 0
                attr_counts[ename] = 0
                dialogue_counts[ename] = 0
                chapter_counts[ename] = 0

            if not characters:
                return

            # Contar menciones y capítulos de presencia
            for ch in context.chapters:
                content = self._get_val(ch, "content") or self._get_val(ch, "text") or ""
                content_lower = content.lower()
                for name in characters:
                    count = content_lower.count(name.lower())
                    if count > 0:
                        mention_counts[name] += count
                        chapter_counts[name] += 1

            # Contar atributos
            for attr in context.attributes:
                attr_name = (
                    attr.get("entity_name", "")
                    if isinstance(attr, dict)
                    else getattr(attr, "entity_name", "")
                )
                if attr_name in attr_counts:
                    attr_counts[attr_name] += 1

            # Contar diálogos atribuidos
            for d in context.dialogues:
                speaker = d.get("resolved_speaker") or d.get("speaker_hint", "")
                if speaker in dialogue_counts:
                    dialogue_counts[speaker] += 1

            # Detectar personajes planos: aparecen en ≥2 capítulos con ≥3 menciones
            # pero ≤1 atributos y ≤1 diálogos
            shallow = []
            for name in characters:
                mentions = mention_counts.get(name, 0)
                chapters_in = chapter_counts.get(name, 0)
                attrs = attr_counts.get(name, 0)
                dialogues = dialogue_counts.get(name, 0)

                if chapters_in >= 2 and mentions >= 3 and attrs <= 1 and dialogues <= 1:
                    shallow.append({
                        "entity_name": name,
                        "mentions": mentions,
                        "chapters_present": chapters_in,
                        "attributes": attrs,
                        "dialogues": dialogues,
                        "description": (
                            f"'{name}' aparece en {chapters_in} capítulos "
                            f"({mentions} menciones) pero tiene solo {attrs} atributo(s) "
                            f"y {dialogues} diálogo(s). Personaje poco desarrollado."
                        ),
                    })

            if shallow:
                if not hasattr(context, "shallow_characters"):
                    context.shallow_characters = []
                context.shallow_characters = shallow
                context.stats["shallow_characters"] = len(shallow)
                logger.info(f"Shallow characters: {len(shallow)} detected")

        except Exception as e:
            logger.warning(f"Shallow character detection failed: {e}")
