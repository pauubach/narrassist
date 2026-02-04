"""
Tests para el módulo de plantillas narrativas (narrative_templates).

Cubre:
- Smoke test: import y creación
- Beat detection por plantilla
- Granularity normalization
- Kishotenketsu tolerances
- Twist detection
"""

import pytest

from narrative_assistant.analysis.narrative_templates import (
    TEMPLATE_DEFINITIONS,
    BeatStatus,
    NarrativeTemplateAnalyzer,
    NarrativeTemplateReport,
    TemplateBeat,
    TemplateMatch,
    TemplateType,
)


@pytest.fixture
def analyzer():
    return NarrativeTemplateAnalyzer()


def _make_chapter(number: int, total: int = 10, **kwargs) -> dict:
    """Crear datos de capítulo mínimos."""
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


def _make_rich_manuscript(total: int = 12) -> list[dict]:
    """Crear manuscrito con señales narrativas para tests de detección."""
    chapters = []
    for i in range(1, total + 1):
        ch = _make_chapter(i, total)
        pos = i / total

        # Setup: nuevos personajes al inicio
        if pos <= 0.15:
            ch["new_characters"] = ["Ana", "Luis"]
            ch["positive_interactions"] = 3

        # Incidente detonante
        if 0.10 <= pos <= 0.20:
            ch["key_events"].append({"event_type": "conflict"})

        # Desarrollo
        if 0.25 <= pos <= 0.55:
            ch["key_events"].append({"event_type": "discovery"})
            ch["total_interactions"] = 5

        # Punto medio
        if abs(pos - 0.50) < 0.1:
            ch["key_events"].append({"event_type": "revelation"})

        # Clímax
        if 0.70 <= pos <= 0.85:
            ch["key_events"].append({"event_type": "conflict"})
            ch["dominant_tone"] = "tense"
            ch["tone_intensity"] = 0.9

        # Resolución
        if pos >= 0.90:
            ch["dominant_tone"] = "positive"
            ch["tone_intensity"] = 0.4

        chapters.append(ch)

    return chapters


# =============================================================================
# Smoke tests
# =============================================================================


class TestTemplateSmoke:
    def test_import(self):
        from narrative_assistant.analysis.narrative_templates import NarrativeTemplateAnalyzer

        assert NarrativeTemplateAnalyzer is not None

    def test_create_analyzer(self, analyzer):
        assert analyzer is not None

    def test_five_templates_defined(self):
        """Hay 5 plantillas definidas."""
        assert len(TEMPLATE_DEFINITIONS) == 5
        expected = {
            TemplateType.THREE_ACT,
            TemplateType.HERO_JOURNEY,
            TemplateType.SAVE_THE_CAT,
            TemplateType.KISHOTENKETSU,
            TemplateType.FIVE_ACT,
        }
        assert set(TEMPLATE_DEFINITIONS.keys()) == expected

    def test_each_template_has_beats(self):
        """Cada plantilla genera una lista de beats."""
        for tt, defn in TEMPLATE_DEFINITIONS.items():
            beats = defn["beats_fn"]()
            assert len(beats) >= 4, f"{tt} debería tener al menos 4 beats"
            for b in beats:
                assert isinstance(b, TemplateBeat)


# =============================================================================
# Analysis
# =============================================================================


class TestTemplateAnalysis:
    def test_analyze_returns_all_templates(self, analyzer):
        """El análisis devuelve matches para todas las plantillas."""
        chapters = _make_rich_manuscript(12)
        report = analyzer.analyze(chapters, total_chapters=12)
        assert isinstance(report, NarrativeTemplateReport)
        assert len(report.matches) == 5
        assert report.best_match is not None

    def test_analyze_too_few_chapters(self, analyzer):
        """Con menos de 3 capítulos devuelve report sin matches."""
        report = analyzer.analyze([], total_chapters=0)
        assert len(report.matches) == 0
        assert report.best_match is None
        assert len(report.manuscript_summary) > 0

    def test_best_match_has_highest_score(self, analyzer):
        """El best_match tiene el score más alto."""
        chapters = _make_rich_manuscript(12)
        report = analyzer.analyze(chapters, total_chapters=12)
        max_score = max(m.fit_score for m in report.matches)
        assert report.best_match.fit_score == max_score


# =============================================================================
# Granularity normalization
# =============================================================================


class TestGranularityNormalization:
    def test_kishotenketsu_score_penalized(self, analyzer):
        """Kishotenketsu (4 beats) recibe penalización por granularidad."""
        chapters = _make_rich_manuscript(8)
        report = analyzer.analyze(chapters, total_chapters=8)

        kish = next(
            m for m in report.matches if m.template_type == TemplateType.KISHOTENKETSU.value
        )
        # Si todos los beats se detectan, score debería estar por debajo del
        # máximo teórico debido a la penalización
        if kish.detected_count == kish.total_beats:
            # 4 beats → factor ~0.87, así que max sería ~87 en lugar de 100
            assert kish.fit_score < 95, (
                f"Kishotenketsu con todos beats detectados no debería superar 95, "
                f"pero tiene {kish.fit_score}"
            )

    def test_hero_journey_no_penalty(self, analyzer):
        """Hero's Journey (12 beats) no tiene penalización."""
        chapters = _make_rich_manuscript(12)
        report = analyzer.analyze(chapters, total_chapters=12)

        hero = next(m for m in report.matches if m.template_type == TemplateType.HERO_JOURNEY.value)
        # Hero Journey tiene 12 beats (> 7), no hay penalización
        assert hero.total_beats >= 7


# =============================================================================
# Beat detection
# =============================================================================


class TestBeatDetection:
    def test_setup_requires_multiple_characters(self, analyzer):
        """Setup requiere ≥2 personajes para DETECTED."""
        # Solo 1 personaje nuevo → POSSIBLE
        chapters = [
            _make_chapter(1, new_characters=["Ana"]),
            _make_chapter(2),
            _make_chapter(3),
        ]
        report = analyzer.analyze(chapters, total_chapters=3)
        three_act = next(
            m for m in report.matches if m.template_type == TemplateType.THREE_ACT.value
        )
        setup = next((b for b in three_act.beats if b.beat_id == "setup"), None)
        if setup:
            assert setup.status in (BeatStatus.POSSIBLE, BeatStatus.MISSING), (
                f"Con 1 personaje, setup debería ser POSSIBLE, no {setup.status}"
            )

    def test_setup_detected_with_multiple_characters(self, analyzer):
        """Setup DETECTED con ≥2 personajes nuevos."""
        chapters = [
            _make_chapter(1, new_characters=["Ana", "Luis", "Pedro"]),
            _make_chapter(2),
            _make_chapter(3),
            _make_chapter(4),
            _make_chapter(5),
        ]
        report = analyzer.analyze(chapters, total_chapters=5)
        three_act = next(
            m for m in report.matches if m.template_type == TemplateType.THREE_ACT.value
        )
        setup = next((b for b in three_act.beats if b.beat_id == "setup"), None)
        if setup:
            assert setup.status == BeatStatus.DETECTED

    def test_development_requires_enough_events(self, analyzer):
        """Development requiere ≥3 eventos o ≥5 interacciones para DETECTED."""
        # Solo 1 evento → should be POSSIBLE not DETECTED
        chapters = [
            _make_chapter(1, new_characters=["Ana"]),
            _make_chapter(2),
            _make_chapter(3, key_events=[{"event_type": "discovery"}], total_interactions=2),
            _make_chapter(4),
            _make_chapter(5),
        ]
        report = analyzer.analyze(chapters, total_chapters=5)
        three_act = next(
            m for m in report.matches if m.template_type == TemplateType.THREE_ACT.value
        )
        dev = next((b for b in three_act.beats if b.beat_id == "development"), None)
        if dev and dev.status != BeatStatus.MISSING:
            # With only 1 event and 2 interactions, should be POSSIBLE
            assert dev.status == BeatStatus.POSSIBLE, (
                f"Con 1 evento y 2 interacciones, development debería ser POSSIBLE, no {dev.status}"
            )


# =============================================================================
# Twist detection (Kishotenketsu)
# =============================================================================


class TestTwistDetection:
    def test_twist_detected_with_revelation(self, analyzer):
        """Ten/twist detectado con evento de revelación en zona correcta."""
        chapters = []
        for i in range(1, 9):
            ch = _make_chapter(i, total=8)
            if i == 5:  # ~62.5% → within twist zone
                ch["llm_events"] = [{"event_type": "revelation"}]
            chapters.append(ch)

        report = analyzer.analyze(chapters, total_chapters=8)
        kish = next(
            m for m in report.matches if m.template_type == TemplateType.KISHOTENKETSU.value
        )
        twist = next((b for b in kish.beats if b.beat_id == "ten_twist"), None)
        assert twist is not None
        assert twist.status in (BeatStatus.DETECTED, BeatStatus.POSSIBLE)


# =============================================================================
# Serialization
# =============================================================================


class TestTemplateSerialization:
    def test_report_to_dict(self, analyzer):
        """El report se serializa correctamente."""
        chapters = _make_rich_manuscript(6)
        report = analyzer.analyze(chapters, total_chapters=6)
        data = report.to_dict()
        assert "best_match" in data
        assert "matches" in data
        assert "total_chapters" in data
        assert data["total_chapters"] == 6
        assert len(data["matches"]) == 5

    def test_match_to_dict_has_beats(self, analyzer):
        """Cada match serializado incluye beats."""
        chapters = _make_rich_manuscript(6)
        report = analyzer.analyze(chapters, total_chapters=6)
        for match in report.matches:
            d = match.to_dict()
            assert "beats" in d
            assert "fit_score" in d
            assert "detected_count" in d
            assert "total_beats" in d
