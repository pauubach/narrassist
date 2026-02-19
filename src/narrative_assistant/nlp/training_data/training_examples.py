"""
Generador de ejemplos de entrenamiento sintéticos para votación ponderada.

Crea un dataset variado que simula diferentes escenarios donde cada método
de extracción tiene diferentes niveles de éxito.

Escenarios incluidos:
1. Casos claros donde todos los métodos coinciden
2. Casos donde solo el LLM detecta atributos implícitos
3. Casos donde los patrones son más precisos
4. Casos con errores ortográficos (LLM mejor)
5. Casos con metáforas (patterns mejor filtran)
6. Casos de primera persona / narrador
7. Casos con correferencias
"""

import json
import logging
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """
    Ejemplo de entrenamiento para optimización de pesos.

    Attributes:
        entity_name: Nombre de la entidad
        attribute_key: Tipo de atributo (eye_color, hair_color, etc.)
        attribute_value: Valor correcto del atributo
        text_context: Texto de donde se extrajo

        scores: Confianza de cada método {método: score}
        is_correct: Si el atributo extraído es correcto (ground truth)

        scenario: Escenario de prueba para análisis
        notes: Notas adicionales
    """

    entity_name: str
    attribute_key: str
    attribute_value: str
    text_context: str

    # Scores de cada método (0.0-1.0)
    scores: dict = field(default_factory=dict)

    # Ground truth
    is_correct: bool = True

    # Metadata
    scenario: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TrainingExample":
        return cls(**data)


# =============================================================================
# Escenarios de entrenamiento
# =============================================================================

SCENARIOS = {
    # Escenario 1: Todos los métodos coinciden (caso ideal)
    "all_agree": {
        "description": "Todos los métodos detectan correctamente el atributo",
        "examples": [
            {
                "text": "Juan tenía los ojos azules y el pelo negro.",
                "entity": "Juan",
                "key": "eye_color",
                "value": "azules",
                "scores": {"llm": 0.95, "embeddings": 0.85, "dependency": 0.80, "patterns": 0.90},
                "is_correct": True,
            },
            {
                "text": "María, de cabello rubio y ojos verdes, entró en la sala.",
                "entity": "María",
                "key": "hair_color",
                "value": "rubio",
                "scores": {"llm": 0.92, "embeddings": 0.88, "dependency": 0.75, "patterns": 0.95},
                "is_correct": True,
            },
            {
                "text": "El doctor García era alto y corpulento.",
                "entity": "García",
                "key": "height",
                "value": "alto",
                "scores": {"llm": 0.90, "embeddings": 0.82, "dependency": 0.85, "patterns": 0.88},
                "is_correct": True,
            },
            {
                "text": "Laura, la abogada, tenía treinta años.",
                "entity": "Laura",
                "key": "profession",
                "value": "abogada",
                "scores": {"llm": 0.93, "embeddings": 0.78, "dependency": 0.72, "patterns": 0.85},
                "is_correct": True,
            },
        ],
    },
    # Escenario 2: Solo LLM detecta (atributos implícitos)
    "llm_implicit": {
        "description": "Solo el LLM detecta atributos implícitos/contextuales",
        "examples": [
            {
                "text": "Mis estudios como lingüista me llevaron por muchos caminos.",
                "entity": "Narrador",
                "key": "profession",
                "value": "lingüista",
                "scores": {"llm": 0.88, "embeddings": 0.45, "dependency": 0.30, "patterns": 0.20},
                "is_correct": True,
            },
            {
                "text": "Desde niña rubia, siempre soñé con viajar.",
                "entity": "Narrador",
                "key": "hair_color",
                "value": "rubio",
                "scores": {"llm": 0.85, "embeddings": 0.40, "dependency": 0.25, "patterns": 0.15},
                "is_correct": True,
            },
            {
                "text": "He sido siempre una persona curiosa y observadora.",
                "entity": "Narrador",
                "key": "personality",
                "value": "curiosa",
                "scores": {"llm": 0.82, "embeddings": 0.55, "dependency": 0.35, "patterns": 0.10},
                "is_correct": True,
            },
            {
                "text": "En la academia militar aprendí disciplina.",
                "entity": "Narrador",
                "key": "profession",
                "value": "militar",
                "scores": {"llm": 0.78, "embeddings": 0.42, "dependency": 0.20, "patterns": 0.05},
                "is_correct": True,
            },
            {
                "text": "Mi hermana mayor siempre me protegía.",
                "entity": "Narrador",
                "key": "relationship",
                "value": "tiene hermana mayor",
                "scores": {"llm": 0.80, "embeddings": 0.35, "dependency": 0.40, "patterns": 0.00},
                "is_correct": True,
            },
        ],
    },
    # Escenario 3: Patterns mejor (formato explícito)
    "patterns_explicit": {
        "description": "Patrones regex funcionan mejor por formato explícito",
        "examples": [
            {
                "text": "Pedro, de 45 años, caminaba despacio.",
                "entity": "Pedro",
                "key": "age",
                "value": "45",
                "scores": {"llm": 0.75, "embeddings": 0.50, "dependency": 0.60, "patterns": 0.95},
                "is_correct": True,
            },
            {
                "text": "La espada de acero brillaba en sus manos.",
                "entity": "espada",
                "key": "material",
                "value": "acero",
                "scores": {"llm": 0.70, "embeddings": 0.55, "dependency": 0.45, "patterns": 0.92},
                "is_correct": True,
            },
            {
                "text": "Elena, la médica del pueblo, era conocida por todos.",
                "entity": "Elena",
                "key": "profession",
                "value": "médica",
                "scores": {"llm": 0.85, "embeddings": 0.60, "dependency": 0.55, "patterns": 0.93},
                "is_correct": True,
            },
        ],
    },
    # Escenario 4: Errores ortográficos (LLM robusto)
    "typos": {
        "description": "Texto con errores ortográficos - LLM más robusto",
        "examples": [
            {
                "text": "Juan tenia los ojos asules y el pelo negro.",  # azules mal escrito
                "entity": "Juan",
                "key": "eye_color",
                "value": "azules",
                "scores": {"llm": 0.85, "embeddings": 0.60, "dependency": 0.50, "patterns": 0.30},
                "is_correct": True,
            },
            {
                "text": "Maria era una mujer alta y ruvia.",  # rubia mal escrito
                "entity": "Maria",
                "key": "hair_color",
                "value": "rubio",
                "scores": {"llm": 0.80, "embeddings": 0.55, "dependency": 0.40, "patterns": 0.25},
                "is_correct": True,
            },
            {
                "text": "El medico examino al pasiente con cuidado.",  # médico, paciente
                "entity": "medico",
                "key": "profession",
                "value": "médico",
                "scores": {"llm": 0.88, "embeddings": 0.65, "dependency": 0.55, "patterns": 0.60},
                "is_correct": True,
            },
        ],
    },
    # Escenario 5: Metáforas (patterns filtra mejor)
    "metaphors": {
        "description": "Texto con metáforas - patterns las filtra correctamente",
        "examples": [
            {
                "text": "Sus ojos eran dos luceros en la noche.",
                "entity": "Persona",
                "key": "eye_color",
                "value": "luceros",  # Incorrecto - es metáfora
                "scores": {"llm": 0.40, "embeddings": 0.55, "dependency": 0.60, "patterns": 0.15},
                "is_correct": False,  # NO debería extraerse
            },
            {
                "text": "Era alto como un roble centenario.",
                "entity": "Persona",
                "key": "height",
                "value": "roble",  # Incorrecto - es comparación
                "scores": {"llm": 0.35, "embeddings": 0.50, "dependency": 0.45, "patterns": 0.10},
                "is_correct": False,
            },
            {
                "text": "Tenía el pelo de fuego, salvaje e indomable.",
                "entity": "Persona",
                "key": "hair_color",
                "value": "fuego",  # Incorrecto - metáfora
                "scores": {"llm": 0.30, "embeddings": 0.45, "dependency": 0.40, "patterns": 0.08},
                "is_correct": False,
            },
            {
                "text": "Juan tenía el pelo de fuego. También tenía ojos verdes.",
                "entity": "Juan",
                "key": "eye_color",
                "value": "verdes",  # Correcto - este sí
                "scores": {"llm": 0.90, "embeddings": 0.75, "dependency": 0.70, "patterns": 0.85},
                "is_correct": True,
            },
        ],
    },
    # Escenario 6: Correferencias (necesita contexto)
    "coreference": {
        "description": "Atributos con pronombres que requieren resolución",
        "examples": [
            {
                "text": "Juan saludó a María. Ella tenía el pelo largo y rubio.",
                "entity": "María",
                "key": "hair_color",
                "value": "rubio",
                "scores": {"llm": 0.88, "embeddings": 0.70, "dependency": 0.55, "patterns": 0.45},
                "is_correct": True,
            },
            {
                "text": "El detective interrogó al sospechoso. Sus ojos grises no mostraban emoción.",
                "entity": "sospechoso",
                "key": "eye_color",
                "value": "grises",
                "scores": {"llm": 0.82, "embeddings": 0.65, "dependency": 0.50, "patterns": 0.40},
                "is_correct": True,
            },
            {
                "text": "Ana miraba a Pedro. Él era alto y de complexión atlética.",
                "entity": "Pedro",
                "key": "build",
                "value": "atlética",
                "scores": {"llm": 0.85, "embeddings": 0.72, "dependency": 0.60, "patterns": 0.55},
                "is_correct": True,
            },
        ],
    },
    # Escenario 7: Atributos negados
    "negated": {
        "description": "Atributos que están negados en el texto",
        "examples": [
            {
                "text": "Juan no era alto, más bien de estatura media.",
                "entity": "Juan",
                "key": "height",
                "value": "alto",
                "scores": {"llm": 0.20, "embeddings": 0.55, "dependency": 0.50, "patterns": 0.60},
                "is_correct": False,  # Está negado
            },
            {
                "text": "María nunca fue rubia, siempre tuvo el pelo oscuro.",
                "entity": "María",
                "key": "hair_color",
                "value": "rubia",
                "scores": {"llm": 0.15, "embeddings": 0.45, "dependency": 0.40, "patterns": 0.50},
                "is_correct": False,
            },
            {
                "text": "No tenía ojos azules como pensaba, sino verdes.",
                "entity": "Persona",
                "key": "eye_color",
                "value": "verdes",  # Este sí es correcto
                "scores": {"llm": 0.85, "embeddings": 0.70, "dependency": 0.55, "patterns": 0.65},
                "is_correct": True,
            },
        ],
    },
    # Escenario 8: Diálogos (contexto diferente)
    "dialogue": {
        "description": "Atributos mencionados en diálogos",
        "examples": [
            {
                "text": "—Eres demasiado joven para entender —dijo el anciano.",
                "entity": "interlocutor",
                "key": "age",
                "value": "joven",
                "scores": {"llm": 0.75, "embeddings": 0.60, "dependency": 0.45, "patterns": 0.40},
                "is_correct": True,
            },
            {
                "text": "«Tu pelo rubio me recuerda al sol», le susurró.",
                "entity": "interlocutor",
                "key": "hair_color",
                "value": "rubio",
                "scores": {"llm": 0.80, "embeddings": 0.65, "dependency": 0.50, "patterns": 0.55},
                "is_correct": True,
            },
        ],
    },
    # Escenario 9: Embeddings destacan (similitud semántica)
    "semantic_similarity": {
        "description": "Casos donde embeddings capturan mejor la semántica",
        "examples": [
            {
                "text": "Su cabellera dorada brillaba al sol.",
                "entity": "Persona",
                "key": "hair_color",
                "value": "rubio",  # dorada = rubio
                "scores": {"llm": 0.85, "embeddings": 0.90, "dependency": 0.40, "patterns": 0.30},
                "is_correct": True,
            },
            {
                "text": "Era de complexión robusta, como un toro.",
                "entity": "Persona",
                "key": "build",
                "value": "corpulento",
                "scores": {"llm": 0.80, "embeddings": 0.85, "dependency": 0.55, "patterns": 0.45},
                "is_correct": True,
            },
        ],
    },
    # Escenario 10: Dependency parsing destaca (estructura sintáctica)
    "syntactic": {
        "description": "Estructura sintáctica clara - dependency parsing mejor",
        "examples": [
            {
                "text": "El joven era valiente.",
                "entity": "joven",
                "key": "personality",
                "value": "valiente",
                "scores": {"llm": 0.80, "embeddings": 0.70, "dependency": 0.90, "patterns": 0.65},
                "is_correct": True,
            },
            {
                "text": "La mujer alta entró en la habitación.",
                "entity": "mujer",
                "key": "height",
                "value": "alta",
                "scores": {"llm": 0.75, "embeddings": 0.65, "dependency": 0.88, "patterns": 0.70},
                "is_correct": True,
            },
        ],
    },
    # Escenario 11: Falsos positivos (todos fallan)
    "false_positives": {
        "description": "Casos donde no hay atributo real pero se detecta incorrectamente",
        "examples": [
            {
                "text": "Juan pintó la pared de azul.",
                "entity": "Juan",
                "key": "eye_color",
                "value": "azul",  # Incorrecto - es la pared
                "scores": {"llm": 0.25, "embeddings": 0.40, "dependency": 0.35, "patterns": 0.30},
                "is_correct": False,
            },
            {
                "text": "El libro verde estaba sobre la mesa de María.",
                "entity": "María",
                "key": "eye_color",
                "value": "verde",  # Incorrecto - es el libro
                "scores": {"llm": 0.20, "embeddings": 0.35, "dependency": 0.30, "patterns": 0.25},
                "is_correct": False,
            },
        ],
    },
    # Escenario 12: Múltiples entidades (desambiguación)
    "disambiguation": {
        "description": "Múltiples entidades - necesita desambiguar",
        "examples": [
            {
                "text": "Juan y María caminaban juntos. Él era alto y ella baja.",
                "entity": "Juan",
                "key": "height",
                "value": "alto",
                "scores": {"llm": 0.90, "embeddings": 0.75, "dependency": 0.70, "patterns": 0.60},
                "is_correct": True,
            },
            {
                "text": "Juan y María caminaban juntos. Él era alto y ella baja.",
                "entity": "María",
                "key": "height",
                "value": "baja",
                "scores": {"llm": 0.88, "embeddings": 0.72, "dependency": 0.68, "patterns": 0.55},
                "is_correct": True,
            },
            {
                "text": "Los hermanos Pedro y Ana heredaron los ojos verdes de su madre.",
                "entity": "Pedro",
                "key": "eye_color",
                "value": "verdes",
                "scores": {"llm": 0.85, "embeddings": 0.70, "dependency": 0.65, "patterns": 0.50},
                "is_correct": True,
            },
        ],
    },
}


def generate_synthetic_dataset(
    num_examples_per_scenario: int = 5,
    add_noise: bool = True,
    noise_level: float = 0.1,
) -> list[TrainingExample]:
    """
    Genera un dataset sintético de entrenamiento.

    Args:
        num_examples_per_scenario: Ejemplos por escenario base
        add_noise: Si añadir variación aleatoria a los scores
        noise_level: Nivel de ruido (0.0-0.3)

    Returns:
        Lista de TrainingExample
    """
    examples = []

    for scenario_name, scenario_data in SCENARIOS.items():
        base_examples = scenario_data.get("examples", [])

        for base in base_examples:
            # Crear ejemplo base
            scores = dict(base.get("scores", {}))

            # Añadir ruido si está habilitado
            if add_noise:
                for method in scores:
                    noise = random.uniform(-noise_level, noise_level)
                    scores[method] = max(0.0, min(1.0, scores[method] + noise))

            example = TrainingExample(
                entity_name=base.get("entity", ""),
                attribute_key=base.get("key", ""),
                attribute_value=base.get("value", ""),
                text_context=base.get("text", ""),
                scores=scores,
                is_correct=base.get("is_correct", False),
                scenario=scenario_name,
                notes=scenario_data.get("description", ""),
            )
            examples.append(example)

        # Generar variaciones adicionales
        if num_examples_per_scenario > len(base_examples):
            for _ in range(num_examples_per_scenario - len(base_examples)):
                # Elegir un ejemplo base aleatorio y variar scores
                base = random.choice(base_examples)
                scores = {}
                for method, score in base.get("scores", {}).items():
                    variation = random.uniform(-0.15, 0.15)
                    scores[method] = max(0.0, min(1.0, score + variation))

                example = TrainingExample(
                    entity_name=base.get("entity", ""),
                    attribute_key=base.get("key", ""),
                    attribute_value=base.get("value", ""),
                    text_context=base.get("text", ""),
                    scores=scores,
                    is_correct=base.get("is_correct", False),
                    scenario=scenario_name,
                    notes=f"Variación de: {scenario_data.get('description', '')}",
                )
                examples.append(example)

    logger.info(f"Generados {len(examples)} ejemplos sintéticos de entrenamiento")
    return examples


def save_training_data(
    examples: list[TrainingExample],
    path: Path,
) -> None:
    """
    Guarda ejemplos de entrenamiento a archivo JSON Lines.

    Args:
        examples: Lista de ejemplos
        path: Ruta del archivo
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")

    logger.info(f"Guardados {len(examples)} ejemplos en {path}")


def load_training_data(path: Path) -> list[TrainingExample]:
    """
    Carga ejemplos de entrenamiento desde archivo JSON Lines.

    Args:
        path: Ruta del archivo

    Returns:
        Lista de TrainingExample
    """
    examples = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                examples.append(TrainingExample.from_dict(data))

    logger.info(f"Cargados {len(examples)} ejemplos desde {path}")
    return examples


# =============================================================================
# Análisis del dataset
# =============================================================================


def analyze_dataset(examples: list[TrainingExample]) -> dict:
    """
    Analiza un dataset de entrenamiento.

    Returns:
        Estadísticas del dataset
    """
    stats = {
        "total_examples": len(examples),
        "correct_examples": sum(1 for e in examples if e.is_correct),
        "incorrect_examples": sum(1 for e in examples if not e.is_correct),
        "by_scenario": {},
        "by_attribute": {},
        "method_avg_scores": {
            "llm": [],
            "embeddings": [],
            "dependency": [],
            "patterns": [],
        },
    }

    for example in examples:
        # Por escenario
        scenario = getattr(example, "scenario", None)
        if scenario not in stats["by_scenario"]:
            stats["by_scenario"][scenario] = {"total": 0, "correct": 0}
        stats["by_scenario"][scenario]["total"] += 1
        if getattr(example, "is_correct", False):
            stats["by_scenario"][scenario]["correct"] += 1

        # Por atributo
        attribute_key = getattr(example, "attribute_key", None)
        if attribute_key not in stats["by_attribute"]:
            stats["by_attribute"][attribute_key] = {"total": 0, "correct": 0}
        stats["by_attribute"][attribute_key]["total"] += 1
        if getattr(example, "is_correct", False):
            stats["by_attribute"][attribute_key]["correct"] += 1

        # Scores promedio
        for method, score in getattr(example, "scores", {}).items():
            if method in stats["method_avg_scores"]:
                stats["method_avg_scores"][method].append(score)

    # Calcular promedios
    for method in stats["method_avg_scores"]:
        scores = stats["method_avg_scores"][method]
        if scores:
            stats["method_avg_scores"][method] = sum(scores) / len(scores)
        else:
            stats["method_avg_scores"][method] = 0.0

    return stats
