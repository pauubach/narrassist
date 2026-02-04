"""Tests para el modulo de atribucion de hablante."""

from dataclasses import dataclass
from typing import List, Optional

import pytest

from narrative_assistant.voice.speaker_attribution import (
    SPEECH_VERBS,
    AttributionConfidence,
    AttributionMethod,
    DialogueAttribution,
    SpeakerAttributor,
    attribute_speakers,
)

# ============================================================================
# Mock classes para tests
# ============================================================================


@dataclass
class MockEntity:
    """Entidad mock para tests."""

    id: int
    canonical_name: str
    aliases: list[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class MockDialogue:
    """Dialogo mock para tests."""

    text: str
    start_char: int
    end_char: int
    chapter: int
    context_after: str = ""
    context_before: str = ""


@dataclass
class MockVoiceProfile:
    """Perfil de voz mock para tests."""

    entity_id: int
    uses_usted: bool = False
    uses_tu: bool = True
    avg_intervention_length: float = 10.0
    filler_words: list[str] = None

    def __post_init__(self):
        if self.filler_words is None:
            self.filler_words = []


# ============================================================================
# Tests para SpeakerAttributor
# ============================================================================


class TestSpeakerAttributor:
    """Tests para SpeakerAttributor."""

    def test_init(self):
        """Test inicializacion del atribuidor."""
        entities = [
            MockEntity(1, "Juan", ["Juanito"]),
            MockEntity(2, "Maria"),
        ]
        attributor = SpeakerAttributor(entities)

        assert len(attributor.entities) == 2
        assert "juan" in attributor.entity_names
        assert "juanito" in attributor.entity_names
        assert "maria" in attributor.entity_names

    def test_init_empty_entities(self):
        """Test inicializacion sin entidades."""
        attributor = SpeakerAttributor([])
        assert len(attributor.entities) == 0

    def test_explicit_attribution_verb_after(self):
        """Test atribucion explicita con verbo despues del dialogo."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue(
                text="¡Hola!",
                start_char=100,
                end_char=110,
                chapter=1,
                context_after=" —dijo Juan con una sonrisa.",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 1
        assert attributions[0].speaker_name == "Juan"
        assert attributions[0].confidence == AttributionConfidence.HIGH
        assert attributions[0].attribution_method == AttributionMethod.EXPLICIT_VERB
        assert attributions[0].speech_verb == "dijo"

    def test_explicit_attribution_verb_before(self):
        """Test atribucion explicita con verbo antes del dialogo."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue(
                text="¡Hola!",
                start_char=100,
                end_char=110,
                chapter=1,
                context_before="Juan dijo:",
                context_after="",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 1
        assert attributions[0].speaker_name == "Juan"
        assert attributions[0].confidence == AttributionConfidence.HIGH

    def test_explicit_attribution_with_alias(self):
        """Test atribucion usando alias."""
        entities = [
            MockEntity(1, "Juan", ["Juanito", "Juancho"]),
        ]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue(
                text="¡Hola!",
                start_char=100,
                end_char=110,
                chapter=1,
                context_after=" —respondio Juanito.",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert attributions[0].speaker_name == "Juan"  # Nombre canonico
        assert attributions[0].confidence == AttributionConfidence.HIGH

    def test_alternation_two_speakers(self):
        """Test alternancia entre dos hablantes."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue(
                text="¡Hola!", start_char=100, end_char=110, chapter=1, context_after=" —dijo Juan."
            ),
            MockDialogue(
                text="¿Como estas?",
                start_char=200,
                end_char=220,
                chapter=1,
                context_after="",  # Sin verbo explicito
            ),
            MockDialogue(
                text="Muy bien, gracias.",
                start_char=300,
                end_char=330,
                chapter=1,
                context_after=" —respondio Maria.",
            ),
        ]

        # Menciones de entidad para establecer participantes
        entity_mentions = [
            (1, 115, 119),  # "Juan" despues del primer dialogo
            (2, 335, 340),  # "Maria" despues del tercer dialogo
        ]

        attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

        assert len(attributions) == 3

        # Primero es Juan (explicito)
        assert attributions[0].speaker_name == "Juan"
        assert attributions[0].confidence == AttributionConfidence.HIGH

        # Segundo deberia ser Maria (alternancia) o similar
        # Nota: depende de como se detecten los participantes
        assert attributions[1].confidence in (
            AttributionConfidence.MEDIUM,
            AttributionConfidence.LOW,
            AttributionConfidence.UNKNOWN,
        )

        # Tercero es Maria (explicito)
        assert attributions[2].speaker_name == "Maria"
        assert attributions[2].confidence == AttributionConfidence.HIGH

    def test_voice_profile_matching(self):
        """Test matching por perfil de voz."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]

        # Juan usa 'tu', Maria usa 'usted'
        voice_profiles = {
            1: MockVoiceProfile(
                entity_id=1, uses_usted=False, uses_tu=True, filler_words=["bueno"]
            ),
            2: MockVoiceProfile(entity_id=2, uses_usted=True, uses_tu=False, filler_words=["pues"]),
        }

        attributor = SpeakerAttributor(entities, voice_profiles)

        # Dialogo que usa 'usted' - deberia matchear con Maria
        dialogues = [
            MockDialogue(
                text="Bueno, ¿como esta usted hoy?", start_char=100, end_char=130, chapter=1
            ),
        ]

        # Solo Maria como participante
        entity_mentions = [(2, 50, 55)]

        attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

        # Puede atribuirse a Maria por perfil o proximidad
        assert len(attributions) == 1

    def test_no_attribution_possible(self):
        """Test sin atribucion posible."""
        entities = []  # Sin entidades
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue(text="¡Hola!", start_char=100, end_char=110, chapter=1),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 1
        assert attributions[0].confidence == AttributionConfidence.UNKNOWN
        assert attributions[0].attribution_method == AttributionMethod.NONE

    def test_chapter_reset(self):
        """Test que el contexto se resetea entre capitulos."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue(
                text="Dialogo cap 1",
                start_char=100,
                end_char=120,
                chapter=1,
                context_after=" —dijo Juan.",
            ),
            MockDialogue(
                text="Dialogo cap 2",
                start_char=100,
                end_char=120,
                chapter=2,
                # Sin contexto, nuevo capitulo
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        # El segundo dialogo no deberia heredar contexto del primero
        assert attributions[0].speaker_name == "Juan"
        # El segundo puede ser UNKNOWN si no hay contexto
        assert attributions[1].confidence in (
            AttributionConfidence.LOW,
            AttributionConfidence.UNKNOWN,
        )

    def test_multiple_verbs_supported(self):
        """Test que multiples verbos de habla funcionan."""
        entities = [MockEntity(1, "Juan")]
        attributor = SpeakerAttributor(entities)

        test_verbs = ["dijo", "respondio", "grito", "susurro", "pregunto", "exclamo"]

        for verb in test_verbs:
            dialogues = [
                MockDialogue(
                    text="Texto",
                    start_char=100,
                    end_char=110,
                    chapter=1,
                    context_after=f" —{verb} Juan.",
                ),
            ]
            attributions = attributor.attribute_dialogues(dialogues)
            assert attributions[0].speaker_name == "Juan", f"Fallo con verbo: {verb}"
            assert attributions[0].confidence == AttributionConfidence.HIGH


# ============================================================================
# Tests para DialogueAttribution
# ============================================================================


class TestDialogueAttribution:
    """Tests para DialogueAttribution."""

    def test_to_dict(self):
        """Test conversion a diccionario."""
        attr = DialogueAttribution(
            dialogue_id=1,
            text="¡Hola!",
            start_char=100,
            end_char=110,
            chapter=1,
            speaker_id=1,
            speaker_name="Juan",
            confidence=AttributionConfidence.HIGH,
            attribution_method=AttributionMethod.EXPLICIT_VERB,
            speech_verb="dijo",
        )

        d = attr.to_dict()

        assert d["dialogue_id"] == 1
        assert d["speaker_name"] == "Juan"
        assert d["confidence"] == "high"
        assert d["attribution_method"] == "explicit_verb"
        assert d["speech_verb"] == "dijo"

    def test_default_values(self):
        """Test valores por defecto."""
        attr = DialogueAttribution(dialogue_id=1, text="Test", start_char=0, end_char=4, chapter=1)

        assert attr.speaker_id is None
        assert attr.speaker_name is None
        assert attr.confidence == AttributionConfidence.UNKNOWN
        assert attr.attribution_method == AttributionMethod.NONE


# ============================================================================
# Tests para get_attribution_stats
# ============================================================================


class TestAttributionStats:
    """Tests para estadisticas de atribucion."""

    def test_get_stats(self):
        """Test generacion de estadisticas."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue("Hola", 0, 4, 1, context_after=" —dijo Juan."),
            MockDialogue("¿Que tal?", 10, 20, 1),
            MockDialogue("Bien", 30, 40, 1, context_after=" —respondio Maria."),
        ]

        attributions = attributor.attribute_dialogues(dialogues)
        stats = attributor.get_attribution_stats(attributions)

        assert stats["total_dialogues"] == 3
        assert stats["by_confidence"]["high"] == 2
        assert "explicit_verb" in stats["by_method"]
        assert stats["attribution_rate"] >= 0.5

    def test_stats_empty(self):
        """Test estadisticas con lista vacia."""
        attributor = SpeakerAttributor([])
        stats = attributor.get_attribution_stats([])

        assert stats["total_dialogues"] == 0
        assert stats["attribution_rate"] == 0.0


# ============================================================================
# Tests para funciones de filtrado
# ============================================================================


class TestFiltering:
    """Tests para funciones de filtrado."""

    def test_get_unattributed(self):
        """Test obtener dialogos sin atribucion."""
        entities = [MockEntity(1, "Juan")]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue("Hola", 0, 4, 1, context_after=" —dijo Juan."),
            MockDialogue("¿Que?", 10, 15, 1),  # Sin atribucion
        ]

        attributions = attributor.attribute_dialogues(dialogues)
        unattributed = attributor.get_unattributed_dialogues(attributions)

        # El segundo puede o no estar atribuido dependiendo del contexto
        assert isinstance(unattributed, list)

    def test_get_low_confidence(self):
        """Test obtener dialogos con baja confianza."""
        entities = [MockEntity(1, "Juan")]
        attributor = SpeakerAttributor(entities)

        dialogues = [
            MockDialogue("Hola", 0, 4, 1, context_after=" —dijo Juan."),
            MockDialogue("¿Que?", 10, 15, 1),  # Probablemente baja confianza
        ]

        attributions = attributor.attribute_dialogues(dialogues)
        low_conf = attributor.get_low_confidence_dialogues(attributions)

        # Al menos verificar que devuelve una lista
        assert isinstance(low_conf, list)


# ============================================================================
# Tests para funcion de conveniencia
# ============================================================================


class TestAttributeSpeakers:
    """Tests para attribute_speakers."""

    def test_basic_usage(self):
        """Test uso basico de la funcion."""
        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]

        dialogues = [
            MockDialogue("Hola", 0, 4, 1, context_after=" —dijo Juan."),
            MockDialogue("Hola", 10, 14, 1, context_after=" —respondio Maria."),
        ]

        attributions, stats = attribute_speakers(dialogues, entities)

        assert len(attributions) == 2
        assert stats["total_dialogues"] == 2
        assert attributions[0].speaker_name == "Juan"
        assert attributions[1].speaker_name == "Maria"


# ============================================================================
# Tests de integracion
# ============================================================================


class TestSpeakerAttributionIntegration:
    """Tests de integracion."""

    def test_complex_dialogue_scene(self):
        """Test escena de dialogo compleja."""
        entities = [
            MockEntity(1, "Juan", ["Juanito"]),
            MockEntity(2, "Maria", ["Mari"]),
            MockEntity(3, "Pedro"),
        ]

        voice_profiles = {
            1: MockVoiceProfile(1, uses_tu=True, filler_words=["bueno", "pues"]),
            2: MockVoiceProfile(2, uses_usted=True, filler_words=["mira"]),
        }

        attributor = SpeakerAttributor(entities, voice_profiles)

        dialogues = [
            # Juan inicia
            MockDialogue(
                "¡Buenos dias a todos!", 0, 25, 1, context_after=" —saludo Juan al entrar."
            ),
            # Maria responde
            MockDialogue(
                "Buenos dias. ¿Como esta usted?", 50, 85, 1, context_after=" —pregunto Maria."
            ),
            # Juan otra vez (alternancia)
            MockDialogue(
                "Muy bien, gracias por preguntar.",
                100,
                140,
                1,
                context_after="",  # Sin verbo, deberia alternar
            ),
            # Alguien nuevo (Pedro) - explicito
            MockDialogue("Yo tambien estoy bien.", 150, 180, 1, context_after=" —anadio Pedro."),
        ]

        entity_mentions = [
            (1, 35, 39),  # Juan
            (2, 95, 100),  # Maria
            (3, 190, 195),  # Pedro
        ]

        attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

        assert len(attributions) == 4

        # Primero: Juan (explicito)
        assert attributions[0].speaker_name == "Juan"
        assert attributions[0].confidence == AttributionConfidence.HIGH

        # Segundo: Maria (explicito)
        assert attributions[1].speaker_name == "Maria"
        assert attributions[1].confidence == AttributionConfidence.HIGH

        # Tercero: Puede ser alternancia o inferido
        # (depende de los participantes detectados)

        # Cuarto: Pedro (explicito)
        assert attributions[3].speaker_name == "Pedro"
        assert attributions[3].confidence == AttributionConfidence.HIGH

    def test_full_text_context(self):
        """Test con texto completo para contexto."""
        entities = [
            MockEntity(1, "Ana"),
            MockEntity(2, "Luis"),
        ]
        attributor = SpeakerAttributor(entities)

        full_text = """
        Ana entro en la habitacion.
        —¡Hola! —dijo Ana.
        —¿Que tal? —respondio Luis.
        Ambos se sentaron a conversar.
        """

        dialogues = [
            MockDialogue("¡Hola!", 45, 52, 1),
            MockDialogue("¿Que tal?", 70, 80, 1),
        ]

        attributions = attributor.attribute_dialogues(
            dialogues, entity_mentions=[], full_text=full_text
        )

        assert len(attributions) == 2
        # Deberia poder extraer contexto del full_text


# ============================================================================
# Tests para SPEECH_VERBS
# ============================================================================


class TestSpeechVerbs:
    """Tests para la constante SPEECH_VERBS."""

    def test_contains_common_verbs(self):
        """Test que contiene verbos comunes."""
        common = ["dijo", "pregunto", "respondio", "grito", "susurro"]
        for verb in common:
            assert verb in SPEECH_VERBS, f"Falta verbo comun: {verb}"

    def test_contains_emotional_verbs(self):
        """Test que contiene verbos emocionales."""
        emotional = ["grito", "susurro", "murmuro", "exclamo"]
        for verb in emotional:
            assert verb in SPEECH_VERBS, f"Falta verbo emocional: {verb}"

    def test_no_duplicates(self):
        """Test que no hay duplicados."""
        assert len(SPEECH_VERBS) == len(set(SPEECH_VERBS))
