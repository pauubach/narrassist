"""
Tipos base para el módulo de corrección gramatical.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GrammarErrorType(Enum):
    """Tipos de errores gramaticales detectados."""

    # Concordancia
    GENDER_AGREEMENT = "gender_agreement"          # el casa → la casa
    NUMBER_AGREEMENT = "number_agreement"          # los casa → las casas
    SUBJECT_VERB_AGREEMENT = "subject_verb"        # ellos va → ellos van
    ADJECTIVE_AGREEMENT = "adjective_agreement"    # niña alto → niña alta

    # Uso de palabras
    WRONG_PREPOSITION = "wrong_preposition"        # voy a casa → voy a la casa
    MISSING_PREPOSITION = "missing_preposition"    # confío ti → confío en ti
    EXTRA_PREPOSITION = "extra_preposition"        # dijo de que → dijo que
    DEQUEISMO = "dequeismo"                        # pienso de que → pienso que
    QUEISMO = "queismo"                            # me alegro que → me alegro de que

    # Verbos
    WRONG_TENSE = "wrong_tense"                    # Ayer voy → Ayer fui
    WRONG_MOOD = "wrong_mood"                      # Subjuntivo/Indicativo
    INFINITIVE_ERROR = "infinitive_error"          # *Habemos → Hay/Somos
    GERUND_ERROR = "gerund_error"                  # *Siendo que → Ya que

    # Pronombres
    LEISMO = "leismo"                              # Le vi (persona) - aceptado en España
    LAISMO = "laismo"                              # La dije → Le dije
    LOISMO = "loismo"                              # Lo dije a ella → Le dije

    # Estructura
    WORD_ORDER = "word_order"                      # Orden incorrecto
    MISSING_WORD = "missing_word"                  # Falta palabra
    EXTRA_WORD = "extra_word"                      # Palabra sobrante
    SENTENCE_FRAGMENT = "sentence_fragment"        # Oración incompleta
    RUN_ON_SENTENCE = "run_on_sentence"            # Oración demasiado larga

    # Puntuación gramatical
    COMMA_SPLICE = "comma_splice"                  # Coma donde debería ir punto
    MISSING_COMMA = "missing_comma"                # Falta coma
    WRONG_PUNCTUATION = "wrong_punctuation"        # Puntuación incorrecta
    PUNCTUATION = "punctuation"                    # Error de puntuación general

    # Otros
    REDUNDANCY = "redundancy"                      # subir arriba, bajar abajo
    PLEONASM = "pleonasm"                          # Redundancia expresiva
    ANACOLUTHON = "anacoluthon"                    # Cambio brusco de estructura
    OTHER = "other"


class GrammarSeverity(Enum):
    """Severidad del error gramatical."""

    ERROR = "error"        # Error claro que debe corregirse
    WARNING = "warning"    # Posible error o estilo cuestionable
    STYLE = "style"        # Sugerencia de estilo
    INFO = "info"          # Información/posible mejora


class GrammarDetectionMethod(Enum):
    """Método que detectó el error."""

    SPACY_DEP = "spacy_dependency"    # Análisis de dependencias spaCy
    REGEX = "regex"                    # Patrón regex
    RULE = "rule"                      # Regla gramatical explícita
    LLM = "llm"                        # LLM local (Ollama)
    HEURISTIC = "heuristic"            # Heurística
    LANGUAGETOOL = "languagetool"      # LanguageTool (+2000 reglas)


@dataclass
class GrammarIssue:
    """Un error gramatical detectado."""

    # Texto y posición
    text: str                          # Fragmento con error
    start_char: int                    # Posición inicio en texto
    end_char: int                      # Posición fin en texto
    sentence: str                      # Oración completa

    # Clasificación
    error_type: GrammarErrorType
    severity: GrammarSeverity = GrammarSeverity.WARNING

    # Corrección
    suggestion: Optional[str] = None   # Corrección sugerida
    alternatives: list[str] = field(default_factory=list)

    # Metadata
    confidence: float = 0.5            # 0.0-1.0
    detection_method: GrammarDetectionMethod = GrammarDetectionMethod.RULE
    explanation: str = ""              # Explicación para el usuario
    rule_id: str = ""                  # ID de la regla aplicada

    # Contexto gramatical
    affected_words: list[str] = field(default_factory=list)
    grammatical_context: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validar y normalizar."""
        self.confidence = max(0.0, min(1.0, self.confidence))
        if not self.explanation:
            self.explanation = self._generate_explanation()

    def _generate_explanation(self) -> str:
        """Generar explicación por defecto según tipo de error."""
        explanations = {
            GrammarErrorType.GENDER_AGREEMENT: "Error de concordancia de género",
            GrammarErrorType.NUMBER_AGREEMENT: "Error de concordancia de número",
            GrammarErrorType.SUBJECT_VERB_AGREEMENT: "El sujeto y el verbo no concuerdan",
            GrammarErrorType.ADJECTIVE_AGREEMENT: "El adjetivo no concuerda con el sustantivo",
            GrammarErrorType.WRONG_PREPOSITION: "Preposición incorrecta",
            GrammarErrorType.MISSING_PREPOSITION: "Falta una preposición",
            GrammarErrorType.EXTRA_PREPOSITION: "Preposición innecesaria",
            GrammarErrorType.DEQUEISMO: "Dequeísmo: uso incorrecto de 'de que'",
            GrammarErrorType.QUEISMO: "Queísmo: falta 'de' antes de 'que'",
            GrammarErrorType.WRONG_TENSE: "Tiempo verbal incorrecto",
            GrammarErrorType.WRONG_MOOD: "Modo verbal incorrecto",
            GrammarErrorType.LEISMO: "Leísmo detectado",
            GrammarErrorType.LAISMO: "Laísmo: uso incorrecto de 'la' como CI",
            GrammarErrorType.LOISMO: "Loísmo: uso incorrecto de 'lo' como CI",
            GrammarErrorType.WORD_ORDER: "Orden de palabras inusual",
            GrammarErrorType.REDUNDANCY: "Expresión redundante",
            GrammarErrorType.RUN_ON_SENTENCE: "Oración excesivamente larga",
            GrammarErrorType.COMMA_SPLICE: "Coma donde debería ir punto o conjunción",
        }
        return explanations.get(self.error_type, "Error gramatical detectado")

    @property
    def is_high_confidence(self) -> bool:
        """True si la confianza es alta (>0.8)."""
        return self.confidence >= 0.8

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "sentence": self.sentence,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
            "detection_method": self.detection_method.value,
            "explanation": self.explanation,
            "rule_id": self.rule_id,
        }


@dataclass
class GrammarReport:
    """Resultado del análisis gramatical."""

    issues: list[GrammarIssue] = field(default_factory=list)
    processed_chars: int = 0
    processed_sentences: int = 0

    # Estadísticas
    by_type: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    by_method: dict[str, int] = field(default_factory=dict)

    def add_issue(self, issue: GrammarIssue) -> None:
        """Añadir un issue y actualizar estadísticas."""
        self.issues.append(issue)

        # Actualizar contadores
        type_key = issue.error_type.value
        self.by_type[type_key] = self.by_type.get(type_key, 0) + 1

        severity_key = issue.severity.value
        self.by_severity[severity_key] = self.by_severity.get(severity_key, 0) + 1

        method_key = issue.detection_method.value
        self.by_method[method_key] = self.by_method.get(method_key, 0) + 1

    def get_by_type(self, error_type: GrammarErrorType) -> list[GrammarIssue]:
        """Filtrar issues por tipo."""
        return [i for i in self.issues if i.error_type == error_type]

    def get_by_severity(self, severity: GrammarSeverity) -> list[GrammarIssue]:
        """Filtrar issues por severidad."""
        return [i for i in self.issues if i.severity == severity]

    def get_errors(self) -> list[GrammarIssue]:
        """Obtener solo errores (no warnings ni style)."""
        return self.get_by_severity(GrammarSeverity.ERROR)

    def get_high_confidence(self, threshold: float = 0.8) -> list[GrammarIssue]:
        """Filtrar issues con alta confianza."""
        return [i for i in self.issues if i.confidence >= threshold]

    @property
    def error_count(self) -> int:
        """Número total de errores."""
        return self.by_severity.get("error", 0)

    @property
    def warning_count(self) -> int:
        """Número total de warnings."""
        return self.by_severity.get("warning", 0)

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "issues": [i.to_dict() for i in self.issues],
            "processed_chars": self.processed_chars,
            "processed_sentences": self.processed_sentences,
            "by_type": self.by_type,
            "by_severity": self.by_severity,
            "by_method": self.by_method,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }


# =============================================================================
# Reglas gramaticales del español
# =============================================================================

# Verbos que rigen preposición específica
VERB_PREPOSITION_RULES = {
    # Verbos con "de"
    "acordarse": "de",
    "alegrarse": "de",
    "arrepentirse": "de",
    "avergonzarse": "de",
    "cansarse": "de",
    "darse cuenta": "de",
    "depender": "de",
    "despedirse": "de",
    "disfrutar": "de",
    "enamorarse": "de",
    "enterarse": "de",
    "estar seguro": "de",
    "fiarse": "de",
    "hablar": "de",  # hablar de algo
    "olvidarse": "de",
    "quejarse": "de",
    "tratarse": "de",

    # Verbos con "en"
    "confiar": "en",
    "consistir": "en",
    "creer": "en",
    "fijarse": "en",
    "insistir": "en",
    "pensar": "en",  # pensar en algo
    "tardar": "en",

    # Verbos con "a"
    "acostumbrarse": "a",
    "aprender": "a",
    "atreverse": "a",
    "ayudar": "a",
    "comenzar": "a",
    "contribuir": "a",
    "dedicarse": "a",
    "empezar": "a",
    "enseñar": "a",
    "invitar": "a",
    "ir": "a",
    "negarse": "a",
    "oponerse": "a",
    "renunciar": "a",
    "volver": "a",

    # Verbos con "con"
    "casarse": "con",
    "contar": "con",
    "encontrarse": "con",
    "enfadarse": "con",
    "soñar": "con",
    "tropezar": "con",

    # Verbos con "por"
    "interesarse": "por",
    "preguntar": "por",
    "preocuparse": "por",
    "votar": "por",
}

# Verbos que NO llevan preposición antes de "que" (dequeísmo)
VERBS_WITHOUT_DE_QUE = {
    "pensar", "creer", "opinar", "considerar", "suponer",
    "imaginar", "parecer", "resultar", "decir", "afirmar",
    "negar", "asegurar", "sostener", "manifestar", "expresar",
    "indicar", "señalar", "comunicar", "anunciar", "advertir",
    "ver", "notar", "observar", "percibir", "sentir",
}

# Verbos que SÍ llevan preposición antes de "que" (queísmo)
VERBS_WITH_DE_QUE = {
    "acordarse", "alegrarse", "arrepentirse", "avergonzarse",
    "convencerse", "darse cuenta", "enterarse", "olvidarse",
    "quejarse", "estar seguro", "estar convencido",
    "tener la certeza", "tener la seguridad",
}

# Redundancias basadas en lemas (verbo + adverbio innecesario)
# El lema del verbo se compara con spaCy, así cualquier conjugación funciona
LEMMA_REDUNDANCIES = {
    # (lema del verbo, adverbio redundante) -> sugerencia (usar lema)
    ("subir", "arriba"): "subir (sin 'arriba')",
    ("bajar", "abajo"): "bajar (sin 'abajo')",
    ("salir", "afuera"): "salir (sin 'afuera')",
    ("entrar", "adentro"): "entrar (sin 'adentro')",
}

# Expresiones redundantes que se buscan literalmente (para casos sin lematización)
REDUNDANT_EXPRESSIONS = {
    # Expresiones fijas
    "volver a repetir": "repetir",
    "lapso de tiempo": "lapso",
    "pero sin embargo": "pero / sin embargo",
    "más mejor": "mejor",
    "más peor": "peor",
    "más mayor": "mayor",
    "más menor": "menor",
    "muy mucho": "mucho",
    "muy poco": "poco",
    "el día de hoy": "hoy",
    "a la mayor brevedad posible": "lo antes posible",
    "completamente lleno": "lleno",
    "completamente vacío": "vacío",
    "falso pretexto": "pretexto",
    "protagonista principal": "protagonista",
    "prever de antemano": "prever",
    "persona humana": "persona",
    "hechos reales": "hechos",
}

# Patrones regex para errores gramaticales
GRAMMAR_PATTERNS = [
    # Dequeísmo
    (r'\b(pienso|creo|opino|considero|supongo|digo|afirmo)\s+de\s+que\b',
     GrammarErrorType.DEQUEISMO, "Dequeísmo: sobra 'de'"),

    # Queísmo
    (r'\b(me alegro|me arrepiento|me acuerdo|me olvido|estoy seguro)\s+que\b',
     GrammarErrorType.QUEISMO, "Queísmo: falta 'de'"),

    # Laísmo
    (r'\b(la|las)\s+(dije|digo|diré|dije|conté|cuento|contaré|pregunté|pregunto)\b',
     GrammarErrorType.LAISMO, "Laísmo: usar 'le/les' en lugar de 'la/las'"),

    # Loísmo
    (r'\b(lo|los)\s+(dije|digo|diré|conté|cuento|contaré|pregunté|pregunto)\s+(a\s+(él|ella|ellos|ellas))\b',
     GrammarErrorType.LOISMO, "Loísmo: usar 'le/les' en lugar de 'lo/los'"),

    # Concordancia artículo-sustantivo (casos obvios)
    (r'\bel\s+(casa|mesa|silla|ventana|puerta|cama|cocina|sala)\b',
     GrammarErrorType.GENDER_AGREEMENT, "Error de género: usar 'la'"),
    (r'\bla\s+(libro|coche|perro|gato|árbol|cielo|suelo|techo)\b',
     GrammarErrorType.GENDER_AGREEMENT, "Error de género: usar 'el'"),

    # Concordancia número
    (r'\b(el|la|un|una)\s+\w+s\b(?!\s+(que|de|en|con|para|por))',
     GrammarErrorType.NUMBER_AGREEMENT, "Posible error de número"),

    # Infinitivo incorrecto (*habemos)
    (r'\bhabemos\b',
     GrammarErrorType.INFINITIVE_ERROR, "Forma incorrecta: usar 'hay' o 'somos'"),

    # Gerundio de posterioridad
    (r'\b\w+ó\s+\w+ando\b',
     GrammarErrorType.GERUND_ERROR, "Posible gerundio de posterioridad"),

    # Oraciones muy largas (más de 60 palabras)
    # Se detecta por separado con lógica especial

    # Coma antes de "y" en enumeración de dos elementos
    (r'\b\w+,\s+y\s+\w+\b(?!\s*,)',
     GrammarErrorType.WRONG_PUNCTUATION, "Coma innecesaria antes de 'y'"),

    # Punto y coma mal usado
    (r';\s+[a-záéíóúñ]',
     GrammarErrorType.WRONG_PUNCTUATION, "Después de punto y coma se escribe minúscula"),
]

# Palabras que suelen confundirse gramaticalmente
CONFUSING_PAIRS = {
    ("haber", "a ver"): "Confusión haber/a ver",
    ("sino", "si no"): "Confusión sino/si no",
    ("porque", "por qué", "porqué", "por que"): "Confusión porque/por qué",
    ("a", "ha"): "Confusión a/ha (preposición vs verbo haber)",
    ("echo", "hecho"): "Confusión echo/hecho",
    ("ay", "hay", "ahí"): "Confusión ay/hay/ahí",
}
