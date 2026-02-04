"""
Sistema unificado de coordenadas de texto.

Este módulo resuelve el problema de desalineación de posiciones entre:
1. DocxParser que calcula start_char/end_char al leer párrafos
2. RawDocument.full_text que reconstruye el texto filtrando vacíos
3. Pipeline NLP que tokeniza sobre full_text

La solución es calcular las posiciones DESPUÉS de construir el texto final,
garantizando que las posiciones siempre correspondan al texto que se usa.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextSpan:
    """
    Representa un span de texto con sus coordenadas.

    Attributes:
        start: Posición de inicio en full_text
        end: Posición de fin en full_text
        paragraph_index: Índice del párrafo original (incluyendo vacíos)
        text: Texto del span
    """

    start: int
    end: int
    paragraph_index: int
    text: str

    @property
    def length(self) -> int:
        return self.end - self.start


class TextCoordinateSystem:
    """
    Sistema unificado de coordenadas de texto.

    Construye el texto completo y mantiene un mapeo bidireccional entre:
    - Posiciones en el texto completo (full_text)
    - Índices y offsets dentro de párrafos originales

    El separador entre párrafos es siempre "\\n\\n" (2 caracteres).

    Example:
        >>> paragraphs = [Paragraph("Hola", ...), Paragraph("Mundo", ...)]
        >>> coords = TextCoordinateSystem(paragraphs)
        >>> coords.full_text
        'Hola\\n\\nMundo'
        >>> coords.get_paragraph_span(0)
        TextSpan(start=0, end=4, ...)
        >>> coords.text_offset_to_paragraph(6)
        (1, 0)  # Párrafo 1, offset 0
    """

    SEPARATOR = "\n\n"
    SEPARATOR_LEN = 2

    def __init__(self, paragraphs: list, filter_empty: bool = True):
        """
        Inicializa el sistema de coordenadas.

        Args:
            paragraphs: Lista de objetos con atributo .text y .is_empty
            filter_empty: Si True, excluye párrafos vacíos del texto final
        """
        self._original_paragraphs = paragraphs
        self._filter_empty = filter_empty

        # Mapeos construidos en _build()
        self._full_text: str = ""
        self._paragraph_spans: list[TextSpan] = []
        # Mapeo de índice original → índice en _paragraph_spans (-1 si filtrado)
        self._original_to_filtered: dict[int, int] = {}
        # Mapeo inverso: índice filtrado → índice original
        self._filtered_to_original: list[int] = []

        self._build()

    def _build(self) -> None:
        """Construye el texto completo y los mapeos de posiciones."""
        offset = 0
        parts: list[str] = []
        filtered_idx = 0

        for orig_idx, para in enumerate(self._original_paragraphs):
            # Verificar si filtrar
            is_empty = (
                getattr(para, "is_empty", not para.text.strip()) if hasattr(para, "text") else True
            )

            if self._filter_empty and is_empty:
                self._original_to_filtered[orig_idx] = -1
                continue

            # Obtener texto
            text = para.text if hasattr(para, "text") else str(para)

            # Crear span
            span = TextSpan(
                start=offset, end=offset + len(text), paragraph_index=orig_idx, text=text
            )
            self._paragraph_spans.append(span)

            # Mapeos
            self._original_to_filtered[orig_idx] = filtered_idx
            self._filtered_to_original.append(orig_idx)

            parts.append(text)
            offset += len(text) + self.SEPARATOR_LEN
            filtered_idx += 1

        self._full_text = self.SEPARATOR.join(parts)

        logger.debug(
            f"TextCoordinateSystem construido: {len(self._original_paragraphs)} párrafos originales, "
            f"{len(self._paragraph_spans)} después de filtrar, {len(self._full_text)} caracteres"
        )

    @property
    def full_text(self) -> str:
        """Texto completo con párrafos unidos por \\n\\n."""
        return self._full_text

    @property
    def paragraph_count(self) -> int:
        """Número de párrafos (después de filtrar vacíos si aplica)."""
        return len(self._paragraph_spans)

    @property
    def original_paragraph_count(self) -> int:
        """Número total de párrafos originales (incluyendo vacíos)."""
        return len(self._original_paragraphs)

    def get_paragraph_span(self, filtered_index: int) -> TextSpan | None:
        """
        Obtiene el span de un párrafo por su índice filtrado.

        Args:
            filtered_index: Índice del párrafo (0-based, excluyendo vacíos)

        Returns:
            TextSpan o None si el índice está fuera de rango
        """
        if 0 <= filtered_index < len(self._paragraph_spans):
            return self._paragraph_spans[filtered_index]
        return None

    def get_paragraph_span_by_original_index(self, original_index: int) -> TextSpan | None:
        """
        Obtiene el span de un párrafo por su índice original.

        Args:
            original_index: Índice del párrafo en el documento original

        Returns:
            TextSpan o None si el párrafo fue filtrado o no existe
        """
        filtered_idx = self._original_to_filtered.get(original_index, -1)
        if filtered_idx >= 0:
            return self._paragraph_spans[filtered_idx]
        return None

    def text_offset_to_paragraph(self, text_offset: int) -> tuple[int, int]:
        """
        Convierte un offset en full_text a (índice_párrafo_original, offset_dentro).

        Args:
            text_offset: Posición en full_text

        Returns:
            Tupla (índice_párrafo_original, offset_dentro_del_párrafo)

        Raises:
            ValueError: Si el offset está fuera de rango o en un separador
        """
        if text_offset < 0:
            raise ValueError(f"Offset negativo: {text_offset}")

        if text_offset > len(self._full_text):
            raise ValueError(f"Offset {text_offset} fuera de rango [0, {len(self._full_text)}]")

        # Caso especial: offset exactamente al final
        if text_offset == len(self._full_text):
            if self._paragraph_spans:
                last_span = self._paragraph_spans[-1]
                return last_span.paragraph_index, len(last_span.text)
            raise ValueError("Documento vacío")

        # Buscar el párrafo que contiene este offset
        for span in self._paragraph_spans:
            if span.start <= text_offset < span.end:
                return span.paragraph_index, text_offset - span.start

            # Si está en el separador después de este párrafo, atribuir al final del párrafo
            separator_start = span.end
            separator_end = span.end + self.SEPARATOR_LEN
            if separator_start <= text_offset < separator_end:
                # Está en el separador - atribuir al final del párrafo anterior
                return span.paragraph_index, len(span.text)

        raise ValueError(f"Offset {text_offset} no encontrado en ningún párrafo")

    def paragraph_offset_to_text(self, original_para_index: int, para_offset: int) -> int:
        """
        Convierte un offset dentro de un párrafo a offset en full_text.

        Args:
            original_para_index: Índice del párrafo en el documento original
            para_offset: Offset dentro del párrafo

        Returns:
            Offset en full_text

        Raises:
            ValueError: Si el párrafo fue filtrado o el offset está fuera de rango
        """
        span = self.get_paragraph_span_by_original_index(original_para_index)
        if span is None:
            raise ValueError(f"Párrafo {original_para_index} fue filtrado o no existe")

        if para_offset < 0 or para_offset > len(span.text):
            raise ValueError(
                f"Offset {para_offset} fuera de rango para párrafo {original_para_index} "
                f"(longitud: {len(span.text)})"
            )

        return span.start + para_offset

    def find_text_in_paragraph(
        self, original_para_index: int, search_text: str, start_offset: int = 0
    ) -> tuple[int, int] | None:
        """
        Busca texto dentro de un párrafo y retorna posiciones en full_text.

        Args:
            original_para_index: Índice del párrafo original
            search_text: Texto a buscar
            start_offset: Offset inicial dentro del párrafo

        Returns:
            Tupla (start_in_full_text, end_in_full_text) o None si no encontrado
        """
        span = self.get_paragraph_span_by_original_index(original_para_index)
        if span is None:
            return None

        # Buscar dentro del texto del párrafo
        pos = span.text.find(search_text, start_offset)
        if pos == -1:
            return None

        start_in_text = span.start + pos
        end_in_text = start_in_text + len(search_text)

        return start_in_text, end_in_text

    def get_text_at_offset(self, start: int, end: int) -> str:
        """
        Obtiene el texto entre dos offsets en full_text.

        Args:
            start: Offset de inicio
            end: Offset de fin

        Returns:
            Subcadena de full_text
        """
        return self._full_text[start:end]

    def validate_span(self, start: int, end: int) -> bool:
        """
        Valida que un span está dentro de los límites y no cruza separadores de forma incorrecta.

        Args:
            start: Offset de inicio
            end: Offset de fin

        Returns:
            True si el span es válido
        """
        if start < 0 or end > len(self._full_text) or start > end:
            return False

        # Verificar que el texto extraído coincide con lo esperado
        # (no empieza ni termina en medio de un separador)
        try:
            self.text_offset_to_paragraph(start)
            if end < len(self._full_text):
                self.text_offset_to_paragraph(end)
            return True
        except ValueError:
            return False

    def recalculate_paragraph_positions(self, paragraphs: list) -> list:
        """
        Recalcula las posiciones start_char/end_char de una lista de párrafos
        para que coincidan con full_text.

        Args:
            paragraphs: Lista de objetos RawParagraph o similar con atributos
                       start_char, end_char modificables

        Returns:
            La misma lista con posiciones actualizadas

        Note:
            Modifica los objetos in-place además de retornarlos.
        """
        for orig_idx, para in enumerate(paragraphs):
            span = self.get_paragraph_span_by_original_index(orig_idx)
            if span is not None:
                para.start_char = span.start
                para.end_char = span.end
            else:
                # Párrafo filtrado - marcar como inválido
                para.start_char = -1
                para.end_char = -1

        return paragraphs


def build_coordinate_system(paragraphs: list, filter_empty: bool = True) -> TextCoordinateSystem:
    """
    Función de conveniencia para crear un TextCoordinateSystem.

    Args:
        paragraphs: Lista de párrafos
        filter_empty: Si filtrar párrafos vacíos

    Returns:
        TextCoordinateSystem configurado
    """
    return TextCoordinateSystem(paragraphs, filter_empty)
