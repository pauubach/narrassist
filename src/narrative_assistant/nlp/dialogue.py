"""
Detector de Diálogos para textos narrativos.

Detecta intervenciones de diálogo usando los distintos formatos del español:
- Raya (—): Formato tradicional español
- Comillas latinas («»): Formato europeo
- Comillas inglesas (""): Formato anglosajón
- Comillas tipográficas (""): Variante tipográfica

El detector prioriza los formatos más largos y elimina solapamientos,
manteniendo la intervención más completa en caso de conflicto.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.result import Result
from ..core.errors import NLPError, ErrorSeverity

logger = logging.getLogger(__name__)


class DialogueType(Enum):
    """Tipos de formato de diálogo detectados."""

    DASH = "dash"  # Raya española (—)
    GUILLEMETS = "guillemets"  # Comillas latinas («»)
    QUOTES = "quotes"  # Comillas inglesas ("")
    QUOTES_TYPOGRAPHIC = "quotes_typographic"  # Comillas tipográficas ("")


@dataclass
class DialogueSpan:
    """
    Intervención de diálogo extraída del texto.

    Attributes:
        text: Contenido del diálogo (sin marcadores)
        start_char: Posición de inicio en el texto original (incluye marcador)
        end_char: Posición de fin en el texto original (incluye marcador)
        dialogue_type: Tipo de formato detectado
        attribution_text: Texto de atribución ("dijo Juan") si existe
        speaker_hint: Pista sobre el hablante extraída de la atribución
        confidence: Confianza de la detección (0.0-1.0)
    """

    text: str
    start_char: int
    end_char: int
    dialogue_type: DialogueType
    attribution_text: Optional[str] = None
    speaker_hint: Optional[str] = None
    confidence: float = 0.9

    def __post_init__(self):
        """Extrae pista de hablante de la atribución si existe."""
        if self.attribution_text and self.speaker_hint is None:
            self.speaker_hint = _extract_speaker_hint(self.attribution_text)

    @property
    def full_text(self) -> str:
        """Texto completo incluyendo atribución."""
        if self.attribution_text:
            return f"{self.text} {self.attribution_text}"
        return self.text

    @property
    def char_count(self) -> int:
        """Longitud del diálogo en caracteres."""
        return len(self.text)

    def __hash__(self) -> int:
        return hash((self.text, self.start_char, self.end_char))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DialogueSpan):
            return False
        return (
            self.text == other.text
            and self.start_char == other.start_char
            and self.end_char == other.end_char
        )


@dataclass
class DialogueResult:
    """
    Resultado de la detección de diálogos.

    Attributes:
        dialogues: Lista de diálogos detectados
        processed_chars: Caracteres procesados
        by_type: Conteo por tipo de diálogo
    """

    dialogues: list[DialogueSpan] = field(default_factory=list)
    processed_chars: int = 0

    @property
    def by_type(self) -> dict[str, int]:
        """Retorna conteo de diálogos por tipo."""
        counts: dict[str, int] = {t.value: 0 for t in DialogueType}
        for d in self.dialogues:
            counts[d.dialogue_type.value] += 1
        return counts

    @property
    def total_dialogue_chars(self) -> int:
        """Total de caracteres en diálogos."""
        return sum(d.char_count for d in self.dialogues)

    @property
    def dialogue_ratio(self) -> float:
        """Ratio de texto que es diálogo (0.0-1.0)."""
        if self.processed_chars == 0:
            return 0.0
        return self.total_dialogue_chars / self.processed_chars

    def get_by_type(self, dtype: DialogueType) -> list[DialogueSpan]:
        """Retorna diálogos filtrados por tipo."""
        return [d for d in self.dialogues if d.dialogue_type == dtype]


@dataclass
class DialogueDetectionError(NLPError):
    """Error durante la detección de diálogos."""

    text_sample: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"Dialogue detection error: {self.original_error}"
        self.user_message = (
            "Error al detectar diálogos. "
            "Se continuará con los resultados parciales."
        )
        super().__post_init__()


# =============================================================================
# Patrones de detección
# =============================================================================

# Verbos de habla comunes en español para detectar atribuciones
SPEECH_VERBS = {
    "dijo",
    "decia",
    "decía",
    "pregunto",
    "preguntó",
    "respondio",
    "respondió",
    "exclamo",
    "exclamó",
    "grito",
    "gritó",
    "susurro",
    "susurró",
    "murmuro",
    "murmuró",
    "contesto",
    "contestó",
    "replico",
    "replicó",
    "añadio",
    "añadió",
    "continuo",
    "continuó",
    "interrumpio",
    "interrumpió",
    "protesto",
    "protestó",
    "insistio",
    "insistió",
    "explico",
    "explicó",
    "comento",
    "comentó",
    "observo",
    "observó",
    "confeso",
    "confesó",
    "admitio",
    "admitió",
    "nego",
    "negó",
    "afirmo",
    "afirmó",
    "aseguro",
    "aseguró",
    "penso",
    "pensó",
}

# Patrones de diálogo ordenados por especificidad (más específicos primero)
# Cada patrón es: (regex_compilado, tipo, num_grupos_atribucion)
DIALOGUE_PATTERNS: list[tuple[re.Pattern[str], DialogueType, int]] = [
    # Raya española con atribución: —¿Vienes?— preguntó Juan.
    # Soporta: "preguntó él", "dijo la mujer", "exclamó María García"
    # Captura: grupo 1 = diálogo, grupo 2 = atribución opcional
    (
        re.compile(
            r"—([^—\n]+?)—\s*"
            r"([a-záéíóúüñ]+\s+"  # Verbo de habla
            r"(?:"
            r"(?:el|la|los|las)\s+[a-záéíóúüñ]+"  # "la mujer", "el hombre"
            r"|él|ella|ellos|ellas"  # Pronombres
            r"|[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*)?"  # Nombre propio
            r")"
            r"[^.!?\n—]{0,100}[.!?]?)",  # Resto hasta puntuación (máx 100 chars, evita ReDoS)
            re.UNICODE,
        ),
        DialogueType.DASH,
        2,
    ),
    # Raya española simple: —Texto hasta fin de línea o punto
    (
        re.compile(r"—([^—\n]+[.!?])", re.UNICODE),
        DialogueType.DASH,
        0,
    ),
    # Raya española al inicio de línea (más permisivo)
    (
        re.compile(r"(?:^|\n)—([^\n—]+)", re.UNICODE | re.MULTILINE),
        DialogueType.DASH,
        0,
    ),
    # Comillas latinas: «Texto»
    (
        re.compile(r"«([^»]+)»", re.UNICODE),
        DialogueType.GUILLEMETS,
        0,
    ),
    # Comillas tipográficas: "Texto"
    (
        re.compile("\u201c([^\u201d]+)\u201d", re.UNICODE),
        DialogueType.QUOTES_TYPOGRAPHIC,
        0,
    ),
    # Comillas inglesas: "Texto"
    (
        re.compile(r'"([^"]+)"', re.UNICODE),
        DialogueType.QUOTES,
        0,
    ),
]

# Longitud mínima para considerar un diálogo válido
MIN_DIALOGUE_LENGTH = 2

# Caracteres de guión que se normalizan a raya (em-dash)
# - Guión-menos (U+002D): usado en teclados estándar
# - Guión corto/en-dash (U+2013): común en procesadores de texto
# - Doble guión (--): convención de máquinas de escribir
EN_DASH = "\u2013"  # –
EM_DASH = "\u2014"  # —

# Patrón para detectar guión-menos al inicio de línea (posible diálogo)
# Solo normaliza cuando parece inicio de diálogo, no guiones dentro de palabras
HYPHEN_DIALOGUE_PATTERN = re.compile(r"(^|\n)-(?=[^-\d])", re.MULTILINE)


def _normalize_dashes(text: str) -> str:
    """
    Normaliza diferentes tipos de guiones a raya española (em-dash).

    Convierte:
    - En-dash (–) → Em-dash (—)
    - Doble guión (--) → Em-dash (—)
    - Guión-menos (-) al inicio de línea → Em-dash (—)

    No modifica guiones dentro de palabras (ej: "veintiún") ni rangos numéricos.

    Args:
        text: Texto a normalizar

    Returns:
        Texto con guiones normalizados
    """
    if not text:
        return text

    result = text

    # Primero: doble guión → em-dash (antes de otros para evitar conflictos)
    result = result.replace("--", EM_DASH)

    # Segundo: en-dash → em-dash
    result = result.replace(EN_DASH, EM_DASH)

    # Tercero: guión-menos al inicio de línea → em-dash
    # Solo cuando parece inicio de diálogo (no seguido de otro guión o dígito)
    result = HYPHEN_DIALOGUE_PATTERN.sub(rf"\1{EM_DASH}", result)

    return result


def _extract_speaker_hint(attribution: str) -> Optional[str]:
    """
    Extrae una pista del hablante del texto de atribución.

    Args:
        attribution: Texto como "dijo Juan" o "preguntó la mujer"

    Returns:
        Nombre o descripción del hablante, o None
    """
    if not attribution:
        return None

    # Buscar patrón: verbo + nombre/descripción
    # Ej: "dijo Juan García", "preguntó la anciana", "exclamó él"
    pattern = re.compile(
        r"(?:dij[oa]|pregunt[oó]|respond[ií]|exclam[oó]|grit[oó]|susurr[oó]|"
        r"murmur[oó]|contest[oó]|replic[oó]|a[ñn]adi[oó]|continu[oó])\s+"
        r"((?:el|la|los|las)\s+)?([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*)?|"
        r"(?:el|la|los|las)\s+[a-záéíóúüñ]+|él|ella|ellos|ellas)",
        re.IGNORECASE | re.UNICODE,
    )

    match = pattern.search(attribution)
    if match:
        # Retornar el nombre/descripción encontrado
        article = match.group(1) or ""
        name = match.group(2)
        return (article + name).strip()

    return None


def detect_dialogues(text: str) -> Result[DialogueResult]:
    """
    Detecta intervenciones de diálogo en el texto.

    Soporta múltiples formatos de diálogo español:
    - Raya (—): Formato tradicional
    - Comillas latinas («»): Formato europeo
    - Comillas inglesas (""): Formato anglosajón
    - Comillas tipográficas (""): Variante moderna

    Normaliza automáticamente diferentes tipos de guiones:
    - En-dash (–) → Em-dash (—)
    - Doble guión (--) → Em-dash (—)
    - Guión-menos (-) al inicio de línea → Em-dash (—)

    Args:
        text: Texto a procesar

    Returns:
        Result con DialogueResult conteniendo los diálogos detectados
    """
    if not text or not text.strip():
        return Result.success(DialogueResult(processed_chars=0))

    # Normalizar guiones antes de procesar
    normalized_text = _normalize_dashes(text)

    result = DialogueResult(processed_chars=len(text))
    detected_spans: set[tuple[int, int]] = set()  # Para evitar duplicados exactos

    try:
        for pattern, dtype, attr_group in DIALOGUE_PATTERNS:
            for match in pattern.finditer(normalized_text):
                # Extraer texto del diálogo (siempre grupo 1)
                dialogue_text = match.group(1)

                # Validar longitud mínima
                if len(dialogue_text.strip()) < MIN_DIALOGUE_LENGTH:
                    continue

                # Extraer atribución si existe
                attribution = None
                if attr_group > 0 and match.lastindex and match.lastindex >= attr_group:
                    attribution = match.group(attr_group)

                # Evitar duplicados exactos por posición
                span_key = (match.start(), match.end())
                if span_key in detected_spans:
                    continue
                detected_spans.add(span_key)

                dialogue = DialogueSpan(
                    text=dialogue_text.strip(),
                    start_char=match.start(),
                    end_char=match.end(),
                    dialogue_type=dtype,
                    attribution_text=attribution.strip() if attribution else None,
                )
                result.dialogues.append(dialogue)

        # Ordenar por posición y eliminar solapamientos (preferir más largos)
        result.dialogues.sort(key=lambda d: d.start_char)
        result.dialogues = _remove_overlapping(result.dialogues)

        logger.debug(
            f"Diálogos detectados: {len(result.dialogues)} "
            f"({result.by_type}), ratio={result.dialogue_ratio:.1%}"
        )

        return Result.success(result)

    except Exception as e:
        error = DialogueDetectionError(
            text_sample=text[:100] if len(text) > 100 else text,  # Original text for context
            original_error=str(e),
        )
        logger.error(f"Error en detección de diálogos: {e}")
        return Result.partial(result, [error])


def _remove_overlapping(dialogues: list[DialogueSpan]) -> list[DialogueSpan]:
    """
    Elimina diálogos que se solapan, manteniendo el más largo.

    Args:
        dialogues: Lista de diálogos ordenados por start_char

    Returns:
        Lista filtrada sin solapamientos
    """
    if not dialogues:
        return []

    result: list[DialogueSpan] = []

    for dialogue in dialogues:
        if not result:
            result.append(dialogue)
            continue

        last = result[-1]

        # Si no hay solapamiento, añadir directamente
        if dialogue.start_char >= last.end_char:
            result.append(dialogue)
        # Si hay solapamiento, mantener el que cubre más span
        # (preferimos el match completo con atribución sobre el parcial)
        elif (dialogue.end_char - dialogue.start_char) > (last.end_char - last.start_char):
            result[-1] = dialogue

    return result


def get_dialogue_density(
    dialogues: list[DialogueSpan],
    chapter_start: int,
    chapter_end: int,
) -> float:
    """
    Calcula la densidad de diálogo en un rango de texto.

    Args:
        dialogues: Lista de diálogos
        chapter_start: Inicio del rango
        chapter_end: Fin del rango

    Returns:
        Ratio de caracteres de diálogo vs total (0.0-1.0)
    """
    if chapter_end <= chapter_start:
        return 0.0

    dialogue_chars = sum(
        d.char_count
        for d in dialogues
        if d.start_char >= chapter_start and d.end_char <= chapter_end
    )

    total_chars = chapter_end - chapter_start
    return dialogue_chars / total_chars if total_chars > 0 else 0.0
