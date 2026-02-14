"""
Chunking de documentos grandes para procesamiento NLP eficiente.

Estrategias:
- Por párrafos (respeta estructura)
- Por oraciones (para análisis detallado)
- Por tamaño fijo (para embedding batch)
- Sliding window (para contexto solapado)
"""

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """
    Fragmento de texto con metadatos de posición.

    Attributes:
        text: Contenido del chunk
        start_char: Posición de inicio en documento original
        end_char: Posición de fin en documento original
        chunk_index: Índice del chunk (0-based)
        total_chunks: Total de chunks (si conocido)
        metadata: Metadatos adicionales (ej: paragraph_index)
    """

    text: str
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int | None = None
    metadata: dict = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def char_count(self) -> int:
        """Número de caracteres en el chunk."""
        return len(self.text)

    @property
    def word_count(self) -> int:
        """Número aproximado de palabras."""
        return len(self.text.split())


class TextChunker:
    """
    Divide texto en chunks para procesamiento eficiente.

    Uso:
        chunker = TextChunker(chunk_size=1000, overlap=100)
        for chunk in chunker.chunk_text(text):
            process(chunk)
    """

    # Tamaños por defecto
    DEFAULT_CHUNK_SIZE = 1000  # caracteres
    DEFAULT_OVERLAP = 100  # caracteres de solapamiento
    DEFAULT_MIN_CHUNK_SIZE = 50  # mínimo para no crear chunks muy pequeños

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
        respect_sentences: bool = True,
    ):
        """
        Args:
            chunk_size: Tamaño objetivo de cada chunk (caracteres)
            overlap: Solapamiento entre chunks consecutivos
            min_chunk_size: Tamaño mínimo de un chunk
            respect_sentences: Intentar no cortar oraciones
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.respect_sentences = respect_sentences

        # Patrón para detectar fin de oración
        self._sentence_end = re.compile(r'[.!?]["\')\]]?\s+')

    def chunk_text(self, text: str) -> Iterator[TextChunk]:
        """
        Divide texto en chunks con solapamiento.

        Args:
            text: Texto completo a dividir

        Yields:
            TextChunk para cada fragmento
        """
        if not text or len(text) <= self.chunk_size:
            # Documento pequeño, un solo chunk
            yield TextChunk(
                text=text,
                start_char=0,
                end_char=len(text),
                chunk_index=0,
                total_chunks=1,
            )
            return

        text_length = len(text)
        chunks = []
        start = 0
        chunk_index = 0

        while start < text_length:
            # Calcular fin tentativo
            end = min(start + self.chunk_size, text_length)

            # Si no es el final del texto, buscar mejor punto de corte
            if end < text_length and self.respect_sentences:
                end = self._find_sentence_boundary(text, start, end)

            chunk_text = text[start:end]

            # Solo añadir si tiene contenido significativo
            if chunk_text.strip() and len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        start_char=start,
                        end_char=end,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1

            # Siguiente chunk con overlap
            start = end - self.overlap
            if start >= text_length:
                break

        # Actualizar total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
            yield chunk

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """
        Busca el mejor punto de corte cercano a end que sea fin de oración.

        Args:
            text: Texto completo
            start: Inicio del chunk actual
            end: Fin tentativo

        Returns:
            Posición ajustada de fin
        """
        # Buscar fin de oración en la región cercana al final
        search_start = max(start + self.min_chunk_size, end - 200)
        search_region = text[search_start : end + 100]

        # Buscar el último fin de oración antes del límite
        last_boundary = -1
        for match in self._sentence_end.finditer(search_region):
            boundary_pos = search_start + match.end()
            if boundary_pos <= end + 50:  # Permitir un poco más allá del límite
                last_boundary = boundary_pos

        if last_boundary > start + self.min_chunk_size:
            return last_boundary

        # No encontrado, usar fin original
        return end

    def chunk_by_paragraphs(
        self,
        paragraphs: list,
        max_chars_per_chunk: int = 2000,
    ) -> Iterator[TextChunk]:
        """
        Agrupa párrafos en chunks respetando estructura.

        Args:
            paragraphs: Lista de objetos con atributo .text
            max_chars_per_chunk: Máximo de caracteres por chunk

        Yields:
            TextChunk agrupando párrafos
        """
        if not paragraphs:
            return

        current_texts = []  # type: ignore[var-annotated]
        current_chars = 0
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para_text = para.text if hasattr(para, "text") else str(para)
            para_len = len(para_text)

            # Si añadir este párrafo excede el límite, flush
            if current_chars + para_len > max_chars_per_chunk and current_texts:
                chunk_text = "\n\n".join(current_texts)
                yield TextChunk(
                    text=chunk_text,
                    start_char=current_start,
                    end_char=current_start + len(chunk_text),
                    chunk_index=chunk_index,
                    metadata={"paragraph_count": len(current_texts)},
                )
                chunk_index += 1
                current_texts = []
                current_chars = 0
                current_start += len(chunk_text) + 2

            current_texts.append(para_text)
            current_chars += para_len

        # Último chunk
        if current_texts:
            chunk_text = "\n\n".join(current_texts)
            yield TextChunk(
                text=chunk_text,
                start_char=current_start,
                end_char=current_start + len(chunk_text),
                chunk_index=chunk_index,
                metadata={"paragraph_count": len(current_texts)},
            )


def chunk_for_embeddings(
    text: str,
    max_tokens: int = 256,
    overlap_tokens: int = 32,
) -> Iterator[TextChunk]:
    """
    Divide texto para procesamiento de embeddings.

    Los modelos de embeddings tienen límite de tokens.
    Asumimos ~4 caracteres por token (aproximación para español).

    Args:
        text: Texto a dividir
        max_tokens: Máximo de tokens por chunk
        overlap_tokens: Tokens de solapamiento

    Yields:
        TextChunk optimizados para embedding
    """
    # Aproximación: 4 chars = 1 token
    char_size = max_tokens * 4
    char_overlap = overlap_tokens * 4

    chunker = TextChunker(
        chunk_size=char_size,
        overlap=char_overlap,
        respect_sentences=True,
    )

    yield from chunker.chunk_text(text)


def chunk_for_spacy(
    text: str,
    max_chars: int = 100000,
) -> Iterator[TextChunk]:
    """
    Divide texto para procesamiento con spaCy.

    spaCy tiene límite por defecto de 1M caracteres.
    Para mejor rendimiento, procesamos en chunks más pequeños.

    Args:
        text: Texto a dividir
        max_chars: Máximo de caracteres por chunk (default 100k)

    Yields:
        TextChunk para procesamiento spaCy
    """
    chunker = TextChunker(
        chunk_size=max_chars,
        overlap=500,  # Solapamiento para continuidad de entidades
        respect_sentences=True,
    )

    yield from chunker.chunk_text(text)
