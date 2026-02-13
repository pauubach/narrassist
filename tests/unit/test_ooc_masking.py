"""Tests para BK-15: Detección de masking emocional en OOC."""

import pytest

from narrative_assistant.analysis.character_profiling import (
    ActionIndicator,
    CharacterProfile,
    CharacterRole,
    PresenceIndicator,
    SentimentIndicator,
)
from narrative_assistant.analysis.out_of_character import (
    DeviationSeverity,
    DeviationType,
    OutOfCharacterDetector,
)


def _make_profile(
    entity_id: int = 1,
    name: str = "María",
    sentiment: float = 0.6,
) -> CharacterProfile:
    """Crea un perfil con sentimiento positivo alto (línea base)."""
    return CharacterProfile(
        entity_id=entity_id,
        entity_name=name,
        role=CharacterRole.PROTAGONIST,
        presence=PresenceIndicator(
            total_mentions=20,
            chapters_present=[1, 2],
            mentions_per_chapter={1: 10, 2: 10},
        ),
        actions=ActionIndicator(action_count=10, agency_score=0.5),
        sentiment=SentimentIndicator(
            positive_mentions=8,
            negative_mentions=2,
            avg_sentiment=sentiment,
            sentiment_by_chapter={1: sentiment, 2: sentiment},
        ),
    )


# Textos base reutilizables.
# Cap 1 necesita >=2 frases con "María" + palabras de POSITIVE_WORDS.
# Cap 2 necesita >=2 frases con "María" + palabras de NEGATIVE_WORDS.
# Esto genera un shift de sentimiento >= 0.5 entre capítulos.
_POSITIVE_CHAPTER = (
    "María era feliz y sentía amor por todos. "
    "María sonreía con alegría y esperanza. "
    "María sentía paz y calma a su alrededor."
)

_NEGATIVE_CHAPTER_NO_MASK = (
    "María sentía dolor y odio profundo. "
    "María lloraba de tristeza y angustia. "
    "María sentía miedo y culpa."
)


class TestEmotionalMasking:
    """Tests para _check_emotional_masking y su integración en OOC."""

    def test_fingio_calma_is_intentional(self):
        """'fingió calma' debe marcar el evento como intencional (INFO)."""
        detector = OutOfCharacterDetector()
        profile = _make_profile(sentiment=0.7)

        chapter_texts = {
            1: _POSITIVE_CHAPTER,
            2: (
                "María fingió calma ante todos. "
                "María sentía dolor y odio profundo. "
                "María sufría tristeza y angustia."
            ),
        }

        report = detector.detect(profiles=[profile], chapter_texts=chapter_texts)

        emotion_events = [
            e for e in report.events if e.deviation_type == DeviationType.EMOTION_SHIFT
        ]
        assert len(emotion_events) >= 1
        event = emotion_events[0]
        assert event.is_intentional is True
        assert event.severity == DeviationSeverity.INFO
        assert event.confidence <= 0.3

    def test_disimulando_calma_is_intentional(self):
        """'disimulando su calma' debe marcar como intencional."""
        detector = OutOfCharacterDetector()
        profile = _make_profile(sentiment=0.7)

        chapter_texts = {
            1: _POSITIVE_CHAPTER,
            2: (
                "María iba disimulando su calma con esfuerzo. "
                "María sentía dolor y odio intenso. "
                "María sufría tristeza y angustia."
            ),
        }

        report = detector.detect(profiles=[profile], chapter_texts=chapter_texts)
        emotion_events = [
            e for e in report.events if e.deviation_type == DeviationType.EMOTION_SHIFT
        ]
        assert len(emotion_events) >= 1
        assert emotion_events[0].is_intentional is True

    def test_aparentaba_with_physical_leak(self):
        """'aparentaba calma aunque temblaba' → INFO + confidence=0.3."""
        detector = OutOfCharacterDetector()
        profile = _make_profile(sentiment=0.7)

        chapter_texts = {
            1: _POSITIVE_CHAPTER,
            2: (
                "María aparentaba calma aunque temblaba por dentro. "
                "María sentía dolor y odio profundo. "
                "María sufría tristeza y angustia."
            ),
        }

        report = detector.detect(profiles=[profile], chapter_texts=chapter_texts)
        emotion_events = [
            e for e in report.events if e.deviation_type == DeviationType.EMOTION_SHIFT
        ]
        assert len(emotion_events) >= 1
        event = emotion_events[0]
        assert event.is_intentional is True
        assert event.severity == DeviationSeverity.INFO
        assert event.confidence == pytest.approx(0.3)
        assert "plot-relevant" in event.description

    def test_normal_emotion_shift_not_suppressed(self):
        """Cambio emocional genuino sin masking → WARNING (no suprimido)."""
        detector = OutOfCharacterDetector()
        profile = _make_profile(sentiment=0.7)

        chapter_texts = {
            1: _POSITIVE_CHAPTER,
            2: _NEGATIVE_CHAPTER_NO_MASK,
        }

        report = detector.detect(profiles=[profile], chapter_texts=chapter_texts)
        emotion_events = [
            e for e in report.events if e.deviation_type == DeviationType.EMOTION_SHIFT
        ]
        assert len(emotion_events) >= 1
        event = emotion_events[0]
        assert event.is_intentional is False
        assert event.severity == DeviationSeverity.WARNING

    def test_masking_verb_without_maskable_emotion(self):
        """'fingió sorpresa' NO debe marcarse intencional (sorpresa no maskable)."""
        detector = OutOfCharacterDetector()
        profile = _make_profile(sentiment=0.7)

        chapter_texts = {
            1: _POSITIVE_CHAPTER,
            2: (
                "María fingió sorpresa ante la noticia. "
                "María sentía dolor y odio profundo. "
                "María sufría tristeza y angustia."
            ),
        }

        report = detector.detect(profiles=[profile], chapter_texts=chapter_texts)
        emotion_events = [
            e for e in report.events if e.deviation_type == DeviationType.EMOTION_SHIFT
        ]
        for event in emotion_events:
            assert event.is_intentional is False

    def test_masking_far_from_character_not_detected(self):
        """Masking lejos del nombre del personaje → no detectado."""
        detector = OutOfCharacterDetector()
        profile = _make_profile(name="María", sentiment=0.7)

        # Masking de Pedro, a >300 chars de cualquier "María"
        filler = "La noche era oscura y silenciosa. " * 15  # ~510 chars
        chapter_texts = {
            1: _POSITIVE_CHAPTER,
            2: (
                f"María llegó al lugar. {filler}"
                f"Pedro fingió calma ante los presentes. {filler}"
                "María sentía dolor y odio profundo. "
                "María sufría tristeza y angustia."
            ),
        }

        report = detector.detect(profiles=[profile], chapter_texts=chapter_texts)
        emotion_events = [
            e for e in report.events if e.deviation_type == DeviationType.EMOTION_SHIFT
        ]
        for event in emotion_events:
            assert event.is_intentional is False
