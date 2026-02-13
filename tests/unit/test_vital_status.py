"""Tests para el módulo de estado vital de personajes."""

import pytest

from narrative_assistant.analysis.vital_status import (
    DeathEvent,
    PostMortemAppearance,
    VitalStatus,
    VitalStatusAnalyzer,
    VitalStatusReport,
    analyze_vital_status,
)


class TestVitalStatus:
    """Tests para VitalStatus enum."""

    def test_values(self):
        """Verifica valores del enum."""
        assert VitalStatus.ALIVE.value == "alive"
        assert VitalStatus.DEAD.value == "dead"
        assert VitalStatus.PRESUMED_DEAD.value == "presumed_dead"
        assert VitalStatus.UNKNOWN.value == "unknown"

    def test_all_values_present(self):
        """Verifica que todos los valores esperados existen."""
        values = [s.value for s in VitalStatus]
        assert "alive" in values
        assert "dead" in values
        assert "presumed_dead" in values
        assert "unknown" in values


class TestDeathEvent:
    """Tests para DeathEvent dataclass."""

    def test_create(self):
        """Test creación de evento de muerte."""
        event = DeathEvent(
            entity_id=1,
            entity_name="Juan",
            chapter=5,
            start_char=100,
            end_char=150,
            excerpt="Juan murió al caer del puente",
            death_type="direct",
            confidence=0.95,
        )

        assert event.entity_id == 1
        assert event.entity_name == "Juan"
        assert event.chapter == 5
        assert event.start_char == 100
        assert event.end_char == 150
        assert event.death_type == "direct"
        assert event.confidence == 0.95

    def test_default_confidence(self):
        """Test confianza por defecto."""
        event = DeathEvent(
            entity_id=1,
            entity_name="Pedro",
            chapter=3,
            start_char=0,
            end_char=50,
            excerpt="Pedro falleció",
            death_type="narrated",
        )

        assert event.confidence == 0.8

    def test_to_dict(self):
        """Test conversión a diccionario."""
        event = DeathEvent(
            entity_id=2,
            entity_name="María",
            chapter=7,
            start_char=200,
            end_char=280,
            excerpt="El cuerpo sin vida de María",
            death_type="direct",
            confidence=0.9,
        )

        d = event.to_dict()
        assert d["entity_id"] == 2
        assert d["entity_name"] == "María"
        assert d["chapter"] == 7
        assert d["death_type"] == "direct"
        assert d["confidence"] == 0.9
        assert "excerpt" in d

    def test_detected_at_auto(self):
        """Test que detected_at se genera automáticamente."""
        event = DeathEvent(
            entity_id=1,
            entity_name="Test",
            chapter=1,
            start_char=0,
            end_char=10,
            excerpt="Test murió",
            death_type="direct",
        )

        assert event.detected_at is not None


class TestPostMortemAppearance:
    """Tests para PostMortemAppearance dataclass."""

    def test_create(self):
        """Test creación de aparición post-mortem."""
        appearance = PostMortemAppearance(
            entity_id=1,
            entity_name="Juan",
            death_chapter=3,
            appearance_chapter=7,
            appearance_start_char=500,
            appearance_end_char=550,
            appearance_excerpt="Juan dijo algo",
            appearance_type="dialogue",
            is_valid=False,
            confidence=0.85,
        )

        assert appearance.entity_id == 1
        assert appearance.entity_name == "Juan"
        assert appearance.death_chapter == 3
        assert appearance.appearance_chapter == 7
        assert appearance.appearance_type == "dialogue"
        assert appearance.is_valid is False
        assert appearance.confidence == 0.85

    def test_valid_appearance(self):
        """Test aparición válida (flashback/recuerdo)."""
        appearance = PostMortemAppearance(
            entity_id=2,
            entity_name="María",
            death_chapter=5,
            appearance_chapter=8,
            appearance_start_char=100,
            appearance_end_char=150,
            appearance_excerpt="Recordaba a María diciendo",
            appearance_type="narration",
            is_valid=True,
            confidence=0.5,
        )

        assert appearance.is_valid is True

    def test_to_dict(self):
        """Test conversión a diccionario."""
        appearance = PostMortemAppearance(
            entity_id=3,
            entity_name="Pedro",
            death_chapter=2,
            appearance_chapter=10,
            appearance_start_char=1000,
            appearance_end_char=1100,
            appearance_excerpt="Pedro se levantó",
            appearance_type="action",
            is_valid=False,
        )

        d = appearance.to_dict()
        assert d["entity_id"] == 3
        assert d["entity_name"] == "Pedro"
        assert d["death_chapter"] == 2
        assert d["appearance_chapter"] == 10
        assert d["appearance_type"] == "action"
        assert d["is_valid"] is False


class TestVitalStatusReport:
    """Tests para VitalStatusReport dataclass."""

    def test_create_empty(self):
        """Test creación de reporte vacío."""
        report = VitalStatusReport(project_id=1)

        assert report.project_id == 1
        assert len(report.death_events) == 0
        assert len(report.post_mortem_appearances) == 0
        assert len(report.entities_status) == 0

    def test_create_with_data(self):
        """Test creación de reporte con datos."""
        death = DeathEvent(
            entity_id=1,
            entity_name="Juan",
            chapter=3,
            start_char=100,
            end_char=150,
            excerpt="Juan murió",
            death_type="direct",
        )

        appearance = PostMortemAppearance(
            entity_id=1,
            entity_name="Juan",
            death_chapter=3,
            appearance_chapter=5,
            appearance_start_char=500,
            appearance_end_char=550,
            appearance_excerpt="Juan dijo",
            appearance_type="dialogue",
            is_valid=False,
        )

        report = VitalStatusReport(
            project_id=1,
            death_events=[death],
            post_mortem_appearances=[appearance],
            entities_status={1: VitalStatus.DEAD},
        )

        assert len(report.death_events) == 1
        assert len(report.post_mortem_appearances) == 1
        assert report.entities_status[1] == VitalStatus.DEAD

    def test_inconsistencies_property(self):
        """Test propiedad inconsistencies (filtra is_valid)."""
        valid = PostMortemAppearance(
            entity_id=1,
            entity_name="Juan",
            death_chapter=3,
            appearance_chapter=5,
            appearance_start_char=0,
            appearance_end_char=50,
            appearance_excerpt="Recordaba a Juan",
            appearance_type="narration",
            is_valid=True,
        )

        invalid = PostMortemAppearance(
            entity_id=1,
            entity_name="Juan",
            death_chapter=3,
            appearance_chapter=7,
            appearance_start_char=100,
            appearance_end_char=150,
            appearance_excerpt="Juan caminó",
            appearance_type="action",
            is_valid=False,
        )

        report = VitalStatusReport(
            project_id=1,
            post_mortem_appearances=[valid, invalid],
        )

        assert len(report.inconsistencies) == 1
        assert report.inconsistencies[0].is_valid is False

    def test_to_dict(self):
        """Test conversión a diccionario."""
        report = VitalStatusReport(
            project_id=1,
            entities_status={1: VitalStatus.DEAD, 2: VitalStatus.ALIVE},
        )

        d = report.to_dict()
        assert d["project_id"] == 1
        assert d["entities_status"][1] == "dead"
        assert d["entities_status"][2] == "alive"
        assert d["inconsistencies_count"] == 0


class TestVitalStatusAnalyzer:
    """Tests para VitalStatusAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador de estado vital."""
        analyzer = VitalStatusAnalyzer(project_id=1)
        # Registrar algunos personajes de prueba
        analyzer.register_entity(1, "Juan", ["Juanito", "el doctor"])
        analyzer.register_entity(2, "María", ["la enfermera"])
        analyzer.register_entity(3, "Pedro")
        return analyzer

    def test_creation(self, analyzer):
        """Test creación del analizador."""
        assert analyzer is not None
        assert analyzer.project_id == 1

    def test_register_entity(self, analyzer):
        """Test registro de entidades."""
        assert analyzer.get_entity_id("juan") == 1
        assert analyzer.get_entity_id("juanito") == 1
        assert analyzer.get_entity_id("el doctor") == 1
        assert analyzer.get_entity_id("maría") == 2
        assert analyzer.get_entity_id("pedro") == 3

    def test_get_entity_id_unknown(self, analyzer):
        """Test obtención de ID para entidad desconocida."""
        assert analyzer.get_entity_id("desconocido") is None

    def test_detect_death_direct(self, analyzer):
        """Test detección de muerte directa."""
        text = "Juan murió al caer del puente. Fue una tragedia."
        events = analyzer.detect_death_events(text, chapter=5)

        assert len(events) == 1
        assert events[0].entity_name == "Juan"
        assert events[0].death_type == "direct"
        assert events[0].chapter == 5
        assert events[0].confidence >= 0.9

    def test_detect_death_caused(self, analyzer):
        """Test detección de muerte causada."""
        text = "El asesino mató a Pedro en el callejón oscuro."
        events = analyzer.detect_death_events(text, chapter=3)

        assert len(events) == 1
        assert events[0].entity_name == "Pedro"
        assert events[0].death_type == "caused"

    def test_detect_death_reported(self, analyzer):
        """Test detección de muerte reportada (presente perfecto)."""
        text = "María ha muerto esta mañana en el hospital."
        events = analyzer.detect_death_events(text, chapter=8)

        assert len(events) == 1
        assert events[0].entity_name == "María"
        assert events[0].death_type == "reported"

    def test_detect_death_implied(self, analyzer):
        """Test detección de muerte implícita."""
        text = "Visitaron la tumba de Juan en el cementerio."
        events = analyzer.detect_death_events(text, chapter=10)

        assert len(events) == 1
        assert events[0].entity_name == "Juan"
        assert events[0].death_type == "implied"
        assert events[0].confidence < 0.7  # Menor confianza para implícitas

    def test_detect_death_falleció(self, analyzer):
        """Test detección con verbo fallecer."""
        text = "Pedro falleció durante la operación."
        events = analyzer.detect_death_events(text, chapter=4)

        assert len(events) == 1
        assert events[0].entity_name == "Pedro"

    def test_detect_death_cayó_muerto(self, analyzer):
        """Test detección con cayó muerto."""
        text = "María cayó muerta frente a todos."
        events = analyzer.detect_death_events(text, chapter=6)

        assert len(events) == 1
        assert events[0].entity_name == "María"

    def test_detect_multiple_deaths(self, analyzer):
        """Test detección de múltiples muertes."""
        text = "Juan murió primero. Luego asesinaron a Pedro. María falleció días después."
        events = analyzer.detect_death_events(text, chapter=5)

        assert len(events) == 3
        names = {e.entity_name for e in events}
        assert "Juan" in names
        assert "Pedro" in names
        assert "María" in names

    def test_no_duplicate_death_events(self, analyzer):
        """Test que no se duplican eventos de muerte."""
        text1 = "Juan murió al caer."
        text2 = "Recordaban cómo Juan había muerto."  # No debe crear nuevo evento

        analyzer.detect_death_events(text1, chapter=3)
        events = analyzer.detect_death_events(text2, chapter=5)

        # No debe haber nuevo evento porque ya murió antes
        juan_events = [e for e in events if e.entity_name == "Juan"]
        assert len(juan_events) == 0

    def test_detect_death_unknown_character(self, analyzer):
        """Test que no detecta muerte de personaje desconocido."""
        text = "Roberto murió en la batalla."
        events = analyzer.detect_death_events(text, chapter=1)

        assert len(events) == 0  # Roberto no está registrado

    def test_check_post_mortem_dialogue(self, analyzer):
        """Test detección de diálogo post-mortem."""
        # Primero, matar al personaje
        text1 = "Juan murió en el capítulo anterior."
        analyzer.detect_death_events(text1, chapter=3)

        # Luego, verificar aparición
        text2 = "Juan dijo algo muy importante a María."
        appearances = analyzer.check_post_mortem_appearances(text2, chapter=5)

        assert len(appearances) == 1
        assert appearances[0].entity_name == "Juan"
        assert appearances[0].appearance_type == "dialogue"
        assert appearances[0].is_valid is False

    def test_check_post_mortem_action(self, analyzer):
        """Test detección de acción post-mortem."""
        text1 = "Pedro falleció en el hospital."
        analyzer.detect_death_events(text1, chapter=2)

        text2 = "Pedro se levantó y caminó hacia la puerta."
        appearances = analyzer.check_post_mortem_appearances(text2, chapter=4)

        assert len(appearances) >= 1
        assert any(a.appearance_type == "action" for a in appearances)

    def test_valid_reference_memory(self, analyzer):
        """Test que recuerdos son referencias válidas."""
        text1 = "María murió en el incendio."
        analyzer.detect_death_events(text1, chapter=5)

        text2 = "Recordaba cómo María sonrió aquella última vez."
        appearances = analyzer.check_post_mortem_appearances(text2, chapter=8)

        # Debería ser válido porque es un recuerdo
        assert all(a.is_valid is True for a in appearances) if appearances else True

    def test_valid_reference_flashback(self, analyzer):
        """Test que flashbacks son referencias válidas."""
        text1 = "Juan murió hace años."
        analyzer.detect_death_events(text1, chapter=3)

        text2 = "Años antes, Juan dijo que nunca olvidaría aquel día."
        appearances = analyzer.check_post_mortem_appearances(text2, chapter=10)

        # Debería ser válido porque hay marcador de flashback
        if appearances:
            assert all(a.is_valid is True for a in appearances)

    def test_valid_reference_ghost(self, analyzer):
        """Test que fantasmas son referencias válidas."""
        text1 = "Pedro murió en la mansión."
        analyzer.detect_death_events(text1, chapter=2)

        text2 = "El fantasma de Pedro dijo algo escalofriante."
        appearances = analyzer.check_post_mortem_appearances(text2, chapter=8)

        if appearances:
            assert all(a.is_valid is True for a in appearances)

    def test_no_post_mortem_in_same_chapter(self, analyzer):
        """Test que no hay falsos positivos en el mismo capítulo de muerte."""
        text = "Juan murió. Antes de morir, Juan dijo sus últimas palabras."
        analyzer.detect_death_events(text, chapter=5)
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)

        # No debería detectar aparición post-mortem en el mismo capítulo
        assert len(appearances) == 0

    def test_analyze_chapter(self, analyzer):
        """Test análisis completo de capítulo."""
        text = "Pedro cayó muerto al suelo. Todos quedaron en shock."

        deaths, appearances = analyzer.analyze_chapter(text, chapter=5)

        assert len(deaths) == 1
        assert deaths[0].entity_name == "Pedro"
        # No hay apariciones porque es el mismo capítulo
        assert len(appearances) == 0

    def test_get_entity_status_alive(self, analyzer):
        """Test estado vital: vivo."""
        assert analyzer.get_entity_status(1) == VitalStatus.ALIVE

    def test_get_entity_status_dead(self, analyzer):
        """Test estado vital: muerto."""
        text = "Juan murió."
        analyzer.detect_death_events(text, chapter=3)

        assert analyzer.get_entity_status(1) == VitalStatus.DEAD

    def test_get_entity_status_presumed_dead(self, analyzer):
        """Test estado vital: presumiblemente muerto."""
        text = "Juan nunca regresó de aquella misión."
        analyzer.detect_death_events(text, chapter=3)

        # implied deaths should be PRESUMED_DEAD
        assert analyzer.get_entity_status(1) == VitalStatus.PRESUMED_DEAD

    def test_generate_report(self, analyzer):
        """Test generación de reporte."""
        text = "María falleció pacíficamente."
        analyzer.detect_death_events(text, chapter=5)

        report = analyzer.generate_report()

        assert report.project_id == 1
        assert len(report.death_events) == 1
        assert report.entities_status[2] == VitalStatus.DEAD  # María
        assert report.entities_status[1] == VitalStatus.ALIVE  # Juan

    def test_clear(self, analyzer):
        """Test limpieza del estado interno."""
        text = "Juan murió."
        analyzer.detect_death_events(text, chapter=3)
        assert analyzer.get_entity_status(1) == VitalStatus.DEAD

        analyzer.clear()
        assert analyzer.get_entity_status(1) == VitalStatus.ALIVE


class TestAnalyzeVitalStatusFunction:
    """Tests para la función analyze_vital_status."""

    def test_basic_analysis(self):
        """Test análisis básico de estado vital."""
        chapters = [
            {"number": 1, "content": "Todo era tranquilo en la casa."},
            {"number": 2, "content": "Juan murió en un accidente."},
            {"number": 3, "content": "Todos lloraban su pérdida."},
        ]

        entities = [
            {"id": 1, "entity_type": "character", "canonical_name": "Juan", "aliases": []},
            {"id": 2, "entity_type": "character", "canonical_name": "María", "aliases": []},
        ]

        result = analyze_vital_status(
            project_id=1,
            chapters=chapters,
            entities=entities,
        )

        assert result.is_success
        report = result.value
        assert len(report.death_events) == 1
        assert report.death_events[0].entity_name == "Juan"
        assert report.entities_status[1] == VitalStatus.DEAD
        assert report.entities_status[2] == VitalStatus.ALIVE

    def test_analysis_with_post_mortem_appearance(self):
        """Test análisis con aparición post-mortem."""
        chapters = [
            {"number": 1, "content": "Pedro murió en la batalla."},
            {"number": 2, "content": "Pedro dijo que todo estaba bien."},  # Inconsistencia
        ]

        entities = [
            {"id": 1, "entity_type": "character", "canonical_name": "Pedro", "aliases": []},
        ]

        result = analyze_vital_status(
            project_id=1,
            chapters=chapters,
            entities=entities,
        )

        assert result.is_success
        report = result.value
        assert len(report.death_events) == 1
        assert len(report.post_mortem_appearances) >= 1
        assert len(report.inconsistencies) >= 1

    def test_analysis_with_aliases(self):
        """Test análisis reconociendo aliases."""
        chapters = [
            {"number": 1, "content": "El doctor llegó al hospital."},
            {"number": 2, "content": "Juanito murió durante la operación."},
        ]

        entities = [
            {
                "id": 1,
                "entity_type": "character",
                "canonical_name": "Juan",
                "aliases": ["Juanito", "el doctor"],
            },
        ]

        result = analyze_vital_status(
            project_id=1,
            chapters=chapters,
            entities=entities,
        )

        assert result.is_success
        report = result.value
        assert len(report.death_events) == 1
        assert report.death_events[0].entity_name == "Juan"

    def test_analysis_only_characters(self):
        """Test que solo analiza personajes/animales/criaturas."""
        chapters = [
            {"number": 1, "content": "Madrid murió como ciudad. (metáfora)"},
        ]

        entities = [
            {"id": 1, "entity_type": "location", "canonical_name": "Madrid", "aliases": []},
        ]

        result = analyze_vital_status(
            project_id=1,
            chapters=chapters,
            entities=entities,
        )

        assert result.is_success
        report = result.value
        # No debería detectar muerte porque es una ubicación
        assert len(report.death_events) == 0

    def test_analysis_empty_chapters(self):
        """Test análisis con capítulos vacíos."""
        chapters = [
            {"number": 1, "content": ""},
            {"number": 2, "text": ""},  # Alternative field name
        ]

        entities = [
            {"id": 1, "entity_type": "character", "canonical_name": "Juan", "aliases": []},
        ]

        result = analyze_vital_status(
            project_id=1,
            chapters=chapters,
            entities=entities,
        )

        assert result.is_success
        report = result.value
        assert len(report.death_events) == 0

    def test_analysis_chapter_ordering(self):
        """Test que los capítulos se procesan en orden."""
        # Capítulos desordenados
        chapters = [
            {"number": 3, "content": "María dijo algo."},  # Post-mortem si cap 1 primero
            {"number": 1, "content": "María murió."},
            {"number": 2, "content": "Todos lloraban."},
        ]

        entities = [
            {"id": 1, "entity_type": "character", "canonical_name": "María", "aliases": []},
        ]

        result = analyze_vital_status(
            project_id=1,
            chapters=chapters,
            entities=entities,
        )

        assert result.is_success
        report = result.value
        # María muere en cap 1, luego aparece en cap 3
        assert len(report.death_events) == 1
        # Should detect post-mortem in chapter 3
        assert len(report.post_mortem_appearances) >= 1


class TestDeathPatterns:
    """Tests específicos para patrones de detección de muerte."""

    @pytest.fixture
    def analyzer(self):
        """Analizador con personajes comunes."""
        analyzer = VitalStatusAnalyzer(project_id=1)
        analyzer.register_entity(1, "Juan")
        analyzer.register_entity(2, "María")
        analyzer.register_entity(3, "Pedro")
        return analyzer

    def test_pattern_murió(self, analyzer):
        """Test patrón 'murió'."""
        texts = [
            "Juan murió al amanecer.",
            "Juan murió.",
            "Juan murió rápidamente.",
        ]
        for text in texts:
            analyzer.clear()
            events = analyzer.detect_death_events(text, chapter=1)
            assert len(events) == 1, f"Failed for: {text}"

    def test_pattern_falleció(self, analyzer):
        """Test patrón 'falleció'."""
        texts = [
            "María falleció en el hospital.",
            "María falleció pacíficamente.",
        ]
        for text in texts:
            analyzer.clear()
            events = analyzer.detect_death_events(text, chapter=1)
            assert len(events) == 1, f"Failed for: {text}"

    def test_pattern_asesinaron(self, analyzer):
        """Test patrón 'asesinó/asesinaron'."""
        texts = [
            "Lo asesinaron a Pedro en su casa.",
            "Alguien asesinó a Juan.",
        ]
        for text in texts:
            analyzer.clear()
            events = analyzer.detect_death_events(text, chapter=1)
            assert len(events) >= 1, f"Failed for: {text}"

    def test_pattern_fue_asesinado(self, analyzer):
        """Test patrón 'fue asesinado'."""
        text = "Pedro fue asesinado por un desconocido."
        events = analyzer.detect_death_events(text, chapter=1)
        assert len(events) == 1

    def test_pattern_cadaver(self, analyzer):
        """Test patrón 'el cadáver de'."""
        text = "Encontraron el cadáver de Juan en el río."
        events = analyzer.detect_death_events(text, chapter=1)
        assert len(events) == 1

    def test_pattern_cuerpo_sin_vida(self, analyzer):
        """Test patrón 'cuerpo sin vida'."""
        text = "El cuerpo sin vida de María yacía en el suelo."
        events = analyzer.detect_death_events(text, chapter=1)
        assert len(events) == 1

    def test_pattern_disparo(self, analyzer):
        """Test patrón 'disparó a'."""
        text = "El asesino disparó a Pedro sin piedad."
        events = analyzer.detect_death_events(text, chapter=1)
        assert len(events) == 1

    def test_pattern_tumba(self, analyzer):
        """Test patrón 'la tumba de' (implícito)."""
        text = "Visitaron la tumba de Juan cada año."
        events = analyzer.detect_death_events(text, chapter=1)
        assert len(events) == 1
        assert events[0].death_type == "implied"


class TestValidReferencePatterns:
    """Tests para patrones de referencias válidas (no inconsistencias)."""

    @pytest.fixture
    def analyzer(self):
        """Analizador con personaje muerto."""
        analyzer = VitalStatusAnalyzer(project_id=1)
        analyzer.register_entity(1, "Juan")
        # Matar al personaje primero
        analyzer.detect_death_events("Juan murió.", chapter=1)
        return analyzer

    def test_valid_recordaba(self, analyzer):
        """Test que 'recordaba a X' es válido."""
        text = "Ella recordaba a Juan con cariño."
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)
        # No debe detectar aparición activa aquí
        # o si detecta, debe ser marcada como válida
        if appearances:
            assert all(a.is_valid for a in appearances)

    def test_valid_el_recuerdo_de(self, analyzer):
        """Test que 'el recuerdo de X' es válido."""
        text = "El recuerdo de Juan la perseguía."
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)
        if appearances:
            assert all(a.is_valid for a in appearances)

    def test_valid_fantasma(self, analyzer):
        """Test que 'el fantasma de X' es válido."""
        text = "El fantasma de Juan dijo algo."
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)
        if appearances:
            assert all(a.is_valid for a in appearances)

    def test_valid_anos_antes(self, analyzer):
        """Test que marcador 'años antes' hace válido."""
        text = "Años antes, Juan dijo que siempre la amaría."
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)
        if appearances:
            assert all(a.is_valid for a in appearances)

    def test_valid_cuando_vivia(self, analyzer):
        """Test que 'cuando X vivía' es válido."""
        text = "Cuando Juan vivía, todo era diferente. Juan sonreía siempre."
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)
        if appearances:
            assert all(a.is_valid for a in appearances)

    def test_invalid_action_without_markers(self, analyzer):
        """Test que acción sin marcadores es inválida."""
        text = "Juan se levantó y miró por la ventana."
        appearances = analyzer.check_post_mortem_appearances(text, chapter=5)

        # Debe detectar apariciones inválidas
        assert len(appearances) >= 1
        assert any(not a.is_valid for a in appearances)


# ============================================================================
# BK-08: Integration tests — vital_status + temporal_map
# ============================================================================


class TestVitalStatusWithTemporalMapIntegration:
    """Tests de integración vital_status + temporal_map (BK-08)."""

    def test_flashback_before_death_not_flagged(self):
        """Flashback anterior a muerte no debe marcarse como inconsistencia."""
        from datetime import date

        from narrative_assistant.temporal.temporal_map import (
            NarrativeType,
            TemporalMap,
            TemporalSlice,
        )

        temporal_map = TemporalMap()
        temporal_map.add_slice(1, TemporalSlice(
            chapter=1, story_date=date(2020, 1, 1),
            narrative_type=NarrativeType.CHRONOLOGICAL,
        ))
        temporal_map.add_slice(2, TemporalSlice(
            chapter=2, story_date=date(2020, 6, 1),
            narrative_type=NarrativeType.CHRONOLOGICAL,
        ))
        temporal_map.add_slice(3, TemporalSlice(
            chapter=3, story_date=date(2020, 3, 1),
            narrative_type=NarrativeType.ANALEPSIS,
        ))

        chapters = [
            {"number": 1, "content": "Juan está sano.", "story_date": date(2020, 1, 1)},
            {"number": 2, "content": "Juan murió de neumonía.", "story_date": date(2020, 6, 1)},
            {"number": 3, "content": "En marzo, Juan sonrió en la playa.", "story_date": date(2020, 3, 1)},
        ]
        entities = [{"id": 1, "entity_type": "character", "canonical_name": "Juan", "aliases": []}]

        result = analyze_vital_status(1, chapters, entities, temporal_map=temporal_map)
        assert result.is_success
        report = result.value

        assert len(report.death_events) == 1
        assert report.death_events[0].chapter == 2
        # Cap 3 es flashback anterior a muerte → no debe ser inconsistencia
        inconsistencies = report.inconsistencies
        for inc in inconsistencies:
            assert inc.appearance_chapter != 3, (
                "Flashback anterior a muerte no debe marcarse como inconsistencia"
            )

    def test_day_offset_temporal_map(self):
        """Temporal map con day_offset funciona correctamente."""
        from narrative_assistant.temporal.temporal_map import (
            NarrativeType,
            TemporalMap,
            TemporalSlice,
        )

        temporal_map = TemporalMap()
        temporal_map.add_slice(1, TemporalSlice(
            chapter=1, day_offset=0,
            narrative_type=NarrativeType.CHRONOLOGICAL,
        ))
        temporal_map.add_slice(2, TemporalSlice(
            chapter=2, day_offset=5,
            narrative_type=NarrativeType.CHRONOLOGICAL,
        ))
        temporal_map.add_slice(3, TemporalSlice(
            chapter=3, day_offset=-365,
            narrative_type=NarrativeType.ANALEPSIS,
        ))

        chapters = [
            {"number": 1, "content": "Hoy es el día 0.", "day_offset": 0},
            {"number": 2, "content": "Cinco días después, Elena murió.", "day_offset": 5},
            {"number": 3, "content": "Un año antes, Elena bailó bajo la lluvia.", "day_offset": -365},
        ]
        entities = [{"id": 1, "entity_type": "character", "canonical_name": "Elena", "aliases": []}]

        result = analyze_vital_status(1, chapters, entities, temporal_map=temporal_map)
        assert result.is_success
        report = result.value

        assert len(report.death_events) == 1
        # Cap 3 (day -365) es anterior a muerte (day 5) → no inconsistencia
        for inc in report.inconsistencies:
            assert inc.appearance_chapter != 3

    def test_death_registers_temporal_instance_when_age_is_explicit(self):
        """Si la muerte menciona edad, registra instancia temporal en TemporalMap."""
        from narrative_assistant.temporal.temporal_map import (
            NarrativeType,
            TemporalMap,
            TemporalSlice,
        )

        temporal_map = TemporalMap()
        temporal_map.add_slice(2, TemporalSlice(
            chapter=2,
            day_offset=10,
            narrative_type=NarrativeType.CHRONOLOGICAL,
        ))
        temporal_map.add_slice(3, TemporalSlice(
            chapter=3,
            day_offset=20,
            narrative_type=NarrativeType.CHRONOLOGICAL,
        ))

        analyzer = VitalStatusAnalyzer(project_id=1, temporal_map=temporal_map)
        analyzer.register_entity(1, "Juan")

        events = analyzer.detect_death_events("Juan murió a los 45 años.", chapter=2)
        assert len(events) == 1
        assert events[0].temporal_instance_id == "1@age:45"

        assert (
            temporal_map.is_character_alive_in_chapter(
                1, 3, temporal_instance_id="1@age:45"
            )
            is False
        )
        assert (
            temporal_map.is_character_alive_in_chapter(
                1, 3, temporal_instance_id="1@age:40"
            )
            is True
        )

    def test_fallback_without_temporal_map(self):
        """Sin temporal_map, usa comparación lineal por capítulo."""
        chapters = [
            {"number": 1, "content": "Pedro está aquí."},
            {"number": 2, "content": "Pedro murió trágicamente."},
            {"number": 3, "content": "Pedro se levantó y habló."},
        ]
        entities = [{"id": 1, "entity_type": "character", "canonical_name": "Pedro", "aliases": []}]

        result = analyze_vital_status(1, chapters, entities, temporal_map=None)
        assert result.is_success
        report = result.value

        assert len(report.death_events) == 1
        # Cap 3 es posterior a muerte sin temporal_map → debe detectar
        assert len(report.post_mortem_appearances) >= 1

    def test_speculative_death_not_recorded(self):
        """Muerte especulativa (irrealis) no debe registrarse como real."""
        chapters = [
            {"number": 1, "content": "Si Ana hubiera muerto, todo sería diferente."},
            {"number": 2, "content": "Ana caminó por el parque."},
        ]
        entities = [{"id": 1, "entity_type": "character", "canonical_name": "Ana", "aliases": []}]

        result = analyze_vital_status(1, chapters, entities)
        assert result.is_success
        report = result.value

        # No debe registrar muerte especulativa
        assert len(report.death_events) == 0

    def test_pluperfect_death_detected_with_lower_confidence(self):
        """Muerte en pluscuamperfecto detectada con confianza reducida."""
        chapters = [
            {"number": 1, "content": "Carlos había muerto tres años antes."},
        ]
        entities = [{"id": 1, "entity_type": "character", "canonical_name": "Carlos", "aliases": []}]

        result = analyze_vital_status(1, chapters, entities)
        assert result.is_success
        report = result.value

        assert len(report.death_events) == 1
        assert report.death_events[0].death_type == "pluperfect"
        assert report.death_events[0].confidence == 0.65
