"""
Motor de inferencia de expectativas comportamentales con votación multi-modelo.

Este módulo usa múltiples técnicas/modelos para:
1. Analizar patrones de comportamiento de personajes
2. Inferir expectativas basadas en su caracterización
3. Detectar violaciones de expectativas que podrían ser inconsistencias

Sistema de votación:
- Múltiples modelos LLM locales (Ollama)
- Análisis basado en reglas/heurísticas
- Análisis de embeddings (similitud semántica)
- Votación ponderada para consenso

Las expectativas pueden ser:
- Comportamentales: "Juan es pacifista, no atacaría sin provocación"
- Relacionales: "María odia a Pedro, no le ayudaría voluntariamente"
- De conocimiento: "Ana no sabe del secreto, no puede mencionarlo"
- De capacidad: "El niño tiene 5 años, no puede conducir un coche"
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ExpectationType(Enum):
    """Tipos de expectativas sobre personajes."""

    BEHAVIORAL = "behavioral"  # Basada en personalidad/valores
    RELATIONAL = "relational"  # Basada en relaciones
    KNOWLEDGE = "knowledge"  # Basada en lo que saben
    CAPABILITY = "capability"  # Basada en capacidades físicas/mentales
    TEMPORAL = "temporal"  # Basada en eventos previos
    CONTEXTUAL = "contextual"  # Basada en contexto de la escena


class ViolationSeverity(Enum):
    """Severidad de la violación de expectativa."""

    CRITICAL = "critical"  # Rompe completamente la caracterización
    HIGH = "high"  # Muy improbable dado el personaje
    MEDIUM = "medium"  # Inusual pero posible
    LOW = "low"  # Ligeramente fuera de carácter


class InferenceMethod(Enum):
    """Métodos de inferencia disponibles."""

    # Modelos LLM locales (vía Ollama)
    LLAMA3_2 = "llama3.2"  # Llama 3.2 3B - Rápido, buena calidad
    MISTRAL = "mistral"  # Mistral 7B - Mayor calidad, más lento
    GEMMA2 = "gemma2"  # Gemma 2 9B - Alta calidad
    QWEN2_5 = "qwen2.5"  # Qwen 2.5 7B - Muy bueno en español

    # Métodos basados en reglas/heurísticas
    RULE_BASED = "rule_based"  # Patrones y heurísticas
    EMBEDDINGS = "embeddings"  # Similitud semántica con embeddings


# Pesos por defecto para votación
DEFAULT_WEIGHTS = {
    InferenceMethod.LLAMA3_2: 0.25,
    InferenceMethod.MISTRAL: 0.30,
    InferenceMethod.GEMMA2: 0.25,
    InferenceMethod.QWEN2_5: 0.30,
    InferenceMethod.RULE_BASED: 0.15,
    InferenceMethod.EMBEDDINGS: 0.20,
}


@dataclass
class BehavioralExpectation:
    """
    Una expectativa sobre el comportamiento de un personaje.

    Representa lo que esperaríamos que un personaje haga o no haga
    basándonos en su caracterización establecida.
    """

    character_id: int
    character_name: str
    expectation_type: ExpectationType
    description: str
    reasoning: str  # Por qué se espera esto
    confidence: float  # 0.0 - 1.0
    source_chapters: list[int] = field(default_factory=list)
    related_traits: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    inference_method: Optional[str] = None  # Método que generó esta expectativa
    votes: dict[str, float] = field(default_factory=dict)  # Votos por método

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "expectation_type": self.expectation_type.value,
            "description": self.description,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "source_chapters": self.source_chapters,
            "related_traits": self.related_traits,
            "created_at": self.created_at.isoformat(),
            "inference_method": self.inference_method,
            "votes": self.votes,
        }


@dataclass
class ExpectationViolation:
    """
    Una posible violación de expectativa detectada.

    Indica que un personaje ha actuado de forma inconsistente
    con su caracterización establecida.
    """

    expectation: BehavioralExpectation
    violation_text: str  # Texto donde ocurre la violación
    chapter_number: int
    position: int  # Posición en el texto
    severity: ViolationSeverity
    explanation: str  # Por qué es una violación
    possible_justifications: list[str] = field(default_factory=list)
    is_false_positive: bool = False  # Marcado por el usuario
    detection_methods: list[str] = field(default_factory=list)  # Métodos que detectaron
    consensus_score: float = 0.0  # Grado de acuerdo entre métodos

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "expectation": self.expectation.to_dict(),
            "violation_text": self.violation_text,
            "chapter_number": self.chapter_number,
            "position": self.position,
            "severity": self.severity.value,
            "explanation": self.explanation,
            "possible_justifications": self.possible_justifications,
            "is_false_positive": self.is_false_positive,
            "detection_methods": self.detection_methods,
            "consensus_score": self.consensus_score,
        }


@dataclass
class CharacterBehaviorProfile:
    """
    Perfil comportamental completo de un personaje.

    Agrupa todas las expectativas y patrones detectados.
    """

    character_id: int
    character_name: str
    personality_traits: list[str]
    values: list[str]
    fears: list[str]
    goals: list[str]
    speech_patterns: list[str]
    expectations: list[BehavioralExpectation] = field(default_factory=list)
    analyzed_chapters: list[int] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    methods_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "personality_traits": self.personality_traits,
            "values": self.values,
            "fears": self.fears,
            "goals": self.goals,
            "speech_patterns": self.speech_patterns,
            "expectations": [e.to_dict() for e in self.expectations],
            "analyzed_chapters": self.analyzed_chapters,
            "last_updated": self.last_updated.isoformat(),
            "methods_used": self.methods_used,
        }


@dataclass
class InferenceConfig:
    """Configuración para el motor de inferencia."""

    # Métodos habilitados - Por defecto TODOS los métodos están disponibles
    # ya que todos los modelos vienen pre-instalados con la aplicación
    enabled_methods: list[InferenceMethod] = field(default_factory=lambda: [
        InferenceMethod.LLAMA3_2,
        InferenceMethod.MISTRAL,
        InferenceMethod.GEMMA2,
        InferenceMethod.QWEN2_5,
        InferenceMethod.RULE_BASED,
        InferenceMethod.EMBEDDINGS,
    ])

    # Pesos personalizados (opcional)
    custom_weights: Optional[dict[InferenceMethod, float]] = None

    # Umbral mínimo de confianza
    min_confidence: float = 0.5

    # Umbral de consenso para violaciones
    min_consensus: float = 0.6

    # Priorizar velocidad vs precisión
    prioritize_speed: bool = True

    @property
    def weights(self) -> dict[InferenceMethod, float]:
        """Obtiene los pesos activos."""
        if self.custom_weights:
            return self.custom_weights
        return {m: DEFAULT_WEIGHTS.get(m, 0.2) for m in self.enabled_methods}


class ExpectationInferenceEngine:
    """
    Motor de inferencia de expectativas usando votación multi-modelo.

    Analiza el texto narrativo combinando:
    1. Múltiples modelos LLM locales (vía Ollama)
    2. Análisis basado en reglas y heurísticas
    3. Similitud semántica con embeddings
    4. Votación ponderada para consenso

    Esto proporciona mayor precisión que usar un solo modelo.
    """

    # Prompt de sistema para análisis de personajes (para LLMs)
    CHARACTER_ANALYSIS_SYSTEM = """Eres un experto en análisis narrativo y caracterización de personajes.
Tu tarea es analizar textos literarios para extraer información sobre personajes.

Reglas:
1. Basa tus análisis SOLO en la evidencia textual proporcionada
2. Distingue entre lo que se muestra vs lo que se dice del personaje
3. Considera el contexto cultural y temporal de la narrativa
4. Sé conservador: mejor menos conclusiones pero más sólidas
5. Indica el nivel de confianza de cada inferencia

Responde SIEMPRE en formato JSON válido."""

    # Patrones para análisis basado en reglas
    TRAIT_PATTERNS = {
        "valiente": [r"se enfrentó", r"sin miedo", r"valentía", r"coraje", r"osadía"],
        "cobarde": [r"huyó", r"temblaba", r"miedo", r"cobardía", r"escapó aterrorizado"],
        "amable": [r"sonrió amablemente", r"ayudó a", r"bondad", r"gentil", r"compasivo"],
        "cruel": [r"golpeó", r"maltrataba", r"crueldad", r"despiadado", r"sin piedad"],
        "inteligente": [r"dedujo", r"comprendió rápidamente", r"astuto", r"perspicaz"],
        "impulsivo": [r"sin pensar", r"arrebato", r"impulsivamente", r"precipitado"],
        "pacífico": [r"evitó el conflicto", r"pacifista", r"no violencia", r"conciliador"],
        "violento": [r"atacó", r"agresivo", r"furioso golpe", r"violentamente"],
        "honesto": [r"dijo la verdad", r"sinceramente", r"honestidad", r"franco"],
        "mentiroso": [r"mintió", r"engañó", r"ocultó la verdad", r"falso"],
        "leal": [r"no abandonó", r"fiel a", r"lealtad", r"siempre a su lado"],
        "traidor": [r"traicionó", r"vendió a", r"traición", r"delató"],
    }

    VALUE_PATTERNS = {
        "familia": [r"por su familia", r"proteger a los suyos", r"amor familiar"],
        "honor": [r"su honor", r"dignidad", r"reputación", r"orgullo"],
        "dinero": [r"riqueza", r"fortuna", r"dinero", r"oro", r"codicia"],
        "poder": [r"dominar", r"control", r"poder", r"autoridad"],
        "libertad": [r"ser libre", r"libertad", r"independencia", r"autonomía"],
        "justicia": [r"justicia", r"lo correcto", r"equidad", r"imparcial"],
        "amor": [r"amor verdadero", r"por amor", r"enamorado"],
        "venganza": [r"venganza", r"vengar", r"ajustar cuentas", r"represalia"],
    }

    def __init__(self, config: Optional[InferenceConfig] = None):
        """
        Inicializa el motor.

        Args:
            config: Configuración de inferencia
        """
        self._config = config or InferenceConfig()
        self._profiles: dict[int, CharacterBehaviorProfile] = {}
        self._ollama_available: dict[str, bool] = {}
        self._embeddings_model = None
        self._check_available_methods()

    def _check_available_methods(self) -> None:
        """Verifica qué métodos están disponibles."""
        from .client import get_llm_client

        # Verificar modelos LLM
        client = get_llm_client()
        if client and client.is_available:
            # Verificar cada modelo en Ollama
            for method in [
                InferenceMethod.LLAMA3_2,
                InferenceMethod.MISTRAL,
                InferenceMethod.GEMMA2,
                InferenceMethod.QWEN2_5,
            ]:
                self._ollama_available[method.value] = self._check_ollama_model(method.value)

        # Verificar embeddings
        try:
            from narrative_assistant.nlp.embeddings import get_embeddings_model
            self._embeddings_model = get_embeddings_model()
        except Exception:
            pass

    def _check_ollama_model(self, model_name: str) -> bool:
        """Verifica si un modelo específico está disponible en Ollama."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = [m.get("name", "") for m in response.json().get("models", [])]
                return any(model_name in m for m in models)
        except Exception:
            pass
        return False

    @property
    def is_available(self) -> bool:
        """Verifica si al menos un método está disponible."""
        # Rule-based siempre está disponible
        if InferenceMethod.RULE_BASED in self._config.enabled_methods:
            return True

        # Verificar LLMs
        for method in self._config.enabled_methods:
            if method.value in self._ollama_available and self._ollama_available[method.value]:
                return True

        # Verificar embeddings
        if InferenceMethod.EMBEDDINGS in self._config.enabled_methods and self._embeddings_model:
            return True

        return False

    @property
    def available_methods(self) -> list[str]:
        """Lista de métodos disponibles."""
        methods = []

        if InferenceMethod.RULE_BASED in self._config.enabled_methods:
            methods.append("rule_based")

        for method in [
            InferenceMethod.LLAMA3_2,
            InferenceMethod.MISTRAL,
            InferenceMethod.GEMMA2,
            InferenceMethod.QWEN2_5,
        ]:
            if method in self._config.enabled_methods:
                if self._ollama_available.get(method.value, False):
                    methods.append(method.value)

        if InferenceMethod.EMBEDDINGS in self._config.enabled_methods and self._embeddings_model:
            methods.append("embeddings")

        return methods

    def analyze_character(
        self,
        character_id: int,
        character_name: str,
        text_samples: list[str],
        chapter_numbers: list[int],
        existing_attributes: Optional[dict] = None,
    ) -> Optional[CharacterBehaviorProfile]:
        """
        Analiza un personaje para construir su perfil comportamental.

        Usa votación entre múltiples métodos para mayor precisión.
        """
        if not self.is_available:
            logger.warning("Ningún método de inferencia disponible")
            return None

        all_traits: dict[str, list[float]] = {}  # trait -> [confidences]
        all_values: dict[str, list[float]] = {}
        all_expectations: list[BehavioralExpectation] = []
        methods_used = []

        # 1. Análisis basado en reglas (siempre disponible)
        if InferenceMethod.RULE_BASED in self._config.enabled_methods:
            traits, values = self._analyze_with_rules(text_samples)
            for trait, conf in traits.items():
                all_traits.setdefault(trait, []).append(conf)
            for value, conf in values.items():
                all_values.setdefault(value, []).append(conf)
            methods_used.append("rule_based")

        # 2. Análisis con modelos LLM
        llm_methods = [
            (InferenceMethod.LLAMA3_2, "llama3.2"),
            (InferenceMethod.MISTRAL, "mistral"),
            (InferenceMethod.GEMMA2, "gemma2"),
            (InferenceMethod.QWEN2_5, "qwen2.5"),
        ]

        for method, model_name in llm_methods:
            if method not in self._config.enabled_methods:
                continue
            if not self._ollama_available.get(model_name, False):
                continue

            result = self._analyze_with_llm(
                model_name, character_name, text_samples, chapter_numbers, existing_attributes
            )
            if result:
                for trait in result.get("personality_traits", []):
                    all_traits.setdefault(trait, []).append(0.8)
                for value in result.get("values", []):
                    all_values.setdefault(value, []).append(0.8)

                # Convertir expectativas
                for exp_data in result.get("behavioral_expectations", []):
                    try:
                        exp = self._parse_expectation(
                            exp_data, character_id, character_name, model_name
                        )
                        all_expectations.append(exp)
                    except Exception as e:
                        logger.debug(f"Error parseando expectativa: {e}")

                methods_used.append(model_name)

        # 3. Análisis con embeddings (similitud semántica)
        if InferenceMethod.EMBEDDINGS in self._config.enabled_methods and self._embeddings_model:
            emb_traits = self._analyze_with_embeddings(text_samples)
            for trait, conf in emb_traits.items():
                all_traits.setdefault(trait, []).append(conf)
            methods_used.append("embeddings")

        # 4. Votación y consolidación
        final_traits = self._consolidate_votes(all_traits)
        final_values = self._consolidate_votes(all_values)
        final_expectations = self._consolidate_expectations(all_expectations)

        # Construir perfil
        profile = CharacterBehaviorProfile(
            character_id=character_id,
            character_name=character_name,
            personality_traits=list(final_traits.keys()),
            values=list(final_values.keys()),
            fears=[],  # Extraer de expectativas
            goals=[],  # Extraer de expectativas
            speech_patterns=[],
            expectations=final_expectations,
            analyzed_chapters=chapter_numbers,
            methods_used=methods_used,
        )

        # Cachear
        self._profiles[character_id] = profile
        return profile

    def _analyze_with_rules(
        self, text_samples: list[str]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Análisis basado en reglas y patrones."""
        text = " ".join(text_samples).lower()
        traits = {}
        values = {}

        # Buscar patrones de rasgos
        for trait, patterns in self.TRAIT_PATTERNS.items():
            count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)
            if count > 0:
                # Normalizar confianza basada en frecuencia
                confidence = min(0.9, 0.3 + count * 0.1)
                traits[trait] = confidence

        # Buscar patrones de valores
        for value, patterns in self.VALUE_PATTERNS.items():
            count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)
            if count > 0:
                confidence = min(0.9, 0.3 + count * 0.1)
                values[value] = confidence

        return traits, values

    def _analyze_with_llm(
        self,
        model_name: str,
        character_name: str,
        text_samples: list[str],
        chapter_numbers: list[int],
        existing_attributes: Optional[dict],
    ) -> Optional[dict]:
        """Análisis usando un modelo LLM específico."""
        try:
            import httpx

            samples_text = "\n\n---\n\n".join(
                [f"[Capítulo {ch}]\n{text}" for text, ch in zip(text_samples, chapter_numbers)]
            )

            prompt = f"""Analiza el siguiente personaje basándote en los fragmentos de texto proporcionados.

PERSONAJE: {character_name}

ATRIBUTOS CONOCIDOS:
{existing_attributes if existing_attributes else "Ninguno especificado"}

FRAGMENTOS DE TEXTO:
{samples_text[:8000]}

Extrae la siguiente información sobre el personaje:

{{
  "personality_traits": ["lista de rasgos de personalidad observados"],
  "values": ["valores y principios que guían al personaje"],
  "fears": ["miedos o preocupaciones del personaje"],
  "goals": ["objetivos o motivaciones"],
  "speech_patterns": ["patrones de habla distintivos"],
  "behavioral_expectations": [
    {{
      "type": "behavioral|relational|knowledge|capability|temporal|contextual",
      "description": "qué esperaríamos que haga/no haga",
      "reasoning": "por qué esperamos esto basado en el texto",
      "confidence": 0.0-1.0,
      "source_chapters": [números de capítulos],
      "related_traits": ["rasgos relacionados"]
    }}
  ]
}}"""

            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": f"{self.CHARACTER_ANALYSIS_SYSTEM}\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 2048,
                    }
                },
                timeout=600.0,  # 10 min - CPU sin GPU es muy lento
            )

            if response.status_code == 200:
                text = response.json().get("response", "")
                # Extraer JSON de la respuesta
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    import json
                    return json.loads(text[start:end])

        except Exception as e:
            logger.debug(f"Error en análisis LLM ({model_name}): {e}")

        return None

    def _analyze_with_embeddings(self, text_samples: list[str]) -> dict[str, float]:
        """Análisis usando similitud de embeddings."""
        if not self._embeddings_model:
            return {}

        try:
            # Definir arquetipos de rasgos con descripciones
            trait_descriptions = {
                "valiente": "una persona valiente que enfrenta el peligro sin miedo",
                "cobarde": "una persona cobarde que huye del peligro y tiene miedo",
                "amable": "una persona amable, gentil y compasiva con los demás",
                "cruel": "una persona cruel, despiadada y sin compasión",
                "inteligente": "una persona inteligente, astuta y perspicaz",
                "impulsivo": "una persona impulsiva que actúa sin pensar",
                "honesto": "una persona honesta que siempre dice la verdad",
                "mentiroso": "una persona mentirosa que engaña a los demás",
            }

            text = " ".join(text_samples[:5])[:2000]  # Limitar texto
            text_emb = self._embeddings_model.encode([text])[0]

            traits = {}
            for trait, desc in trait_descriptions.items():
                trait_emb = self._embeddings_model.encode([desc])[0]
                # Calcular similitud coseno
                similarity = float(
                    sum(a * b for a, b in zip(text_emb, trait_emb)) /
                    (sum(a**2 for a in text_emb)**0.5 * sum(b**2 for b in trait_emb)**0.5)
                )
                if similarity > 0.3:  # Umbral mínimo
                    traits[trait] = similarity

            return traits

        except Exception as e:
            logger.debug(f"Error en análisis con embeddings: {e}")
            return {}

    def _parse_expectation(
        self,
        exp_data: dict,
        character_id: int,
        character_name: str,
        method: str,
    ) -> BehavioralExpectation:
        """Parsea datos de expectativa a objeto."""
        try:
            exp_type = ExpectationType(exp_data.get("type", "behavioral"))
        except ValueError:
            exp_type = ExpectationType.BEHAVIORAL

        return BehavioralExpectation(
            character_id=character_id,
            character_name=character_name,
            expectation_type=exp_type,
            description=exp_data.get("description", ""),
            reasoning=exp_data.get("reasoning", ""),
            confidence=float(exp_data.get("confidence", 0.5)),
            source_chapters=exp_data.get("source_chapters", []),
            related_traits=exp_data.get("related_traits", []),
            inference_method=method,
        )

    def _consolidate_votes(
        self, votes: dict[str, list[float]]
    ) -> dict[str, float]:
        """Consolida votos de múltiples métodos."""
        consolidated = {}
        for item, confidences in votes.items():
            if len(confidences) >= 2:  # Requiere al menos 2 votos
                avg_confidence = sum(confidences) / len(confidences)
                if avg_confidence >= self._config.min_confidence:
                    consolidated[item] = avg_confidence
            elif len(confidences) == 1 and confidences[0] >= 0.7:
                # Un solo voto con alta confianza
                consolidated[item] = confidences[0]

        return consolidated

    def _consolidate_expectations(
        self, expectations: list[BehavioralExpectation]
    ) -> list[BehavioralExpectation]:
        """Consolida expectativas similares de múltiples métodos."""
        if not expectations:
            return []

        # Agrupar por tipo y descripción similar
        groups: dict[str, list[BehavioralExpectation]] = {}

        for exp in expectations:
            key = f"{exp.expectation_type.value}:{exp.description[:50]}"
            groups.setdefault(key, []).append(exp)

        # Consolidar cada grupo
        consolidated = []
        for group in groups.values():
            if len(group) == 1:
                consolidated.append(group[0])
            else:
                # Combinar expectativas similares
                best = max(group, key=lambda e: e.confidence)
                best.votes = {e.inference_method or "unknown": e.confidence for e in group}
                best.confidence = sum(e.confidence for e in group) / len(group)
                consolidated.append(best)

        # Ordenar por confianza
        consolidated.sort(key=lambda e: e.confidence, reverse=True)
        return consolidated

    def detect_violations(
        self,
        character_id: int,
        text: str,
        chapter_number: int,
        position: int = 0,
    ) -> list[ExpectationViolation]:
        """
        Detecta violaciones de expectativas usando múltiples métodos con votación.
        """
        if not self.is_available:
            return []

        profile = self._profiles.get(character_id)
        if not profile:
            return []

        all_violations: dict[str, list[ExpectationViolation]] = {}

        # 1. Detección con reglas
        if InferenceMethod.RULE_BASED in self._config.enabled_methods:
            rule_violations = self._detect_with_rules(profile, text, chapter_number, position)
            for v in rule_violations:
                key = f"{v.violation_text[:50]}:{v.explanation[:50]}"
                all_violations.setdefault(key, []).append(v)

        # 2. Detección con LLMs
        for method, model_name in [
            (InferenceMethod.LLAMA3_2, "llama3.2"),
            (InferenceMethod.MISTRAL, "mistral"),
        ]:
            if method not in self._config.enabled_methods:
                continue
            if not self._ollama_available.get(model_name, False):
                continue

            llm_violations = self._detect_with_llm(
                model_name, profile, text, chapter_number, position
            )
            for v in llm_violations:
                key = f"{v.violation_text[:50]}:{v.explanation[:50]}"
                all_violations.setdefault(key, []).append(v)

        # Consolidar con votación
        final_violations = []
        for key, violations in all_violations.items():
            if len(violations) >= 2 or (len(violations) == 1 and violations[0].consensus_score > 0.7):
                # Consenso alcanzado
                best = violations[0]
                best.detection_methods = [v.detection_methods[0] for v in violations if v.detection_methods]
                best.consensus_score = len(violations) / len(self.available_methods)
                final_violations.append(best)

        return final_violations

    def _detect_with_rules(
        self,
        profile: CharacterBehaviorProfile,
        text: str,
        chapter_number: int,
        position: int,
    ) -> list[ExpectationViolation]:
        """Detecta violaciones usando patrones."""
        violations = []

        # Contradicciones de rasgos
        trait_contradictions = {
            "valiente": ["cobarde", "huyó", "temblaba de miedo"],
            "cobarde": ["se enfrentó valientemente", "sin miedo"],
            "pacífico": ["atacó", "golpeó", "violentamente"],
            "violento": ["pacíficamente", "sin violencia"],
            "honesto": ["mintió", "engañó", "ocultó"],
            "leal": ["traicionó", "vendió", "delató"],
        }

        text_lower = text.lower()
        for trait in profile.personality_traits:
            contradictions = trait_contradictions.get(trait.lower(), [])
            for pattern in contradictions:
                if re.search(pattern, text_lower):
                    # Encontrar el texto exacto
                    match = re.search(pattern, text_lower)
                    if match:
                        violation_text = text[max(0, match.start()-50):min(len(text), match.end()+50)]

                        # Buscar expectativa relacionada
                        related_exp = next(
                            (e for e in profile.expectations
                             if trait.lower() in [t.lower() for t in e.related_traits]),
                            None
                        )
                        if not related_exp:
                            related_exp = BehavioralExpectation(
                                character_id=profile.character_id,
                                character_name=profile.character_name,
                                expectation_type=ExpectationType.BEHAVIORAL,
                                description=f"Se espera comportamiento {trait}",
                                reasoning=f"El personaje ha mostrado rasgos de {trait}",
                                confidence=0.7,
                                related_traits=[trait],
                            )

                        violations.append(ExpectationViolation(
                            expectation=related_exp,
                            violation_text=violation_text,
                            chapter_number=chapter_number,
                            position=position + (match.start() if match else 0),
                            severity=ViolationSeverity.MEDIUM,
                            explanation=f"El personaje {profile.character_name} actúa de forma contraria a su rasgo '{trait}'",
                            detection_methods=["rule_based"],
                            consensus_score=0.5,
                        ))

        return violations

    def _detect_with_llm(
        self,
        model_name: str,
        profile: CharacterBehaviorProfile,
        text: str,
        chapter_number: int,
        position: int,
    ) -> list[ExpectationViolation]:
        """
        Detecta violaciones de expectativas usando LLM.

        Envía el perfil del personaje y el texto al modelo LLM para
        analizar si hay comportamientos que contradicen la caracterización.
        """
        import httpx
        import json

        violations = []

        try:
            # Preparar contexto del personaje
            traits_text = ", ".join(profile.personality_traits[:10]) if profile.personality_traits else "sin rasgos definidos"
            values_text = ", ".join(profile.values[:5]) if profile.values else "sin valores definidos"

            # Formatear expectativas para el prompt
            expectations_text = "\n".join([
                f"- [{e.expectation_type.value}] {e.description} (confianza: {e.confidence:.0%})"
                for e in profile.expectations[:5]
            ]) if profile.expectations else "Sin expectativas definidas"

            prompt = f"""Analiza si el siguiente texto contiene comportamientos que contradicen la caracterización establecida del personaje.

PERSONAJE: {profile.character_name}

RASGOS DE PERSONALIDAD: {traits_text}

VALORES: {values_text}

EXPECTATIVAS COMPORTAMENTALES:
{expectations_text}

TEXTO A ANALIZAR:
"{text[:2000]}"

Si encuentras violaciones de las expectativas, responde con JSON:
{{
  "violations": [
    {{
      "violation_text": "extracto corto del texto donde ocurre la violación",
      "severity": "critical|high|medium|low",
      "explanation": "explicación de por qué es una violación",
      "expectation_violated": "descripción de la expectativa violada",
      "justifications": ["posible justificación 1", "posible justificación 2"]
    }}
  ]
}}

Si NO hay violaciones, responde:
{{"violations": []}}

IMPORTANTE: Solo marca como violación si claramente contradice la caracterización. No marques si es ambiguo o podría tener justificación narrativa."""

            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": f"{self.CHARACTER_ANALYSIS_SYSTEM}\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Bajo para más consistencia
                        "num_predict": 1024,
                    }
                },
                timeout=120.0,
            )

            if response.status_code == 200:
                response_text = response.json().get("response", "")

                # Extraer JSON de la respuesta
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    data = json.loads(response_text[start:end])

                    for v in data.get("violations", []):
                        # Mapear severidad
                        severity_map = {
                            "critical": ViolationSeverity.CRITICAL,
                            "high": ViolationSeverity.HIGH,
                            "medium": ViolationSeverity.MEDIUM,
                            "low": ViolationSeverity.LOW,
                        }
                        severity = severity_map.get(v.get("severity", "medium"), ViolationSeverity.MEDIUM)

                        # Encontrar o crear expectativa relacionada
                        related_exp = next(
                            (e for e in profile.expectations
                             if v.get("expectation_violated", "").lower() in e.description.lower()),
                            None
                        )
                        if not related_exp:
                            related_exp = BehavioralExpectation(
                                character_id=profile.character_id,
                                character_name=profile.character_name,
                                expectation_type=ExpectationType.BEHAVIORAL,
                                description=v.get("expectation_violated", "Expectativa de comportamiento"),
                                reasoning="Detectado por análisis LLM",
                                confidence=0.6,
                            )

                        violation = ExpectationViolation(
                            expectation=related_exp,
                            violation_text=v.get("violation_text", text[:100]),
                            chapter_number=chapter_number,
                            position=position,
                            severity=severity,
                            explanation=v.get("explanation", ""),
                            possible_justifications=v.get("justifications", []),
                            detection_methods=[model_name],
                            consensus_score=0.6,  # Un solo método
                        )
                        violations.append(violation)

                    logger.debug(f"LLM ({model_name}) detectó {len(violations)} violaciones")

        except json.JSONDecodeError as e:
            logger.debug(f"Error parseando respuesta JSON de {model_name}: {e}")
        except httpx.TimeoutException:
            logger.debug(f"Timeout en detección LLM ({model_name})")
        except Exception as e:
            logger.debug(f"Error en detección LLM ({model_name}): {e}")

        return violations

    def get_profile(self, character_id: int) -> Optional[CharacterBehaviorProfile]:
        """Obtiene el perfil cacheado de un personaje."""
        return self._profiles.get(character_id)

    def clear_profile(self, character_id: int) -> None:
        """Elimina el perfil cacheado de un personaje."""
        self._profiles.pop(character_id, None)

    def clear_all_profiles(self) -> None:
        """Elimina todos los perfiles cacheados."""
        self._profiles.clear()

    def update_config(self, config: InferenceConfig) -> None:
        """Actualiza la configuración y recarga métodos disponibles."""
        self._config = config
        self._check_available_methods()


# Singleton
_engine: Optional[ExpectationInferenceEngine] = None
_engine_lock = threading.Lock()


def _get_engine() -> ExpectationInferenceEngine:
    """Obtiene el motor singleton (thread-safe)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ExpectationInferenceEngine()
    return _engine


def infer_expectations(
    character_id: int,
    character_name: str,
    text_samples: list[str],
    chapter_numbers: list[int],
    existing_attributes: Optional[dict] = None,
) -> Optional[CharacterBehaviorProfile]:
    """
    Función de conveniencia para analizar un personaje.
    """
    engine = _get_engine()
    return engine.analyze_character(
        character_id=character_id,
        character_name=character_name,
        text_samples=text_samples,
        chapter_numbers=chapter_numbers,
        existing_attributes=existing_attributes,
    )


def detect_expectation_violations(
    character_id: int,
    text: str,
    chapter_number: int,
    position: int = 0,
) -> list[ExpectationViolation]:
    """
    Función de conveniencia para detectar violaciones.
    """
    engine = _get_engine()
    return engine.detect_violations(
        character_id=character_id,
        text=text,
        chapter_number=chapter_number,
        position=position,
    )
