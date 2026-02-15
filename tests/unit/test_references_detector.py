"""Tests para ReferencesDetector (S18-A3)."""

import pytest

from narrative_assistant.corrections.config import ReferencesConfig
from narrative_assistant.corrections.detectors.references import ReferencesDetector
from narrative_assistant.corrections.types import ReferencesIssueType


@pytest.fixture
def detector():
    return ReferencesDetector(ReferencesConfig(enabled=True))


@pytest.fixture
def disabled_detector():
    return ReferencesDetector(ReferencesConfig(enabled=False))


class TestReferencesDetectorBasic:
    def test_disabled_returns_empty(self, disabled_detector):
        issues = disabled_detector.detect("Texto con cita [1].")
        assert issues == []

    def test_no_citations_flags_issue(self, detector):
        issues = detector.detect("Este es un artículo científico sin ninguna referencia.")
        assert len(issues) == 1
        assert issues[0].issue_type == ReferencesIssueType.NO_CITATIONS.value

    def test_text_with_numeric_citations(self, detector):
        text = (
            "Según estudios previos [1], la técnica es efectiva [2].\n\n"
            "## Referencias\n\n"
            "[1] García, A. (2024). Título. Revista.\n"
            "[2] López, B. (2023). Otro título. Conferencia.\n"
        )
        issues = detector.detect(text)
        # Con bibliografía y citas → no hay issues graves
        no_cit = [i for i in issues if i.issue_type == ReferencesIssueType.NO_CITATIONS.value]
        no_bib = [i for i in issues if i.issue_type == ReferencesIssueType.NO_BIBLIOGRAPHY.value]
        assert len(no_cit) == 0
        assert len(no_bib) == 0


class TestReferencesDetectorFormats:
    def test_detect_numeric_cite_simple(self, detector):
        text = "Esto se demostró [1].\n\n## Referencias\n[1] Ref."
        issues = detector.detect(text)
        assert not any(i.issue_type == ReferencesIssueType.NO_CITATIONS.value for i in issues)

    def test_detect_numeric_cite_range(self, detector):
        text = "Varios estudios [1-3] confirman esto.\n\n## Bibliografía\n[1] A.\n[2] B.\n[3] C."
        issues = detector.detect(text)
        assert not any(i.issue_type == ReferencesIssueType.NO_CITATIONS.value for i in issues)

    def test_detect_author_year_parenthetical(self, detector):
        text = "La teoría (García, 2024) es relevante.\n\n## Referencias\nGarcía, A. (2024)."
        issues = detector.detect(text)
        assert not any(i.issue_type == ReferencesIssueType.NO_CITATIONS.value for i in issues)

    def test_detect_author_year_inline(self, detector):
        text = "García (2024) demostró que...\n\n## Referencias\nGarcía, A. (2024)."
        issues = detector.detect(text)
        assert not any(i.issue_type == ReferencesIssueType.NO_CITATIONS.value for i in issues)

    def test_detect_author_et_al(self, detector):
        text = "Según García et al. (2024), el resultado...\n\n## Referencias\nGarcía et al."
        issues = detector.detect(text)
        assert not any(i.issue_type == ReferencesIssueType.NO_CITATIONS.value for i in issues)


class TestReferencesDetectorMixedFormat:
    def test_mixed_format_detected(self, detector):
        text = (
            "Según [1], el resultado es positivo. García (2024) lo confirma.\n\n"
            "## Referencias\n[1] Ref."
        )
        issues = detector.detect(text)
        mixed = [i for i in issues if i.issue_type == ReferencesIssueType.MIXED_FORMAT.value]
        assert len(mixed) == 1
        assert mixed[0].confidence == 0.90

    def test_single_format_no_mixed_issue(self, detector):
        text = "Estudios [1] y [2] confirman.\n\n## Referencias\n[1] A.\n[2] B."
        issues = detector.detect(text)
        mixed = [i for i in issues if i.issue_type == ReferencesIssueType.MIXED_FORMAT.value]
        assert len(mixed) == 0


class TestReferencesDetectorBibliography:
    def test_no_bibliography_detected(self, detector):
        text = "Según [1], esto es importante. También [2] y [3]."
        issues = detector.detect(text)
        no_bib = [i for i in issues if i.issue_type == ReferencesIssueType.NO_BIBLIOGRAPHY.value]
        assert len(no_bib) == 1
        assert no_bib[0].confidence == 0.92

    def test_bibliography_with_different_headers(self, detector):
        for header in ["## Referencias", "## Bibliografía", "## Bibliography",
                       "## References", "## Fuentes"]:
            text = f"Cita [1].\n\n{header}\n[1] Ref."
            issues = detector.detect(text)
            no_bib = [i for i in issues if i.issue_type == ReferencesIssueType.NO_BIBLIOGRAPHY.value]
            assert len(no_bib) == 0, f"Failed for header: {header}"


class TestReferencesDetectorOrphanCitations:
    def test_orphan_citation_detected(self, detector):
        text = (
            "Según [1] y [5], la técnica funciona.\n\n"
            "## Referencias\n"
            "[1] García, A. (2024). Título.\n"
        )
        issues = detector.detect(text)
        orphans = [i for i in issues if i.issue_type == ReferencesIssueType.ORPHAN_CITATION.value]
        # [5] is orphan
        assert len(orphans) >= 1
        assert any("5" in i.extra_data.get("citation_number", "") for i in orphans)

    def test_no_orphans_when_all_present(self, detector):
        text = (
            "Cita [1] y [2].\n\n"
            "## Referencias\n"
            "[1] García. Título.\n"
            "[2] López. Otro.\n"
        )
        issues = detector.detect(text)
        orphans = [i for i in issues if i.issue_type == ReferencesIssueType.ORPHAN_CITATION.value]
        assert len(orphans) == 0

    def test_config_disable_orphan_detection(self):
        config = ReferencesConfig(enabled=True, detect_orphan_citations=False)
        det = ReferencesDetector(config)
        text = "Según [99].\n\n## Referencias\n[1] Ref."
        issues = det.detect(text)
        orphans = [i for i in issues if i.issue_type == ReferencesIssueType.ORPHAN_CITATION.value]
        assert len(orphans) == 0

    def test_orphan_detection_expands_ranges(self, detector):
        text = (
            "Resultados previos [1-3] respaldan la hipótesis.\n\n"
            "## Referencias\n"
            "[1] García, A. (2024). Título.\n"
            "[3] López, B. (2023). Otro título.\n"
        )
        issues = detector.detect(text)
        orphans = [i for i in issues if i.issue_type == ReferencesIssueType.ORPHAN_CITATION.value]
        assert any(i.extra_data.get("citation_number") == "2" for i in orphans)


class TestReferencesDetectorUnusedReferences:
    def test_unused_reference_detected(self):
        """Entrada en bibliografía sin cita en texto → flaggeada."""
        config = ReferencesConfig(enabled=True, detect_unused_references=True)
        det = ReferencesDetector(config)
        text = (
            "Según [1], esto es importante.\n\n"
            "## Referencias\n"
            "[1] García. Estudio.\n"
            "[2] López. Análisis.\n"  # No citado
        )
        issues = det.detect(text)
        unused = [i for i in issues if i.issue_type == ReferencesIssueType.UNUSED_REFERENCE.value]
        assert len(unused) == 1
        assert unused[0].text == "[2]"

    def test_all_references_cited_no_issue(self):
        """Todas las entradas citadas → sin issue."""
        config = ReferencesConfig(enabled=True, detect_unused_references=True)
        det = ReferencesDetector(config)
        text = (
            "Según [1] y [2].\n\n"
            "## Referencias\n"
            "[1] García. Estudio.\n"
            "[2] López. Análisis.\n"
        )
        issues = det.detect(text)
        unused = [i for i in issues if i.issue_type == ReferencesIssueType.UNUSED_REFERENCE.value]
        assert len(unused) == 0

    def test_config_disable_unused_detection(self):
        """Con detect_unused_references=False, no se chequea."""
        config = ReferencesConfig(enabled=True, detect_unused_references=False)
        det = ReferencesDetector(config)
        text = (
            "Según [1].\n\n"
            "## Referencias\n"
            "[1] García.\n"
            "[2] López.\n"
        )
        issues = det.detect(text)
        unused = [i for i in issues if i.issue_type == ReferencesIssueType.UNUSED_REFERENCE.value]
        assert len(unused) == 0

    def test_range_citation_marks_middle_reference_as_used(self):
        """[1-3] cuenta 1, 2 y 3 como citadas (sin falsos UNUSED_REFERENCE)."""
        config = ReferencesConfig(enabled=True, detect_unused_references=True)
        det = ReferencesDetector(config)
        text = (
            "Varios estudios [1-3] confirman el resultado.\n\n"
            "## Referencias\n"
            "[1] García.\n"
            "[2] López.\n"
            "[3] Pérez.\n"
        )
        issues = det.detect(text)
        unused = [i for i in issues if i.issue_type == ReferencesIssueType.UNUSED_REFERENCE.value]
        assert len(unused) == 0
