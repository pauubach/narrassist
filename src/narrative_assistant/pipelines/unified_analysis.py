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
from .ua_alerts import PipelineAlertsMixin
from .ua_consistency import PipelineConsistencyMixin
from .ua_deep_extraction import PipelineDeepExtractionMixin
from .ua_ner import PipelineNERMixin
from .ua_quality import PipelineQualityMixin
from .ua_resolution import PipelineResolutionMixin

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
    run_sentence_energy: bool = True  # Detectar voz pasiva, verbos débiles, baja energía
    run_sensory_report: bool = True  # Detectar déficit de descripciones sensoriales
    run_typography: bool = True  # Detectar errores tipográficos (guiones, comillas, espacios)
    run_pov_check: bool = True  # Detectar cambios de punto de vista narrativo
    run_references_check: bool = False  # Detectar referencias bibliográficas inconsistentes
    run_acronyms_check: bool = True  # Detectar siglas sin definir o inconsistentes

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
    run_vital_status: bool = True  # Detectar personajes fallecidos que reaparecen
    run_character_location: bool = True  # Detectar ubicaciones imposibles de personajes
    run_chekhov: bool = True  # Detectar personajes/elementos introducidos y olvidados
    run_speech_tracking: bool = True  # Character Speech Consistency Tracking (v0.10.13)
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
    sentence_energy_issues: list = field(default_factory=list)  # Oraciones de baja energía
    sensory_report: dict = field(default_factory=dict)  # Reporte de densidad sensorial
    typography_issues: list = field(default_factory=list)  # Errores tipográficos
    pov_issues: list = field(default_factory=list)  # Cambios de punto de vista
    reference_issues: list = field(default_factory=list)  # Problemas de referencias bibliográficas
    acronym_issues: list = field(default_factory=list)  # Siglas inconsistentes
    filler_issues: list = field(default_factory=list)  # Muletillas lingüísticas (FillerDetector)

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
    vital_status_report: Any | None = None  # Reporte de estado vital de personajes
    location_inconsistencies: list = field(default_factory=list)  # Ubicaciones imposibles
    ooc_events: list = field(default_factory=list)  # Eventos fuera de personaje (OOC)
    chekhov_threads: list = field(default_factory=list)  # Hilos narrativos abandonados (Chekhov)
    shallow_characters: list = field(default_factory=list)  # Personajes planos
    knowledge_anachronisms: list = field(default_factory=list)  # Anacronismos de conocimiento
    speech_change_alerts: list = field(default_factory=list)  # Cambios de habla por personaje (v0.10.13)

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


class UnifiedAnalysisPipeline(
    PipelineNERMixin,
    PipelineResolutionMixin,
    PipelineDeepExtractionMixin,
    PipelineQualityMixin,
    PipelineConsistencyMixin,
    PipelineAlertsMixin,
):
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
                return Result.failure(phase_result.error)  # type: ignore[arg-type]

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
                        NarrativeError(
                            message=f"Memoria insuficiente para fase '{phase_name}'",
                            severity=ErrorSeverity.RECOVERABLE,
                        )
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
            result: Result[None] = phase_func(*args)
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
                return Result.failure(parse_result.error)  # type: ignore[arg-type]

            raw_doc = parse_result.value
            context.raw_document = raw_doc
            assert raw_doc is not None
            context.full_text = raw_doc.full_text
            context.stats["total_characters"] = len(context.full_text)

            # 1.2 Fingerprint
            fingerprint = generate_fingerprint(context.full_text)
            context.fingerprint = fingerprint.full_hash

            # 1.3 Proyecto
            name = project_name or path.stem
            project_mgr = ProjectManager()

            existing = project_mgr.get_by_fingerprint(fingerprint.full_hash)
            if existing and existing.id is not None:
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
                    return Result.failure(create_result.error)  # type: ignore[arg-type]
                assert create_result.value is not None
                context.project_id = create_result.value.id  # type: ignore[assignment]

            # 1.4 Sesión
            session_mgr = SessionManager(project_id=context.project_id)
            session = session_mgr.start()
            context.session_id = session.id  # type: ignore[assignment]

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
            result = detector.detect(context.raw_document)  # type: ignore[arg-type]

            if result.is_success and result.value is not None and hasattr(result.value, "chapters"):
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

            if result.is_success and result.value is not None and result.value.dialogues:
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

                # Asignar capítulo a cada diálogo basándose en posición
                if context.chapters:
                    for d in context.dialogues:
                        d_start = d.get("start_char", 0)
                        for ch in context.chapters:
                            ch_start = ch.get("start_char", 0) if isinstance(ch, dict) else getattr(ch, "start_char", 0)
                            ch_end = ch.get("end_char", 0) if isinstance(ch, dict) else getattr(ch, "end_char", 0)
                            ch_num = ch.get("number", 0) if isinstance(ch, dict) else getattr(ch, "number", 0)
                            if ch_start <= d_start <= ch_end:
                                d["chapter"] = ch_num
                                break

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

    # Phase 2: NER extraction and temporal markers -> moved to ua_ner.py

    # =========================================================================
    # FASE 3: RESOLUCIÓN Y FUSIÓN
    # =========================================================================

    # Phase 3: Coreference, entity fusion, dialogue attribution -> moved to ua_resolution.py

    # =========================================================================
    # FASE 4: EXTRACCIÓN PROFUNDA
    # =========================================================================

    # Phase 4: Attributes, relationships, interactions, knowledge, voice profiles -> moved to ua_deep_extraction.py

    # =========================================================================
    # FASE 5: ANÁLISIS DE CALIDAD
    # =========================================================================

    # Phase 5: Spelling, grammar, repetitions, coherence, register, pacing -> moved to ua_quality.py

    # =========================================================================
    # FASE 6: CONSISTENCIA Y ALERTAS
    # =========================================================================

    # Phase 6: Consistency checks (attributes, temporal, focalization, voice, emotional, sentiment) -> moved to ua_consistency.py

    # =========================================================================
    # GENERACIÓN DE ALERTAS
    # =========================================================================

    # Alert generation from detected issues -> moved to ua_alerts.py

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
