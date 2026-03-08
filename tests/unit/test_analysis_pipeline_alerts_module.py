from types import SimpleNamespace

from narrative_assistant.analysis.attribute_consistency import AttributeInconsistency
from narrative_assistant.analysis.emotional_coherence import EmotionalIncoherence, IncoherenceType
from narrative_assistant.alerts.models import AlertCategory
from narrative_assistant.core.result import Result
from narrative_assistant.focalization.violations import (
    FocalizationViolation,
    ViolationSeverity,
    ViolationType,
)
from narrative_assistant.nlp.attributes import AttributeKey
from narrative_assistant.pipelines.analysis_pipeline_alerts import (
    create_alerts_from_emotional_incoherences,
    create_alerts_from_focalization_violations,
    create_alerts_from_inconsistencies,
    create_alerts_from_temporal_inconsistencies,
    create_alerts_from_voice_deviations,
)
from narrative_assistant.temporal.inconsistencies import (
    InconsistencySeverity,
    InconsistencyType,
    TemporalInconsistency,
)
from narrative_assistant.voice.deviations import (
    DeviationSeverity,
    DeviationType,
    VoiceDeviation,
)


class _FakeAlertEngine:
    def __init__(self):
        self.calls = []

    def create_from_attribute_inconsistency(self, **kwargs):
        self.calls.append(kwargs)
        return Result.success(SimpleNamespace(id=101))


class _FakeAlertRepo:
    def __init__(self):
        self.calls = []
        self._next_id = 1

    def create_alert(self, **kwargs):
        self.calls.append(kwargs)
        alert_id = self._next_id
        self._next_id += 1
        return alert_id

    def get_alert_by_id(self, alert_id):
        return SimpleNamespace(id=alert_id)


def test_create_alerts_from_inconsistencies_resolves_entity_and_skips_low_confidence(monkeypatch):
    fake_engine = _FakeAlertEngine()
    fake_repo = SimpleNamespace(
        find_entities_by_name=lambda **kwargs: [SimpleNamespace(id=7)] if kwargs.get("fuzzy") else [],
    )

    monkeypatch.setattr(
        "narrative_assistant.pipelines.analysis_pipeline_alerts.get_alert_engine",
        lambda: fake_engine,
    )
    monkeypatch.setattr(
        "narrative_assistant.pipelines.analysis_pipeline_alerts.get_entity_repository",
        lambda: fake_repo,
    )

    low = AttributeInconsistency(
        entity_name="Elena",
        entity_id=0,
        attribute_key=AttributeKey.EYE_COLOR,
        value1="azul",
        value2="verde",
        confidence=0.2,
        explanation="baja",
    )
    high = AttributeInconsistency(
        entity_name="Elena",
        entity_id=0,
        attribute_key=AttributeKey.EYE_COLOR,
        value1="azul",
        value1_chapter=1,
        value1_position=10,
        value1_excerpt="ojos azules",
        value2="verde",
        value2_chapter=2,
        value2_position=30,
        value2_excerpt="ojos verdes",
        confidence=0.9,
        explanation="alta",
    )

    result = create_alerts_from_inconsistencies(1, [low, high], min_confidence=0.5)

    assert result.is_success
    assert len(result.value) == 1
    assert len(fake_engine.calls) == 1
    call = fake_engine.calls[0]
    assert call["entity_id"] == 7
    assert len(call["sources"]) == 2
    assert call["sources"][0]["chapter"] == 1


def test_create_alerts_from_temporal_and_voice_deviations_builds_expected_categories(monkeypatch):
    fake_repo = _FakeAlertRepo()

    monkeypatch.setattr(
        "narrative_assistant.alerts.repository.get_alert_repository",
        lambda: fake_repo,
    )

    temporal = TemporalInconsistency(
        inconsistency_type=InconsistencyType.ANACHRONISM,
        severity=InconsistencySeverity.HIGH,
        description="Objeto fuera de época",
        chapter=4,
        position=120,
        found="móvil",
        expected="teléfono fijo",
    )
    temporal_result = create_alerts_from_temporal_inconsistencies(1, [temporal])
    assert temporal_result.is_success
    assert len(temporal_result.value) == 1
    assert fake_repo.calls[0]["category"] == AlertCategory.TIMELINE_ISSUE.value

    voice = VoiceDeviation(
        entity_id=9,
        entity_name="Lucía",
        deviation_type=DeviationType.FORMALITY_SHIFT,
        severity=DeviationSeverity.HIGH,
        chapter=5,
        position=300,
        text="Buenos días, tío.",
        expected_value=0.8,
        actual_value=0.2,
        description="Cambio brusco de registro",
        confidence=0.8,
    )
    voice_alerts = create_alerts_from_voice_deviations(1, [voice])
    assert voice_alerts.is_success
    assert len(voice_alerts.value) == 1
    assert fake_repo.calls[-1]["entity_id"] == 9


def test_create_alerts_from_focalization_and_emotional_resolve_entity_and_metadata(monkeypatch):
    fake_repo = _FakeAlertRepo()
    entity_repo = SimpleNamespace(find_by_name=lambda project_id, name: SimpleNamespace(id=13))

    monkeypatch.setattr(
        "narrative_assistant.alerts.repository.get_alert_repository",
        lambda: fake_repo,
    )
    monkeypatch.setattr(
        "narrative_assistant.pipelines.analysis_pipeline_alerts.get_entity_repository",
        lambda: entity_repo,
    )

    focalization = FocalizationViolation(
        violation_type=ViolationType.THOUGHT_IN_EXTERNAL,
        severity=ViolationSeverity.HIGH,
        chapter=3,
        scene=None,
        position=88,
        text_excerpt="Pensó que nadie lo vería.",
        entity_involved=4,
        entity_name="Mario",
        explanation="Acceso mental indebido",
        declared_focalizer="Ana",
        suggestion="Reescribir desde focalización externa",
        confidence=0.9,
    )
    foc_result = create_alerts_from_focalization_violations(1, [focalization])
    assert foc_result.is_success
    assert len(foc_result.value) == 1
    assert fake_repo.calls[0]["entity_id"] == 4

    incoherence = EmotionalIncoherence(
        entity_name="Mario",
        incoherence_type=IncoherenceType.EMOTION_DIALOGUE,
        declared_emotion="furioso",
        actual_behavior="tono amable",
        declared_text="Mario estaba furioso.",
        behavior_text="Gracias por todo, amigo.",
        confidence=0.85,
        explanation="El diálogo contradice la emoción declarada.",
        suggestion="Ajustar el tono del diálogo",
        chapter_id=3,
        start_char=120,
        end_char=150,
    )
    emo_result = create_alerts_from_emotional_incoherences(1, [incoherence])
    assert emo_result.is_success
    assert len(emo_result.value) == 1
    assert fake_repo.calls[-1]["entity_id"] == 13
    assert fake_repo.calls[-1]["source_chapter"] == 3
