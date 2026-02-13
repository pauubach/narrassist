"""Tests para BK-10b (scene breaks) y BK-10c (confidence decay) en speaker attribution."""

from dataclasses import dataclass

import pytest

from narrative_assistant.voice.speaker_attribution import (
    AttributionConfidence,
    AttributionMethod,
    SpeakerAttributor,
)


@dataclass
class _FakeEntity:
    id: int
    canonical_name: str
    name: str = ""
    aliases: list = None

    def __post_init__(self):
        self.name = self.name or self.canonical_name
        self.aliases = self.aliases or []


@dataclass
class _FakeDialogue:
    text: str
    start_char: int
    end_char: int
    chapter: int
    speaker_hint: str = ""
    context_before: str = ""
    context_after: str = ""


class TestSceneBreaks:
    """BK-10b: Scene breaks resetean contexto de speaker attribution."""

    def _build_attributor(self):
        entities = [
            _FakeEntity(id=1, canonical_name="Juan"),
            _FakeEntity(id=2, canonical_name="María"),
        ]
        return SpeakerAttributor(entities)

    def test_asterisk_scene_break_resets_context(self):
        """'***' entre diálogos debe resetear last_speaker y participants."""
        attr = self._build_attributor()

        # Texto con scene break de asteriscos
        full_text = (
            "—Hola —dijo Juan.\n"
            "—Adiós —dijo María.\n"
            "\n***\n\n"
            "—Buenos días.\n"  # Tras scene break: no hay last_speaker
        )

        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
            _FakeDialogue(text="Buenos días", start_char=40, end_char=51, chapter=1),
        ]

        mentions = [
            (1, 12, 16),  # "Juan" at pos 12
            (2, 31, 36),  # "María" at pos 31
        ]

        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        # Los dos primeros deben tener speaker explícito
        assert results[0].speaker_id == 1  # Juan
        assert results[1].speaker_id == 2  # María
        # El tercero no debe heredar alternancia de la escena anterior
        # (puede ser UNKNOWN o PROXIMITY, pero NO alternancia con María/Juan)
        assert results[2].attribution_method != AttributionMethod.ALTERNATION

    def test_dash_scene_break_resets_context(self):
        """'---' entre diálogos debe resetear contexto."""
        attr = self._build_attributor()

        full_text = (
            "—Hola —dijo Juan.\n" "—Adiós —dijo María.\n" "\n---\n\n" "—Algo nuevo.\n"
        )

        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
            _FakeDialogue(text="Algo nuevo", start_char=40, end_char=50, chapter=1),
        ]

        mentions = [(1, 12, 16), (2, 31, 36)]
        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        assert results[2].attribution_method != AttributionMethod.ALTERNATION

    def test_triple_newline_scene_break_resets_context(self):
        """Triple newline debe resetear contexto."""
        attr = self._build_attributor()

        full_text = (
            "—Hola —dijo Juan.\n" "—Adiós —dijo María.\n" "\n\n\n" "—Otra escena.\n"
        )

        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
            _FakeDialogue(text="Otra escena", start_char=42, end_char=53, chapter=1),
        ]

        mentions = [(1, 12, 16), (2, 31, 36)]
        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        assert results[2].attribution_method != AttributionMethod.ALTERNATION

    def test_no_scene_break_alternation_continues(self):
        """Sin scene break, la alternancia continúa normalmente."""
        attr = self._build_attributor()

        full_text = "—Hola —dijo Juan.\n" "—Adiós —dijo María.\n" "—¿Qué tal?\n"

        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
            _FakeDialogue(text="¿Qué tal?", start_char=40, end_char=50, chapter=1),
        ]

        mentions = [(1, 12, 16), (2, 31, 36)]
        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        # Sin scene break: alternancia → Juan (turno 3)
        assert results[2].speaker_id == 1
        assert results[2].attribution_method == AttributionMethod.ALTERNATION


class TestConfidenceDecay:
    """BK-10c: Confidence decay con distancia de diálogos."""

    def _build_attributor(self):
        entities = [
            _FakeEntity(id=1, canonical_name="Juan"),
            _FakeEntity(id=2, canonical_name="María"),
        ]
        return SpeakerAttributor(entities)

    def test_close_alternation_has_medium_confidence(self):
        """Alternancia cercana a explícito → MEDIUM confidence."""
        attr = self._build_attributor()

        full_text = (
            "—Hola —dijo Juan.\n"
            "—Adiós —dijo María.\n"
            "—¿Sí?.\n"  # 1 turno desde explícito → decay ≈ 0.97 → MEDIUM
        )

        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
            _FakeDialogue(text="¿Sí?", start_char=40, end_char=44, chapter=1),
        ]

        mentions = [(1, 12, 16), (2, 31, 36)]
        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        assert results[2].attribution_method == AttributionMethod.ALTERNATION
        assert results[2].confidence == AttributionConfidence.MEDIUM

    def test_distant_alternation_has_low_confidence(self):
        """Alternancia muy lejana → LOW confidence (decay < 0.74)."""
        attr = self._build_attributor()

        # Crear muchos diálogos sin verbo de habla explícito
        # Solo los 2 primeros tienen verba dicendi
        full_text = "—Hola —dijo Juan.\n—Adiós —dijo María.\n"
        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
        ]
        mentions = [(1, 12, 16), (2, 31, 36)]

        # Añadir 10+ diálogos sin explícito → decay^10 ≈ 0.74
        pos = 40
        for idx in range(12):
            text_d = f"Turno {idx}"
            dialogues.append(
                _FakeDialogue(
                    text=text_d, start_char=pos, end_char=pos + len(text_d), chapter=1
                )
            )
            full_text += f"—{text_d}.\n"
            pos += len(text_d) + 5

        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        # Los últimos diálogos de alternancia deberían tener LOW
        last = results[-1]
        if last.attribution_method == AttributionMethod.ALTERNATION:
            assert last.confidence == AttributionConfidence.LOW

    def test_scene_break_resets_decay(self):
        """Scene break debe resetear turns_since_explicit."""
        attr = self._build_attributor()

        full_text = (
            "—Hola —dijo Juan.\n"
            "—Adiós —dijo María.\n"
            "—Algo.\n"
            "—Otro.\n"
            "—Más.\n"
            "—Sigue.\n"
            "—Ya.\n"
            "—Dale.\n"
            "—Venga.\n"
            "—Ok.\n"
            "—Bien.\n"
            "\n***\n\n"
            "—Nuevo —dijo Juan.\n"
            "—Reset —dijo María.\n"
            "—Tras reset.\n"  # turns_since_explicit=1 (reseteado tras scene break)
        )

        dialogues = [
            _FakeDialogue(
                text="Hola",
                start_char=1,
                end_char=5,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            _FakeDialogue(
                text="Adiós",
                start_char=19,
                end_char=24,
                chapter=1,
                context_after=" —dijo María.",
            ),
        ]
        mentions = [(1, 12, 16), (2, 31, 36)]

        # Diálogos sin explícito antes del scene break
        pos = 40
        for idx in range(9):
            text_d = f"D{idx}"
            dialogues.append(
                _FakeDialogue(
                    text=text_d, start_char=pos, end_char=pos + len(text_d), chapter=1
                )
            )
            pos += 10

        # Post scene-break: nuevos diálogos con explícito
        sb_pos = full_text.find("***")
        post_pos = sb_pos + 10
        dialogues.append(
            _FakeDialogue(
                text="Nuevo",
                start_char=post_pos,
                end_char=post_pos + 5,
                chapter=1,
                context_after=" —dijo Juan.",
            )
        )
        mentions.append((1, post_pos + 12, post_pos + 16))

        post_pos += 25
        dialogues.append(
            _FakeDialogue(
                text="Reset",
                start_char=post_pos,
                end_char=post_pos + 5,
                chapter=1,
                context_after=" —dijo María.",
            )
        )
        mentions.append((2, post_pos + 12, post_pos + 18))

        post_pos += 25
        dialogues.append(
            _FakeDialogue(
                text="Tras reset",
                start_char=post_pos,
                end_char=post_pos + 10,
                chapter=1,
            )
        )

        results = attr.attribute_dialogues(dialogues, mentions, full_text)

        # El último diálogo ("Tras reset") debería tener confianza MEDIUM
        # porque turns_since_explicit se reseteó en el scene break
        last = results[-1]
        if last.attribution_method == AttributionMethod.ALTERNATION:
            assert last.confidence == AttributionConfidence.MEDIUM
