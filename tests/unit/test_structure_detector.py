"""Tests para ScientificStructureDetector (S18-A5)."""

import pytest

from narrative_assistant.corrections.config import StructureConfig
from narrative_assistant.corrections.detectors.scientific_structure import (
    ScientificStructureDetector,
)
from narrative_assistant.corrections.types import StructureIssueType


@pytest.fixture
def scientific_detector():
    return ScientificStructureDetector(StructureConfig(enabled=True, profile="scientific"))


@pytest.fixture
def essay_detector():
    return ScientificStructureDetector(StructureConfig(enabled=True, profile="essay"))


@pytest.fixture
def technical_detector():
    return ScientificStructureDetector(StructureConfig(enabled=True, profile="technical"))


@pytest.fixture
def disabled_detector():
    return ScientificStructureDetector(StructureConfig(enabled=False))


class TestStructureDetectorBasic:
    def test_disabled_returns_empty(self, disabled_detector):
        issues = disabled_detector.detect("Texto sin estructura.")
        assert issues == []

    def test_category_is_structure(self, scientific_detector):
        from narrative_assistant.corrections.types import CorrectionCategory
        assert scientific_detector.category == CorrectionCategory.STRUCTURE


class TestStructureDetectorScientificProfile:
    def test_complete_document_no_issues(self, scientific_detector):
        text = (
            "## Resumen\nEste artículo...\n\n"
            "## Introducción\nEn este trabajo...\n\n"
            "## Metodología\nSe utilizó...\n\n"
            "## Resultados\nLos resultados...\n\n"
            "## Conclusiones\nEn conclusión...\n\n"
            "## Referencias\n[1] García...\n"
        )
        issues = scientific_detector.detect(text)
        missing = [i for i in issues if i.issue_type == StructureIssueType.MISSING_SECTION.value]
        assert len(missing) == 0

    def test_missing_introduction(self, scientific_detector):
        text = (
            "## Metodología\nSe utilizó...\n\n"
            "## Resultados\nLos resultados...\n\n"
            "## Conclusiones\nEn conclusión...\n\n"
            "## Referencias\n[1] Ref.\n"
        )
        issues = scientific_detector.detect(text)
        missing = [i for i in issues if i.issue_type == StructureIssueType.MISSING_SECTION.value]
        missing_names = [i.extra_data["missing_section"] for i in missing]
        assert "introduction" in missing_names

    def test_missing_methodology(self, scientific_detector):
        text = (
            "## Introducción\nEn este trabajo...\n\n"
            "## Resultados\nLos resultados...\n\n"
            "## Conclusiones\nEn conclusión...\n\n"
            "## Referencias\n[1] Ref.\n"
        )
        issues = scientific_detector.detect(text)
        missing_names = [
            i.extra_data["missing_section"]
            for i in issues
            if i.issue_type == StructureIssueType.MISSING_SECTION.value
        ]
        assert "methodology" in missing_names

    def test_missing_abstract_detected(self, scientific_detector):
        text = (
            "## Introducción\nEn este trabajo...\n\n"
            "## Metodología\nSe utilizó...\n\n"
            "## Resultados\nLos datos...\n\n"
            "## Conclusiones\nEn conclusión...\n\n"
            "## Referencias\n[1] Ref.\n"
        )
        issues = scientific_detector.detect(text)
        abstract = [i for i in issues if i.issue_type == StructureIssueType.MISSING_ABSTRACT.value]
        assert len(abstract) == 1


class TestStructureDetectorEssayProfile:
    def test_essay_needs_fewer_sections(self, essay_detector):
        text = (
            "## Introducción\nEl ensayo trata...\n\n"
            "## Conclusiones\nPor tanto...\n\n"
            "## Referencias\n[1] Fuente.\n"
        )
        issues = essay_detector.detect(text)
        missing = [i for i in issues if i.issue_type == StructureIssueType.MISSING_SECTION.value]
        assert len(missing) == 0  # Solo necesita intro + conclusiones + referencias

    def test_essay_missing_conclusions(self, essay_detector):
        text = (
            "## Introducción\nEl ensayo trata...\n\n"
            "## Referencias\n[1] Fuente.\n"
        )
        issues = essay_detector.detect(text)
        missing_names = [
            i.extra_data["missing_section"]
            for i in issues
            if i.issue_type == StructureIssueType.MISSING_SECTION.value
        ]
        assert "conclusions" in missing_names


class TestStructureDetectorTechnicalProfile:
    def test_technical_minimal_sections(self, technical_detector):
        text = (
            "## Introducción\nEste manual...\n\n"
            "## Referencias\n[1] Doc.\n"
        )
        issues = technical_detector.detect(text)
        missing = [i for i in issues if i.issue_type == StructureIssueType.MISSING_SECTION.value]
        assert len(missing) == 0


class TestStructureDetectorOrder:
    def test_wrong_order_detected(self, scientific_detector):
        text = (
            "## Resultados\nLos datos...\n\n"
            "## Introducción\nEn este trabajo...\n\n"
            "## Metodología\nSe utilizó...\n\n"
            "## Conclusiones\nEn conclusión...\n\n"
            "## Referencias\n[1] Ref.\n"
        )
        issues = scientific_detector.detect(text)
        wrong = [i for i in issues if i.issue_type == StructureIssueType.WRONG_ORDER.value]
        assert len(wrong) >= 1

    def test_correct_order_no_issues(self, scientific_detector):
        text = (
            "## Introducción\nEn este trabajo...\n\n"
            "## Metodología\nSe utilizó...\n\n"
            "## Resultados\nLos datos...\n\n"
            "## Conclusiones\nEn conclusión...\n\n"
            "## Referencias\n[1] Ref.\n"
        )
        issues = scientific_detector.detect(text)
        wrong = [i for i in issues if i.issue_type == StructureIssueType.WRONG_ORDER.value]
        assert len(wrong) == 0


class TestStructureDetectorHeaders:
    def test_detect_numbered_headers(self, scientific_detector):
        text = (
            "1. Introducción\nTexto...\n\n"
            "2. Metodología\nTexto...\n\n"
            "3. Resultados\nTexto...\n\n"
            "4. Conclusiones\nTexto...\n\n"
            "5. Referencias\nTexto...\n"
        )
        issues = scientific_detector.detect(text)
        missing = [i for i in issues if i.issue_type == StructureIssueType.MISSING_SECTION.value]
        assert len(missing) == 0

    def test_detect_spanish_variants(self, scientific_detector):
        """Acepta variantes como 'Materiales y Métodos', 'Discusión'."""
        text = (
            "## Introducción\nTexto...\n\n"
            "## Materiales y Métodos\nTexto...\n\n"
            "## Resultados\nTexto...\n\n"
            "## Discusión\nTexto...\n\n"
            "## Conclusiones\nTexto...\n\n"
            "## Bibliografía\nTexto...\n"
        )
        issues = scientific_detector.detect(text)
        missing = [i for i in issues if i.issue_type == StructureIssueType.MISSING_SECTION.value]
        assert len(missing) == 0
