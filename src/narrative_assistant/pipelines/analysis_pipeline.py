"""
Pipeline completo de análisis de manuscritos.

Orquesta todos los pasos del análisis:
- Parsing del documento
- Detección de estructura (capítulos/escenas)
- Extracción de entidades (NER)
- Extracción de atributos
- Análisis de consistencia
- Generación de alertas
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..alerts.engine import AlertEngine, get_alert_engine
from ..alerts.models import Alert, AlertCategory, AlertSeverity
from ..analysis.attribute_consistency import (
    AttributeConsistencyChecker,
    AttributeInconsistency,
)
from ..core.errors import NarrativeError, ErrorSeverity
from ..core.result import Result
from ..entities.models import Entity
from ..entities.repository import get_entity_repository
from ..nlp.attributes import AttributeExtractor, ExtractedAttribute as LegacyExtractedAttribute
from ..nlp.attributes import AttributeKey, AttributeCategory as LegacyAttributeCategory
from ..nlp.extraction import (
    AttributeExtractionPipeline,
    PipelineConfig as ExtractionPipelineConfig,
    AggregatedAttribute,
    AttributeType,
)
from ..nlp.ner import NERExtractor
from ..parsers.base import detect_format, get_parser
from ..parsers.structure_detector import StructureDetector
from ..persistence.database import get_database
from ..persistence.document_fingerprint import generate_fingerprint
from ..persistence.project import ProjectManager
from ..persistence.session import SessionManager

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """
    Configuración del pipeline de análisis.

    Attributes:
        run_ner: Ejecutar NER (extracción de entidades)
        run_attributes: Ejecutar extracción de atributos
        run_consistency: Ejecutar análisis de consistencia
        create_alerts: Crear alertas en la base de datos
        min_confidence: Confianza mínima para alertas
        batch_size: Tamaño de batch para procesamiento NLP
        force_reanalysis: Si True, limpia datos previos y re-analiza
        use_hybrid_extraction: Usar pipeline híbrido (regex+dependency+embeddings)
        use_llm_extraction: Usar LLM local (Ollama) para extracción
        llm_ensemble_mode: Usar múltiples modelos LLM con votación
        llm_models: Lista de modelos Ollama a usar (ej: ["mistral:7b-instruct"])
    """

    run_ner: bool = True
    run_attributes: bool = True
    run_consistency: bool = True
    create_alerts: bool = True
    min_confidence: float = 0.5
    batch_size: Optional[int] = None
    force_reanalysis: bool = False
    # Nuevo pipeline híbrido de extracción de atributos
    use_hybrid_extraction: bool = True  # Usar nuevo pipeline por defecto
    use_llm_extraction: bool = False  # LLM deshabilitado por defecto (requiere Ollama)
    llm_ensemble_mode: bool = False  # Múltiples modelos con votación
    llm_models: Optional[list[str]] = None  # Modelos Ollama a usar


@dataclass
class ChapterInfo:
    """Información de un capítulo detectado."""
    number: int
    title: Optional[str]
    content: str
    start_char: int
    end_char: int
    word_count: int
    structure_type: str = "chapter"


@dataclass
class AnalysisReport:
    """
    Informe de análisis completo.

    Attributes:
        project_id: ID del proyecto analizado
        session_id: ID de la sesión de análisis
        document_path: Ruta del documento analizado
        document_fingerprint: Huella SHA-256 del documento
        entities: Entidades detectadas
        alerts: Alertas generadas
        chapters: Capítulos detectados
        stats: Estadísticas del análisis
        errors: Errores no fatales ocurridos
        warnings: Advertencias
        start_time: Momento de inicio
        end_time: Momento de finalización
    """

    project_id: int
    session_id: int
    document_path: str
    document_fingerprint: str
    entities: list[Entity] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    chapters: list[ChapterInfo] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    errors: list[NarrativeError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Duración del análisis en segundos."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def has_errors(self) -> bool:
        """True si hubo errores durante el análisis."""
        return len(self.errors) > 0

    @property
    def critical_alerts(self) -> list[Alert]:
        """Retorna solo alertas críticas."""
        return [a for a in self.alerts if a.severity == AlertSeverity.CRITICAL]

    @property
    def warning_alerts(self) -> list[Alert]:
        """Retorna solo alertas de advertencia."""
        return [a for a in self.alerts if a.severity == AlertSeverity.WARNING]


def run_full_analysis(
    document_path: str | Path,
    project_name: Optional[str] = None,
    config: Optional[PipelineConfig] = None,
) -> Result[AnalysisReport]:
    """
    Ejecuta análisis completo de un manuscrito.

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
            return Result.failure(parse_result.error)

        raw_document = parse_result.value
        report.stats["total_characters"] = len(raw_document.full_text)
        logger.info(f"Parsed document: {len(raw_document.full_text)} characters")

        # STEP 3: Calcular fingerprint del documento
        fingerprint = generate_fingerprint(raw_document.full_text)
        report.document_fingerprint = fingerprint.full_hash

        # STEP 4: Crear/obtener proyecto
        project_result = _get_or_create_project_with_text(
            path, project_name, raw_document.full_text, fingerprint
        )
        if project_result.is_failure:
            return Result.failure(project_result.error)

        project_id = project_result.value
        report.project_id = project_id

        # STEP 4.5: Limpiar datos previos si es re-análisis forzado
        if config.force_reanalysis:
            logger.info("Force reanalysis: clearing previous data...")
            clear_result = _clear_project_data(project_id)
            if clear_result.is_failure:
                report.errors.append(clear_result.error)
                logger.warning("Failed to clear project data, continuing anyway")
            else:
                stats = clear_result.value
                report.stats["cleared_entities"] = stats["entities_deleted"]
                report.stats["cleared_attributes"] = stats["attributes_deleted"]
                report.stats["cleared_alerts"] = stats["alerts_deleted"]

        # STEP 5: Crear sesión de análisis
        session_result = _create_session(project_id)
        if session_result.is_failure:
            return Result.failure(session_result.error)

        report.session_id = session_result.value

        # STEP 6: Detectar estructura y guardar capítulos
        structure_result = _detect_structure(raw_document)
        if structure_result.is_failure:
            report.errors.append(structure_result.error)
            logger.warning("Structure detection failed, continuing without it")
        else:
            structure = structure_result.value
            report.stats["chapters"] = len(structure.chapters) if hasattr(structure, 'chapters') else 0
            logger.info(f"Detected {report.stats['chapters']} chapters")

            # Extraer y guardar capítulos
            if hasattr(structure, 'chapters') and structure.chapters:
                full_text = raw_document.full_text
                chapters_info = []
                for ch in structure.chapters:
                    # get_text() excluye la primera línea (título) por defecto
                    content = ch.get_text(full_text)
                    word_count = len(content.split())

                    # Calcular start_char del contenido (después del título)
                    chapter_full_text = full_text[ch.start_char : ch.end_char]
                    first_newline = chapter_full_text.find('\n')
                    if first_newline != -1:
                        # Saltar título y líneas vacías
                        content_offset = first_newline + 1
                        while content_offset < len(chapter_full_text) and chapter_full_text[content_offset] == '\n':
                            content_offset += 1
                        content_start_char = ch.start_char + content_offset
                    else:
                        content_start_char = ch.start_char

                    chapters_info.append(ChapterInfo(
                        number=ch.number,
                        title=ch.title,
                        content=content,
                        start_char=content_start_char,
                        end_char=ch.end_char,
                        word_count=word_count,
                        structure_type=ch.structure_type.value if hasattr(ch.structure_type, 'value') else str(ch.structure_type)
                    ))
                report.chapters = chapters_info

                # Persistir capítulos en la base de datos
                persist_chapters_result = _persist_chapters(chapters_info, project_id)
                if persist_chapters_result.is_failure:
                    report.errors.append(persist_chapters_result.error)
                    logger.warning("Chapter persistence failed")
                else:
                    logger.info(f"Persisted {len(chapters_info)} chapters to database")

        # STEP 7: Extracción NER
        entities = []
        if config.run_ner:
            ner_result = _run_ner(raw_document.full_text, project_id)
            if ner_result.is_failure:
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
                report.errors.append(attr_result.error)
                logger.warning("Attribute extraction failed")
            else:
                attr_extraction = attr_result.value
                # attr_extraction es un AttributeExtractionResult con .attributes
                if hasattr(attr_extraction, 'attributes'):
                    attributes = attr_extraction.attributes
                else:
                    attributes = attr_extraction if isinstance(attr_extraction, list) else []

                # PERSISTIR ATRIBUTOS EN LA DB
                persist_result = _persist_attributes(attributes, entities, project_id)
                if persist_result.is_failure:
                    report.errors.append(persist_result.error)
                    logger.warning("Attribute persistence failed")
                else:
                    persisted_count = persist_result.value
                    report.stats["attributes_persisted"] = persisted_count

                report.stats["attributes_extracted"] = len(attributes)
                logger.info(f"Extracted {len(attributes)} attributes")

        # STEP 9: Fusión automática de entidades similares
        # IMPORTANTE: Después de extraer atributos para que se muevan automáticamente
        if entities:
            logger.info("Starting automatic entity fusion...")
            fusion_result = _run_entity_fusion(project_id, report.session_id)
            if fusion_result.is_failure:
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
                logger.info(f"Reloaded {len(attributes_for_consistency)} attributes from DB for consistency check")

                if attributes_for_consistency:
                    consistency_result = _run_consistency_analysis(attributes_for_consistency)
                    if consistency_result.is_failure:
                        report.errors.append(consistency_result.error)
                        logger.warning("Consistency analysis failed")
                    else:
                        inconsistencies = consistency_result.value or []
                        report.stats["inconsistencies_found"] = len(inconsistencies)
                        logger.info(f"Found {len(inconsistencies)} inconsistencies")
            else:
                report.errors.append(reload_result.error)
                logger.warning("Failed to reload attributes from DB")

        # STEP 10: Crear alertas
        if config.create_alerts and inconsistencies:
            alerts_result = _create_alerts_from_inconsistencies(
                project_id, inconsistencies, config.min_confidence
            )
            if alerts_result.is_failure:
                report.errors.append(alerts_result.error)
                logger.warning("Alert creation failed")
            else:
                report.alerts = alerts_result.value or []
                report.stats["alerts_created"] = len(report.alerts)
                logger.info(f"Created {len(report.alerts)} alerts")

        # Finalizar
        report.end_time = datetime.now()
        logger.info(
            f"Analysis complete: {report.duration_seconds:.2f}s, "
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
    path: Path, project_name: Optional[str], text: str, fingerprint: Any
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
        alert_repo = get_alert_repository()

        stats = {
            "entities_deleted": 0,
            "attributes_deleted": 0,
            "alerts_deleted": 0,
        }

        # 1. Borrar alertas del proyecto
        with db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM alerts WHERE project_id = ?",
                (project_id,)
            )
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
                    tuple(entity_ids)
                )
                stats["attributes_deleted"] = cursor.rowcount

        # 3. Borrar entidades (soft delete o hard delete)
        with db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM entities WHERE project_id = ?",
                (project_id,)
            )
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
        if ner_result is None or not hasattr(ner_result, 'entities'):
            logger.warning("NER extraction returned None or invalid result, using empty list")
            return Result.success([])

        entities_data = ner_result.entities

        # Persistir entidades en la DB
        from ..entities.models import EntityType, EntityImportance
        import re

        # Mapeo de EntityLabel a EntityType
        label_to_type = {
            "PER": EntityType.CHARACTER,
            "LOC": EntityType.LOCATION,
            "ORG": EntityType.ORGANIZATION,
        }

        # Deduplicar y limpiar entidades
        unique_entities = {}  # {canonical_name: (entity_obj, max_confidence)}

        for entity_obj in entities_data:
            # Limpiar canonical_form: eliminar saltos de línea, múltiples espacios
            raw_text = entity_obj.text.strip()
            canonical = re.sub(r'\s+', ' ', raw_text)  # Normalizar espacios
            canonical = canonical.strip()

            # ============================================================
            # FILTROS DE CALIDAD EXHAUSTIVOS
            # ============================================================

            # 1. Ignorar texto vacío o muy corto
            if not canonical or len(canonical) < 2:
                continue

            # 2. Ignorar títulos de capítulos
            if re.match(r'^cap[ií]tulo\s+\d+', canonical, re.IGNORECASE):
                continue
            if re.match(r'^chapter\s+\d+', canonical, re.IGNORECASE):
                continue

            # 3. Ignorar frases largas (probablemente no son nombres)
            word_count = len(canonical.split())
            if word_count > 4:
                continue

            # 4. Ignorar líneas que parecen descripciones o narración
            description_starts = r'^(ten[ií]a|era|estaba|llevaba|parec[ií]a|hab[ií]a|fue|ser[ií]a|est[aá])'
            if re.match(description_starts, canonical, re.IGNORECASE):
                continue

            # 5. Ignorar expresiones de diálogo y exclamaciones
            dialogue_starters = r'^(buenos\s*d[ií]as?|hola|adi[oó]s|gracias|por\s*favor|imposible|claro|vale|bien|no|s[ií]|qu[eé]|c[oó]mo|pero|pasa)'
            if re.match(dialogue_starters, canonical, re.IGNORECASE):
                continue

            # 6. Ignorar descripciones físicas
            physical_desc = r'^(cabello|pelo|ojos|cara|manos|piernas|brazos|pies|cuerpo|barba|bigote)'
            if re.match(physical_desc, canonical, re.IGNORECASE):
                continue

            # 7. Ignorar frases posesivas
            possessive_desc = r'^(sus?|mis?|tus?)\s+'
            if re.match(possessive_desc, canonical, re.IGNORECASE):
                continue

            # 8. Ignorar frases de narración
            narrative_phrases = r'^(algo|todo|nada|alguien|nadie|alguno|ninguno|el\s+otro\s+d[ií]a|fresh\s*test|test|pipeline)'
            if re.match(narrative_phrases, canonical, re.IGNORECASE):
                continue

            # 9. Ignorar verbos
            verbs = r'^(hacer|estar|ser|tener|ir|venir|decir|ver|dar|saber|querer|llegar|pasar|deber|poner|parecer|quedar|creer|hablar|seguir|encontrar|sentarse?|tocó?|entró?|miró?|preguntó?|respondió?|dijo)'
            if re.match(verbs, canonical, re.IGNORECASE):
                continue

            # 10. Ignorar artículos y preposiciones solas
            common_words = r'^(el|la|los|las|un|una|unos|unas|este|esta|estos|estas|ese|esa|esos|esas|aquel|aquella|aquellos|aquellas|otro|otra|otros|otras|de|del|al|en|con|por|para|sin|sobre|bajo|entre|hacia|desde|hasta)$'
            if re.match(common_words, canonical, re.IGNORECASE):
                continue

            # 11. Ignorar frases que contienen "extraño", "pasando", etc. (fragmentos de oraciones)
            fragment_patterns = r'(extra[ñn]o|pasando|pasaba|ocurr|sucedi|confund|sorprend)'
            if re.search(fragment_patterns, canonical, re.IGNORECASE):
                continue

            # 12. Ignorar si es solo un artículo + sustantivo común
            common_nouns = r'^(el|la|los|las|un|una)\s+(hombre|mujer|ni[ñn]o|ni[ñn]a|persona|gente|cosa|casa|puerta|mesa|cocina|cafeter[ií]a|barrio|centro|d[ií]a|semana|ma[ñn]ana|noche|tarde|cambio|aspecto)$'
            if re.match(common_nouns, canonical, re.IGNORECASE):
                continue

            # 13. Verificar que tenga al menos una mayúscula inicial (nombre propio)
            # Excepto para lugares que pueden estar en minúsculas
            first_word = canonical.split()[0]
            if not first_word[0].isupper() and entity_obj.label.value != "LOC":
                continue

            # 14. Ignorar exclamaciones e interjecciones
            exclamations = r'^(ay|oh|eh|ah|uy|vaya|caramba|diablos|cielos|dios)$'
            if re.match(exclamations, canonical, re.IGNORECASE):
                continue

            # 15. Ignorar frases que contienen solo pronombres
            only_pronouns = r'^([eé]l|ella|ellos|ellas|yo|t[uú]|nosotros|vosotros|usted|ustedes)$'
            if re.match(only_pronouns, canonical, re.IGNORECASE):
                continue

            # ============================================================
            # DEDUPLICACIÓN INTELIGENTE CON CONTENCIÓN
            # ============================================================

            canonical_lower = canonical.lower()

            # Verificar si ya existe una entidad que contenga o sea contenida por esta
            should_add = True
            key_to_replace = None

            for existing_key, (existing_obj, existing_canonical, existing_confidence) in list(unique_entities.items()):
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
                    logger.debug(f"Replacing '{existing_canonical}' with more complete '{canonical}'")
                    break

                # Si el existente contiene al nuevo (ej: "María Sánchez" ya existe, viene "María")
                # y es del mismo tipo de entidad
                if canonical_lower in existing_key and existing_obj.label == entity_obj.label:
                    # El existente es más completo, no agregar
                    should_add = False
                    logger.debug(f"Skipping '{canonical}' - already have more complete '{existing_canonical}'")
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
                importance = EntityImportance.CRITICAL
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

        logger.info(f"Persisted {len(persisted_entities)} unique entities from {len(entities_data)} extracted mentions")
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

                if merge_result.is_success:
                    merged_count += 1
                    logger.info(f"Successfully merged into entity ID: {merge_result.value.result_entity_id}")
                else:
                    logger.warning(
                        f"Failed to merge '{name1}' + '{name2}': {merge_result.error}"
                    )

        return Result.success(merged_count)

    except Exception as e:
        error = NarrativeError(
            message=f"Entity fusion failed: {str(e)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Unexpected error during entity fusion")
        return Result.failure(error)


def _persist_chapters(chapters: list["ChapterInfo"], project_id: int) -> Result[int]:
    """
    Persiste los capítulos detectados en la base de datos.

    Args:
        chapters: Lista de ChapterInfo con información de capítulos
        project_id: ID del proyecto

    Returns:
        Result con el número de capítulos persistidos
    """
    try:
        from ..persistence.chapter import ChapterRepository, ChapterData

        chapter_repo = ChapterRepository()

        # Eliminar capítulos anteriores del proyecto (re-análisis)
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
                structure_type=ch.structure_type
            )
            for ch in chapters
        ]

        # Guardar todos los capítulos
        created = chapter_repo.create_many(chapter_data_list)

        logger.info(f"Persisted {len(created)} chapters for project {project_id}")
        return Result.success(len(created))

    except Exception as e:
        error = NarrativeError(
            message=f"Error persisting chapters: {e}",
            severity=ErrorSeverity.RECOVERABLE
        )
        logger.exception("Error persisting chapters")
        return Result.failure(error)


def _run_attribute_extraction(
    text: str,
    entities: list[Entity],
    config: Optional[PipelineConfig] = None,
    chapters: Optional[list[ChapterInfo]] = None,
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
    chapters: Optional[list[ChapterInfo]] = None,
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
            pattern = r'\b' + re.escape(entity.canonical_name) + r'\b'

            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity_mentions.append((
                    entity.canonical_name,
                    match.start(),
                    match.end()
                ))

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
            AttributeType.EYE_COLOR, AttributeType.HAIR_COLOR,
            AttributeType.HAIR_TYPE, AttributeType.HEIGHT,
            AttributeType.BUILD, AttributeType.AGE, AttributeType.SKIN,
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
                logger.warning(f"Entity not found for attribute: {attr.entity_name} -> {attr.key}={attr.value}")
                continue

            # Mapear category a attribute_type
            attribute_type = str(attr.category.value) if hasattr(attr.category, 'value') else str(attr.category)

            # Mapear key
            attribute_key = str(attr.key.value) if hasattr(attr.key, 'value') else str(attr.key)

            # Persistir
            try:
                entity_repo.create_attribute(
                    entity_id=entity_id,
                    attribute_type=attribute_type,
                    attribute_key=attribute_key,
                    attribute_value=attr.value,
                    confidence=attr.confidence,
                    source_mention_id=None,  # TODO: obtener mention_id si existe
                )
                persisted_count += 1
            except Exception as e:
                logger.error(f"Failed to persist attribute {attribute_key}={attr.value} for entity {entity_id}: {e}")

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
        from ..nlp.attributes import ExtractedAttribute, AttributeKey, AttributeCategory

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
        checker = AttributeConsistencyChecker(
            use_embeddings=True,
            min_confidence=0.5
        )
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
            logger.debug(f"Processing inconsistency: {incon.entity_name}.{incon.attribute_key.value} = {incon.value1} vs {incon.value2}, confidence={incon.confidence}")

            # Filtrar por confianza mínima
            if incon.confidence < min_confidence:
                logger.debug(f"  -> Skipped: confidence {incon.confidence} < {min_confidence}")
                continue

            # RESOLUCIÓN entity_name → entity_id
            # Si entity_id es 0 (placeholder), buscar por nombre
            entity_id = incon.entity_id
            if entity_id == 0:
                # find_entities_by_name devuelve lista directamente
                found_entities = entity_repo.find_entities_by_name(
                    project_id=project_id, name=incon.entity_name
                )
                if found_entities:
                    entity_id = found_entities[0].id
                    logger.debug(f"Found entity_id={entity_id} for '{incon.entity_name}'")
                else:
                    logger.warning(
                        f"Entity not found: {incon.entity_name}, skipping alert"
                    )
                    continue

            # Construir fuentes con información de ubicación
            value1_source = {
                "chapter": incon.value1_chapter,
                "position": 0,  # TODO: extraer de AttributeExtractor
                "text": incon.value1_excerpt,
            }
            value2_source = {
                "chapter": incon.value2_chapter,
                "position": 0,
                "text": incon.value2_excerpt,
            }

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
            )

            if alert_result.is_success:
                alerts.append(alert_result.value)
                logger.debug(f"  -> Alert created successfully")
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
