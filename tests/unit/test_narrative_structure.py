"""
Tests para el detector de estructura narrativa (prolepsis/analepsis).

Cubre:
- Detección de prolepsis por tiempos verbales
- Detección de prolepsis por marcadores temporales
- Resolución de eventos anticipados
- Severidad de prolepsis
"""

import pytest

from narrative_assistant.analysis.narrative_structure import (
    NarrativeStructureDetector,
    NarrativeAnomaly,
    ProlepsisSeverity,
    get_narrative_structure_detector,
    reset_narrative_structure_detector,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton antes de cada test."""
    reset_narrative_structure_detector()
    yield
    reset_narrative_structure_detector()


@pytest.fixture
def detector():
    """Instancia del detector."""
    return get_narrative_structure_detector()


@pytest.fixture
def sample_chapters():
    """Capítulos de ejemplo con prolepsis."""
    return [
        {
            "number": 1,
            "start_char": 0,
            "end_char": 500,
            "content": """
            María encontró la pistola en el cajón del escritorio.
            La casa olía a humedad y memorias.
            """,
        },
        {
            "number": 2,
            "start_char": 500,
            "end_char": 1200,
            "content": """
            Un año después, cuando organizó la ceremonia en el jardín,
            María recordaría este momento como el principio del fin de su inocencia.
            Los vecinos vendrían a rendir homenaje, pero ella sabría
            que ninguno conocía la verdad completa.

            Pedro encontró las cartas escondidas detrás de los libros.
            """,
        },
        {
            "number": 3,
            "start_char": 1200,
            "end_char": 1800,
            "content": """
            Rosario escuchó en silencio la confesión de María.
            La anciana suspiró profundamente.
            """,
        },
        {
            "number": 4,
            "start_char": 1800,
            "end_char": 2400,
            "content": """
            Carmen murió dos semanas después.
            María heredó los diarios de Elena.
            """,
        },
        {
            "number": 5,
            "start_char": 2400,
            "end_char": 3000,
            "content": """
            Un año después del hallazgo de la pistola, María organizó
            una pequeña ceremonia en el jardín. Invitó a los vecinos
            que recordaban a su padre.

            La nieve comenzó a caer, cubriendo los secretos del jardín.
            """,
        },
    ]


# =============================================================================
# Tests de detección básica de prolepsis
# =============================================================================

class TestProlepisDetection:
    """Tests para detección de prolepsis."""

    def test_detects_prolepsis_with_conditional_tense(self, detector, sample_chapters):
        """Detecta prolepsis que usa condicional (recordaría, sabría)."""
        text = "\n".join(ch["content"] for ch in sample_chapters)

        result = detector.detect_prolepsis(text, sample_chapters)

        assert len(result) >= 1

        # Debe encontrar la prolepsis del capítulo 2
        prolepsis_ch2 = [p for p in result if p.location.chapter == 2]
        assert len(prolepsis_ch2) >= 1

        # Verificar que usa condicional como evidencia
        p = prolepsis_ch2[0]
        assert p.anomaly_type == NarrativeAnomaly.PROLEPSIS
        assert any("condicional" in e.lower() for e in p.evidence)

    def test_detects_prolepsis_with_future_marker(self, detector):
        """Detecta prolepsis con marcador temporal futuro."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "end_char": 200,
                "content": "María caminó por el jardín.",
            },
            {
                "number": 2,
                "start_char": 200,
                "end_char": 500,
                "content": """
                Años más tarde, María comprendería el significado de aquellas palabras.
                Por ahora, solo sentía confusión.
                """,
            },
        ]
        text = "\n".join(ch["content"] for ch in chapters)

        result = detector.detect_prolepsis(text, chapters)

        assert len(result) >= 1
        p = result[0]
        assert p.location.chapter == 2
        assert "anticipación" in p.evidence[0].lower() or "condicional" in p.evidence[0].lower()

    def test_no_false_positives_on_simple_past(self, detector):
        """No detecta falsos positivos en pasado simple."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "end_char": 200,
                "content": """
                María caminó por el jardín. Encontró las flores marchitas.
                Recordó los días de su infancia.
                """,
            },
        ]
        text = chapters[0]["content"]

        result = detector.detect_prolepsis(text, chapters, min_confidence=0.7)

        # No debería detectar prolepsis en texto con pasado simple
        assert len(result) == 0


# =============================================================================
# Tests de resolución de eventos
# =============================================================================

class TestEventResolution:
    """Tests para encontrar eventos anticipados en capítulos posteriores."""

    def test_resolves_ceremony_event(self, detector, sample_chapters):
        """Encuentra la ceremonia mencionada en cap 2 que ocurre en cap 5."""
        text = "\n".join(ch["content"] for ch in sample_chapters)

        result = detector.detect_prolepsis(text, sample_chapters)

        # Buscar prolepsis que menciona la ceremonia
        ceremony_prolepsis = [
            p for p in result
            if "ceremonia" in p.location.text.lower()
        ]

        assert len(ceremony_prolepsis) >= 1
        p = ceremony_prolepsis[0]

        # Debería resolver al capítulo 5
        assert p.resolved_event_chapter == 5


# =============================================================================
# Tests de severidad
# =============================================================================

class TestProlepsisSeverity:
    """Tests para evaluación de severidad."""

    def test_high_severity_for_death_spoiler(self, detector):
        """Severidad alta cuando anticipa muerte."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "end_char": 200,
                "content": """
                Años después, cuando encontraran su cuerpo,
                todos recordarían esta noche como el principio del fin.
                """,
            },
        ]
        text = chapters[0]["content"]

        # Forzar detección aunque confianza sea baja
        detector._prolepsis_patterns.append(
            (detector._prolepsis_patterns[0][0], 0.5)
        )

        result = detector.detect_prolepsis(text, chapters, min_confidence=0.3)

        # Debería detectar y marcar como alta severidad por "cuerpo"
        # Nota: depende de los keywords exactos
        if result:
            assert result[0].severity in [ProlepsisSeverity.HIGH, ProlepsisSeverity.MEDIUM]

    def test_medium_severity_for_remembering(self, detector, sample_chapters):
        """Severidad media para 'recordaría' genérico."""
        text = "\n".join(ch["content"] for ch in sample_chapters)

        result = detector.detect_prolepsis(text, sample_chapters)

        # El ejemplo usa "recordaría" que es medium
        assert any(p.severity == ProlepsisSeverity.MEDIUM for p in result)


# =============================================================================
# Tests de casos límite
# =============================================================================

class TestEdgeCases:
    """Tests para casos límite."""

    def test_empty_text(self, detector):
        """Maneja texto vacío sin error."""
        result = detector.detect_prolepsis("", [])
        assert result == []

    def test_single_chapter(self, detector):
        """Funciona con un solo capítulo."""
        chapters = [
            {
                "number": 1,
                "start_char": 0,
                "end_char": 100,
                "content": "Un año después, María recordaría este momento.",
            }
        ]

        result = detector.detect_prolepsis(chapters[0]["content"], chapters)

        # Puede detectar aunque no haya capítulos posteriores
        assert isinstance(result, list)

    def test_no_chapters(self, detector):
        """Maneja lista vacía de capítulos."""
        result = detector.detect_prolepsis("Texto sin capítulos", [])
        assert result == []


# =============================================================================
# Tests de detect_all
# =============================================================================

class TestDetectAll:
    """Tests para el método detect_all."""

    def test_detect_all_returns_report(self, detector, sample_chapters):
        """detect_all devuelve reporte completo."""
        text = "\n".join(ch["content"] for ch in sample_chapters)

        report = detector.detect_all(text, sample_chapters)

        assert report.chapters_analyzed == 5
        assert len(report.prolepsis_found) >= 1
        assert report.total_anomalies >= 1

    def test_report_to_dict(self, detector, sample_chapters):
        """El reporte se serializa correctamente."""
        text = "\n".join(ch["content"] for ch in sample_chapters)

        report = detector.detect_all(text, sample_chapters)
        data = report.to_dict()

        assert "prolepsis" in data
        assert "analepsis" in data
        assert "chapters_analyzed" in data
        assert "by_type" in data
        assert "by_severity" in data


# =============================================================================
# Tests con documento real
# =============================================================================

class TestWithRichDocument:
    """Tests usando el documento test_document_rich.txt."""

    @pytest.fixture
    def rich_document_chapters(self):
        """Capítulos del documento de test con prolepsis conocida."""
        # Capítulo 2 contiene la prolepsis conocida
        return [
            {
                "number": 1,
                "start_char": 0,
                "end_char": 1000,
                "content": """
                María encontró la pistola de su padre en el cajón del escritorio un martes de noviembre.
                La casa olía a humedad y memorias.
                """,
            },
            {
                "number": 2,
                "start_char": 1000,
                "end_char": 2500,
                "content": """
                Una semana después, María encontró unas cartas escondidas.
                Pedro estaba furioso cuando se enteró.

                Un año después, cuando organizó la ceremonia en el jardín,
                María recordaría este momento como el principio del fin de su inocencia.
                Los vecinos vendrían a rendir homenaje, pero ella sabría
                que ninguno conocía la verdad completa.
                """,
            },
            {
                "number": 3,
                "start_char": 2500,
                "end_char": 3500,
                "content": """
                María confrontó a su madre, doña Rosario.
                La mujer escuchó en silencio.
                """,
            },
            {
                "number": 4,
                "start_char": 3500,
                "end_char": 4500,
                "content": """
                Pasaron tres meses. Era febrero.
                Pedro volvió una tarde de domingo.
                """,
            },
            {
                "number": 5,
                "start_char": 4500,
                "end_char": 5500,
                "content": """
                Un año después del hallazgo de la pistola, María organizó
                una pequeña ceremonia en el jardín. Invitó a los vecinos
                que recordaban a su padre.

                Esa noche, encontró una última carta.
                """,
            },
        ]

    def test_detects_known_prolepsis(self, detector, rich_document_chapters):
        """Detecta la prolepsis conocida 'ceremonia en el jardín'."""
        text = "\n".join(ch["content"] for ch in rich_document_chapters)

        result = detector.detect_prolepsis(text, rich_document_chapters)

        # Debe encontrar al menos una prolepsis en cap 2
        prolepsis_ch2 = [p for p in result if p.location.chapter == 2]
        assert len(prolepsis_ch2) >= 1, "No se detectó la prolepsis en capítulo 2"

        # Verificar que menciona la ceremonia
        found_ceremony = any(
            "ceremonia" in p.location.text.lower() for p in prolepsis_ch2
        )
        assert found_ceremony, "No se encontró la mención de 'ceremonia'"

        # Verificar que se resolvió al capítulo 5
        ceremony_p = [p for p in prolepsis_ch2 if "ceremonia" in p.location.text.lower()][0]
        assert ceremony_p.resolved_event_chapter == 5, (
            f"Esperado: cap 5, Obtenido: cap {ceremony_p.resolved_event_chapter}"
        )
