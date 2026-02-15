"""Tests para CoherenceDetector (S18-B4).

Tests unitarios con mocks — no requieren Ollama ni modelos cargados.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.corrections.config import CoherenceConfig
from narrative_assistant.corrections.detectors.coherence import (
    CoherenceDetector,
    _JACCARD_REDUNDANCY_THRESHOLD,
)
from narrative_assistant.corrections.types import CoherenceIssueType, CorrectionCategory


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def detector():
    return CoherenceDetector(CoherenceConfig(enabled=True, use_llm=False))


@pytest.fixture
def disabled_detector():
    return CoherenceDetector(CoherenceConfig(enabled=False))


@pytest.fixture
def llm_detector():
    return CoherenceDetector(CoherenceConfig(enabled=True, use_llm=True))


def _make_text(*paragraphs: str) -> str:
    """Helper para crear texto con párrafos separados por doble newline."""
    return "\n\n".join(paragraphs)


def _long_para(base: str, n_words: int = 20) -> str:
    """Crea un párrafo con al menos n_words para superar min_paragraph_words."""
    words = base.split()
    while len(words) < n_words:
        words.extend(base.split())
    return " ".join(words[:n_words])


# ============================================================================
# Básicos
# ============================================================================


class TestCoherenceDetectorBasic:
    def test_disabled_returns_empty(self, disabled_detector):
        text = _make_text(
            _long_para("Párrafo primero con contenido importante."),
            _long_para("Párrafo primero con contenido importante."),
        )
        issues = disabled_detector.detect(text)
        assert issues == []

    def test_category_is_coherence(self, detector):
        assert detector.category == CorrectionCategory.COHERENCE

    def test_requires_llm_true(self, detector):
        assert detector.requires_llm is True

    def test_empty_text_no_crash(self, detector):
        issues = detector.detect("")
        assert isinstance(issues, list)
        assert len(issues) == 0

    def test_single_paragraph_no_issues(self, detector):
        """Un solo párrafo sustantivo → no se puede comparar → sin issues."""
        text = _long_para("Este es un párrafo largo con mucho contenido sobre un tema.")
        issues = detector.detect(text)
        assert len(issues) == 0

    def test_short_paragraphs_ignored(self, detector):
        """Párrafos con < min_paragraph_words se ignoran."""
        text = _make_text("Corto.", "Otro corto.", "Y otro.")
        issues = detector.detect(text)
        assert len(issues) == 0


# ============================================================================
# Tier 3: Jaccard (heurístico) — siempre disponible
# ============================================================================


class TestJaccardHeuristic:
    def test_redundant_paragraphs_detected(self, detector):
        """Párrafos con vocabulario muy similar → redundante."""
        para = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para obtener resultados estadísticamente significativos en el análisis."
        )
        # Segundo párrafo casi idéntico
        para2 = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para lograr resultados estadísticamente significativos en el análisis."
        )
        text = _make_text(para, para2)
        issues = detector.detect(text)
        redundant = [
            i for i in issues
            if i.issue_type == CoherenceIssueType.REDUNDANT_PARAGRAPH.value
        ]
        assert len(redundant) >= 1

    def test_different_paragraphs_no_issue(self, detector):
        """Párrafos con vocabulario diferente → no flaggeados."""
        para1 = _long_para(
            "La astronomía estudia los cuerpos celestes, planetas, estrellas y galaxias "
            "utilizando telescopios y observatorios especializados en diferentes longitudes."
        )
        para2 = _long_para(
            "La gastronomía francesa destaca por sus salsas elaboradas, vinos tintos "
            "y postres refinados que combinan ingredientes frescos con técnicas clásicas."
        )
        text = _make_text(para1, para2)
        issues = detector.detect(text)
        redundant = [
            i for i in issues
            if i.issue_type == CoherenceIssueType.REDUNDANT_PARAGRAPH.value
        ]
        assert len(redundant) == 0

    def test_method_used_is_jaccard(self, detector):
        """Sin LLM ni embeddings, method_used debe ser 'jaccard'."""
        para = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para obtener resultados estadísticamente significativos en el análisis."
        )
        para2 = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para lograr resultados estadísticamente significativos en el análisis."
        )
        text = _make_text(para, para2)
        issues = detector.detect(text)
        for issue in issues:
            assert issue.extra_data.get("method_used") == "jaccard"

    def test_jaccard_similarity_in_extra_data(self, detector):
        """La similitud Jaccard se incluye en extra_data."""
        para = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para obtener resultados estadísticamente significativos en el análisis."
        )
        text = _make_text(para, para)  # Idéntico
        issues = detector.detect(text)
        assert len(issues) >= 1
        assert "jaccard_similarity" in issues[0].extra_data

    def test_confidence_range(self, detector):
        """La confianza del Jaccard está en rango razonable."""
        para = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para obtener resultados estadísticamente significativos en el análisis."
        )
        text = _make_text(para, para)
        issues = detector.detect(text)
        for issue in issues:
            assert 0.65 <= issue.confidence <= 0.85


# ============================================================================
# Tier 2: Embeddings (mocked)
# ============================================================================


class TestEmbeddingsFallback:
    def test_embeddings_used_when_llm_unavailable(self):
        """Si LLM no disponible pero embeddings sí → tier 2."""
        import numpy as np

        detector = CoherenceDetector(CoherenceConfig(enabled=True, use_llm=False))

        # Mock embeddings model
        mock_model = MagicMock()
        # Dos párrafos muy similares → embeddings casi iguales
        emb1 = np.random.randn(384)
        emb1 = emb1 / np.linalg.norm(emb1)
        mock_model.encode.return_value = np.array([emb1, emb1])  # Idénticos

        para = _long_para(
            "La investigación demuestra resultados significativos en el campo "
            "de la inteligencia artificial y el procesamiento de datos complejos."
        )
        text = _make_text(para, para)

        with patch(
            "narrative_assistant.nlp.embeddings.get_embeddings_model",
            return_value=mock_model,
        ):
            # Importar directamente para patchear correctamente
            issues = detector.detect(text)

        # Debería usar embeddings (tier 2) ya que use_llm=False
        assert any(i.extra_data.get("method_used") == "embeddings" for i in issues)

    def test_embeddings_fallback_to_jaccard(self):
        """Si embeddings falla → fallback a Jaccard."""
        detector = CoherenceDetector(CoherenceConfig(enabled=True, use_llm=False))

        # Mock embeddings que lanza excepción
        with patch(
            "narrative_assistant.nlp.embeddings.get_embeddings_model",
            side_effect=ImportError("No model"),
        ):
            para = _long_para(
                "La investigación demuestra resultados significativos en el campo "
                "de la inteligencia artificial y el procesamiento de datos complejos."
            )
            text = _make_text(para, para)
            issues = detector.detect(text)

        # Debería caer a Jaccard
        for issue in issues:
            assert issue.extra_data.get("method_used") == "jaccard"

    def test_embeddings_similarity_in_extra_data(self):
        """La similitud de embeddings se incluye en extra_data."""
        import numpy as np

        detector = CoherenceDetector(CoherenceConfig(enabled=True, use_llm=False))

        mock_model = MagicMock()
        emb = np.ones(384) / np.sqrt(384)
        mock_model.encode.return_value = np.array([emb, emb])

        para = _long_para(
            "La investigación científica avanza continuamente en métodos de análisis "
            "de datos mediante técnicas computacionales modernas y algoritmos."
        )
        text = _make_text(para, para)

        with patch(
            "narrative_assistant.nlp.embeddings.get_embeddings_model",
            return_value=mock_model,
        ):
            issues = detector.detect(text)

        redundant = [
            i for i in issues
            if i.issue_type == CoherenceIssueType.REDUNDANT_PARAGRAPH.value
        ]
        assert len(redundant) >= 1
        assert "similarity" in redundant[0].extra_data

    def test_embeddings_low_similarity_no_issue(self):
        """Párrafos con baja similitud de embeddings → no flaggeados."""
        import numpy as np

        detector = CoherenceDetector(CoherenceConfig(enabled=True, use_llm=False))

        mock_model = MagicMock()
        # Dos embeddings ortogonales (similitud ≈ 0)
        emb1 = np.zeros(384)
        emb1[0] = 1.0
        emb2 = np.zeros(384)
        emb2[1] = 1.0
        mock_model.encode.return_value = np.array([emb1, emb2])

        para1 = _long_para("La astronomía estudia estrellas planetas galaxias universo.")
        para2 = _long_para("La gastronomía combina ingredientes salsas postres cocina.")
        text = _make_text(para1, para2)

        with patch(
            "narrative_assistant.nlp.embeddings.get_embeddings_model",
            return_value=mock_model,
        ):
            issues = detector.detect(text)

        redundant = [
            i for i in issues
            if i.issue_type == CoherenceIssueType.REDUNDANT_PARAGRAPH.value
            and i.extra_data.get("method_used") == "embeddings"
        ]
        assert len(redundant) == 0


# ============================================================================
# Tier 1: LLM (mocked)
# ============================================================================


class TestLLMMocked:
    def _make_mock_llm(self, response_json: dict) -> MagicMock:
        """Crea un mock de LLM client que retorna JSON."""
        mock = MagicMock()
        mock.is_available = True
        mock.complete.return_value = json.dumps(response_json)
        return mock

    def test_llm_detects_redundant(self, llm_detector):
        """LLM detecta párrafos redundantes."""
        llm_response = {
            "issues": [
                {
                    "type": "redundant",
                    "paragraph_indices": [0, 1],
                    "explanation": "Ambos párrafos hablan de lo mismo.",
                    "suggestion": "Fusionar en uno solo.",
                    "confidence": 0.85,
                }
            ]
        }

        mock_client = self._make_mock_llm(llm_response)
        mock_scheduler = MagicMock()

        para = _long_para(
            "La investigación demuestra resultados significativos en inteligencia "
            "artificial y procesamiento de datos complejos con múltiples variables."
        )
        text = _make_text(para, para)

        with (
            patch(
                "narrative_assistant.llm.client.get_llm_client",
                return_value=mock_client,
            ),
            patch(
                "narrative_assistant.llm.client.get_llm_scheduler",
                return_value=mock_scheduler,
            ),
            patch(
                "narrative_assistant.llm.sanitization.sanitize_for_prompt",
                side_effect=lambda t, **kw: t,
            ),
            patch(
                "narrative_assistant.llm.sanitization.validate_llm_response",
                return_value=llm_response,
            ),
        ):
            issues = llm_detector.detect(text)

        assert len(issues) >= 1
        assert issues[0].extra_data.get("method_used") == "llm"
        assert issues[0].issue_type == CoherenceIssueType.REDUNDANT_PARAGRAPH.value

    def test_llm_detects_weak_transition(self, llm_detector):
        """LLM detecta transiciones débiles."""
        llm_response = {
            "issues": [
                {
                    "type": "weak_transition",
                    "paragraph_indices": [1],
                    "explanation": "El segundo párrafo cambia de tema sin transición.",
                    "suggestion": "Añadir conector temático.",
                    "confidence": 0.78,
                }
            ]
        }

        mock_client = self._make_mock_llm(llm_response)

        para1 = _long_para("La metodología empleada se basa en técnicas cuantitativas.")
        para2 = _long_para("Los resultados obtenidos demuestran una correlación positiva.")
        text = _make_text(para1, para2)

        with (
            patch(
                "narrative_assistant.llm.client.get_llm_client",
                return_value=mock_client,
            ),
            patch(
                "narrative_assistant.llm.client.get_llm_scheduler",
                return_value=MagicMock(),
            ),
            patch(
                "narrative_assistant.llm.sanitization.sanitize_for_prompt",
                side_effect=lambda t, **kw: t,
            ),
            patch(
                "narrative_assistant.llm.sanitization.validate_llm_response",
                return_value=llm_response,
            ),
        ):
            issues = llm_detector.detect(text)

        weak = [i for i in issues if i.issue_type == CoherenceIssueType.WEAK_TRANSITION.value]
        assert len(weak) >= 1

    def test_llm_low_confidence_filtered(self, llm_detector):
        """Issues con confianza < 0.70 se filtran."""
        llm_response = {
            "issues": [
                {
                    "type": "redundant",
                    "paragraph_indices": [0, 1],
                    "explanation": "Quizás redundante.",
                    "suggestion": "Revisar.",
                    "confidence": 0.50,  # Demasiado bajo
                }
            ]
        }

        mock_client = self._make_mock_llm(llm_response)

        para = _long_para("La investigación demuestra resultados en inteligencia artificial.")
        text = _make_text(para, para)

        with (
            patch(
                "narrative_assistant.llm.client.get_llm_client",
                return_value=mock_client,
            ),
            patch(
                "narrative_assistant.llm.client.get_llm_scheduler",
                return_value=MagicMock(),
            ),
            patch(
                "narrative_assistant.llm.sanitization.sanitize_for_prompt",
                side_effect=lambda t, **kw: t,
            ),
            patch(
                "narrative_assistant.llm.sanitization.validate_llm_response",
                return_value=llm_response,
            ),
        ):
            issues = llm_detector.detect(text)

        # Issue con confianza 0.50 → filtrado
        assert len(issues) == 0

    def test_llm_unavailable_falls_to_lower_tier(self, llm_detector):
        """Si LLM no disponible → cae a embeddings o Jaccard."""
        mock_client = MagicMock()
        mock_client.is_available = False

        para = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para obtener resultados estadísticamente significativos en el análisis."
        )
        text = _make_text(para, para)

        with patch(
            "narrative_assistant.llm.client.get_llm_client",
            return_value=mock_client,
        ):
            issues = llm_detector.detect(text)

        # Debe haber caído a un tier inferior
        for issue in issues:
            assert issue.extra_data.get("method_used") in ("embeddings", "jaccard")

    def test_llm_invalid_response_falls_to_lower_tier(self, llm_detector):
        """Si LLM retorna respuesta inválida → cae a tier inferior."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.complete.return_value = "this is not json"

        para = _long_para(
            "La metodología experimental utiliza técnicas avanzadas de procesamiento "
            "para obtener resultados estadísticamente significativos en el análisis."
        )
        text = _make_text(para, para)

        with (
            patch(
                "narrative_assistant.llm.client.get_llm_client",
                return_value=mock_client,
            ),
            patch(
                "narrative_assistant.llm.client.get_llm_scheduler",
                return_value=MagicMock(),
            ),
            patch(
                "narrative_assistant.llm.sanitization.sanitize_for_prompt",
                side_effect=lambda t, **kw: t,
            ),
            patch(
                "narrative_assistant.llm.sanitization.validate_llm_response",
                return_value=None,  # Validation fails
            ),
        ):
            issues = llm_detector.detect(text)

        # Should fall to lower tier
        for issue in issues:
            assert issue.extra_data.get("method_used") in ("embeddings", "jaccard")

    def test_llm_no_issues_returned(self, llm_detector):
        """LLM retorna lista vacía de issues → 0 issues."""
        llm_response = {"issues": []}

        mock_client = self._make_mock_llm(llm_response)

        para1 = _long_para("La investigación en astronomía avanza rápidamente con telescopios.")
        para2 = _long_para("Los resultados confirman la existencia de exoplanetas habitables.")
        text = _make_text(para1, para2)

        with (
            patch(
                "narrative_assistant.llm.client.get_llm_client",
                return_value=mock_client,
            ),
            patch(
                "narrative_assistant.llm.client.get_llm_scheduler",
                return_value=MagicMock(),
            ),
            patch(
                "narrative_assistant.llm.sanitization.sanitize_for_prompt",
                side_effect=lambda t, **kw: t,
            ),
            patch(
                "narrative_assistant.llm.sanitization.validate_llm_response",
                return_value=llm_response,
            ),
        ):
            issues = llm_detector.detect(text)

        assert len(issues) == 0


# ============================================================================
# Helpers
# ============================================================================


class TestHelpers:
    def test_split_paragraphs(self, detector):
        """_split_paragraphs divide correctamente por doble newline."""
        text = "Párrafo uno.\n\nPárrafo dos.\n\nPárrafo tres."
        paras = detector._split_paragraphs(text)
        assert len(paras) == 3
        assert paras[0][0] == "Párrafo uno."
        assert paras[1][0] == "Párrafo dos."
        assert paras[2][0] == "Párrafo tres."

    def test_bag_of_words_excludes_stopwords(self, detector):
        """Bag-of-words excluye stopwords comunes."""
        text = "La metodología de análisis en el campo de la investigación es compleja."
        bag = detector._bag_of_words(text)
        assert "metodología" in bag
        assert "análisis" in bag
        assert "compleja" in bag
        # Stopwords excluidas
        assert "la" not in bag
        assert "de" not in bag
        assert "en" not in bag
        assert "el" not in bag

    def test_jaccard_similarity_identical(self, detector):
        """Similitud Jaccard de conjuntos idénticos = 1.0."""
        s = {"a", "b", "c"}
        assert detector._jaccard_similarity(s, s) == 1.0

    def test_jaccard_similarity_disjoint(self, detector):
        """Similitud Jaccard de conjuntos disjuntos = 0.0."""
        assert detector._jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_jaccard_similarity_partial(self, detector):
        """Similitud Jaccard parcial."""
        s1 = {"a", "b", "c", "d"}
        s2 = {"a", "b", "e", "f"}
        # intersection = 2, union = 6 → 2/6 ≈ 0.333
        assert abs(detector._jaccard_similarity(s1, s2) - 2 / 6) < 0.001

    def test_map_llm_issue_type_valid(self, detector):
        """Mapeo de tipos LLM válidos."""
        assert detector._map_llm_issue_type("redundant") == CoherenceIssueType.REDUNDANT_PARAGRAPH.value
        assert detector._map_llm_issue_type("weak_transition") == CoherenceIssueType.WEAK_TRANSITION.value
        assert detector._map_llm_issue_type("topic_discontinuity") == CoherenceIssueType.TOPIC_DISCONTINUITY.value
        assert detector._map_llm_issue_type("merge_suggested") == CoherenceIssueType.MERGE_SUGGESTED.value
        assert detector._map_llm_issue_type("split_suggested") == CoherenceIssueType.SPLIT_SUGGESTED.value

    def test_map_llm_issue_type_invalid(self, detector):
        """Tipo LLM desconocido → None."""
        assert detector._map_llm_issue_type("unknown_type") is None


# ============================================================================
# Config round-trip
# ============================================================================


class TestCoherenceConfigRoundTrip:
    def test_config_in_correction_config_roundtrip(self):
        """CoherenceConfig se serializa y deserializa correctamente."""
        from narrative_assistant.corrections.config import CorrectionConfig

        config = CorrectionConfig()
        config.coherence = CoherenceConfig(
            enabled=True,
            use_llm=True,
            llm_model="mistral",
            fallback_model="llama3.2",
            max_paragraphs=30,
            min_paragraph_words=20,
            temperature=0.3,
        )

        d = config.to_dict()
        restored = CorrectionConfig.from_dict(d)

        assert restored.coherence.enabled is True
        assert restored.coherence.use_llm is True
        assert restored.coherence.llm_model == "mistral"
        assert restored.coherence.fallback_model == "llama3.2"
        assert restored.coherence.max_paragraphs == 30
        assert restored.coherence.min_paragraph_words == 20
        assert restored.coherence.temperature == 0.3
