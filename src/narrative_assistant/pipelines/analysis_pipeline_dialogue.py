"""Helpers de dialogo y voz para el pipeline legacy de analisis."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from ..entities.models import Entity
from ..nlp.dialogue import detect_dialogues
from ..voice import VoiceDeviationDetector, VoiceProfileBuilder

if TYPE_CHECKING:
    from .analysis_pipeline_models import ChapterInfo


_LOGGER = logging.getLogger(__name__)


def extract_dialogues_from_chapter(
    chapter: "ChapterInfo",
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extrae dialogos del texto del capitulo y estima speaker por contexto."""
    dialogues: list[dict[str, Any]] = []
    text = chapter.content

    character_names: dict[str, Any] = {}
    for entity in entities:
        if entity.get("type") not in ("PERSON", "CHARACTER", "PER"):
            continue
        name = entity.get("name", "").lower()
        if not name:
            continue
        character_names[name] = entity["id"]
        for part in name.split():
            if len(part) > 2:
                character_names[part] = entity["id"]

    dialogue_patterns = [
        r"[—–]\s*([^—–\n]+?)(?=[—–\n]|$)",
        r"«([^»]+)»",
        r'"([^"]+)"',
    ]

    all_matches: list[tuple[int, str]] = []
    for pattern in dialogue_patterns:
        for match in re.finditer(pattern, text):
            all_matches.append((match.start(), match.group(1).strip()))
    all_matches.sort(key=lambda item: item[0])

    for position, dialogue_text in all_matches:
        if len(dialogue_text) < 5:
            continue

        context_start = max(0, position - 100)
        context = text[context_start:position].lower()
        speaker_id = None
        best_distance = 100

        for name, character_id in character_names.items():
            index = context.rfind(name)
            if index < 0:
                continue
            distance = len(context) - index
            if distance < best_distance:
                best_distance = distance
                speaker_id = character_id

        if speaker_id is None:
            continue

        dialogues.append(
            {
                "text": dialogue_text,
                "speaker_id": speaker_id,
                "chapter": chapter.number,
                "position": chapter.start_char + position,
            }
        )

    return dialogues


def run_voice_analysis(
    chapters: list["ChapterInfo"],
    entities: list[Entity],
    logger: logging.Logger | None = None,
) -> Result[dict[str, Any]]:
    """Ejecuta analisis de voz legacy reutilizando helpers de dialogo."""
    active_logger = logger or _LOGGER

    try:
        entities_dict = [
            {
                "id": entity.id,
                "name": entity.canonical_name or getattr(entity, "name", ""),
                "type": entity.entity_type.value,
            }
            for entity in entities
        ]

        dialogues_all: list[Any] = []
        for chapter in chapters:
            dialogues_all.extend(extract_dialogues_from_chapter(chapter, entities_dict))

        builder = VoiceProfileBuilder(min_interventions=3)
        profiles = builder.build_profiles(dialogues_all, entities_dict)

        detector = VoiceDeviationDetector()
        deviations = detector.detect_deviations(profiles, dialogues_all)

        active_logger.info(
            "Voice analysis complete: %s profiles, %s deviations",
            len(profiles),
            len(deviations),
        )
        return Result.success({"profiles": profiles, "deviations": deviations})
    except Exception as exc:
        error = NarrativeError(
            message=f"Voice analysis failed: {str(exc)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        active_logger.exception("Error during voice analysis")
        return Result.failure(error)


def extract_dialogues_for_emotional_analysis(
    chapter_number: int,
    chapter_content: str,
    logger: logging.Logger | None = None,
) -> list[tuple[str, str, int, int]]:
    """Convierte los dialogos detectados al formato esperado por emotional coherence."""
    active_logger = logger or _LOGGER
    dialogue_result = detect_dialogues(chapter_content)
    if dialogue_result.is_failure:
        active_logger.warning("Could not extract dialogues from chapter %s", chapter_number)
        return []

    return [
        (
            dialogue.speaker_hint or "desconocido",
            dialogue.text,
            dialogue.start_char,
            dialogue.end_char,
        )
        for dialogue in dialogue_result.value.dialogues
    ]
