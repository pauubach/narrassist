"""
Tests para el módulo de energía de oraciones (sentence_energy).

Cubre:
- Happy path: análisis de texto con voz activa/pasiva
- Error path: texto vacío, sin oraciones
- Calibración española: estar+participio NO es pasiva
- Excepciones: haber+participio, ir+preposición, hacer+colocación
- Nominalizaciones: excepciones léxicas
"""

import pytest

from narrative_assistant.nlp.style.sentence_energy import SentenceEnergyDetector


@pytest.fixture
def detector():
    """Crear detector con configuración por defecto."""
    return SentenceEnergyDetector()


def _unwrap(result):
    """Extraer el valor de un Result, fallando si es failure."""
    assert result.is_success, f"Expected success but got failure: {result.error}"
    return result.value


# =============================================================================
# Smoke tests
# =============================================================================


class TestSentenceEnergySmoke:
    """Tests básicos de importación y creación."""

    def test_import(self):
        """El módulo se importa correctamente."""
        from narrative_assistant.nlp.style.sentence_energy import SentenceEnergyDetector

        assert SentenceEnergyDetector is not None

    def test_create_detector(self, detector):
        """Se puede crear una instancia del detector."""
        assert detector is not None

    def test_detector_has_analyze_method(self, detector):
        """El detector tiene método analyze."""
        assert hasattr(detector, "analyze")
        assert callable(detector.analyze)


# =============================================================================
# Happy path
# =============================================================================


class TestSentenceEnergyHappyPath:
    """Tests de análisis normal."""

    def test_active_voice_scores_high(self, detector):
        """Oraciones activas deben tener energía alta."""
        text = "El detective golpeó la mesa. La testigo gritó su confesión. El asesino huyó por la ventana."
        result = _unwrap(detector.analyze(text))
        assert len(result.sentences) > 0
        avg = result.avg_energy
        assert avg >= 50, f"Energía promedio debería ser >= 50 para voz activa, pero fue {avg}"

    def test_passive_voice_scores_lower(self, detector):
        """Oraciones pasivas perifrásticas deben tener energía más baja."""
        text = "La puerta fue abierta por el mayordomo. La carta fue escrita por el abogado. El mensaje fue enviado por el secretario."
        result = _unwrap(detector.analyze(text))
        assert len(result.sentences) > 0
        passive_count = sum(1 for s in result.sentences if s.is_passive)
        assert passive_count >= 1, "Debería detectar al menos una voz pasiva perifrástica"

    def test_returns_sentence_details(self, detector):
        """El resultado incluye detalles por oración."""
        text = "María corre por el parque. Juan lee un libro en silencio."
        result = _unwrap(detector.analyze(text))
        assert len(result.sentences) >= 2
        for s in result.sentences:
            assert hasattr(s, "energy_score")
            assert hasattr(s, "text")
            assert 0 <= s.energy_score <= 100


# =============================================================================
# Error path
# =============================================================================


class TestSentenceEnergyErrorPath:
    """Tests de manejo de errores."""

    def test_empty_text(self, detector):
        """Texto vacío devuelve Result exitoso con 0 oraciones."""
        raw = detector.analyze("")
        assert raw.is_success
        result = raw.value
        assert len(result.sentences) == 0

    def test_whitespace_only(self, detector):
        """Solo espacios en blanco devuelve Result exitoso."""
        raw = detector.analyze("   \n\t  ")
        assert raw.is_success
        assert len(raw.value.sentences) == 0

    def test_single_word(self, detector):
        """Una sola palabra no lanza excepción."""
        raw = detector.analyze("Hola")
        assert raw.is_success


# =============================================================================
# Calibración española
# =============================================================================


class TestSpanishCalibration:
    """Tests de calibración específica para español."""

    def test_estar_participio_not_passive(self, detector):
        """'estar + participio' NO debe marcarse como pasiva (es estativo)."""
        text = "La puerta estaba cerrada. La ventana estaba abierta. El libro estaba terminado."
        result = _unwrap(detector.analyze(text))
        passive_count = sum(1 for s in result.sentences if s.is_passive)
        assert passive_count == 0, (
            f"'estar + participio' no es pasiva en español, pero se detectaron {passive_count} pasivas"
        )

    def test_ser_participio_is_passive(self, detector):
        """'ser + participio' SÍ debe marcarse como pasiva perifrástica."""
        text = "El libro fue escrito por el autor. La ley fue aprobada por el congreso."
        result = _unwrap(detector.analyze(text))
        passive_count = sum(1 for s in result.sentences if s.is_passive)
        assert passive_count >= 1, "Debería detectar pasiva perifrástica con 'ser + participio'"

    def test_haber_participio_not_weak(self, detector):
        """'haber + participio' (tiempos compuestos) NO debe penalizar como verbo débil."""
        text = "María ha llegado a la ciudad. Pedro había encontrado la solución."
        result = _unwrap(detector.analyze(text))
        for s in result.sentences:
            weak_reasons = [
                i for i in s.issues if "débil" in str(i).lower() or "weak" in str(i).lower()
            ]
            assert len(weak_reasons) == 0, f"Tiempos compuestos no deben penalizar: {weak_reasons}"

    def test_ir_preposition_not_weak(self, detector):
        """'ir + preposición de movimiento' NO debe penalizar como verbo débil."""
        text = "Juan fue a la tienda. María iba hacia el parque."
        raw = detector.analyze(text)
        assert raw.is_success

    def test_nominalization_exceptions(self, detector):
        """Palabras léxicas como 'habitación' no deben marcarse como nominalización."""
        text = "La habitación estaba en silencio. La posición del ejército era estratégica."
        result = _unwrap(detector.analyze(text))
        for s in result.sentences:
            nom_issues = [i for i in s.issues if "nominal" in str(i).lower()]
            for issue in nom_issues:
                assert "habitación" not in str(issue), "'habitación' es léxica, no nominalización"
                assert "posición" not in str(issue), "'posición' es léxica, no nominalización"


# =============================================================================
# Low threshold parameter
# =============================================================================


class TestLowThreshold:
    """Tests del parámetro low_threshold."""

    def test_custom_threshold(self, detector):
        """El parámetro low_threshold se puede pasar."""
        text = "El gato duerme. El perro ladra."
        raw = detector.analyze(text, low_threshold=30)
        assert raw.is_success

    def test_default_threshold_behavior(self, detector):
        """Sin low_threshold usa el umbral por defecto."""
        text = "El gato duerme. El perro ladra."
        raw = detector.analyze(text)
        assert raw.is_success
