"""
Tipos base para el módulo de corrección ortográfica.
"""

from dataclasses import dataclass, field
from enum import Enum


class SpellingErrorType(Enum):
    """Tipos de errores ortográficos detectados."""

    TYPO = "typo"  # Error tipográfico (tecla adyacente)
    MISSPELLING = "misspelling"  # Palabra mal escrita
    ACCENT = "accent"  # Falta o sobra tilde (María/Maria)
    CASE = "case"  # Mayúscula/minúscula incorrecta
    HOMOPHONE = "homophone"  # Confusión de homófonos (haber/a ver)
    SPLIT_WORD = "split_word"  # Palabra dividida incorrectamente
    JOINED_WORD = "joined_word"  # Palabras unidas incorrectamente
    REPEATED_CHAR = "repeated_char"  # Caracteres repetidos (holaaa)
    FOREIGN_WORD = "foreign_word"  # Palabra extranjera sin marcar
    OCR_ERROR = "ocr_error"  # Error típico de OCR (rn→m, l→1)
    REDUNDANCY = "redundancy"  # Redundancias (subir arriba, etc...)
    REPETITION = "repetition"  # Repetición de palabras (casa casa)
    SEMANTIC = "semantic"  # Error semántico (riegos de seguridad)
    DEQUEISMO = "dequeismo"  # "pienso de que" (de que innecesario)
    QUEISMO = "queismo"  # "me acuerdo que" (falta de)
    STYLE = "style"  # Sugerencia de estilo (no error estricto)


class SpellingSeverity(Enum):
    """Severidad del error ortográfico."""

    ERROR = "error"  # Error claro que debe corregirse
    WARNING = "warning"  # Posible error, requiere revisión
    INFO = "info"  # Sugerencia de mejora


class DetectionMethod(Enum):
    """Método que detectó el error."""

    DICTIONARY = "dictionary"  # Diccionario (hunspell/aspell)
    LEVENSHTEIN = "levenshtein"  # Distancia de edición
    REGEX = "regex"  # Patrón regex
    LLM = "llm"  # LLM local (Ollama)
    CONTEXT = "context"  # Análisis de contexto


@dataclass
class SpellingIssue:
    """Un error ortográfico detectado."""

    # Texto original y posición
    word: str  # Palabra con error
    start_char: int  # Posición inicio en texto
    end_char: int  # Posición fin en texto
    sentence: str  # Oración donde aparece

    # Clasificación
    error_type: SpellingErrorType
    severity: SpellingSeverity = SpellingSeverity.WARNING

    # Corrección
    suggestions: list[str] = field(default_factory=list)
    best_suggestion: str | None = None

    # Metadata
    confidence: float = 0.5  # 0.0-1.0
    detection_method: DetectionMethod = DetectionMethod.DICTIONARY
    explanation: str = ""  # Explicación para el usuario

    # Capítulo (asignado tras mapeo de posición global → capítulo)
    chapter: int | None = None

    # Para deduplicación
    context_hash: str = ""  # Hash del contexto para agrupar

    def __post_init__(self):
        """Validar y normalizar."""
        self.confidence = max(0.0, min(1.0, self.confidence))
        if self.suggestions and not self.best_suggestion:
            self.best_suggestion = self.suggestions[0]
        if not self.context_hash:
            self.context_hash = f"{self.start_char}:{self.end_char}:{self.word}"

    @property
    def is_high_confidence(self) -> bool:
        """True si la confianza es alta (>0.8)."""
        return self.confidence >= 0.8

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "word": self.word,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "sentence": self.sentence,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "suggestions": self.suggestions,
            "best_suggestion": self.best_suggestion,
            "confidence": self.confidence,
            "detection_method": self.detection_method.value,
            "explanation": self.explanation,
            "chapter": self.chapter,
        }


@dataclass
class SpellingReport:
    """Resultado del análisis ortográfico."""

    issues: list[SpellingIssue] = field(default_factory=list)
    processed_chars: int = 0
    processed_words: int = 0

    # Estadísticas por tipo
    by_type: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    by_method: dict[str, int] = field(default_factory=dict)

    # Palabras ignoradas (nombres propios, términos técnicos)
    ignored_words: set[str] = field(default_factory=set)

    def add_issue(self, issue: SpellingIssue) -> None:
        """Añadir un issue y actualizar estadísticas."""
        self.issues.append(issue)

        # Actualizar contadores
        type_key = issue.error_type.value
        self.by_type[type_key] = self.by_type.get(type_key, 0) + 1

        severity_key = issue.severity.value
        self.by_severity[severity_key] = self.by_severity.get(severity_key, 0) + 1

        method_key = issue.detection_method.value
        self.by_method[method_key] = self.by_method.get(method_key, 0) + 1

    def get_by_type(self, error_type: SpellingErrorType) -> list[SpellingIssue]:
        """Filtrar issues por tipo."""
        return [i for i in self.issues if i.error_type == error_type]

    def get_by_severity(self, severity: SpellingSeverity) -> list[SpellingIssue]:
        """Filtrar issues por severidad."""
        return [i for i in self.issues if i.severity == severity]

    def get_errors(self) -> list[SpellingIssue]:
        """Obtener solo errores (no warnings ni info)."""
        return self.get_by_severity(SpellingSeverity.ERROR)

    def get_high_confidence(self, threshold: float = 0.8) -> list[SpellingIssue]:
        """Filtrar issues con alta confianza."""
        return [i for i in self.issues if i.confidence >= threshold]

    @property
    def unique_issues(self) -> dict[str, SpellingIssue]:
        """Issues deduplicados por posición."""
        unique: dict[str, SpellingIssue] = {}
        for issue in self.issues:
            key = issue.context_hash
            if key not in unique or issue.confidence > unique[key].confidence:
                unique[key] = issue
        return unique

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
            "processed_words": self.processed_words,
            "by_type": self.by_type,
            "by_severity": self.by_severity,
            "by_method": self.by_method,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }


# =============================================================================
# Patrones comunes de errores en español
# =============================================================================

# Errores de tildes más comunes
COMMON_ACCENT_ERRORS: dict[str, str] = {
    "mas": "más",  # conjunción vs adverbio
    "si": "sí",  # condicional vs afirmación
    "el": "él",  # artículo vs pronombre
    "tu": "tú",  # posesivo vs pronombre
    "mi": "mí",  # posesivo vs pronombre
    "se": "sé",  # pronombre vs verbo
    "de": "dé",  # preposición vs verbo
    "te": "té",  # pronombre vs sustantivo
    "solo": "sólo",  # adjetivo vs adverbio (según contexto)
    "aun": "aún",  # conjunción vs adverbio
    "donde": "dónde",  # relativo vs interrogativo
    "como": "cómo",  # relativo vs interrogativo
    "cuando": "cuándo",  # relativo vs interrogativo
    "que": "qué",  # relativo vs interrogativo
    "quien": "quién",  # relativo vs interrogativo
    "cual": "cuál",  # relativo vs interrogativo
    "cuanto": "cuánto",  # relativo vs interrogativo
}

# Confusiones de homófonos
COMMON_HOMOPHONES: dict[str, list[str]] = {
    "haber": ["a ver"],
    "a ver": ["haber"],
    "hay": ["ahí", "ay"],
    "ahí": ["hay", "ay"],
    "ay": ["hay", "ahí"],
    "a": ["ha"],  # preposición vs verbo haber (ej: "a estado" → "ha estado")
    "ha": ["a"],  # verbo haber vs preposición
    "halla": ["haya", "aya"],
    "haya": ["halla", "aya"],
    "echo": ["hecho"],
    "hecho": ["echo"],
    "baca": ["vaca"],
    "vaca": ["baca"],
    "bello": ["vello"],
    "vello": ["bello"],
    "callo": ["cayo"],
    "cayo": ["callo"],
    "Asia": ["hacia"],
    "hacia": ["Asia"],
    "asta": ["hasta"],
    "hasta": ["asta"],
    "ola": ["hola"],
    "hola": ["ola"],
    "hora": ["ora"],
    "ora": ["hora"],
    "uso": ["huso"],
    "huso": ["uso"],
}

# Errores típicos de OCR
OCR_CONFUSIONS: dict[str, str] = {
    "rn": "m",  # "carne" -> "came"
    "cl": "d",  # "clave" -> "dave"
    "vv": "w",
    "li": "h",
    "ll": "ll",  # a veces se confunde
    "1": "l",
    "0": "o",
    "O": "0",
    "l": "1",
}

# Palabras que suelen confundirse
COMMONLY_CONFUSED: dict[str, list[str]] = {
    "sino": ["si no"],
    "si no": ["sino"],
    "porque": ["por que", "por qué", "porqué"],
    "por que": ["porque", "por qué", "porqué"],
    "por qué": ["porque", "por que", "porqué"],
    "porqué": ["porque", "por que", "por qué"],
    "conque": ["con que", "con qué"],
    "con que": ["conque", "con qué"],
    "adonde": ["a donde"],
    "a donde": ["adonde"],
    "también": ["tan bien"],
    "tan bien": ["también"],
    "tampoco": ["tan poco"],
    "tan poco": ["tampoco"],
    "sobretodo": ["sobre todo"],
    "sobre todo": ["sobretodo"],
    "entorno": ["en torno"],
    "en torno": ["entorno"],
    "aparte": ["a parte"],
    "a parte": ["aparte"],
    "acerca": ["a cerca"],
    "demás": ["de más"],
    "de más": ["demás"],
    "asimismo": ["así mismo"],
    "así mismo": ["asimismo"],
}
