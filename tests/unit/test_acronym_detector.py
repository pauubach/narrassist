"""Tests para AcronymDetector (S18-A4)."""

import pytest

from narrative_assistant.corrections.config import AcronymConfig
from narrative_assistant.corrections.detectors.acronyms import AcronymDetector
from narrative_assistant.corrections.types import AcronymIssueType


@pytest.fixture
def detector():
    return AcronymDetector(AcronymConfig(enabled=True))


@pytest.fixture
def disabled_detector():
    return AcronymDetector(AcronymConfig(enabled=False))


class TestAcronymDetectorBasic:
    def test_disabled_returns_empty(self, disabled_detector):
        issues = disabled_detector.detect("Se usó PLN sin definir.")
        assert issues == []

    def test_defined_before_use_no_issue(self, detector):
        text = "Procesamiento de Lenguaje Natural (PLN) es una disciplina. PLN se aplica en muchos campos."
        issues = detector.detect(text)
        undefined = [i for i in issues if i.issue_type == AcronymIssueType.UNDEFINED_ACRONYM.value]
        assert len(undefined) == 0

    def test_undefined_acronym_detected(self, detector):
        text = "El sistema usa PLN para procesar datos. Además emplea NER para extraer entidades."
        issues = detector.detect(text)
        undefined = [i for i in issues if i.issue_type == AcronymIssueType.UNDEFINED_ACRONYM.value]
        acronyms_found = {i.text for i in undefined}
        assert "PLN" in acronyms_found
        assert "NER" in acronyms_found


class TestAcronymDetectorKnown:
    def test_known_acronym_no_issue(self, detector):
        """Siglas universales (EEUU, ONU, etc.) no necesitan definición."""
        text = "La ONU declaró que EEUU participaría en la conferencia de la UE."
        issues = detector.detect(text)
        undefined = [i for i in issues if i.issue_type == AcronymIssueType.UNDEFINED_ACRONYM.value]
        known_flagged = [i for i in undefined if i.text in ("ONU", "EEUU", "UE")]
        assert len(known_flagged) == 0

    def test_custom_known_acronyms(self):
        config = AcronymConfig(
            enabled=True,
            known_acronyms=["PLN", "NER"],
        )
        det = AcronymDetector(config)
        text = "Se usó PLN y NER en el estudio."
        issues = det.detect(text)
        undefined = [i for i in issues if i.issue_type == AcronymIssueType.UNDEFINED_ACRONYM.value]
        assert len(undefined) == 0


class TestAcronymDetectorLateDefinition:
    def test_late_definition_detected(self, detector):
        text = (
            "El PLN ha avanzado mucho en los últimos años. "
            "Procesamiento de Lenguaje Natural (PLN) se define como..."
        )
        issues = detector.detect(text)
        late = [i for i in issues if i.issue_type == AcronymIssueType.LATE_DEFINITION.value]
        assert len(late) == 1
        assert late[0].text == "PLN"


class TestAcronymDetectorRedefinition:
    def test_redefined_acronym_detected(self, detector):
        text = (
            "Procesamiento de Lenguaje Natural (PLN) es importante. "
            "Programación Lógica Numérica (PLN) también existe."
        )
        issues = detector.detect(text)
        redef = [i for i in issues if i.issue_type == AcronymIssueType.REDEFINED_ACRONYM.value]
        assert len(redef) == 1
        assert redef[0].confidence == 0.90

    def test_same_definition_twice_no_redefine(self, detector):
        text = (
            "Procesamiento de Lenguaje Natural (PLN) es importante. "
            "El Procesamiento de Lenguaje Natural (PLN) tiene muchas aplicaciones."
        )
        issues = detector.detect(text)
        redef = [i for i in issues if i.issue_type == AcronymIssueType.REDEFINED_ACRONYM.value]
        assert len(redef) == 0


class TestAcronymDetectorFiltering:
    def test_short_words_not_flagged(self, detector):
        """Palabras de 1 letra en mayúscula no son siglas."""
        text = "El punto A está lejos del punto B."
        issues = detector.detect(text)
        # "A" y "B" son muy cortas (< min_acronym_length=2)
        assert len(issues) == 0

    def test_false_acronyms_filtered(self, detector):
        """Artículos y preposiciones en mayúscula no son siglas."""
        text = "EL PRESIDENTE DE LA REPÚBLICA."
        issues = detector.detect(text)
        undefined = [i for i in issues if i.issue_type == AcronymIssueType.UNDEFINED_ACRONYM.value]
        # EL, DE, LA should be filtered
        false_flagged = [i for i in undefined if i.text in ("EL", "DE", "LA")]
        assert len(false_flagged) == 0

    def test_reverse_definition_format(self, detector):
        """PLN (Procesamiento de Lenguaje Natural) también es definición válida."""
        text = "PLN (Procesamiento de Lenguaje Natural) se usa ampliamente. PLN mejora cada año."
        issues = detector.detect(text)
        undefined = [i for i in issues if i.issue_type == AcronymIssueType.UNDEFINED_ACRONYM.value]
        pln_undefined = [i for i in undefined if i.text == "PLN"]
        assert len(pln_undefined) == 0

    def test_max_acronym_length(self):
        config = AcronymConfig(enabled=True, max_acronym_length=4)
        det = AcronymDetector(config)
        text = "ABCDE se usa mucho en este contexto."
        issues = det.detect(text)
        # ABCDE tiene 5 letras > max 4, no debería ser flaggeado
        undefined = [i for i in issues if i.text == "ABCDE"]
        assert len(undefined) == 0

    def test_category_is_acronyms(self, detector):
        from narrative_assistant.corrections.types import CorrectionCategory
        assert detector.category == CorrectionCategory.ACRONYMS


class TestAcronymDetectorInconsistentForm:
    def test_inconsistent_form_detected(self, detector):
        """NLP y N.L.P. en el mismo texto → inconsistent_form."""
        text = (
            "Procesamiento de Lenguaje Natural (NLP) es un campo activo. "
            "También se escribe N.L.P. en algunos textos."
        )
        issues = detector.detect(text)
        inconsistent = [
            i for i in issues if i.issue_type == AcronymIssueType.INCONSISTENT_FORM.value
        ]
        assert len(inconsistent) == 1
        assert inconsistent[0].confidence == 0.82

    def test_only_dotted_no_inconsistency(self, detector):
        """Solo forma con puntos, sin forma plain → no es inconsistente."""
        text = "La O.N.U. organizó la conferencia internacional."
        issues = detector.detect(text)
        inconsistent = [
            i for i in issues if i.issue_type == AcronymIssueType.INCONSISTENT_FORM.value
        ]
        assert len(inconsistent) == 0

    def test_only_plain_no_inconsistency(self, detector):
        """Solo forma sin puntos → no es inconsistente."""
        text = "Procesamiento de Lenguaje Natural (NLP) es útil. NLP avanza rápido."
        issues = detector.detect(text)
        inconsistent = [
            i for i in issues if i.issue_type == AcronymIssueType.INCONSISTENT_FORM.value
        ]
        assert len(inconsistent) == 0
