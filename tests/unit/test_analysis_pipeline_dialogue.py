import logging
from types import SimpleNamespace

from narrative_assistant.pipelines.analysis_pipeline_dialogue import (
    extract_dialogues_for_emotional_analysis,
    extract_dialogues_from_chapter,
)
from narrative_assistant.pipelines.analysis_pipeline_models import ChapterInfo


def test_extract_dialogues_from_chapter_assigns_nearest_speaker():
    chapter = ChapterInfo(
        number=3,
        title="Capitulo 3",
        content='Juan sonrio. "Hola Maria" contesto. Pedro se aparto.',
        start_char=100,
        end_char=150,
        word_count=8,
    )
    entities = [
        {"id": 1, "name": "Juan Perez", "type": "PER"},
        {"id": 2, "name": "Pedro", "type": "PER"},
    ]

    dialogues = extract_dialogues_from_chapter(chapter, entities)

    assert len(dialogues) == 1
    assert dialogues[0]["speaker_id"] == 1
    assert dialogues[0]["chapter"] == 3
    assert dialogues[0]["position"] >= chapter.start_char


def test_extract_dialogues_from_chapter_ignores_short_or_unattributed_dialogues():
    chapter = ChapterInfo(
        number=1,
        title=None,
        content='"No" y luego "Vale". Finalmente "Sin contexto suficiente".',
        start_char=0,
        end_char=80,
        word_count=7,
    )

    dialogues = extract_dialogues_from_chapter(chapter, [{"id": 1, "name": "Ana", "type": "PER"}])

    assert dialogues == []


def test_extract_dialogues_for_emotional_analysis_maps_detected_spans(monkeypatch):
    fake_result = SimpleNamespace(
        is_failure=False,
        value=SimpleNamespace(
            dialogues=[
                SimpleNamespace(
                    speaker_hint="Maria",
                    text="No pienso volver",
                    start_char=12,
                    end_char=28,
                ),
                SimpleNamespace(
                    speaker_hint=None,
                    text="De acuerdo",
                    start_char=40,
                    end_char=50,
                ),
            ]
        ),
    )
    monkeypatch.setattr(
        "narrative_assistant.pipelines.analysis_pipeline_dialogue.detect_dialogues",
        lambda text: fake_result,
    )

    dialogues = extract_dialogues_for_emotional_analysis(4, "contenido")

    assert dialogues == [
        ("Maria", "No pienso volver", 12, 28),
        ("desconocido", "De acuerdo", 40, 50),
    ]


def test_extract_dialogues_for_emotional_analysis_logs_warning_on_failure(monkeypatch, caplog):
    fake_result = SimpleNamespace(is_failure=True, value=None)
    monkeypatch.setattr(
        "narrative_assistant.pipelines.analysis_pipeline_dialogue.detect_dialogues",
        lambda text: fake_result,
    )

    with caplog.at_level(logging.WARNING):
        dialogues = extract_dialogues_for_emotional_analysis(9, "contenido")

    assert dialogues == []
    assert "Could not extract dialogues from chapter 9" in caplog.text
