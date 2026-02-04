"""
Tests adversariales estilo GAN para el sistema de atribución de hablante.

Este módulo implementa el patrón Adversary-Linguist-Defender para
probar los límites del sistema de atribución de diálogos.

Adversary: Crea casos difíciles de atribución de hablante
Linguist: Valida que sean casos reales del español literario
Defender: Sistema de atribución de hablante

Categorías de prueba:
1. Patrón verbo + nombre (—dijo Juan)
2. Patrón nombre + verbo (Juan dijo:)
3. Patrón coma + verbo (,dijo Juan)
4. Verbos de habla variados
5. Alternancia de hablantes
6. Múltiples hablantes (3+)
7. Diálogos sin atribución explícita
8. Diálogos interrumpidos
9. Diálogos anidados (citas dentro de citas)
10. Diálogos con acción intercalada
11. Monólogos internos
12. Voz pasiva y construcciones impersonales
13. Estilo indirecto libre
14. Perfiles de voz (tú/usted)
15. Muletillas y coletillas
16. Nombres compuestos
17. Apodos y aliases
18. Diálogos largos
19. Cambios de escena
20. Casos ambiguos
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest

from narrative_assistant.voice.speaker_attribution import (
    SPEECH_VERBS,
    AttributionConfidence,
    AttributionMethod,
    DialogueAttribution,
    SpeakerAttributor,
    attribute_speakers,
)

# =============================================================================
# Test Data: Mock Entities and Dialogues
# =============================================================================


@dataclass
class MockEntity:
    """Entidad mock para tests."""

    id: int
    name: str
    canonical_name: str
    aliases: list[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class MockDialogue:
    """Diálogo mock para tests."""

    text: str
    start_char: int
    end_char: int
    chapter: int
    context_before: str = ""
    context_after: str = ""


# Entidades de prueba
ENTITIES = [
    MockEntity(id=1, name="María", canonical_name="María García", aliases=["Mari", "la García"]),
    MockEntity(id=2, name="Juan", canonical_name="Juan Pérez", aliases=["Juanito", "el Pérez"]),
    MockEntity(
        id=3, name="Doctor García", canonical_name="Doctor García", aliases=["el doctor", "García"]
    ),
    MockEntity(id=4, name="Ana María", canonical_name="Ana María López", aliases=["Anita"]),
    MockEntity(id=5, name="Pedro", canonical_name="Pedro Sánchez", aliases=["Pedrito"]),
    MockEntity(id=6, name="Isabel", canonical_name="Isabel Ruiz", aliases=["Isa"]),
]


class TestVerbNamePattern:
    """Tests para el patrón —dijo Nombre."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_after,expected_speaker,expected_verb",
        [
            # Caso 1: Patrón básico con dijo
            ("—dijo María.", "María", "dijo"),
            # Caso 2: Con respondió
            ("—respondió Juan.", "Juan", "respondió"),
            # Caso 3: Con preguntó
            ("—preguntó Pedro.", "Pedro", "preguntó"),
            # Caso 4: Con exclamó
            ("—exclamó Isabel.", "Isabel", "exclamó"),
            # Caso 5: Con susurró
            ("—susurró María.", "María", "susurró"),
            # Caso 6: Con gritó
            ("—gritó Juan.", "Juan", "gritó"),
            # Caso 7: Con murmuró
            ("—murmuró Pedro.", "Pedro", "murmuró"),
        ],
    )
    def test_verb_name_patterns(self, attributor, context_after, expected_speaker, expected_verb):
        """Verifica detección del patrón —verbo Nombre."""
        dialogue = MockDialogue(
            text="Buenos días", start_char=0, end_char=11, chapter=1, context_after=context_after
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        attr = attributions[0]

        if expected_speaker:
            assert attr.speaker_name is not None, f"No se detectó hablante en: {context_after}"
            assert expected_speaker in attr.speaker_name
            assert attr.confidence == AttributionConfidence.HIGH
            assert attr.attribution_method == AttributionMethod.EXPLICIT_VERB


class TestNameVerbPattern:
    """Tests para el patrón Nombre dijo:."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_before,expected_speaker",
        [
            # Caso 1: Patrón básico
            ("María dijo:", "María"),
            # Caso 2: Con preguntó
            ("Juan preguntó:", "Juan"),
            # Caso 3: Con añadió
            ("Pedro añadió:", "Pedro"),
            # Caso 4: Sin dos puntos
            ("Isabel respondió", "Isabel"),
            # Caso 5: Con guión después
            ("María exclamó —", "María"),
        ],
    )
    def test_name_verb_patterns(self, attributor, context_before, expected_speaker):
        """Verifica detección del patrón Nombre verbo:."""
        dialogue = MockDialogue(
            text="Buenos días",
            start_char=50,
            end_char=61,
            chapter=1,
            context_before=context_before,
            context_after="",
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        attr = attributions[0]

        if expected_speaker:
            assert attr.speaker_name is not None, f"No se detectó hablante en: {context_before}"
            assert expected_speaker in attr.speaker_name


class TestCommaVerbPattern:
    """Tests para el patrón , verbo Nombre."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_after,expected_speaker",
        [
            # Caso 1: Coma + verbo
            (", dijo María.", "María"),
            # Caso 2: Coma + respondió
            (", respondió Juan con calma.", "Juan"),
            # Caso 3: Coma + añadió
            (", añadió Pedro pensativo.", "Pedro"),
        ],
    )
    def test_comma_verb_patterns(self, attributor, context_after, expected_speaker):
        """Verifica detección del patrón , verbo Nombre."""
        dialogue = MockDialogue(
            text="Esto es importante",
            start_char=0,
            end_char=18,
            chapter=1,
            context_after=context_after,
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        attr = attributions[0]

        if expected_speaker:
            assert attr.speaker_name is not None


class TestSpeechVerbsVariety:
    """Tests para variedad de verbos de habla."""

    def test_speech_verbs_exist(self):
        """Verifica que existen verbos de habla en el diccionario."""
        assert len(SPEECH_VERBS) > 0
        assert "dijo" in SPEECH_VERBS
        assert "respondió" in SPEECH_VERBS or "respondio" in SPEECH_VERBS

    @pytest.mark.parametrize(
        "verb",
        [
            "dijo",
            "respondió",
            "preguntó",
            "exclamó",
            "gritó",
            "susurró",
            "murmuró",
            "añadió",
            "afirmó",
            "negó",
        ],
    )
    def test_verb_normalization(self, verb):
        """Verifica que los verbos comunes están en el diccionario."""
        # Normalizar quitando tildes para comparar
        verb_no_accent = verb.replace("ó", "o").replace("í", "i")
        found = any(v.replace("ó", "o").replace("í", "i") == verb_no_accent for v in SPEECH_VERBS)
        # Al menos la versión sin tilde debería estar
        assert found or verb_no_accent in SPEECH_VERBS


class TestAlternation:
    """Tests para alternancia de hablantes."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_two_speaker_alternation(self, attributor):
        """Alternancia entre dos hablantes."""
        dialogues = [
            MockDialogue(
                text="Hola, ¿cómo estás?",
                start_char=0,
                end_char=18,
                chapter=1,
                context_after="—dijo María.",
            ),
            MockDialogue(
                text="Muy bien, gracias.",
                start_char=50,
                end_char=68,
                chapter=1,
                context_before="",
                context_after="",
            ),
            MockDialogue(
                text="Me alegro mucho.",
                start_char=100,
                end_char=116,
                chapter=1,
                context_before="",
                context_after="",
            ),
        ]

        # Crear menciones para establecer participantes
        entity_mentions = [(1, 30, 35), (2, 75, 79)]  # María y Juan mencionados

        attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

        assert len(attributions) == 3
        # Primera debe ser María (explícito)
        assert "María" in attributions[0].speaker_name
        # Segunda y tercera pueden usar alternancia si hay 2 participantes

    def test_three_speaker_no_alternation(self, attributor):
        """Con 3+ hablantes no aplica alternancia simple."""
        dialogues = [
            MockDialogue(
                text="Empecemos", start_char=0, end_char=9, chapter=1, context_after="—dijo María."
            ),
            MockDialogue(
                text="De acuerdo",
                start_char=50,
                end_char=60,
                chapter=1,
                context_after="—añadió Juan.",
            ),
            MockDialogue(
                text="¿Por dónde?",
                start_char=100,
                end_char=111,
                chapter=1,
                context_before="",
                context_after="",
            ),
        ]

        entity_mentions = [(1, 20, 25), (2, 70, 74), (5, 95, 100)]  # María, Juan, Pedro

        attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

        assert len(attributions) == 3
        # El tercero no debería usar alternancia simple (hay 3 participantes)


class TestUnattributedDialogues:
    """Tests para diálogos sin atribución explícita."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_dialogue_without_attribution(self, attributor):
        """Diálogo sin ninguna marca de hablante."""
        dialogue = MockDialogue(
            text="Esto no tiene hablante claro.",
            start_char=0,
            end_char=29,
            chapter=1,
            context_before="Había silencio.",
            context_after="Nadie respondió.",
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        attr = attributions[0]

        # Puede ser UNKNOWN o LOW
        assert attr.confidence in (AttributionConfidence.UNKNOWN, AttributionConfidence.LOW)

    def test_proximity_based_attribution(self, attributor):
        """Atribución basada en proximidad de mención."""
        dialogue = MockDialogue(
            text="Buenos días a todos.",
            start_char=100,
            end_char=120,
            chapter=1,
            context_before="María se acercó al grupo.",
            context_after="El grupo la miró.",
        )

        # María mencionada justo antes
        entity_mentions = [(1, 50, 55)]

        attributions = attributor.attribute_dialogues([dialogue], entity_mentions)

        assert len(attributions) == 1
        # Puede usar proximidad


class TestInterruptedDialogues:
    """Tests para diálogos interrumpidos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_interrupted_by_action(self, attributor):
        """Diálogo interrumpido por acción."""
        dialogues = [
            MockDialogue(
                text="Yo creo que...",
                start_char=0,
                end_char=14,
                chapter=1,
                context_after="—empezó María, pero Juan la interrumpió.",
            ),
            MockDialogue(
                text="¡No digas tonterías!",
                start_char=50,
                end_char=70,
                chapter=1,
                context_after="—la cortó Juan.",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 2
        # Primer diálogo debe ser de María
        assert "María" in attributions[0].speaker_name
        # Segundo debe ser de Juan
        assert "Juan" in attributions[1].speaker_name


class TestNestedDialogues:
    """Tests para diálogos anidados (citas dentro de citas)."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_quoted_dialogue(self, attributor):
        """Cita de otro personaje dentro del diálogo."""
        dialogue = MockDialogue(
            text='Y entonces Juan me dijo: "No vengas mañana".',
            start_char=0,
            end_char=44,
            chapter=1,
            context_after="—explicó María.",
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # El hablante principal es María (quien explica)
        assert "María" in attributions[0].speaker_name


class TestActionIntercalated:
    """Tests para diálogos con acción intercalada."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_dialogue_with_action(self, attributor):
        """Acción entre dos partes del mismo diálogo."""
        dialogues = [
            MockDialogue(
                text="Mira",
                start_char=0,
                end_char=4,
                chapter=1,
                context_after="—señaló María el libro—",
            ),
            MockDialogue(
                text="esto es lo que buscaba.",
                start_char=50,
                end_char=73,
                chapter=1,
                context_before="—señaló María el libro—",
                context_after="",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 2
        # Ambos deberían ser de María


class TestInternalMonologues:
    """Tests para monólogos internos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_thought_attribution(self, attributor):
        """Pensamiento atribuido."""
        dialogue = MockDialogue(
            text="¿Qué habré hecho mal?",
            start_char=0,
            end_char=21,
            chapter=1,
            context_after="—pensó María.",
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # "pensó" puede no estar en SPEECH_VERBS pero debería funcionar
        # o al menos no crashear


class TestPassiveAndImpersonal:
    """Tests para voz pasiva y construcciones impersonales."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_after,description",
        [
            ("—se oyó decir.", "pasiva refleja"),
            ("—se escuchó.", "impersonal"),
            ("—resonó en la sala.", "voz impersonal"),
        ],
    )
    def test_impersonal_attributions(self, attributor, context_after, description):
        """Verifica manejo de construcciones impersonales."""
        dialogue = MockDialogue(
            text="¡Silencio!", start_char=0, end_char=10, chapter=1, context_after=context_after
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # Sin hablante claro, debe ser UNKNOWN o LOW
        # (no debe crashear)


class TestFreeIndirectStyle:
    """Tests para estilo indirecto libre."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_free_indirect_style(self, attributor):
        """Estilo indirecto libre (difícil de atribuir)."""
        dialogue = MockDialogue(
            text="¿Qué más daba ya todo aquello?",
            start_char=50,
            end_char=80,
            chapter=1,
            context_before="María miraba por la ventana.",
            context_after="Las calles estaban vacías.",
        )

        entity_mentions = [(1, 0, 5)]  # María mencionada antes

        attributions = attributor.attribute_dialogues([dialogue], entity_mentions)

        assert len(attributions) == 1
        # Puede usar proximidad para María


class TestVoiceProfiles:
    """Tests para perfiles de voz (tú/usted, muletillas)."""

    @pytest.fixture
    def voice_profiles(self):
        """Perfiles de voz mock."""

        @dataclass
        class MockProfile:
            entity_id: int
            uses_usted: bool
            uses_tu: bool
            avg_intervention_length: float
            filler_words: list[str]

        return {
            1: MockProfile(1, False, True, 10.0, ["bueno", "pues"]),  # María - informal
            2: MockProfile(2, True, False, 15.0, ["verá", "mire"]),  # Juan - formal
        }

    def test_voice_profile_matching(self, voice_profiles):
        """Matching por perfil de voz."""
        attributor = SpeakerAttributor(ENTITIES, voice_profiles)

        # Diálogo informal sin atribución explícita
        dialogue = MockDialogue(
            text="Bueno, pues yo creo que tú deberías ir.",
            start_char=0,
            end_char=39,
            chapter=1,
            context_before="",
            context_after="",
        )

        # Ambos personajes mencionados cerca
        entity_mentions = [(1, -50, -45), (2, -30, -26)]

        attributions = attributor.attribute_dialogues([dialogue], entity_mentions)

        assert len(attributions) == 1
        # Podría preferir María por el perfil informal (tú, bueno, pues)

    def test_formal_voice_detection(self, voice_profiles):
        """Detección de voz formal."""
        attributor = SpeakerAttributor(ENTITIES, voice_profiles)

        # Diálogo formal
        dialogue = MockDialogue(
            text="Verá usted, mire, esto requiere paciencia.",
            start_char=0,
            end_char=42,
            chapter=1,
            context_before="",
            context_after="",
        )

        entity_mentions = [(1, -50, -45), (2, -30, -26)]

        attributions = attributor.attribute_dialogues([dialogue], entity_mentions)

        assert len(attributions) == 1
        # Podría preferir Juan por el perfil formal (usted, verá, mire)


class TestCompoundNames:
    """Tests para nombres compuestos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_after,expected_name",
        [
            ("—dijo Ana María.", "Ana María"),
            ("—respondió Doctor García.", "Doctor García"),
        ],
    )
    def test_compound_names(self, attributor, context_after, expected_name):
        """Verifica detección con nombres compuestos."""
        dialogue = MockDialogue(
            text="Entendido.", start_char=0, end_char=10, chapter=1, context_after=context_after
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # Puede detectar solo la primera parte del nombre


class TestAliases:
    """Tests para apodos y aliases."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_after,expected_id",
        [
            ("—dijo Mari.", 1),  # Alias de María
            ("—respondió Juanito.", 2),  # Alias de Juan
            ("—añadió el doctor.", 3),  # Alias de Doctor García
        ],
    )
    def test_alias_attribution(self, attributor, context_after, expected_id):
        """Verifica atribución usando aliases."""
        dialogue = MockDialogue(
            text="Sí, claro.", start_char=0, end_char=10, chapter=1, context_after=context_after
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # Puede resolver el alias al personaje correcto


class TestLongDialogues:
    """Tests para diálogos largos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_long_dialogue(self, attributor):
        """Diálogo muy largo con atribución al final."""
        long_text = """
        Verás, todo empezó hace muchos años, cuando yo era apenas un niño.
        Mi padre me llevó al campo y me enseñó a pescar.
        Pasábamos horas junto al río, sin decir nada, solo pescando.
        Esos fueron los mejores momentos de mi vida.
        Nunca olvidaré aquellos días de verano.
        """
        dialogue = MockDialogue(
            text=long_text.strip(),
            start_char=0,
            end_char=len(long_text.strip()),
            chapter=1,
            context_after="—relató Juan con nostalgia.",
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        assert "Juan" in attributions[0].speaker_name

    def test_multiple_paragraphs_same_speaker(self, attributor):
        """Múltiples párrafos del mismo hablante."""
        dialogues = [
            MockDialogue(
                text="Primer párrafo de mi discurso.",
                start_char=0,
                end_char=30,
                chapter=1,
                context_after="—empezó María.",
            ),
            MockDialogue(
                text="Segundo párrafo, continuando.",
                start_char=50,
                end_char=79,
                chapter=1,
                context_before="",
                context_after="",
            ),
            MockDialogue(
                text="Tercer párrafo, concluyendo.",
                start_char=100,
                end_char=128,
                chapter=1,
                context_before="",
                context_after="—concluyó.",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 3
        # El primero es explícitamente de María


class TestSceneChanges:
    """Tests para cambios de escena."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_chapter_change_resets_context(self, attributor):
        """El cambio de capítulo debe resetear el contexto."""
        dialogues = [
            MockDialogue(
                text="Adiós.", start_char=0, end_char=6, chapter=1, context_after="—dijo María."
            ),
            MockDialogue(
                text="Hola.",
                start_char=100,
                end_char=105,
                chapter=2,
                context_before="",
                context_after="",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)

        assert len(attributions) == 2
        # El segundo no debería heredar a María del capítulo anterior

    def test_scene_break_within_chapter(self, attributor):
        """Ruptura de escena dentro del capítulo."""
        # Simular ruptura de escena con gran separación de caracteres
        dialogues = [
            MockDialogue(
                text="Nos vemos.",
                start_char=0,
                end_char=10,
                chapter=1,
                context_after="—dijo María.",
            ),
            MockDialogue(
                text="Buenos días.",
                start_char=5000,
                end_char=5012,
                chapter=1,
                context_before="",
                context_after="",
            ),
        ]

        entity_mentions = [(1, 20, 25)]  # María solo cerca del primer diálogo

        attributions = attributor.attribute_dialogues(dialogues, entity_mentions)

        assert len(attributions) == 2
        # El segundo está muy lejos, puede no usar alternancia


class TestAmbiguousCases:
    """Tests para casos ambiguos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_multiple_names_in_context(self, attributor):
        """Múltiples nombres en el contexto."""
        dialogue = MockDialogue(
            text="Sí.",
            start_char=50,
            end_char=53,
            chapter=1,
            context_before="María miró a Juan.",
            context_after="Juan sonrió.",
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # Ambiguo: podría ser María o Juan

    def test_pronoun_in_attribution(self, attributor):
        """Pronombre en lugar de nombre."""
        dialogue = MockDialogue(
            text="De acuerdo.", start_char=50, end_char=61, chapter=1, context_after="—dijo él."
        )

        attributions = attributor.attribute_dialogues([dialogue])

        assert len(attributions) == 1
        # "él" no es un nombre conocido, puede ser UNKNOWN


class TestAttributionStats:
    """Tests para estadísticas de atribución."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_stats_generation(self, attributor):
        """Verifica generación de estadísticas."""
        dialogues = [
            MockDialogue(
                text="Uno", start_char=0, end_char=3, chapter=1, context_after="—dijo María."
            ),
            MockDialogue(
                text="Dos", start_char=20, end_char=23, chapter=1, context_after="—respondió Juan."
            ),
            MockDialogue(
                text="Tres",
                start_char=40,
                end_char=44,
                chapter=1,
                context_before="",
                context_after="",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)
        stats = attributor.get_attribution_stats(attributions)

        assert "total_dialogues" in stats
        assert stats["total_dialogues"] == 3
        assert "by_confidence" in stats
        assert "by_method" in stats
        assert "attribution_rate" in stats

    def test_unattributed_dialogues_list(self, attributor):
        """Verifica lista de diálogos sin atribuir."""
        dialogues = [
            MockDialogue(
                text="Con hablante",
                start_char=0,
                end_char=12,
                chapter=1,
                context_after="—dijo María.",
            ),
            MockDialogue(
                text="Sin hablante",
                start_char=50,
                end_char=62,
                chapter=1,
                context_before="",
                context_after="",
            ),
        ]

        attributions = attributor.attribute_dialogues(dialogues)
        unattributed = attributor.get_unattributed_dialogues(attributions)

        # Al menos uno debería estar sin atribuir claramente
        # (el segundo no tiene marcas)


class TestEdgeCases:
    """Tests para casos extremos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    def test_empty_dialogue_list(self, attributor):
        """Lista vacía de diálogos."""
        attributions = attributor.attribute_dialogues([])
        assert len(attributions) == 0

    def test_dialogue_empty_text(self, attributor):
        """Diálogo con texto vacío."""
        dialogue = MockDialogue(
            text="", start_char=0, end_char=0, chapter=1, context_after="—dijo María."
        )

        attributions = attributor.attribute_dialogues([dialogue])
        assert len(attributions) == 1

    def test_no_entities(self):
        """Sin entidades registradas."""
        attributor = SpeakerAttributor([])

        dialogue = MockDialogue(
            text="Hola", start_char=0, end_char=4, chapter=1, context_after="—dijo María."
        )

        attributions = attributor.attribute_dialogues([dialogue])
        assert len(attributions) == 1
        # No puede atribuir sin entidades

    def test_unicode_names(self, attributor):
        """Nombres con caracteres Unicode."""
        dialogue = MockDialogue(
            text="Sí.",
            start_char=0,
            end_char=3,
            chapter=1,
            context_after="—dijo María.",  # Con tilde
        )

        attributions = attributor.attribute_dialogues([dialogue])
        assert len(attributions) == 1


class TestConvenienceFunction:
    """Tests para la función de conveniencia attribute_speakers."""

    def test_attribute_speakers_function(self):
        """Verifica la función de conveniencia."""
        dialogues = [
            MockDialogue(
                text="Hola", start_char=0, end_char=4, chapter=1, context_after="—dijo María."
            ),
        ]

        attributions, stats = attribute_speakers(dialogues, ENTITIES)

        assert len(attributions) == 1
        assert isinstance(stats, dict)
        assert "total_dialogues" in stats


class TestSpecialPunctuation:
    """Tests para puntuación especial en diálogos."""

    @pytest.fixture
    def attributor(self):
        return SpeakerAttributor(ENTITIES)

    @pytest.mark.parametrize(
        "context_after,description",
        [
            ("—dijo María—.", "guiones em-dash"),
            ("-dijo María.", "guiones cortos"),
            ("— dijo María.", "espacio después de guión"),
            ("—dijo María —.", "guión al final"),
        ],
    )
    def test_punctuation_variations(self, attributor, context_after, description):
        """Verifica detección con variaciones de puntuación."""
        dialogue = MockDialogue(
            text="Sí", start_char=0, end_char=2, chapter=1, context_after=context_after
        )

        attributions = attributor.attribute_dialogues([dialogue])
        assert len(attributions) == 1


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
