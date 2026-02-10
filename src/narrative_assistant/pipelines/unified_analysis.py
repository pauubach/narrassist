"""
Pipeline unificado de análisis de manuscritos.

Orquesta TODOS los analizadores disponibles de forma optimizada:

FASE 1 - PARSING Y ESTRUCTURA:
  - Parsing del documento
  - Detección de estructura (capítulos/escenas)
  - Detección de diálogos (speaker hints para NER)

FASE 2 - EXTRACCIÓN BASE (paralelo):
  - NER mejorado con dialogue hints
  - Marcadores temporales
  - Detección de focalización

FASE 3 - RESOLUCIÓN Y FUSIÓN:
  - Correferencias (votación multi-método)
  - Fusión semántica de entidades
  - Atribución de diálogos

FASE 4 - EXTRACCIÓN PROFUNDA (paralelo):
  - Atributos de entidades
  - Relaciones entre personajes
  - Conocimiento entre personajes
  - Perfiles de voz

FASE 5 - ANÁLISIS DE CALIDAD (paralelo):
  - Ortografía
  - Gramática
  - Repeticiones léxicas
  - Repeticiones semánticas
  - Coherencia narrativa (saltos bruscos)

FASE 6 - CONSISTENCIA Y ALERTAS:
  - Consistencia de atributos
  - Consistencia temporal
  - Violaciones de focalización
  - Desviaciones de voz
  - Generación de alertas
"""

import logging
import threading
import unicodedata
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..core.errors import ErrorSeverity, NarrativeError, PhaseError, PhasePreconditionError
from ..core.memory_monitor import MemoryMonitor
from ..core.result import Result

logger = logging.getLogger(__name__)


def _normalize_key(text: str) -> str:
    """Normaliza un nombre para usarlo como clave de agrupación.

    Elimina diacríticos (acentos, tildes) y convierte a minúsculas
    para evitar duplicados por variantes de acentuación.
    Ej: 'María García' → 'maria garcia'
    """
    nfkd = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class AnalysisPhase(Enum):
    """Fases del análisis."""

    PARSING = "parsing"
    STRUCTURE = "structure"
    BASE_EXTRACTION = "base_extraction"
    RESOLUTION = "resolution"
    DEEP_EXTRACTION = "deep_extraction"
    QUALITY = "quality"
    CONSISTENCY = "consistency"
    ALERTS = "alerts"


@dataclass
class UnifiedConfig:
    """
    Configuración del pipeline unificado.

    Cada fase puede habilitarse/deshabilitarse independientemente.
    """

    # Fases principales
    run_structure: bool = True
    run_document_classification: bool = (
        True  # Clasificar tipo de documento (ficción/ensayo/técnico)
    )
    run_dialogue_detection: bool = True
    run_ner: bool = True
    run_coreference: bool = True
    run_entity_fusion: bool = True
    run_attributes: bool = True
    run_relationships: bool = False  # Costoso, opcional
    run_interactions: bool = False  # Interacciones entre personajes (diálogo, acción, etc.)
    run_knowledge: bool = False  # Costoso, opcional
    run_voice_profiles: bool = False  # Experimental

    # Análisis de calidad
    run_spelling: bool = True
    run_grammar: bool = True
    run_lexical_repetitions: bool = True
    run_semantic_repetitions: bool = False  # Costoso
    run_coherence: bool = True  # Detectar saltos de coherencia narrativa
    run_register_analysis: bool = False  # Detectar cambios de registro (formal/coloquial)
    run_sticky_sentences: bool = True  # Detectar oraciones pesadas (exceso de glue words)

    # Análisis avanzado
    run_temporal: bool = True  # Extracción de marcadores temporales
    run_focalization: bool = False  # Experimental
    run_voice_deviations: bool = False  # Requiere voice_profiles
    run_emotional: bool = True  # Coherencia emocional (emoción declarada vs. comportamiento)
    run_sentiment: bool = False  # Análisis de arco emocional por capítulo (pysentimiento)
    run_pacing: bool = False  # Análisis de ritmo narrativo (longitud capítulos, diálogo/narración)

    # Consistencia
    run_consistency: bool = True
    run_temporal_consistency: bool = True
    create_alerts: bool = True

    # Features avanzadas (gated por licencia)
    run_character_profiling: bool = True
    run_network_analysis: bool = True
    run_anachronism_detection: bool = True
    run_ooc_detection: bool = True
    run_classical_spanish: bool = True
    run_name_variants: bool = True
    run_multi_model_voting: bool = True
    run_full_reports: bool = True

    # Parámetros
    min_confidence: float = 0.5
    use_llm: bool = False  # Usar LLM local (Ollama)
    parallel_extraction: bool = True
    max_workers: int = 4
    force_reanalysis: bool = False

    # Memory bounds
    enable_memory_monitoring: bool = True
    memory_warning_mb: float = 2048  # Umbral de warning (MB)
    max_chapter_chars_for_chunking: int = 100_000  # Capítulos >100k chars se procesan en chunks

    # Umbrales
    spelling_min_confidence: float = 0.6
    grammar_min_confidence: float = 0.5
    repetition_min_distance: int = 50  # Palabras entre repeticiones
    coherence_similarity_threshold: float = 0.3  # Similitud mínima entre párrafos

    def __post_init__(self):
        """Valida dependencias y ajusta configuración automáticamente."""
        self._validate_dependencies()
        self._sync_llm_settings()

    def _validate_dependencies(self):
        """Valida que las dependencias entre opciones sean correctas."""
        # voice_deviations requiere voice_profiles
        if self.run_voice_deviations and not self.run_voice_profiles:
            logger.warning(
                "run_voice_deviations requiere run_voice_profiles. "
                "Desactivando run_voice_deviations."
            )
            self.run_voice_deviations = False

        # entity_fusion requiere NER
        if self.run_entity_fusion and not self.run_ner:
            logger.warning("run_entity_fusion requiere run_ner. Desactivando run_entity_fusion.")
            self.run_entity_fusion = False

        # coreference requiere NER
        if self.run_coreference and not self.run_ner:
            logger.warning("run_coreference requiere run_ner. Desactivando run_coreference.")
            self.run_coreference = False

        # attributes requiere NER
        if self.run_attributes and not self.run_ner:
            logger.warning("run_attributes requiere run_ner. Desactivando run_attributes.")
            self.run_attributes = False

        # relationships requiere coreference o NER
        if self.run_relationships and not (self.run_coreference or self.run_ner):
            logger.warning(
                "run_relationships requiere run_coreference o run_ner. "
                "Desactivando run_relationships."
            )
            self.run_relationships = False

        # knowledge requiere NER y relationships
        if self.run_knowledge and not self.run_ner:
            logger.warning("run_knowledge requiere run_ner. Desactivando run_knowledge.")
            self.run_knowledge = False

        # consistency requiere attributes
        if self.run_consistency and not self.run_attributes:
            logger.warning("run_consistency requiere run_attributes. Desactivando run_consistency.")
            self.run_consistency = False

        # temporal_consistency requiere run_temporal
        if self.run_temporal_consistency and not self.run_temporal:
            logger.warning(
                "run_temporal_consistency requiere run_temporal. "
                "Desactivando run_temporal_consistency."
            )
            self.run_temporal_consistency = False

        # semantic_repetitions requiere LLM para mejor calidad
        if self.run_semantic_repetitions and not self.use_llm:
            logger.info(
                "run_semantic_repetitions funciona mejor con use_llm=True. "
                "Usando fallback de embeddings."
            )

    def _sync_llm_settings(self):
        """Sincroniza configuración de LLM entre módulos."""
        # Si LLM está deshabilitado, ajustar opciones que dependen fuertemente de él
        if not self.use_llm:
            # Knowledge analysis depende mucho del LLM
            if self.run_knowledge:
                logger.info("run_knowledge sin LLM tendrá calidad reducida (~30% menos).")

    @classmethod
    def express(cls) -> "UnifiedConfig":
        """Perfil Express: Solo ortografía y gramática. Muy rápido."""
        return cls(
            run_structure=True,
            run_dialogue_detection=False,
            run_ner=False,
            run_coreference=False,
            run_entity_fusion=False,
            run_attributes=False,
            run_relationships=False,
            run_knowledge=False,
            run_voice_profiles=False,
            run_spelling=True,
            run_grammar=True,
            run_lexical_repetitions=False,
            run_semantic_repetitions=False,
            run_coherence=False,
            run_sticky_sentences=False,
            run_temporal=False,
            run_focalization=False,
            run_voice_deviations=False,
            run_emotional=False,
            run_consistency=False,
            run_temporal_consistency=False,
            use_llm=False,
        )

    @classmethod
    def standard(cls) -> "UnifiedConfig":
        """Perfil Estándar: NER + correferencias + calidad + estilo."""
        return cls(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_coreference=True,
            run_entity_fusion=True,
            run_attributes=True,
            run_relationships=False,
            run_knowledge=False,
            run_voice_profiles=False,
            run_spelling=True,
            run_grammar=True,
            run_lexical_repetitions=True,
            run_semantic_repetitions=False,
            run_coherence=True,
            run_register_analysis=True,
            run_sticky_sentences=True,
            run_temporal=False,
            run_focalization=False,
            run_voice_deviations=False,
            run_emotional=True,
            run_pacing=True,
            run_consistency=True,
            run_temporal_consistency=False,
            use_llm=False,
        )

    @classmethod
    def deep(cls) -> "UnifiedConfig":
        """Perfil Profundo: Con LLM y relaciones."""
        return cls(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_coreference=True,
            run_entity_fusion=True,
            run_attributes=True,
            run_relationships=True,
            run_knowledge=True,
            run_voice_profiles=False,
            run_spelling=True,
            run_grammar=True,
            run_lexical_repetitions=True,
            run_semantic_repetitions=False,
            run_coherence=True,
            run_register_analysis=True,
            run_temporal=False,
            run_focalization=False,
            run_voice_deviations=False,
            run_emotional=True,
            run_sentiment=True,
            run_pacing=True,
            run_consistency=True,
            run_temporal_consistency=False,
            use_llm=True,
        )

    @classmethod
    def complete(cls) -> "UnifiedConfig":
        """Perfil Completo: Todo habilitado."""
        return cls(
            run_structure=True,
            run_dialogue_detection=True,
            run_ner=True,
            run_coreference=True,
            run_entity_fusion=True,
            run_attributes=True,
            run_relationships=True,
            run_interactions=True,
            run_knowledge=True,
            run_voice_profiles=True,
            run_spelling=True,
            run_grammar=True,
            run_lexical_repetitions=True,
            run_semantic_repetitions=True,
            run_coherence=True,
            run_register_analysis=True,
            run_temporal=True,
            run_focalization=True,
            run_voice_deviations=True,
            run_emotional=True,
            run_sentiment=True,
            run_pacing=True,
            run_consistency=True,
            run_temporal_consistency=True,
            use_llm=True,
        )


@dataclass
class AnalysisContext:
    """
    Contexto compartido entre fases del análisis.

    Permite que cada fase acceda a los resultados de fases anteriores.
    """

    # IDs
    project_id: int = 0
    session_id: int = 0

    # Documento
    document_path: str = ""
    full_text: str = ""
    fingerprint: str = ""
    raw_document: Any | None = None  # RawDocument parseado
    document_type: str = "unknown"  # Tipo de documento detectado
    document_classification: dict = field(default_factory=dict)  # Clasificación completa

    # Estructura
    chapters: list = field(default_factory=list)
    scenes: list = field(default_factory=list)

    # Diálogos (FASE 1) - Alimenta NER
    dialogues: list = field(default_factory=list)
    speaker_hints: dict = field(default_factory=dict)  # {position: speaker_name}

    # Entidades (FASE 2)
    entities: list = field(default_factory=list)
    entity_map: dict = field(default_factory=dict)  # {name: entity_id}

    # Correferencias (FASE 3)
    coreference_chains: list = field(default_factory=list)
    mention_to_entity: dict = field(default_factory=dict)  # {mention_text: entity_name}
    coref_voting_details: dict = field(default_factory=dict)  # {(start, end): MentionVotingDetail}

    # Atributos y relaciones (FASE 4)
    attributes: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    interactions: list = field(default_factory=list)  # Interacciones entre personajes
    interaction_patterns: list = field(default_factory=list)
    knowledge_matrix: dict = field(default_factory=dict)
    voice_profiles: dict = field(default_factory=dict)

    # Calidad (FASE 5)
    spelling_issues: list = field(default_factory=list)
    grammar_issues: list = field(default_factory=list)
    lexical_repetitions: list = field(default_factory=list)
    semantic_repetitions: list = field(default_factory=list)
    coherence_breaks: list = field(default_factory=list)  # Saltos de coherencia
    register_changes: list = field(default_factory=list)  # Cambios de registro narrativo
    sticky_sentences: list = field(default_factory=list)  # Oraciones pesadas (sticky sentences)

    # Marcadores temporales y focalización
    temporal_markers: list = field(default_factory=list)
    focalization_segments: list = field(default_factory=list)

    # Inconsistencias (FASE 6)
    inconsistencies: list = field(default_factory=list)
    temporal_inconsistencies: list = field(default_factory=list)
    focalization_violations: list = field(default_factory=list)
    voice_deviations: list = field(default_factory=list)
    emotional_incoherences: list = field(default_factory=list)
    sentiment_arcs: list = field(default_factory=list)  # Arco emocional por capítulo
    pacing_analysis: dict = field(default_factory=dict)  # Análisis de ritmo narrativo

    # Alertas
    alerts: list = field(default_factory=list)

    # Métricas
    stats: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    # Tracking de fases completadas
    completed_phases: set = field(default_factory=set)
    skipped_phases: set = field(default_factory=set)

    # Lock para acceso thread-safe a entity_map
    _entity_map_lock: threading.Lock = field(default_factory=threading.Lock)

    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    phase_times: dict = field(default_factory=dict)

    def get_entity_id(self, name: str) -> int | None:
        """Acceso thread-safe a entity_map."""
        with self._entity_map_lock:
            return self.entity_map.get(name.lower())

    def get_entity_map_snapshot(self) -> dict:
        """Copia inmutable del entity_map para uso en threads."""
        with self._entity_map_lock:
            return dict(self.entity_map)


@dataclass
class UnifiedReport:
    """Informe completo del análisis unificado."""

    project_id: int
    session_id: int
    document_path: str
    fingerprint: str

    # Resultados principales
    entities: list = field(default_factory=list)
    attributes: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    interactions: list = field(default_factory=list)
    interaction_patterns: list = field(default_factory=list)
    alerts: list = field(default_factory=list)

    # Estructura
    chapters: list = field(default_factory=list)
    dialogues: list = field(default_factory=list)

    # Calidad
    spelling_issues: list = field(default_factory=list)
    grammar_issues: list = field(default_factory=list)
    repetitions: list = field(default_factory=list)
    coherence_breaks: list = field(default_factory=list)
    register_changes: list = field(default_factory=list)

    # Análisis avanzado
    emotional_incoherences: list = field(default_factory=list)
    voice_profiles: list = field(default_factory=list)
    knowledge_relations: list = field(default_factory=list)
    sentiment_arcs: list = field(default_factory=list)
    pacing_analysis: dict = field(default_factory=dict)

    # Métricas
    stats: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    phase_times: dict = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class UnifiedAnalysisPipeline:
    """
    Pipeline unificado que orquesta todos los analizadores.

    Optimizaciones:
    - Dialogue hints mejoran NER
    - Paralelización donde es posible
    - Contexto compartido evita recomputación
    - Fases opcionales para flexibilidad
    """

    def __init__(self, config: UnifiedConfig | None = None):
        self.config = config or UnifiedConfig()
        self._executor = None
        self._is_low_vram = False
        self._memory_monitor = MemoryMonitor(
            warning_threshold_mb=self.config.memory_warning_mb,
        )
        self._memory_monitor.enabled = self.config.enable_memory_monitoring

        # Detectar si estamos en un sistema con poca VRAM
        self._detect_hardware_limits()

    def _detect_hardware_limits(self) -> None:
        """Detecta limitaciones de hardware y ajusta configuración."""
        try:
            from ..core.device import MIN_SAFE_VRAM_GB, get_device_detector

            detector = get_device_detector()
            device = detector.detect_best_device("auto")

            if device.is_low_vram:
                self._is_low_vram = True
                # Reducir workers paralelos para evitar saturación de GPU
                if self.config.max_workers > 2:
                    logger.warning(
                        f"GPU con poca VRAM ({device.memory_gb:.1f}GB < {MIN_SAFE_VRAM_GB}GB). "
                        f"Reduciendo workers paralelos de {self.config.max_workers} a 2."
                    )
                    self.config.max_workers = 2
        except Exception as e:
            logger.debug(f"Error detecting hardware limits: {e}")

    def _clear_gpu_memory_if_needed(self) -> None:
        """Limpia memoria GPU en sistemas con poca VRAM."""
        if self._is_low_vram:
            try:
                from ..core.device import clear_gpu_memory

                clear_gpu_memory()
                logger.debug("GPU memory cleared between phases")
            except Exception as e:
                logger.debug(f"Error clearing GPU memory: {e}")

    def analyze(
        self,
        document_path: str | Path,
        project_name: str | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> Result[UnifiedReport]:
        """
        Ejecuta el análisis completo unificado.

        Args:
            document_path: Ruta al documento
            project_name: Nombre del proyecto (opcional)
            progress_callback: Callback de progreso (0.0-1.0, mensaje)

        Returns:
            Result con UnifiedReport
        """
        path = Path(document_path)
        context = AnalysisContext(
            document_path=str(path.absolute()),
            start_time=datetime.now(),
        )

        logger.info(f"Starting unified analysis: {path.name}")

        try:
            # ========== FASE 1: PARSING Y ESTRUCTURA ==========
            if progress_callback:
                progress_callback(0.0, "Parseando documento...")

            phase_result = self._run_phase(
                "parsing",
                self._phase_1_parsing,
                context,
                args=(path, project_name, context),
                is_fatal=True,
            )
            if phase_result.is_failure:
                return Result.failure(phase_result.error)

            self._clear_gpu_memory_if_needed()

            # ========== FASE 2: EXTRACCIÓN BASE ==========
            if progress_callback:
                progress_callback(0.15, "Extracción base...")

            precondition = self._check_precondition_text(context, "base_extraction")
            if precondition.is_failure:
                context.errors.append(precondition.error)
            else:
                self._run_phase(
                    "base_extraction",
                    self._phase_2_base_extraction,
                    context,
                    args=(context,),
                )
            self._clear_gpu_memory_if_needed()

            # ========== FASE 3: RESOLUCIÓN Y FUSIÓN ==========
            if progress_callback:
                progress_callback(0.35, "Resolviendo referencias...")

            precondition = self._check_precondition_entities(context, "resolution")
            if precondition.is_failure:
                context.errors.append(precondition.error)
            else:
                self._run_phase(
                    "resolution",
                    self._phase_3_resolution,
                    context,
                    args=(context,),
                )
            self._clear_gpu_memory_if_needed()

            # ========== FASE 4: EXTRACCIÓN PROFUNDA ==========
            if progress_callback:
                progress_callback(0.50, "Extracción profunda...")

            precondition = self._check_precondition_entities(context, "deep_extraction")
            if precondition.is_failure:
                context.errors.append(precondition.error)
            else:
                self._run_phase(
                    "deep_extraction",
                    self._phase_4_deep_extraction,
                    context,
                    args=(context,),
                )
            self._clear_gpu_memory_if_needed()

            # ========== FASE 5: ANÁLISIS DE CALIDAD ==========
            if progress_callback:
                progress_callback(0.70, "Análisis de calidad...")

            # Calidad solo requiere texto, no entidades
            precondition = self._check_precondition_text(context, "quality")
            if precondition.is_failure:
                context.errors.append(precondition.error)
            else:
                self._run_phase(
                    "quality",
                    self._phase_5_quality,
                    context,
                    args=(context,),
                )
            self._clear_gpu_memory_if_needed()

            # ========== FASE 6: CONSISTENCIA Y ALERTAS ==========
            if progress_callback:
                progress_callback(0.85, "Verificando consistencia...")

            precondition = self._check_precondition_entities(context, "consistency")
            if precondition.is_failure:
                context.errors.append(precondition.error)
            else:
                self._run_phase(
                    "consistency",
                    self._phase_6_consistency,
                    context,
                    args=(context,),
                )

            # ========== GENERAR ALERTAS ==========
            if self.config.create_alerts:
                if progress_callback:
                    progress_callback(0.95, "Generando alertas...")

                self._generate_all_alerts(context)

            # ========== ENRIQUECIMIENTO DE CAPÍTULOS ==========
            self._enrich_chapter_metrics(context)

            # ========== SINCRONIZAR CONTADORES DE MENCIONES ==========
            try:
                from ..entities.repository import get_entity_repository

                entity_repo = get_entity_repository()
                reconciled = entity_repo.reconcile_all_mention_counts(context.project_id)
                context.stats["mention_counts_reconciled"] = reconciled
                logger.info(f"Reconciled mention_count for {reconciled} entities")
            except Exception as e:
                logger.warning(f"Failed to reconcile mention counts: {e}")

            # ========== FINALIZAR ==========
            if progress_callback:
                progress_callback(1.0, "Análisis completado")

            # Log resumen de fases y memoria
            self._log_phase_summary(context)
            self._log_memory_summary(context)

            report = self._build_report(context)

            if context.errors:
                return Result.partial(report, context.errors)

            return Result.success(report)

        except Exception as e:
            error = NarrativeError(
                message=f"Unexpected error in unified analysis: {str(e)}",
                severity=ErrorSeverity.FATAL,
            )
            logger.exception("Unexpected error in unified analysis")
            return Result.failure(error)

    # =========================================================================
    # VALIDACIÓN DE FASES Y EJECUCIÓN CONTROLADA
    # =========================================================================

    def _run_phase(
        self,
        phase_name: str,
        phase_func: Callable,
        context: AnalysisContext,
        args: tuple = (),
        is_fatal: bool = False,
    ) -> Result[None]:
        """
        Ejecuta una fase con error handling tipado y monitoreo de memoria.

        Captura excepciones y las convierte en PhaseError con contexto.
        Registra la fase como completada o fallida.
        Mide delta de memoria RSS antes/después de cada fase.
        Verifica presión de memoria antes de cada fase y actúa según tier.
        """
        # Pre-fase: verificar presión de memoria
        try:
            from ..core.resource_manager import get_resource_manager

            rm = get_resource_manager()
            pressure = rm.check_memory_pressure()
            if pressure == "danger":
                logger.warning(
                    f"Presión de memoria PELIGROSA antes de '{phase_name}' — "
                    f"intentando liberar memoria"
                )
                rm.relieve_memory_pressure(aggressive=True)
                pressure = rm.check_memory_pressure()
                if pressure == "danger" and not is_fatal:
                    logger.error(
                        f"Memoria insuficiente para '{phase_name}' — saltando fase"
                    )
                    context.skipped_phases.add(phase_name)
                    return Result.failure(
                        f"Memoria insuficiente para fase '{phase_name}'"
                    )
            elif pressure in ("critical", "warning"):
                logger.info(
                    f"Presión de memoria ({pressure}) antes de '{phase_name}' — "
                    f"liberando memoria"
                )
                rm.relieve_memory_pressure(aggressive=(pressure == "critical"))
        except Exception as e:
            logger.debug(f"Error en check de memoria pre-fase: {e}")

        phase_start = datetime.now()
        mem_start = self._memory_monitor.snapshot(phase_name, label="start")

        try:
            result = phase_func(*args)
            elapsed = (datetime.now() - phase_start).total_seconds()
            context.phase_times[phase_name] = elapsed

            mem_end = self._memory_monitor.snapshot(phase_name, label="end")
            mem_delta_str = ""
            if mem_start and mem_end:
                delta = mem_end.memory_mb - mem_start.memory_mb
                mem_delta_str = f", mem: {mem_end.memory_mb:.0f} MB ({delta:+.1f})"

            if result.is_failure:
                context.skipped_phases.add(phase_name)
                if is_fatal:
                    return result
                phase_error = PhaseError(
                    phase_name=phase_name,
                    input_summary=self._summarize_phase_input(context, phase_name),
                    output_summary="Fase falló — sin output",
                    original_error=str(result.error) if result.error else "Unknown",
                )
                context.errors.append(phase_error)
                logger.warning(
                    f"Phase '{phase_name}' failed after {elapsed:.1f}s{mem_delta_str}: "
                    f"{result.error}"
                )
                return result

            context.completed_phases.add(phase_name)
            logger.info(
                f"Phase '{phase_name}' completed in {elapsed:.1f}s{mem_delta_str} — "
                f"{self._summarize_phase_output(context, phase_name)}"
            )
            return result

        except Exception as e:
            elapsed = (datetime.now() - phase_start).total_seconds()
            context.phase_times[phase_name] = elapsed
            self._memory_monitor.snapshot(phase_name, label="end")
            context.skipped_phases.add(phase_name)

            phase_error = PhaseError(
                phase_name=phase_name,
                input_summary=self._summarize_phase_input(context, phase_name),
                output_summary="Excepción no controlada",
                original_error=str(e),
            )
            context.errors.append(phase_error)
            logger.exception(f"Phase '{phase_name}' crashed after {elapsed:.1f}s")

            if is_fatal:
                phase_error.severity = ErrorSeverity.FATAL
                return Result.failure(phase_error)
            return Result.failure(phase_error)

    def _check_precondition_text(self, context: AnalysisContext, phase_name: str) -> Result[None]:
        """Verifica que el texto del documento existe."""
        if not context.full_text or len(context.full_text.strip()) == 0:
            error = PhasePreconditionError(
                phase_name=phase_name,
                missing_data="texto del documento (full_text vacío)",
            )
            context.skipped_phases.add(phase_name)
            return Result.failure(error)
        return Result.success(None)

    def _check_precondition_entities(
        self, context: AnalysisContext, phase_name: str
    ) -> Result[None]:
        """Verifica que hay entidades disponibles (NER funcionó)."""
        if not context.entities:
            word_count = len(context.full_text.split()) if context.full_text else 0
            error = PhasePreconditionError(
                phase_name=phase_name,
                missing_data=(
                    f"entidades (0 entidades para documento de {word_count} palabras). "
                    "NER probablemente falló o no se ejecutó."
                ),
            )
            context.skipped_phases.add(phase_name)
            logger.warning(
                f"Skipping phase '{phase_name}': no entities available "
                f"(document has {word_count} words)"
            )
            return Result.failure(error)
        return Result.success(None)

    def _summarize_phase_input(self, context: AnalysisContext, phase_name: str) -> str:
        """Resumen de datos de entrada para una fase (para diagnóstico)."""
        parts = []
        if context.full_text:
            parts.append(f"text={len(context.full_text)} chars")
        if context.chapters:
            parts.append(f"chapters={len(context.chapters)}")
        if context.entities:
            parts.append(f"entities={len(context.entities)}")
        if context.attributes:
            parts.append(f"attributes={len(context.attributes)}")
        return ", ".join(parts) if parts else "empty"

    def _summarize_phase_output(self, context: AnalysisContext, phase_name: str) -> str:
        """Resumen de datos de salida tras una fase (para diagnóstico)."""
        summaries = {
            "parsing": (f"text={len(context.full_text)} chars, chapters={len(context.chapters)}"),
            "base_extraction": f"entities={len(context.entities)}",
            "resolution": (
                f"coref_chains={len(context.coreference_chains)}, "
                f"entity_map={len(context.entity_map)} entries"
            ),
            "deep_extraction": (
                f"attributes={len(context.attributes)}, relationships={len(context.relationships)}"
            ),
            "quality": (
                f"spelling={len(context.spelling_issues)}, "
                f"grammar={len(context.grammar_issues)}, "
                f"repetitions={len(context.lexical_repetitions)}"
            ),
            "consistency": (
                f"inconsistencies={len(context.inconsistencies)}, "
                f"emotional={len(context.emotional_incoherences)}"
            ),
        }
        return summaries.get(phase_name, "ok")

    def _log_phase_summary(self, context: AnalysisContext) -> None:
        """Log resumen de todas las fases al finalizar el análisis."""
        total_time = sum(context.phase_times.values())
        completed = sorted(context.completed_phases)
        skipped = sorted(context.skipped_phases)
        error_count = len(context.errors)

        logger.info(
            f"Analysis complete in {total_time:.1f}s — "
            f"phases completed: {completed}, "
            f"phases skipped: {skipped}, "
            f"errors: {error_count}"
        )

        if skipped:
            logger.warning(
                f"Skipped phases: {skipped}. Results may be incomplete. Check errors for details."
            )

        for phase, elapsed in sorted(context.phase_times.items()):
            status = "✓" if phase in context.completed_phases else "✗"
            logger.info(f"  {status} {phase}: {elapsed:.1f}s")

    def _log_memory_summary(self, context: AnalysisContext) -> None:
        """Log resumen de uso de memoria al finalizar el análisis."""
        report = self._memory_monitor.get_report()
        if not report.snapshots:
            return

        # Almacenar métricas de memoria en stats
        context.stats["memory_peak_mb"] = round(report.peak_mb, 1)
        context.stats["memory_total_delta_mb"] = round(report.total_delta_mb, 1)
        context.stats["memory_phase_deltas"] = {
            k: round(v, 1) for k, v in report.get_phase_deltas().items()
        }

        logger.info(report.summary())

    # =========================================================================
    # FASE 1: PARSING Y ESTRUCTURA
    # =========================================================================

    def _phase_1_parsing(
        self, path: Path, project_name: str | None, context: AnalysisContext
    ) -> Result[None]:
        """
        Fase 1: Parsing, estructura y detección de diálogos.

        El orden es importante:
        1. Parsear documento
        2. Detectar estructura (capítulos)
        3. Detectar diálogos → extrae speaker_hints para mejorar NER
        """
        phase_start = datetime.now()

        # 1.1 Validar y parsear
        if not path.exists():
            return Result.failure(
                NarrativeError(message=f"Document not found: {path}", severity=ErrorSeverity.FATAL)
            )

        try:
            from ..parsers.base import detect_format, get_parser
            from ..persistence.document_fingerprint import generate_fingerprint
            from ..persistence.project import ProjectManager
            from ..persistence.session import SessionManager

            parser = get_parser(path)
            parse_result = parser.parse(path)
            if parse_result.is_failure:
                return Result.failure(parse_result.error)

            raw_doc = parse_result.value
            context.raw_document = raw_doc
            context.full_text = raw_doc.full_text
            context.stats["total_characters"] = len(context.full_text)

            # 1.2 Fingerprint
            fingerprint = generate_fingerprint(context.full_text)
            context.fingerprint = fingerprint.full_hash

            # 1.3 Proyecto
            name = project_name or path.stem
            project_mgr = ProjectManager()

            existing = project_mgr.get_by_fingerprint(fingerprint.full_hash)
            if existing:
                context.project_id = existing.id
                if self.config.force_reanalysis:
                    self._clear_project_data(context.project_id)
            else:
                doc_format = detect_format(path)
                create_result = project_mgr.create_from_document(
                    text=context.full_text,
                    name=name,
                    document_format=doc_format.value,
                    document_path=path,
                    check_existing=False,
                )
                if create_result.is_failure:
                    return Result.failure(create_result.error)
                context.project_id = create_result.value.id

            # 1.4 Sesión
            session_mgr = SessionManager(project_id=context.project_id)
            session = session_mgr.start()
            context.session_id = session.id

            # 1.5 Estructura
            if self.config.run_structure:
                self._detect_structure(context)

            # 1.6 Clasificación de documento
            if self.config.run_document_classification:
                self._classify_document(context)

            # 1.7 Diálogos - CRÍTICO: Antes de NER para speaker hints
            if self.config.run_dialogue_detection:
                self._detect_dialogues(context)

            context.phase_times["parsing"] = (datetime.now() - phase_start).total_seconds()
            return Result.success(None)

        except Exception as e:
            return Result.failure(
                NarrativeError(message=f"Parsing failed: {str(e)}", severity=ErrorSeverity.FATAL)
            )

    def _detect_structure(self, context: AnalysisContext) -> None:
        """Detectar capítulos y escenas."""
        try:
            from ..parsers.structure_detector import StructureDetector

            detector = StructureDetector()
            result = detector.detect(context.raw_document)

            if result.is_success and hasattr(result.value, "chapters"):
                for ch in result.value.chapters:
                    content = ch.get_text(context.full_text)
                    context.chapters.append(
                        {
                            "number": ch.number,
                            "title": ch.title,
                            "content": content,
                            "start_char": ch.start_char,
                            "end_char": ch.end_char,
                            "word_count": len(content.split()),
                        }
                    )
                context.stats["chapters"] = len(context.chapters)

        except Exception as e:
            logger.warning(f"Structure detection failed: {e}")

    def _classify_document(self, context: AnalysisContext) -> None:
        """
        Clasificar el tipo de documento para ajustar el análisis.

        Detecta si es:
        - Ficción (novela, cuento)
        - Ensayo
        - Autoayuda
        - Técnico (manual)
        - Memorias
        - Libro de cocina
        - Académico

        Esto afecta cómo se interpretan las entidades y alertas.
        """
        try:
            from ..parsers.document_classifier import classify_document

            result = classify_document(context.full_text)

            context.document_type = result.document_type.value
            context.document_classification = {
                "type": result.document_type.value,
                "confidence": result.confidence,
                "indicators": result.indicators[:10],  # Top 10 indicadores
                "recommended_settings": result.recommended_settings,
            }

            context.stats["document_type"] = result.document_type.value
            context.stats["document_type_confidence"] = result.confidence

            logger.info(
                f"Document classified as {result.document_type.value} "
                f"(confidence: {result.confidence:.2f})"
            )

            # Opcionalmente ajustar configuración según tipo de documento
            self._adjust_config_for_document_type(result.document_type.value)

        except ImportError:
            logger.debug("Document classifier not available")
        except Exception as e:
            logger.warning(f"Document classification failed: {e}")

    def _adjust_config_for_document_type(self, document_type: str) -> None:
        """
        Ajusta configuración según tipo de documento detectado.

        Por ejemplo, para documentos técnicos desactiva el análisis de
        emociones de personajes (no tiene sentido).
        """
        # No hacer ajustes automáticos agresivos - el usuario puede
        # tener razones para querer ciertos análisis.
        # Solo logging informativo.
        if document_type in ("technical", "cookbook", "academic"):
            if self.config.run_emotional:
                logger.info(
                    f"Note: Emotional coherence analysis enabled for {document_type} "
                    f"document - results may not be relevant"
                )
            if self.config.run_focalization:
                logger.info(
                    f"Note: Focalization analysis enabled for {document_type} "
                    f"document - results may not be relevant"
                )

    def _detect_dialogues(self, context: AnalysisContext) -> None:
        """
        Detectar diálogos y extraer speaker hints.

        Los speaker hints se usan para mejorar NER:
        - "—Ven aquí —dijo María." → speaker_hint["María"] en esa posición
        - Ayuda a confirmar entidades de tipo PERSON
        """
        try:
            from ..nlp.dialogue import detect_dialogues

            result = detect_dialogues(context.full_text)

            if result.is_success and result.value.dialogues:
                for dialogue in result.value.dialogues:
                    context.dialogues.append(
                        {
                            "text": dialogue.text,
                            "start_char": dialogue.start_char,
                            "end_char": dialogue.end_char,
                            "type": dialogue.dialogue_type.value
                            if hasattr(dialogue.dialogue_type, "value")
                            else str(dialogue.dialogue_type),
                            "speaker_hint": dialogue.speaker_hint,
                        }
                    )

                    # Extraer speaker hints para NER
                    if dialogue.speaker_hint:
                        context.speaker_hints[dialogue.start_char] = dialogue.speaker_hint

                context.stats["dialogues"] = len(context.dialogues)
                context.stats["speaker_hints"] = len(context.speaker_hints)
                logger.info(
                    f"Detected {len(context.dialogues)} dialogues, {len(context.speaker_hints)} speaker hints"
                )

        except Exception as e:
            logger.warning(f"Dialogue detection failed: {e}")

    # =========================================================================
    # FASE 2: EXTRACCIÓN BASE
    # =========================================================================

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

    # =========================================================================
    # FASE 3: RESOLUCIÓN Y FUSIÓN
    # =========================================================================

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
            from ..nlp.coreference_resolver import CorefConfig, resolve_coreferences_voting

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

            # Convertir diálogos dict a objetos para compatibilidad con getattr()
            dialogue_objects = []
            for d in context.dialogues:
                dialogue_objects.append(
                    SimpleNamespace(
                        text=d.get("text", ""),
                        start_char=d.get("start_char", 0),
                        end_char=d.get("end_char", 0),
                        chapter=d.get("chapter", 1),
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
                    speaker = dialogue.get("speaker_hint", "")
                    if speaker:
                        speaker_lower = speaker.lower()
                        if speaker_lower in context.mention_to_entity:
                            dialogue["resolved_speaker"] = context.mention_to_entity[speaker_lower]
                            dialogue["attribution_method"] = "coreference"
                        else:
                            dialogue["resolved_speaker"] = speaker
                            dialogue["attribution_method"] = "hint_only"

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

    # =========================================================================
    # FASE 4: EXTRACCIÓN PROFUNDA
    # =========================================================================

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

    # =========================================================================
    # FASE 5: ANÁLISIS DE CALIDAD
    # =========================================================================

    def _phase_5_quality(self, context: AnalysisContext) -> Result[None]:
        """
        Fase 5: Ortografía, gramática, repeticiones.

        Parallelizable: Cada análisis es independiente.
        """
        phase_start = datetime.now()

        tasks = []

        if self.config.run_spelling:
            tasks.append(("spelling", self._run_spelling_check))

        if self.config.run_grammar:
            tasks.append(("grammar", self._run_grammar_check))

        if self.config.run_lexical_repetitions:
            tasks.append(("lexical_rep", self._run_lexical_repetitions))

        if self.config.run_semantic_repetitions:
            tasks.append(("semantic_rep", self._run_semantic_repetitions))

        if self.config.run_coherence:
            tasks.append(("coherence", self._run_coherence_check))

        if self.config.run_register_analysis:
            tasks.append(("register", self._run_register_analysis))

        if self.config.run_pacing:
            tasks.append(("pacing", self._run_pacing_analysis))

        if self.config.run_sticky_sentences:
            tasks.append(("sticky", self._run_sticky_sentences))

        # Ejecutar en paralelo si está configurado
        if self.config.parallel_extraction and len(tasks) > 1:
            self._run_parallel_tasks(tasks, context)
        else:
            for name, func in tasks:
                try:
                    func(context)
                except Exception as e:
                    logger.warning(f"{name} failed: {e}")

        context.phase_times["quality"] = (datetime.now() - phase_start).total_seconds()
        return Result.success(None)

    @staticmethod
    def _find_chapter_for_position(
        position: int, chapters: list
    ) -> int | None:
        """
        Mapea una posición global de carácter al número de capítulo correspondiente.

        Args:
            position: Posición (start_char) en el texto completo
            chapters: Lista de objetos Chapter con start_char, end_char, number

        Returns:
            Número de capítulo o None si no se encuentra
        """
        for ch in chapters:
            if ch.start_char <= position < ch.end_char:
                return ch.number
        return None

    def _assign_chapters_to_issues(
        self, issues: list, chapters: list
    ) -> None:
        """
        Asigna el número de capítulo a cada issue según su posición global.

        Args:
            issues: Lista de SpellingIssue o GrammarIssue con start_char
            chapters: Lista de Chapter con start_char, end_char, number
        """
        if not chapters:
            return
        for issue in issues:
            if hasattr(issue, "chapter") and hasattr(issue, "start_char"):
                issue.chapter = self._find_chapter_for_position(
                    issue.start_char, chapters
                )

    def _run_spelling_check(self, context: AnalysisContext) -> None:
        """Verificar ortografía."""
        try:
            from ..nlp.orthography import get_spelling_checker

            checker = get_spelling_checker()

            # Añadir entidades conocidas al diccionario
            known_entities = [e.canonical_name for e in context.entities]
            checker.add_to_dictionary(known_entities)

            result = checker.check(
                context.full_text,
                known_entities=known_entities,
                use_llm=self.config.use_llm,
            )

            if result.is_success:
                # Filtrar por confianza
                context.spelling_issues = [
                    issue
                    for issue in result.value.issues
                    if issue.confidence >= self.config.spelling_min_confidence
                ]
                # Mapear posición global → capítulo
                self._assign_chapters_to_issues(
                    context.spelling_issues, context.chapters
                )
                context.stats["spelling_issues"] = len(context.spelling_issues)

        except Exception as e:
            logger.warning(f"Spelling check failed: {e}")

    def _run_grammar_check(self, context: AnalysisContext) -> None:
        """Verificar gramática."""
        try:
            from ..nlp.grammar import get_grammar_checker

            checker = get_grammar_checker()
            result = checker.check(
                context.full_text,
                use_llm=self.config.use_llm,
            )

            if result.is_success:
                context.grammar_issues = [
                    issue
                    for issue in result.value.issues
                    if issue.confidence >= self.config.grammar_min_confidence
                ]
                # Mapear posición global → capítulo
                self._assign_chapters_to_issues(
                    context.grammar_issues, context.chapters
                )
                context.stats["grammar_issues"] = len(context.grammar_issues)

        except Exception as e:
            logger.warning(f"Grammar check failed: {e}")

    def _run_lexical_repetitions(self, context: AnalysisContext) -> None:
        """Detectar repeticiones léxicas."""
        try:
            from ..nlp.style import get_repetition_detector

            detector = get_repetition_detector()
            result = detector.detect_lexical(
                context.full_text, min_distance=self.config.repetition_min_distance
            )

            if result.is_success:
                context.lexical_repetitions = result.value.repetitions
                context.stats["lexical_repetitions"] = len(context.lexical_repetitions)

        except ImportError:
            # Módulo aún no implementado
            pass
        except Exception as e:
            logger.warning(f"Lexical repetition detection failed: {e}")

    def _run_semantic_repetitions(self, context: AnalysisContext) -> None:
        """Detectar repeticiones semánticas."""
        try:
            from ..nlp.style import get_repetition_detector

            detector = get_repetition_detector()
            result = detector.detect_semantic(
                context.full_text, min_distance=self.config.repetition_min_distance
            )

            if result.is_success:
                context.semantic_repetitions = result.value.repetitions
                context.stats["semantic_repetitions"] = len(context.semantic_repetitions)

        except ImportError:
            # Módulo aún no implementado
            pass
        except Exception as e:
            logger.warning(f"Semantic repetition detection failed: {e}")

    def _run_coherence_check(self, context: AnalysisContext) -> None:
        """Detectar saltos de coherencia narrativa entre párrafos/segmentos."""
        try:
            from ..nlp.style import get_coherence_detector

            detector = get_coherence_detector(
                similarity_threshold=self.config.coherence_similarity_threshold
            )

            # Analizar por capítulos si hay estructura detectada
            if context.chapters:
                chapters_data = [
                    {
                        "id": ch.get("number"),
                        "content": ch.get("content", ""),
                        "title": ch.get("title", ""),
                    }
                    for ch in context.chapters
                ]
                result = detector.detect_in_chapters(chapters_data)
            else:
                # Analizar texto completo
                result = detector.detect(context.full_text)

            if result.is_success:
                context.coherence_breaks = result.value.breaks
                context.stats["coherence_breaks"] = len(context.coherence_breaks)
                context.stats["coherence_avg_similarity"] = result.value.avg_similarity
                context.stats["coherence_min_similarity"] = result.value.min_similarity

        except ImportError:
            logger.debug("Coherence detector not available")
        except Exception as e:
            logger.warning(f"Coherence check failed: {e}")

    def _run_register_analysis(self, context: AnalysisContext) -> None:
        """
        Detectar cambios de registro narrativo (formal/coloquial/técnico/poético).

        Útil para:
        - Detectar inconsistencias tonales en la narración
        - Identificar saltos abruptos de estilo
        - Alertar sobre mezcla inadecuada de registros
        """
        try:
            from ..voice.register import (
                RegisterAnalyzer,
                RegisterChangeDetector,
            )

            detector = RegisterChangeDetector()

            # Preparar segmentos: (texto, capítulo, posición, es_diálogo)
            segments = []

            if context.chapters:
                for ch in context.chapters:
                    content = ch.get("content", "")
                    chapter_num = ch.get("number", 1)
                    start_char = ch.get("start_char", 0)

                    # Dividir en párrafos para análisis granular
                    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                    current_pos = start_char

                    for para in paragraphs:
                        # Detectar si es diálogo (empieza con guión o comillas)
                        is_dialogue = para.startswith(("—", "-", "«", '"', "'"))

                        if len(para) > 50:  # Solo párrafos sustanciales
                            segments.append((para, chapter_num, current_pos, is_dialogue))

                        current_pos += len(para) + 2  # +2 por \n\n
            else:
                # Sin estructura de capítulos, analizar texto completo
                paragraphs = [p.strip() for p in context.full_text.split("\n\n") if p.strip()]
                current_pos = 0

                for para in paragraphs:
                    is_dialogue = para.startswith(("—", "-", "«", '"', "'"))
                    if len(para) > 50:
                        segments.append((para, 1, current_pos, is_dialogue))
                    current_pos += len(para) + 2

            if not segments:
                return

            # Analizar documento
            analyses = detector.analyze_document(segments)

            # Detectar cambios significativos (medium o superior)
            changes = detector.detect_changes(min_severity="medium")

            context.register_changes = [ch.to_dict() for ch in changes]
            context.stats["register_segments_analyzed"] = len(analyses)
            context.stats["register_changes_detected"] = len(changes)

            # Obtener distribución de registros
            summary = detector.get_summary()
            context.stats["register_distribution"] = summary.get("distribution", {})
            context.stats["dominant_register"] = summary.get("dominant_register")

            logger.info(f"Register analysis: {len(changes)} changes in {len(analyses)} segments")

        except ImportError as e:
            logger.debug(f"Register analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Register analysis failed: {e}")

    def _run_pacing_analysis(self, context: AnalysisContext) -> None:
        """
        Analizar ritmo narrativo del documento.

        Detecta:
        - Capítulos desproporcionados
        - Ratio diálogo/narración
        - Bloques de texto densos
        - Desequilibrios estructurales
        """
        if not context.chapters:
            return

        try:
            from ..analysis.pacing import analyze_pacing

            result = analyze_pacing(
                chapters=context.chapters,
                full_text=context.full_text,
            )

            context.pacing_analysis = result.to_dict()

            # Estadísticas
            context.stats["pacing_issues"] = len(result.issues)
            if result.summary:
                context.stats["avg_chapter_words"] = result.summary.get("avg_chapter_words", 0)
                context.stats["chapter_word_variance"] = result.summary.get(
                    "chapter_word_variance", 0
                )
                context.stats["avg_dialogue_ratio"] = result.summary.get("avg_dialogue_ratio", 0)

            logger.info(
                f"Pacing analysis: {len(result.issues)} issues in {len(context.chapters)} chapters"
            )

        except ImportError as e:
            logger.debug(f"Pacing analyzer not available: {e}")
        except Exception as e:
            logger.warning(f"Pacing analysis failed: {e}")

    def _run_sticky_sentences(self, context: AnalysisContext) -> None:
        """Detectar oraciones pesadas (sticky sentences)."""
        try:
            from ..nlp.style.sticky_sentences import get_sticky_sentence_detector

            detector = get_sticky_sentence_detector()

            all_sticky = []
            for ch in context.chapters:
                ch_num = ch.chapter_number if hasattr(ch, "chapter_number") else 0
                ch_content = ch.content if hasattr(ch, "content") else str(ch)
                result = detector.analyze(ch_content, chapter=ch_num)
                if result.is_success:
                    all_sticky.extend(result.value.sticky_sentences)

            context.sticky_sentences = all_sticky
            context.stats["sticky_sentences"] = len(all_sticky)
            logger.info(f"Sticky sentences: {len(all_sticky)} detected")

        except ImportError as e:
            logger.debug(f"Sticky sentence detector not available: {e}")
        except Exception as e:
            logger.warning(f"Sticky sentence analysis failed: {e}")

    # =========================================================================
    # FASE 6: CONSISTENCIA Y ALERTAS
    # =========================================================================

    def _phase_6_consistency(self, context: AnalysisContext) -> Result[None]:
        """Fase 6: Análisis de consistencia."""
        phase_start = datetime.now()

        try:
            if self.config.run_consistency and context.attributes:
                self._run_attribute_consistency(context)

            if self.config.run_temporal_consistency and context.temporal_markers:
                self._run_temporal_consistency(context)

            if self.config.run_focalization and context.focalization_segments:
                self._run_focalization_consistency(context)

            if self.config.run_voice_deviations and context.voice_profiles:
                self._run_voice_deviation_detection(context)

            if self.config.run_emotional and context.chapters:
                self._run_emotional_coherence(context)

            if self.config.run_sentiment and context.chapters:
                self._run_sentiment_analysis(context)

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

            if result.is_success:
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
        """Verificar violaciones de focalización si hay declaraciones."""
        try:
            from ..focalization.declaration import FocalizationDeclarationService
            from ..focalization.violations import FocalizationViolationDetector

            service = FocalizationDeclarationService()
            declarations = service.get_all_declarations(context.project_id)

            if not declarations:
                logger.debug("No focalization declarations, skipping check")
                return

            # Crear detector con entidades
            detector = FocalizationViolationDetector(service, context.entities)

            all_violations = []
            for ch in context.chapters:
                content = ch.get("content", "")
                chapter_num = ch.get("number", 0)

                if content:
                    violations = detector.detect_violations(
                        project_id=context.project_id,
                        text=content,
                        chapter=chapter_num,
                    )
                    all_violations.extend(violations)

            if all_violations:
                context.stats["focalization_violations"] = len(all_violations)
                logger.info(f"Found {len(all_violations)} focalization violations")

                # Almacenar para generación de alertas
                if not hasattr(context, "focalization_violations"):
                    context.focalization_violations = []
                context.focalization_violations.extend(all_violations)

        except ImportError:
            logger.debug("Focalization module not available")
        except Exception as e:
            logger.warning(f"Focalization consistency check failed: {e}")

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
            dialogues_by_chapter = {}
            for d in context.dialogues:
                chapter = d.get("chapter", 0)
                if chapter not in dialogues_by_chapter:
                    dialogues_by_chapter[chapter] = []
                dialogues_by_chapter[chapter].append(d)

            # Analizar cada capítulo
            for ch in context.chapters:
                chapter_num = ch.get("number", 0)
                content = ch.get("content", "")

                if not content:
                    continue

                chapter_dialogues = dialogues_by_chapter.get(chapter_num, [])

                # El checker analiza el capítulo completo
                # analyze_chapter() retorna list[EmotionalIncoherence] directamente
                result = checker.analyze_chapter(
                    chapter_text=content,
                    chapter_id=chapter_num,
                    dialogues=chapter_dialogues,
                    entity_names=[e.canonical_name for e in context.entities],
                )

                # Manejar tanto Result como list directa
                if hasattr(result, "is_success"):
                    incoherences = result.value if result.is_success else []
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
                arc_result = analyzer.analyze_emotional_arc(
                    text=content,
                    chapter_id=chapter_num,
                    segment_size=500,  # Dividir en segmentos de ~500 chars
                )

                if arc_result.is_success and arc_result.value:
                    arc = arc_result.value
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

    # =========================================================================
    # GENERACIÓN DE ALERTAS
    # =========================================================================

    def _generate_all_alerts(self, context: AnalysisContext) -> None:
        """Generar todas las alertas desde los issues detectados."""
        try:
            from ..alerts.engine import get_alert_engine
            from ..alerts.models import AlertCategory, AlertSeverity

            engine = get_alert_engine()

            # Alertas de inconsistencias de atributos
            for inc in context.inconsistencies:
                # Convertir attribute_key enum a string para la API
                attr_key_str = (
                    inc.attribute_key.value
                    if hasattr(inc.attribute_key, "value")
                    else str(inc.attribute_key)
                )
                result = engine.create_from_attribute_inconsistency(
                    project_id=context.project_id,
                    entity_name=inc.entity_name,
                    entity_id=context.entity_map.get(inc.entity_name.lower(), 0),
                    attribute_key=attr_key_str,
                    value1=inc.value1,
                    value2=inc.value2,
                    value1_source={
                        "chapter": inc.value1_chapter,
                        "excerpt": inc.value1_excerpt,
                        "start_char": inc.value1_position,
                        "end_char": inc.value1_position + len(inc.value1_excerpt)
                        if inc.value1_excerpt
                        else 0,
                    },
                    value2_source={
                        "chapter": inc.value2_chapter,
                        "excerpt": inc.value2_excerpt,
                        "start_char": inc.value2_position,
                        "end_char": inc.value2_position + len(inc.value2_excerpt)
                        if inc.value2_excerpt
                        else 0,
                    },
                    explanation=inc.explanation,
                    confidence=inc.confidence,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de inconsistencias temporales
            for tinc in context.temporal_inconsistencies:
                inc_type = (
                    tinc.inconsistency_type.value
                    if hasattr(tinc.inconsistency_type, "value")
                    else str(tinc.inconsistency_type)
                )
                result = engine.create_from_temporal_inconsistency(
                    project_id=context.project_id,
                    inconsistency_type=inc_type,
                    description=tinc.description,
                    explanation=tinc.suggestion or tinc.description,
                    chapter=tinc.chapter,
                    start_char=tinc.position,
                    end_char=tinc.position + 50,  # Approximate span
                    excerpt=tinc.expected or "",
                    confidence=tinc.confidence,
                    extra_data={
                        "expected": tinc.expected,
                        "found": tinc.found,
                        "severity": tinc.severity.value
                        if hasattr(tinc.severity, "value")
                        else str(tinc.severity),
                        "methods_agreed": tinc.methods_agreed,
                    },
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de ortografía
            for issue in context.spelling_issues:
                result = engine.create_from_spelling_issue(
                    project_id=context.project_id,
                    word=issue.word,
                    start_char=issue.start_char,
                    end_char=issue.end_char,
                    sentence=issue.sentence,
                    error_type=issue.error_type.value,
                    suggestions=issue.suggestions,
                    confidence=issue.confidence,
                    explanation=issue.explanation,
                    chapter=issue.chapter,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de gramática
            for issue in context.grammar_issues:
                result = engine.create_from_grammar_issue(
                    project_id=context.project_id,
                    text=issue.text,
                    start_char=issue.start_char,
                    end_char=issue.end_char,
                    sentence=issue.sentence,
                    error_type=issue.error_type.value,
                    suggestion=issue.suggestion,
                    confidence=issue.confidence,
                    explanation=issue.explanation,
                    rule_id=issue.rule_id,
                    chapter=issue.chapter,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de repeticiones léxicas (word echo)
            for rep in context.lexical_repetitions:
                word = rep.word if hasattr(rep, "word") else str(rep)
                occurrences = []
                if hasattr(rep, "occurrences"):
                    for occ in rep.occurrences:
                        if hasattr(occ, "start_char"):
                            occurrences.append(
                                {
                                    "start_char": occ.start_char,
                                    "end_char": occ.end_char,
                                    "context": occ.context[:100]
                                    if hasattr(occ, "context") and occ.context
                                    else "",
                                }
                            )
                        elif isinstance(occ, dict):
                            occurrences.append(occ)

                result = engine.create_from_word_echo(
                    project_id=context.project_id,
                    word=word,
                    occurrences=occurrences,
                    min_distance=self.config.repetition_min_distance,
                    chapter=rep.chapter if hasattr(rep, "chapter") else None,
                    confidence=rep.confidence if hasattr(rep, "confidence") else 0.7,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de repeticiones semánticas
            for rep in context.semantic_repetitions:
                word = rep.word if hasattr(rep, "word") else str(rep)
                count = rep.count if hasattr(rep, "count") else 0
                result = engine.create_alert(
                    project_id=context.project_id,
                    alert_type="style_semantic_repetition",
                    category=AlertCategory.STYLE,
                    severity=AlertSeverity.INFO,
                    title=f"Repetición semántica: '{word}'",
                    description=f"La palabra '{word}' y sus sinónimos aparecen {count} veces en proximidad",
                    explanation=f"Se detectó repetición semántica de '{word}' y palabras similares. Esto puede indicar sobrecarga conceptual en el texto.",
                    extra_data={
                        "word": word,
                        "similar_words": rep.similar_words if hasattr(rep, "similar_words") else [],
                        "count": count,
                        "repetition_type": "semantic",
                    },
                    confidence=rep.confidence if hasattr(rep, "confidence") else 0.6,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de saltos de coherencia narrativa
            for brk in context.coherence_breaks:
                severity_map = {
                    "high": AlertSeverity.WARNING,
                    "medium": AlertSeverity.INFO,
                    "low": AlertSeverity.HINT,
                }
                severity = severity_map.get(
                    brk.severity.value if hasattr(brk.severity, "value") else brk.severity,
                    AlertSeverity.INFO,
                )

                result = engine.create_alert(
                    project_id=context.project_id,
                    alert_type="coherence_break",
                    category=AlertCategory.STYLE,
                    severity=severity,
                    title=f"Salto de coherencia: {brk.break_type.value if hasattr(brk.break_type, 'value') else brk.break_type}",
                    description="Posible discontinuidad narrativa entre segmentos",
                    explanation=brk.explanation,
                    extra_data={
                        "break_type": brk.break_type.value
                        if hasattr(brk.break_type, "value")
                        else str(brk.break_type),
                        "similarity_score": brk.similarity_score,
                        "expected_similarity": brk.expected_similarity,
                        "text_before": brk.text_before[:100] if brk.text_before else "",
                        "text_after": brk.text_after[:100] if brk.text_after else "",
                        "position_char": brk.position_char,
                        "chapter_id": brk.chapter_id,
                    },
                    confidence=brk.confidence,
                    position=brk.position_char,
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de desviaciones de voz/comportamiento
            for deviation in context.voice_deviations:
                entity_name = deviation.get("entity_name", "Personaje")
                severity_str = deviation.get("severity", "medium").upper()
                severity = getattr(AlertSeverity, severity_str, AlertSeverity.MEDIUM)
                explanation = deviation.get("explanation", "Comportamiento fuera de carácter")

                result = engine.create_alert(
                    project_id=context.project_id,
                    alert_type="behavior_deviation",
                    category=AlertCategory.BEHAVIORAL,
                    severity=severity,
                    title=f"Inconsistencia de comportamiento: {entity_name}",
                    description=f"Posible desviación del comportamiento esperado de {entity_name}",
                    explanation=explanation,
                    entity_id=deviation.get("entity_id"),
                    entity_name=entity_name,
                    extra_data={
                        "chapter": deviation.get("chapter"),
                        "violation_text": deviation.get("violation_text"),
                        "expectation": deviation.get("expectation"),
                        "consensus_score": deviation.get("consensus_score"),
                        "detection_methods": deviation.get("detection_methods"),
                    },
                    confidence=deviation.get("consensus_score", 0.5),
                )
                if result.is_success:
                    context.alerts.append(result.value)

            # Alertas de ritmo narrativo (pacing)
            if context.pacing_analysis:
                issues = context.pacing_analysis.get("issues", [])
                for issue in issues:
                    if isinstance(issue, dict):
                        result = engine.create_from_pacing_issue(
                            project_id=context.project_id,
                            issue_type=issue.get("issue_type", "unknown"),
                            severity_level=issue.get("severity", "info"),
                            chapter=issue.get("segment_id"),
                            segment_type=issue.get("segment_type", "chapter"),
                            description=issue.get("description", ""),
                            explanation=issue.get("explanation", ""),
                            suggestion=issue.get("suggestion", ""),
                            actual_value=issue.get("actual_value", 0.0),
                            expected_range=tuple(issue.get("expected_range", (0.0, 0.0))),
                            comparison_value=issue.get("comparison_value"),
                        )
                        if result.is_success:
                            context.alerts.append(result.value)

            # Alertas de oraciones pesadas (sticky sentences)
            for sent in context.sticky_sentences:
                severity_val = (
                    sent.severity.value if hasattr(sent.severity, "value") else str(sent.severity)
                )
                # Solo alertar a partir de severidad medium
                if severity_val in ("medium", "high", "critical"):
                    result = engine.create_from_sticky_sentence(
                        project_id=context.project_id,
                        sentence=sent.text[:200] if len(sent.text) > 200 else sent.text,
                        glue_percentage=sent.glue_percentage,
                        chapter=sent.chapter if hasattr(sent, "chapter") else None,
                        start_char=sent.start_char if hasattr(sent, "start_char") else None,
                        end_char=sent.end_char if hasattr(sent, "end_char") else None,
                        severity_level=severity_val,
                        confidence=0.75,
                    )
                    if result.is_success:
                        context.alerts.append(result.value)

            # Alertas de cambios de registro narrativo
            for change in context.register_changes:
                if isinstance(change, dict):
                    severity = change.get("severity", "medium")
                    if severity in ("medium", "high", "critical"):
                        result = engine.create_from_register_change(
                            project_id=context.project_id,
                            from_register=change.get("from_register", "unknown"),
                            to_register=change.get("to_register", "unknown"),
                            severity_level=severity,
                            chapter=change.get("chapter", 0),
                            position=change.get("position", 0),
                            context_before=change.get("context_before", "")[:200],
                            context_after=change.get("context_after", "")[:200],
                            explanation=change.get("explanation", "Cambio de registro detectado"),
                            confidence=change.get("confidence", 0.7),
                        )
                        if result.is_success:
                            context.alerts.append(result.value)

            # Alertas de variantes de nombres de entidades
            try:
                from ..analysis.name_variant_detector import detect_name_variants
                from ..entities.repository import get_entity_repository

                entity_repo = get_entity_repository()
                mentions_by_entity: dict[int, list] = {}
                for entity in context.entities:
                    eid = getattr(entity, "id", None)
                    if eid is not None:
                        mentions_by_entity[eid] = entity_repo.get_mentions_by_entity(eid)

                dialogue_spans = [
                    (d.get("start_char", 0), d.get("end_char", 0))
                    for d in context.dialogues
                    if d.get("start_char") is not None and d.get("end_char") is not None
                ]

                name_variants = detect_name_variants(
                    entities=context.entities,
                    mentions_by_entity=mentions_by_entity,
                    dialogue_spans=dialogue_spans if dialogue_spans else None,
                )

                for nv in name_variants:
                    result = engine.create_from_name_variant(
                        project_id=context.project_id,
                        entity_id=nv.entity_id,
                        entity_name=nv.entity_name,
                        canonical_form=nv.canonical_form,
                        variant_form=nv.variant_form,
                        canonical_count=nv.canonical_count,
                        variant_count=nv.variant_count,
                        variant_mentions=nv.variant_mentions,
                        all_in_dialogue=nv.all_in_dialogue,
                        confidence=nv.confidence,
                    )
                    if result.is_success:
                        context.alerts.append(result.value)

            except Exception as e:
                logger.warning(f"Name variant detection failed: {e}")

            context.stats["alerts_created"] = len(context.alerts)

        except Exception as e:
            logger.warning(f"Alert generation failed: {e}")

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _run_parallel_tasks(
        self, tasks: list[tuple[str, Callable]], context: AnalysisContext
    ) -> None:
        """
        Ejecutar tareas en paralelo con tracking de errores.

        Cada tarea que falle se registra como warning con su nombre,
        en vez de silenciar el error.
        """
        failed_tasks = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(func, context): name for name, func in tasks}

            for future in as_completed(futures):
                name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    failed_tasks.append(name)
                    logger.warning(f"Parallel task '{name}' failed: {e}", exc_info=True)
                    context.warnings.append(f"Sub-tarea '{name}' falló: {e}")

        if failed_tasks:
            logger.warning(
                f"Parallel execution: {len(failed_tasks)}/{len(tasks)} tasks failed: {failed_tasks}"
            )

    def _persist_attributes(self, context: AnalysisContext) -> None:
        """Persistir atributos en la base de datos."""
        try:
            from ..persistence.database import get_database

            db = get_database()
            persisted = 0

            # Snapshot del entity_map para acceso thread-safe
            entity_map_snapshot = context.get_entity_map_snapshot()

            for attr in context.attributes:
                entity_id = entity_map_snapshot.get(attr.entity_name.lower())
                if not entity_id:
                    continue

                # Determinar categoría del atributo para la columna attribute_type
                attr_key = attr.key.value if hasattr(attr.key, "value") else str(attr.key)
                _PHYSICAL_ATTRS = {
                    "eye_color",
                    "hair_color",
                    "hair_type",
                    "height",
                    "build",
                    "age",
                    "skin",
                    "distinctive_feature",
                }
                _PSYCHOLOGICAL_ATTRS = {"personality"}
                _SOCIAL_ATTRS = {"profession"}
                if attr_key in _PHYSICAL_ATTRS:
                    attr_category = "physical"
                elif attr_key in _PSYCHOLOGICAL_ATTRS:
                    attr_category = "psychological"
                elif attr_key in _SOCIAL_ATTRS:
                    attr_category = "social"
                elif attr_key == "location":
                    attr_category = "location"
                else:
                    attr_category = "other"

                with db.connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO entity_attributes
                        (entity_id, attribute_type, attribute_key, attribute_value, confidence)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            entity_id,
                            attr_category,
                            attr_key,
                            attr.value,
                            attr.confidence if hasattr(attr, "confidence") else 0.8,
                        ),
                    )
                    persisted += 1

            context.stats["attributes_persisted"] = persisted

        except Exception as e:
            logger.warning(f"Attribute persistence failed: {e}")

    def _clear_project_data(self, project_id: int) -> None:
        """Limpiar datos previos del proyecto."""
        try:
            from ..persistence.database import get_database

            db = get_database()
            with db.connection() as conn:
                conn.execute("DELETE FROM alerts WHERE project_id = ?", (project_id,))
                conn.execute(
                    "DELETE FROM entity_attributes WHERE entity_id IN (SELECT id FROM entities WHERE project_id = ?)",
                    (project_id,),
                )
                conn.execute("DELETE FROM entities WHERE project_id = ?", (project_id,))

        except Exception as e:
            logger.warning(f"Failed to clear project data: {e}")

    def _enrich_chapter_metrics(self, context: AnalysisContext) -> None:
        """
        Computa y persiste métricas de enriquecimiento para cada capítulo.

        Métricas: dialogue_ratio, avg_sentence_length, scene_count,
        characters_present_count, dominant_tone, tone_intensity,
        reading_time_minutes.
        """
        if not context.chapters or not context.project_id:
            return

        try:
            from ..persistence.chapter import (
                ChapterRepository,
                compute_chapter_metrics,
            )

            chapter_repo = ChapterRepository()
            db_chapters = chapter_repo.get_by_project(context.project_id)
            if not db_chapters:
                return

            # Nombres de entidades conocidas para conteo de presencia
            entity_names = [
                getattr(e, "canonical_name", "") or getattr(e, "name", "")
                for e in (context.entities or [])
                if getattr(e, "canonical_name", "") or getattr(e, "name", "")
            ]

            enriched_count = 0
            for db_ch in db_chapters:
                content = db_ch.content
                if not content:
                    continue

                metrics = compute_chapter_metrics(content, entity_names or None)
                if metrics and db_ch.id:
                    chapter_repo.update_metrics(db_ch.id, metrics)
                    enriched_count += 1

            if enriched_count > 0:
                logger.info(f"Chapter enrichment: {enriched_count} chapters enriched with metrics")

        except Exception as e:
            logger.warning(f"Chapter enrichment failed (non-fatal): {e}")

    def _build_report(self, context: AnalysisContext) -> UnifiedReport:
        """Construir informe final."""
        return UnifiedReport(
            project_id=context.project_id,
            session_id=context.session_id,
            document_path=context.document_path,
            fingerprint=context.fingerprint,
            entities=context.entities,
            attributes=context.attributes,
            relationships=context.relationships,
            interactions=context.interactions,
            interaction_patterns=context.interaction_patterns,
            alerts=context.alerts,
            chapters=context.chapters,
            dialogues=context.dialogues,
            spelling_issues=context.spelling_issues,
            grammar_issues=context.grammar_issues,
            repetitions=context.lexical_repetitions + context.semantic_repetitions,
            coherence_breaks=context.coherence_breaks,
            register_changes=context.register_changes,
            emotional_incoherences=context.emotional_incoherences,
            voice_profiles=list(context.voice_profiles.values()) if context.voice_profiles else [],
            knowledge_relations=list(context.knowledge_matrix.values())
            if context.knowledge_matrix
            else [],
            sentiment_arcs=context.sentiment_arcs,
            pacing_analysis=context.pacing_analysis,
            stats=context.stats,
            errors=context.errors,
            warnings=context.warnings,
            start_time=context.start_time,
            end_time=datetime.now(),
            phase_times=context.phase_times,
        )


# =============================================================================
# Funciones de conveniencia
# =============================================================================


def run_unified_analysis(
    document_path: str | Path,
    project_name: str | None = None,
    config: UnifiedConfig | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
) -> Result[UnifiedReport]:
    """
    Ejecutar análisis unificado con configuración por defecto.

    Args:
        document_path: Ruta al documento
        project_name: Nombre del proyecto (opcional)
        config: Configuración (opcional)
        progress_callback: Callback de progreso

    Returns:
        Result con UnifiedReport
    """
    pipeline = UnifiedAnalysisPipeline(config)
    return pipeline.analyze(document_path, project_name, progress_callback)
