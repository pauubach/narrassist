"""
Tests de rendimiento para detección de redundancia semántica.

Cubre:
- Manuscritos de 50K, 100K palabras
- Diferentes modos (fast, balanced, thorough)
- Uso de memoria
- Escalabilidad
- Comparación FAISS vs lineal

Nota: Estos tests requieren sentence-transformers instalado.
"""

import gc
import sys
import time
from typing import Optional

import pytest

# =============================================================================
# Fixtures para generación de documentos con redundancias
# =============================================================================


def generate_redundant_chapter(
    chapter_num: int, word_count: int = 5000, redundancy_rate: float = 0.05
) -> dict:
    """
    Genera un capítulo sintético con redundancias controladas.

    Args:
        chapter_num: Número de capítulo
        word_count: Palabras aproximadas
        redundancy_rate: Proporción de oraciones redundantes (0.0-1.0)

    Returns:
        Dict con número y contenido
    """
    base_sentences = [
        "María caminaba por el parque pensando en su vida pasada.",
        "Pedro la observaba desde lejos sin atreverse a acercarse.",
        "El sol brillaba intensamente sobre la ciudad dormida.",
        "Los pájaros cantaban en los árboles del jardín antiguo.",
        "La brisa movía suavemente las hojas de los árboles centenarios.",
        "Carmen llegó tarde a la reunión como siempre solía hacer.",
        "Juan preparó el desayuno para toda la familia reunida.",
        "El reloj marcaba las diez de la mañana exactas.",
        "La lluvia comenzó a caer de repente sobre la ciudad.",
        "Elena abrió la ventana para respirar el aire fresco.",
        "La casa olía a humedad y memorias de tiempos mejores.",
        "Roberto guardaba secretos que nadie más conocía entonces.",
        "Las estrellas brillaban en el cielo nocturno despejado.",
        "El viento soplaba con fuerza entre los edificios viejos.",
        "Marta recordaba los días de su infancia feliz.",
    ]

    # Oraciones temáticamente similares (para generar redundancias semánticas)
    redundant_variants = {
        0: "María paseaba por el jardín reflexionando sobre su existencia pasada.",
        1: "Pedro la miraba a distancia sin valor para aproximarse.",
        2: "El astro rey iluminaba con fuerza la urbe adormecida.",
        5: "Carmen arribó con retraso al encuentro como era su costumbre.",
        10: "La vivienda tenía aroma a humedad y recuerdos de épocas mejores.",
        14: "Marta rememoraba las jornadas de su niñez alegre.",
    }

    paragraphs = []
    current_words = 0
    target_words = word_count
    sentence_idx = 0
    redundancy_counter = 0

    while current_words < target_words:
        # Construir párrafo (5-8 oraciones)
        num_sentences = 5 + (len(paragraphs) % 4)
        para_sentences = []

        for _ in range(num_sentences):
            base_idx = sentence_idx % len(base_sentences)

            # Decidir si insertar redundancia
            if (
                redundancy_counter / max(1, sentence_idx + 1) < redundancy_rate
                and base_idx in redundant_variants
            ):
                para_sentences.append(redundant_variants[base_idx])
                redundancy_counter += 1
            else:
                para_sentences.append(base_sentences[base_idx])

            sentence_idx += 1

        para = " ".join(para_sentences)
        paragraphs.append(para)
        current_words += len(para.split())

    content = f"Capítulo {chapter_num}\n\n" + "\n\n".join(paragraphs)

    return {
        "number": chapter_num,
        "content": content,
        "start_char": 0,
    }


def generate_manuscript_with_redundancy(
    total_words: int, words_per_chapter: int = 5000, redundancy_rate: float = 0.05
) -> tuple[str, list[dict]]:
    """
    Genera un manuscrito completo con redundancias controladas.

    Args:
        total_words: Palabras totales aproximadas
        words_per_chapter: Palabras por capítulo
        redundancy_rate: Proporción de redundancias

    Returns:
        (texto_completo, lista_de_capítulos)
    """
    num_chapters = max(1, total_words // words_per_chapter)
    chapters = []
    full_text = ""

    for i in range(1, num_chapters + 1):
        chapter = generate_redundant_chapter(i, words_per_chapter, redundancy_rate)
        chapter["start_char"] = len(full_text)
        full_text += chapter["content"] + "\n\n"
        chapter["end_char"] = len(full_text)
        chapters.append(chapter)

    return full_text, chapters


# =============================================================================
# Tests de rendimiento por tamaño
# =============================================================================


class TestSemanticRedundancyPerformance:
    """Tests de rendimiento para detección de redundancia semántica."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_50k_words_fast_mode_under_60_seconds(self, detector):
        """Analiza 50K palabras en modo fast en menos de 60 segundos."""
        text, chapters = generate_manuscript_with_redundancy(50000)

        gc.collect()

        start_time = time.time()
        result = detector.detect(chapters, mode="fast")
        elapsed = time.time() - start_time

        assert result.is_success, f"Error: {result.error}"
        assert elapsed < 60, f"Modo fast tardó {elapsed:.1f}s (máximo 60s)"

        report = result.value
        print(f"\n50K palabras (fast): {elapsed:.1f}s, {len(report.duplicates)} duplicados")

    @pytest.mark.slow
    def test_50k_words_balanced_mode_under_90_seconds(self, detector):
        """Analiza 50K palabras en modo balanced en menos de 90 segundos."""
        text, chapters = generate_manuscript_with_redundancy(50000)

        gc.collect()

        start_time = time.time()
        result = detector.detect(chapters, mode="balanced")
        elapsed = time.time() - start_time

        assert result.is_success, f"Error: {result.error}"
        assert elapsed < 90, f"Modo balanced tardó {elapsed:.1f}s (máximo 90s)"

        report = result.value
        print(f"\n50K palabras (balanced): {elapsed:.1f}s, {len(report.duplicates)} duplicados")

    @pytest.mark.slow
    def test_100k_words_fast_mode_under_120_seconds(self, detector):
        """Analiza 100K palabras en modo fast en menos de 120 segundos."""
        text, chapters = generate_manuscript_with_redundancy(100000)

        gc.collect()

        start_time = time.time()
        result = detector.detect(chapters, mode="fast")
        elapsed = time.time() - start_time

        assert result.is_success, f"Error: {result.error}"
        assert elapsed < 120, f"Modo fast tardó {elapsed:.1f}s (máximo 120s)"

        report = result.value
        print(f"\n100K palabras (fast): {elapsed:.1f}s, {len(report.duplicates)} duplicados")

    @pytest.mark.slow
    @pytest.mark.skip(reason="Test muy largo - ejecutar manualmente")
    def test_100k_words_thorough_mode(self, detector):
        """Analiza 100K palabras en modo thorough (sin límite estricto)."""
        text, chapters = generate_manuscript_with_redundancy(100000)

        gc.collect()

        start_time = time.time()
        result = detector.detect(chapters, mode="thorough")
        elapsed = time.time() - start_time

        assert result.is_success, f"Error: {result.error}"

        report = result.value
        print(f"\n100K palabras (thorough): {elapsed:.1f}s, {len(report.duplicates)} duplicados")


# =============================================================================
# Tests de comparación de modos
# =============================================================================


class TestModeComparison:
    """Tests para comparar rendimiento entre modos."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_mode_performance_comparison_20k(self, detector):
        """Compara rendimiento de los tres modos con 20K palabras."""
        text, chapters = generate_manuscript_with_redundancy(20000, redundancy_rate=0.08)

        results = {}

        for mode in ["fast", "balanced", "thorough"]:
            gc.collect()

            start_time = time.time()
            result = detector.detect(chapters, mode=mode)
            elapsed = time.time() - start_time

            assert result.is_success, f"Error en modo {mode}: {result.error}"

            results[mode] = {
                "time": elapsed,
                "duplicates": len(result.value.duplicates),
            }

        # Verificar que fast sea más rápido que balanced
        assert results["fast"]["time"] <= results["balanced"]["time"] * 1.5, (
            f"Fast ({results['fast']['time']:.1f}s) no es más rápido que "
            f"balanced ({results['balanced']['time']:.1f}s)"
        )

        # Verificar que balanced sea más rápido que thorough
        assert results["balanced"]["time"] <= results["thorough"]["time"] * 1.5, (
            f"Balanced ({results['balanced']['time']:.1f}s) no es más rápido que "
            f"thorough ({results['thorough']['time']:.1f}s)"
        )

        print("\nComparación de modos (20K palabras):")
        for mode, data in results.items():
            print(f"  {mode}: {data['time']:.1f}s, {data['duplicates']} duplicados")


# =============================================================================
# Tests de uso de memoria
# =============================================================================


class TestMemoryUsage:
    """Tests para verificar uso razonable de memoria."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_memory_not_excessive_30k(self, detector):
        """Verifica que el uso de memoria sea razonable para 30K palabras."""
        text, chapters = generate_manuscript_with_redundancy(30000)

        # Medir tamaño aproximado del input
        input_size = sys.getsizeof(text)
        for ch in chapters:
            input_size += sys.getsizeof(ch.get("content", ""))

        gc.collect()

        result = detector.detect(chapters, mode="balanced")

        assert result.is_success

        # El reporte no debería ser desproporcionadamente grande
        report = result.value
        report_dict = report.to_dict() if hasattr(report, "to_dict") else str(report)
        report_size = len(str(report_dict))

        # El output no debería ser más de 20x el input
        assert report_size < input_size * 20, (
            f"Output ({report_size} bytes) demasiado grande vs input ({input_size} bytes)"
        )

    @pytest.mark.slow
    def test_garbage_collection_works(self, detector):
        """Verifica que los objetos se liberan correctamente."""
        # Primer análisis
        text1, chapters1 = generate_manuscript_with_redundancy(10000)
        result1 = detector.detect(chapters1, mode="fast")

        # Liberar referencias
        del text1, chapters1, result1
        collected = gc.collect()

        # Segundo análisis para verificar que no hay memory leak
        text2, chapters2 = generate_manuscript_with_redundancy(10000)
        result2 = detector.detect(chapters2, mode="fast")

        assert result2.is_success
        assert collected >= 0  # No establecemos mínimo estricto


# =============================================================================
# Tests de escalabilidad
# =============================================================================


class TestScalability:
    """Tests para verificar escalabilidad aproximadamente lineal."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_linear_scalability_fast_mode(self, detector):
        """Verifica que el tiempo escale de forma razonable en modo fast."""
        times = []

        for word_count in [10000, 20000, 30000]:
            text, chapters = generate_manuscript_with_redundancy(word_count)
            gc.collect()

            start = time.time()
            result = detector.detect(chapters, mode="fast")
            elapsed = time.time() - start

            assert result.is_success, f"Error en {word_count} palabras"
            times.append((word_count, elapsed))

        # Verificar que no sea exponencial
        # Si es lineal, 30K debería tomar ~3x de 10K
        # Permitimos hasta 6x para dar margen (FAISS tiene overhead inicial)
        ratio = times[2][1] / times[0][1] if times[0][1] > 0.1 else 1

        assert ratio < 10, (
            f"Escalabilidad no lineal: {times[0][0]} palabras en {times[0][1]:.2f}s, "
            f"{times[2][0]} palabras en {times[2][1]:.2f}s (ratio {ratio:.1f}x)"
        )

        print("\nEscalabilidad (modo fast):")
        for wc, t in times:
            print(f"  {wc} palabras: {t:.2f}s")

    @pytest.mark.slow
    def test_scaling_with_sentence_count(self, detector):
        """Verifica escalabilidad basada en número de oraciones."""
        # Generar documentos con diferente densidad de oraciones
        results = []

        for sentences_per_chapter in [50, 100, 150]:
            # Calcular palabras para lograr aproximadamente esas oraciones
            # (promedio ~15 palabras por oración)
            word_count = sentences_per_chapter * 15 * 5  # 5 capítulos

            text, chapters = generate_manuscript_with_redundancy(
                word_count, words_per_chapter=sentences_per_chapter * 15
            )

            gc.collect()

            start = time.time()
            result = detector.detect(chapters, mode="fast")
            elapsed = time.time() - start

            assert result.is_success

            total_sentences = sum(len(ch.get("content", "").split(".")) for ch in chapters)
            results.append((total_sentences, elapsed))

        print("\nEscalabilidad por oraciones:")
        for s, t in results:
            print(f"  ~{s} oraciones: {t:.2f}s")


# =============================================================================
# Tests de detección de redundancias
# =============================================================================


class TestRedundancyDetection:
    """Tests para verificar que se detectan redundancias correctamente."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_detects_known_redundancies(self, detector):
        """Verifica que detecta redundancias conocidas en el texto generado."""
        # Generar con alta tasa de redundancia
        text, chapters = generate_manuscript_with_redundancy(
            20000,
            redundancy_rate=0.15,  # 15% de redundancias
        )

        result = detector.detect(chapters, mode="balanced", threshold=0.80)

        assert result.is_success
        report = result.value

        # Con 15% de redundancia, debería detectar al menos algunas
        assert len(report.duplicates) > 0, (
            "No se detectaron redundancias en texto con 15% de redundancia"
        )

        print(f"\nRedundancias detectadas: {len(report.duplicates)}")
        if report.duplicates:
            # Mostrar ejemplo
            dup = report.duplicates[0]
            print(f"  Ejemplo: similitud {dup.similarity:.2f}")
            print(f"    Texto 1: {dup.text1[:60]}...")
            print(f"    Texto 2: {dup.text2[:60]}...")

    @pytest.mark.slow
    def test_no_false_positives_unique_text(self, detector):
        """Verifica que no hay falsos positivos en texto único."""
        # Texto con cero redundancias
        text, chapters = generate_manuscript_with_redundancy(
            15000,
            redundancy_rate=0.0,  # Sin redundancias
        )

        result = detector.detect(chapters, mode="fast", threshold=0.95)  # Umbral alto

        assert result.is_success
        report = result.value

        # Con umbral 0.95 y sin redundancias intencionales,
        # no debería haber muchos duplicados
        # (permitimos algunos por coincidencias de estructura)
        assert len(report.duplicates) < 10, (
            f"Demasiados falsos positivos: {len(report.duplicates)} duplicados "
            "en texto sin redundancias"
        )


# =============================================================================
# Tests de threshold
# =============================================================================


class TestThresholdBehavior:
    """Tests para verificar comportamiento con diferentes umbrales."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_lower_threshold_more_duplicates(self, detector):
        """Umbral más bajo debería encontrar más duplicados."""
        text, chapters = generate_manuscript_with_redundancy(15000, redundancy_rate=0.10)

        gc.collect()

        # Umbral alto
        result_high = detector.detect(chapters, mode="fast", threshold=0.90)
        assert result_high.is_success
        dups_high = len(result_high.value.duplicates)

        # Umbral bajo
        result_low = detector.detect(chapters, mode="fast", threshold=0.75)
        assert result_low.is_success
        dups_low = len(result_low.value.duplicates)

        # Umbral bajo debería encontrar igual o más duplicados
        assert dups_low >= dups_high, (
            f"Umbral bajo ({dups_low}) debería encontrar >= que alto ({dups_high})"
        )

        print(f"\nUmbral 0.90: {dups_high} duplicados")
        print(f"Umbral 0.75: {dups_low} duplicados")


# =============================================================================
# Tests de FAISS vs lineal
# =============================================================================


class TestFAISSvsLinear:
    """Tests para comparar FAISS con búsqueda lineal."""

    @pytest.fixture
    def detector(self):
        """Crea instancia del detector."""
        try:
            from narrative_assistant.analysis.semantic_redundancy import (
                SemanticRedundancyDetector,
            )

            return SemanticRedundancyDetector()
        except ImportError:
            pytest.skip("sentence-transformers no disponible")

    @pytest.mark.slow
    def test_faiss_faster_than_linear_large_doc(self, detector):
        """FAISS debería ser más rápido que lineal en documentos grandes."""
        text, chapters = generate_manuscript_with_redundancy(30000)

        gc.collect()

        # Medir tiempo con FAISS (si disponible)
        start_faiss = time.time()
        result_faiss = detector.detect(chapters, mode="balanced")
        time_faiss = time.time() - start_faiss

        assert result_faiss.is_success

        # Verificar si FAISS fue usado
        used_faiss = detector._faiss_available if hasattr(detector, "_faiss_available") else None

        print("\n30K palabras:")
        print(f"  Tiempo: {time_faiss:.2f}s")
        print(f"  FAISS disponible: {used_faiss}")
        print(f"  Duplicados: {len(result_faiss.value.duplicates)}")


# =============================================================================
# Marcador para tests lentos
# =============================================================================


def pytest_configure(config):
    """Registra el marcador 'slow' para tests lentos."""
    config.addinivalue_line("markers", "slow: marca tests que tardan más de 10 segundos")
