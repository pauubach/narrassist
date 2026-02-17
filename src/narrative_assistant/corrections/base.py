"""
Clase base para detectores de correcciones.

Los detectores analizan el texto y generan CorrectionIssue que se
presentan al corrector como sugerencias. El corrector decide si
aplicar o ignorar cada sugerencia.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .types import CorrectionCategory


@dataclass
class CorrectionIssue:
    """
    Issue de corrección detectado.

    Representa un problema potencial encontrado en el texto que se
    presenta al corrector como sugerencia. NO se aplica automáticamente.

    INVARIANTES CRÍTICOS (Sistema de Coordenadas):

    1. start_char y end_char DEBEN ser posiciones ABSOLUTAS en el documento completo
       - Rango válido: [0, len(documento)]
       - Unidad: Unicode codepoints (NO bytes UTF-8, NO UTF-16 code units)
       - Sistema de coordenadas: Absoluto desde inicio del documento (char 0)
       - chapter_index es solo CONTEXTO, NO afecta interpretación de posiciones

    2. Relación con texto:
       - documento[start_char:end_char] DEBE extraer exactamente el texto del issue
       - Invariante validado en tests: extracted_text == issue.text

    3. Ordenación:
       - SIEMPRE: 0 <= start_char <= end_char <= len(documento)
       - Violación indica bug en detector que generó el issue

    Ejemplo concreto:
        Documento completo: "Cap 1 text\\nCap 2 text"  (20 chars)
        Capítulos:
          - Cap 1: chars [0, 11), start_char=0
          - Cap 2: chars [11, 20), start_char=11

        Issue en "Cap 2":
            start_char = 11  # Posición ABSOLUTA (NO relativa a capítulo 2)
            end_char = 16
            text = "Cap 2"
            chapter_index = 2  # Solo para contexto UI

        Validación:
            documento[11:16] == "Cap 2"  # ✓ Correcto
            documento[0:5] != "Cap 2"    # ✗ Incorrecto (posición relativa)

    Attributes:
        category: Categoría principal (typography, repetition, etc.)
        issue_type: Tipo específico del problema
        start_char: Posición ABSOLUTA inicial (Unicode codepoints, desde char 0 del documento)
        end_char: Posición ABSOLUTA final (Unicode codepoints, desde char 0 del documento)
        text: Texto problemático encontrado
        explanation: Explicación del problema para el corrector
        suggestion: Texto sugerido como corrección (opcional)
        confidence: Confianza de la detección (0.0-1.0)
        context: Contexto alrededor del problema
        chapter_index: Índice del capítulo (solo contexto, NO afecta posiciones)
        rule_id: ID de la regla que detectó el problema
        extra_data: Datos adicionales específicos del tipo
    """

    category: str
    issue_type: str
    start_char: int
    end_char: int
    text: str
    explanation: str
    suggestion: str | None = None
    confidence: float = 0.8
    context: str = ""
    chapter_index: int | None = None
    rule_id: str | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "category": self.category,
            "issue_type": self.issue_type,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "context": self.context,
            "chapter_index": self.chapter_index,
            "rule_id": self.rule_id,
            "extra_data": self.extra_data,
        }


def validate_issue_positions(
    issue: CorrectionIssue,
    doc_length: int,
    strict: bool = True
) -> bool:
    """
    Validar que posiciones de un issue sean coherentes con el invariante.

    Verifica que:
    1. start_char >= 0
    2. end_char <= doc_length
    3. start_char <= end_char

    Args:
        issue: Issue a validar
        doc_length: Longitud del documento completo (len(full_text))
        strict: Si True, lanza excepción. Si False, retorna bool + warning

    Returns:
        True si válido, False si inválido (solo si strict=False)

    Raises:
        ValueError: Si strict=True y posiciones inválidas

    Example:
        >>> doc = "Hello world"
        >>> issue = CorrectionIssue(..., start_char=0, end_char=5, ...)
        >>> validate_issue_positions(issue, len(doc), strict=True)
        True
    """
    import logging
    logger = logging.getLogger(__name__)

    errors = []

    if issue.start_char < 0:
        errors.append(f"start_char {issue.start_char} < 0")

    if issue.end_char > doc_length:
        errors.append(
            f"end_char {issue.end_char} > doc_length {doc_length}"
        )

    if issue.start_char > issue.end_char:
        errors.append(
            f"start_char {issue.start_char} > end_char {issue.end_char}"
        )

    if errors:
        msg = (
            f"Invalid issue positions in {issue.issue_type}: "
            f"{', '.join(errors)}"
        )
        if strict:
            raise ValueError(msg)
        logger.warning(msg)
        return False

    return True


class BaseDetector(ABC):
    """
    Clase base abstracta para detectores de correcciones.

    Los detectores analizan texto y generan una lista de CorrectionIssue
    que se presentan al corrector como sugerencias.

    Cada detector implementa:
    - detect(): Método principal que analiza el texto
    - category: Categoría de alertas que genera
    """

    @abstractmethod
    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
    ) -> list[CorrectionIssue]:
        """
        Detecta problemas en el texto.

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo (opcional)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        pass

    @property
    @abstractmethod
    def category(self) -> CorrectionCategory:
        """Categoría de correcciones que genera este detector."""
        pass

    @property
    def requires_spacy(self) -> bool:
        """Si el detector necesita análisis de spaCy."""
        return False

    @property
    def requires_llm(self) -> bool:
        """Si el detector necesita un LLM (Ollama)."""
        return False

    def _extract_context(self, text: str, start: int, end: int, window: int = 40) -> str:
        """
        Extrae contexto alrededor de una posición.

        Args:
            text: Texto completo
            start: Posición inicial del problema
            end: Posición final del problema
            window: Caracteres de contexto a cada lado

        Returns:
            Texto de contexto con el problema marcado
        """
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)

        # Ajustar a límites de palabra
        while ctx_start > 0 and text[ctx_start] not in " \n\t":
            ctx_start -= 1
        while ctx_end < len(text) and text[ctx_end] not in " \n\t":
            ctx_end += 1

        context = text[ctx_start:ctx_end].strip()

        # Añadir elipsis si hay más texto
        if ctx_start > 0:
            context = "..." + context
        if ctx_end < len(text):
            context = context + "..."

        return context
