"""
Integración de resolución de correferencias + atribución de diálogos.

Valida que el pipeline de resolución reutiliza salidas del motor de coref
para mejorar `resolved_speaker` sin duplicar lógica.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from narrative_assistant.entities.models import Entity, EntityType
from narrative_assistant.nlp.coreference_resolver import (
    CoreferenceChain,
    CorefResult,
    Mention,
    MentionType,
)
from narrative_assistant.pipelines.ua_resolution import PipelineResolutionMixin
from narrative_assistant.pipelines.unified_analysis import AnalysisContext


class _ResolutionPipeline(PipelineResolutionMixin):
    """Pipeline mínimo para tests del mixin de resolución."""

    def __init__(self):
        self.config = SimpleNamespace(use_llm=False)
        self._memory_monitor = Mock()


class _EntityRepoStub:
    """Stub de repositorio de entidades para evitar accesos reales."""

    def get_mentions_by_entity(self, _entity_id: int):
        return []


class _DatabaseStub:
    """Stub de DB para saltar correcciones de hablante."""

    def fetchall(self, *_args, **_kwargs):
        return []


def _character(entity_id: int, canonical_name: str, aliases: list[str] | None = None) -> Entity:
    return Entity(
        id=entity_id,
        project_id=1,
        entity_type=EntityType.CHARACTER,
        canonical_name=canonical_name,
        aliases=aliases or [],
    )


def test_pronoun_coref_map_is_used_to_resolve_dialogue_speaker():
    """
    End-to-end interno:
    coref -> pronoun_resolution_map -> _attribute_dialogues -> resolved_speaker.
    """
    full_text = (
        "Don Ramiro recibió la terrible noticia.\n"
        "Él se derrumbó en su sillón.\n"
        "—Mi pequeña Isabel... ¿Quién haría algo así?\n"
    )
    dialogue_text = "Mi pequeña Isabel... ¿Quién haría algo así?"
    dialogue_start = full_text.index(dialogue_text)
    dialogue_end = dialogue_start + len(dialogue_text)
    pronoun_start = full_text.index("Él")
    pronoun_end = pronoun_start + len("Él")

    context = AnalysisContext(project_id=1, session_id=1, full_text=full_text)
    context.chapters = [
        {
            "number": 1,
            "title": "Capítulo 1",
            "content": full_text,
            "start_char": 0,
            "end_char": len(full_text),
        }
    ]
    context.entities = [
        _character(1, "Don Ramiro Estebanez", ["Don Ramiro", "Ramiro"]),
        _character(2, "Elena Montero", ["Elena"]),
    ]
    context.dialogues = [
        {
            "text": dialogue_text,
            "start_char": dialogue_start,
            "end_char": dialogue_end,
            "chapter": 1,
            # Detector puede venir sin tilde aunque en texto esté "Él"
            "speaker_hint": "el",
            "attribution_text": "",
        }
    ]

    coref_result = CorefResult(
        chains=[
            CoreferenceChain(
                main_mention="Don Ramiro",
                mentions=[
                    Mention(
                        text="Don Ramiro",
                        start_char=0,
                        end_char=len("Don Ramiro"),
                        mention_type=MentionType.PROPER_NOUN,
                    ),
                    Mention(
                        text="Él",
                        start_char=pronoun_start,
                        end_char=pronoun_end,
                        mention_type=MentionType.PRONOUN,
                    ),
                ],
            )
        ]
    )

    pipeline = _ResolutionPipeline()

    with patch(
        "narrative_assistant.nlp.coreference_resolver.resolve_coreferences_voting",
        return_value=coref_result,
    ):
        pipeline._run_coreference(context)

    assert context.pronoun_resolution_map[(pronoun_start, pronoun_end)] == "Don Ramiro"
    assert context.mention_to_entity["él"] == "Don Ramiro"

    with (
        patch(
            "narrative_assistant.entities.repository.get_entity_repository",
            return_value=_EntityRepoStub(),
        ),
        patch(
            "narrative_assistant.persistence.database.get_database",
            return_value=_DatabaseStub(),
        ),
    ):
        pipeline._attribute_dialogues(context)

    attributed = context.dialogues[0]
    assert attributed["resolved_speaker"] == "Don Ramiro Estebanez"
    assert attributed["speaker_id"] == 1
    assert attributed["attribution_method"] == "coreference_pronoun"
    assert attributed["attribution_confidence"] == "medium"


def test_attribution_text_is_wired_and_has_priority_over_wrong_hint():
    """
    Integra el cableado detect_dialogues -> context.dialogues['attribution_text']
    -> SpeakerAttributor para priorizar atribución explícita local.
    """
    full_text = (
        "—Señorita Montero, es un honor recibirla en mi humilde morada.\n"
        "—El honor es mío, profesor.\n"
    )
    dialogue_text = "Señorita Montero, es un honor recibirla en mi humilde morada."
    dialogue_start = full_text.index(dialogue_text)
    dialogue_end = dialogue_start + len(dialogue_text)

    context = AnalysisContext(project_id=1, session_id=1, full_text=full_text)
    context.entities = [
        _character(1, "Don Ramiro Estebanez", ["Don Ramiro", "Ramiro"]),
        _character(2, "Elena Montero", ["Elena"]),
    ]
    context.dialogues = [
        {
            "text": dialogue_text,
            "start_char": dialogue_start,
            "end_char": dialogue_end,
            "chapter": 1,
            "speaker_hint": "Elena",
            "attribution_text": " - dijo Don Ramiro con una reverencia leve.",
        }
    ]

    pipeline = _ResolutionPipeline()
    with (
        patch(
            "narrative_assistant.entities.repository.get_entity_repository",
            return_value=_EntityRepoStub(),
        ),
        patch(
            "narrative_assistant.persistence.database.get_database",
            return_value=_DatabaseStub(),
        ),
    ):
        pipeline._attribute_dialogues(context)

    attributed = context.dialogues[0]
    assert attributed["resolved_speaker"] == "Don Ramiro Estebanez"
    assert attributed["speaker_id"] == 1
    assert attributed["attribution_method"] == "explicit_verb"
    assert attributed["attribution_confidence"] == "high"
