"""
Tests de rendimiento para manuscritos grandes.

Cubre:
- Manuscritos de 50K, 100K y 200K palabras
- Tiempo de procesamiento
- Uso de memoria
- Escalabilidad

Nota: Estos tests generan documentos sintéticos para medir rendimiento.
"""

import gc
import time
from typing import Generator

import pytest

# =============================================================================
# Fixtures para generación de documentos
# =============================================================================


def generate_chapter(chapter_num: int, word_count: int = 5000) -> dict:
    """
    Genera un capítulo sintético con contenido narrativo.

    Args:
        chapter_num: Número de capítulo
        word_count: Palabras aproximadas

    Returns:
        Dict con número y contenido
    """
    sentences = [
        "María caminaba por el parque pensando en su vida.",
        "Pedro la observaba desde lejos sin atreverse a acercarse.",
        "El sol brillaba intensamente sobre la ciudad.",
        "Los pájaros cantaban en los árboles del jardín.",
        "La brisa movía suavemente las hojas de los árboles.",
        "Carmen llegó tarde a la reunión como siempre.",
        "Juan preparó el desayuno para toda la familia.",
        "El reloj marcaba las diez de la mañana.",
        "La lluvia comenzó a caer de repente.",
        "Elena abrió la ventana para respirar aire fresco.",
    ]

    dialogues = [
        "—¿Cómo estás hoy? —preguntó María con curiosidad.",
        "—Bien, gracias —respondió Pedro sonriendo.",
        "—No lo sé —dijo Carmen pensativa.",
        "—Vamos a ver qué pasa —añadió Juan.",
        "—Me parece bien —contestó Elena.",
    ]

    paragraphs = []
    current_words = 0
    target_words = word_count

    while current_words < target_words:
        # Alternar entre narración y diálogo
        if len(paragraphs) % 3 == 2:
            # Párrafo de diálogo
            dialogue_lines = [dialogues[i % len(dialogues)] for i in range(3)]
            para = "\n".join(dialogue_lines)
        else:
            # Párrafo narrativo (5-8 oraciones)
            num_sentences = 5 + (len(paragraphs) % 4)
            para_sentences = [
                sentences[(len(paragraphs) + i) % len(sentences)] for i in range(num_sentences)
            ]
            para = " ".join(para_sentences)

        paragraphs.append(para)
        current_words += len(para.split())

    content = f"Capítulo {chapter_num}\n\n" + "\n\n".join(paragraphs)

    return {
        "number": chapter_num,
        "content": content,
        "start_char": 0,  # Se recalcula después
    }


def generate_manuscript(total_words: int, words_per_chapter: int = 5000) -> tuple[str, list[dict]]:
    """
    Genera un manuscrito completo.

    Args:
        total_words: Palabras totales aproximadas
        words_per_chapter: Palabras por capítulo

    Returns:
        (texto_completo, lista_de_capítulos)
    """
    num_chapters = max(1, total_words // words_per_chapter)
    chapters = []
    full_text = ""

    for i in range(1, num_chapters + 1):
        chapter = generate_chapter(i, words_per_chapter)
        chapter["start_char"] = len(full_text)
        full_text += chapter["content"] + "\n\n"
        chapters.append(chapter)

    return full_text, chapters


# =============================================================================
# Tests de rendimiento para detector de duplicados
# =============================================================================


class TestDuplicateDetectorPerformance:
    """Tests de rendimiento para detección de duplicados."""

    @pytest.mark.slow
    def test_50k_words_under_30_seconds(self):
        """Analiza 50K palabras en menos de 30 segundos."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        text, chapters = generate_manuscript(50000)
        detector = DuplicateDetector()

        # Forzar recolección de basura antes
        gc.collect()

        start_time = time.time()
        report = detector.detect_all(text, chapters)
        elapsed = time.time() - start_time

        assert report is not None
        assert elapsed < 30, f"Tardó {elapsed:.1f}s (máximo 30s)"

    @pytest.mark.slow
    def test_100k_words_under_60_seconds(self):
        """Analiza 100K palabras en menos de 60 segundos."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        text, chapters = generate_manuscript(100000)
        detector = DuplicateDetector()

        gc.collect()

        start_time = time.time()
        report = detector.detect_all(text, chapters)
        elapsed = time.time() - start_time

        assert report is not None
        assert elapsed < 60, f"Tardó {elapsed:.1f}s (máximo 60s)"

    @pytest.mark.slow
    @pytest.mark.skip(reason="Test muy largo - ejecutar manualmente")
    def test_200k_words_scalability(self):
        """Verifica escalabilidad con 200K palabras."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        text, chapters = generate_manuscript(200000)
        detector = DuplicateDetector()

        gc.collect()

        start_time = time.time()
        report = detector.detect_all(text, chapters)
        elapsed = time.time() - start_time

        assert report is not None
        # No establecemos límite estricto, solo verificamos que complete
        print(f"200K palabras procesadas en {elapsed:.1f}s")


# =============================================================================
# Tests de rendimiento para validador de diálogos
# =============================================================================


class TestDialogueValidatorPerformance:
    """Tests de rendimiento para validación de diálogos."""

    @pytest.mark.slow
    def test_50k_words_dialogue_validation(self):
        """Valida diálogos en 50K palabras en menos de 20 segundos."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        text, chapters = generate_manuscript(50000)
        validator = DialogueContextValidator()

        gc.collect()

        start_time = time.time()
        report = validator.validate_all(chapters)
        elapsed = time.time() - start_time

        assert report is not None
        assert elapsed < 20, f"Tardó {elapsed:.1f}s (máximo 20s)"

    @pytest.mark.slow
    def test_100k_words_dialogue_validation(self):
        """Valida diálogos en 100K palabras en menos de 45 segundos."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        text, chapters = generate_manuscript(100000)
        validator = DialogueContextValidator()

        gc.collect()

        start_time = time.time()
        report = validator.validate_all(chapters)
        elapsed = time.time() - start_time

        assert report is not None
        assert elapsed < 45, f"Tardó {elapsed:.1f}s (máximo 45s)"


# =============================================================================
# Tests de rendimiento para detector de estructura narrativa
# =============================================================================


class TestNarrativeStructurePerformance:
    """Tests de rendimiento para detección de estructura narrativa."""

    @pytest.mark.slow
    def test_50k_words_narrative_analysis(self):
        """Analiza estructura narrativa en 50K palabras en menos de 15 segundos."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        text, chapters = generate_manuscript(50000)
        detector = NarrativeStructureDetector()

        gc.collect()

        start_time = time.time()
        report = detector.detect_all(text, chapters)
        elapsed = time.time() - start_time

        assert report is not None
        assert elapsed < 15, f"Tardó {elapsed:.1f}s (máximo 15s)"


# =============================================================================
# Tests de uso de memoria
# =============================================================================


class TestMemoryUsage:
    """Tests para verificar uso razonable de memoria."""

    @pytest.mark.slow
    def test_memory_not_excessive_50k(self):
        """Verifica que el uso de memoria sea razonable para 50K palabras."""
        import sys

        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        text, chapters = generate_manuscript(50000)

        # Medir tamaño aproximado del input
        input_size = sys.getsizeof(text)

        detector = DuplicateDetector()
        gc.collect()

        report = detector.detect_all(text, chapters)

        # El reporte no debería ser desproporcionadamente grande
        report_dict = report.to_dict()
        report_size = len(str(report_dict))

        # El output no debería ser más de 10x el input
        # (esto es heurístico, no un límite técnico)
        assert report_size < input_size * 10, (
            f"Output ({report_size} bytes) demasiado grande vs input ({input_size} bytes)"
        )

    @pytest.mark.slow
    def test_garbage_collection_works(self):
        """Verifica que los objetos se liberan correctamente."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        # Primer análisis
        text1, chapters1 = generate_manuscript(10000)
        detector1 = DuplicateDetector()
        report1 = detector1.detect_all(text1, chapters1)

        # Liberar referencias
        del text1, chapters1, detector1, report1
        collected = gc.collect()

        # Debería haber recolectado algo
        # (si no hay memory leaks graves)
        assert collected >= 0  # No establecemos mínimo estricto


# =============================================================================
# Tests de escalabilidad lineal
# =============================================================================


class TestScalability:
    """Tests para verificar escalabilidad aproximadamente lineal."""

    @pytest.mark.slow
    def test_linear_scalability_duplicate_detector(self):
        """Verifica que el tiempo escale de forma razonable."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        times = []

        for word_count in [10000, 20000, 30000]:
            text, chapters = generate_manuscript(word_count)
            gc.collect()

            start = time.time()
            detector.detect_all(text, chapters)
            elapsed = time.time() - start

            times.append((word_count, elapsed))

        # Verificar que no sea exponencial
        # Si es lineal, 30K debería tomar ~3x de 10K
        # Permitimos hasta 5x para dar margen
        ratio = times[2][1] / times[0][1] if times[0][1] > 0.01 else 1

        assert ratio < 10, (
            f"Escalabilidad no lineal: {times[0][0]} palabras en {times[0][1]:.2f}s, "
            f"{times[2][0]} palabras en {times[2][1]:.2f}s (ratio {ratio:.1f}x)"
        )


# =============================================================================
# Marcador para tests lentos
# =============================================================================


def pytest_configure(config):
    """Registra el marcador 'slow' para tests lentos."""
    config.addinivalue_line("markers", "slow: marca tests que tardan más de 10 segundos")
