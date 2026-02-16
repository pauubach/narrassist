"""
Configuración centralizada del sistema de votación LLM por roles.

Define:
- ModelRole: perspectivas de análisis (SPANISH, REASONING, NARRATIVE)
- QualityLevel: niveles de calidad visibles al usuario (Rápida/Completa/Experta)
- QUALITY_MATRIX: configuración de votación por tarea y nivel
- ROLE_SUBSTITUTES: cadenas de fallback por rol
- resolve_fallbacks(): sustitución inteligente cuando un modelo no está disponible
- detect_capacity() / recommend_level(): recomendación basada en hardware
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ModelRole(Enum):
    """Perspectiva de análisis que aporta cada modelo."""

    SPANISH = "spanish"  # Comprensión profunda del español
    REASONING = "reasoning"  # Lógica temporal, causal, deductiva
    NARRATIVE = "narrative"  # Personajes, voz, estilo literario


class QualityLevel(Enum):
    """Niveles de calidad visibles al usuario (sin nombres de modelos)."""

    RAPIDA = "rapida"  # 1 modelo por tarea (el de mayor peso)
    COMPLETA = "completa"  # 2 modelos votando
    EXPERTA = "experta"  # 3 modelos votando


class AnalysisTask(Enum):
    """Tareas de análisis que usan votación LLM."""

    COREFERENCE = "coreference"
    EXPECTATIONS = "expectations"
    OOC = "ooc"  # Out-of-character
    TEMPORAL = "temporal"
    PROFILING = "profiling"
    CLASSICAL_SPANISH = "classical_spanish"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class VotingSlot:
    """Un slot de votación: un rol asignado a un modelo con un peso."""

    role: ModelRole
    model_name: str
    weight: float


@dataclass
class TaskVotingConfig:
    """Configuración de votación para una tarea concreta."""

    task: AnalysisTask
    slots: list[VotingSlot]  # Ordenados por peso descendente
    min_confidence: float  # Umbral mínimo para aceptar resultado

    @property
    def model_names(self) -> list[str]:
        return [s.model_name for s in self.slots]

    def slot_for_level(self, level: QualityLevel) -> list[VotingSlot]:
        """Retorna los slots activos según el nivel de calidad."""
        n = {QualityLevel.RAPIDA: 1, QualityLevel.COMPLETA: 2, QualityLevel.EXPERTA: 3}
        return self.slots[: n.get(level, 1)]


@dataclass
class HardwareProfile:
    """Perfil de capacidad de hardware para modelos LLM."""

    vram_gb: float | None  # NVIDIA CUDA
    unified_memory_gb: float | None  # Apple Metal (compartida)
    ram_gb: float  # RAM del sistema
    device_type: str  # "cuda", "mps", "cpu"
    effective_budget_gb: float  # Presupuesto real para modelos LLM

    @property
    def has_gpu(self) -> bool:
        return self.device_type in ("cuda", "mps")


@dataclass
class VotingResult:
    """Resultado de una votación multi-modelo."""

    consensus: Any | None  # Resultado consolidado
    confidence: float  # Confianza ponderada
    models_used: list[str]  # Modelos que participaron
    roles_used: list[ModelRole]  # Roles representados
    per_model_results: dict[str, Any] = field(default_factory=dict)
    per_model_times: dict[str, float] = field(default_factory=dict)
    fallbacks_applied: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.consensus is not None and len(self.models_used) > 0


# =============================================================================
# Modelos core y sus roles
# =============================================================================

# Modelos principales (core) — se descargan con Completa/Experta
CORE_MODELS: dict[str, list[ModelRole]] = {
    "qwen3": [ModelRole.SPANISH, ModelRole.REASONING],
    "hermes3": [ModelRole.NARRATIVE],
    "deepseek-r1": [ModelRole.REASONING],
}

# Modelos fallback — se usan cuando un core no está disponible
FALLBACK_MODELS: dict[str, list[ModelRole]] = {
    "qwen2.5": [ModelRole.SPANISH],
    "gemma2": [ModelRole.NARRATIVE],
    "mistral": [ModelRole.REASONING],  # Legacy
    "llama3.2": [ModelRole.SPANISH, ModelRole.REASONING, ModelRole.NARRATIVE],
}

# Cadenas de sustitución por rol (ordenadas por preferencia)
ROLE_SUBSTITUTES: dict[ModelRole, list[str]] = {
    ModelRole.SPANISH: ["qwen3", "qwen2.5", "gemma2", "llama3.2"],
    ModelRole.REASONING: ["deepseek-r1", "qwen3", "mistral", "llama3.2"],
    ModelRole.NARRATIVE: ["hermes3", "gemma2", "qwen2.5", "llama3.2"],
}


# =============================================================================
# Matriz de votación por tarea (configuración ideal con 3 core models)
# =============================================================================

QUALITY_MATRIX: dict[AnalysisTask, TaskVotingConfig] = {
    AnalysisTask.COREFERENCE: TaskVotingConfig(
        task=AnalysisTask.COREFERENCE,
        slots=[
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.40),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.35),
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.25),
        ],
        min_confidence=0.70,
    ),
    AnalysisTask.EXPECTATIONS: TaskVotingConfig(
        task=AnalysisTask.EXPECTATIONS,
        slots=[
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.40),
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.35),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.25),
        ],
        min_confidence=0.60,
    ),
    AnalysisTask.OOC: TaskVotingConfig(
        task=AnalysisTask.OOC,
        slots=[
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.45),
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.30),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.25),
        ],
        min_confidence=0.80,
    ),
    AnalysisTask.TEMPORAL: TaskVotingConfig(
        task=AnalysisTask.TEMPORAL,
        slots=[
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.45),
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.30),
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.25),
        ],
        min_confidence=0.75,
    ),
    AnalysisTask.PROFILING: TaskVotingConfig(
        task=AnalysisTask.PROFILING,
        slots=[
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.40),
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.35),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.25),
        ],
        min_confidence=0.65,
    ),
    AnalysisTask.CLASSICAL_SPANISH: TaskVotingConfig(
        task=AnalysisTask.CLASSICAL_SPANISH,
        slots=[
            VotingSlot(ModelRole.SPANISH, "qwen3", 0.50),
            VotingSlot(ModelRole.REASONING, "deepseek-r1", 0.30),
            VotingSlot(ModelRole.NARRATIVE, "hermes3", 0.20),
        ],
        min_confidence=0.85,
    ),
}

# Umbrales de sensibilidad: el slider (1-10) escala los min_confidence
# sensitivity=1 → min_confidence * 1.3 (más estricto, menos alertas)
# sensitivity=5 → min_confidence * 1.0 (default)
# sensitivity=10 → min_confidence * 0.7 (más permisivo, más alertas)
SENSITIVITY_RANGE = (0.7, 1.3)  # Factor mínimo y máximo


# =============================================================================
# Requisitos de hardware por nivel
# =============================================================================

# Tamaño aproximado en GB de cada modelo cargado en VRAM/RAM
MODEL_MEMORY_GB: dict[str, float] = {
    "qwen3": 8.5,
    "hermes3": 4.7,
    "deepseek-r1": 4.4,
    "qwen2.5": 4.4,
    "gemma2": 5.5,
    "mistral": 4.1,
    "llama3.2": 2.0,
}

# Modelos necesarios por nivel (se cargan de uno en uno, no simultáneamente)
LEVEL_MODELS: dict[QualityLevel, list[str]] = {
    QualityLevel.RAPIDA: ["qwen3"],  # Solo el de mayor peso por tarea
    QualityLevel.COMPLETA: ["qwen3", "hermes3"],  # 2 core
    QualityLevel.EXPERTA: ["qwen3", "hermes3", "deepseek-r1"],  # 3 core
}

# Presupuesto mínimo efectivo (el modelo más grande que necesitan)
LEVEL_MIN_BUDGET_GB: dict[QualityLevel, float] = {
    QualityLevel.RAPIDA: 6.0,  # qwen2.5 o llama3.2 como fallback
    QualityLevel.COMPLETA: 12.0,
    QualityLevel.EXPERTA: 20.0,
}

# Fallback de modelos por nivel cuando el budget es menor que el core
LEVEL_FALLBACK_MODELS: dict[QualityLevel, list[str]] = {
    QualityLevel.RAPIDA: ["qwen2.5", "llama3.2"],  # Si qwen3 no cabe
    QualityLevel.COMPLETA: ["qwen2.5", "llama3.2"],
    QualityLevel.EXPERTA: ["qwen2.5", "llama3.2"],
}


# =============================================================================
# Funciones
# =============================================================================


def resolve_fallbacks(
    task_config: TaskVotingConfig,
    available_models: set[str],
    level: QualityLevel = QualityLevel.EXPERTA,
) -> TaskVotingConfig:
    """
    Resuelve sustituciones cuando un modelo no está disponible.

    Reglas:
    1. Para cada slot, verificar si su modelo está en available_models
    2. Si NO: buscar en ROLE_SUBSTITUTES[slot.role] el primer modelo
       disponible que NO esté ya asignado a otro slot
    3. Si no hay sustituto: eliminar el slot
    4. Limitar slots al número que corresponde al nivel de calidad

    Args:
        task_config: Configuración ideal de la tarea
        available_models: Modelos realmente instalados/descargados
        level: Nivel de calidad seleccionado

    Returns:
        TaskVotingConfig con modelos sustituidos según disponibilidad
    """
    # Normalizar nombres (quitar tags :latest, etc.)
    normalized_available = {m.split(":")[0].strip().lower() for m in available_models}

    # Determinar cuántos slots activos según nivel
    active_slots = task_config.slot_for_level(level)

    resolved_slots: list[VotingSlot] = []
    used_models: set[str] = set()

    for slot in active_slots:
        model = slot.model_name

        if model in normalized_available and model not in used_models:
            # Modelo original disponible
            resolved_slots.append(slot)
            used_models.add(model)
        else:
            # Buscar sustituto para el mismo rol
            substitute = _find_substitute(slot.role, normalized_available, used_models)
            if substitute:
                logger.info(
                    f"Fallback: {model} → {substitute} "
                    f"(rol {slot.role.value}, tarea {task_config.task.value})"
                )
                resolved_slots.append(
                    VotingSlot(role=slot.role, model_name=substitute, weight=slot.weight)
                )
                used_models.add(substitute)
            else:
                logger.warning(
                    f"Sin sustituto para rol {slot.role.value} "
                    f"(tarea {task_config.task.value}, modelo original: {model})"
                )

    if not resolved_slots:
        logger.error(
            f"Votación imposible para tarea {task_config.task.value}: "
            f"ningún modelo disponible. Disponibles: {normalized_available}"
        )

    # Renormalizar pesos para que sumen 1.0
    total_weight = sum(s.weight for s in resolved_slots)
    if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
        resolved_slots = [
            VotingSlot(s.role, s.model_name, s.weight / total_weight)
            for s in resolved_slots
        ]

    return TaskVotingConfig(
        task=task_config.task,
        slots=resolved_slots,
        min_confidence=task_config.min_confidence,
    )


def _find_substitute(
    role: ModelRole,
    available: set[str],
    already_used: set[str],
) -> str | None:
    """Encuentra el mejor sustituto disponible para un rol."""
    for candidate in ROLE_SUBSTITUTES.get(role, []):
        if candidate in available and candidate not in already_used:
            return candidate
    return None


def get_voting_config(
    task: AnalysisTask,
    available_models: set[str],
    level: QualityLevel = QualityLevel.EXPERTA,
    sensitivity: float = 5.0,
) -> TaskVotingConfig:
    """
    Obtiene la configuración de votación resuelta para una tarea.

    Args:
        task: Tarea de análisis
        available_models: Modelos instalados
        level: Nivel de calidad
        sensitivity: Valor del slider (1-10), default 5

    Returns:
        TaskVotingConfig con fallbacks resueltos y confianza ajustada
    """
    base_config = QUALITY_MATRIX[task]
    resolved = resolve_fallbacks(base_config, available_models, level)

    # Ajustar min_confidence según sensibilidad
    if sensitivity != 5.0:
        factor = _sensitivity_to_factor(sensitivity)
        resolved = TaskVotingConfig(
            task=resolved.task,
            slots=resolved.slots,
            min_confidence=max(0.1, min(0.99, resolved.min_confidence * factor)),
        )

    return resolved


def _sensitivity_to_factor(sensitivity: float) -> float:
    """Convierte valor de slider (1-10) a factor multiplicador de confianza."""
    # sensitivity=1 → factor=1.3 (más estricto)
    # sensitivity=5 → factor=1.0 (neutro)
    # sensitivity=10 → factor=0.7 (más permisivo)
    clamped = max(1.0, min(10.0, sensitivity))
    min_factor, max_factor = SENSITIVITY_RANGE
    return max_factor - (clamped - 1.0) * (max_factor - min_factor) / 9.0


def get_required_models(level: QualityLevel) -> set[str]:
    """Retorna el conjunto de modelos necesarios para un nivel."""
    return set(LEVEL_MODELS.get(level, []))


def recommend_level(profile: HardwareProfile) -> QualityLevel:
    """Recomienda el nivel de calidad máximo para el hardware dado."""
    budget = profile.effective_budget_gb

    if budget >= LEVEL_MIN_BUDGET_GB[QualityLevel.EXPERTA]:
        return QualityLevel.EXPERTA
    if budget >= LEVEL_MIN_BUDGET_GB[QualityLevel.COMPLETA]:
        return QualityLevel.COMPLETA
    return QualityLevel.RAPIDA


def get_available_levels(profile: HardwareProfile) -> list[dict[str, Any]]:
    """
    Retorna los niveles con su estado de disponibilidad.

    Returns:
        Lista de dicts con: level, label, description, available, reason
    """
    budget = profile.effective_budget_gb
    recommended = recommend_level(profile)

    levels = [
        {
            "level": QualityLevel.RAPIDA,
            "label": "Rápida",
            "description": "Análisis rápido con un motor",
            "available": True,  # Siempre disponible (llama3.2 3B cabe en cualquier sitio)
            "reason": None,
            "recommended": recommended == QualityLevel.RAPIDA,
        },
        {
            "level": QualityLevel.COMPLETA,
            "label": "Completa",
            "description": "Análisis con verificación cruzada (2 motores)",
            "available": budget >= LEVEL_MIN_BUDGET_GB[QualityLevel.COMPLETA],
            "reason": (
                f"Requiere {LEVEL_MIN_BUDGET_GB[QualityLevel.COMPLETA]:.0f} GB "
                f"(disponible: {budget:.1f} GB)"
                if budget < LEVEL_MIN_BUDGET_GB[QualityLevel.COMPLETA]
                else None
            ),
            "recommended": recommended == QualityLevel.COMPLETA,
        },
        {
            "level": QualityLevel.EXPERTA,
            "label": "Experta",
            "description": "Máxima precisión con 3 motores votando",
            "available": budget >= LEVEL_MIN_BUDGET_GB[QualityLevel.EXPERTA],
            "reason": (
                f"Requiere {LEVEL_MIN_BUDGET_GB[QualityLevel.EXPERTA]:.0f} GB "
                f"(disponible: {budget:.1f} GB)"
                if budget < LEVEL_MIN_BUDGET_GB[QualityLevel.EXPERTA]
                else None
            ),
            "recommended": recommended == QualityLevel.EXPERTA,
        },
    ]

    return levels


def estimate_analysis_time(
    profile: HardwareProfile,
    level: QualityLevel,
    word_count: int,
    benchmarks: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Estima el tiempo de análisis basado en hardware, nivel y longitud.

    Args:
        profile: Perfil de hardware
        level: Nivel de calidad
        word_count: Número de palabras del manuscrito
        benchmarks: tok/s medidos por modelo (de model_benchmarks table)

    Returns:
        Dict con min_seconds, max_seconds, description
    """
    # Tokens estimados por palabra (prompt + respuesta)
    tokens_per_word = 2.5
    total_tokens = word_count * tokens_per_word

    # Número de tareas LLM × slots por nivel
    num_tasks = len(AnalysisTask)
    slots_per_level = {QualityLevel.RAPIDA: 1, QualityLevel.COMPLETA: 2, QualityLevel.EXPERTA: 3}
    total_calls = num_tasks * slots_per_level.get(level, 1)

    # tok/s estimado (usa benchmark real si disponible, sino estima por hardware)
    if benchmarks:
        avg_toks = sum(benchmarks.values()) / len(benchmarks)
    elif profile.device_type == "cuda":
        avg_toks = 40.0  # GPU NVIDIA típica
    elif profile.device_type == "mps":
        avg_toks = 25.0  # Apple Silicon típica
    else:
        avg_toks = 8.0  # CPU

    # Tokens por llamada LLM (prompt ~500 + respuesta ~200)
    tokens_per_call = 700
    llm_seconds = (total_calls * tokens_per_call) / avg_toks

    # Tiempo NLP (spaCy, embeddings) — proporcional a palabras
    nlp_seconds = word_count / 500  # ~500 palabras/segundo

    total_min = nlp_seconds + llm_seconds * 0.8
    total_max = nlp_seconds + llm_seconds * 1.5

    # Formatear
    if total_max < 60:
        description = f"~{int(total_max)} segundos"
    elif total_max < 3600:
        description = f"~{int(total_max / 60)} minutos"
    else:
        description = f"~{total_max / 3600:.1f} horas"

    return {
        "min_seconds": int(total_min),
        "max_seconds": int(total_max),
        "description": description,
        "llm_calls": total_calls,
        "avg_toks_per_sec": avg_toks,
    }
