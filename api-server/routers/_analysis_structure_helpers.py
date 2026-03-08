"""Helpers de estructura persistida para el pipeline de analisis."""

from __future__ import annotations

import logging
from typing import Any


def find_chapter_id_for_position(chapters_with_ids: list[Any], start_char: int) -> int | None:
    """Busca el chapter_id mas adecuado para una posicion de caracter."""
    for chapter in chapters_with_ids:
        if chapter.start_char <= start_char < chapter.end_char:
            return chapter.id
    if chapters_with_ids:
        closest = min(chapters_with_ids, key=lambda chapter: abs(chapter.start_char - start_char))
        return closest.id
    return None


def compute_and_persist_chapter_metrics(
    chapters_data: list[dict[str, Any]],
    chapters_with_ids: list[Any],
    chapter_repo: Any,
    chapters_count: int,
    logger: logging.Logger,
) -> None:
    """Calcula metricas ligeras por capitulo y las persiste."""
    from narrative_assistant.persistence.chapter import compute_chapter_metrics

    metrics_computed = 0
    for chapter_db in chapters_with_ids:
        chapter_data = next(
            (chapter for chapter in chapters_data if chapter["chapter_number"] == chapter_db.chapter_number),
            None,
        )
        if not chapter_data or not chapter_data.get("content"):
            continue
        metrics = compute_chapter_metrics(chapter_data["content"])
        if metrics:
            chapter_repo.update_metrics(chapter_db.id, metrics)  # type: ignore[arg-type]
            metrics_computed += 1

    logger.info("Chapter metrics computed for %s/%s chapters", metrics_computed, chapters_count)


def detect_and_persist_dialogues(
    project_id: int,
    chapters_data: list[dict[str, Any]],
    chapters_with_ids: list[Any],
    db_session: Any,
    chapters_count: int,
    logger: logging.Logger,
) -> int:
    """Detecta dialogos por capitulo, limpia los previos y persiste el resultado."""
    from narrative_assistant.nlp.dialogue import detect_dialogues
    from narrative_assistant.persistence.dialogue import DialogueData, get_dialogue_repository

    dialogue_repo = get_dialogue_repository(db_session)
    dialogue_repo.delete_by_project(project_id)

    dialogues_total = 0
    for chapter_db in chapters_with_ids:
        chapter_data = next(
            (chapter for chapter in chapters_data if chapter["chapter_number"] == chapter_db.chapter_number),
            None,
        )
        if not chapter_data or not chapter_data.get("content"):
            continue

        dialogue_result = detect_dialogues(chapter_data["content"])
        if not dialogue_result.is_success or not dialogue_result.value.dialogues:
            continue

        dialogues_to_save = []
        for dialogue_span in dialogue_result.value.dialogues:
            dialogues_to_save.append(
                DialogueData(
                    id=None,
                    project_id=project_id,
                    chapter_id=chapter_db.id,
                    start_char=dialogue_span.start_char,
                    end_char=dialogue_span.end_char,
                    text=dialogue_span.text,
                    dialogue_type=dialogue_span.dialogue_type.value,
                    original_format=dialogue_span.original_format,
                    attribution_text=dialogue_span.attribution_text,
                    speaker_hint=dialogue_span.speaker_hint,
                    confidence=dialogue_span.confidence,
                )
            )

        dialogue_repo.create_batch(dialogues_to_save)
        dialogues_total += len(dialogues_to_save)

    logger.info(
        "Dialogues detected and persisted: %s dialogues across %s chapters",
        dialogues_total,
        chapters_count,
    )
    return dialogues_total


def initialize_dialogue_style_preference(
    project_id: int,
    db_session: Any,
    logger: logging.Logger,
) -> None:
    """Inicializa dialogue_style_preference desde correction_config si aun no existe."""
    from narrative_assistant.nlp.dialogue_config_mapper import (
        map_correction_config_to_dialogue_preference,
    )
    from narrative_assistant.persistence.project import ProjectManager

    project_manager = ProjectManager(db_session)
    project = project_manager.get_by_id(project_id)
    if not project or not project.settings_json:
        return

    correction_config = project.settings_json.get("correction_config", {})
    dialogue_dash = correction_config.get("dialogue_dash")
    quote_style = correction_config.get("quote_style")
    preference = map_correction_config_to_dialogue_preference(dialogue_dash, quote_style)

    if "dialogue_style_preference" in project.settings_json:
        return

    project.settings_json["dialogue_style_preference"] = preference
    project_manager.update(project)
    logger.info(
        "Initialized dialogue_style_preference=%s from correction_config",
        preference,
    )
