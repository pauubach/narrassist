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

    def test_extract_with_entities_sets_temporal_instance_id(self, extractor):
        """Si hay entidad+edad, se genera temporal_instance_id estable."""
        text = "Juan, a los 40 años, volvió al pueblo."
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(1, 0, 4)],  # (entity_id, start, end)
            chapter=1,
        )

        age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
        assert len(age_markers) >= 1
        assert age_markers[0].entity_id == 1
        assert age_markers[0].temporal_instance_id == "1@age:40"

    def test_extract_character_age_from_recien_cumplidos(self, extractor):
        """Parsea correctamente patrones con grupos opcionales: 'recién cumplidos los X'."""
        text = "Recién cumplidos los 41, Ana se mudó de ciudad."
        markers = extractor.extract(text)

        age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
        assert len(age_markers) >= 1
        assert any(m.age == 41 for m in age_markers)

    def test_extract_with_entities_sets_phase_instance_id(self, extractor):
        """Sin edad numérica, 'de joven' genera instancia temporal estable por fase."""
        text = "Ana, de joven, soñaba con viajar en el tiempo."
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(2, 0, 3)],
            chapter=1,
        )

        age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
        assert len(age_markers) >= 1

        young_marker = next((m for m in age_markers if "joven" in m.text.lower()), None)
        assert young_marker is not None
        assert young_marker.age is None
        assert young_marker.age_phase == "young"
        assert young_marker.temporal_instance_id == "2@phase:young"

    def test_extract_with_entities_infers_phase_from_adjacent_mention(self, extractor):
        """Infiere fase implícita en adjetivo pegado a la mención ('joven Juan')."""
        text = "El joven Juan habló con el viejo Juan."
        first = text.find("Juan")
        second = text.find("Juan", first + 1)
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(1, first, first + 4), (1, second, second + 4)],
            chapter=1,
        )

        age_markers = [m for m in markers if m.marker_type == MarkerType.CHARACTER_AGE]
        instances = {m.temporal_instance_id for m in age_markers if m.temporal_instance_id}
        assert "1@phase:young" in instances
        assert "1@phase:elder" in instances

    def test_extract_with_entities_infers_relative_offset_instance(self, extractor):
        """Infiere instancia temporal por desfase relativo ('dentro de 5 años')."""
        text = "Juan se encontró con su yo de dentro de 5 años."
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(1, 0, 4)],
            chapter=1,
        )

        offset_marker = next(
            (m for m in markers if m.temporal_instance_id == "1@offset_years:+5"),
            None,
        )
        assert offset_marker is not None
        assert offset_marker.relative_year_offset == 5

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

    def test_export_to_json_includes_day_offset_and_weekday(self, builder, sample_chapters):
        """export_to_json incluye day_offset y weekday en cada evento."""
        extractor = TemporalMarkerExtractor()
        markers = extractor.extract("El 15 de marzo de 1985", chapter=1)

        builder.build_from_markers(markers, sample_chapters)
        json_data = builder.export_to_json()

        for event in json_data["events"]:
            assert "day_offset" in event
            assert "weekday" in event

    def test_temporal_instance_id_propagates_to_events_and_json(self, builder, sample_chapters):
        """La instancia temporal detectada viaja a eventos operativos y export JSON."""
        marker = TemporalMarker(
            text="a los 40 años",
            marker_type=MarkerType.CHARACTER_AGE,
            start_char=5,
            end_char=18,
            chapter=1,
            entity_id=1,
            age=40,
            temporal_instance_id="1@age:40",
            confidence=0.9,
        )

        timeline = builder.build_from_markers([marker], sample_chapters)

        assert any(
            event.temporal_instance_id == "1@age:40" for event in timeline.events
        )

        chapter_event = next(e for e in timeline.events if e.chapter == 1 and e.paragraph == 0)
        assert chapter_event.temporal_instance_id == "1@age:40"

        json_data = builder.export_to_json()
        assert any(
            event.get("temporal_instance_id") == "1@age:40" for event in json_data["events"]
        )

    def test_phase_instance_without_numeric_age_creates_timeline_event(
        self, builder, sample_chapters
    ):
        """Marcadores por fase implícita deben crear evento aunque no haya edad numérica."""
        marker = TemporalMarker(
            text="joven Juan",
            marker_type=MarkerType.CHARACTER_AGE,
            start_char=3,
            end_char=13,
            chapter=1,
            entity_id=1,
            age_phase="young",
            temporal_instance_id="1@phase:young",
            confidence=0.7,
        )

        timeline = builder.build_from_markers([marker], sample_chapters)
        assert any(
            event.temporal_instance_id == "1@phase:young" for event in timeline.events
        )

    def test_extreme_offset_no_crash(self, builder, sample_chapters):
        """Offsets extremos no provocan crash (OverflowError)."""
        # Ancla con fecha absoluta
        anchor = TemporalMarker(
            text="1 de enero de 9990",
            marker_type=MarkerType.ABSOLUTE_DATE,
            chapter=1,
            start_char=0,
            end_char=20,
            year=9990,
            month=1,
            day=1,
            confidence=0.9,
        )
        # Marcador relativo extremo: 100.000 años después
        # Esto provocaría OverflowError en date sin protección
        extreme = TemporalMarker(
            text="cien mil años después",
            marker_type=MarkerType.RELATIVE_TIME,
            chapter=2,
            start_char=100,
            end_char=130,
            direction="future",
            quantity=100_000,
            magnitude="año",
            confidence=0.7,
        )
        # No debe crashear
        timeline = builder.build_from_markers([anchor, extreme], sample_chapters)
        assert len(timeline.events) >= 1

    def test_extreme_day_offset_clamped(self, builder, sample_chapters):
        """day_offset se limita a ±365.000."""
        from narrative_assistant.temporal.timeline import MAX_DAY_OFFSET

        # Ancla relativa (generará day_offset=0 como sintético)
        anchor = TemporalMarker(
            text="aquella mañana",
            marker_type=MarkerType.RELATIVE_TIME,
            chapter=1,
            start_char=0,
            end_char=14,
            confidence=0.9,
        )
        # Relativo extremo: 500.000 días (~1370 años) → debe clamparse
        extreme = TemporalMarker(
            text="quinientos mil días después",
            marker_type=MarkerType.RELATIVE_TIME,
            chapter=2,
            start_char=100,
            end_char=140,
            direction="future",
            quantity=500_000,
            magnitude="día",
            confidence=0.7,
        )
        timeline = builder.build_from_markers([anchor, extreme], sample_chapters)
        offsets = [e.day_offset for e in timeline.events if e.day_offset is not None]
        for off in offsets:
            assert abs(off) <= MAX_DAY_OFFSET, (
                f"day_offset {off} excede el límite ±{MAX_DAY_OFFSET}"
            )


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


class TestTemporalInstanceEdgeCases:
    """Tests de gaps de cobertura para instancias temporales."""

    @pytest.fixture
    def extractor(self):
        return TemporalMarkerExtractor()

    @pytest.fixture
    def builder(self):
        return TimelineBuilder()

    @pytest.fixture
    def sample_chapters(self):
        return [
            {"number": 1, "title": "Cap 1", "content": "Texto del capítulo 1.", "start_position": 0},
            {"number": 2, "title": "Cap 2", "content": "Texto del capítulo 2.", "start_position": 100},
        ]

    def test_negative_offset_hace_n_anios(self, extractor):
        """'hace 5 años' genera offset negativo -5."""
        text = "Juan recordaba lo que pasó hace 5 años."
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(1, 0, 4)],
            chapter=1,
        )
        offset_marker = next(
            (m for m in markers if getattr(m, "relative_year_offset", None) is not None),
            None,
        )
        assert offset_marker is not None
        assert offset_marker.relative_year_offset == -5
        assert offset_marker.temporal_instance_id == "1@offset_years:-5"

    def test_negative_offset_anios_atras(self, extractor):
        """'3 años atrás' genera offset negativo -3."""
        text = "María, 3 años atrás, vivía en otra ciudad."
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(2, 0, 5)],
            chapter=1,
        )
        offset_marker = next(
            (m for m in markers if getattr(m, "relative_year_offset", None) is not None),
            None,
        )
        assert offset_marker is not None
        assert offset_marker.relative_year_offset == -3
        assert offset_marker.temporal_instance_id == "2@offset_years:-3"

    def test_pequeno_as_phase(self, extractor):
        """'pequeño Juan' genera instancia @phase:child (B1 fix)."""
        text = "El pequeño Juan corría por los campos."
        first_juan = text.find("Juan")
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(1, first_juan, first_juan + 4)],
            chapter=1,
        )
        instances = {
            m.temporal_instance_id
            for m in markers
            if m.temporal_instance_id
        }
        assert "1@phase:child" in instances

    def test_multiple_instances_same_chapter(self, builder, sample_chapters):
        """Dos instancias distintas en el mismo capítulo: no se asigna al evento base."""
        marker_a = TemporalMarker(
            text="a los 40", marker_type=MarkerType.CHARACTER_AGE,
            start_char=0, end_char=8, chapter=1, entity_id=1,
            age=40, temporal_instance_id="1@age:40", confidence=0.9,
        )
        marker_b = TemporalMarker(
            text="a los 20", marker_type=MarkerType.CHARACTER_AGE,
            start_char=50, end_char=58, chapter=1, entity_id=1,
            age=20, temporal_instance_id="1@age:20", confidence=0.9,
        )
        timeline = builder.build_from_markers([marker_a, marker_b], sample_chapters)
        # El evento base del capítulo no debería tener instancia (ambiguo: hay 2)
        chapter_event = next(
            (e for e in timeline.events if e.chapter == 1 and e.paragraph == 0),
            None,
        )
        assert chapter_event is not None
        assert chapter_event.temporal_instance_id is None

    def test_legacy_mentions_without_type_still_work(self, extractor):
        """Menciones legacy sin entity_type siguen detectando edad."""
        text = "Pedro, a los 30 años, decidió viajar."
        markers = extractor.extract_with_entities(
            text=text,
            entity_mentions=[(1, 0, 5)],
            chapter=1,
        )
        age_markers = [m for m in markers if m.age == 30]
        assert len(age_markers) >= 1

    def test_resolve_offset_years_sign_format(self, builder, sample_chapters):
        """Verifica formato correcto de sign en offset_years: +N y -N."""
        marker_pos = TemporalMarker(
            text="dentro de 5 años", marker_type=MarkerType.CHARACTER_AGE,
            start_char=0, end_char=16, chapter=1, entity_id=1,
            relative_year_offset=5, temporal_instance_id="1@offset_years:+5",
            confidence=0.8,
        )
        marker_neg = TemporalMarker(
            text="hace 3 años", marker_type=MarkerType.CHARACTER_AGE,
            start_char=0, end_char=11, chapter=2, entity_id=1,
            relative_year_offset=-3, temporal_instance_id="1@offset_years:-3",
            confidence=0.8,
        )
        timeline = builder.build_from_markers(
            [marker_pos, marker_neg], sample_chapters,
        )
        instances = {e.temporal_instance_id for e in timeline.events if e.temporal_instance_id}
        assert "1@offset_years:+5" in instances
        assert "1@offset_years:-3" in instances
