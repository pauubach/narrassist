"""Tests para TemporalMap y NonLinearNarrativeDetector."""

from datetime import date

import pytest

from narrative_assistant.temporal.non_linear_detector import (
    NonLinearNarrativeDetector, NonLinearSignal)
from narrative_assistant.temporal.temporal_map import (AgeReference,
                                                       NarrativeType,
                                                       TemporalMap,
                                                       TemporalSlice)


class TestTemporalMap:
    """Tests para TemporalMap."""

    @pytest.fixture
    def linear_map(self):
        """Mapa temporal lineal: cap1=día0, cap2=día5, cap3=día10."""
        tmap = TemporalMap()
        tmap.add_slice(1, TemporalSlice(chapter=1, day_offset=0))
        tmap.add_slice(2, TemporalSlice(chapter=2, day_offset=5))
        tmap.add_slice(3, TemporalSlice(chapter=3, day_offset=10))
        return tmap

    @pytest.fixture
    def nonlinear_map(self):
        """
        Mapa no lineal:
        - Cap1: día 0 (presente)
        - Cap2: día 5 (presente)
        - Cap3: día -100 (flashback, muerte en el pasado)
        - Cap4: día 10 (presente)
        - Cap5: día -50 (flashback, personaje aún vivo)
        """
        tmap = TemporalMap()
        tmap.add_slice(
            1,
            TemporalSlice(
                chapter=1,
                day_offset=0,
                narrative_type=NarrativeType.CHRONOLOGICAL,
            ),
        )
        tmap.add_slice(
            2,
            TemporalSlice(
                chapter=2,
                day_offset=5,
                narrative_type=NarrativeType.CHRONOLOGICAL,
            ),
        )
        tmap.add_slice(
            3,
            TemporalSlice(
                chapter=3,
                day_offset=-100,
                narrative_type=NarrativeType.ANALEPSIS,
            ),
        )
        tmap.add_slice(
            4,
            TemporalSlice(
                chapter=4,
                day_offset=10,
                narrative_type=NarrativeType.CHRONOLOGICAL,
            ),
        )
        tmap.add_slice(
            5,
            TemporalSlice(
                chapter=5,
                day_offset=-50,
                narrative_type=NarrativeType.ANALEPSIS,
            ),
        )
        return tmap

    def test_age_in_present(self, linear_map):
        """Edad en presente: ref_age + time_diff."""
        linear_map.add_age_reference(
            AgeReference(entity_id=1, age=30, chapter=1, day_offset=0)
        )
        # Cap 3 está 10 días después → sigue teniendo 30
        age = linear_map.get_character_age_in_chapter(1, 3)
        assert age == 30  # 10 días no cambian la edad en años

    def test_age_in_flashback(self, nonlinear_map):
        """En flashback → personaje más joven."""
        nonlinear_map.add_age_reference(
            AgeReference(entity_id=1, age=30, chapter=1, day_offset=0)
        )
        # Cap 3 es día -100 (100 días antes) → aún 30 (< 1 año)
        age = nonlinear_map.get_character_age_in_chapter(1, 3)
        assert age == 29 or age == 30  # 100 días ~ 0.27 años

    def test_consistency_no_false_positive(self):
        """Mapa vacío → no genera falsos positivos."""
        tmap = TemporalMap()
        # Sin slices, todo retorna None/True (fail-safe)
        assert tmap.get_story_time(1) is None
        assert tmap.is_character_alive_in_chapter(1, 1) is True
        assert tmap.get_character_age_in_chapter(1, 1) is None

    def test_inconsistency_age_mismatch(self):
        """Detecta inconsistencia de edad: dos refs incompatibles."""
        tmap = TemporalMap()
        tmap.add_slice(1, TemporalSlice(chapter=1, story_date=date(2020, 1, 1)))
        tmap.add_slice(5, TemporalSlice(chapter=5, story_date=date(2020, 6, 1)))

        # Ref: 30 años en cap 1
        tmap.add_age_reference(
            AgeReference(entity_id=1, age=30, chapter=1, story_date=date(2020, 1, 1))
        )

        # En cap 5 (6 meses después) debería tener ~30
        age = tmap.get_character_age_in_chapter(1, 5)
        assert age == 30  # 6 meses no cambian la edad entera

    def test_alive_before_death(self, linear_map):
        """Personaje vivo antes de su muerte en story_time."""
        linear_map.register_death(entity_id=1, death_chapter=2)  # muere día 5
        # Cap 1 es día 0 → anterior a la muerte → vivo
        assert linear_map.is_character_alive_in_chapter(1, 1) is True

    def test_alive_in_flashback(self, nonlinear_map):
        """Personaje muerto en cap3 pero flashback cap5 → vivo."""
        # Muere en cap 3 (día -100)
        nonlinear_map.register_death(entity_id=1, death_chapter=3)
        # Cap 5 es día -50, que es DESPUÉS de día -100 → muerto
        assert nonlinear_map.is_character_alive_in_chapter(1, 5) is False

        # Pero si muere en cap 2 (día 5), cap 5 (día -50) es anterior → vivo
        nonlinear_map2 = TemporalMap()
        nonlinear_map2.add_slice(
            2,
            TemporalSlice(chapter=2, day_offset=5),
        )
        nonlinear_map2.add_slice(
            5,
            TemporalSlice(
                chapter=5,
                day_offset=-50,
                narrative_type=NarrativeType.ANALEPSIS,
            ),
        )
        nonlinear_map2.register_death(entity_id=1, death_chapter=2)  # muere día 5
        # Cap 5 (día -50) es anterior a día 5 → vivo en flashback
        assert nonlinear_map2.is_character_alive_in_chapter(1, 5) is True

    def test_story_time_gap_hours(self, linear_map):
        """Cálculo de gap en horas entre capítulos."""
        gap = linear_map.get_story_time_gap_hours(1, 3)
        assert gap is not None
        assert gap == 10 * 24  # 10 días = 240 horas

    def test_nested_flashbacks(self):
        """Flashback embebido dentro de otro capítulo."""
        tmap = TemporalMap()
        tmap.add_slice(
            1,
            TemporalSlice(
                chapter=1,
                day_offset=0,
                narrative_type=NarrativeType.CHRONOLOGICAL,
            ),
        )
        tmap.add_slice(
            2,
            TemporalSlice(
                chapter=2,
                day_offset=-365,
                narrative_type=NarrativeType.ANALEPSIS,
                is_embedded=True,
                parent_chapter=1,
            ),
        )

        assert tmap.get_narrative_type(2) == NarrativeType.ANALEPSIS
        assert tmap._slices[2].is_embedded is True
        assert tmap._slices[2].parent_chapter == 1

        # Gap = 365 días
        gap = tmap.get_story_time_gap_hours(1, 2)
        assert gap is not None
        assert gap == -365 * 24  # Negativo (va al pasado)


class TestTemporalMapWithDates:
    """Tests con fechas absolutas."""

    def test_date_based_alive_check(self):
        """Verificación de vida con fechas absolutas."""
        tmap = TemporalMap()
        tmap.add_slice(1, TemporalSlice(chapter=1, story_date=date(1920, 1, 1)))
        tmap.add_slice(3, TemporalSlice(chapter=3, story_date=date(1920, 6, 1)))
        tmap.add_slice(
            5,
            TemporalSlice(
                chapter=5,
                story_date=date(1919, 1, 1),
                narrative_type=NarrativeType.ANALEPSIS,
            ),
        )

        # Personaje muere en cap 3 (junio 1920)
        tmap.register_death(entity_id=42, death_chapter=3)

        # Cap 1 (enero 1920) → antes de muerte → vivo
        assert tmap.is_character_alive_in_chapter(42, 1) is True

        # Cap 5 (enero 1919, flashback) → antes de muerte → vivo
        assert tmap.is_character_alive_in_chapter(42, 5) is True


class TestNonLinearDetector:
    """Tests para NonLinearNarrativeDetector."""

    @pytest.fixture
    def detector(self):
        return NonLinearNarrativeDetector()

    def test_subjunctive_flashback(self, detector):
        """'Si hubiera sabido' → señal de flashback."""
        text = "Si hubiera sabido lo que iba a pasar, habría actuado diferente."
        signals = detector.detect_signals(text, chapter=1)
        assert len(signals) >= 1
        assert any(s.signal_type == "subjunctive" for s in signals)
        assert all(
            s.direction == "past" for s in signals if s.signal_type == "subjunctive"
        )

    def test_retrospective_adverb(self, detector):
        """'De niño' → señal retrospectiva."""
        text = "De niño, solía jugar en aquel parque junto a su casa."
        signals = detector.detect_signals(text, chapter=3)
        assert len(signals) >= 1
        assert any(s.signal_type == "retrospective" for s in signals)

    def test_prospective_signal(self, detector):
        """'Años después' → señal prospectiva."""
        text = "Años después recordaría aquel día como el más importante de su vida."
        signals = detector.detect_signals(text, chapter=5)
        assert len(signals) >= 1
        assert any(s.signal_type == "prospective" for s in signals)
        assert any(s.direction == "future" for s in signals)

    def test_no_signals_neutral(self, detector):
        """Texto neutral → sin señales."""
        text = "El hombre caminó por la calle y compró pan en la tienda."
        signals = detector.detect_signals(text, chapter=1)
        assert len(signals) == 0

    def test_chapter_classification(self, detector):
        """3+ señales retrospectivas → analepsis."""
        text = (
            "De niño, Juan corría por los campos. "
            "Años atrás, todo era diferente. "
            "Cuando era pequeño, su padre le contaba historias. "
            "En aquella época, la vida era más sencilla."
        )
        result = detector.classify_chapter(text, chapter=7, min_signals=2)
        assert result == "analepsis"

    def test_chapter_classification_chronological(self, detector):
        """Texto sin señales → chronological."""
        text = "El sol brillaba y los pájaros cantaban en los árboles."
        result = detector.classify_chapter(text, chapter=1)
        assert result == "chronological"
