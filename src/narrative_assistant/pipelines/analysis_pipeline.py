"""
Pipeline completo de análisis de manuscritos.

.. deprecated:: 1.0
    Este módulo está DEPRECADO. Use :mod:`unified_analysis` en su lugar.

    El pipeline unificado ofrece:
    - Mejor integración de correferencias
    - Análisis de registro narrativo
    - Análisis de sentimiento
    - Análisis de ritmo/pacing
    - Interacciones entre personajes
    - Speaker attribution avanzada
    - Clasificación de documentos integrada

    Migración::

        # Antes (deprecado)
        from narrative_assistant.pipelines.analysis_pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline()
        result = pipeline.analyze(document_path)

        # Ahora (recomendado)
        from narrative_assistant.pipelines.unified_analysis import (
            UnifiedAnalysisPipeline,
            UnifiedConfig,
        )
        pipeline = UnifiedAnalysisPipeline(UnifiedConfig.standard())
        result = pipeline.analyze(document_path)

        # O con perfil completo
        pipeline = UnifiedAnalysisPipeline(UnifiedConfig.complete())
        result = pipeline.analyze(document_path)

Orquesta todos los pasos del análisis:
- Parsing del documento
- Detección de estructura (capítulos/escenas)
- Extracción de entidades (NER)
- Extracción de atributos
- Análisis de consistencia
- Generación de alertas
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any


from ..alerts.engine import get_alert_engine
from ..alerts.models import Alert, AlertCategory, AlertSeverity
from ..analysis.attribute_consistency import (
    AttributeConsistencyChecker,
    AttributeInconsistency,
)
from ..analysis.emotional_coherence import (
    EmotionalIncoherence,
    get_emotional_coherence_checker,
)
from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from ..core.utils import format_duration
from ..entities.models import Entity
from ..entities.repository import get_entity_repository
from ..focalization import (
    FocalizationDeclaration,
    FocalizationViolation,
    FocalizationViolationDetector,
)
from ..focalization.declaration import get_focalization_service
from ..nlp.attributes import AttributeCategory as LegacyAttributeCategory
from ..nlp.attributes import AttributeExtractor, AttributeKey
from ..nlp.attributes import ExtractedAttribute as LegacyExtractedAttribute
from ..nlp.extraction import (
    AggregatedAttribute,
    AttributeExtractionPipeline,
    AttributeType,
)
from ..nlp.extraction import (
    PipelineConfig as ExtractionPipelineConfig,
)
from ..nlp.ner import NERExtractor
from ..parsers.base import detect_format, get_parser
from ..parsers.document_classifier import (
    DocumentClassification,
    DocumentType,
    classify_document,
)
from ..parsers.structure_detector import StructureDetector
from ..persistence.database import get_database
from ..persistence.document_fingerprint import generate_fingerprint
from ..persistence.project import ProjectManager
from ..persistence.session import SessionManager
from ..temporal import TemporalInconsistency
from .analysis_pipeline_dialogue import (
    extract_dialogues_for_emotional_analysis as _extract_dialogues_for_emotional_analysis,
    extract_dialogues_from_chapter as _extract_dialogues_from_chapter,
    run_voice_analysis as _run_voice_analysis,
)
from .analysis_pipeline_models import AnalysisReport, ChapterInfo, PipelineConfig, SectionInfo
from .analysis_pipeline_temporal import _persist_timeline, _run_temporal_analysis
from ..voice import (
    VoiceDeviation,
    VoiceProfile,
)

logger = logging.getLogger(__name__)


def run_full_analysis(
    document_path: str | Path,
    project_name: str | None = None,
    config: PipelineConfig | None = None,
) -> Result[AnalysisReport]:
    """
    Ejecuta análisis completo de un manuscrito.

    .. deprecated:: 1.0
        Use :func:`unified_analysis.run_unified_analysis` en su lugar.

    Args:
        document_path: Ruta al documento (DOCX, TXT, MD)
        project_name: Nombre del proyecto (opcional, usa nombre del archivo)
        config: Configuración del pipeline (opcional, usa default)

    Returns:
        Result con AnalysisReport completo

    Example:
        >>> result = run_full_analysis("novela.docx", "Mi Novela")
        >>> if result.is_success:
        >>>     report = result.value
        >>>     print(f"Entidades: {len(report.entities)}")
        >>>     print(f"Alertas: {len(report.alerts)}")
    """
    import warnings

    warnings.warn(
        "run_full_analysis está deprecado. "
        "Use unified_analysis.run_unified_analysis() en su lugar. "
        "Ver docstring del módulo para guía de migración.",
        DeprecationWarning,
        stacklevel=2,
    )
    path = Path(document_path)
    config = config or PipelineConfig()
    report = AnalysisReport(
        project_id=0,  # Se asignará después
        session_id=0,  # Se asignará después
        document_path=str(path.absolute()),
        document_fingerprint="",
        start_time=datetime.now(),
    )

    logger.info(f"Starting full analysis: {path.name}")

    try:
        # STEP 1: Validar documento
        if not path.exists():
            error = NarrativeError(
                message=f"Document not found: {path}",
                severity=ErrorSeverity.FATAL,
            )
            return Result.failure(error)

        # STEP 2: Parsear documento
        parse_result = _parse_document(path)
        if parse_result.is_failure:
            if parse_result.error is not None:
                return Result.failure(parse_result.error)
            else:
                return Result.failure(NarrativeError(message="Unknown parse error", severity=ErrorSeverity.FATAL))

        raw_document = parse_result.value
        assert raw_document is not None
        report.stats["total_characters"] = len(raw_document.full_text)
        logger.info(f"Parsed document: {len(raw_document.full_text)} characters")

        # STEP 2.5: Clasificar tipo de documento para ajustar análisis
        doc_title = raw_document.metadata.get("title", path.stem)
        classification = classify_document(
            text=raw_document.full_text,
            title=doc_title,
            metadata=raw_document.metadata,
        )
        report.document_type = classification.document_type
        report.document_classification = classification
        report.stats["document_type"] = classification.document_type.value
        report.stats["document_type_confidence"] = classification.confidence
        logger.info(
            f"Document classified as: {classification.document_type.value} "
            f"(confidence: {classification.confidence:.2f})"
        )

        # Ajustar configuración según tipo de documento
        if classification.document_type != DocumentType.UNKNOWN:
            config = _adjust_config_for_document_type(config, classification)

        # STEP 3: Calcular fingerprint del documento
        fingerprint = generate_fingerprint(raw_document.full_text)
        report.document_fingerprint = fingerprint.full_hash

        # STEP 4: Crear/obtener proyecto
        project_result = _get_or_create_project_with_text(
            path, project_name, raw_document.full_text, fingerprint
        )
        if project_result.is_failure:
            if project_result.error is not None:
                return Result.failure(project_result.error)
            else:
                return Result.failure(NarrativeError(message="Unknown project error", severity=ErrorSeverity.FATAL))

        project_id = project_result.value
        assert isinstance(project_id, int)
        report.project_id = project_id

        # STEP 4.5: Limpiar datos previos si es re-análisis forzado
        if config.force_reanalysis:
            logger.info("Force reanalysis: clearing previous data...")
            clear_result = _clear_project_data(project_id)
            if clear_result.is_failure:
                if clear_result.error is not None:
                    report.errors.append(clear_result.error)
                logger.warning("Failed to clear project data, continuing anyway")
            else:
                stats = clear_result.value
                assert stats is not None
                report.stats["cleared_entities"] = stats["entities_deleted"]
                report.stats["cleared_attributes"] = stats["attributes_deleted"]
                report.stats["cleared_alerts"] = stats["alerts_deleted"]

        # STEP 5: Crear sesión de análisis
        session_result = _create_session(project_id)
        if session_result.is_failure:
            if session_result.error is not None:
                return Result.failure(session_result.error)
            else:
                return Result.failure(NarrativeError(message="Unknown session error", severity=ErrorSeverity.FATAL))

        report.session_id = session_result.value
        assert report.session_id is not None

        # STEP 6: Detectar estructura y guardar capítulos
        structure_result = _detect_structure(raw_document)
        if structure_result.is_failure:
            if structure_result.error is not None:
                report.errors.append(structure_result.error)
            logger.warning("Structure detection failed, continuing without it")
        else:
            structure = structure_result.value
            assert structure is not None
            report.stats["chapters"] = (
                len(structure.chapters) if hasattr(structure, "chapters") else 0
            )
            logger.info(f"Detected {report.stats['chapters']} chapters")

            # Extraer y guardar capítulos
            if hasattr(structure, "chapters") and structure.chapters:
                full_text = raw_document.full_text
                chapters_info = []
                for ch in structure.chapters:
                    # get_text() excluye la primera línea (título) por defecto
                    content = ch.get_text(full_text)
                    word_count = len(content.split())

                    # Calcular start_char del contenido (después del título)
                    chapter_full_text = full_text[ch.start_char : ch.end_char]
                    first_newline = chapter_full_text.find("\n")
                    if first_newline != -1:
                        # Saltar título y líneas vacías
                        content_offset = first_newline + 1
                        while (
                            content_offset < len(chapter_full_text)
                            and chapter_full_text[content_offset] == "\n"
                        ):
                            content_offset += 1
                        content_start_char = ch.start_char + content_offset
                    else:
                        content_start_char = ch.start_char

                    # Convertir secciones del Chapter a SectionInfo
                    section_infos = (
                        _convert_sections_to_info(ch.sections)
                        if hasattr(ch, "sections") and ch.sections
                        else []
                    )
                    if section_infos:
                        logger.info(
                            f"Capítulo {ch.number}: {len(section_infos)} secciones detectadas"
                        )

                    chapters_info.append(
                        ChapterInfo(
                            number=ch.number,
                            title=ch.title,
                            content=content,
                            start_char=content_start_char,
                            end_char=ch.end_char,
                            word_count=word_count,
                            structure_type=ch.structure_type.value
                            if hasattr(ch.structure_type, "value")
                            else str(ch.structure_type),
                            sections=section_infos,
                        )
                    )
                report.chapters = chapters_info

                # Persistir capítulos en la base de datos
                persist_chapters_result = _persist_chapters(chapters_info, project_id)
                if persist_chapters_result.is_failure:
                    if persist_chapters_result.error is not None:
                        report.errors.append(persist_chapters_result.error)
                    logger.warning("Chapter persistence failed")
                else:
                    logger.info(f"Persisted {len(chapters_info)} chapters to database")

        # STEP 7: Extracción NER
        entities = []
        if config.run_ner:
            ner_result = _run_ner(raw_document.full_text, project_id)
            if ner_result.is_failure:
                if ner_result.error is not None:
                    report.errors.append(ner_result.error)
                logger.warning("NER failed, skipping entity extraction")
            else:
                entities = ner_result.value or []
                report.entities = entities
                report.stats["entities_detected"] = len(entities)
                logger.info(f"Extracted {len(entities)} entities")

        # STEP 8: Extracción de atributos (ANTES de fusión para capturar todas las menciones)
        # Usa el pipeline híbrido por defecto (regex + dependency + embeddings)
        # IMPORTANTE: Pasar los capítulos para extracción por capítulo y detección de inconsistencias
        attributes = []
        if config.run_attributes and entities:
            attr_result = _run_attribute_extraction(
                raw_document.full_text, entities, config, report.chapters
            )
            if attr_result.is_failure:
                if attr_result.error is not None:
                    report.errors.append(attr_result.error)
                logger.warning("Attribute extraction failed")
            else:
                attr_extraction = attr_result.value
                # attr_extraction es un AttributeExtractionResult con .attributes
                if hasattr(attr_extraction, "attributes"):
                    attributes = getattr(attr_extraction, "attributes", [])
                else:
                    attributes = attr_extraction if isinstance(attr_extraction, list) else []

                # PERSISTIR ATRIBUTOS EN LA DB
                persist_result = _persist_attributes(attributes, entities, project_id)
                if persist_result.is_failure:
                    if persist_result.error is not None:
                        report.errors.append(persist_result.error)
                    logger.warning("Attribute persistence failed")
                else:
                    persisted_count = persist_result.value
                    report.stats["attributes_persisted"] = persisted_count

                report.stats["attributes_extracted"] = len(attributes)
                logger.info(f"Extracted {len(attributes)} attributes")

                # STEP 8a: Crear alertas de atributos ambiguos
                # Si hay atributos con propiedad ambigua, crear alertas interactivas
                if config.create_alerts and hasattr(attr_extraction, "ambiguous_attributes"):
                    ambiguous_attrs = getattr(attr_extraction, "ambiguous_attributes", None)
                    if ambiguous_attrs:
                        logger.info(f"Found {len(ambiguous_attrs)} ambiguous attributes")
                        ambig_alerts_result = _create_alerts_from_ambiguous_attributes(
                            project_id, ambiguous_attrs
                        )
                        if ambig_alerts_result.is_failure:
                            if ambig_alerts_result.error is not None:
                                report.errors.append(ambig_alerts_result.error)
                            logger.warning("Ambiguous attribute alert creation failed")
                        else:
                            ambig_alerts = ambig_alerts_result.value or []
                            report.stats["ambiguous_attribute_alerts_created"] = len(ambig_alerts)
                            logger.info(f"Created {len(ambig_alerts)} ambiguous attribute alerts")

        # STEP 9: Fusión automática de entidades similares
        # IMPORTANTE: Después de extraer atributos para que se muevan automáticamente
        if entities:
            logger.info("Starting automatic entity fusion...")
            fusion_result = _run_entity_fusion(project_id, report.session_id)
            if fusion_result.is_failure:
                if fusion_result.error is not None:
                    report.errors.append(fusion_result.error)
                logger.warning("Entity fusion failed")
            else:
                merged_count = fusion_result.value or 0
                report.stats["entities_merged"] = merged_count
                logger.info(f"Merged {merged_count} entity pairs")

                # Recargar entidades después de fusión
                if merged_count and merged_count > 0:
                    entity_repo = get_entity_repository()
                    entities = entity_repo.get_entities_by_project(project_id)
                    report.entities = entities
                    report.stats["entities_after_fusion"] = len(entities)
                    logger.info(f"Entities after fusion: {len(entities)}")

        # STEP 10: Análisis de consistencia
        # IMPORTANTE: Después de la fusión, recargar atributos desde BD
        # para que tengan el entity_name canónico correcto
        inconsistencies = []
        if config.run_consistency:
            # Recargar atributos desde BD (tienen entity_name actualizado post-fusión)
            reload_result = _reload_attributes_from_db(project_id)
            if reload_result.is_success:
                attributes_for_consistency = reload_result.value or []
                report.stats["attributes_for_consistency"] = len(attributes_for_consistency)
                logger.info(
                    f"Reloaded {len(attributes_for_consistency)} attributes from DB for consistency check"
                )

                if attributes_for_consistency:
                    consistency_result = _run_consistency_analysis(attributes_for_consistency)
                    if consistency_result.is_failure:
                        if consistency_result.error is not None:
                            report.errors.append(consistency_result.error)
                        logger.warning("Consistency analysis failed")
                    else:
                        inconsistencies = consistency_result.value or []
                        report.stats["inconsistencies_found"] = len(inconsistencies)
                        logger.info(f"Found {len(inconsistencies)} inconsistencies")
            else:
                if reload_result.error is not None:
                    report.errors.append(reload_result.error)
                logger.warning("Failed to reload attributes from DB")

        # STEP 11: Crear alertas de atributos
        if config.create_alerts and inconsistencies:
            alerts_result = _create_alerts_from_inconsistencies(
                project_id, inconsistencies, config.min_confidence
            )
            if alerts_result.is_failure:
                if alerts_result.error is not None:
                    report.errors.append(alerts_result.error)
                logger.warning("Alert creation failed")
            else:
                report.alerts = alerts_result.value or []
                report.stats["alerts_created"] = len(report.alerts)
                logger.info(f"Created {len(report.alerts)} alerts")

        # STEP 12: Análisis temporal (timeline)
        if config.run_temporal and report.chapters:
            temporal_result = _run_temporal_analysis(
                raw_document.full_text,
                getattr(report, "chapters", []),
                project_id=project_id,
                entities=getattr(report, "entities", None),
            )
            if temporal_result.is_failure:
                if temporal_result.error is not None:
                    report.errors.append(temporal_result.error)
                logger.warning("Temporal analysis failed")
            else:
                timeline_data = temporal_result.value
                if timeline_data is not None:
                    report.timeline = timeline_data.get("timeline")
                    report.temporal_inconsistencies = timeline_data.get("inconsistencies")
                report.stats["temporal_markers"] = timeline_data["markers_count"]
                report.stats["timeline_events"] = (
                    len(report.timeline.events) if report.timeline else 0
                )
                report.stats["temporal_inconsistencies"] = len(report.temporal_inconsistencies)
                logger.info(
                    f"Temporal analysis: {timeline_data['markers_count']} markers, "
                    f"{report.stats['timeline_events']} events, "
                    f"{len(report.temporal_inconsistencies)} inconsistencies"
                )

                # NUEVO: Persistir timeline y marcadores en la base de datos
                if report.timeline is not None:
                    _persist_timeline(
                        project_id,
                        report.timeline,
                        timeline_data["markers"],
                    )

                # Crear alertas de inconsistencias temporales
                if config.create_alerts and report.temporal_inconsistencies:
                    temporal_alerts_result = _create_alerts_from_temporal_inconsistencies(
                        project_id, report.temporal_inconsistencies
                    )
                    if temporal_alerts_result.is_success:
                        temporal_alerts = temporal_alerts_result.value or []
                        report.alerts.extend(temporal_alerts)
                        report.stats["temporal_alerts_created"] = len(temporal_alerts)
                        logger.info(f"Created {len(temporal_alerts)} temporal alerts")

        # STEP 13: Análisis de voz y registro
        if config.run_voice and report.entities:
            voice_result = _run_voice_analysis(report.chapters, report.entities)
            if voice_result.is_failure:
                report.errors.append(voice_result.error)
                logger.warning(f"Voice analysis failed: {voice_result.error.message}")
            else:
                voice_data = voice_result.value
                assert voice_data is not None
                report.voice_profiles = voice_data["profiles"]
                report.voice_deviations = voice_data["deviations"]
                report.stats["voice_profiles"] = len(report.voice_profiles)
                report.stats["voice_deviations"] = len(report.voice_deviations)
                logger.info(
                    f"Voice analysis: {len(report.voice_profiles)} profiles, "
                    f"{len(report.voice_deviations)} deviations"
                )

                # Crear alertas de desviaciones de voz
                if config.create_alerts and report.voice_deviations:
                    voice_alerts_result = _create_alerts_from_voice_deviations(
                        project_id, report.voice_deviations
                    )
                    if voice_alerts_result.is_success:
                        voice_alerts = voice_alerts_result.value or []
                        report.alerts.extend(voice_alerts)
                        report.stats["voice_alerts_created"] = len(voice_alerts)
                        logger.info(f"Created {len(voice_alerts)} voice alerts")

        # STEP 14: Análisis de focalización (requiere declaraciones previas)
        # NOTA: Este paso requiere que el usuario haya declarado la focalización
        # de los capítulos. Si no hay declaraciones, se omite.
        if config.run_focalization and report.chapters and report.entities:
            foc_result = _run_focalization_analysis(project_id, report.chapters, report.entities)
            if foc_result.is_failure:
                report.errors.append(foc_result.error)
                logger.warning(f"Focalization analysis failed: {foc_result.error.message}")
            else:
                foc_data = foc_result.value
                assert foc_data is not None
                report.focalization_declarations = foc_data.get("declarations", [])
                report.focalization_violations = foc_data.get("violations", [])
                report.stats["focalization_declarations"] = len(report.focalization_declarations)
                report.stats["focalization_violations"] = len(report.focalization_violations)
                logger.info(
                    f"Focalization analysis: {len(report.focalization_declarations)} declarations, "
                    f"{len(report.focalization_violations)} violations"
                )

                # Crear alertas de violaciones de focalización
                if config.create_alerts and report.focalization_violations:
                    foc_alerts_result = _create_alerts_from_focalization_violations(
                        project_id, report.focalization_violations
                    )
                    if foc_alerts_result.is_success:
                        foc_alerts = foc_alerts_result.value or []
                        report.alerts.extend(foc_alerts)
                        report.stats["focalization_alerts_created"] = len(foc_alerts)
                        logger.info(f"Created {len(foc_alerts)} focalization alerts")

        # STEP 15: Análisis de coherencia emocional
        if config.run_emotional and report.chapters and report.entities:
            emotional_result = _run_emotional_analysis(project_id, report.chapters, report.entities)
            if emotional_result.is_failure:
                report.errors.append(emotional_result.error)
                logger.warning(f"Emotional analysis failed: {emotional_result.error.message}")
            else:
                report.emotional_incoherences = emotional_result.value or []
                report.stats["emotional_incoherences"] = len(report.emotional_incoherences)
                logger.info(
                    f"Emotional analysis: {len(report.emotional_incoherences)} incoherences"
                )

                # Crear alertas de incoherencias emocionales
                if config.create_alerts and report.emotional_incoherences:
                    emotional_alerts_result = _create_alerts_from_emotional_incoherences(
                        project_id, report.emotional_incoherences
                    )
                    if emotional_alerts_result.is_success:
                        emotional_alerts = emotional_alerts_result.value or []
                        report.alerts.extend(emotional_alerts)
                        report.stats["emotional_alerts_created"] = len(emotional_alerts)
                        logger.info(f"Created {len(emotional_alerts)} emotional alerts")

        # Finalizar
        report.end_time = datetime.now()
        logger.info(
            f"Analysis complete: {format_duration(report.duration_seconds)}, "
            f"{len(report.entities)} entities, {len(report.alerts or [])} alerts"
        )

        # Si hay errores no fatales, retornar éxito parcial
        if report.errors:
            return Result.partial(report, report.errors)

        return Result.success(report)

    except Exception as e:
        error = NarrativeError(
            message=f"Unexpected error during analysis: {str(e)}",
            severity=ErrorSeverity.FATAL,
        )
        logger.exception("Unexpected error during analysis")
        return Result.failure(error)


def _get_or_create_project_with_text(
    path: Path, project_name: str | None, text: str, fingerprint: Any
) -> Result[int]:
    """
    Obtiene o crea un proyecto con texto ya parseado.

    Args:
        path: Ruta del documento
        project_name: Nombre del proyecto (opcional)
        text: Texto del documento ya parseado
        fingerprint: DocumentFingerprint ya calculado

    Returns:
        Result con el ID del proyecto
    """
    name = project_name or path.stem
    project_mgr = ProjectManager()

    # Buscar proyecto existente por fingerprint
    existing = project_mgr.get_by_fingerprint(fingerprint.full_hash)
    if existing is not None:
        logger.info(f"Found existing project: {existing.name}")
        return Result.success(existing.id)

    # Crear nuevo proyecto
    doc_format = detect_format(path)
    create_result = project_mgr.create_from_document(
        text=text,
        name=name,
        document_format=doc_format.value,
        document_path=path,
        check_existing=False,  # Ya verificamos arriba
    )
    if create_result.is_failure:
        return Result.failure(create_result.error)

    project = create_result.value
    assert project is not None
    logger.info(f"Created new project: {name} (ID: {project.id})")
    return Result.success(project.id)


def _create_session(project_id: int) -> Result[int]:
    """Crea una nueva sesión de análisis."""
    try:
        session_mgr = SessionManager(project_id=project_id)
        session = session_mgr.start()
        return Result.success(session.id)
    except Exception as e:
        error = NarrativeError(
            message=f"Failed to create session: {str(e)}",
            severity=ErrorSeverity.FATAL,
        )
        return Result.failure(error)


def _clear_project_data(project_id: int) -> Result[dict]:
    """
    Limpia todos los datos de análisis de un proyecto.

    Se usa antes de re-analizar para evitar duplicados.

    Args:
        project_id: ID del proyecto a limpiar

    Returns:
        Result con estadísticas de limpieza
    """
    try:
        from ..alerts.repository import get_alert_repository

        db = get_database()
        entity_repo = get_entity_repository()
        get_alert_repository()

        stats = {
            "entities_deleted": 0,
            "attributes_deleted": 0,
            "alerts_deleted": 0,
        }

        # 1. Borrar alertas del proyecto
        with db.connection() as conn:
            cursor = conn.execute("DELETE FROM alerts WHERE project_id = ?", (project_id,))
            stats["alerts_deleted"] = cursor.rowcount

        # 2. Borrar atributos (a través de entities)
        # Primero obtener IDs de entidades
        entities = entity_repo.get_entities_by_project(project_id)
        entity_ids = [e.id for e in entities]

        if entity_ids:
            placeholders = ",".join(["?" for _ in entity_ids])
            with db.connection() as conn:
                cursor = conn.execute(
                    f"DELETE FROM entity_attributes WHERE entity_id IN ({placeholders})",
                    tuple(entity_ids),
                )
                stats["attributes_deleted"] = cursor.rowcount

        # 3. Borrar entidades (soft delete o hard delete)
        with db.connection() as conn:
            cursor = conn.execute("DELETE FROM entities WHERE project_id = ?", (project_id,))
            stats["entities_deleted"] = cursor.rowcount

        logger.info(
            f"Cleared project {project_id} data: "
            f"{stats['entities_deleted']} entities, "
            f"{stats['attributes_deleted']} attributes, "
            f"{stats['alerts_deleted']} alerts"
        )
        return Result.success(stats)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to clear project data: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error clearing project data")
        return Result.failure(error)


def _adjust_config_for_document_type(
    config: PipelineConfig,
    classification: DocumentClassification,
) -> PipelineConfig:
    """
    Ajusta la configuración del pipeline según el tipo de documento.

    Args:
        config: Configuración original
        classification: Clasificación del documento

    Returns:
        Configuración ajustada (puede ser la misma si no hay cambios)
    """
    settings = classification.recommended_settings
    doc_type = classification.document_type

    # Para documentos que NO son ficción, desactivar análisis que no aplican
    if doc_type in (DocumentType.SELF_HELP, DocumentType.ESSAY, DocumentType.TECHNICAL):
        # El análisis temporal no tiene sentido en ensayos/autoayuda
        config.run_temporal = settings.get("analysis", {}).get("temporal_analysis", False)
        # El análisis de voz narrativa tampoco
        config.run_voice = False
        # El análisis de focalización tampoco
        config.run_focalization = False
        logger.info(
            f"Adjusted config for {doc_type.value}: "
            f"temporal={config.run_temporal}, voice={config.run_voice}"
        )

    # Para ficción y memorias, todo habilitado
    elif doc_type in (DocumentType.FICTION, DocumentType.MEMOIR):
        config.run_temporal = True
        config.run_voice = True

    # Para libros de cocina, desactivar casi todo
    elif doc_type == DocumentType.COOKBOOK:
        config.run_ner = False  # No buscar personajes
        config.run_temporal = False
        config.run_voice = False
        config.run_emotional = False
        config.run_consistency = False
        logger.info("Cookbook detected: minimal analysis mode")

    return config


def _parse_document(path: Path) -> Result[Any]:
    """Parsea el documento."""
    try:
        parser = get_parser(path)
        return parser.parse(path)
    except Exception as e:
        error = NarrativeError(
            message=f"Failed to parse document: {str(e)}",
            severity=ErrorSeverity.FATAL,
        )
        return Result.failure(error)


def _detect_structure(raw_document: Any) -> Result[Any]:
    """Detecta estructura de capítulos/escenas."""
    detector = StructureDetector()
    return detector.detect(raw_document)


def _run_ner(text: str, project_id: int) -> Result[list[Entity]]:
    """
    Ejecuta NER y persiste entidades.

    IMPORTANTE: Aquí se persisten las entidades en la DB,
    generando los entity_id que se usarán en las alertas.
    """
    try:
        ner = NERExtractor()
        entity_repo = get_entity_repository()

        # Extraer entidades con NER
        extraction_result = ner.extract_entities(text)
        if extraction_result.is_failure:
            return Result.failure(extraction_result.error)

        ner_result = extraction_result.value

        # Validar que ner_result no sea None
        if ner_result is None or not hasattr(ner_result, "entities"):
            logger.warning("NER extraction returned None or invalid result, using empty list")
            return Result.success([])

        entities_data = ner_result.entities

        # Persistir entidades en la DB
        import re

        from ..entities.models import EntityImportance, EntityType

        # Mapeo de EntityLabel a EntityType
        label_to_type = {
            "PER": EntityType.CHARACTER,
            "LOC": EntityType.LOCATION,
            "ORG": EntityType.ORGANIZATION,
        }

        # Deduplicar y limpiar entidades
        unique_entities: dict[str, Any] = {}  # {canonical_name: (entity_obj, max_confidence)}

        for entity_obj in entities_data:
            # Limpiar canonical_form: eliminar saltos de línea, múltiples espacios
            raw_text = entity_obj.text.strip()
            canonical = re.sub(r"\s+", " ", raw_text)  # Normalizar espacios
            canonical = canonical.strip()

            # ============================================================
            # FILTROS DE CALIDAD EXHAUSTIVOS
            # ============================================================

            # 1. Ignorar texto vacío o muy corto
            if not canonical or len(canonical) < 2:
                continue

            # 2. Ignorar títulos de capítulos
            if re.match(r"^cap[ií]tulo\s+\d+", canonical, re.IGNORECASE):
                continue
            if re.match(r"^chapter\s+\d+", canonical, re.IGNORECASE):
                continue

            # 3. Ignorar frases largas (probablemente no son nombres)
            word_count = len(canonical.split())
            if word_count > 4:
                continue

            # 4. Ignorar líneas que parecen descripciones o narración
            description_starts = (
                r"^(ten[ií]a|era|estaba|llevaba|parec[ií]a|hab[ií]a|fue|ser[ií]a|est[aá])"
            )
            if re.match(description_starts, canonical, re.IGNORECASE):
                continue

            # 5. Ignorar expresiones de diálogo y exclamaciones
            dialogue_starters = r"^(buenos\s*d[ií]as?|hola|adi[oó]s|gracias|por\s*favor|imposible|claro|vale|bien|no|s[ií]|qu[eé]|c[oó]mo|pero|pasa)"
            if re.match(dialogue_starters, canonical, re.IGNORECASE):
                continue

            # 6. Ignorar descripciones físicas
            physical_desc = (
                r"^(cabello|pelo|ojos|cara|manos|piernas|brazos|pies|cuerpo|barba|bigote)"
            )
            if re.match(physical_desc, canonical, re.IGNORECASE):
                continue

            # 7. Ignorar frases posesivas
            possessive_desc = r"^(sus?|mis?|tus?)\s+"
            if re.match(possessive_desc, canonical, re.IGNORECASE):
                continue

            # 8. Ignorar frases de narración
            narrative_phrases = r"^(algo|todo|nada|alguien|nadie|alguno|ninguno|el\s+otro\s+d[ií]a|fresh\s*test|test|pipeline)"
            if re.match(narrative_phrases, canonical, re.IGNORECASE):
                continue

            # 9. Ignorar verbos
            verbs = r"^(hacer|estar|ser|tener|ir|venir|decir|ver|dar|saber|querer|llegar|pasar|deber|poner|parecer|quedar|creer|hablar|seguir|encontrar|sentarse?|tocó?|entró?|miró?|preguntó?|respondió?|dijo)"
            if re.match(verbs, canonical, re.IGNORECASE):
                continue

            # 10. Ignorar artículos y preposiciones solas
            common_words = r"^(el|la|los|las|un|una|unos|unas|este|esta|estos|estas|ese|esa|esos|esas|aquel|aquella|aquellos|aquellas|otro|otra|otros|otras|de|del|al|en|con|por|para|sin|sobre|bajo|entre|hacia|desde|hasta)$"
            if re.match(common_words, canonical, re.IGNORECASE):
                continue

            # 11. Ignorar frases que contienen "extraño", "pasando", etc. (fragmentos de oraciones)
            fragment_patterns = r"(extra[ñn]o|pasando|pasaba|ocurr|sucedi|confund|sorprend)"
            if re.search(fragment_patterns, canonical, re.IGNORECASE):
                continue

            # 12. Ignorar si es solo un artículo + sustantivo común
            common_nouns = r"^(el|la|los|las|un|una)\s+(hombre|mujer|ni[ñn]o|ni[ñn]a|persona|gente|cosa|casa|puerta|mesa|cocina|cafeter[ií]a|barrio|centro|d[ií]a|semana|ma[ñn]ana|noche|tarde|cambio|aspecto)$"
            if re.match(common_nouns, canonical, re.IGNORECASE):
                continue

            # 13. Verificar que tenga al menos una mayúscula inicial (nombre propio)
            # Excepto para lugares que pueden estar en minúsculas
            first_word = canonical.split()[0]
            if not first_word[0].isupper() and entity_obj.label.value != "LOC":
                continue

            # 14. Ignorar exclamaciones e interjecciones
            exclamations = r"^(ay|oh|eh|ah|uy|vaya|caramba|diablos|cielos|dios)$"
            if re.match(exclamations, canonical, re.IGNORECASE):
                continue

            # 15. Ignorar frases que contienen solo pronombres
            only_pronouns = r"^([eé]l|ella|ellos|ellas|yo|t[uú]|nosotros|vosotros|usted|ustedes)$"
            if re.match(only_pronouns, canonical, re.IGNORECASE):
                continue

            # ============================================================
            # DEDUPLICACIÓN INTELIGENTE CON CONTENCIÓN
            # ============================================================

            canonical_lower = canonical.lower()

            # Verificar si ya existe una entidad que contenga o sea contenida por esta
            should_add = True
            key_to_replace = None

            for existing_key, (existing_obj, existing_canonical, existing_confidence) in list(
                unique_entities.items()
            ):
                # Si son exactamente iguales (case-insensitive)
                if canonical_lower == existing_key:
                    # Mantener el de mayor confianza
                    if entity_obj.confidence > existing_confidence:
                        key_to_replace = existing_key
                    else:
                        should_add = False
                    break

                # Si el nuevo nombre contiene al existente (ej: "Juan Pérez" contiene "Juan")
                # y es del mismo tipo de entidad
                if existing_key in canonical_lower and existing_obj.label == entity_obj.label:
                    # El nuevo es más completo, reemplazar
                    key_to_replace = existing_key
                    logger.debug(
                        f"Replacing '{existing_canonical}' with more complete '{canonical}'"
                    )
                    break

                # Si el existente contiene al nuevo (ej: "María Sánchez" ya existe, viene "María")
                # y es del mismo tipo de entidad
                if canonical_lower in existing_key and existing_obj.label == entity_obj.label:
                    # El existente es más completo, no agregar
                    should_add = False
                    logger.debug(
                        f"Skipping '{canonical}' - already have more complete '{existing_canonical}'"
                    )
                    break

            if key_to_replace:
                del unique_entities[key_to_replace]
                unique_entities[canonical_lower] = (entity_obj, canonical, entity_obj.confidence)
            elif should_add:
                unique_entities[canonical_lower] = (entity_obj, canonical, entity_obj.confidence)

        persisted_entities = []

        for canonical_lower, (entity_obj, canonical_clean, confidence) in unique_entities.items():
            # Mapear label a tipo
            entity_type = label_to_type.get(entity_obj.label.value, EntityType.CHARACTER)

            # Mapear confidence a importance (5 niveles)
            if confidence >= 0.95:
                importance = EntityImportance.PRINCIPAL
            elif confidence >= 0.85:
                importance = EntityImportance.HIGH
            elif confidence >= 0.7:
                importance = EntityImportance.MEDIUM
            elif confidence >= 0.5:
                importance = EntityImportance.LOW
            else:
                importance = EntityImportance.MINIMAL

            # Crear entidad desde ExtractedEntity
            # Usar canonical_clean (con mayúsculas/minúsculas originales) como nombre
            entity = Entity(
                id=None,  # Se asignará por la DB
                project_id=project_id,
                entity_type=entity_type,
                canonical_name=canonical_clean,  # Nombre limpio pero con capitalización original
                aliases=[],
                importance=importance,
            )

            # Guardar en DB
            try:
                entity_id = entity_repo.create_entity(entity)
                if entity_id:
                    # create_entity retorna el ID directamente
                    entity.id = entity_id
                    persisted_entities.append(entity)
                    logger.debug(f"Persisted entity: {entity.canonical_name} (ID: {entity_id})")
                else:
                    logger.warning(
                        f"Failed to persist entity '{canonical_clean}': create_entity returned None"
                    )
            except Exception as e:
                logger.error(f"Exception persisting entity '{canonical_clean}': {e}")

        logger.info(
            f"Persisted {len(persisted_entities)} unique entities from {len(entities_data)} extracted mentions"
        )
        return Result.success(persisted_entities)

    except Exception as e:
        error = NarrativeError(
            message=f"NER extraction failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _run_entity_fusion(project_id: int, session_id: int) -> Result[int]:
    """
    Ejecuta fusión automática de entidades similares.

    Args:
        project_id: ID del proyecto
        session_id: ID de la sesión

    Returns:
        Result con número de pares de entidades fusionadas
    """
    try:
        from ..entities.fusion import get_fusion_service

        fusion_service = get_fusion_service()

        # Obtener sugerencias de fusión
        suggestions = fusion_service.suggest_merges(project_id, max_suggestions=50)
        merged_count = 0

        # Fusión automática para casos muy obvios (similarity >= 0.85)
        for suggestion in suggestions:
            if suggestion.similarity >= 0.85:
                # Elegir el nombre canónico más largo (generalmente más completo)
                name1 = suggestion.entity1.canonical_name
                name2 = suggestion.entity2.canonical_name
                canonical = name1 if len(name1) >= len(name2) else name2

                logger.info(
                    f"Auto-merging entities (similarity: {suggestion.similarity:.2f}): "
                    f"'{name1}' + '{name2}' -> '{canonical}'"
                )

                # API correcta: entity_ids es lista, canonical_name es el nombre resultante
                merge_result = fusion_service.merge_entities(
                    project_id=project_id,
                    entity_ids=[suggestion.entity1.id, suggestion.entity2.id],
                    canonical_name=canonical,
                    note=f"Auto-merge (similarity: {suggestion.similarity:.2f})",
                )

                if merge_result.is_success and merge_result.value is not None:
                    merged_count += 1
                    logger.info(
                        f"Successfully merged into entity ID: {merge_result.value.result_entity_id}"
                    )
                else:
                    logger.warning(f"Failed to merge '{name1}' + '{name2}': {merge_result.error}")

        return Result.success(merged_count)

    except Exception as e:
        error = NarrativeError(
            message=f"Entity fusion failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Unexpected error during entity fusion")
        return Result.failure(error)


def _convert_sections_to_info(sections: list) -> list["SectionInfo"]:
    """
    Convierte secciones del parser (Section) a SectionInfo del pipeline.

    Args:
        sections: Lista de Section del structure_detector

    Returns:
        Lista de SectionInfo
    """
    result = []
    for s in sections:
        subsections = (
            _convert_sections_to_info(s.subsections)
            if hasattr(s, "subsections") and s.subsections
            else []
        )
        result.append(
            SectionInfo(
                number=s.number,
                title=s.title,
                heading_level=s.heading_level,
                start_char=s.start_char,
                end_char=s.end_char,
                subsections=subsections,
            )
        )
    return result


def _persist_chapters(chapters: list["ChapterInfo"], project_id: int) -> Result[int]:
    """
    Persiste los capítulos y sus secciones en la base de datos.

    Args:
        chapters: Lista de ChapterInfo con información de capítulos
        project_id: ID del proyecto

    Returns:
        Result con el número de capítulos persistidos
    """
    try:
        from ..persistence.chapter import (
            ChapterData,
            ChapterRepository,
            SectionRepository,
        )

        chapter_repo = ChapterRepository()
        section_repo = SectionRepository()

        # Eliminar secciones y capítulos anteriores del proyecto (re-análisis)
        section_repo.delete_by_project(project_id)
        chapter_repo.delete_by_project(project_id)

        # Crear objetos ChapterData
        chapter_data_list = [
            ChapterData(
                id=None,
                project_id=project_id,
                chapter_number=ch.number,
                title=ch.title,
                content=ch.content,
                start_char=ch.start_char,
                end_char=ch.end_char,
                word_count=ch.word_count,
                structure_type=ch.structure_type,
            )
            for ch in chapters
        ]

        # Guardar todos los capítulos
        created_chapters = chapter_repo.create_many(chapter_data_list)

        # Persistir secciones para cada capítulo
        total_sections = 0
        for i, ch in enumerate(chapters):
            if ch.sections:
                chapter_id = created_chapters[i].id
                sections_created = _persist_sections_recursive(
                    ch.sections, project_id, chapter_id, None, section_repo
                )
                total_sections += sections_created

        logger.info(
            f"Persisted {len(created_chapters)} chapters and {total_sections} sections for project {project_id}"
        )
        return Result.success(len(created_chapters))

    except Exception as e:
        error = NarrativeError(
            message=f"Error persisting chapters: {e}", severity=ErrorSeverity.RECOVERABLE
        )
        logger.exception("Error persisting chapters")
        return Result.failure(error)


def _persist_sections_recursive(
    sections: list["SectionInfo"],
    project_id: int,
    chapter_id: int,
    parent_section_id: int | None,
    section_repo: "SectionRepository",
) -> int:
    """
    Persiste secciones recursivamente (incluyendo subsecciones).

    Args:
        sections: Lista de SectionInfo a persistir
        project_id: ID del proyecto
        chapter_id: ID del capítulo
        parent_section_id: ID de la sección padre (None si es nivel superior)
        section_repo: Repositorio de secciones

    Returns:
        Número total de secciones persistidas
    """
    from ..persistence.chapter import SectionData

    count = 0
    for s in sections:
        section_data = SectionData(
            id=None,
            project_id=project_id,
            chapter_id=chapter_id,
            parent_section_id=parent_section_id,
            section_number=s.number,
            title=s.title,
            heading_level=s.heading_level,
            start_char=s.start_char,
            end_char=s.end_char,
        )
        created = section_repo.create(section_data)
        count += 1

        # Persistir subsecciones recursivamente
        if s.subsections:
            count += _persist_sections_recursive(
                s.subsections, project_id, chapter_id, created.id, section_repo
            )

    return count


def _run_attribute_extraction(
    text: str,
    entities: list[Entity],
    config: PipelineConfig | None = None,
    chapters: list[ChapterInfo] | None = None,
) -> Result[list[Any]]:
    """
    Extrae atributos de las entidades.

    Puede usar dos modos:
    1. Pipeline híbrido (nuevo): Combina regex, dependency, embeddings y LLM
    2. Pipeline legacy: Solo regex patterns

    Args:
        text: Texto del documento
        entities: Lista de entidades detectadas
        config: Configuración del pipeline
        chapters: Lista de capítulos (opcional, para extracción por capítulo)

    Returns:
        Result con lista de atributos extraídos
    """
    config = config or PipelineConfig()

    if config.use_hybrid_extraction:
        return _run_hybrid_attribute_extraction(text, entities, config, chapters)
    else:
        return _run_legacy_attribute_extraction(text, entities)


def _run_hybrid_attribute_extraction(
    text: str,
    entities: list[Entity],
    config: PipelineConfig,
    chapters: list[ChapterInfo] | None = None,
) -> Result[list[Any]]:
    """
    Extrae atributos usando el pipeline híbrido.

    Combina múltiples extractores:
    - RegexExtractor: Patrones de alta precisión
    - DependencyExtractor: Análisis gramatical con spaCy
    - EmbeddingsExtractor: Clasificación semántica
    - LLMExtractor: Refinamiento con Ollama (opcional)

    IMPORTANTE: Si se proporcionan capítulos, extrae atributos por capítulo
    para poder detectar inconsistencias entre diferentes partes del texto.

    Args:
        text: Texto del documento
        entities: Lista de entidades
        config: Configuración del pipeline
        chapters: Lista de capítulos (opcional, para extracción por capítulo)

    Returns:
        Result con lista de AggregatedAttribute convertidos a formato legacy
    """
    try:
        # Configurar el pipeline de extracción
        extraction_config = ExtractionPipelineConfig(
            use_regex=True,
            use_dependency=True,
            use_embeddings=True,
            use_llm=config.use_llm_extraction,
            min_confidence=config.min_confidence,
            parallel_extraction=True,
        )

        # Crear pipeline
        pipeline = AttributeExtractionPipeline(config=extraction_config)

        # Extraer nombres de entidades para el pipeline
        entity_names = [e.canonical_name for e in entities if e.canonical_name]

        logger.info(f"Running hybrid extraction for {len(entity_names)} entities")

        all_aggregated_attrs = []

        if chapters and len(chapters) > 0:
            # Extracción por capítulo para detectar inconsistencias
            logger.info(f"Extracting attributes per chapter ({len(chapters)} chapters)")
            for chapter in chapters:
                chapter_attrs = pipeline.extract(
                    text=chapter.content,
                    entity_names=entity_names,
                    chapter=chapter.number,
                )
                all_aggregated_attrs.extend(chapter_attrs)
                logger.debug(f"Chapter {chapter.number}: {len(chapter_attrs)} attributes")
        else:
            # Extracción del texto completo (fallback)
            all_aggregated_attrs = pipeline.extract(
                text=text,
                entity_names=entity_names,
                chapter=None,
            )

        logger.info(f"Hybrid extraction found {len(all_aggregated_attrs)} total attributes")

        # Convertir AggregatedAttribute a formato legacy (ExtractedAttribute)
        legacy_attrs = _convert_to_legacy_format(all_aggregated_attrs)

        # Simular el formato de retorno del AttributeExtractor legacy
        class AttributeExtractionResult:
            def __init__(self, attributes):
                self.attributes = attributes

        return Result.success(AttributeExtractionResult(legacy_attrs))

    except Exception as e:
        logger.exception("Hybrid attribute extraction failed")
        error = NarrativeError(
            message=f"Hybrid attribute extraction failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _run_legacy_attribute_extraction(text: str, entities: list[Entity]) -> Result[list[Any]]:
    """
    Extrae atributos usando el extractor legacy (solo regex).

    Args:
        text: Texto del documento
        entities: Lista de entidades

    Returns:
        Result con AttributeExtractionResult
    """
    try:
        import re

        extractor = AttributeExtractor()

        # Encontrar todas las menciones de cada entidad en el texto
        entity_mentions = []

        for entity in entities:
            pattern = r"\b" + re.escape(entity.canonical_name) + r"\b"
            entity_type = (
                entity.entity_type.value
                if hasattr(entity, "entity_type") and hasattr(entity.entity_type, "value")
                else str(entity.entity_type)
                if hasattr(entity, "entity_type")
                else None
            )

            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity_mentions.append(
                    (
                        entity.canonical_name,
                        match.start(),
                        match.end(),
                        entity_type,
                    )
                )

        logger.debug(f"Found {len(entity_mentions)} entity mentions for attribute extraction")

        result = extractor.extract_attributes(text, entity_mentions)
        return result

    except Exception as e:
        error = NarrativeError(
            message=f"Attribute extraction failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _convert_to_legacy_format(
    aggregated_attrs: list[AggregatedAttribute],
) -> list[LegacyExtractedAttribute]:
    """
    Convierte AggregatedAttribute del nuevo pipeline al formato legacy.

    Esto permite reutilizar el código de persistencia y consistencia existente.

    Args:
        aggregated_attrs: Atributos del pipeline híbrido

    Returns:
        Lista de ExtractedAttribute en formato legacy
    """
    # Mapeo de AttributeType (nuevo) a AttributeKey (legacy)
    type_to_key = {
        AttributeType.EYE_COLOR: AttributeKey.EYE_COLOR,
        AttributeType.HAIR_COLOR: AttributeKey.HAIR_COLOR,
        AttributeType.HAIR_TYPE: AttributeKey.HAIR_TYPE,
        AttributeType.HEIGHT: AttributeKey.HEIGHT,
        AttributeType.BUILD: AttributeKey.BUILD,
        AttributeType.AGE: AttributeKey.AGE,
        AttributeType.SKIN: AttributeKey.SKIN,
        AttributeType.DISTINCTIVE_FEATURE: AttributeKey.DISTINCTIVE_FEATURE,
        AttributeType.LOCATION: AttributeKey.LOCATION,
        AttributeType.PROFESSION: AttributeKey.PROFESSION,
        AttributeType.PERSONALITY: AttributeKey.PERSONALITY,
        AttributeType.OTHER: AttributeKey.OTHER,
    }

    legacy_attrs = []

    for attr in aggregated_attrs:
        # Mapear tipo de atributo
        attr_key = type_to_key.get(attr.attribute_type, AttributeKey.OTHER)

        # Determinar categoría basándose en el tipo
        if attr.attribute_type in {
            AttributeType.EYE_COLOR,
            AttributeType.HAIR_COLOR,
            AttributeType.HAIR_TYPE,
            AttributeType.HEIGHT,
            AttributeType.BUILD,
            AttributeType.AGE,
            AttributeType.SKIN,
            AttributeType.DISTINCTIVE_FEATURE,
        }:
            category = LegacyAttributeCategory.PHYSICAL
        elif attr.attribute_type == AttributeType.LOCATION:
            category = LegacyAttributeCategory.GEOGRAPHIC
        elif attr.attribute_type == AttributeType.PERSONALITY:
            category = LegacyAttributeCategory.PSYCHOLOGICAL
        elif attr.attribute_type == AttributeType.PROFESSION:
            category = LegacyAttributeCategory.SOCIAL
        else:
            category = LegacyAttributeCategory.PHYSICAL

        # Crear atributo legacy
        legacy_attr = LegacyExtractedAttribute(
            entity_name=attr.entity_name,
            category=category,
            key=attr_key,
            value=attr.value,
            source_text="",  # No disponible en agregado
            start_char=0,
            end_char=0,
            confidence=attr.final_confidence,
            chapter_id=attr.chapter,
        )

        legacy_attrs.append(legacy_attr)

        logger.debug(
            f"Converted: {attr.entity_name}.{attr.attribute_type.value}={attr.value} "
            f"(confidence={attr.final_confidence:.2f}, consensus={attr.consensus_level})"
        )

    return legacy_attrs


def _persist_attributes(
    attributes: list[Any], entities: list[Entity], project_id: int
) -> Result[int]:
    """
    Persiste atributos extraídos en la base de datos.

    Args:
        attributes: Lista de ExtractedAttribute
        entities: Lista de entidades persistidas (con entity.id)
        project_id: ID del proyecto

    Returns:
        Result con el número de atributos persistidos
    """
    try:
        entity_repo = get_entity_repository()

        # Crear mapa de nombre canónico a entity_id para búsqueda rápida
        entity_map = {}  # {canonical_name_lower: entity_id}
        for entity in entities:
            if entity.canonical_name and entity.id:
                entity_map[entity.canonical_name.lower()] = entity.id

        persisted_count = 0

        for attr in attributes:
            # Buscar entity_id por nombre
            entity_name_lower = attr.entity_name.lower() if attr.entity_name else ""
            entity_id = entity_map.get(entity_name_lower)

            if not entity_id:
                logger.warning(
                    f"Entity not found for attribute: {attr.entity_name} -> {attr.key}={attr.value}"
                )
                continue

            # Mapear category a attribute_type
            attribute_type = (
                str(attr.category.value) if hasattr(attr.category, "value") else str(attr.category)
            )

            # Mapear key
            attribute_key = str(attr.key.value) if hasattr(attr.key, "value") else str(attr.key)

            # Buscar mention_id si el atributo tiene posición de caracteres
            source_mention_id = None
            if hasattr(attr, "start_char") and hasattr(attr, "end_char") and attr.start_char > 0:
                chapter_id = getattr(attr, "chapter_id", None)
                mention = entity_repo.find_mention_by_position(
                    entity_id=entity_id,
                    start_char=attr.start_char,
                    end_char=attr.end_char,
                    chapter_id=chapter_id,
                )
                if mention:
                    source_mention_id = mention.id

            # Persistir
            try:
                entity_repo.create_attribute(
                    entity_id=entity_id,
                    attribute_type=attribute_type,
                    attribute_key=attribute_key,
                    attribute_value=attr.value,
                    confidence=attr.confidence,
                    source_mention_id=source_mention_id,
                )
                persisted_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to persist attribute {attribute_key}={attr.value} for entity {entity_id}: {e}"
                )

        logger.info(f"Persisted {persisted_count} attributes from {len(attributes)} extracted")
        return Result.success(persisted_count)

    except Exception as e:
        error = NarrativeError(
            message=f"Attribute persistence failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _reload_attributes_from_db(project_id: int) -> Result[list[Any]]:
    """
    Recarga atributos desde la BD con entity_name actualizado.

    Esto es necesario después de la fusión de entidades, ya que los
    atributos ahora están asociados a la entidad canónica y necesitamos
    el nombre canónico actualizado para el análisis de consistencia.

    Args:
        project_id: ID del proyecto

    Returns:
        Result con lista de ExtractedAttribute reconstruidos
    """
    try:
        from ..nlp.attributes import AttributeCategory, AttributeKey, ExtractedAttribute

        entity_repo = get_entity_repository()

        # Obtener atributos con entity_name actualizado
        db_attrs = entity_repo.get_attributes_by_project(project_id)

        # Convertir a ExtractedAttribute para el consistency checker
        attributes = []
        for db_attr in db_attrs:
            # Mapear attribute_key string a AttributeKey enum
            try:
                attr_key = AttributeKey(db_attr["attribute_key"])
            except ValueError:
                attr_key = AttributeKey.OTHER

            # Mapear attribute_type string a AttributeCategory enum
            try:
                attr_category = AttributeCategory(db_attr["attribute_type"])
            except ValueError:
                attr_category = AttributeCategory.PHYSICAL

            attr = ExtractedAttribute(
                entity_name=db_attr["entity_name"],  # Nombre canónico actualizado!
                key=attr_key,
                value=db_attr["attribute_value"],
                category=attr_category,
                confidence=db_attr["confidence"] or 0.8,
                source_text="",  # No disponible desde BD
                start_char=0,
                end_char=0,
                chapter_id=None,
            )
            attributes.append(attr)

        logger.info(f"Reloaded {len(attributes)} attributes from DB for project {project_id}")
        return Result.success(attributes)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to reload attributes from DB: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error reloading attributes from DB")
        return Result.failure(error)


def _run_consistency_analysis(
    attributes: list[Any],
) -> Result[list[AttributeInconsistency]]:
    """Analiza consistencia de atributos."""
    try:
        checker = AttributeConsistencyChecker(use_embeddings=True, min_confidence=0.5)
        result = checker.check_consistency(attributes)
        return result

    except Exception as e:
        error = NarrativeError(
            message=f"Consistency analysis failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _create_alerts_from_inconsistencies(
    project_id: int,
    inconsistencies: list[AttributeInconsistency],
    min_confidence: float,
) -> Result[list[Alert]]:
    """
    Convierte inconsistencias en alertas.

    CRÍTICO: Aquí se resuelve entity_name → entity_id usando EntityRepository.
    """
    try:
        engine = get_alert_engine()
        entity_repo = get_entity_repository()
        alerts = []

        logger.info(f"Processing {len(inconsistencies)} inconsistencies for alerts...")
        for incon in inconsistencies:
            logger.debug(
                f"Processing inconsistency: {incon.entity_name}.{incon.attribute_key.value} = {incon.value1} vs {incon.value2}, confidence={incon.confidence}"
            )

            # Filtrar por confianza mínima
            if incon.confidence < min_confidence:
                logger.debug(f"  -> Skipped: confidence {incon.confidence} < {min_confidence}")
                continue

            # RESOLUCIÓN entity_name → entity_id
            # Si entity_id es 0 (placeholder), buscar por nombre
            entity_id = incon.entity_id
            if entity_id == 0:
                # Primero intentar búsqueda exacta (case-insensitive)
                found_entities = entity_repo.find_entities_by_name(
                    project_id=project_id, name=incon.entity_name
                )
                # Si no hay match exacto, intentar fuzzy (ej: "María" → "María Sánchez")
                if not found_entities:
                    found_entities = entity_repo.find_entities_by_name(
                        project_id=project_id, name=incon.entity_name, fuzzy=True
                    )
                if found_entities:
                    entity_id = found_entities[0].id
                    logger.debug(f"Found entity_id={entity_id} for '{incon.entity_name}'")
                else:
                    logger.warning(f"Entity not found: {incon.entity_name}, skipping alert")
                    continue

            # Construir fuentes con información de ubicación
            # Soportar tanto multi-valor (conflicting_values) como legacy (value1/value2)
            if incon.conflicting_values and len(incon.conflicting_values) > 0:
                # Multi-valor: construir sources[] COMPLETO desde conflicting_values
                sources = []
                for cv in incon.conflicting_values:
                    sources.append(
                        {
                            "chapter": cv.chapter,
                            "position": cv.position,
                            "start_char": cv.position,
                            "end_char": cv.position + 100,  # Estimación
                            "text": cv.excerpt,
                            "value": cv.value,
                        }
                    )

                # Legacy: usar primeros 2 valores para compatibilidad con campos value1/value2
                # NOTA: sources[] contiene TODOS los valores, no solo 2
                value1_source = sources[0] if len(sources) >= 1 else {}
                value2_source = sources[1] if len(sources) >= 2 else {}
            else:
                # Legacy: value1/value2
                value1_source = {
                    "chapter": incon.value1_chapter,
                    "position": incon.value1_position,
                    "start_char": incon.value1_position,
                    "end_char": incon.value1_position + 100,
                    "text": incon.value1_excerpt,
                    "value": incon.value1,
                }
                value2_source = {
                    "chapter": incon.value2_chapter,
                    "position": incon.value2_position,
                    "start_char": incon.value2_position,
                    "end_char": incon.value2_position + 100,
                    "text": incon.value2_excerpt,
                    "value": incon.value2,
                }
                sources = [value1_source, value2_source]

            # Crear alerta
            alert_result = engine.create_from_attribute_inconsistency(
                project_id=project_id,
                entity_name=incon.entity_name,
                entity_id=entity_id,
                attribute_key=incon.attribute_key.value,
                value1=incon.value1,
                value2=incon.value2,
                value1_source=value1_source,
                value2_source=value2_source,
                explanation=incon.explanation,
                confidence=incon.confidence,
                sources=sources,  # Nueva lista de fuentes
            )

            if alert_result.is_success:
                alerts.append(alert_result.value)
                logger.debug("  -> Alert created successfully")
            else:
                logger.warning(f"Failed to create alert: {alert_result.error}")

        logger.info(f"Created {len(alerts)} alerts from {len(inconsistencies)} inconsistencies")
        return Result.success(alerts)

    except Exception as e:
        error = NarrativeError(
            message=f"Alert creation failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _create_alerts_from_ambiguous_attributes(
    project_id: int,
    ambiguous_attrs: list,  # list[AmbiguousAttribute] from nlp.attributes
) -> Result[list[Alert]]:
    """
    Crea alertas interactivas para atributos con propiedad ambigua.

    Cuando el scope resolver no puede determinar con certeza a qué
    entidad pertenece un atributo, genera una alerta pidiendo al usuario
    que seleccione el propietario correcto.

    Args:
        project_id: ID del proyecto
        ambiguous_attrs: Lista de AmbiguousAttribute colectados durante extracción

    Returns:
        Result con lista de Alert creadas
    """
    try:
        engine = get_alert_engine()
        entity_repo = get_entity_repository()
        alerts = []

        logger.info(f"Processing {len(ambiguous_attrs)} ambiguous attributes for alerts...")
        for amb_attr in ambiguous_attrs:
            logger.debug(
                f"Processing ambiguous attribute: {amb_attr.attribute_key}={amb_attr.attribute_value}, "
                f"candidates={amb_attr.candidates}"
            )

            # Resolver entity_name -> entity_id para todos los candidatos
            candidates_with_ids = []
            for candidate_name in amb_attr.candidates:
                found_entities = entity_repo.find_entities_by_name(
                    project_id=project_id, name=candidate_name
                )
                # Fuzzy fallback
                if not found_entities:
                    found_entities = entity_repo.find_entities_by_name(
                        project_id=project_id, name=candidate_name, fuzzy=True
                    )
                if found_entities:
                    candidates_with_ids.append({
                        "entity_name": candidate_name,
                        "entity_id": found_entities[0].id,
                    })
                else:
                    logger.warning(f"Entity not found: {candidate_name}, skipping from candidates")

            # Si no pudimos resolver ningún candidato, skip
            if not candidates_with_ids:
                logger.warning("No valid candidates found after entity resolution, skipping alert")
                continue

            # Crear alerta usando el alert engine
            alert_result = engine.create_from_ambiguous_attribute(
                project_id=project_id,
                attribute_key=amb_attr.attribute_key,
                attribute_value=amb_attr.attribute_value,
                candidates=candidates_with_ids,
                source_text=amb_attr.source_text,
                chapter=amb_attr.chapter_id,
                start_char=amb_attr.start_char,
                end_char=amb_attr.end_char,
            )

            if alert_result.is_success:
                alerts.append(alert_result.value)
                logger.debug("  -> Alert created successfully")
            else:
                logger.warning(f"Failed to create alert: {alert_result.error}")

        logger.info(f"Created {len(alerts)} ambiguous attribute alerts from {len(ambiguous_attrs)} ambiguous attributes")
        return Result.success(alerts)

    except Exception as e:
        error = NarrativeError(
            message=f"Ambiguous attribute alert creation failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        return Result.failure(error)


def _create_alerts_from_temporal_inconsistencies(
    project_id: int,
    inconsistencies: list[TemporalInconsistency],
) -> Result[list[Alert]]:
    """
    Crea alertas a partir de inconsistencias temporales.

    Args:
        project_id: ID del proyecto
        inconsistencies: Lista de inconsistencias temporales detectadas

    Returns:
        Result con lista de alertas creadas
    """
    try:
        from ..alerts.repository import get_alert_repository

        alert_repo = get_alert_repository()
        alerts = []

        # Mapeo de severidad temporal a severidad de alerta
        severity_map = {
            "critical": AlertSeverity.CRITICAL,
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.INFO,
        }

        # Mapeo de tipo de inconsistencia a categoría
        category_map = {
            "age_contradiction": AlertCategory.CHARACTER_CONSISTENCY,
            "impossible_sequence": AlertCategory.TIMELINE_ISSUE,
            "time_jump_suspicious": AlertCategory.TIMELINE_ISSUE,
            "marker_conflict": AlertCategory.TIMELINE_ISSUE,
            "character_age_mismatch": AlertCategory.CHARACTER_CONSISTENCY,
            "anachronism": AlertCategory.TIMELINE_ISSUE,
        }

        for incon in inconsistencies:
            severity = severity_map.get(incon.severity.value, AlertSeverity.INFO)
            category = category_map.get(
                incon.inconsistency_type.value, AlertCategory.TIMELINE_ISSUE
            )

            # Construir título descriptivo
            title = f"Inconsistencia temporal: {incon.inconsistency_type.value.replace('_', ' ').title()}"

            # Construir descripción
            description = incon.description
            if incon.expected and incon.found:
                description += f"\n\nEsperado: {incon.expected}\nEncontrado: {incon.found}"
            if incon.suggestion:
                description += f"\n\nSugerencia: {incon.suggestion}"

            # Crear alerta en la base de datos
            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=None,  # Las alertas temporales no siempre tienen entidad
                category=category.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=incon.chapter,
                source_position=incon.position,
                confidence=incon.confidence,
            )

            if alert_id:
                # Recuperar la alerta creada
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)
                    logger.debug(f"Created temporal alert: {title}")

        logger.info(f"Created {len(alerts)} temporal alerts")
        return Result.success(alerts)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to create temporal alerts: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error creating temporal alerts")
        return Result.failure(error)


def _create_alerts_from_voice_deviations(
    project_id: int,
    deviations: list[VoiceDeviation],
) -> Result[list[Alert]]:
    """
    Crea alertas a partir de desviaciones de voz.

    Args:
        project_id: ID del proyecto
        deviations: Lista de desviaciones de voz detectadas

    Returns:
        Result con lista de alertas creadas
    """
    from ..alerts.repository import get_alert_repository
    from ..voice.deviations import DeviationType

    try:
        alert_repo = get_alert_repository()
        alerts = []

        # Mapeo de severidad de desviación a severidad de alerta
        severity_map = {
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }

        # Mapeo de tipo de desviación a categoría
        category_map = {
            DeviationType.FORMALITY_SHIFT.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.LENGTH_ANOMALY.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.VOCABULARY_SHIFT.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.FILLER_ANOMALY.value: AlertCategory.VOICE_DEVIATION,
            DeviationType.PUNCTUATION_SHIFT.value: AlertCategory.VOICE_DEVIATION,
        }

        for deviation in deviations:
            severity = severity_map.get(deviation.severity.value, AlertSeverity.INFO)
            category = category_map.get(
                deviation.deviation_type.value, AlertCategory.CHARACTER_CONSISTENCY
            )

            # Construir título descriptivo
            title = f"Desviación de voz: {deviation.entity_name}"

            # Construir descripción
            description = deviation.description
            if deviation.text:
                # Truncar texto si es muy largo
                text_preview = (
                    deviation.text[:150] + "..." if len(deviation.text) > 150 else deviation.text
                )
                description += f'\n\nTexto: "{text_preview}"'

            # Crear alerta en la base de datos
            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=deviation.entity_id,
                category=category.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=deviation.chapter,
                source_position=deviation.position,
                confidence=deviation.confidence,
            )

            if alert_id:
                # Recuperar la alerta creada
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)
                    logger.debug(f"Created voice alert: {title}")

        logger.info(f"Created {len(alerts)} voice alerts")
        return Result.success(alerts)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to create voice alerts: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error creating voice alerts")
        return Result.failure(error)


def _run_focalization_analysis(
    project_id: int,
    chapters: list[ChapterInfo],
    entities: list[Entity],
) -> Result[dict]:
    """
    Ejecuta análisis de focalización.

    Nota: Este análisis requiere que el usuario haya declarado previamente
    la focalización de los capítulos. Busca declaraciones en la base de datos.

    Args:
        project_id: ID del proyecto
        chapters: Lista de capítulos
        entities: Lista de entidades

    Returns:
        Result con diccionario conteniendo declarations y violations
    """
    try:
        # Crear servicio con persistencia SQLite
        service = get_focalization_service(use_sqlite=True)

        # Buscar declaraciones existentes en la base de datos
        # Por ahora, retornamos vacío si no hay declaraciones
        declarations = service.get_all_declarations(project_id)

        if not declarations:
            logger.info("No focalization declarations found, skipping analysis")
            return Result.success(
                {
                    "declarations": [],
                    "violations": [],
                }
            )

        # Convertir entidades a formato compatible
        entity_list = []
        for e in entities:
            entity_list.append(e)

        # Crear detector
        detector = FocalizationViolationDetector(service, entity_list)

        # Detectar violaciones por capítulo
        all_violations = []
        for chapter in chapters:
            violations = detector.detect_violations(
                project_id=project_id, text=chapter.content, chapter=chapter.number
            )
            all_violations.extend(violations)

        logger.info(
            f"Focalization analysis complete: {len(declarations)} declarations, "
            f"{len(all_violations)} violations"
        )

        return Result.success(
            {
                "declarations": declarations,
                "violations": all_violations,
            }
        )

    except Exception as e:
        error = NarrativeError(
            message=f"Focalization analysis failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error during focalization analysis")
        return Result.failure(error)


def _create_alerts_from_focalization_violations(
    project_id: int,
    violations: list[FocalizationViolation],
) -> Result[list[Alert]]:
    """
    Crea alertas a partir de violaciones de focalización.

    Args:
        project_id: ID del proyecto
        violations: Lista de violaciones detectadas

    Returns:
        Result con lista de alertas creadas
    """
    from ..alerts.repository import get_alert_repository

    try:
        alert_repo = get_alert_repository()
        alerts = []

        # Mapeo de severidad
        severity_map = {
            "high": AlertSeverity.WARNING,
            "medium": AlertSeverity.INFO,
            "low": AlertSeverity.HINT,
        }

        for violation in violations:
            severity = severity_map.get(violation.severity.value, AlertSeverity.INFO)

            # Construir título
            title = f"Violación de focalización: {violation.violation_type.value.replace('_', ' ').title()}"
            if violation.entity_name:
                title = f"Violación de focalización: {violation.entity_name}"

            # Construir descripción
            description = violation.explanation
            if violation.declared_focalizer:
                description += f"\n\nFocalizador declarado: {violation.declared_focalizer}"
            if violation.suggestion:
                description += f"\n\nSugerencia: {violation.suggestion}"
            if violation.text_excerpt:
                excerpt = (
                    violation.text_excerpt[:150] + "..."
                    if len(violation.text_excerpt) > 150
                    else violation.text_excerpt
                )
                description += f'\n\nTexto: "{excerpt}"'

            # Crear alerta
            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=violation.entity_involved,
                category=AlertCategory.FOCALIZATION.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=violation.chapter,
                source_position=violation.position,
                confidence=violation.confidence,
            )

            if alert_id:
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)
                    logger.debug(f"Created focalization alert: {title}")

        logger.info(f"Created {len(alerts)} focalization alerts")
        return Result.success(alerts)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to create focalization alerts: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error creating focalization alerts")
        return Result.failure(error)


def _run_emotional_analysis(
    project_id: int,
    chapters: list[ChapterInfo],
    entities: list[Entity],
) -> Result[list[EmotionalIncoherence]]:
    """
    Ejecuta análisis de coherencia emocional.

    Analiza la coherencia entre emociones detectadas y:
    - Diálogos de los personajes
    - Acciones realizadas
    - Evolución temporal de estados emocionales

    Args:
        project_id: ID del proyecto
        chapters: Lista de capítulos
        entities: Lista de entidades (personajes)

    Returns:
        Result con lista de incoherencias emocionales detectadas
    """
    try:
        # Obtener el checker de coherencia emocional
        checker = get_emotional_coherence_checker()

        all_incoherences: list[EmotionalIncoherence] = []

        # Filtrar solo personajes y obtener sus nombres
        characters = [e for e in entities if e.entity_type == "PER"]
        character_names = [c.canonical_name for c in characters]

        for chapter in chapters:
            try:
                dialogues_data = _extract_dialogues_for_emotional_analysis(
                    chapter.number,
                    chapter.content,
                    logger,
                )

                # Analizar capítulo con diálogos
                chapter_incoherences = checker.analyze_chapter(
                    chapter_text=chapter.content,
                    entity_names=character_names,
                    dialogues=dialogues_data,
                    chapter_id=chapter.number,
                )
                all_incoherences.extend(chapter_incoherences)

            except Exception as e:
                logger.warning(f"Error analyzing chapter {chapter.number}: {e}")
                continue

        logger.info(
            f"Emotional analysis complete: {len(all_incoherences)} incoherences "
            f"across {len(chapters)} chapters"
        )

        return Result.success(all_incoherences)

    except Exception as e:
        error = NarrativeError(
            message=f"Emotional analysis failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error during emotional analysis")
        return Result.failure(error)


def _create_alerts_from_emotional_incoherences(
    project_id: int,
    incoherences: list[EmotionalIncoherence],
) -> Result[list[Alert]]:
    """
    Crea alertas a partir de incoherencias emocionales.

    Args:
        project_id: ID del proyecto
        incoherences: Lista de incoherencias detectadas

    Returns:
        Result con lista de alertas creadas
    """
    from ..alerts.repository import get_alert_repository
    from ..analysis.emotional_coherence import IncoherenceType

    try:
        alert_repo = get_alert_repository()
        alerts = []

        # Mapeo de severidad según tipo de incoherencia
        severity_map = {
            IncoherenceType.EMOTION_DIALOGUE: AlertSeverity.WARNING,
            IncoherenceType.EMOTION_ACTION: AlertSeverity.INFO,
            IncoherenceType.TEMPORAL_JUMP: AlertSeverity.INFO,
            IncoherenceType.NARRATOR_BIAS: AlertSeverity.HINT,
        }

        # Mapeo de etiquetas para títulos
        type_labels = {
            IncoherenceType.EMOTION_DIALOGUE: "Diálogo incoherente con emoción",
            IncoherenceType.EMOTION_ACTION: "Acción incoherente con emoción",
            IncoherenceType.TEMPORAL_JUMP: "Cambio emocional abrupto",
            IncoherenceType.NARRATOR_BIAS: "Inconsistencia del narrador",
        }

        for incoherence in incoherences:
            # Determinar severidad basada en confianza y tipo
            if incoherence.confidence >= 0.8:
                severity = AlertSeverity.WARNING
            elif incoherence.confidence >= 0.6:
                severity = severity_map.get(incoherence.incoherence_type, AlertSeverity.INFO)
            else:
                severity = AlertSeverity.HINT

            # Construir título descriptivo
            title = type_labels.get(
                incoherence.incoherence_type,
                f"Incoherencia emocional: {incoherence.incoherence_type.value}",
            )
            if incoherence.entity_name:
                title = f"{incoherence.entity_name}: {title}"

            # Construir descripción detallada
            description = incoherence.explanation

            if incoherence.declared_emotion and incoherence.actual_behavior:
                description += (
                    f"\n\nEmoción declarada: {incoherence.declared_emotion}"
                    f"\nComportamiento detectado: {incoherence.actual_behavior}"
                )

            if incoherence.behavior_text:
                excerpt = (
                    incoherence.behavior_text[:150] + "..."
                    if len(incoherence.behavior_text) > 150
                    else incoherence.behavior_text
                )
                description += f'\n\nTexto: "{excerpt}"'

            if incoherence.suggestion:
                description += f"\n\nSugerencia: {incoherence.suggestion}"

            # Buscar entity_id si hay personaje asociado
            entity_id = None
            if incoherence.entity_name:
                from ..entities.repository import get_entity_repository

                entity_repo = get_entity_repository()
                entity = entity_repo.find_by_name(project_id, incoherence.entity_name)
                if entity:
                    entity_id = entity.id

            # Crear alerta
            alert_id = alert_repo.create_alert(
                project_id=project_id,
                entity_id=entity_id,
                category=AlertCategory.EMOTIONAL.value,
                severity=severity.value,
                title=title,
                description=description,
                source_chapter=incoherence.chapter_id,
                source_position=incoherence.start_char,
                confidence=incoherence.confidence,
            )

            if alert_id:
                alert = alert_repo.get_alert_by_id(alert_id)
                if alert:
                    alerts.append(alert)
                    logger.debug(f"Created emotional alert: {title}")

        logger.info(f"Created {len(alerts)} emotional alerts")
        return Result.success(alerts)

    except Exception as e:
        error = NarrativeError(
            message=f"Failed to create emotional alerts: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error creating emotional alerts")
        return Result.failure(error)
