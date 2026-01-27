"""
Tests adversariales GAN-style para el sistema de coherencia emocional.

Objetivo: Identificar casos límite donde el sistema detecta incorrectamente
incoherencias o falla en detectar problemas reales.

Categorías de tests:
1. Emoción-diálogo coherente (no debe alertar)
2. Emoción-diálogo incoherente (debe alertar)
3. Emoción-acción coherente
4. Emoción-acción incoherente
5. Ironía y sarcasmo (coherencia válida)
6. Disimulo (personaje ocultando emociones)
7. Emociones mixtas
8. Cambios emocionales válidos
9. Cambios emocionales abruptos (inválidos)
10. Contexto cultural
11. Género literario específico
12. Estados emocionales ambiguos
13. Narrador vs personaje
14. Emociones graduales
15. Catarsis emocional
16. Shock y trauma
17. Humor negro
18. Emociones complejas
19. Negación emocional
20. Expresiones idiomáticas emocionales

Basado en patrones de escritura narrativa española.
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmotionalCoherenceTestCase:
    """Caso de test para coherencia emocional."""
    id: str
    category: str
    text: str
    entity_name: str
    declared_emotion: str
    should_be_incoherent: bool  # True si DEBE detectar incoherencia
    incoherence_type: Optional[str] = None  # "emotion_dialogue", "emotion_action", "temporal_jump"
    difficulty: str = "medium"
    linguistic_note: str = ""


# =============================================================================
# CATEGORÍA 1: EMOCIÓN-DIÁLOGO COHERENTE (no debe alertar)
# =============================================================================

COHERENT_DIALOGUE_TESTS = [
    EmotionalCoherenceTestCase(
        id="coh_dial_01_feliz_positivo",
        category="dialogo_coherente",
        text='María estaba feliz. —¡Qué maravilloso día! —exclamó con alegría.',
        entity_name="María",
        declared_emotion="feliz",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Emoción positiva + diálogo positivo = coherente"
    ),
    EmotionalCoherenceTestCase(
        id="coh_dial_02_triste_negativo",
        category="dialogo_coherente",
        text='Juan estaba triste. —Todo se ha perdido —murmuró abatido.',
        entity_name="Juan",
        declared_emotion="triste",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Emoción negativa + diálogo negativo = coherente"
    ),
    EmotionalCoherenceTestCase(
        id="coh_dial_03_enfadado_agresivo",
        category="dialogo_coherente",
        text='Pedro estaba furioso. —¡Esto es inaceptable! —gritó golpeando la mesa.',
        entity_name="Pedro",
        declared_emotion="furioso",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Furia + diálogo agresivo = coherente"
    ),
    EmotionalCoherenceTestCase(
        id="coh_dial_04_asustado_temeroso",
        category="dialogo_coherente",
        text='Ana estaba aterrada. —No... no puedo hacerlo —tartamudeó temblando.',
        entity_name="Ana",
        declared_emotion="aterrada",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Miedo + diálogo temeroso = coherente"
    ),
    EmotionalCoherenceTestCase(
        id="coh_dial_05_tranquilo_neutro",
        category="dialogo_coherente",
        text='Carlos estaba sereno. —Veamos qué opciones tenemos —dijo con calma.',
        entity_name="Carlos",
        declared_emotion="sereno",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Serenidad + diálogo neutro = coherente"
    ),
]

# =============================================================================
# CATEGORÍA 2: EMOCIÓN-DIÁLOGO INCOHERENTE (debe alertar)
# =============================================================================

INCOHERENT_DIALOGUE_TESTS = [
    EmotionalCoherenceTestCase(
        id="inc_dial_01_triste_alegre",
        category="dialogo_incoherente",
        text='María estaba devastada por la noticia. —¡Fantástico, esto es genial! —exclamó riendo.',
        entity_name="María",
        declared_emotion="devastada",
        should_be_incoherent=True,
        incoherence_type="emotion_dialogue",
        difficulty="easy",
        linguistic_note="Devastación + diálogo alegre = incoherente"
    ),
    EmotionalCoherenceTestCase(
        id="inc_dial_02_feliz_negativo",
        category="dialogo_incoherente",
        text='Juan estaba eufórico. —Todo es horrible, nada tiene sentido —dijo con amargura.',
        entity_name="Juan",
        declared_emotion="eufórico",
        should_be_incoherent=True,
        incoherence_type="emotion_dialogue",
        difficulty="easy",
        linguistic_note="Euforia + diálogo amargo = incoherente"
    ),
    EmotionalCoherenceTestCase(
        id="inc_dial_03_asustado_valiente",
        category="dialogo_incoherente",
        text='Pedro estaba aterrado. —¡Adelante, no les tengo miedo! —gritó con valentía.',
        entity_name="Pedro",
        declared_emotion="aterrado",
        should_be_incoherent=True,
        incoherence_type="emotion_dialogue",
        difficulty="medium",
        linguistic_note="Terror + diálogo valiente = incoherente"
    ),
    EmotionalCoherenceTestCase(
        id="inc_dial_04_furioso_amable",
        category="dialogo_incoherente",
        text='Ana estaba furiosa. —Por supuesto, querido, como tú digas —respondió dulcemente.',
        entity_name="Ana",
        declared_emotion="furiosa",
        should_be_incoherent=True,
        incoherence_type="emotion_dialogue",
        difficulty="medium",
        linguistic_note="Furia + respuesta dulce = incoherente (o disimulo)"
    ),
]

# =============================================================================
# CATEGORÍA 3: EMOCIÓN-ACCIÓN COHERENTE
# =============================================================================

COHERENT_ACTION_TESTS = [
    EmotionalCoherenceTestCase(
        id="coh_act_01_feliz_sonrie",
        category="accion_coherente",
        text="María estaba feliz. Sonreía mientras caminaba por el parque.",
        entity_name="María",
        declared_emotion="feliz",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Felicidad + sonrisa = coherente"
    ),
    EmotionalCoherenceTestCase(
        id="coh_act_02_triste_llora",
        category="accion_coherente",
        text="Juan estaba destrozado. Las lágrimas corrían por su rostro.",
        entity_name="Juan",
        declared_emotion="destrozado",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Tristeza + llorar = coherente"
    ),
    EmotionalCoherenceTestCase(
        id="coh_act_03_nervioso_temblor",
        category="accion_coherente",
        text="Pedro estaba muy nervioso. Sus manos temblaban al sostener el papel.",
        entity_name="Pedro",
        declared_emotion="nervioso",
        should_be_incoherent=False,
        difficulty="easy",
        linguistic_note="Nerviosismo + temblor = coherente"
    ),
]

# =============================================================================
# CATEGORÍA 4: EMOCIÓN-ACCIÓN INCOHERENTE
# =============================================================================

INCOHERENT_ACTION_TESTS = [
    EmotionalCoherenceTestCase(
        id="inc_act_01_triste_rie",
        category="accion_incoherente",
        text="María estaba profundamente deprimida. Saltaba de alegría por la habitación.",
        entity_name="María",
        declared_emotion="deprimida",
        should_be_incoherent=True,
        incoherence_type="emotion_action",
        difficulty="easy",
        linguistic_note="Depresión + saltar de alegría = incoherente"
    ),
    EmotionalCoherenceTestCase(
        id="inc_act_02_sereno_violento",
        category="accion_incoherente",
        text="Juan estaba completamente sereno. Golpeó la pared con furia.",
        entity_name="Juan",
        declared_emotion="sereno",
        should_be_incoherent=True,
        incoherence_type="emotion_action",
        difficulty="easy",
        linguistic_note="Serenidad + golpe furioso = incoherente"
    ),
]

# =============================================================================
# CATEGORÍA 5: IRONÍA Y SARCASMO (coherencia válida)
# =============================================================================

IRONY_TESTS = [
    EmotionalCoherenceTestCase(
        id="irony_01_explicita",
        category="ironia",
        text='María estaba furiosa. —¡Qué maravilla! —dijo con evidente sarcasmo.',
        entity_name="María",
        declared_emotion="furiosa",
        should_be_incoherent=False,  # El sarcasmo explica la discrepancia
        difficulty="hard",
        linguistic_note="Sarcasmo explícito hace coherente el contraste"
    ),
    EmotionalCoherenceTestCase(
        id="irony_02_mordaz",
        category="ironia",
        text='Juan estaba irritado. —Claro, perfecto, genial —respondió mordazmente.',
        entity_name="Juan",
        declared_emotion="irritado",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Respuesta mordaz coherente con irritación"
    ),
    EmotionalCoherenceTestCase(
        id="irony_03_burlona",
        category="ironia",
        text='Ana estaba enfadada. —Qué inteligente —comentó con tono burlón.',
        entity_name="Ana",
        declared_emotion="enfadada",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Burla coherente con enfado"
    ),
]

# =============================================================================
# CATEGORÍA 6: DISIMULO (personaje ocultando emociones)
# =============================================================================

CONCEALMENT_TESTS = [
    EmotionalCoherenceTestCase(
        id="conc_01_explicito",
        category="disimulo",
        text='María estaba aterrada, pero fingió serenidad. —Todo está bien —mintió.',
        entity_name="María",
        declared_emotion="aterrada",
        should_be_incoherent=False,  # El fingimiento está explícito
        difficulty="hard",
        linguistic_note="Fingimiento explícito hace coherente"
    ),
    EmotionalCoherenceTestCase(
        id="conc_02_ocultando",
        category="disimulo",
        text='Juan hervía de rabia por dentro, pero mantuvo la compostura. —Entiendo.',
        entity_name="Juan",
        declared_emotion="rabia",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="'Por dentro' + 'mantuvo compostura' indica disimulo"
    ),
    EmotionalCoherenceTestCase(
        id="conc_03_mascara",
        category="disimulo",
        text='Bajo su máscara de calma, Ana sentía pánico. —Procedamos —dijo con voz firme.',
        entity_name="Ana",
        declared_emotion="pánico",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="'Máscara de calma' indica ocultamiento"
    ),
]

# =============================================================================
# CATEGORÍA 7: EMOCIONES MIXTAS
# =============================================================================

MIXED_EMOTION_TESTS = [
    EmotionalCoherenceTestCase(
        id="mixed_01_alegre_triste",
        category="emociones_mixtas",
        text='María sentía una mezcla de alegría y tristeza. Sonrió con lágrimas en los ojos.',
        entity_name="María",
        declared_emotion="alegría y tristeza",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Emociones mixtas justifican conducta mixta"
    ),
    EmotionalCoherenceTestCase(
        id="mixed_02_alivio_culpa",
        category="emociones_mixtas",
        text='Juan sentía alivio y culpa a partes iguales. No sabía si reír o llorar.',
        entity_name="Juan",
        declared_emotion="alivio y culpa",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Conflicto emocional interno"
    ),
]

# =============================================================================
# CATEGORÍA 8: CAMBIOS EMOCIONALES VÁLIDOS
# =============================================================================

VALID_CHANGE_TESTS = [
    EmotionalCoherenceTestCase(
        id="valid_ch_01_gradual",
        category="cambio_valido",
        text='María estaba preocupada. Tras escuchar las buenas noticias, su expresión se relajó y sonrió aliviada.',
        entity_name="María",
        declared_emotion="preocupada → aliviada",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Cambio gradual justificado por evento"
    ),
    EmotionalCoherenceTestCase(
        id="valid_ch_02_causa",
        category="cambio_valido",
        text='Juan estaba tranquilo. Cuando vio la serpiente, el pánico lo invadió.',
        entity_name="Juan",
        declared_emotion="tranquilo → pánico",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Cambio abrupto pero justificado por estímulo"
    ),
]

# =============================================================================
# CATEGORÍA 9: CAMBIOS EMOCIONALES ABRUPTOS (inválidos)
# =============================================================================

INVALID_CHANGE_TESTS = [
    EmotionalCoherenceTestCase(
        id="inv_ch_01_sin_causa",
        category="cambio_invalido",
        text='María estaba destrozada, llorando sin consuelo. De pronto estaba radiante de felicidad.',
        entity_name="María",
        declared_emotion="destrozada → feliz",
        should_be_incoherent=True,
        incoherence_type="temporal_jump",
        difficulty="medium",
        linguistic_note="Cambio extremo sin justificación"
    ),
    EmotionalCoherenceTestCase(
        id="inv_ch_02_instantaneo",
        category="cambio_invalido",
        text='Juan reía a carcajadas. Un segundo después estaba sumido en profunda depresión.',
        entity_name="Juan",
        declared_emotion="riendo → deprimido",
        should_be_incoherent=True,
        incoherence_type="temporal_jump",
        difficulty="medium",
        linguistic_note="Cambio instantáneo sin causa"
    ),
]

# =============================================================================
# CATEGORÍA 10: CONTEXTO CULTURAL
# =============================================================================

CULTURAL_TESTS = [
    EmotionalCoherenceTestCase(
        id="cult_01_estoico",
        category="cultural",
        text='El samurái estaba devastado por la muerte de su señor. Mantuvo el rostro impasible.',
        entity_name="El samurái",
        declared_emotion="devastado",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Contexto cultural justifica contención emocional"
    ),
    EmotionalCoherenceTestCase(
        id="cult_02_protocolo",
        category="cultural",
        text='La reina estaba furiosa. Sonrió con cortesía durante toda la ceremonia.',
        entity_name="La reina",
        declared_emotion="furiosa",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Protocolo social justifica disimulo"
    ),
]

# =============================================================================
# CATEGORÍA 11: GÉNERO LITERARIO
# =============================================================================

GENRE_TESTS = [
    EmotionalCoherenceTestCase(
        id="genre_01_comedia",
        category="genero",
        text='María estaba desesperada. Tropezó con la alfombra y cayó sobre el pastel de bodas.',
        entity_name="María",
        declared_emotion="desesperada",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="En comedia, la acción cómica no invalida la emoción"
    ),
    EmotionalCoherenceTestCase(
        id="genre_02_melodrama",
        category="genero",
        text='Juan sintió que su corazón se hacía añicos en mil pedazos de cristal roto.',
        entity_name="Juan",
        declared_emotion="destrozado",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Melodrama permite expresiones hiperbólicas"
    ),
]

# =============================================================================
# CATEGORÍA 12: ESTADOS AMBIGUOS
# =============================================================================

AMBIGUOUS_TESTS = [
    EmotionalCoherenceTestCase(
        id="ambig_01_confuso",
        category="ambiguo",
        text='María no sabía qué sentir. Alternaba entre risas y sollozos.',
        entity_name="María",
        declared_emotion="confusión emocional",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Confusión emocional justifica conducta errática"
    ),
    EmotionalCoherenceTestCase(
        id="ambig_02_shock",
        category="ambiguo",
        text='Juan estaba en shock. Su rostro no mostraba ninguna expresión.',
        entity_name="Juan",
        declared_emotion="shock",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Shock puede producir inexpresividad"
    ),
]

# =============================================================================
# CATEGORÍA 13: NARRADOR VS PERSONAJE
# =============================================================================

NARRATOR_VS_CHARACTER_TESTS = [
    EmotionalCoherenceTestCase(
        id="narr_01_omnisciente",
        category="narrador_personaje",
        text='María sonreía, pero el narrador sabía que por dentro lloraba.',
        entity_name="María",
        declared_emotion="tristeza interna",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Narrador omnisciente revela emoción oculta"
    ),
    EmotionalCoherenceTestCase(
        id="narr_02_interpretacion",
        category="narrador_personaje",
        text='Juan parecía tranquilo, aunque cualquiera podía ver la tensión en sus hombros.',
        entity_name="Juan",
        declared_emotion="tenso",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Apariencia vs realidad indicada"
    ),
]

# =============================================================================
# CATEGORÍA 14: EMOCIONES GRADUALES
# =============================================================================

GRADUAL_TESTS = [
    EmotionalCoherenceTestCase(
        id="grad_01_creciente",
        category="gradual",
        text='La irritación de María fue creciendo. Primero frunció el ceño, luego apretó los puños, y finalmente explotó.',
        entity_name="María",
        declared_emotion="irritación creciente",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Escalada emocional gradual"
    ),
    EmotionalCoherenceTestCase(
        id="grad_02_decreciente",
        category="gradual",
        text='El enfado de Juan se fue disipando. Su respiración se calmó y sus hombros se relajaron.',
        entity_name="Juan",
        declared_emotion="enfado decreciente",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Desescalada emocional"
    ),
]

# =============================================================================
# CATEGORÍA 15: CATARSIS EMOCIONAL
# =============================================================================

CATHARSIS_TESTS = [
    EmotionalCoherenceTestCase(
        id="cath_01_llanto",
        category="catarsis",
        text='María finalmente lloró. Después del llanto, se sintió más ligera.',
        entity_name="María",
        declared_emotion="triste → aliviada",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Catarsis produce cambio emocional válido"
    ),
    EmotionalCoherenceTestCase(
        id="cath_02_grito",
        category="catarsis",
        text='Juan gritó toda su frustración. Agotado pero liberado, se dejó caer en la silla.',
        entity_name="Juan",
        declared_emotion="frustración → liberación",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Liberación emocional tras descarga"
    ),
]

# =============================================================================
# CATEGORÍA 16: SHOCK Y TRAUMA
# =============================================================================

SHOCK_TESTS = [
    EmotionalCoherenceTestCase(
        id="shock_01_paralisis",
        category="shock",
        text='María acababa de recibir la terrible noticia. Permaneció inmóvil, sin reaccionar.',
        entity_name="María",
        declared_emotion="shock",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Shock produce parálisis emocional"
    ),
    EmotionalCoherenceTestCase(
        id="shock_02_risa_histerica",
        category="shock",
        text='Juan, tras el accidente, comenzó a reír histéricamente.',
        entity_name="Juan",
        declared_emotion="shock traumático",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Risa histérica como respuesta al trauma"
    ),
]

# =============================================================================
# CATEGORÍA 17: HUMOR NEGRO
# =============================================================================

DARK_HUMOR_TESTS = [
    EmotionalCoherenceTestCase(
        id="dark_01_funeral",
        category="humor_negro",
        text='María estaba destrozada en el funeral. —Al menos ya no ronca —murmuró intentando una sonrisa.',
        entity_name="María",
        declared_emotion="destrozada",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Humor negro como mecanismo de defensa"
    ),
]

# =============================================================================
# CATEGORÍA 18: EMOCIONES COMPLEJAS
# =============================================================================

COMPLEX_EMOTION_TESTS = [
    EmotionalCoherenceTestCase(
        id="complex_01_nostalgia",
        category="emociones_complejas",
        text='María sentía nostalgia. Sonreía mientras las lágrimas rodaban por su mejilla.',
        entity_name="María",
        declared_emotion="nostalgia",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Nostalgia mezcla alegría del recuerdo y tristeza de la pérdida"
    ),
    EmotionalCoherenceTestCase(
        id="complex_02_orgullo_herido",
        category="emociones_complejas",
        text='Juan tenía el orgullo herido. Se negó a pedir ayuda aunque la necesitaba.',
        entity_name="Juan",
        declared_emotion="orgullo herido",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Orgullo herido produce conducta de rechazo"
    ),
]

# =============================================================================
# CATEGORÍA 19: NEGACIÓN EMOCIONAL
# =============================================================================

DENIAL_TESTS = [
    EmotionalCoherenceTestCase(
        id="denial_01_explicita",
        category="negacion",
        text='María estaba claramente asustada. —No tengo miedo —insistió con voz temblorosa.',
        entity_name="María",
        declared_emotion="asustada",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Negación verbal mientras el cuerpo revela la verdad"
    ),
    EmotionalCoherenceTestCase(
        id="denial_02_autoengano",
        category="negacion",
        text='Juan estaba destrozado, pero se repetía que estaba bien. —Estoy bien —se mentía.',
        entity_name="Juan",
        declared_emotion="destrozado",
        should_be_incoherent=False,
        difficulty="hard",
        linguistic_note="Autoengaño explícito ('se mentía')"
    ),
]

# =============================================================================
# CATEGORÍA 20: EXPRESIONES IDIOMÁTICAS
# =============================================================================

IDIOM_TESTS = [
    EmotionalCoherenceTestCase(
        id="idiom_01_subir_pared",
        category="expresiones",
        text='María estaba que se subía por las paredes de la rabia.',
        entity_name="María",
        declared_emotion="rabia",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Expresión idiomática de enfado extremo"
    ),
    EmotionalCoherenceTestCase(
        id="idiom_02_corazon_puño",
        category="expresiones",
        text='Juan tenía el corazón en un puño esperando los resultados.',
        entity_name="Juan",
        declared_emotion="ansiedad",
        should_be_incoherent=False,
        difficulty="medium",
        linguistic_note="Expresión idiomática de ansiedad"
    ),
]


# =============================================================================
# FIXTURE Y TEST RUNNER
# =============================================================================

ALL_EMOTIONAL_COHERENCE_TESTS = (
    COHERENT_DIALOGUE_TESTS +
    INCOHERENT_DIALOGUE_TESTS +
    COHERENT_ACTION_TESTS +
    INCOHERENT_ACTION_TESTS +
    IRONY_TESTS +
    CONCEALMENT_TESTS +
    MIXED_EMOTION_TESTS +
    VALID_CHANGE_TESTS +
    INVALID_CHANGE_TESTS +
    CULTURAL_TESTS +
    GENRE_TESTS +
    AMBIGUOUS_TESTS +
    NARRATOR_VS_CHARACTER_TESTS +
    GRADUAL_TESTS +
    CATHARSIS_TESTS +
    SHOCK_TESTS +
    DARK_HUMOR_TESTS +
    COMPLEX_EMOTION_TESTS +
    DENIAL_TESTS +
    IDIOM_TESTS
)


class TestEmotionalCoherenceAdversarial:
    """Tests adversariales para coherencia emocional."""

    @pytest.fixture
    def analyzer(self):
        """Crea instancia del analizador de coherencia emocional."""
        from narrative_assistant.analysis.emotional_coherence import EmotionalCoherenceAnalyzer
        return EmotionalCoherenceAnalyzer()

    @pytest.mark.parametrize("test_case", ALL_EMOTIONAL_COHERENCE_TESTS, ids=lambda tc: tc.id)
    def test_emotional_coherence_case(self, analyzer, test_case: EmotionalCoherenceTestCase):
        """Ejecuta un caso de test de coherencia emocional."""
        # Analizar el texto
        incoherences = analyzer.analyze_text(
            test_case.text,
            entity_name=test_case.entity_name
        )

        has_incoherence = len(incoherences) > 0

        if test_case.should_be_incoherent:
            assert has_incoherence, (
                f"[{test_case.id}] Se esperaba incoherencia pero no se detectó.\n"
                f"Texto: {test_case.text}\n"
                f"Emoción: {test_case.declared_emotion}\n"
                f"Nota: {test_case.linguistic_note}"
            )
        else:
            assert not has_incoherence, (
                f"[{test_case.id}] Se detectó incoherencia pero no debería.\n"
                f"Texto: {test_case.text}\n"
                f"Emoción: {test_case.declared_emotion}\n"
                f"Incoherencias: {[i.explanation for i in incoherences]}\n"
                f"Nota: {test_case.linguistic_note}"
            )


class TestEmotionalCoherenceByCategory:
    """Tests organizados por categoría."""

    @pytest.fixture
    def analyzer(self):
        from narrative_assistant.analysis.emotional_coherence import EmotionalCoherenceAnalyzer
        return EmotionalCoherenceAnalyzer()

    @pytest.mark.parametrize("test_case", INCOHERENT_DIALOGUE_TESTS, ids=lambda tc: tc.id)
    def test_incoherent_dialogue(self, analyzer, test_case):
        """Tests de diálogo incoherente."""
        incoherences = analyzer.analyze_text(test_case.text, test_case.entity_name)
        assert len(incoherences) > 0, f"[{test_case.id}] Debería detectar incoherencia"

    @pytest.mark.parametrize("test_case", IRONY_TESTS, ids=lambda tc: tc.id)
    def test_irony(self, analyzer, test_case):
        """Tests de ironía (no debe alertar)."""
        incoherences = analyzer.analyze_text(test_case.text, test_case.entity_name)
        assert len(incoherences) == 0, f"[{test_case.id}] No debería alertar por ironía"

    @pytest.mark.parametrize("test_case", CONCEALMENT_TESTS, ids=lambda tc: tc.id)
    def test_concealment(self, analyzer, test_case):
        """Tests de disimulo (no debe alertar)."""
        incoherences = analyzer.analyze_text(test_case.text, test_case.entity_name)
        assert len(incoherences) == 0, f"[{test_case.id}] No debería alertar por disimulo"


def get_test_summary():
    """Genera resumen de los tests por categoría."""
    from collections import Counter

    categories = Counter(tc.category for tc in ALL_EMOTIONAL_COHERENCE_TESTS)
    difficulties = Counter(tc.difficulty for tc in ALL_EMOTIONAL_COHERENCE_TESTS)
    should_detect = sum(1 for tc in ALL_EMOTIONAL_COHERENCE_TESTS if tc.should_be_incoherent)
    should_not = len(ALL_EMOTIONAL_COHERENCE_TESTS) - should_detect

    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS ADVERSARIALES DE COHERENCIA EMOCIONAL")
    print("=" * 60)
    print(f"\nTotal de casos: {len(ALL_EMOTIONAL_COHERENCE_TESTS)}")
    print(f"  - Deben detectar incoherencia: {should_detect}")
    print(f"  - NO deben detectar: {should_not}")
    print(f"\nPor categoría:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print(f"\nPor dificultad:")
    for diff, count in sorted(difficulties.items()):
        print(f"  {diff}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    get_test_summary()
    pytest.main([__file__, "-v", "--tb=short"])
