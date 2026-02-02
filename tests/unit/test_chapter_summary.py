"""Tests para el módulo de resumen de capítulos."""

import pytest
from narrative_assistant.analysis.chapter_summary import (
    AnalysisMode,
    EventType,
    NarrativeEvent,
    CharacterPresence,
    ChekhovElement,
    CharacterArc,
    AbandonedThread,
    ChapterSummary,
    ChapterProgressReport,
    REVELATION_PATTERNS,
    DEATH_PATTERNS,
    DECISION_PATTERNS,
)


class TestAnalysisMode:
    """Tests para AnalysisMode enum."""

    def test_values(self):
        """Verifica valores del enum."""
        assert AnalysisMode.BASIC.value == "basic"
        assert AnalysisMode.STANDARD.value == "standard"
        assert AnalysisMode.DEEP.value == "deep"

    def test_all_values_present(self):
        """Verifica que todos los valores esperados existen."""
        values = [m.value for m in AnalysisMode]
        assert "basic" in values
        assert "standard" in values
        assert "deep" in values

    def test_string_conversion(self):
        """Test que los valores son strings."""
        assert str(AnalysisMode.BASIC.value) == "basic"
        assert isinstance(AnalysisMode.STANDARD.value, str)


class TestEventType:
    """Tests para EventType enum."""

    def test_basic_events(self):
        """Verifica eventos básicos."""
        assert EventType.FIRST_APPEARANCE.value == "first_appearance"
        assert EventType.RETURN.value == "return"
        assert EventType.DEATH.value == "death"
        assert EventType.DEPARTURE.value == "departure"
        assert EventType.CONFLICT.value == "conflict"
        assert EventType.ALLIANCE.value == "alliance"

    def test_advanced_events(self):
        """Verifica eventos avanzados que requieren LLM."""
        assert EventType.DECISION.value == "decision"
        assert EventType.DISCOVERY.value == "discovery"
        assert EventType.REVELATION.value == "revelation"
        assert EventType.BETRAYAL.value == "betrayal"
        assert EventType.SACRIFICE.value == "sacrifice"
        assert EventType.TRANSFORMATION.value == "transformation"
        assert EventType.PLOT_TWIST.value == "plot_twist"
        assert EventType.CLIMAX_MOMENT.value == "climax_moment"
        assert EventType.RESOLUTION.value == "resolution"

    def test_all_event_types_count(self):
        """Verifica número total de tipos de evento."""
        # Básicos: 9, Avanzados: 9
        assert len(list(EventType)) >= 15


class TestNarrativeEvent:
    """Tests para NarrativeEvent dataclass."""

    def test_create_minimal(self):
        """Test creación con parámetros mínimos."""
        event = NarrativeEvent(
            event_type=EventType.FIRST_APPEARANCE,
            description="Juan aparece por primera vez",
        )

        assert event.event_type == EventType.FIRST_APPEARANCE
        assert event.description == "Juan aparece por primera vez"
        assert event.characters_involved == []
        assert event.chapter_number == 0
        assert event.position == 0
        assert event.confidence == 1.0
        assert event.source_text == ""
        assert event.detected_by == "pattern"

    def test_create_full(self):
        """Test creación con todos los parámetros."""
        event = NarrativeEvent(
            event_type=EventType.DEATH,
            description="María muere en el accidente",
            characters_involved=["María", "Juan"],
            chapter_number=5,
            position=1234,
            confidence=0.95,
            source_text="María murió al caer por el precipicio",
            detected_by="llm",
        )

        assert event.event_type == EventType.DEATH
        assert event.characters_involved == ["María", "Juan"]
        assert event.chapter_number == 5
        assert event.position == 1234
        assert event.confidence == 0.95
        assert event.detected_by == "llm"

    def test_to_dict(self):
        """Test conversión a diccionario."""
        event = NarrativeEvent(
            event_type=EventType.REVELATION,
            description="Se revela el secreto",
            characters_involved=["Pedro"],
            chapter_number=3,
            position=500,
            confidence=0.8,
            source_text="La verdad es que Pedro había mentido todo este tiempo",
            detected_by="pattern",
        )

        d = event.to_dict()
        assert d["event_type"] == "revelation"
        assert d["description"] == "Se revela el secreto"
        assert d["characters_involved"] == ["Pedro"]
        assert d["chapter_number"] == 3
        assert d["position"] == 500
        assert d["confidence"] == 0.8
        assert "La verdad es que" in d["source_text"]
        assert d["detected_by"] == "pattern"

    def test_to_dict_truncates_source_text(self):
        """Test que source_text se trunca a 200 caracteres."""
        long_text = "x" * 500
        event = NarrativeEvent(
            event_type=EventType.CONFLICT,
            description="Conflicto",
            source_text=long_text,
        )

        d = event.to_dict()
        assert len(d["source_text"]) <= 200


class TestCharacterPresence:
    """Tests para CharacterPresence dataclass."""

    def test_create_minimal(self):
        """Test creación con parámetros mínimos."""
        presence = CharacterPresence(
            entity_id=1,
            name="Juan",
        )

        assert presence.entity_id == 1
        assert presence.name == "Juan"
        assert presence.mention_count == 0
        assert presence.first_mention_position == 0
        assert presence.last_mention_position == 0
        assert presence.is_first_appearance is False
        assert presence.is_return is False
        assert presence.chapters_absent == 0
        assert presence.dialogues_count == 0
        assert presence.actions_count == 0
        assert presence.interactions_with == []
        assert presence.dominant_emotion is None
        assert presence.emotional_trajectory == "stable"

    def test_create_full(self):
        """Test creación con todos los parámetros."""
        presence = CharacterPresence(
            entity_id=2,
            name="María",
            mention_count=15,
            first_mention_position=100,
            last_mention_position=5000,
            is_first_appearance=True,
            is_return=False,
            chapters_absent=0,
            dialogues_count=5,
            actions_count=8,
            interactions_with=["Juan", "Pedro"],
            dominant_emotion="anger",
            emotional_trajectory="rising",
        )

        assert presence.mention_count == 15
        assert presence.is_first_appearance is True
        assert presence.dialogues_count == 5
        assert presence.actions_count == 8
        assert presence.interactions_with == ["Juan", "Pedro"]
        assert presence.dominant_emotion == "anger"
        assert presence.emotional_trajectory == "rising"

    def test_return_with_chapters_absent(self):
        """Test presencia con retorno después de ausencia."""
        presence = CharacterPresence(
            entity_id=3,
            name="Pedro",
            is_return=True,
            chapters_absent=3,
        )

        assert presence.is_return is True
        assert presence.chapters_absent == 3

    def test_to_dict(self):
        """Test conversión a diccionario."""
        presence = CharacterPresence(
            entity_id=1,
            name="Juan",
            mention_count=10,
            dialogues_count=3,
            interactions_with=["María"],
            dominant_emotion="joy",
        )

        d = presence.to_dict()
        assert d["entity_id"] == 1
        assert d["name"] == "Juan"
        assert d["mention_count"] == 10
        assert d["dialogues_count"] == 3
        assert d["interactions_with"] == ["María"]
        assert d["dominant_emotion"] == "joy"


class TestChekhovElement:
    """Tests para ChekhovElement dataclass."""

    def test_create_unfired(self):
        """Test creación de elemento sin payoff."""
        element = ChekhovElement(
            entity_id=1,
            name="La pistola",
            element_type="object",
            setup_chapter=1,
            setup_position=250,
            setup_context="Juan guardó la pistola en el cajón",
        )

        assert element.entity_id == 1
        assert element.name == "La pistola"
        assert element.element_type == "object"
        assert element.setup_chapter == 1
        assert element.payoff_chapter is None
        assert element.is_fired is False
        assert element.confidence == 0.5

    def test_create_fired(self):
        """Test creación de elemento con payoff."""
        element = ChekhovElement(
            entity_id=2,
            name="El mapa",
            element_type="object",
            setup_chapter=2,
            setup_position=100,
            setup_context="Encontraron un mapa antiguo",
            payoff_chapter=8,
            payoff_position=3000,
            payoff_context="El mapa los llevó al tesoro",
            is_fired=True,
            confidence=0.9,
        )

        assert element.payoff_chapter == 8
        assert element.is_fired is True
        assert element.confidence == 0.9

    def test_to_dict(self):
        """Test conversión a diccionario."""
        element = ChekhovElement(
            entity_id=None,
            name="El anillo",
            element_type="detail",
            setup_chapter=1,
            setup_position=50,
            setup_context="El anillo brillaba en la oscuridad",
            llm_analysis="Este objeto parece importante pero no se resuelve",
        )

        d = element.to_dict()
        assert d["entity_id"] is None
        assert d["name"] == "El anillo"
        assert d["element_type"] == "detail"
        assert d["setup_chapter"] == 1
        assert d["is_fired"] is False
        assert d["llm_analysis"] is not None

    def test_to_dict_truncates_context(self):
        """Test que los contextos se truncan a 200 caracteres."""
        long_context = "x" * 500
        element = ChekhovElement(
            entity_id=1,
            name="Objeto",
            element_type="object",
            setup_chapter=1,
            setup_position=0,
            setup_context=long_context,
            payoff_context=long_context,
        )

        d = element.to_dict()
        assert len(d["setup_context"]) <= 200
        assert len(d["payoff_context"]) <= 200


class TestCharacterArc:
    """Tests para CharacterArc dataclass."""

    def test_create_minimal(self):
        """Test creación con parámetros mínimos."""
        arc = CharacterArc(
            character_id=1,
            character_name="Juan",
            arc_type="growth",
        )

        assert arc.character_id == 1
        assert arc.character_name == "Juan"
        assert arc.arc_type == "growth"
        assert arc.start_state == ""
        assert arc.end_state == ""
        assert arc.key_turning_points == []
        assert arc.completeness == 0.0
        assert arc.chapters_present == 0
        assert arc.total_mentions == 0
        assert arc.max_absence_gap == 0
        assert arc.trajectory == "stable"

    def test_arc_types(self):
        """Test diferentes tipos de arco."""
        arc_types = ["growth", "fall", "redemption", "static", "circular"]
        for arc_type in arc_types:
            arc = CharacterArc(
                character_id=1,
                character_name="Test",
                arc_type=arc_type,
            )
            assert arc.arc_type == arc_type

    def test_create_full(self):
        """Test creación con todos los parámetros."""
        arc = CharacterArc(
            character_id=2,
            character_name="María",
            arc_type="redemption",
            start_state="Villana despiadada",
            end_state="Heroína redimida",
            key_turning_points=[
                {"chapter": 5, "event": "Se arrepiente"},
                {"chapter": 10, "event": "Salva al protagonista"},
            ],
            completeness=0.85,
            chapters_present=12,
            total_mentions=150,
            max_absence_gap=2,
            trajectory="rising",
            llm_notes="Arco bien desarrollado",
        )

        assert arc.start_state == "Villana despiadada"
        assert arc.end_state == "Heroína redimida"
        assert len(arc.key_turning_points) == 2
        assert arc.completeness == 0.85
        assert arc.trajectory == "rising"

    def test_to_dict(self):
        """Test conversión a diccionario."""
        arc = CharacterArc(
            character_id=1,
            character_name="Pedro",
            arc_type="fall",
            trajectory="declining",
            completeness=0.6,
        )

        d = arc.to_dict()
        assert d["character_id"] == 1
        assert d["character_name"] == "Pedro"
        assert d["arc_type"] == "fall"
        assert d["trajectory"] == "declining"
        assert d["completeness"] == 0.6


class TestAbandonedThread:
    """Tests para AbandonedThread dataclass."""

    def test_create_minimal(self):
        """Test creación con parámetros mínimos."""
        thread = AbandonedThread(
            description="La profecía nunca se cumple",
            introduced_chapter=2,
            last_mention_chapter=4,
        )

        assert thread.description == "La profecía nunca se cumple"
        assert thread.introduced_chapter == 2
        assert thread.last_mention_chapter == 4
        assert thread.characters_involved == []
        assert thread.entities_involved == []
        assert thread.suggestion is None
        assert thread.confidence == 0.5

    def test_create_full(self):
        """Test creación con todos los parámetros."""
        thread = AbandonedThread(
            description="El romance entre Juan y María",
            introduced_chapter=3,
            last_mention_chapter=7,
            characters_involved=["Juan", "María"],
            entities_involved=["El anillo de compromiso"],
            suggestion="Resolver en capítulo final",
            confidence=0.8,
        )

        assert thread.characters_involved == ["Juan", "María"]
        assert thread.entities_involved == ["El anillo de compromiso"]
        assert thread.suggestion is not None
        assert thread.confidence == 0.8

    def test_to_dict(self):
        """Test conversión a diccionario."""
        thread = AbandonedThread(
            description="Trama abandonada",
            introduced_chapter=1,
            last_mention_chapter=5,
            suggestion="Añadir resolución",
        )

        d = thread.to_dict()
        assert d["description"] == "Trama abandonada"
        assert d["introduced_chapter"] == 1
        assert d["last_mention_chapter"] == 5
        assert d["suggestion"] == "Añadir resolución"


class TestChapterSummary:
    """Tests para ChapterSummary dataclass."""

    def test_create_minimal(self):
        """Test creación con parámetros mínimos."""
        summary = ChapterSummary(chapter_number=1)

        assert summary.chapter_number == 1
        assert summary.chapter_title is None
        assert summary.word_count == 0
        assert summary.characters_present == []
        assert summary.new_characters == []
        assert summary.returning_characters == []
        assert summary.absent_characters == []
        assert summary.key_events == []
        assert summary.llm_events == []
        assert summary.total_interactions == 0
        assert summary.conflict_interactions == 0
        assert summary.positive_interactions == 0
        assert summary.dominant_tone == "neutral"
        assert summary.tone_intensity == 0.5
        assert summary.locations_mentioned == []
        assert summary.location_changes == 0
        assert summary.auto_summary == ""
        assert summary.llm_summary is None

    def test_create_full(self):
        """Test creación con datos completos."""
        presence = CharacterPresence(entity_id=1, name="Juan", mention_count=10)
        event = NarrativeEvent(
            event_type=EventType.FIRST_APPEARANCE,
            description="Juan aparece",
        )

        summary = ChapterSummary(
            chapter_number=3,
            chapter_title="El encuentro",
            word_count=2500,
            characters_present=[presence],
            new_characters=["Juan"],
            key_events=[event],
            total_interactions=5,
            conflict_interactions=2,
            positive_interactions=3,
            dominant_tone="positive",
            tone_intensity=0.7,
            locations_mentioned=["La plaza", "El bar"],
            auto_summary="Juan aparece por primera vez en la plaza.",
        )

        assert summary.chapter_title == "El encuentro"
        assert summary.word_count == 2500
        assert len(summary.characters_present) == 1
        assert len(summary.key_events) == 1
        assert summary.total_interactions == 5
        assert summary.dominant_tone == "positive"

    def test_to_dict(self):
        """Test conversión a diccionario."""
        summary = ChapterSummary(
            chapter_number=5,
            chapter_title="Capítulo V",
            word_count=3000,
            new_characters=["María"],
            locations_mentioned=["Madrid"],
            auto_summary="Resumen automático",
            llm_summary="Resumen LLM",
        )

        d = summary.to_dict()
        assert d["chapter_number"] == 5
        assert d["chapter_title"] == "Capítulo V"
        assert d["word_count"] == 3000
        assert d["new_characters"] == ["María"]
        assert d["locations_mentioned"] == ["Madrid"]
        assert d["auto_summary"] == "Resumen automático"
        assert d["llm_summary"] == "Resumen LLM"


class TestChapterProgressReport:
    """Tests para ChapterProgressReport dataclass."""

    def test_create_empty(self):
        """Test creación de reporte vacío."""
        report = ChapterProgressReport(project_id=1)

        assert report.project_id == 1
        assert report.analysis_mode == "basic"
        assert report.total_chapters == 0
        assert report.chapters == []
        assert report.total_characters == 0
        assert report.active_characters == 0
        assert report.dormant_characters == []
        assert report.character_arcs == []
        assert report.chekhov_elements == []
        assert report.abandoned_threads == []
        assert report.structural_notes is None

    def test_create_with_data(self):
        """Test creación con datos."""
        chapter_summary = ChapterSummary(chapter_number=1, word_count=1000)
        arc = CharacterArc(character_id=1, character_name="Juan", arc_type="growth")

        report = ChapterProgressReport(
            project_id=1,
            analysis_mode="standard",
            total_chapters=10,
            chapters=[chapter_summary],
            total_characters=5,
            active_characters=4,
            dormant_characters=["Pedro"],
            character_arcs=[arc],
            structural_notes="La estructura es sólida",
        )

        assert report.analysis_mode == "standard"
        assert report.total_chapters == 10
        assert len(report.chapters) == 1
        assert report.total_characters == 5
        assert report.dormant_characters == ["Pedro"]
        assert report.structural_notes is not None

    def test_to_dict(self):
        """Test conversión a diccionario."""
        report = ChapterProgressReport(
            project_id=1,
            analysis_mode="deep",
            total_chapters=5,
            total_characters=10,
            active_characters=8,
            dormant_characters=["María"],
        )

        d = report.to_dict()
        assert d["project_id"] == 1
        assert d["analysis_mode"] == "deep"
        assert d["total_chapters"] == 5
        assert d["total_characters"] == 10
        assert d["active_characters"] == 8
        assert d["dormant_characters"] == ["María"]


class TestPatterns:
    """Tests para los patrones regex."""

    def test_revelation_patterns_match(self):
        """Test que los patrones de revelación funcionan."""
        test_cases = [
            "nunca le había contado la verdad",
            "finalmente descubrió el secreto",
            "la verdad es que todo era mentira",
            "todo este tiempo había estado mintiendo",
            "por fin supo quién era el asesino",
        ]

        for text in test_cases:
            matched = any(p.search(text) for p in REVELATION_PATTERNS)
            assert matched, f"Pattern should match: {text}"

    def test_revelation_patterns_no_false_positives(self):
        """Test que no hay falsos positivos en revelaciones."""
        test_cases = [
            "El cielo estaba despejado",
            "Juan caminó hacia la puerta",
            "Era un día normal",
        ]

        for text in test_cases:
            matched = any(p.search(text) for p in REVELATION_PATTERNS)
            assert not matched, f"Pattern should NOT match: {text}"

    def test_death_patterns_match(self):
        """Test que los patrones de muerte funcionan."""
        test_cases = [
            "Juan murió en el accidente",
            "María falleció pacíficamente",
            "dejó de existir en ese momento",
            "exhaló su último aliento",
            "ya no estaba con nosotros",
        ]

        for text in test_cases:
            matched = any(p.search(text) for p in DEATH_PATTERNS)
            assert matched, f"Pattern should match: {text}"

    def test_death_patterns_no_false_positives(self):
        """Test que no hay falsos positivos en muertes."""
        test_cases = [
            "Estaba muy cansado",
            "Se fue a dormir",
            "Llegó a la ciudad",
        ]

        for text in test_cases:
            matched = any(p.search(text) for p in DEATH_PATTERNS)
            assert not matched, f"Pattern should NOT match: {text}"

    def test_decision_patterns_match(self):
        """Test que los patrones de decisión funcionan."""
        test_cases = [
            "decidió que era hora de actuar",
            "resolvió no volver jamás",
            "tomó la decisión más difícil",
            "no había vuelta atrás",
        ]

        for text in test_cases:
            matched = any(p.search(text) for p in DECISION_PATTERNS)
            assert matched, f"Pattern should match: {text}"

    def test_decision_patterns_no_false_positives(self):
        """Test que no hay falsos positivos en decisiones."""
        test_cases = [
            "Pensó en el futuro",
            "Miraba por la ventana",
            "El día terminó bien",
        ]

        for text in test_cases:
            matched = any(p.search(text) for p in DECISION_PATTERNS)
            assert not matched, f"Pattern should NOT match: {text}"


class TestIntegration:
    """Tests de integración básicos (sin base de datos real)."""

    def test_chapter_summary_with_events(self):
        """Test que ChapterSummary puede contener múltiples eventos."""
        events = [
            NarrativeEvent(
                event_type=EventType.FIRST_APPEARANCE,
                description="Juan aparece",
                chapter_number=1,
            ),
            NarrativeEvent(
                event_type=EventType.CONFLICT,
                description="Conflicto con María",
                characters_involved=["Juan", "María"],
                chapter_number=1,
            ),
        ]

        summary = ChapterSummary(
            chapter_number=1,
            key_events=events,
        )

        assert len(summary.key_events) == 2
        d = summary.to_dict()
        assert len(d["key_events"]) == 2
        assert d["key_events"][0]["event_type"] == "first_appearance"
        assert d["key_events"][1]["event_type"] == "conflict"

    def test_report_with_full_data(self):
        """Test reporte completo con todos los tipos de datos."""
        # Crear datos
        presence = CharacterPresence(
            entity_id=1,
            name="Juan",
            mention_count=20,
            is_first_appearance=True,
        )

        event = NarrativeEvent(
            event_type=EventType.FIRST_APPEARANCE,
            description="Juan aparece",
            characters_involved=["Juan"],
            chapter_number=1,
        )

        chapter = ChapterSummary(
            chapter_number=1,
            chapter_title="Inicio",
            word_count=2000,
            characters_present=[presence],
            new_characters=["Juan"],
            key_events=[event],
            auto_summary="Juan aparece por primera vez.",
        )

        arc = CharacterArc(
            character_id=1,
            character_name="Juan",
            arc_type="growth",
            trajectory="rising",
            chapters_present=10,
        )

        chekhov = ChekhovElement(
            entity_id=2,
            name="La espada",
            element_type="object",
            setup_chapter=1,
            setup_position=100,
            setup_context="La espada antigua colgaba de la pared",
            is_fired=False,
        )

        thread = AbandonedThread(
            description="El misterio del jardín",
            introduced_chapter=2,
            last_mention_chapter=5,
        )

        report = ChapterProgressReport(
            project_id=1,
            analysis_mode="standard",
            total_chapters=10,
            chapters=[chapter],
            total_characters=5,
            active_characters=4,
            dormant_characters=["Pedro"],
            character_arcs=[arc],
            chekhov_elements=[chekhov],
            abandoned_threads=[thread],
            structural_notes="Estructura sólida con un hilo sin resolver.",
        )

        d = report.to_dict()

        # Verificar estructura
        assert d["project_id"] == 1
        assert d["analysis_mode"] == "standard"
        assert d["total_chapters"] == 10
        assert len(d["chapters"]) == 1
        assert len(d["character_arcs"]) == 1
        assert len(d["chekhov_elements"]) == 1
        assert len(d["abandoned_threads"]) == 1

        # Verificar anidado
        assert d["chapters"][0]["chapter_title"] == "Inicio"
        assert d["chapters"][0]["new_characters"] == ["Juan"]
        assert d["character_arcs"][0]["arc_type"] == "growth"
        assert d["chekhov_elements"][0]["is_fired"] is False
        assert d["abandoned_threads"][0]["introduced_chapter"] == 2


# =============================================================================
# Tests para compute_chapter_metrics (S-6: Chapter Model Enrichment)
# =============================================================================

class TestComputeChapterMetrics:
    """Tests para la función de cómputo de métricas de capítulo."""

    def test_empty_content(self):
        """Texto vacío retorna diccionario vacío."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        assert compute_chapter_metrics("") == {}
        assert compute_chapter_metrics("   ") == {}

    def test_reading_time(self):
        """Calcula tiempo de lectura correctamente."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        # 200 palabras = 1 minuto
        text = " ".join(["palabra"] * 200)
        metrics = compute_chapter_metrics(text)
        assert metrics["reading_time_minutes"] == 1

        # 600 palabras = 3 minutos
        text = " ".join(["palabra"] * 600)
        metrics = compute_chapter_metrics(text)
        assert metrics["reading_time_minutes"] == 3

    def test_dialogue_ratio_with_dashes(self):
        """Detecta diálogo con rayas."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = (
            "El sol brillaba.\n"
            "—Hola, ¿cómo estás? —preguntó Juan.\n"
            "—Bien, gracias —respondió María.\n"
            "El viento soplaba."
        )
        metrics = compute_chapter_metrics(text)
        assert "dialogue_ratio" in metrics
        assert metrics["dialogue_ratio"] > 0

    def test_dialogue_ratio_no_dialogue(self):
        """Sin diálogo, ratio es bajo o cero."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = "El sol brillaba. Los pájaros cantaban. Todo era paz."
        metrics = compute_chapter_metrics(text)
        assert metrics.get("dialogue_ratio", 0) < 0.1

    def test_avg_sentence_length(self):
        """Calcula longitud media de oración."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        # 3 oraciones de ~3 palabras cada una
        text = "Esto es corto. Muy breve también. Otra frase aquí."
        metrics = compute_chapter_metrics(text)
        assert "avg_sentence_length" in metrics
        assert 2.0 <= metrics["avg_sentence_length"] <= 4.0

    def test_scene_count_no_breaks(self):
        """Sin separadores de escena, cuenta 1."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = "Un párrafo de texto normal. Otro párrafo."
        metrics = compute_chapter_metrics(text)
        assert metrics["scene_count"] >= 1

    def test_scene_count_with_breaks(self):
        """Detecta separadores de escena ***."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = "Primera escena.\n\n* * *\n\nSegunda escena.\n\n* * *\n\nTercera escena."
        metrics = compute_chapter_metrics(text)
        assert metrics["scene_count"] >= 2

    def test_characters_present_count(self):
        """Cuenta personajes presentes."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = "Juan y María fueron al parque. Pedro se quedó en casa."
        metrics = compute_chapter_metrics(text, entity_names=["Juan", "María", "Pedro", "Ana"])
        assert metrics["characters_present_count"] == 3  # Juan, María, Pedro (no Ana)

    def test_tone_tense(self):
        """Detecta tono tenso."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = (
            "La muerte acechaba. El miedo paralizaba a todos. "
            "Un grito resonó en la oscuridad. Sangre en el suelo."
        )
        metrics = compute_chapter_metrics(text)
        assert metrics["dominant_tone"] == "tense"
        assert metrics["tone_intensity"] > 0.3

    def test_tone_positive(self):
        """Detecta tono positivo."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = (
            "El amor lo llenaba todo. Una sonrisa iluminaba la fiesta. "
            "La alegría era contagiosa. Un abrazo de esperanza."
        )
        metrics = compute_chapter_metrics(text)
        assert metrics["dominant_tone"] == "positive"

    def test_tone_neutral_for_plain_text(self):
        """Texto sin señales emocionales es neutral."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = "El hombre caminaba por la calle. Llevaba un paraguas. Llovía."
        metrics = compute_chapter_metrics(text)
        assert metrics["dominant_tone"] == "neutral"

    def test_metrics_dict_has_all_keys(self):
        """Verifica que las métricas contienen todas las claves esperadas."""
        from narrative_assistant.persistence.chapter import compute_chapter_metrics
        text = "Juan era alto y moreno. María tenía ojos verdes."
        metrics = compute_chapter_metrics(text)
        assert "reading_time_minutes" in metrics
        assert "dialogue_ratio" in metrics
        assert "avg_sentence_length" in metrics
        assert "scene_count" in metrics
        assert "dominant_tone" in metrics
        assert "tone_intensity" in metrics


class TestChapterDataEnrichment:
    """Tests para los campos de enriquecimiento de ChapterData."""

    def test_to_dict_includes_metrics(self):
        """to_dict incluye métricas cuando están presentes."""
        from narrative_assistant.persistence.chapter import ChapterData
        ch = ChapterData(
            id=1, project_id=1, chapter_number=1, title="Test",
            content="Texto", start_char=0, end_char=5, word_count=1,
            dialogue_ratio=0.25, dominant_tone="tense", tone_intensity=0.8,
        )
        d = ch.to_dict()
        assert "metrics" in d
        assert d["metrics"]["dialogue_ratio"] == 0.25
        assert d["metrics"]["dominant_tone"] == "tense"
        assert d["metrics"]["tone_intensity"] == 0.8

    def test_to_dict_empty_metrics_when_none(self):
        """to_dict retorna métricas vacías cuando no hay valores."""
        from narrative_assistant.persistence.chapter import ChapterData
        ch = ChapterData(
            id=1, project_id=1, chapter_number=1, title="Test",
            content="Texto", start_char=0, end_char=5, word_count=1,
        )
        d = ch.to_dict()
        assert "metrics" in d
        assert d["metrics"] == {}
