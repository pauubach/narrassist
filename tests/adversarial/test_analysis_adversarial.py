"""
Tests adversariales para los módulos de análisis avanzado.

Verifica comportamiento robusto ante inputs extremos:
- Manuscrito vacío (0 capítulos)
- Manuscrito de 1 solo capítulo
- Manuscrito con HTML embebido en campos de texto
- Entidades con nombres extremos
- Datos faltantes o parciales
"""

import pytest

from narrative_assistant.analysis.character_archetypes import (
    ArchetypeReport,
    CharacterArchetypeAnalyzer,
)
from narrative_assistant.analysis.narrative_health import (
    HealthStatus,
    NarrativeHealthChecker,
    NarrativeHealthReport,
)
from narrative_assistant.analysis.narrative_templates import (
    NarrativeTemplateAnalyzer,
    NarrativeTemplateReport,
)
from narrative_assistant.nlp.style.sentence_energy import SentenceEnergyDetector

# =============================================================================
# Helpers
# =============================================================================


def _make_chapter(number: int, **kwargs) -> dict:
    ch = {
        "chapter_number": number,
        "word_count": 2000,
        "new_characters": [],
        "key_events": [],
        "llm_events": [],
        "dominant_tone": "neutral",
        "tone_intensity": 0.3,
        "conflict_interactions": 0,
        "positive_interactions": 0,
        "total_interactions": 0,
        "location_changes": 0,
    }
    ch.update(kwargs)
    return ch


def _make_entity(eid: int, name: str, **kwargs) -> dict:
    ent = {
        "id": eid,
        "name": name,
        "entity_type": "character",
        "importance": "secondary",
        "mention_count": 10,
        "chapter_count": 3,
    }
    ent.update(kwargs)
    return ent


# =============================================================================
# Narrative Health - Adversarial
# =============================================================================


class TestNarrativeHealthAdversarial:
    @pytest.fixture
    def checker(self):
        return NarrativeHealthChecker()

    def test_zero_chapters(self, checker):
        """0 capítulos: report válido con score 0 y status CRITICAL."""
        report = checker.check(chapters_data=[], total_chapters=0)
        assert isinstance(report, NarrativeHealthReport)
        assert report.overall_score == 0
        assert report.overall_status == HealthStatus.CRITICAL

    def test_one_chapter(self, checker):
        """1 capítulo: report válido con score 0 y status CRITICAL."""
        report = checker.check(
            chapters_data=[_make_chapter(1)],
            total_chapters=1,
        )
        assert isinstance(report, NarrativeHealthReport)
        assert report.overall_score == 0
        assert report.overall_status == HealthStatus.CRITICAL

    def test_html_in_chapter_events(self, checker):
        """HTML embebido en eventos no causa crash."""
        chapters = [
            _make_chapter(
                1,
                key_events=[
                    {"event_type": '<script>alert("xss")</script>'},
                ],
            ),
            _make_chapter(
                2,
                key_events=[
                    {"event_type": '<img src=x onerror="alert(1)">'},
                ],
            ),
            _make_chapter(3),
        ]
        report = checker.check(chapters_data=chapters, total_chapters=3)
        assert isinstance(report, NarrativeHealthReport)
        assert report.overall_score >= 0

    def test_html_in_entity_names(self, checker):
        """HTML en nombres de entidad no causa crash."""
        entities = [
            {
                "entity_type": "character",
                "name": "<b>María</b>",
                "mention_count": 30,
                "chapters_present": 5,
            },
            {
                "entity_type": "character",
                "name": '"><script>',
                "mention_count": 10,
                "chapters_present": 2,
            },
        ]
        chapters = [_make_chapter(i) for i in range(1, 4)]
        report = checker.check(
            chapters_data=chapters,
            total_chapters=3,
            entities_data=entities,
        )
        assert isinstance(report, NarrativeHealthReport)

    def test_extreme_word_counts(self, checker):
        """Capítulos con word_count 0 y muy alto no causan crash."""
        chapters = [
            _make_chapter(1, word_count=0),
            _make_chapter(2, word_count=1_000_000),
            _make_chapter(3, word_count=1),
        ]
        report = checker.check(chapters_data=chapters, total_chapters=3)
        assert isinstance(report, NarrativeHealthReport)

    def test_all_same_tone(self, checker):
        """Todos los capítulos con el mismo tono: no crash, coherencia alta."""
        chapters = [_make_chapter(i, dominant_tone="positive") for i in range(1, 6)]
        report = checker.check(chapters_data=chapters, total_chapters=5)
        assert isinstance(report, NarrativeHealthReport)


# =============================================================================
# Narrative Templates - Adversarial
# =============================================================================


class TestNarrativeTemplatesAdversarial:
    @pytest.fixture
    def analyzer(self):
        return NarrativeTemplateAnalyzer()

    def test_zero_chapters(self, analyzer):
        """0 capítulos: report vacío sin crash."""
        report = analyzer.analyze(chapters_data=[], total_chapters=0)
        assert isinstance(report, NarrativeTemplateReport)
        assert len(report.matches) == 0
        assert report.best_match is None

    def test_one_chapter(self, analyzer):
        """1 capítulo: report vacío (mínimo 3 para análisis)."""
        report = analyzer.analyze(
            chapters_data=[_make_chapter(1)],
            total_chapters=1,
        )
        assert isinstance(report, NarrativeTemplateReport)
        assert len(report.matches) == 0

    def test_two_chapters(self, analyzer):
        """2 capítulos: report vacío (mínimo 3)."""
        chapters = [_make_chapter(1), _make_chapter(2)]
        report = analyzer.analyze(chapters_data=chapters, total_chapters=2)
        assert isinstance(report, NarrativeTemplateReport)
        assert len(report.matches) == 0

    def test_three_chapters_minimal(self, analyzer):
        """3 capítulos vacíos: report con 5 matches, no crash."""
        chapters = [_make_chapter(i) for i in range(1, 4)]
        report = analyzer.analyze(chapters_data=chapters, total_chapters=3)
        assert isinstance(report, NarrativeTemplateReport)
        assert len(report.matches) == 5

    def test_html_in_events(self, analyzer):
        """HTML en eventos de capítulos no causa crash."""
        chapters = [
            _make_chapter(
                1,
                key_events=[
                    {"event_type": "<script>alert(1)</script>"},
                ],
            ),
            _make_chapter(2),
            _make_chapter(3),
            _make_chapter(4),
        ]
        report = analyzer.analyze(chapters_data=chapters, total_chapters=4)
        assert isinstance(report, NarrativeTemplateReport)

    def test_very_long_manuscript(self, analyzer):
        """100 capítulos: no crash, report con 5 matches."""
        chapters = [_make_chapter(i) for i in range(1, 101)]
        report = analyzer.analyze(chapters_data=chapters, total_chapters=100)
        assert isinstance(report, NarrativeTemplateReport)
        assert len(report.matches) == 5


# =============================================================================
# Character Archetypes - Adversarial
# =============================================================================


class TestCharacterArchetypesAdversarial:
    @pytest.fixture
    def analyzer(self):
        return CharacterArchetypeAnalyzer()

    def test_zero_entities(self, analyzer):
        """0 entidades: report vacío sin crash."""
        report = analyzer.analyze(
            entities=[],
            character_arcs=[],
            relationships=[],
            interactions=[],
            total_chapters=5,
        )
        assert isinstance(report, ArchetypeReport)
        assert len(report.characters) == 0

    def test_one_entity_no_arcs(self, analyzer):
        """1 entidad sin arcos: report con 1 perfil."""
        entities = [_make_entity(1, "Ana", importance="protagonist")]
        report = analyzer.analyze(
            entities=entities,
            character_arcs=[],
            relationships=[],
            interactions=[],
            total_chapters=5,
        )
        assert isinstance(report, ArchetypeReport)
        assert len(report.characters) == 1

    def test_html_in_entity_name(self, analyzer):
        """HTML en nombre de entidad no causa crash."""
        entities = [
            _make_entity(1, '<script>alert("xss")</script>', importance="protagonist"),
        ]
        arcs = [
            {"character_id": 1, "arc_type": "growth", "trajectory": "rising", "completeness": 0.7}
        ]
        report = analyzer.analyze(
            entities=entities,
            character_arcs=arcs,
            relationships=[],
            interactions=[],
            total_chapters=5,
        )
        assert isinstance(report, ArchetypeReport)
        assert len(report.characters) == 1

    def test_many_entities(self, analyzer):
        """50 entidades: no crash."""
        entities = [_make_entity(i, f"Personaje_{i}", mention_count=50 - i) for i in range(1, 51)]
        report = analyzer.analyze(
            entities=entities,
            character_arcs=[],
            relationships=[],
            interactions=[],
            total_chapters=10,
        )
        assert isinstance(report, ArchetypeReport)
        assert len(report.characters) == 50

    def test_relationship_with_nonexistent_entity(self, analyzer):
        """Relación con entity_id que no existe: no crash."""
        entities = [_make_entity(1, "Ana")]
        relationships = [
            {
                "entity1_id": 1,
                "entity2_id": 999,  # No existe
                "relation_type": "RIVALRY",
                "subtype": "",
            }
        ]
        report = analyzer.analyze(
            entities=entities,
            character_arcs=[],
            relationships=relationships,
            interactions=[],
            total_chapters=5,
        )
        assert isinstance(report, ArchetypeReport)


# =============================================================================
# Sentence Energy - Adversarial
# =============================================================================


class TestSentenceEnergyAdversarial:
    @pytest.fixture
    def detector(self):
        return SentenceEnergyDetector()

    def test_empty_text(self, detector):
        """Texto vacío: resultado exitoso con 0 oraciones."""
        result = detector.analyze("")
        assert result.is_success
        assert len(result.value.sentences) == 0

    def test_only_whitespace(self, detector):
        """Solo espacios: resultado exitoso con 0 oraciones."""
        result = detector.analyze("   \n\t\n   ")
        assert result.is_success
        assert len(result.value.sentences) == 0

    def test_html_in_text(self, detector):
        """HTML en texto: se procesa sin crash."""
        text = '<script>alert("xss")</script> El gato corre. <img src=x onerror=alert(1)>'
        result = detector.analyze(text)
        assert result.is_success

    def test_single_character(self, detector):
        """Un solo carácter: no crash."""
        result = detector.analyze("A")
        assert result.is_success

    def test_very_long_sentence(self, detector):
        """Oración de 1000 palabras: no crash."""
        long_sentence = " ".join(["palabra"] * 1000) + "."
        result = detector.analyze(long_sentence)
        assert result.is_success

    def test_only_punctuation(self, detector):
        """Solo puntuación: no crash."""
        result = detector.analyze("...!?¿¡---***")
        assert result.is_success

    def test_unicode_text(self, detector):
        """Texto con Unicode diverso: no crash."""
        text = "日本語のテスト。中文测试。한국어 테스트."
        result = detector.analyze(text)
        assert result.is_success

    def test_numbers_only(self, detector):
        """Solo números: no crash."""
        result = detector.analyze("123 456 789. 10 20 30.")
        assert result.is_success

    def test_repeated_newlines(self, detector):
        """Muchos saltos de línea: no crash."""
        text = "El gato corre." + "\n" * 100 + "El perro ladra."
        result = detector.analyze(text)
        assert result.is_success
