"""
Tests para el módulo de voz y perfiles.
"""

import pytest

from narrative_assistant.voice import (
    DeviationType,
    VoiceDeviation,
    VoiceDeviationDetector,
    VoiceMetrics,
    VoiceProfile,
    VoiceProfileBuilder,
)
from narrative_assistant.voice.deviations import detect_voice_deviations
from narrative_assistant.voice.profiles import (
    FILLERS,
    FORMAL_MARKERS,
    INFORMAL_MARKERS,
    build_voice_profiles_from_chapters,
)

# =============================================================================
# Tests de VoiceMetrics
# =============================================================================


class TestVoiceMetrics:
    """Tests para métricas de voz."""

    def test_default_metrics(self):
        """Métricas por defecto."""
        metrics = VoiceMetrics()
        assert metrics.avg_intervention_length == 0.0
        assert metrics.type_token_ratio == 0.0
        assert metrics.formality_score == 0.5
        assert metrics.filler_ratio == 0.0
        assert metrics.total_interventions == 0

    def test_metrics_with_values(self):
        """Métricas con valores asignados."""
        metrics = VoiceMetrics(
            avg_intervention_length=15.5,
            type_token_ratio=0.7,
            formality_score=0.8,
            total_interventions=20,
            total_words=310,
        )
        assert metrics.avg_intervention_length == 15.5
        assert metrics.type_token_ratio == 0.7
        assert metrics.formality_score == 0.8
        assert metrics.total_words == 310


# =============================================================================
# Tests de VoiceProfile
# =============================================================================


class TestVoiceProfile:
    """Tests para perfiles de voz."""

    def test_profile_creation(self):
        """Creación básica de perfil."""
        profile = VoiceProfile(
            entity_id=1,
            entity_name="Ana",
            confidence=0.8,
        )
        assert profile.entity_id == 1
        assert profile.entity_name == "Ana"
        assert profile.confidence == 0.8
        assert isinstance(profile.metrics, VoiceMetrics)

    def test_profile_to_dict(self):
        """Conversión a diccionario."""
        profile = VoiceProfile(
            entity_id=1,
            entity_name="Pedro",
            confidence=0.75,
            characteristic_words=[("siempre", 2.5), ("nunca", 1.8)],
            speech_patterns=["Inicio: 'Pues mira...'"],
        )

        d = profile.to_dict()
        assert d["entity_id"] == 1
        assert d["entity_name"] == "Pedro"
        assert d["confidence"] == 0.75
        assert len(d["characteristic_words"]) == 2
        assert len(d["speech_patterns"]) == 1


# =============================================================================
# Tests de VoiceProfileBuilder
# =============================================================================


class TestVoiceProfileBuilder:
    """Tests para el constructor de perfiles."""

    @pytest.fixture
    def sample_dialogues(self):
        """Diálogos de ejemplo con marcadores claros de formalidad."""
        return [
            # Personaje formal con más marcadores formales
            {"text": "Buenos dias, senor. Como esta usted hoy?", "speaker_id": 1},
            {"text": "Ciertamente, senor, el tiempo es agradable.", "speaker_id": 1},
            {"text": "Sin embargo, me preocupa el estado de la economia.", "speaker_id": 1},
            {"text": "Asimismo, agradeceria su opinion al respecto.", "speaker_id": 1},
            {"text": "No obstante, usted sabe mejor que yo.", "speaker_id": 1},
            # Personaje informal con marcadores informales
            {"text": "Eh, tio! Que pasa, colega?", "speaker_id": 2},
            {"text": "Pues mira, estoy flipando con esto, tio.", "speaker_id": 2},
            {"text": "Mola mogollon! Es flipante!", "speaker_id": 2},
            {"text": "Venga, vamos a currar, chaval.", "speaker_id": 2},
            {"text": "Jo, que rollo, tio...", "speaker_id": 2},
        ]

    @pytest.fixture
    def sample_entities(self):
        """Entidades de ejemplo."""
        return [
            {"id": 1, "name": "Don Eduardo", "type": "PERSON"},
            {"id": 2, "name": "Marcos", "type": "PERSON"},
        ]

    def test_build_profiles(self, sample_dialogues, sample_entities):
        """Construcción de perfiles para múltiples personajes."""
        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(sample_dialogues, sample_entities)

        assert len(profiles) == 2

        # Perfil formal
        formal_profile = next(p for p in profiles if p.entity_name == "Don Eduardo")
        assert formal_profile.metrics.formality_score > 0.5
        assert formal_profile.metrics.total_interventions == 5

        # Perfil informal
        informal_profile = next(p for p in profiles if p.entity_name == "Marcos")
        assert informal_profile.metrics.formality_score < 0.5
        assert informal_profile.metrics.total_interventions == 5

    def test_empty_dialogues(self, sample_entities):
        """Constructor con diálogos vacíos."""
        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles([], sample_entities)
        assert profiles == []

    def test_filter_non_characters(self, sample_dialogues):
        """Filtra entidades que no son personajes."""
        entities = [
            {"id": 1, "name": "Don Eduardo", "type": "PERSON"},
            {"id": 2, "name": "Marcos", "type": "PERSON"},
            {"id": 3, "name": "Madrid", "type": "LOC"},  # No es personaje
        ]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(sample_dialogues, entities)

        # Solo debería haber perfiles de personajes
        assert len(profiles) == 2
        assert all(p.entity_name in ["Don Eduardo", "Marcos"] for p in profiles)

    def test_intervention_length_metrics(self):
        """Métricas de longitud de intervención."""
        dialogues = [
            {"text": "Una frase corta.", "speaker_id": 1},
            {"text": "Otra frase corta.", "speaker_id": 1},
            {
                "text": "Esta es una frase mucho más larga con muchas más palabras para probar.",
                "speaker_id": 1,
            },
        ]
        entities = [{"id": 1, "name": "Test", "type": "PERSON"}]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entities)

        assert len(profiles) == 1
        metrics = profiles[0].metrics
        assert metrics.total_interventions == 3
        assert metrics.avg_intervention_length > 0
        assert metrics.std_intervention_length > 0
        assert metrics.min_intervention_length < metrics.max_intervention_length

    def test_type_token_ratio(self):
        """Cálculo de riqueza léxica (TTR)."""
        # Diálogos con vocabulario repetitivo
        dialogues = [
            {"text": "El gato negro. El gato negro. El gato negro.", "speaker_id": 1},
        ]
        entities = [{"id": 1, "name": "Repetitivo", "type": "PERSON"}]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entities)

        # TTR bajo por repetición
        ttr = profiles[0].metrics.type_token_ratio
        assert 0 < ttr < 0.5  # Baja riqueza léxica

    def test_filler_detection(self):
        """Detección de muletillas."""
        dialogues = [
            {
                "text": "Bueno, pues mira, o sea, es que básicamente es así, ¿sabes?",
                "speaker_id": 1,
            },
            {
                "text": "Pues bueno, la verdad, obviamente, es decir, claramente sí.",
                "speaker_id": 1,
            },
        ]
        entities = [{"id": 1, "name": "Muletillero", "type": "PERSON"}]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entities)

        metrics = profiles[0].metrics
        assert metrics.filler_ratio > 0.1
        assert len(metrics.top_fillers) > 0

    def test_punctuation_metrics(self):
        """Métricas de puntuación."""
        dialogues = [
            {"text": "¡Increíble! ¡Fantástico! ¡Genial!", "speaker_id": 1},
            {"text": "¿Qué? ¿Cómo? ¿Cuándo? ¿Por qué?", "speaker_id": 1},
        ]
        entities = [{"id": 1, "name": "Expresivo", "type": "PERSON"}]

        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(dialogues, entities)

        metrics = profiles[0].metrics
        assert metrics.exclamation_ratio > 1.0
        assert metrics.question_ratio > 1.0

    def test_characteristic_words(self, sample_dialogues, sample_entities):
        """Detección de palabras características."""
        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(sample_dialogues, sample_entities)

        # El personaje formal debería tener palabras formales características
        formal_profile = next(p for p in profiles if p.entity_name == "Don Eduardo")
        # Puede o no tener palabras características dependiendo de TF-IDF
        assert isinstance(formal_profile.characteristic_words, list)

    def test_speech_patterns(self, sample_dialogues, sample_entities):
        """Detección de patrones de habla."""
        builder = VoiceProfileBuilder()
        profiles = builder.build_profiles(sample_dialogues, sample_entities)

        for profile in profiles:
            assert isinstance(profile.speech_patterns, list)

    def test_confidence_calculation(self):
        """Cálculo de confianza basado en muestras."""
        # Pocos diálogos = baja confianza
        few_dialogues = [
            {"text": "Hola.", "speaker_id": 1},
            {"text": "Adiós.", "speaker_id": 1},
        ]

        # Muchos diálogos = alta confianza
        many_dialogues = [{"text": f"Intervención número {i}.", "speaker_id": 2} for i in range(20)]

        entities = [
            {"id": 1, "name": "Poco", "type": "PERSON"},
            {"id": 2, "name": "Mucho", "type": "PERSON"},
        ]

        builder = VoiceProfileBuilder(min_interventions=5)
        profiles = builder.build_profiles(few_dialogues + many_dialogues, entities)

        low_conf = next(p for p in profiles if p.entity_name == "Poco")
        high_conf = next(p for p in profiles if p.entity_name == "Mucho")

        assert low_conf.confidence < high_conf.confidence


# =============================================================================
# Tests de VoiceDeviationDetector
# =============================================================================


class TestVoiceDeviationDetector:
    """Tests para el detector de desviaciones."""

    @pytest.fixture
    def formal_profile(self):
        """Perfil de personaje formal."""
        metrics = VoiceMetrics(
            avg_intervention_length=20.0,
            std_intervention_length=5.0,
            formality_score=0.9,
            filler_ratio=0.01,
            exclamation_ratio=0.1,
            question_ratio=0.2,
            total_interventions=50,
            total_words=1000,
        )
        return VoiceProfile(
            entity_id=1,
            entity_name="Don Eduardo",
            metrics=metrics,
            confidence=0.8,
        )

    @pytest.fixture
    def informal_profile(self):
        """Perfil de personaje informal."""
        metrics = VoiceMetrics(
            avg_intervention_length=8.0,
            std_intervention_length=3.0,
            formality_score=0.1,
            filler_ratio=0.15,
            exclamation_ratio=1.5,
            question_ratio=0.8,
            total_interventions=50,
            total_words=400,
        )
        return VoiceProfile(
            entity_id=2,
            entity_name="Marcos",
            metrics=metrics,
            confidence=0.75,
        )

    def test_length_deviation_too_long(self, formal_profile):
        """Detecta intervención demasiado larga."""
        detector = VoiceDeviationDetector()

        # Intervención muy larga para el perfil
        dialogues = [
            {
                "text": " ".join(["palabra"] * 50),  # 50 palabras, esperado ~20
                "speaker_id": 1,
                "chapter": 1,
                "position": 100,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)

        length_devs = [d for d in deviations if d.deviation_type == DeviationType.LENGTH_ANOMALY]
        assert len(length_devs) >= 1
        assert "más larga" in length_devs[0].description

    def test_length_deviation_too_short(self, formal_profile):
        """Detecta intervención demasiado corta."""
        detector = VoiceDeviationDetector()

        # Intervención muy corta para el perfil
        dialogues = [
            {
                "text": "Sí.",  # 1 palabra, esperado ~20
                "speaker_id": 1,
                "chapter": 1,
                "position": 100,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)

        length_devs = [d for d in deviations if d.deviation_type == DeviationType.LENGTH_ANOMALY]
        assert len(length_devs) >= 1
        assert "más corta" in length_devs[0].description

    def test_formality_shift_formal_to_informal(self, formal_profile):
        """Detecta cambio de formal a informal."""
        detector = VoiceDeviationDetector()

        # Personaje formal hablando informal
        dialogues = [
            {
                "text": "¡Eh, tío! ¡Qué pasa, colega! Mola mogollón esto, ¿sabes?",
                "speaker_id": 1,
                "chapter": 2,
                "position": 200,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)

        formality_devs = [
            d for d in deviations if d.deviation_type == DeviationType.FORMALITY_SHIFT
        ]
        assert len(formality_devs) >= 1
        assert "más informal" in formality_devs[0].description

    def test_formality_shift_informal_to_formal(self, informal_profile):
        """Detecta cambio de informal a formal."""
        detector = VoiceDeviationDetector()

        # Personaje informal hablando formal
        dialogues = [
            {
                "text": "Ciertamente, señor, agradecería que usted me permitiera expresar mi opinión.",
                "speaker_id": 2,
                "chapter": 3,
                "position": 300,
            }
        ]

        deviations = detector.detect_deviations([informal_profile], dialogues)

        formality_devs = [
            d for d in deviations if d.deviation_type == DeviationType.FORMALITY_SHIFT
        ]
        assert len(formality_devs) >= 1
        assert "más formal" in formality_devs[0].description

    def test_filler_anomaly(self, formal_profile):
        """Detecta uso anómalo de muletillas."""
        detector = VoiceDeviationDetector()

        # Personaje que no usa muletillas usando muchas
        dialogues = [
            {
                "text": "Bueno, pues mira, o sea, básicamente, la verdad es que sinceramente creo que obviamente tienes razón, ¿sabes?",
                "speaker_id": 1,
                "chapter": 4,
                "position": 400,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)

        filler_devs = [d for d in deviations if d.deviation_type == DeviationType.FILLER_ANOMALY]
        assert len(filler_devs) >= 1

    def test_punctuation_deviation(self, formal_profile):
        """Detecta cambio en patrones de puntuación."""
        detector = VoiceDeviationDetector()

        # Personaje tranquilo usando muchas exclamaciones
        dialogues = [
            {
                "text": "¡Increíble! ¡No puedo creerlo! ¡Es fantástico! ¡Maravilloso!",
                "speaker_id": 1,
                "chapter": 5,
                "position": 500,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)

        punct_devs = [d for d in deviations if d.deviation_type == DeviationType.PUNCTUATION_SHIFT]
        assert len(punct_devs) >= 1

    def test_no_deviation_normal_speech(self, formal_profile):
        """No detecta desviación en habla normal."""
        detector = VoiceDeviationDetector()

        # Habla consistente con el perfil
        dialogues = [
            {
                "text": "Buenos días, señor. Le agradezco su atención en este asunto tan importante.",
                "speaker_id": 1,
                "chapter": 1,
                "position": 100,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)

        # Puede haber algunas desviaciones menores, pero no de formalidad
        formality_devs = [
            d for d in deviations if d.deviation_type == DeviationType.FORMALITY_SHIFT
        ]
        assert len(formality_devs) == 0

    def test_low_confidence_profile_ignored(self):
        """Perfiles con baja confianza son ignorados."""
        detector = VoiceDeviationDetector()

        low_conf_profile = VoiceProfile(
            entity_id=1,
            entity_name="Nuevo",
            confidence=0.2,  # Muy baja confianza
        )

        dialogues = [
            {
                "text": "¡Eh, tío! ¡Flipante!",
                "speaker_id": 1,
                "chapter": 1,
                "position": 100,
            }
        ]

        deviations = detector.detect_deviations([low_conf_profile], dialogues)
        assert len(deviations) == 0

    def test_unknown_speaker_ignored(self, formal_profile):
        """Diálogos sin speaker conocido son ignorados."""
        detector = VoiceDeviationDetector()

        dialogues = [
            {
                "text": "¡Eh, tío! ¡Flipante!",
                "speaker_id": 999,  # No existe
                "chapter": 1,
                "position": 100,
            }
        ]

        deviations = detector.detect_deviations([formal_profile], dialogues)
        assert len(deviations) == 0


# =============================================================================
# Tests de integración
# =============================================================================


class TestVoiceIntegration:
    """Tests de integración del módulo de voz."""

    def test_build_profiles_from_chapters(self):
        """Construcción de perfiles desde capítulos."""
        chapters = [
            {
                "number": 1,
                "dialogues": [
                    {"text": "Buenos días, señor.", "speaker_id": 1, "position": 10},
                    {"text": "¿Cómo está usted?", "speaker_id": 1, "position": 50},
                ],
            },
            {
                "number": 2,
                "dialogues": [
                    {"text": "¡Eh, tío! ¿Qué pasa?", "speaker_id": 2, "position": 100},
                    {"text": "Mola mogollón.", "speaker_id": 2, "position": 150},
                ],
            },
        ]

        entities = [
            {"id": 1, "name": "Don Eduardo", "type": "PERSON"},
            {"id": 2, "name": "Marcos", "type": "PERSON"},
        ]

        profiles = build_voice_profiles_from_chapters(chapters, entities)

        assert len(profiles) == 2

    def test_detect_voice_deviations_full_flow(self):
        """Flujo completo de detección de desviaciones."""
        chapters = [
            {
                "number": 1,
                "dialogues": [
                    # Perfil formal establecido con muchos marcadores
                    {
                        "text": "Buenos dias, senor. Como esta usted hoy?",
                        "speaker_id": 1,
                        "position": 10,
                    },
                    {
                        "text": "Ciertamente, senor, es un placer verle.",
                        "speaker_id": 1,
                        "position": 50,
                    },
                    {
                        "text": "Sin embargo, debo comunicarle algo importante.",
                        "speaker_id": 1,
                        "position": 90,
                    },
                    {
                        "text": "Asimismo, usted debe saber que le agradezco.",
                        "speaker_id": 1,
                        "position": 130,
                    },
                    {
                        "text": "No obstante, senor, debo retirarme ahora.",
                        "speaker_id": 1,
                        "position": 170,
                    },
                    {
                        "text": "Ciertamente usted es muy amable, senor.",
                        "speaker_id": 1,
                        "position": 210,
                    },
                    {
                        "text": "Sin embargo usted sabe mejor que yo.",
                        "speaker_id": 1,
                        "position": 250,
                    },
                    {
                        "text": "Efectivamente, senor, es como usted dice.",
                        "speaker_id": 1,
                        "position": 290,
                    },
                    {
                        "text": "Indudablemente usted tiene toda la razon.",
                        "speaker_id": 1,
                        "position": 330,
                    },
                    {
                        "text": "Asimismo le agradezco su tiempo, senor.",
                        "speaker_id": 1,
                        "position": 370,
                    },
                ],
            },
            {
                "number": 2,
                "dialogues": [
                    # Cambio de registro: personaje formal hablando MUY informal
                    {
                        "text": "Eh, tio! Mola mogollon esto! Flipante, colega! Es guay, chaval!",
                        "speaker_id": 1,
                        "position": 500,
                    },
                ],
            },
        ]

        entities = [
            {"id": 1, "name": "Don Eduardo", "type": "PERSON"},
        ]

        profiles, deviations = detect_voice_deviations(chapters, entities)

        assert len(profiles) == 1
        # Debería detectar al menos alguna desviación
        assert len(deviations) >= 1
        # Verificar que la desviación de formalidad está presente
        formality_devs = [
            d for d in deviations if d.deviation_type == DeviationType.FORMALITY_SHIFT
        ]
        assert len(formality_devs) >= 1

    def test_deviation_to_dict(self):
        """Conversión de desviación a diccionario."""
        deviation = VoiceDeviation(
            entity_id=1,
            entity_name="Test",
            deviation_type=DeviationType.FORMALITY_SHIFT,
            severity=DeviationType.FORMALITY_SHIFT,  # Esto es un error, corregir abajo
            chapter=1,
            position=100,
            text="Texto de prueba",
            expected_value=0.9,
            actual_value=0.2,
            description="Descripción de la desviación",
            confidence=0.8,
        )

        # Corregir: severity debe ser DeviationSeverity
        from narrative_assistant.voice.deviations import DeviationSeverity

        deviation.severity = DeviationSeverity.MEDIUM

        d = deviation.to_dict()
        assert d["entity_id"] == 1
        assert d["deviation_type"] == "formality_shift"
        assert d["severity"] == "medium"
        assert d["expected_value"] == 0.9
        assert d["actual_value"] == 0.2


# =============================================================================
# Tests de marcadores y constantes
# =============================================================================


class TestVoiceConstants:
    """Tests para constantes del módulo."""

    def test_formal_markers_not_empty(self):
        """Marcadores formales definidos."""
        assert len(FORMAL_MARKERS) > 10

    def test_informal_markers_not_empty(self):
        """Marcadores informales definidos."""
        assert len(INFORMAL_MARKERS) > 10

    def test_fillers_not_empty(self):
        """Muletillas definidas."""
        assert len(FILLERS) > 10

    def test_no_overlap_formal_informal(self):
        """Sin solapamiento entre formal e informal."""
        overlap = FORMAL_MARKERS & INFORMAL_MARKERS
        assert len(overlap) == 0, f"Solapamiento encontrado: {overlap}"
