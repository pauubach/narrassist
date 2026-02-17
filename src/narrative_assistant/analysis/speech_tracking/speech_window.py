"""
SpeechWindow - Ventana temporal de diálogos de un personaje.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SpeechWindow:
    """
    Ventana temporal de diálogos de un personaje.

    Representa todos los diálogos de un personaje en un rango de capítulos,
    usado para calcular métricas de habla y detectar cambios temporales.
    """

    character_id: int
    character_name: str
    start_chapter: int
    end_chapter: int
    dialogues: list[str]
    total_words: int
    dialogue_count: int

    @property
    def chapter_range(self) -> str:
        """Rango de capítulos en formato legible."""
        if self.start_chapter == self.end_chapter:
            return str(self.start_chapter)
        return f"{self.start_chapter}-{self.end_chapter}"

    @property
    def avg_words_per_dialogue(self) -> float:
        """Promedio de palabras por diálogo."""
        if self.dialogue_count == 0:
            return 0.0
        return self.total_words / self.dialogue_count

    @classmethod
    def from_chapters(
        cls,
        character_id: int,
        character_name: str,
        chapters: list,  # List[Chapter]
        start_chapter_idx: int,
        end_chapter_idx: int,
    ) -> Optional["SpeechWindow"]:
        """
        Extrae diálogos del personaje en un rango de capítulos.

        Args:
            character_id: ID del personaje
            character_name: Nombre del personaje
            chapters: Lista de capítulos del manuscrito
            start_chapter_idx: Índice del capítulo inicial (0-indexed)
            end_chapter_idx: Índice del capítulo final (0-indexed, inclusive)

        Returns:
            SpeechWindow con diálogos extraídos, o None si no hay diálogos
        """
        dialogues = []
        total_words = 0

        # Extraer diálogos del rango de capítulos
        for i in range(start_chapter_idx, end_chapter_idx + 1):
            if i >= len(chapters):
                break

            chapter = chapters[i]
            chapter_dialogues = cls._extract_character_dialogues(
                chapter, character_id, character_name
            )

            for dialogue in chapter_dialogues:
                dialogues.append(dialogue)
                total_words += len(dialogue.split())

        if not dialogues:
            logger.debug(
                f"No dialogues found for character {character_name} "
                f"in chapters {start_chapter_idx}-{end_chapter_idx}"
            )
            return None

        # Capítulos en formato 1-indexed para UI
        return cls(
            character_id=character_id,
            character_name=character_name,
            start_chapter=start_chapter_idx + 1,
            end_chapter=end_chapter_idx + 1,
            dialogues=dialogues,
            total_words=total_words,
            dialogue_count=len(dialogues),
        )

    @staticmethod
    def _extract_character_dialogues(
        chapter, character_id: int, character_name: str
    ) -> list[str]:
        """
        Extrae diálogos del personaje de un capítulo.

        Heurísticas de extracción:
        1. Buscar mentions del personaje en contexto de diálogo
        2. Usar patrones de raya de diálogo (—)
        3. Verificar proximidad entre nombre y diálogo (<100 chars)

        Returns:
            Lista de diálogos (texto limpio sin rayas)
        """
        dialogues = []

        # Si el chapter tiene información estructurada de diálogos
        if hasattr(chapter, "dialogues") and chapter.dialogues:
            for dialogue_info in chapter.dialogues:
                # Verificar si pertenece al personaje
                if (
                    hasattr(dialogue_info, "character_id")
                    and dialogue_info.character_id == character_id
                ):
                    dialogues.append(dialogue_info.text)
                elif (
                    hasattr(dialogue_info, "speaker")
                    and character_name.lower() in dialogue_info.speaker.lower()
                ):
                    dialogues.append(dialogue_info.text)

        # Fallback: Extracción básica basada en menciones
        if not dialogues and hasattr(chapter, "text"):
            dialogues = SpeechWindow._extract_dialogues_by_proximity(
                chapter.text, character_name
            )

        return dialogues

    @staticmethod
    def _extract_dialogues_by_proximity(text: str, character_name: str) -> list[str]:
        """
        Extrae diálogos por proximidad al nombre del personaje.

        Heurística simple:
        1. Buscar menciones del nombre
        2. Buscar diálogos (— ... —) en ventana de ±200 caracteres
        3. Atribuir diálogo al personaje si está cerca
        """
        import re

        dialogues = []

        # Patrón de diálogo con raya (español)
        dialogue_pattern = r"—([^—]+)—"

        # Buscar todas las menciones del personaje
        name_variants = [
            character_name,
            character_name.split()[0],  # Primer nombre
        ]

        for variant in name_variants:
            # Buscar menciones
            for match in re.finditer(
                re.escape(variant), text, flags=re.IGNORECASE
            ):
                mention_pos = match.start()

                # Buscar diálogos en ventana de ±200 caracteres
                window_start = max(0, mention_pos - 200)
                window_end = min(len(text), mention_pos + 200)
                window_text = text[window_start:window_end]

                # Extraer diálogos en la ventana
                for dialogue_match in re.finditer(dialogue_pattern, window_text):
                    dialogue_text = dialogue_match.group(1).strip()
                    if dialogue_text and len(dialogue_text) > 5:  # Mínimo 5 chars
                        dialogues.append(dialogue_text)

        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_dialogues = []
        for d in dialogues:
            if d not in seen:
                seen.add(d)
                unique_dialogues.append(d)

        return unique_dialogues


def create_sliding_windows(
    character_id: int,
    character_name: str,
    chapters: list,
    window_size: int = 3,
    overlap: int = 1,
    min_words_per_window: int = 200,
) -> list[SpeechWindow]:
    """
    Crea ventanas deslizantes de diálogos de un personaje.

    Args:
        character_id: ID del personaje
        character_name: Nombre del personaje
        chapters: Lista de capítulos del manuscrito
        window_size: Tamaño de ventana en capítulos (default: 3)
        overlap: Solapamiento entre ventanas en capítulos (default: 1)
        min_words_per_window: Palabras mínimas para ventana válida (default: 200)

    Returns:
        Lista de SpeechWindow válidas (con suficientes palabras)

    Example:
        chapters = [Ch1, Ch2, Ch3, Ch4, Ch5, Ch6]
        window_size = 3, overlap = 1
        → Windows: [1-3], [3-5], [5-6]
    """
    windows = []
    num_chapters = len(chapters)

    if num_chapters < window_size:
        # Si hay menos capítulos que el tamaño de ventana, crear una sola ventana
        window = SpeechWindow.from_chapters(
            character_id, character_name, chapters, 0, num_chapters - 1
        )
        if window and window.total_words >= min_words_per_window:
            windows.append(window)
        return windows

    # Calcular step (avance entre ventanas)
    step = window_size - overlap
    if step <= 0:
        step = 1  # Mínimo avance de 1 capítulo

    # Crear ventanas deslizantes
    start_idx = 0
    while start_idx < num_chapters:
        end_idx = min(start_idx + window_size - 1, num_chapters - 1)

        window = SpeechWindow.from_chapters(
            character_id, character_name, chapters, start_idx, end_idx
        )

        # Validar ventana (suficientes palabras)
        if window and window.total_words >= min_words_per_window:
            windows.append(window)

        # Avanzar al siguiente inicio
        start_idx += step

        # Si llegamos al final con la última ventana, salir
        if end_idx == num_chapters - 1:
            break

    logger.debug(
        f"Created {len(windows)} sliding windows for {character_name} "
        f"(window_size={window_size}, overlap={overlap})"
    )

    return windows
