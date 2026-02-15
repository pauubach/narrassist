"""Tests para la extensión de párrafo en ClarityDetector (S18-A6)."""

import pytest

from narrative_assistant.corrections.config import ClarityConfig
from narrative_assistant.corrections.detectors.clarity import ClarityDetector, ClarityIssueType


@pytest.fixture
def detector():
    return ClarityDetector(ClarityConfig(
        enabled=True,
        detect_paragraph_length=True,
        min_paragraph_sentences=2,
        max_paragraph_sentences=10,
    ))


@pytest.fixture
def disabled_detector():
    return ClarityDetector(ClarityConfig(
        enabled=True,
        detect_paragraph_length=False,
    ))


class TestClarityParagraphLength:
    def test_paragraph_too_short(self, detector):
        """Párrafo con 1 sola oración → flaggeado."""
        text = (
            "Primera parte del ensayo con varias palabras para tener suficiente contenido aquí.\n\n"
            "Esta es una oración solitaria que tiene más de diez palabras para no ser heading.\n\n"
            "Segunda parte del ensayo con más texto para complementar. Y otra oración para que no sea corto."
        )
        issues = detector.detect(text)
        short = [i for i in issues if i.issue_type == ClarityIssueType.PARAGRAPH_TOO_SHORT]
        assert len(short) >= 1

    def test_paragraph_too_long(self, detector):
        """Párrafo con >10 oraciones → flaggeado."""
        sentences = [f"Esta es la oración número {i} del párrafo." for i in range(12)]
        text = " ".join(sentences)
        issues = detector.detect(text)
        long_issues = [i for i in issues if i.issue_type == ClarityIssueType.PARAGRAPH_TOO_LONG]
        assert len(long_issues) >= 1

    def test_normal_paragraph_no_issue(self, detector):
        """Párrafo con 3-8 oraciones → no flaggeado."""
        sentences = [f"Oración número {i} es adecuada." for i in range(5)]
        text = " ".join(sentences)
        issues = detector.detect(text)
        para_issues = [
            i for i in issues
            if i.issue_type in (ClarityIssueType.PARAGRAPH_TOO_SHORT,
                                ClarityIssueType.PARAGRAPH_TOO_LONG)
        ]
        assert len(para_issues) == 0

    def test_heading_not_flagged(self, detector):
        """Líneas cortas (headings) no se flaggean como párrafo corto."""
        text = "Título\n\nPrimera oración del párrafo. Segunda oración del párrafo."
        issues = detector.detect(text)
        short = [i for i in issues if i.issue_type == ClarityIssueType.PARAGRAPH_TOO_SHORT]
        # "Título" es heading (< 10 palabras) → ignorado
        heading_flagged = [i for i in short if "Título" in i.text]
        assert len(heading_flagged) == 0

    def test_disabled_no_paragraph_checks(self, disabled_detector):
        """Con detect_paragraph_length=False, no se chequean párrafos."""
        text = "Oración solitaria."
        issues = disabled_detector.detect(text)
        para_issues = [
            i for i in issues
            if i.issue_type in (ClarityIssueType.PARAGRAPH_TOO_SHORT,
                                ClarityIssueType.PARAGRAPH_TOO_LONG)
        ]
        assert len(para_issues) == 0

    def test_custom_thresholds(self):
        """Umbrales personalizados se respetan."""
        config = ClarityConfig(
            enabled=True,
            detect_paragraph_length=True,
            min_paragraph_sentences=3,
            max_paragraph_sentences=5,
        )
        det = ClarityDetector(config)
        # 2 oraciones → corto con min=3 (texto largo para no ser heading)
        text = (
            "Primera oración del párrafo con suficientes palabras para ser un párrafo real. "
            "Segunda oración del párrafo también con bastantes palabras para evitar filtro."
        )
        issues = det.detect(text)
        short = [i for i in issues if i.issue_type == ClarityIssueType.PARAGRAPH_TOO_SHORT]
        assert len(short) >= 1

    def test_empty_text_no_crash(self, detector):
        issues = detector.detect("")
        assert isinstance(issues, list)

    def test_confidence_paragraph_short(self, detector):
        """Confianza de párrafos cortos es >= 0.75."""
        text = (
            "Una sola oración que tiene suficientes palabras para no ser filtrada como heading por el detector.\n\n"
            "Otra cosa con muchas más palabras de las necesarias. Y más texto. Y aún más texto aquí para complementar."
        )
        issues = detector.detect(text)
        short = [i for i in issues if i.issue_type == ClarityIssueType.PARAGRAPH_TOO_SHORT]
        for issue in short:
            assert issue.confidence >= 0.75
