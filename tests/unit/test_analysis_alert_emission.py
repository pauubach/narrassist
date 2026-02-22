import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api-server"))

from routers._analysis_phases import (  # noqa: E402
    _emit_consistency_alerts,
    _emit_grammar_alerts,
    _find_chapter_number_for_position,
    _to_optional_int,
)


class _OkResult:
    is_success = True


class _FakeAlertEngine:
    def __init__(self):
        self.attribute_calls = []
        self.grammar_calls = []
        self.correction_calls = []

    def create_from_attribute_inconsistency(self, **kwargs):
        self.attribute_calls.append(kwargs)
        return _OkResult()

    def create_from_grammar_issue(self, **kwargs):
        self.grammar_calls.append(kwargs)
        return _OkResult()

    def create_from_correction_issue(self, **kwargs):
        self.correction_calls.append(kwargs)
        return _OkResult()


def test_find_chapter_number_for_position_exact_and_nearest():
    chapters_data = [
        {"chapter_number": 1, "start_char": 0, "end_char": 100},
        {"chapter_number": 2, "start_char": 100, "end_char": 200},
        {"chapter_number": 3, "start_char": 200, "end_char": 350},
    ]

    assert _find_chapter_number_for_position(chapters_data, 150) == 2
    assert _find_chapter_number_for_position(chapters_data, 999) == 3
    assert _find_chapter_number_for_position([], 120) is None


def test_emit_consistency_alerts_includes_all_conflicting_values(monkeypatch):
    fake_engine = _FakeAlertEngine()

    import narrative_assistant.alerts.engine as alert_engine_module

    monkeypatch.setattr(alert_engine_module, "get_alert_engine", lambda: fake_engine)

    inconsistency = SimpleNamespace(
        entity_name="Elena Montero",
        entity_id=7,
        attribute_key="eye_color",
        value1="verdes",
        value2="azules",
        value1_chapter=1,
        value1_excerpt="ojos verdes",
        value1_position=15,
        value2_chapter=3,
        value2_excerpt="ojos azules",
        value2_position=230,
        confidence=0.95,
        explanation="Se encontraron 3 colores contradictorios.",
        conflicting_values=[
            {"value": "verdes", "chapter": 1, "position": 15, "excerpt": "ojos verdes"},
            {"value": "azules", "chapter": 3, "position": 230, "excerpt": "ojos azules"},
            # chapter ausente: debe inferirse por start_char
            {"value": "marrones", "chapter": None, "position": 520, "excerpt": "ojos marrones"},
        ],
    )

    ctx = {
        "project_id": 1,
        "chapters_data": [
            {"chapter_number": 1, "start_char": 0, "end_char": 120},
            {"chapter_number": 3, "start_char": 200, "end_char": 300},
            {"chapter_number": 7, "start_char": 500, "end_char": 700},
        ],
        "inconsistencies": [inconsistency],
        "vital_status_report": None,
        "location_report": None,
        "ooc_report": None,
        "anachronism_report": None,
    }

    _emit_consistency_alerts(ctx, tracker=None)

    assert len(fake_engine.attribute_calls) == 1
    call = fake_engine.attribute_calls[0]
    assert len(call["sources"]) == 3

    values = {src["value"] for src in call["sources"]}
    assert values == {"verdes", "azules", "marrones"}

    marrones_source = next(src for src in call["sources"] if src["value"] == "marrones")
    assert marrones_source["chapter"] == 7


def test_emit_grammar_alerts_infers_chapter_from_position(monkeypatch):
    fake_engine = _FakeAlertEngine()

    import narrative_assistant.alerts.engine as alert_engine_module

    monkeypatch.setattr(alert_engine_module, "get_alert_engine", lambda: fake_engine)

    grammar_issue = SimpleNamespace(
        text="hubieron",
        start_char=145,
        end_char=153,
        sentence="Hubieron muchos errores.",
        error_type=SimpleNamespace(value="subject_verb_agreement"),
        suggestion="hubo",
        confidence=0.9,
        explanation="Concordancia incorrecta.",
        rule_id="AGR001",
        chapter=None,
    )
    correction_issue = SimpleNamespace(
        category="typography",
        issue_type="double_space",
        text="  ",
        start_char=260,
        end_char=262,
        explanation="Espacio doble.",
        suggestion=" ",
        confidence=0.7,
        context="Texto con  doble espacio.",
        chapter_index=None,
        rule_id="TYPO001",
        extra_data={},
    )

    ctx = {
        "project_id": 1,
        "chapters_data": [
            {"chapter_number": 1, "start_char": 0, "end_char": 100},
            {"chapter_number": 2, "start_char": 100, "end_char": 200},
            {"chapter_number": 3, "start_char": 200, "end_char": 400},
        ],
        "grammar_issues": [grammar_issue],
        "correction_issues": [correction_issue],
    }

    _emit_grammar_alerts(ctx, tracker=None)

    assert len(fake_engine.grammar_calls) == 1
    assert fake_engine.grammar_calls[0]["chapter"] == 2

    assert len(fake_engine.correction_calls) == 1
    assert fake_engine.correction_calls[0]["chapter"] == 3


# ============================================================================
# Tests para _to_optional_int (cobertura de edge cases)
# ============================================================================


@pytest.mark.parametrize(
    "value,expected",
    [
        # Casos básicos
        (None, None),
        (42, 42),
        (0, 0),
        (-5, -5),
        # Floats
        (42.5, 42),
        (42.9, 42),
        (-3.7, -3),
        (0.0, 0),
        # Strings válidos
        ("123", 123),
        ("-456", -456),
        ("0", 0),
        ("  789  ", 789),  # con espacios
        ("  -5  ", -5),  # negativo con espacios
        # Strings inválidos
        ("", None),
        ("  ", None),
        ("abc", None),
        ("123abc", None),  # parcialmente numérico
        ("12.5", None),  # float como string (no es isdigit)
        # Booleans (deben retornar None, no 0/1)
        (True, None),
        (False, None),
        # Otros tipos
        ([], None),
        ({}, None),
        (object(), None),
    ],
)
def test_to_optional_int(value, expected):
    """Test comprehensive de _to_optional_int con todos los edge cases."""
    assert _to_optional_int(value) == expected


# ============================================================================
# Tests para _find_chapter_number_for_position (edge cases)
# ============================================================================


def test_find_chapter_number_for_position_at_boundary():
    """Test posición exacta en límite de capítulo."""
    chapters_data = [
        {"chapter_number": 1, "start_char": 0, "end_char": 100},
        {"chapter_number": 2, "start_char": 100, "end_char": 200},
    ]
    # Posición 100 es start de cap 2, debe retornar 2 (no 1)
    assert _find_chapter_number_for_position(chapters_data, 100) == 2


def test_find_chapter_number_for_position_with_malformed_data():
    """Test con chapters_data con valores missing/malformed."""
    chapters_data = [
        {"chapter_number": 1, "start_char": 0, "end_char": 100},
        {"chapter_number": None, "start_char": 100, "end_char": 200},  # chapter_number None
        {"chapter_number": 3, "start_char": None, "end_char": 300},  # start_char None
        {"chapter_number": 4, "start_char": 300, "end_char": None},  # end_char None
        {"chapter_number": 5, "start_char": 400, "end_char": 500},  # válido
    ]
    # Posición 450 debe encontrar capítulo 5 (ignorando los malformados)
    assert _find_chapter_number_for_position(chapters_data, 450) == 5


def test_find_chapter_number_for_position_nearest_fallback():
    """Test fallback a capítulo más cercano cuando no hay match exacto."""
    chapters_data = [
        {"chapter_number": 1, "start_char": 0, "end_char": 100},
        {"chapter_number": 2, "start_char": 200, "end_char": 300},  # gap: 100-200
        {"chapter_number": 3, "start_char": 400, "end_char": 500},
    ]
    # Posición 350 está en gap → debe retornar el más cercano (cap 3, start=400, dist=50)
    assert _find_chapter_number_for_position(chapters_data, 350) == 3

    # Posición 150 → cap 2 (start=200, dist=50) más cercano que cap 1 (end=100, dist=50)
    # Pero como cap 1 end=100 y cap 2 start=200, ambos están a 50
    # El algoritmo toma el primer candidato con mínima distancia (cap 1)
    result = _find_chapter_number_for_position(chapters_data, 150)
    assert result in [1, 2]  # Ambos son válidos en este caso (dist 50 vs 50)


def test_find_chapter_number_for_position_with_type_coercion():
    """Test con tipos heterogéneos (strings, floats) que necesitan coerción."""
    chapters_data = [
        {"chapter_number": "1", "start_char": "0", "end_char": "100"},  # strings
        {"chapter_number": 2.0, "start_char": 100.0, "end_char": 200.0},  # floats
    ]
    assert _find_chapter_number_for_position(chapters_data, 50) == 1
    assert _find_chapter_number_for_position(chapters_data, 150) == 2


def test_find_chapter_number_for_position_with_negative_start_char():
    """Test con start_char negativo (edge case inusual pero posible)."""
    chapters_data = [
        {"chapter_number": 1, "start_char": 0, "end_char": 100},
    ]
    # start_char negativo → fallback a capítulo más cercano (cap 1, dist=10)
    # Comportamiento actual: retorna cap 1 (no None)
    assert _find_chapter_number_for_position(chapters_data, -10) == 1


def test_find_chapter_number_for_position_empty_chapters():
    """Test con chapters_data vacío."""
    assert _find_chapter_number_for_position([], 120) is None


def test_find_chapter_number_for_position_none_position():
    """Test con start_char=None."""
    chapters_data = [
        {"chapter_number": 1, "start_char": 0, "end_char": 100},
    ]
    assert _find_chapter_number_for_position(chapters_data, None) is None


# ============================================================================
# Tests para deduplicación de sources en _emit_consistency_alerts
# ============================================================================


def test_emit_consistency_alerts_deduplicates_sources(monkeypatch):
    """Test que sources duplicadas se eliminan correctamente."""
    fake_engine = _FakeAlertEngine()

    import narrative_assistant.alerts.engine as alert_engine_module

    monkeypatch.setattr(alert_engine_module, "get_alert_engine", lambda: fake_engine)

    inconsistency = SimpleNamespace(
        entity_name="María",
        entity_id=5,
        attribute_key="age",
        value1="25",
        value2="30",
        value1_chapter=1,
        value1_excerpt="25 años",
        value1_position=10,
        value2_chapter=2,
        value2_excerpt="30 años",
        value2_position=110,
        confidence=0.8,
        explanation="Inconsistencia de edad",
        conflicting_values=[
            {"value": "25", "chapter": 1, "position": 10, "excerpt": "25 años"},
            {"value": "25", "chapter": 1, "position": 10, "excerpt": "25 años"},  # duplicado
            {"value": "30", "chapter": 2, "position": 110, "excerpt": "30 años"},
        ],
    )

    ctx = {
        "project_id": 1,
        "chapters_data": [
            {"chapter_number": 1, "start_char": 0, "end_char": 100},
            {"chapter_number": 2, "start_char": 100, "end_char": 200},
        ],
        "inconsistencies": [inconsistency],
        "vital_status_report": None,
        "location_report": None,
        "ooc_report": None,
        "anachronism_report": None,
    }

    _emit_consistency_alerts(ctx, tracker=None)

    assert len(fake_engine.attribute_calls) == 1
    sources = fake_engine.attribute_calls[0]["sources"]

    # Solo debe haber 2 sources únicas (deduplicadas)
    assert len(sources) == 2
    values = {src["value"] for src in sources}
    assert values == {"25", "30"}


def test_emit_consistency_alerts_fallback_to_value1_value2(monkeypatch):
    """Test fallback a value1/value2 cuando conflicting_values < 2."""
    fake_engine = _FakeAlertEngine()

    import narrative_assistant.alerts.engine as alert_engine_module

    monkeypatch.setattr(alert_engine_module, "get_alert_engine", lambda: fake_engine)

    inconsistency = SimpleNamespace(
        entity_name="Pedro",
        entity_id=3,
        attribute_key="hair_color",
        value1="negro",
        value2="rubio",
        value1_chapter=1,
        value1_excerpt="pelo negro",
        value1_position=15,
        value2_chapter=3,
        value2_excerpt="pelo rubio",
        value2_position=215,
        confidence=0.9,
        explanation="Inconsistencia de color de pelo",
        conflicting_values=[
            {"value": "negro", "chapter": 1, "position": 15, "excerpt": "pelo negro"}
        ],  # Solo 1 elemento → fallback
    )

    ctx = {
        "project_id": 1,
        "chapters_data": [
            {"chapter_number": 1, "start_char": 0, "end_char": 100},
            {"chapter_number": 3, "start_char": 200, "end_char": 300},
        ],
        "inconsistencies": [inconsistency],
        "vital_status_report": None,
        "location_report": None,
        "ooc_report": None,
        "anachronism_report": None,
    }

    _emit_consistency_alerts(ctx, tracker=None)

    assert len(fake_engine.attribute_calls) == 1
    sources = fake_engine.attribute_calls[0]["sources"]

    # Debe tener 2 sources: 1 de conflicting_values + 1 fallback de value2
    assert len(sources) == 2
    values = {src["value"] for src in sources}
    assert values == {"negro", "rubio"}
