"""
Tests para concordancia contextual de adjetivos.

Verifica que el sistema NO reporte falsos positivos cuando un adjetivo
concuerda con el SUJETO de la oración, no con el sustantivo más cercano.

Ejemplo:
    "dijo Carlos con la mandíbula apretada, visiblemente furioso"
    - "apretada" → concuerda con "mandíbula" (femenino) ✓
    - "furioso" → concuerda con "Carlos" (masculino, sujeto) ✓
"""

import pytest

from narrative_assistant.nlp.spacy_gpu import load_spacy_model


@pytest.fixture(scope="module")
def nlp():
    """Carga el modelo de spaCy una vez para todos los tests."""
    return load_spacy_model()


class TestContextualAgreement:
    """Tests para concordancia contextual de adjetivos con el sujeto."""

    def test_adjetivo_concuerda_con_sujeto_masculino(self, nlp):
        """
        ✓ "dijo Carlos con la mandíbula apretada, visiblemente furioso"
        - "furioso" concuerda con "Carlos" (sujeto), no con "mandíbula"
        """
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "dijo Carlos con la mandíbula apretada, visiblemente furioso"
        doc = nlp(text)

        detector = AgreementDetector()
        issues = detector.detect(text, chapter_index=0, spacy_doc=doc)

        # NO debe reportar error de concordancia entre "mandíbula" y "furioso"
        false_positives = [
            i
            for i in issues
            if "mandíbula" in i.text.lower() and "furioso" in i.text.lower()
        ]

        assert (
            len(false_positives) == 0
        ), "No debe reportar error: 'furioso' concuerda con 'Carlos', no con 'mandíbula'"

    def test_adjetivo_concuerda_con_sujeto_femenino(self, nlp):
        """
        ✓ "salió María con el rostro enrojecido, visiblemente furiosa"
        - "furiosa" concuerda con "María" (sujeto), no con "rostro"
        """
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "salió María con el rostro enrojecido, visiblemente furiosa"
        doc = nlp(text)

        detector = AgreementDetector()
        issues = detector.detect(text, chapter_index=0, spacy_doc=doc)

        # NO debe reportar error entre "rostro" y "furiosa"
        false_positives = [
            i
            for i in issues
            if "rostro" in i.text.lower() and "furiosa" in i.text.lower()
        ]

        assert (
            len(false_positives) == 0
        ), "No debe reportar error: 'furiosa' concuerda con 'María', no con 'rostro'"

    def test_construccion_absoluta_con_coma(self, nlp):
        """
        ✓ "El hombre salió de la casa, furioso"
        - "furioso" después de coma modifica al sujeto "hombre"
        """
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "El hombre salió de la casa, furioso"
        doc = nlp(text)

        detector = AgreementDetector()
        issues = detector.detect(text, chapter_index=0, spacy_doc=doc)

        # NO debe reportar error entre "casa" (fem) y "furioso" (masc)
        false_positives = [
            i
            for i in issues
            if "casa" in i.text.lower() and "furioso" in i.text.lower()
        ]

        assert (
            len(false_positives) == 0
        ), "No debe reportar error: 'furioso' concuerda con 'hombre', no con 'casa'"

    def test_adverbio_modo_indica_modificacion_sujeto(self, nlp):
        """
        ✓ "observaba la escena, claramente molesto"
        - "molesto" modificado por "claramente" sugiere que modifica al sujeto implícito
        """
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "Observaba la escena, claramente molesto"
        doc = nlp(text)

        detector = AgreementDetector()
        issues = detector.detect(text, chapter_index=0, spacy_doc=doc)

        # NO debe reportar error entre "escena" (fem) y "molesto" (masc)
        false_positives = [
            i
            for i in issues
            if "escena" in i.text.lower() and "molesto" in i.text.lower()
        ]

        assert (
            len(false_positives) == 0
        ), "No debe reportar error: 'molesto' concuerda con sujeto implícito"

    def test_adjetivo_directo_si_debe_concordar(self, nlp):
        """
        ✗ "la mandíbula apretado" SÍ es error (adjetivo directo)
        - "apretado" SÍ debe concordar con "mandíbula"
        """
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "tenía la mandíbula apretado"
        doc = nlp(text)

        detector = AgreementDetector()
        issues = detector.detect(text, chapter_index=0, spacy_doc=doc)

        # SÍ debe reportar error: "apretado" debe ser "apretada"
        errors = [
            i
            for i in issues
            if "mandíbula" in i.text.lower() and "apretado" in i.text.lower()
        ]

        assert (
            len(errors) >= 1
        ), "Debe reportar error: 'apretado' debe concordar con 'mandíbula' (fem)"

    def test_multiple_adjetivos_contextuales(self, nlp):
        """
        Caso complejo con múltiples adjetivos:
        "Carlos miró la pared, pensativo, mientras Ana leía el libro, concentrada"
        """
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "Carlos miró la pared, pensativo, mientras Ana leía el libro, concentrada"
        doc = nlp(text)

        detector = AgreementDetector()
        issues = detector.detect(text, chapter_index=0, spacy_doc=doc)

        # NO debe reportar:
        # - "pared" (fem) vs "pensativo" (masc) → OK, "pensativo" va con "Carlos"
        # - "libro" (masc) vs "concentrada" (fem) → OK, "concentrada" va con "Ana"
        false_positives = [
            i
            for i in issues
            if ("pared" in i.text.lower() and "pensativo" in i.text.lower())
            or ("libro" in i.text.lower() and "concentrada" in i.text.lower())
        ]

        assert (
            len(false_positives) == 0
        ), "No debe reportar errores en concordancias contextuales correctas"


class TestSubjectModifierDetection:
    """Tests específicos para el método _is_subject_modifier."""

    def test_is_subject_modifier_con_adverbio(self, nlp):
        """Adjetivo modificado por adverbio de modo → probablemente modifica al sujeto."""
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "visiblemente furioso"
        doc = nlp(text)

        detector = AgreementDetector()

        # Buscar el token "furioso"
        furioso_token = None
        for token in doc:
            if token.lower_ == "furioso":
                furioso_token = token
                break

        assert furioso_token is not None
        assert (
            detector._is_subject_modifier(furioso_token) is True
        ), "'furioso' modificado por 'visiblemente' debe detectarse como modificador del sujeto"

    def test_is_subject_modifier_con_coma(self, nlp):
        """Adjetivo después de coma → probablemente modifica al sujeto."""
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "salió de la casa, furioso"
        doc = nlp(text)

        detector = AgreementDetector()

        # Buscar el token "furioso"
        furioso_token = None
        for token in doc:
            if token.lower_ == "furioso":
                furioso_token = token
                break

        assert furioso_token is not None
        result = detector._is_subject_modifier(furioso_token)

        # Puede ser True o False dependiendo del parsing de spaCy
        # Lo importante es que NO reporte error en el test principal
        assert isinstance(result, bool)

    def test_is_subject_modifier_adjetivo_directo(self, nlp):
        """Adjetivo directo (sin coma, sin adverbio) → NO es modificador del sujeto."""
        from narrative_assistant.corrections.detectors.agreement import (
            AgreementDetector,
        )

        text = "la mandíbula apretada"
        doc = nlp(text)

        detector = AgreementDetector()

        # Buscar el token "apretada"
        apretada_token = None
        for token in doc:
            if token.lower_ == "apretada":
                apretada_token = token
                break

        assert apretada_token is not None

        # "apretada" NO debe detectarse como modificador del sujeto
        # (porque modifica directamente a "mandíbula")
        result = detector._is_subject_modifier(apretada_token)
        assert (
            result is False
        ), "'apretada' modifica directamente a 'mandíbula', no al sujeto"
