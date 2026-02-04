"""Tests para los modulos de exportacion."""

from datetime import datetime

import pytest

from narrative_assistant.exporters.character_sheets import (
    AlertSummary,
    AttributeInfo,
    CharacterSheet,
    MentionInfo,
    VoiceProfileSummary,
)
from narrative_assistant.exporters.style_guide import (
    DialogueStyle,
    EntityListing,
    NumberStyle,
    SpellingDecision,
    StyleAnalyzer,
    StyleGuide,
)

# ============================================================================
# Tests para CharacterSheet
# ============================================================================


class TestCharacterSheet:
    """Tests para fichas de personaje."""

    @pytest.fixture
    def sample_sheet(self):
        """Crea una ficha de ejemplo."""
        return CharacterSheet(
            entity_id=1,
            canonical_name="Maria Garcia",
            aliases=["Maria", "La profesora"],
            entity_type="character",
            importance="high",
            physical_attributes=[
                AttributeInfo(
                    category="physical",
                    key="eye_color",
                    value="verdes",
                    confidence=0.9,
                    first_mentioned_chapter=1,
                    occurrences=3,
                    excerpts=["sus ojos verdes brillaban"],
                ),
                AttributeInfo(
                    category="physical",
                    key="hair_color",
                    value="castano",
                    confidence=0.85,
                    first_mentioned_chapter=1,
                ),
            ],
            psychological_attributes=[
                AttributeInfo(
                    category="psychological",
                    key="personality",
                    value="introvertida",
                    confidence=0.7,
                    first_mentioned_chapter=2,
                )
            ],
            other_attributes=[],
            mentions=MentionInfo(
                total_mentions=25,
                chapters=[1, 2, 3, 4],
                mention_frequency={1: 10, 2: 8, 3: 5, 4: 2},
                first_appearance_chapter=1,
                last_appearance_chapter=4,
            ),
            project_id=1,
            confidence_score=0.8,
        )

    def test_to_dict(self, sample_sheet):
        """Test conversion a diccionario."""
        data = sample_sheet.to_dict()

        assert data["entity_id"] == 1
        assert data["canonical_name"] == "Maria Garcia"
        assert len(data["physical_attributes"]) == 2
        assert data["mentions"]["total_mentions"] == 25

    def test_to_json(self, sample_sheet):
        """Test conversion a JSON."""
        json_str = sample_sheet.to_json()

        assert "Maria Garcia" in json_str
        assert "verdes" in json_str
        assert '"entity_id": 1' in json_str

    def test_to_markdown(self, sample_sheet):
        """Test conversion a Markdown."""
        md = sample_sheet.to_markdown()

        assert "# Maria Garcia" in md
        assert "verdes" in md
        assert "castano" in md
        assert "Total de menciones:" in md
        assert "Capítulo 1" in md

    def test_to_markdown_with_voice_profile(self, sample_sheet):
        """Test Markdown con perfil de voz."""
        sample_sheet.voice_profile = VoiceProfileSummary(
            total_interventions=15,
            avg_intervention_length=12.5,
            formality_score=0.7,
            type_token_ratio=0.65,
            uses_usted=True,
            uses_tu=False,
            characteristic_fillers=["bueno", "pues"],
            predominant_register="formal",
        )

        md = sample_sheet.to_markdown()

        assert "Perfil de Voz" in md
        assert "15" in md  # intervenciones
        assert "12.5" in md  # longitud media
        assert "bueno" in md

    def test_to_markdown_with_alerts(self, sample_sheet):
        """Test Markdown con alertas."""
        sample_sheet.alerts = AlertSummary(
            total_alerts=3,
            by_category={"consistency": 2, "style": 1},
            critical_count=1,
            warning_count=2,
            descriptions=["Color de ojos inconsistente", "Edad contradictoria"],
        )

        md = sample_sheet.to_markdown()

        assert "Alertas e Inconsistencias" in md
        assert "Total alertas:** 3" in md
        assert "Color de ojos inconsistente" in md


# ============================================================================
# Tests para StyleAnalyzer
# ============================================================================


class TestStyleAnalyzer:
    """Tests para el analizador de estilo."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador de estilo."""
        return StyleAnalyzer()

    def test_detect_raya_dialogue(self, analyzer):
        """Test deteccion de dialogos con raya."""
        text = """
        —Hola, ¿como estas? —pregunto Maria.
        —Muy bien, gracias —respondio Juan—. ¿Y tu?
        """
        result = analyzer.analyze(text)

        assert result.dialogue_style == DialogueStyle.RAYA.value
        assert any(p.name == "Raya española" for p in result.dialogue_patterns)

    def test_detect_guillemet_dialogue(self, analyzer):
        """Test deteccion de dialogos con comillas angulares."""
        text = """
        «Hola, ¿como estas?», pregunto Maria.
        «Muy bien, gracias», respondio Juan.
        """
        result = analyzer.analyze(text)

        assert result.dialogue_style == DialogueStyle.GUILLEMETS.value

    def test_detect_mixed_dialogue(self, analyzer):
        """Test deteccion de dialogos mixtos."""
        text = """
        —Hola —dijo Maria.
        «Adios», respondio Juan.
        "¿Que tal?", pregunto Pedro.
        """
        result = analyzer.analyze(text)

        assert result.dialogue_style == DialogueStyle.MIXED.value

    def test_punctuation_analysis(self, analyzer):
        """Test analisis de puntuacion."""
        text = """
        Esta es una oracion larga; con punto y coma.
        Otra oracion... con puntos suspensivos.
        Y otra mas; tambien con punto y coma.
        """
        result = analyzer.analyze(text)

        semicolon_pattern = [p for p in result.punctuation_patterns if p.name == "Punto y coma"]
        assert len(semicolon_pattern) == 1
        assert semicolon_pattern[0].frequency == 2

    def test_number_analysis_digits(self, analyzer):
        """Test analisis de numeros en cifras."""
        text = """
        El coche tenia 4 puertas y costaba 15000 euros.
        Condujo 200 kilometros en 3 horas.
        """
        result = analyzer.analyze(text)

        assert "digits" in result.number_examples
        assert len(result.number_examples["digits"]) > 0

    def test_number_analysis_words(self, analyzer):
        """Test analisis de numeros en palabras."""
        text = """
        Habia tres manzanas sobre la mesa.
        Caminaron dos horas y descansaron cinco minutos.
        """
        result = analyzer.analyze(text)

        assert "words" in result.number_examples
        assert len(result.number_examples["words"]) > 0

    def test_statistics(self, analyzer):
        """Test estadisticas del texto."""
        text = """
        Esta es una oracion. Esta es otra oracion. Y una tercera.
        """
        result = analyzer.analyze(text)

        assert result.statistics.total_sentences == 3
        assert result.statistics.total_words > 0
        assert result.statistics.vocabulary_richness > 0


# ============================================================================
# Tests para StyleGuide
# ============================================================================


class TestStyleGuide:
    """Tests para guia de estilo."""

    @pytest.fixture
    def sample_guide(self):
        """Crea guia de estilo de ejemplo."""
        return StyleGuide(
            project_name="Mi Novela",
            project_id=1,
            generated_date="2024-01-15 10:30:00",
            spelling_decisions=[
                SpellingDecision(
                    canonical_form="Maria",
                    variants=["María"],
                    frequency={"Maria": 10, "María": 2},
                    recommendation="canonical",
                    notes="Con acento grafico",
                )
            ],
            characters=[
                EntityListing(
                    type="character",
                    canonical_name="Maria Garcia",
                    aliases=["Maria"],
                    importance="high",
                    first_mention_chapter=1,
                )
            ],
            locations=[
                EntityListing(
                    type="location",
                    canonical_name="Madrid",
                    aliases=["la capital"],
                    importance="medium",
                )
            ],
            organizations=[],
            total_entities=2,
            total_spelling_variants=1,
        )

    def test_to_dict(self, sample_guide):
        """Test conversion a diccionario."""
        data = sample_guide.to_dict()

        assert data["project_name"] == "Mi Novela"
        assert len(data["characters"]) == 1
        assert len(data["spelling_decisions"]) == 1

    def test_to_json(self, sample_guide):
        """Test conversion a JSON."""
        json_str = sample_guide.to_json()

        assert "Mi Novela" in json_str
        assert "Maria Garcia" in json_str

    def test_to_markdown(self, sample_guide):
        """Test conversion a Markdown."""
        md = sample_guide.to_markdown()

        assert "# Guía de Estilo - Mi Novela" in md
        assert "Maria Garcia" in md
        assert "Madrid" in md
        assert "Decisiones de Grafía" in md

    def test_to_markdown_with_style_analysis(self, sample_guide):
        """Test Markdown con analisis estilistico."""
        from narrative_assistant.exporters.style_guide import (
            StyleAnalysis,
            StylePattern,
            TextStatistics,
        )

        sample_guide.style_analysis = StyleAnalysis(
            dialogue_style="raya",
            dialogue_patterns=[
                StylePattern(
                    name="Raya española",
                    description="Dialogos con raya",
                    frequency=50,
                    examples=["—Hola —dijo"],
                    recommendation="Estilo correcto",
                )
            ],
            punctuation_patterns=[],
            uses_oxford_comma=False,
            semicolon_frequency="bajo",
            number_style="words_under_10",
            number_examples={"words": ["tres", "dos"], "digits": ["100"]},
            capitalization_rules=[],
            foreign_word_style="italic",
            foreign_examples=["weekend", "email"],
            predominant_register="neutral",
            formality_level="medium",
            statistics=TextStatistics(
                total_words=5000,
                total_sentences=250,
                avg_sentence_length=20.0,
                vocabulary_richness=0.45,
            ),
            consistency_issues=[],
            recommendations=["Uso correcto de raya"],
        )

        md = sample_guide.to_markdown()

        assert "Análisis Estilístico" in md
        assert "5,000" in md or "5000" in md
        assert "Raya española" in md


# ============================================================================
# Tests de integracion
# ============================================================================


class TestExportersIntegration:
    """Tests de integracion para exportadores."""

    def test_character_sheet_complete_workflow(self):
        """Test flujo completo de ficha de personaje."""
        sheet = CharacterSheet(
            entity_id=1,
            canonical_name="Protagonista",
            aliases=["El heroe"],
            entity_type="character",
            importance="principal",
            physical_attributes=[],
            psychological_attributes=[],
            other_attributes=[],
            mentions=MentionInfo(
                total_mentions=100,
                chapters=[1, 2, 3],
                mention_frequency={1: 50, 2: 30, 3: 20},
                first_appearance_chapter=1,
                last_appearance_chapter=3,
            ),
            voice_profile=VoiceProfileSummary(
                total_interventions=30,
                avg_intervention_length=15.0,
                formality_score=0.5,
                type_token_ratio=0.6,
                uses_usted=False,
                uses_tu=True,
                characteristic_fillers=["vale", "entonces"],
            ),
            alerts=AlertSummary(
                total_alerts=2,
                by_category={"consistency": 2},
                critical_count=0,
                warning_count=2,
                descriptions=["Altura inconsistente"],
            ),
            project_id=1,
            confidence_score=0.85,
        )

        # Probar todas las exportaciones
        data = sheet.to_dict()
        json_str = sheet.to_json()
        md = sheet.to_markdown()

        assert data["canonical_name"] == "Protagonista"
        assert "Protagonista" in json_str
        assert "# Protagonista" in md
        assert "vale" in md  # muletilla
        assert "Altura inconsistente" in md  # alerta
