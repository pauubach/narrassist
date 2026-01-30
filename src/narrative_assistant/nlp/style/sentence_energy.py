"""
Detector de energía de oraciones (Sentence Energy).

Analiza la "energía" de cada oración basándose en:
- Voz activa vs. voz pasiva (ser/estar + participio)
- Verbos débiles vs. verbos de acción
- Tipo de oración (interrogativa, exclamativa, imperativa vs. declarativa)
- Longitud y estructura

Una oración con baja energía es plana: voz pasiva, verbos débiles,
estructura declarativa larga. Una oración con alta energía es dinámica:
verbos de acción, voz activa, variedad de puntuación.

Inspirado en ProWritingAid's Sentence Energy check y la guía de estilo
de Sol Stein ("Stein on Writing").

Referencias:
- Stein, Sol. "Stein on Writing" (1995) — "Use active verbs"
- ProWritingAid: Sentence Energy report
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...core.result import Result
from ...core.errors import NLPError, ErrorSeverity

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["SentenceEnergyDetector"] = None


def get_sentence_energy_detector() -> "SentenceEnergyDetector":
    """Obtener instancia singleton del detector de energía de oraciones."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SentenceEnergyDetector()

    return _instance


def reset_sentence_energy_detector() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================

class EnergyLevel(Enum):
    """Nivel de energía de una oración."""
    VERY_LOW = "very_low"    # 0-20: muy plana, pasiva, verbos débiles
    LOW = "low"              # 20-40: baja energía
    MEDIUM = "medium"        # 40-60: energía moderada
    HIGH = "high"            # 60-80: buena energía
    VERY_HIGH = "very_high"  # 80-100: máxima energía, acción directa


class EnergyIssueType(Enum):
    """Tipo de problema de energía detectado."""
    PASSIVE_VOICE = "passive_voice"
    WEAK_VERB = "weak_verb"
    NOMINALIZATION = "nominalization"
    EXCESSIVE_LENGTH = "excessive_length"


@dataclass
class EnergyIssue:
    """Un problema específico que reduce la energía de una oración."""
    issue_type: EnergyIssueType
    detail: str           # Texto que causa el problema
    suggestion: str       # Sugerencia de mejora
    penalty: float        # Penalización al score (0-1)

    def to_dict(self) -> dict:
        return {
            "type": self.issue_type.value,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "penalty": round(self.penalty, 2),
        }


@dataclass
class SentenceEnergy:
    """Análisis de energía de una oración individual."""

    # Texto
    text: str
    start_char: int
    end_char: int

    # Score principal
    energy_score: float       # 0-100
    energy_level: EnergyLevel

    # Sub-scores
    voice_score: float        # 0-100 (100=activa, 0=pasiva)
    verb_strength: float      # 0-100 (100=verbo fuerte, 0=débil)
    structure_score: float    # 0-100 (variedad de puntuación, longitud)

    # Problemas detectados
    issues: list[EnergyIssue] = field(default_factory=list)

    # Flags
    is_passive: bool = False
    has_weak_verb: bool = False
    has_nominalization: bool = False

    # Contexto
    chapter: int = 0
    word_count: int = 0

    def to_dict(self) -> dict:
        return {
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "energy_score": round(self.energy_score, 1),
            "energy_level": self.energy_level.value,
            "voice_score": round(self.voice_score, 1),
            "verb_strength": round(self.verb_strength, 1),
            "structure_score": round(self.structure_score, 1),
            "issues": [i.to_dict() for i in self.issues],
            "is_passive": self.is_passive,
            "has_weak_verb": self.has_weak_verb,
            "has_nominalization": self.has_nominalization,
            "chapter": self.chapter,
            "word_count": self.word_count,
        }


@dataclass
class SentenceEnergyReport:
    """Resultado del análisis de energía de oraciones."""

    # Oraciones analizadas
    sentences: list[SentenceEnergy] = field(default_factory=list)

    # Estadísticas globales
    total_sentences: int = 0
    avg_energy: float = 0.0
    avg_voice_score: float = 0.0
    avg_verb_strength: float = 0.0
    avg_structure_score: float = 0.0

    # Distribución por nivel
    by_level: dict[str, int] = field(default_factory=dict)

    # Conteos de problemas
    passive_count: int = 0
    weak_verb_count: int = 0
    nominalization_count: int = 0

    # Solo oraciones con baja energía (para highlight)
    low_energy_sentences: list[SentenceEnergy] = field(default_factory=list)

    # Recomendaciones
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sentences": [s.to_dict() for s in self.sentences],
            "statistics": {
                "total_sentences": self.total_sentences,
                "avg_energy": round(self.avg_energy, 1),
                "avg_voice_score": round(self.avg_voice_score, 1),
                "avg_verb_strength": round(self.avg_verb_strength, 1),
                "avg_structure_score": round(self.avg_structure_score, 1),
            },
            "by_level": self.by_level,
            "issues": {
                "passive_count": self.passive_count,
                "weak_verb_count": self.weak_verb_count,
                "nominalization_count": self.nominalization_count,
            },
            "low_energy_sentences": [s.to_dict() for s in self.low_energy_sentences],
            "recommendations": self.recommendations,
        }


# =============================================================================
# Listas lingüísticas para español
# =============================================================================

# Verbos débiles: verbos que no transmiten acción concreta
WEAK_VERBS = {
    # Ser / Estar (copulativos)
    "ser", "estar",
    "soy", "eres", "es", "somos", "sois", "son",
    "era", "eras", "éramos", "erais", "eran",
    "fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron",
    "seré", "serás", "será", "seremos", "seréis", "serán",
    "sería", "serías", "seríamos", "seríais", "serían",
    "sea", "seas", "seamos", "seáis", "sean",
    "estoy", "estás", "está", "estamos", "estáis", "están",
    "estaba", "estabas", "estábamos", "estabais", "estaban",
    "estuve", "estuviste", "estuvo", "estuvimos", "estuvisteis", "estuvieron",
    "estaré", "estarás", "estará", "estaremos", "estaréis", "estarán",
    "estaría", "estarías", "estaríamos", "estaríais", "estarían",
    # Haber (auxiliar)
    "haber", "he", "has", "ha", "hemos", "habéis", "han",
    "había", "habías", "habíamos", "habíais", "habían",
    "hubo", "hay",
    "habré", "habrás", "habrá", "habremos", "habréis", "habrán",
    "habría", "habrías", "habríamos", "habríais", "habrían",
    "haya", "hayas", "hayamos", "hayáis", "hayan",
    # Tener
    "tener", "tengo", "tienes", "tiene", "tenemos", "tenéis", "tienen",
    "tenía", "tenías", "teníamos", "teníais", "tenían",
    "tuvo", "tuve", "tuviste", "tuvimos", "tuvisteis", "tuvieron",
    "tendré", "tendrás", "tendrá", "tendremos", "tendréis", "tendrán",
    "tendría", "tendrías", "tendríamos", "tendríais", "tendrían",
    # Hacer (cuando es genérico)
    "hacer", "hago", "haces", "hace", "hacemos", "hacéis", "hacen",
    "hacía", "hacías", "hacíamos", "hacíais", "hacían",
    "hizo", "hice", "hiciste", "hicimos", "hicisteis", "hicieron",
    "haré", "harás", "hará", "haremos", "haréis", "harán",
    "haría", "harías", "haríamos", "haríais", "harían",
    # Parecer
    "parecer", "parezco", "pareces", "parece", "parecemos", "parecéis", "parecen",
    "parecía", "parecías", "parecíamos", "parecíais", "parecían",
    # Resultar
    "resultar", "resulta", "resultan", "resultaba", "resultaban",
    # Poder (modal, no acción)
    "poder", "puedo", "puedes", "puede", "podemos", "podéis", "pueden",
    "podía", "podías", "podíamos", "podíais", "podían",
    "pudo", "pude", "pudiste", "pudimos", "pudisteis", "pudieron",
    "podré", "podrás", "podrá", "podremos", "podréis", "podrán",
    "podría", "podrías", "podríamos", "podríais", "podrían",
    # Deber (modal)
    "deber", "debo", "debes", "debe", "debemos", "debéis", "deben",
    "debía", "debías", "debíamos", "debíais", "debían",
    "debería", "deberías", "deberíamos", "deberíais", "deberían",
    # Ir (cuando es auxiliar/perifrástico)
    "ir", "voy", "vas", "va", "vamos", "vais", "van",
    "iba", "ibas", "íbamos", "ibais", "iban",
    # Existenciales genéricos
    "existir", "existe", "existen", "existía", "existían",
    "haber", "hay", "había", "hubo",
    # Quedar
    "quedar", "queda", "quedan", "quedaba", "quedaban",
}

# Participios pasados más frecuentes en español (para detección de voz pasiva)
# El patrón principal es: ser/estar + participio (-ado, -ido, -to, -so, -cho)
PASSIVE_AUXILIARIES = {
    "ser", "soy", "eres", "es", "somos", "sois", "son",
    "era", "eras", "éramos", "erais", "eran",
    "fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron",
    "seré", "serás", "será", "seremos", "seréis", "serán",
    "sería", "serías", "seríamos", "seríais", "serían",
    "sea", "seas", "seamos", "seáis", "sean",
    "fuera", "fueras", "fuéramos", "fuerais", "fueran",
    "fuese", "fueses", "fuésemos", "fueseis", "fuesen",
    "sido",
    # Nota: estar NO se incluye — "estar + participio" es construcción
    # estativa/atributiva, NO voz pasiva (RAE, Nueva Gramática §41.6)
}

# Sufijos de nominalizaciones (verbos convertidos en sustantivos abstractos)
NOMINALIZATION_SUFFIXES = (
    "ción", "sión", "miento", "amiento", "imiento",
    "ncia", "encia", "anza", "idad", "edad",
)

# Palabras que NO son nominalizaciones aunque terminen en esos sufijos
NOMINALIZATION_EXCEPTIONS = {
    "acción", "nación", "canción", "estación", "atención",
    "emoción", "pasión", "tensión", "presión", "expresión",
    "momento", "pensamiento", "sentimiento", "movimiento",
    "presencia", "ausencia", "ciencia", "conciencia",
    "esperanza", "confianza", "distancia",
    "ciudad", "sociedad", "realidad", "verdad",
    "corazón", "razón",
    # Sustantivos completamente lexicalizados (no derivaciones productivas)
    "habitación", "posición", "dirección", "educación", "situación",
    "información", "comunicación", "organización", "condición",
    "alimentación", "población", "relación", "tradición",
    "religión", "televisión", "decisión", "comisión",
    "dimensión", "ocasión", "profesión", "sesión", "misión",
    "conocimiento", "nacimiento", "crecimiento", "departamento",
    "apartamento", "documento", "instrumento", "monumento",
    "independencia", "experiencia", "diferencia", "referencia",
    "competencia", "existencia", "paciencia", "violencia",
    "importancia", "tolerancia", "sustancia", "abundancia",
    "seguridad", "capacidad", "necesidad", "actividad",
    "comunidad", "oportunidad", "identidad", "universidad",
}


# Colocaciones fuertes de "hacer" donde el verbo NO es débil
HACER_STRONG_COLLOCATIONS = {
    "trizas", "pedazos", "añicos", "frente", "caso", "falta",
    "daño", "ruido", "fuego", "efecto", "justicia", "historia",
    "honor", "mella", "gracia", "cola", "trampa",
}

# Excepciones de "ir" como verbo de movimiento (no débil)
# Patrón: ir/fue/va + preposición locativa → movimiento = enérgico
IR_MOVEMENT_PREPS = {"a", "al", "hacia", "hasta", "por", "de", "desde"}

# Formas de "ir" para la detección contextual
IR_FORMS = {
    "ir", "voy", "vas", "va", "vamos", "vais", "van",
    "iba", "ibas", "íbamos", "ibais", "iban",
    "fue", "fui", "fuiste", "fuimos", "fuisteis", "fueron",
}

# Formas de "hacer" para detección de colocaciones
HACER_FORMS = {
    "hacer", "hago", "haces", "hace", "hacemos", "hacéis", "hacen",
    "hacía", "hacías", "hacíamos", "hacíais", "hacían",
    "hizo", "hice", "hiciste", "hicimos", "hicisteis", "hicieron",
    "haré", "harás", "hará", "haremos", "haréis", "harán",
    "haría", "harías", "haríamos", "haríais", "harían",
}

# Formas de "haber" (auxiliar) para detección de tiempos compuestos
HABER_FORMS = {
    "he", "has", "ha", "hemos", "habéis", "han",
    "había", "habías", "habíamos", "habíais", "habían",
    "hubo", "hube", "hubiste", "hubimos", "hubisteis", "hubieron",
    "habré", "habrás", "habrá", "habremos", "habréis", "habrán",
    "habría", "habrías", "habríamos", "habríais", "habrían",
    "haya", "hayas", "hayamos", "hayáis", "hayan",
}

# Excepciones idiomáticas de pasiva refleja (no son pasivas reales)
REFLEXIVE_PASSIVE_EXCEPTIONS = {
    "se trata", "se dice", "se sabe", "se cree", "se supone",
    "se espera", "se puede", "se debe", "se necesita", "se quiere",
    "se ve", "se oye", "se nota", "se parece", "se llama",
    "se acerca", "se aleja", "se acuerda", "se olvida",
    "se da cuenta", "se pone", "se queda", "se siente",
}


# =============================================================================
# Detector
# =============================================================================

class SentenceEnergyDetector:
    """
    Detector de energía de oraciones.

    Evalúa cada oración en tres dimensiones:
    1. Voz (activa vs pasiva): peso 40%
    2. Fuerza del verbo (acción vs débil): peso 40%
    3. Estructura (tipo y longitud): peso 20%
    """

    # Pesos para el score compuesto
    WEIGHT_VOICE = 0.40
    WEIGHT_VERB = 0.40
    WEIGHT_STRUCTURE = 0.20

    def __init__(
        self,
        low_energy_threshold: float = 40.0,
        min_words: int = 4,
    ):
        """
        Inicializar detector.

        Args:
            low_energy_threshold: Umbral bajo el cual se marca como baja energía (0-100)
            min_words: Mínimo de palabras para analizar una oración
        """
        self.low_energy_threshold = low_energy_threshold
        self.min_words = min_words

        # Patrones compilados
        self._sentence_pattern = re.compile(
            r'[.!?…]+(?:\s+|$)|[\n]{2,}',
            re.UNICODE
        )
        self._word_pattern = re.compile(
            r'\b([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)\b',
            re.UNICODE
        )
        # Participio: -ado, -ido, -to, -so, -cho
        self._participle_pattern = re.compile(
            r'\b\w+(?:ado|ada|ados|adas|ido|ida|idos|idas'
            r'|to|ta|tos|tas|so|sa|sos|sas|cho|cha|chos|chas)\b',
            re.IGNORECASE | re.UNICODE
        )
        # Nominalizaciones por sufijo
        self._nominalization_pattern = re.compile(
            r'\b[a-záéíóúüñ]+(?:ción|sión|miento|amiento|imiento'
            r'|ncia|encia|anza|idad|edad)\b',
            re.IGNORECASE | re.UNICODE
        )

    def analyze(
        self,
        text: str,
        chapter: int = 0,
        low_threshold: Optional[float] = None,
    ) -> Result[SentenceEnergyReport]:
        """
        Analizar energía de oraciones en un texto.

        Args:
            text: Texto a analizar
            chapter: Número de capítulo para contexto
            low_threshold: Umbral de baja energía (override del default)

        Returns:
            Result con SentenceEnergyReport
        """
        if not text or not text.strip():
            return Result.success(SentenceEnergyReport())

        threshold = low_threshold if low_threshold is not None else self.low_energy_threshold

        try:
            report = SentenceEnergyReport()
            sentences_raw = self._split_sentences(text)
            report.total_sentences = len(sentences_raw)

            all_energy = []
            all_voice = []
            all_verb = []
            all_structure = []

            for sent_text, start, end in sentences_raw:
                words = self._tokenize(sent_text)
                if len(words) < self.min_words:
                    continue

                # Analizar las 3 dimensiones
                voice_score, is_passive, voice_issues = self._analyze_voice(sent_text, words)
                verb_score, has_weak, verb_issues = self._analyze_verb_strength(words)
                structure_score, struct_issues = self._analyze_structure(sent_text, words)

                # Detectar nominalizaciones
                nom_issues = self._detect_nominalizations(sent_text)
                has_nom = len(nom_issues) > 0

                # Score compuesto
                energy_score = (
                    voice_score * self.WEIGHT_VOICE
                    + verb_score * self.WEIGHT_VERB
                    + structure_score * self.WEIGHT_STRUCTURE
                )

                # Penalizar nominalizaciones
                if nom_issues:
                    nom_penalty = min(len(nom_issues) * 5.0, 15.0)
                    energy_score = max(0, energy_score - nom_penalty)

                energy_level = self._get_energy_level(energy_score)

                all_issues = voice_issues + verb_issues + struct_issues + nom_issues

                sent_energy = SentenceEnergy(
                    text=sent_text,
                    start_char=start,
                    end_char=end,
                    energy_score=energy_score,
                    energy_level=energy_level,
                    voice_score=voice_score,
                    verb_strength=verb_score,
                    structure_score=structure_score,
                    issues=all_issues,
                    is_passive=is_passive,
                    has_weak_verb=has_weak,
                    has_nominalization=has_nom,
                    chapter=chapter,
                    word_count=len(words),
                )

                report.sentences.append(sent_energy)
                all_energy.append(energy_score)
                all_voice.append(voice_score)
                all_verb.append(verb_score)
                all_structure.append(structure_score)

                # Contadores
                if is_passive:
                    report.passive_count += 1
                if has_weak:
                    report.weak_verb_count += 1
                if has_nom:
                    report.nominalization_count += 1

                # Baja energía
                if energy_score < threshold:
                    report.low_energy_sentences.append(sent_energy)

                # Distribución
                level_key = energy_level.value
                report.by_level[level_key] = report.by_level.get(level_key, 0) + 1

            # Promedios
            if all_energy:
                report.avg_energy = sum(all_energy) / len(all_energy)
                report.avg_voice_score = sum(all_voice) / len(all_voice)
                report.avg_verb_strength = sum(all_verb) / len(all_verb)
                report.avg_structure_score = sum(all_structure) / len(all_structure)

            # Recomendaciones
            report.recommendations = self._generate_recommendations(report)

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error analyzing sentence energy: {e}", exc_info=True)
            error = NLPError(
                message=f"Error en análisis de energía de oraciones: {e}",
                severity=ErrorSeverity.RECOVERABLE,
            )
            return Result.failure(error)

    def analyze_by_chapter(
        self,
        chapters: list[tuple[int, str]],
    ) -> dict[int, SentenceEnergyReport]:
        """
        Analizar energía por capítulo.

        Args:
            chapters: Lista de tuplas (número_capítulo, contenido)

        Returns:
            Dict de chapter_num -> SentenceEnergyReport
        """
        results = {}
        for chapter_num, content in chapters:
            result = self.analyze(content, chapter=chapter_num)
            if result.is_success:
                results[chapter_num] = result.value
        return results

    # =========================================================================
    # Análisis de voz (activa vs pasiva)
    # =========================================================================

    def _analyze_voice(
        self, text: str, words: list[str]
    ) -> tuple[float, bool, list[EnergyIssue]]:
        """
        Analizar si la oración usa voz activa o pasiva.

        Patrón de voz pasiva en español:
        - Pasiva perifrástica: ser + participio ("fue construido")
        - Pasiva refleja: se + verbo 3ª persona ("se construyó")
        Nota: estar + participio es estativo, NO pasivo (RAE §41.6)

        Returns:
            (score 0-100, is_passive, issues)
        """
        issues = []
        words_lower = [w.lower() for w in words]
        text_lower = text.lower()

        passive_found = False

        # 1. Pasiva perifrástica: ser + participio
        for i, word in enumerate(words_lower):
            if word in PASSIVE_AUXILIARIES:
                # Buscar participio en las siguientes 3 palabras
                window = words_lower[i + 1: i + 4]
                for next_word in window:
                    if self._is_participle(next_word):
                        passive_found = True
                        passive_fragment = " ".join(words[i: i + 3])
                        issues.append(EnergyIssue(
                            issue_type=EnergyIssueType.PASSIVE_VOICE,
                            detail=passive_fragment,
                            suggestion="Considere reescribir en voz activa",
                            penalty=0.35,
                        ))
                        break
                if passive_found:
                    break

        # 2. Pasiva refleja: "se + verbo en 3ª persona"
        if not passive_found:
            for i, word in enumerate(words_lower):
                if word == "se" and i + 1 < len(words_lower):
                    # Comprobar que no es excepción idiomática
                    two_word = f"se {words_lower[i + 1]}"
                    three_word = f"se {' '.join(words_lower[i + 1: i + 3])}" if i + 2 < len(words_lower) else ""
                    if two_word in REFLEXIVE_PASSIVE_EXCEPTIONS or three_word in REFLEXIVE_PASSIVE_EXCEPTIONS:
                        continue
                    # Heurística: "se" + verbo conjugado en 3ª persona
                    next_word = words_lower[i + 1]
                    if self._looks_like_third_person_verb(next_word):
                        passive_found = True
                        passive_fragment = " ".join(words[i: i + 3])
                        issues.append(EnergyIssue(
                            issue_type=EnergyIssueType.PASSIVE_VOICE,
                            detail=f"Pasiva refleja: {passive_fragment}",
                            suggestion="Considere usar un sujeto activo explícito",
                            penalty=0.25,  # Menor que perifrástica (más natural en español)
                        ))
                        break

        # Score: 100 = activa, 30 = pasiva perifrástica, 45 = pasiva refleja
        if passive_found:
            # Pasiva refleja es más natural en español → menor penalización
            is_reflexive = any(i.detail.startswith("Pasiva refleja") for i in issues)
            score = 45.0 if is_reflexive else 30.0
        else:
            score = 100.0

        return score, passive_found, issues

    def _looks_like_third_person_verb(self, word: str) -> bool:
        """Heurística para detectar verbos en 3ª persona singular/plural."""
        # Terminaciones típicas de 3ª persona en español
        third_person_endings = (
            "a", "e", "ó", "ió", "an", "en", "aron", "ieron",
            "aba", "ía", "ará", "erá", "irá",
        )
        if len(word) < 3:
            return False
        # Excluir palabras que terminan así pero no son verbos
        if word in {"se", "de", "que", "le", "me", "te", "ne", "una", "la"}:
            return False
        return word.endswith(third_person_endings)

    def _is_participle(self, word: str) -> bool:
        """Verificar si una palabra parece ser un participio."""
        return bool(self._participle_pattern.match(word))

    # =========================================================================
    # Análisis de fuerza del verbo
    # =========================================================================

    def _analyze_verb_strength(
        self, words: list[str]
    ) -> tuple[float, bool, list[EnergyIssue]]:
        """
        Analizar la fuerza de los verbos en la oración.

        Excepciones contextuales:
        - haber + participio: evaluar el participio (verbo principal), no el auxiliar
        - ir + preposición locativa: verbo de movimiento (no débil)
        - hacer + colocación fuerte: "hacer trizas" es enérgico

        Returns:
            (score 0-100, has_weak_verb, issues)
        """
        issues = []
        words_lower = [w.lower() for w in words]

        weak_found = []
        # Índices a excluir (auxiliares de tiempos compuestos, etc.)
        skip_indices: set[int] = set()

        # Pre-scan: detectar haber + participio (G3)
        for i, word in enumerate(words_lower):
            if word in HABER_FORMS and i + 1 < len(words_lower):
                # Buscar participio en las siguientes 2 palabras
                for j in range(i + 1, min(i + 3, len(words_lower))):
                    if self._is_participle(words_lower[j]):
                        # El auxiliar haber NO es débil en tiempos compuestos
                        skip_indices.add(i)
                        break

        # Pre-scan: detectar ir + prep locativa (G4)
        for i, word in enumerate(words_lower):
            if word in IR_FORMS and i + 1 < len(words_lower):
                next_w = words_lower[i + 1]
                if next_w in IR_MOVEMENT_PREPS:
                    # "ir a la tienda" = movimiento, no débil
                    skip_indices.add(i)

        # Pre-scan: detectar hacer + colocación fuerte (G6)
        for i, word in enumerate(words_lower):
            if word in HACER_FORMS and i + 1 < len(words_lower):
                next_w = words_lower[i + 1]
                if next_w in HACER_STRONG_COLLOCATIONS:
                    skip_indices.add(i)

        for i, word in enumerate(words_lower):
            if i in skip_indices:
                continue
            if word in WEAK_VERBS:
                weak_found.append(word)

        has_weak = len(weak_found) > 0

        if not weak_found:
            score = 100.0
        elif len(weak_found) == 1:
            score = 70.0
        elif len(weak_found) == 2:
            score = 45.0
            issues.append(EnergyIssue(
                issue_type=EnergyIssueType.WEAK_VERB,
                detail=f"Verbos débiles: {', '.join(weak_found[:3])}",
                suggestion="Sustituya por verbos de acción más específicos",
                penalty=0.25,
            ))
        else:
            score = 20.0
            issues.append(EnergyIssue(
                issue_type=EnergyIssueType.WEAK_VERB,
                detail=f"Verbos débiles ({len(weak_found)}): {', '.join(weak_found[:4])}",
                suggestion="La oración acumula demasiados verbos sin acción concreta",
                penalty=0.40,
            ))

        return score, has_weak, issues

    # =========================================================================
    # Análisis de estructura
    # =========================================================================

    def _analyze_structure(
        self, text: str, words: list[str]
    ) -> tuple[float, list[EnergyIssue]]:
        """
        Analizar la estructura de la oración.

        Factores:
        - Tipo de puntuación (¡! ¿? → más energía)
        - Longitud (oraciones muy largas → menos energía)

        Returns:
            (score 0-100, issues)
        """
        issues = []
        score = 70.0  # Base neutra para declarativas

        text_stripped = text.strip()

        # Bonus por tipo de oración
        if text_stripped.endswith("!") or text_stripped.startswith("¡"):
            score = 90.0  # Exclamativa → alta energía
        elif text_stripped.endswith("?") or text_stripped.startswith("¿"):
            score = 85.0  # Interrogativa → buena energía
        elif text_stripped.endswith("...") or text_stripped.endswith("…"):
            score = 60.0  # Suspensiva → energía media

        # Penalización por longitud excesiva
        word_count = len(words)
        if word_count > 40:
            length_penalty = min((word_count - 40) * 1.5, 30.0)
            score = max(10, score - length_penalty)
            issues.append(EnergyIssue(
                issue_type=EnergyIssueType.EXCESSIVE_LENGTH,
                detail=f"Oración de {word_count} palabras",
                suggestion="Las oraciones largas pierden impacto. Considere dividirla.",
                penalty=round(length_penalty / 100, 2),
            ))
        elif word_count > 30:
            # Penalización menor
            score = max(30, score - 10.0)

        return score, issues

    # =========================================================================
    # Detección de nominalizaciones
    # =========================================================================

    def _detect_nominalizations(self, text: str) -> list[EnergyIssue]:
        """
        Detectar nominalizaciones (verbos convertidos en sustantivos abstractos).

        Ejemplo: "la realización de" → "realizar"
                 "el establecimiento de" → "establecer"
        """
        issues = []

        matches = self._nominalization_pattern.findall(text.lower())
        for match in matches:
            if match not in NOMINALIZATION_EXCEPTIONS and len(match) > 6:
                issues.append(EnergyIssue(
                    issue_type=EnergyIssueType.NOMINALIZATION,
                    detail=match,
                    suggestion=f'"{match}" podría expresarse con un verbo directo',
                    penalty=0.10,
                ))

        return issues

    # =========================================================================
    # Helpers
    # =========================================================================

    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """Dividir texto en oraciones con posiciones."""
        sentences = []

        parts = self._sentence_pattern.split(text)
        current_pos = 0

        for part in parts:
            part = part.strip()
            if not part:
                continue

            start = text.find(part, current_pos)
            if start == -1:
                start = current_pos
            end = start + len(part)

            if self._word_pattern.search(part):
                sentences.append((part, start, end))

            current_pos = end

        return sentences

    def _tokenize(self, text: str) -> list[str]:
        """Extraer palabras del texto."""
        return self._word_pattern.findall(text)

    def _get_energy_level(self, score: float) -> EnergyLevel:
        """Obtener nivel de energía según score."""
        if score >= 80:
            return EnergyLevel.VERY_HIGH
        elif score >= 60:
            return EnergyLevel.HIGH
        elif score >= 40:
            return EnergyLevel.MEDIUM
        elif score >= 20:
            return EnergyLevel.LOW
        else:
            return EnergyLevel.VERY_LOW

    def _generate_recommendations(self, report: SentenceEnergyReport) -> list[str]:
        """Generar recomendaciones basadas en el análisis."""
        recommendations = []

        if report.total_sentences == 0:
            return recommendations

        analyzed = len(report.sentences)
        if analyzed == 0:
            return recommendations

        # Energía promedio baja
        if report.avg_energy < 40:
            recommendations.append(
                f"La energía promedio del texto es baja ({report.avg_energy:.0f}/100). "
                "Considere usar más verbos de acción y voz activa."
            )
        elif report.avg_energy < 55:
            recommendations.append(
                f"La energía del texto es moderada ({report.avg_energy:.0f}/100). "
                "Hay margen para oraciones más dinámicas."
            )

        # Proporción de oraciones con baja energía
        low_ratio = len(report.low_energy_sentences) / analyzed
        if low_ratio > 0.30:
            recommendations.append(
                f"El {low_ratio*100:.0f}% de las oraciones tienen baja energía. "
                "Revise las marcadas para mejorar el dinamismo."
            )

        # Voz pasiva
        passive_ratio = report.passive_count / analyzed
        if passive_ratio > 0.20:
            recommendations.append(
                f"El {passive_ratio*100:.0f}% de las oraciones usan voz pasiva. "
                "La voz activa transmite más inmediatez."
            )
        elif report.passive_count > 3:
            recommendations.append(
                f"Hay {report.passive_count} oraciones en voz pasiva. "
                "Algunas podrían reescribirse en voz activa."
            )

        # Verbos débiles
        weak_ratio = report.weak_verb_count / analyzed
        if weak_ratio > 0.40:
            recommendations.append(
                f"El {weak_ratio*100:.0f}% de las oraciones contienen verbos débiles "
                "(ser, estar, tener, hacer). Busque verbos más específicos."
            )

        # Nominalizaciones
        if report.nominalization_count > 5:
            recommendations.append(
                f"Se detectaron {report.nominalization_count} nominalizaciones. "
                "Convertir sustantivos abstractos en verbos da más fuerza al texto."
            )

        # Tip genérico
        if report.avg_energy < 60 and not recommendations:
            recommendations.append(
                "Tip: Combine oraciones cortas y largas, alterne interrogaciones "
                "y exclamaciones para dar ritmo al texto."
            )

        return recommendations
