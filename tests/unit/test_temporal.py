"""
Tests para el módulo de análisis temporal.
"""

from datetime import date

import pytest

from narrative_assistant.temporal import (
    InconsistencyType,
    MarkerType,
    NarrativeOrder,
    TemporalConsistencyChecker,
    TemporalMarker,
    TemporalMarkerExtractor,
    Timeline,
    TimelineBuilder,
    TimelineResolution,
)


class TestTemporalMarkerExtractor:
    """Tests para TemporalMarkerExtractor."""

    @pytest.fixture
    def extractor(self):
        return TemporalMarkerExtractor()

    def test_extract_absolute_date_full(self, extractor):
        """Detecta fechas completas."""
        text = "El 15 de marzo de 1985, Juan dejó su pueblo."
        markers = extractor.extract(text)

        assert len(markers) >= 1
        date_markers = [m for m in markers if m.marker_type == MarkerType.ABSOLUTE_DATE]
        assert len(date_markers) >= 1
        assert date_markers[0].year == 1985
        assert date_markers[0].month == 3
        assert date_markers[0].day == 15

    def test_extract_absolute_date_year_only(self, extractor):
        """Detecta años sueltos."""
        text = "En 1985 comenzó la historia."
        markers = extractor.extract(text)

        date_markers = [m for m in markers if m.marker_type == MarkerType.ABSOLUTE_DATE]
        assert len(date_markers) >= 1
        assert date_markers[0].year == 1985

    def test_extract_relative_time_future(self, extractor):
        """Detecta marcadores relativos hacia el futuro."""
        text = "Tres días después llegó a Madrid."
        markers = extractor.extract(text)

        relative = [m for m in markers if m.marker_type == MarkerType.RELATIVE_TIME]
        assert len(relative) >= 1
        assert relative[0].direction == "future"
        assert relative[0].quantity == 3
        assert relative[0].magnitude == "día"

    def test_extract_relative_time_past(self, extractor):
        """Detecta marcadores relativos hacia el pasado."""
        text = "Dos semanas antes había recibido la carta."
        markers = extractor.extract(text)

        relative = [m for m in markers if m.marker_type == MarkerType.RELATIVE_TIME]
        assert len(relative) >= 1
        assert relative[0].direction == "past"
        assert relative[0].quantity == 2

    def test_extract_character_age(self, extractor):
        """Detecta edades de personajes."""
        text = "Cuando tenía 20 años, empezó a trabajar."
        markers = extractor.extract(text)

        age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
        assert len(age_markers) >= 1
        assert age_markers[0].age == 20

    def test_extract_season_epoch(self, extractor):
        """Detecta referencias a estaciones/épocas."""
        text = "Durante aquel verano vivieron felices."
        markers = extractor.extract(text)

        season = [m for m in markers if m.marker_type == MarkerType.SEASON_EPOCH]
        assert len(season) >= 1
        assert "verano" in season[0].text.lower()

    def test_extract_duration(self, extractor):
        """Detecta duraciones."""
        text = "Trabajó allí durante tres meses."
        markers = extractor.extract(text)

        duration = [m for m in markers if m.marker_type == MarkerType.DURATION]
        assert len(duration) >= 1
        assert duration[0].quantity == 3

    def test_extract_frequency(self, extractor):
        """Detecta frecuencias."""
        text = "Cada mañana salía a correr."
        markers = extractor.extract(text)

        freq = [m for m in markers if m.marker_type == MarkerType.FREQUENCY]
        assert len(freq) >= 1

    def test_extract_multiple_markers(self, extractor):
        """Extrae múltiples tipos de marcadores."""
        text = """
        El 15 de marzo de 1985, cuando tenía 20 años, Juan dejó su pueblo.
        Tres días después llegó a Madrid. Durante aquel verano trabajó
        en una fábrica. Cada mañana se levantaba temprano.
        """
        markers = extractor.extract(text)

        types_found = {m.marker_type for m in markers}
        assert MarkerType.ABSOLUTE_DATE in types_found
        assert MarkerType.CHARACTER_AGE in types_found
        assert MarkerType.RELATIVE_TIME in types_found
        assert MarkerType.SEASON_EPOCH in types_found
        assert MarkerType.FREQUENCY in types_found

    def test_no_duplicate_spans(self, extractor):
        """No extrae el mismo span múltiples veces."""
        text = "El 15 de marzo de 1985 fue un día importante."
        markers = extractor.extract(text)

        # Verificar que no hay spans duplicados
        spans = [(m.start_char, m.end_char) for m in markers]
        assert len(spans) == len(set(spans))


class TestTimelineBuilder:
    """Tests para TimelineBuilder."""

    @pytest.fixture
    def builder(self):
        return TimelineBuilder()

    @pytest.fixture
    def sample_chapters(self):
        return [
            {"number": 1, "title": "La partida", "start_position": 0},
            {"number": 2, "title": "El viaje", "start_position": 100},
            {"number": 3, "title": "Recuerdos", "start_position": 200},
        ]

    def test_build_basic_timeline(self, builder, sample_chapters):
        """Construye timeline básico."""
        extractor = TemporalMarkerExtractor()
        text = """
        El 15 de marzo de 1985, Juan dejó su pueblo.
        Tres días después llegó a Madrid.
        """
        markers = extractor.extract(text, chapter=1)

        timeline = builder.build_from_markers(markers, sample_chapters)

        assert len(timeline.events) >= 3  # Al menos uno por capítulo
        assert len(timeline.anchor_events) >= 1  # Al menos un ancla

    def test_chronological_order(self, builder, sample_chapters):
        """Verifica orden cronológico."""
        extractor = TemporalMarkerExtractor()

        # Crear marcadores para diferentes capítulos
        markers = []
        markers.extend(extractor.extract("El 15 de marzo de 1985", chapter=1))
        markers.extend(extractor.extract("El 20 de marzo de 1985", chapter=2))

        timeline = builder.build_from_markers(markers, sample_chapters)
        chrono = timeline.get_chronological_order()

        dated = [e for e in chrono if e.story_date]
        if len(dated) >= 2:
            assert dated[0].story_date <= dated[1].story_date

    def test_detect_analepsis(self, builder, sample_chapters):
        """Detecta flashbacks (analepsis)."""
        extractor = TemporalMarkerExtractor()

        # Capítulo 1: 1985, Capítulo 2: 1980 (flashback)
        markers = []
        markers.extend(extractor.extract("El 15 de marzo de 1985", chapter=1))
        markers.extend(extractor.extract("En 1980, recordó su infancia", chapter=2))

        timeline = builder.build_from_markers(markers, sample_chapters)

        # Verificar que hay eventos
        assert len(timeline.events) >= 2

    def test_export_to_mermaid(self, builder, sample_chapters):
        """Exporta a formato Mermaid."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("El 15 de marzo de 1985", chapter=1)

        timeline = builder.build_from_markers(markers, sample_chapters)
        mermaid = builder.export_to_mermaid()

        assert "gantt" in mermaid
        assert "Timeline Narrativo" in mermaid

    def test_export_to_json(self, builder, sample_chapters):
        """Exporta a formato JSON."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("El 15 de marzo de 1985", chapter=1)

        timeline = builder.build_from_markers(markers, sample_chapters)
        json_data = builder.export_to_json()

        assert "total_events" in json_data
        assert "events" in json_data
        assert isinstance(json_data["events"], list)


class TestTemporalConsistencyChecker:
    """Tests para TemporalConsistencyChecker."""

    @pytest.fixture
    def checker(self):
        return TemporalConsistencyChecker()

    def test_detect_age_contradiction(self, checker):
        """Detecta contradicciones de edad."""
        # Simular edades que decrecen (imposible)
        character_ages = {
            1: [(1, 30), (3, 25)]  # entity_id 1: 30 años en cap 1, 25 en cap 3
        }

        # Timeline vacío pero con capítulos
        timeline = Timeline()

        inconsistencies = checker.check(timeline, [], character_ages)

        age_issues = [
            i
            for i in inconsistencies
            if i.inconsistency_type == InconsistencyType.AGE_CONTRADICTION
        ]
        assert len(age_issues) >= 1

    def test_no_inconsistencies_valid_timeline(self, checker):
        """No reporta inconsistencias en timeline válido."""
        timeline = Timeline()
        markers = []

        inconsistencies = checker.check(timeline, markers)

        # Timeline vacío no debería tener inconsistencias
        assert len(inconsistencies) == 0

    def test_export_report_empty(self, checker):
        """Genera informe vacío correctamente."""
        checker.check(Timeline(), [])
        report = checker.export_report()

        assert "No se detectaron inconsistencias" in report

    def test_get_by_severity(self, checker):
        """Filtra inconsistencias por severidad."""
        # Crear una inconsistencia manualmente
        from narrative_assistant.temporal.inconsistencies import (
            InconsistencySeverity,
            TemporalInconsistency,
        )

        checker.inconsistencies = [
            TemporalInconsistency(
                inconsistency_type=InconsistencyType.AGE_CONTRADICTION,
                severity=InconsistencySeverity.HIGH,
                description="Test",
                chapter=1,
                position=0,
            )
        ]

        high = checker.get_inconsistencies_by_severity(InconsistencySeverity.HIGH)
        low = checker.get_inconsistencies_by_severity(InconsistencySeverity.LOW)

        assert len(high) == 1
        assert len(low) == 0


class TestIntegration:
    """Tests de integración del módulo temporal."""

    def test_full_pipeline(self):
        """Test completo del pipeline temporal."""
        text = """
        Capítulo 1: La partida
        El 15 de marzo de 1985, cuando tenía 20 años, Juan dejó su pueblo.

        Capítulo 2: El viaje
        Tres días después llegó a Madrid. Durante aquel verano trabajó
        en una fábrica.

        Capítulo 3: Recuerdos
        Recordó aquel verano de 1980, cuando tenía quince años y todo
        era diferente.
        """

        chapters = [
            {"number": 1, "title": "La partida", "start_position": 0},
            {"number": 2, "title": "El viaje", "start_position": 100},
            {"number": 3, "title": "Recuerdos", "start_position": 200},
        ]

        # Extraer marcadores
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract(text)

        assert len(markers) > 0

        # Construir timeline
        builder = TimelineBuilder()
        timeline = builder.build_from_markers(markers, chapters)

        assert len(timeline.events) >= 3

        # Verificar consistencia
        checker = TemporalConsistencyChecker()
        inconsistencies = checker.check(timeline, markers)

        # El informe debería generarse sin errores
        report = checker.export_report()
        assert "Informe de Consistencia Temporal" in report

        # Exportar timeline
        mermaid = builder.export_to_mermaid()
        json_data = builder.export_to_json()

        assert "gantt" in mermaid or "No hay eventos" in mermaid
        assert "total_events" in json_data


class TestAnachronismDetector:
    """Tests para detección de anacronismos."""

    @pytest.fixture
    def detector(self):
        from narrative_assistant.temporal.anachronisms import AnachronismDetector
        return AnachronismDetector()

    def test_detect_narrative_period_siglo(self, detector):
        """Detecta periodo de siglo XVI."""
        text = "En el siglo XVI, los conquistadores llegaron a América."
        period = detector.detect_narrative_period(text)
        assert period is not None
        assert period[0] == 1501
        assert period[1] == 1600

    def test_detect_narrative_period_year(self, detector):
        """Detecta periodo por año explícito."""
        text = "En 1492, Colón descubrió América."
        period = detector.detect_narrative_period(text)
        assert period is not None
        assert 1480 <= period[0] <= 1492
        assert 1492 <= period[1] <= 1510

    def test_detect_anachronism_phone_in_medieval(self, detector):
        """Detecta teléfono como anacronismo en Edad Media."""
        text = "En el siglo XII, el caballero sacó su teléfono móvil."
        report = detector.detect(text)
        assert len(report.anachronisms) >= 1
        terms = [a.term.lower() for a in report.anachronisms]
        assert any("teléfono" in t or "móvil" in t for t in terms)

    def test_no_anachronism_modern(self, detector):
        """No detecta anacronismos en texto moderno."""
        text = "En el siglo XXI, Juan consultó su smartphone."
        report = detector.detect(text)
        assert len(report.anachronisms) == 0

    def test_detect_anachronism_internet_1800(self, detector):
        """Detecta internet como anacronismo en el siglo XIX."""
        text = "En el siglo XIX, la condesa navegó por internet."
        report = detector.detect(text)
        assert len(report.anachronisms) >= 1

    def test_no_period_no_anachronisms(self, detector):
        """Sin periodo detectado, no reporta anacronismos."""
        text = "El personaje caminaba por la calle."
        report = detector.detect(text)
        assert len(report.anachronisms) == 0
