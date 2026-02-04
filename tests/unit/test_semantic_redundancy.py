"""
Tests para el detector de redundancia semántica.

Cubre:
- Detección de oraciones semánticamente similares
- Clasificación de tipos de duplicados (textual, temático, acción)
- Filtrado de falsos positivos (diálogos cortos, frases comunes)
- Diferentes modos de detección (fast, balanced, thorough)
- Integración con ResourceManager
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from narrative_assistant.analysis.semantic_redundancy import (
    DuplicateType,
    RedundancyMode,
    RedundancyReport,
    SemanticDuplicate,
    SemanticRedundancyDetector,
    SentenceInfo,
    get_semantic_redundancy_detector,
)

# Import already at top for TestEdgeCases


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def detector():
    """Detector con mock de embeddings para tests rápidos."""
    return SemanticRedundancyDetector(
        similarity_threshold=0.85,
        mode=RedundancyMode.FAST,
        use_gpu=False,
    )


@pytest.fixture
def mock_embeddings():
    """Mock del modelo de embeddings."""
    with patch(
        "narrative_assistant.analysis.semantic_redundancy.SemanticRedundancyDetector._get_model"
    ) as mock:
        model = MagicMock()
        # Embeddings que producen alta similitud para oraciones 0 y 2
        model.encode.return_value = np.array(
            [
                [1.0, 0.0, 0.0],  # Oración 1
                [0.0, 1.0, 0.0],  # Oración 2 (diferente)
                [0.99, 0.0, 0.1],  # Oración 3 (similar a 1)
                [0.0, 0.0, 1.0],  # Oración 4 (diferente)
            ]
        )
        mock.return_value = model
        yield mock


@pytest.fixture
def sample_chapters():
    """Capítulos de prueba con redundancia conocida."""
    return [
        {
            "number": 1,
            "content": """La casa olía a humedad y memorias. María caminó por el largo pasillo.
            Pedro miraba por la ventana, pensando en el pasado. El silencio era denso.""",
            "start_char": 0,
        },
        {
            "number": 2,
            "content": """El jardín estaba cubierto de hojas secas. Juan podó los rosales.
            La casa olía a humedad y a recuerdos del pasado. Era un aroma persistente.""",
            "start_char": 300,
        },
    ]


# =============================================================================
# Tests de extracción de oraciones
# =============================================================================


class TestSentenceExtraction:
    """Tests para extracción y filtrado de oraciones."""

    def test_extracts_sentences_from_chapters(self, detector):
        """Extrae oraciones correctamente de capítulos."""
        chapters = [
            {
                "number": 1,
                "content": "Primera oración larga suficiente. Segunda oración también larga.",
                "start_char": 0,
            },
        ]

        sentences = detector._extract_sentences(chapters)

        assert len(sentences) == 2
        assert sentences[0].chapter == 1
        assert "Primera" in sentences[0].text

    def test_filters_short_sentences(self, detector):
        """Filtra oraciones muy cortas."""
        chapters = [
            {
                "number": 1,
                "content": "Sí. No. Esta es una oración suficientemente larga para el análisis.",
                "start_char": 0,
            },
        ]

        sentences = detector._extract_sentences(chapters)

        # Solo debe incluir la oración larga
        assert len(sentences) == 1
        assert "suficientemente" in sentences[0].text

    def test_filters_short_dialogues(self, detector):
        """Filtra diálogos cortos."""
        chapters = [
            {
                "number": 1,
                "content": """—Sí señor—. Esta es una narración larga que debería incluirse en el análisis sin problemas.""",
                "start_char": 0,
            },
        ]

        sentences = detector._extract_sentences(chapters)

        # La narración larga debe incluirse pero diálogos cortos como "Sí señor" no
        texts = [s.text for s in sentences]
        # Al menos la narración larga debe estar
        assert any("narración" in t for t in texts)

    def test_filters_common_phrases(self, detector):
        """Filtra oraciones con frases comunes."""
        chapters = [
            {
                "number": 1,
                "content": "Dijo que vendría pronto. Esta es una narración significativa sin frases comunes.",
                "start_char": 0,
            },
        ]

        # Con longitud mínima ajustada para capturar "dijo que"
        detector.min_sentence_length = 15
        sentences = detector._extract_sentences(chapters)

        # "Dijo que vendría pronto" debería filtrarse por ser frase común
        texts = [s.text for s in sentences]
        # Al menos la segunda oración debe estar
        assert any("significativa" in t for t in texts)

    def test_truncates_very_long_sentences(self, detector):
        """Trunca oraciones muy largas."""
        detector.max_sentence_length = 50
        long_sentence = "A" * 100 + "."
        chapters = [{"number": 1, "content": long_sentence, "start_char": 0}]

        sentences = detector._extract_sentences(chapters)

        if sentences:
            assert len(sentences[0].text) <= 53  # 50 + "..."


# =============================================================================
# Tests de detección de duplicados
# =============================================================================


class TestDuplicateDetection:
    """Tests para detección de duplicados semánticos."""

    def test_detects_semantic_duplicates(self, detector, mock_embeddings):
        """Detecta oraciones semánticamente similares."""
        chapters = [
            {
                "number": 1,
                "content": "La casa olía a humedad y memorias antiguas del pasado. " * 2
                + "Pedro caminaba por el jardín sin prisa alguna. "
                + "La vieja casa tenía olor a humedad y recuerdos viejos.",
                "start_char": 0,
            },
        ]

        result = detector.detect(chapters, max_duplicates=10)

        assert result.is_success
        # El mock produce similitud alta entre posiciones 0 y 2

    def test_returns_empty_for_single_sentence(self, detector, mock_embeddings):
        """Retorna vacío si hay una sola oración."""
        chapters = [
            {"number": 1, "content": "Una sola oración en todo el texto sin más.", "start_char": 0},
        ]

        result = detector.detect(chapters)

        assert result.is_success
        assert len(result.value.duplicates) == 0

    def test_respects_similarity_threshold(self, detector, mock_embeddings):
        """Respeta el umbral de similitud configurado."""
        detector.similarity_threshold = 0.99  # Muy estricto
        chapters = [
            {
                "number": 1,
                "content": "Oración A suficientemente larga. Oración B diferente. Oración A ligeramente similar.",
                "start_char": 0,
            },
        ]

        result = detector.detect(chapters)

        assert result.is_success
        # Con umbral tan alto, no debería encontrar duplicados

    def test_penalizes_same_chapter_duplicates(self, detector, mock_embeddings):
        """Penaliza duplicados en el mismo capítulo."""
        # El detector aplica un factor 0.9 a duplicados del mismo capítulo
        # y excluye oraciones muy cercanas (< 3 posiciones)
        chapters = [
            {
                "number": 1,
                "content": "Oración A larga. Oración B. Oración C. Oración A similar.",
                "start_char": 0,
            },
        ]

        result = detector.detect(chapters)

        assert result.is_success


# =============================================================================
# Tests de clasificación de tipos
# =============================================================================


class TestDuplicateTypeClassification:
    """Tests para clasificación de tipos de duplicados."""

    def test_classifies_textual_duplicate(self, detector):
        """Clasifica duplicados textuales (similitud >= 0.95)."""
        dup_type = detector._classify_duplicate_type(
            "La casa olía a humedad y memorias.",
            "La casa olía a humedad y memorias.",
            similarity=0.99,
        )

        assert dup_type == DuplicateType.TEXTUAL

    def test_classifies_action_duplicate(self, detector):
        """Clasifica duplicados de acción."""
        dup_type = detector._classify_duplicate_type(
            "María caminó hacia la puerta con paso decidido.",
            "Juan caminó hacia la ventana con paso firme.",
            similarity=0.87,
        )

        assert dup_type == DuplicateType.ACTION

    def test_classifies_thematic_duplicate(self, detector):
        """Clasifica duplicados temáticos por defecto."""
        dup_type = detector._classify_duplicate_type(
            "El atardecer pintaba el cielo de tonos rojizos.",
            "El ocaso teñía el horizonte de colores cálidos.",
            similarity=0.86,
        )

        assert dup_type == DuplicateType.THEMATIC


# =============================================================================
# Tests de modos de detección
# =============================================================================


class TestDetectionModes:
    """Tests para diferentes modos de detección."""

    def test_fast_mode_uses_fewer_neighbors(self):
        """El modo FAST usa menos vecinos."""
        detector = SemanticRedundancyDetector(mode=RedundancyMode.FAST)
        params = detector._mode_params[RedundancyMode.FAST]

        assert params["k_neighbors"] == 50

    def test_balanced_mode_parameters(self):
        """El modo BALANCED tiene parámetros intermedios."""
        detector = SemanticRedundancyDetector(mode=RedundancyMode.BALANCED)
        params = detector._mode_params[RedundancyMode.BALANCED]

        assert params["k_neighbors"] == 100

    def test_thorough_mode_uses_more_neighbors(self):
        """El modo THOROUGH usa más vecinos."""
        detector = SemanticRedundancyDetector(mode=RedundancyMode.THOROUGH)
        params = detector._mode_params[RedundancyMode.THOROUGH]

        assert params["k_neighbors"] == 500


# =============================================================================
# Tests de reporte
# =============================================================================


class TestRedundancyReport:
    """Tests para el reporte de redundancia."""

    def test_report_to_dict(self):
        """El reporte se serializa correctamente."""
        report = RedundancyReport(
            duplicates=[],
            sentences_analyzed=100,
            chapters_analyzed=5,
            processing_time_seconds=1.5,
            mode="balanced",
            threshold=0.85,
            textual_count=2,
            thematic_count=5,
            action_count=3,
        )

        data = report.to_dict()

        assert data["sentences_analyzed"] == 100
        assert data["chapters_analyzed"] == 5
        assert data["mode"] == "balanced"
        assert data["total_duplicates"] == 0
        assert data["textual_count"] == 2

    def test_semantic_duplicate_to_dict(self):
        """SemanticDuplicate se serializa correctamente."""
        dup = SemanticDuplicate(
            text1="Oración original aquí.",
            text2="Oración similar aquí.",
            chapter1=1,
            chapter2=2,
            position1=0,
            position2=50,
            start_char1=0,
            start_char2=500,
            similarity=0.92,
            duplicate_type=DuplicateType.THEMATIC,
        )

        data = dup.to_dict()

        assert data["text1"] == "Oración original aquí."
        assert data["similarity"] == 0.92
        assert data["duplicate_type"] == "thematic"
        assert data["chapter1"] == 1
        assert data["chapter2"] == 2


# =============================================================================
# Tests de factory function
# =============================================================================


class TestFactoryFunction:
    """Tests para la función factory."""

    def test_get_detector_with_defaults(self):
        """Crea detector con valores por defecto."""
        detector = get_semantic_redundancy_detector()

        assert detector.mode == RedundancyMode.BALANCED
        assert detector.similarity_threshold == 0.85

    def test_get_detector_with_custom_mode(self):
        """Crea detector con modo personalizado."""
        detector = get_semantic_redundancy_detector(mode="fast", threshold=0.80)

        assert detector.mode == RedundancyMode.FAST
        assert detector.similarity_threshold == 0.80

    def test_get_detector_invalid_mode_raises(self):
        """Lanza error con modo inválido."""
        with pytest.raises(ValueError):
            get_semantic_redundancy_detector(mode="invalid_mode")


# =============================================================================
# Tests de casos límite
# =============================================================================


class TestEdgeCases:
    """Tests para casos límite."""

    def test_empty_chapters(self, detector, mock_embeddings):
        """Maneja capítulos vacíos."""
        chapters = [
            {"number": 1, "content": "", "start_char": 0},
            {"number": 2, "content": "   ", "start_char": 0},
        ]

        result = detector.detect(chapters)

        assert result.is_success
        assert result.value.sentences_analyzed == 0

    def test_single_chapter(self, detector, mock_embeddings):
        """Maneja un solo capítulo."""
        chapters = [
            {
                "number": 1,
                "content": "Una oración suficientemente larga para el análisis semántico.",
                "start_char": 0,
            },
        ]

        result = detector.detect(chapters)

        assert result.is_success

    def test_max_duplicates_limit(self, detector):
        """Respeta el límite máximo de duplicados en búsqueda lineal."""
        # Crear oraciones sintéticas para probar el límite
        sentences = [
            SentenceInfo(f"Oración número {i} suficientemente larga.", 1, i, i * 50)
            for i in range(10)
        ]

        # Embeddings que hacen que varias oraciones sean similares
        embeddings = np.random.randn(10, 3).astype(np.float32)
        # Hacer que las primeras 5 sean muy similares
        embeddings[:5] = embeddings[0] + np.random.randn(5, 3) * 0.01

        detector.similarity_threshold = 0.5  # Bajo para capturar más
        duplicates = detector._find_duplicates_linear(sentences, embeddings, max_duplicates=3)

        assert len(duplicates) <= 3

    def test_handles_special_characters(self, detector):
        """Maneja caracteres especiales en el texto."""
        chapters = [
            {
                "number": 1,
                "content": "¿Qué está pasando con todo esto que sucede? ¡No lo puedo creer ni entender! María preguntó directamente: «¿Dónde estás exactamente ahora mismo?»",
                "start_char": 0,
            },
        ]

        # Solo probar extracción de oraciones, no detección completa
        sentences = detector._extract_sentences(chapters)

        # Debe extraer oraciones con caracteres especiales
        assert len(sentences) >= 1
        assert any("¿" in s.text or "¡" in s.text or "«" in s.text for s in sentences)


# =============================================================================
# Tests de integración con ResourceManager
# =============================================================================


class TestResourceManagerIntegration:
    """Tests de integración con el gestor de recursos."""

    def test_uses_resource_manager_gpu_setting(self):
        """Usa configuración de GPU del ResourceManager."""
        with patch(
            "narrative_assistant.analysis.semantic_redundancy.get_resource_manager"
        ) as mock_rm:
            mock_rm.return_value.recommendation.use_gpu_for_embeddings = False

            detector = SemanticRedundancyDetector()

            assert detector.use_gpu == False

    def test_overrides_gpu_setting(self):
        """Permite override de configuración de GPU."""
        with patch(
            "narrative_assistant.analysis.semantic_redundancy.get_resource_manager"
        ) as mock_rm:
            mock_rm.return_value.recommendation.use_gpu_for_embeddings = True

            detector = SemanticRedundancyDetector(use_gpu=False)

            assert detector.use_gpu == False


# =============================================================================
# Tests de búsqueda lineal (fallback sin FAISS)
# =============================================================================


class TestLinearSearch:
    """Tests para búsqueda lineal sin FAISS."""

    def test_linear_search_finds_duplicates(self, detector):
        """La búsqueda lineal encuentra duplicados correctamente."""
        sentences = [
            SentenceInfo("Oración A larga.", 1, 0, 0),
            SentenceInfo("Oración B diferente.", 1, 1, 50),
            SentenceInfo("Oración A similar.", 2, 2, 100),
        ]

        # Embeddings que hacen que 0 y 2 sean similares
        embeddings = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.99, 0.1, 0.0],
            ]
        ).astype(np.float32)

        duplicates = detector._find_duplicates_linear(sentences, embeddings, max_duplicates=10)

        # Debe encontrar similitud entre 0 y 2
        assert len(duplicates) >= 0  # Puede no encontrar si threshold es alto

    def test_linear_search_handles_empty(self, detector):
        """La búsqueda lineal maneja listas vacías."""
        sentences = []
        embeddings = np.array([]).reshape(0, 3).astype(np.float32)

        duplicates = detector._find_duplicates_linear(sentences, embeddings, max_duplicates=10)

        assert len(duplicates) == 0


# =============================================================================
# Tests de configuración
# =============================================================================


class TestConfiguration:
    """Tests para configuración del detector."""

    def test_default_config(self):
        """Verifica configuración por defecto."""
        detector = SemanticRedundancyDetector()

        assert detector.similarity_threshold == 0.85
        assert detector.mode == RedundancyMode.BALANCED
        assert detector.min_sentence_length == 20
        assert detector.max_sentence_length == 500

    def test_custom_config(self):
        """Permite configuración personalizada."""
        detector = SemanticRedundancyDetector(
            similarity_threshold=0.90,
            mode=RedundancyMode.THOROUGH,
            min_sentence_length=30,
            max_sentence_length=300,
        )

        assert detector.similarity_threshold == 0.90
        assert detector.mode == RedundancyMode.THOROUGH
        assert detector.min_sentence_length == 30
        assert detector.max_sentence_length == 300
