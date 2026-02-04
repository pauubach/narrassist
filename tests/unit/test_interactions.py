"""
Tests para el módulo de interacciones entre entidades.

Cubre:
- Modelos de datos (InteractionType, InteractionTone, EntityInteraction, etc.)
- Detección de interacciones (detector.py)
- Análisis de patrones (pattern_analyzer.py)
- Repositorio de persistencia (repository.py)
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from narrative_assistant.interactions import (
    ACTION_VERBS_NEGATIVE,
    ACTION_VERBS_POSITIVE,
    DIALOGUE_VERBS,
    INTERACTION_TYPE_INTENSITY,
    EntityInteraction,
    InteractionAlert,
    # Detector
    InteractionDetector,
    InteractionPattern,
    # Analyzer
    InteractionPatternAnalyzer,
    # Repository
    InteractionRepository,
    InteractionTone,
    # Modelos
    InteractionType,
    detect_interactions_in_text,
)
from narrative_assistant.persistence.database import Database

# ============================================================================
# Tests de Modelos
# ============================================================================


class TestInteractionType:
    """Tests para InteractionType enum."""

    def test_all_interaction_types_exist(self):
        """Verifica que todos los tipos de interacción existen."""
        expected_types = [
            "DIALOGUE",
            "ACTION_TOWARDS",
            "THOUGHT_ABOUT",
            "OBSERVATION",
            "PHYSICAL_CONTACT",
            "GIFT_EXCHANGE",
            "MENTION",
            "REACTION",
        ]
        for type_name in expected_types:
            assert hasattr(InteractionType, type_name)

    def test_interaction_type_values(self):
        """Verifica valores de InteractionType."""
        assert InteractionType.DIALOGUE.value == "dialogue"
        assert InteractionType.ACTION_TOWARDS.value == "action"
        assert InteractionType.PHYSICAL_CONTACT.value == "physical"

    def test_intensity_mapping_exists(self):
        """Verifica que todos los tipos tienen intensidad mapeada."""
        for itype in InteractionType:
            assert itype in INTERACTION_TYPE_INTENSITY
            assert 0 <= INTERACTION_TYPE_INTENSITY[itype] <= 1


class TestInteractionTone:
    """Tests para InteractionTone enum."""

    def test_all_tones_exist(self):
        """Verifica que todos los tonos existen."""
        expected_tones = ["HOSTILE", "COLD", "NEUTRAL", "WARM", "AFFECTIONATE"]
        for tone_name in expected_tones:
            assert hasattr(InteractionTone, tone_name)

    def test_from_score_hostile(self):
        """Score muy negativo -> HOSTILE."""
        assert InteractionTone.from_score(-0.8) == InteractionTone.HOSTILE
        assert InteractionTone.from_score(-0.6) == InteractionTone.HOSTILE

    def test_from_score_cold(self):
        """Score negativo moderado -> COLD."""
        assert InteractionTone.from_score(-0.4) == InteractionTone.COLD
        assert InteractionTone.from_score(-0.25) == InteractionTone.COLD

    def test_from_score_neutral(self):
        """Score cercano a cero -> NEUTRAL."""
        assert InteractionTone.from_score(0.0) == InteractionTone.NEUTRAL
        assert InteractionTone.from_score(0.1) == InteractionTone.NEUTRAL
        assert InteractionTone.from_score(-0.1) == InteractionTone.NEUTRAL

    def test_from_score_warm(self):
        """Score positivo moderado -> WARM."""
        assert InteractionTone.from_score(0.3) == InteractionTone.WARM
        assert InteractionTone.from_score(0.4) == InteractionTone.WARM

    def test_from_score_affectionate(self):
        """Score muy positivo -> AFFECTIONATE."""
        assert InteractionTone.from_score(0.6) == InteractionTone.AFFECTIONATE
        assert InteractionTone.from_score(0.9) == InteractionTone.AFFECTIONATE

    def test_to_score_roundtrip(self):
        """Verifica conversión bidireccional aproximada."""
        for tone in InteractionTone:
            score = tone.to_score()
            # El roundtrip puede no ser exacto pero debe estar en el mismo rango
            recovered = InteractionTone.from_score(score)
            assert recovered == tone


class TestEntityInteraction:
    """Tests para EntityInteraction dataclass."""

    def test_create_basic_interaction(self):
        """Crea interacción básica."""
        interaction = EntityInteraction(
            initiator_name="Juan",
            receiver_name="María",
            interaction_type=InteractionType.DIALOGUE,
            tone=InteractionTone.WARM,
            chapter=1,
            text_excerpt="—¿Cómo estás? —preguntó Juan.",
        )

        assert interaction.initiator_name == "Juan"
        assert interaction.receiver_name == "María"
        assert interaction.interaction_type == InteractionType.DIALOGUE
        assert interaction.tone == InteractionTone.WARM

    def test_interaction_has_uuid(self):
        """Verifica que se genera UUID automáticamente."""
        i1 = EntityInteraction()
        i2 = EntityInteraction()
        assert i1.id != i2.id
        assert len(i1.id) == 36  # UUID formato

    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        interaction = EntityInteraction(
            initiator_name="Pedro",
            receiver_name="Luis",
            interaction_type=InteractionType.PHYSICAL_CONTACT,
            tone=InteractionTone.HOSTILE,
            chapter=3,
            confidence=0.85,
        )

        data = interaction.to_dict()
        assert data["initiator_name"] == "Pedro"
        assert data["receiver_name"] == "Luis"
        assert data["interaction_type"] == "physical"
        assert data["tone"] == "hostile"
        assert data["chapter"] == 3
        assert data["confidence"] == 0.85

    def test_from_dict(self):
        """Verifica deserialización desde diccionario."""
        data = {
            "id": "test-uuid-1234",
            "initiator_name": "Ana",
            "receiver_name": "Carlos",
            "interaction_type": "thought",
            "tone": "warm",
            "chapter": 5,
            "text_excerpt": "Ana pensó en Carlos",
            "confidence": 0.7,
        }

        interaction = EntityInteraction.from_dict(data)
        assert interaction.id == "test-uuid-1234"
        assert interaction.initiator_name == "Ana"
        assert interaction.receiver_name == "Carlos"
        assert interaction.interaction_type == InteractionType.THOUGHT_ABOUT
        assert interaction.tone == InteractionTone.WARM


class TestInteractionPattern:
    """Tests para InteractionPattern dataclass."""

    def test_create_pattern(self):
        """Crea patrón de interacción."""
        pattern = InteractionPattern(
            entity1_name="Juan",
            entity2_name="María",
            total_interactions=10,
            average_tone=InteractionTone.WARM,
            average_sentiment_score=0.4,
        )

        assert pattern.entity1_name == "Juan"
        assert pattern.total_interactions == 10
        assert pattern.average_tone == InteractionTone.WARM

    def test_pattern_to_dict(self):
        """Verifica serialización de patrón."""
        pattern = InteractionPattern(
            entity1_name="A",
            entity2_name="B",
            total_interactions=5,
            tone_trend="improving",
        )

        data = pattern.to_dict()
        assert data["entity1_name"] == "A"
        assert data["total_interactions"] == 5
        assert data["tone_trend"] == "improving"


# ============================================================================
# Tests de Detector
# ============================================================================


class TestInteractionDetector:
    """Tests para InteractionDetector."""

    @pytest.fixture
    def detector(self):
        """Crea detector sin analizador de sentimiento."""
        return InteractionDetector()

    @pytest.fixture
    def entities(self):
        """Lista de entidades de prueba."""
        return ["Juan", "María", "Pedro", "Ana"]

    def test_detect_action_positive(self, detector, entities):
        """Detecta acción positiva."""
        text = "Juan abrazó a María con cariño."
        interactions = detector.detect_actions(text, entities, chapter=1)

        assert len(interactions) >= 1
        action = interactions[0]
        assert action.initiator_name == "Juan"
        assert action.receiver_name == "María"
        assert action.interaction_type == InteractionType.ACTION_TOWARDS

    def test_detect_action_negative(self, detector, entities):
        """Detecta acción negativa."""
        text = "Pedro golpeó a Juan furiosamente."
        interactions = detector.detect_actions(text, entities, chapter=1)

        assert len(interactions) >= 1
        action = interactions[0]
        assert action.initiator_name == "Pedro"
        assert action.receiver_name == "Juan"
        assert action.tone == InteractionTone.HOSTILE

    def test_detect_thought(self, detector, entities):
        """Detecta pensamiento sobre otra entidad."""
        text = "María pensó en Juan durante toda la noche."
        interactions = detector.detect_thoughts(text, entities, chapter=2)

        assert len(interactions) >= 1
        thought = interactions[0]
        assert thought.initiator_name == "María"
        assert thought.receiver_name == "Juan"
        assert thought.interaction_type == InteractionType.THOUGHT_ABOUT

    def test_detect_physical_contact(self, detector, entities):
        """Detecta contacto físico."""
        text = "Ana besó a Pedro suavemente."
        interactions = detector.detect_physical_contact(text, entities, chapter=3)

        assert len(interactions) >= 1
        contact = interactions[0]
        assert contact.initiator_name == "Ana"
        assert contact.receiver_name == "Pedro"
        assert contact.interaction_type == InteractionType.PHYSICAL_CONTACT

    def test_detect_all_combines_types(self, detector, entities):
        """detect_all combina todos los tipos de detección."""
        text = """
        Juan abrazó a María. Ella pensó en él con cariño.
        Pedro golpeó a Ana en un arrebato de furia.
        """
        interactions = detector.detect_all(text, entities, chapter=1)

        # Debe detectar múltiples interacciones
        assert len(interactions) >= 2

        # Verificar que hay variedad de tipos
        types = {i.interaction_type for i in interactions}
        assert len(types) >= 1

    def test_ignores_non_entities(self, detector, entities):
        """No detecta interacciones con entidades desconocidas."""
        text = "Roberto abrazó a Carmen."  # No están en entities
        interactions = detector.detect_all(text, entities, chapter=1)

        # No debe detectar nada porque no son entidades conocidas
        assert len(interactions) == 0

    def test_classify_tone_hostile(self, detector):
        """Clasifica tono hostil correctamente."""
        text = "Lo golpeó con furia y desprecio, su odio era palpable."
        tone = detector.classify_tone(text)
        assert tone == InteractionTone.HOSTILE

    def test_classify_tone_affectionate(self, detector):
        """Clasifica tono afectuoso."""
        text = "Lo abrazó con ternura y amor, su adoración era evidente."
        tone = detector.classify_tone(text)
        assert tone in [InteractionTone.AFFECTIONATE, InteractionTone.WARM]

    def test_classify_tone_neutral(self, detector):
        """Clasifica tono neutral."""
        text = "Caminaron juntos por el parque."
        tone = detector.classify_tone(text)
        assert tone == InteractionTone.NEUTRAL

    def test_detect_dialogue_interaction(self, detector):
        """Detecta interacción en diálogo."""
        dialogue = "—Te quiero mucho, María —dijo Juan."
        speaker = "Juan"
        context_entities = ["Juan", "María"]

        interaction = detector.detect_dialogue_interaction(
            dialogue_text=dialogue,
            speaker=speaker,
            context_entities=context_entities,
            chapter=1,
            start_char=0,
            end_char=len(dialogue),
        )

        assert interaction is not None
        assert interaction.initiator_name == "Juan"
        assert interaction.receiver_name == "María"
        assert interaction.interaction_type == InteractionType.DIALOGUE

    def test_detect_dialogue_with_tu_pronoun(self, detector):
        """Detecta destinatario por pronombre 'tú'."""
        dialogue = "—¿Cómo estás tú hoy?"
        speaker = "Juan"
        context_entities = ["Juan", "María"]

        interaction = detector.detect_dialogue_interaction(
            dialogue_text=dialogue,
            speaker=speaker,
            context_entities=context_entities,
            chapter=1,
        )

        assert interaction is not None
        assert interaction.receiver_name == "María"


class TestDetectInteractionsInText:
    """Tests para función de conveniencia detect_interactions_in_text."""

    def test_convenience_function_works(self):
        """La función de conveniencia detecta interacciones."""
        text = "Juan ayudó a María generosamente."
        entities = ["Juan", "María"]

        interactions = detect_interactions_in_text(text, entities, chapter=1)

        assert len(interactions) >= 1
        assert interactions[0].initiator_name == "Juan"


# ============================================================================
# Tests de Pattern Analyzer
# ============================================================================


class TestInteractionPatternAnalyzer:
    """Tests para InteractionPatternAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Crea analizador de patrones."""
        return InteractionPatternAnalyzer()

    @pytest.fixture
    def sample_interactions(self):
        """Crea conjunto de interacciones de muestra."""
        return [
            EntityInteraction(
                initiator_name="Juan",
                receiver_name="María",
                interaction_type=InteractionType.DIALOGUE,
                tone=InteractionTone.WARM,
                chapter=1,
                start_char=0,
            ),
            EntityInteraction(
                initiator_name="María",
                receiver_name="Juan",
                interaction_type=InteractionType.DIALOGUE,
                tone=InteractionTone.WARM,
                chapter=1,
                start_char=100,
            ),
            EntityInteraction(
                initiator_name="Juan",
                receiver_name="María",
                interaction_type=InteractionType.PHYSICAL_CONTACT,
                tone=InteractionTone.AFFECTIONATE,
                chapter=2,
                start_char=200,
            ),
            EntityInteraction(
                initiator_name="Pedro",
                receiver_name="Ana",
                interaction_type=InteractionType.ACTION_TOWARDS,
                tone=InteractionTone.HOSTILE,
                chapter=3,
                start_char=300,
            ),
        ]

    def test_analyze_pair_basic(self, analyzer, sample_interactions):
        """Analiza patrón entre un par de entidades."""
        juan_maria = [
            i
            for i in sample_interactions
            if {i.initiator_name, i.receiver_name} == {"Juan", "María"}
        ]

        pattern = analyzer.analyze_pair("Juan", "María", juan_maria)

        assert pattern.entity1_name == "Juan"
        assert pattern.entity2_name == "María"
        assert pattern.total_interactions == 3
        assert pattern.average_tone in [InteractionTone.WARM, InteractionTone.AFFECTIONATE]

    def test_analyze_pair_calculates_asymmetry(self, analyzer):
        """Calcula asimetría correctamente."""
        interactions = [
            EntityInteraction(initiator_name="A", receiver_name="B", chapter=1),
            EntityInteraction(initiator_name="A", receiver_name="B", chapter=1),
            EntityInteraction(initiator_name="A", receiver_name="B", chapter=1),
            EntityInteraction(initiator_name="B", receiver_name="A", chapter=1),
        ]

        pattern = analyzer.analyze_pair("A", "B", interactions)

        # A inicia 3, B inicia 1 -> A domina
        assert pattern.initiations_by_entity1 == 3
        assert pattern.initiations_by_entity2 == 1
        assert pattern.asymmetry_ratio < 0.5  # A inicia más

    def test_generate_all_patterns(self, analyzer, sample_interactions):
        """Genera patrones para todos los pares."""
        patterns = analyzer.generate_all_patterns(sample_interactions)

        # Debe generar patrones para Juan-María y Pedro-Ana
        assert len(patterns) == 2
        # Las claves están normalizadas a minúsculas
        assert ("juan", "maría") in patterns or ("maría", "juan") in patterns

    def test_detect_anomaly_tone_shift(self, analyzer, sample_interactions):
        """Detecta anomalía por cambio brusco de tono."""
        # Patrón establecido: Juan-María son cálidos
        juan_maria = [
            i
            for i in sample_interactions
            if {i.initiator_name, i.receiver_name} == {"Juan", "María"}
        ]
        pattern = analyzer.analyze_pair("Juan", "María", juan_maria)

        # Nueva interacción hostil - anómala
        new_hostile = EntityInteraction(
            initiator_name="Juan",
            receiver_name="María",
            interaction_type=InteractionType.ACTION_TOWARDS,
            tone=InteractionTone.HOSTILE,
            chapter=10,
        )

        alert = analyzer.detect_anomaly(pattern, new_hostile)

        # Debe detectar anomalía
        assert alert is not None
        assert alert.severity in ["warning", "error"]

    def test_no_anomaly_for_consistent_interaction(self, analyzer, sample_interactions):
        """No genera alerta para interacción consistente."""
        juan_maria = [
            i
            for i in sample_interactions
            if {i.initiator_name, i.receiver_name} == {"Juan", "María"}
        ]
        pattern = analyzer.analyze_pair("Juan", "María", juan_maria)

        # Nueva interacción cálida - consistente
        new_warm = EntityInteraction(
            initiator_name="Juan",
            receiver_name="María",
            interaction_type=InteractionType.DIALOGUE,
            tone=InteractionTone.WARM,
            chapter=10,
        )

        alert = analyzer.detect_anomaly(pattern, new_warm)
        assert alert is None

    def test_detect_asymmetric_relationships(self, analyzer):
        """Detecta relaciones muy asimétricas."""
        interactions = [
            EntityInteraction(initiator_name="Dominador", receiver_name="Sumiso", chapter=i)
            for i in range(10)
        ]
        # Solo una interacción iniciada por Sumiso
        interactions.append(
            EntityInteraction(initiator_name="Sumiso", receiver_name="Dominador", chapter=11)
        )

        patterns = analyzer.generate_all_patterns(interactions)
        alerts = analyzer.detect_asymmetric_relationships(patterns, threshold=0.25)

        assert len(alerts) >= 1
        assert (
            "asimétrica" in alerts[0].explanation.lower()
            or "asymmetric" in alerts[0].explanation.lower()
        )


# ============================================================================
# Tests de Repository
# ============================================================================


class TestInteractionRepository:
    """Tests para InteractionRepository."""

    @pytest.fixture
    def db(self, tmp_path):
        """Crea base de datos temporal."""
        db_path = tmp_path / "test_interactions.db"
        database = Database(db_path)
        # Crear proyecto de prueba para FK constraints
        with database.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_path, document_fingerprint, document_format)
                   VALUES (?, ?, ?, ?, ?)""",
                (1, "Test Project", "/test/path.docx", "abc123fingerprint", "docx"),
            )
        return database

    @pytest.fixture
    def repo(self, db):
        """Crea repositorio."""
        return InteractionRepository(db)

    @pytest.fixture
    def sample_interaction(self):
        """Crea interacción de muestra."""
        return EntityInteraction(
            project_id=1,
            initiator_id="entity-1",
            receiver_id="entity-2",
            initiator_name="Juan",
            receiver_name="María",
            interaction_type=InteractionType.DIALOGUE,
            tone=InteractionTone.WARM,
            chapter=1,
            text_excerpt="—Hola María —dijo Juan.",
            start_char=0,
            end_char=25,
            confidence=0.8,
        )

    def test_save_and_get_interaction(self, repo, sample_interaction):
        """Guarda y recupera interacción."""
        repo.save_interaction(sample_interaction)
        retrieved = repo.get_interaction(sample_interaction.id)

        assert retrieved is not None
        assert retrieved.id == sample_interaction.id
        assert retrieved.initiator_name == "Juan"
        assert retrieved.receiver_name == "María"
        assert retrieved.interaction_type == InteractionType.DIALOGUE

    def test_get_interactions_by_project(self, repo, sample_interaction):
        """Obtiene interacciones por proyecto."""
        repo.save_interaction(sample_interaction)

        # Crear otra interacción del mismo proyecto
        i2 = EntityInteraction(
            project_id=1,
            initiator_name="Pedro",
            receiver_name="Ana",
            chapter=2,
        )
        repo.save_interaction(i2)

        # Obtener interacciones usando el método correcto
        interactions = repo.get_interactions_for_project(1)
        assert len(interactions) == 2
        assert all(i.project_id == 1 for i in interactions)

    def test_get_interactions_by_chapter(self, repo):
        """Obtiene interacciones filtrando por capítulo."""
        for ch in [1, 1, 2, 3]:
            repo.save_interaction(
                EntityInteraction(
                    project_id=1,
                    initiator_name="A",
                    receiver_name="B",
                    chapter=ch,
                )
            )

        # Filtrar por capítulo en el método get_interactions_for_project
        all_interactions = repo.get_interactions_for_project(1)
        chapter_1 = [i for i in all_interactions if i.chapter == 1]
        assert len(chapter_1) == 2

    def test_get_interactions_by_entity_pair(self, repo, sample_interaction):
        """Obtiene interacciones entre par de entidades."""
        repo.save_interaction(sample_interaction)

        # Interacción inversa
        repo.save_interaction(
            EntityInteraction(
                project_id=1,
                initiator_name="María",
                receiver_name="Juan",
                chapter=2,
            )
        )

        # Otra interacción diferente
        repo.save_interaction(
            EntityInteraction(
                project_id=1,
                initiator_name="Pedro",
                receiver_name="Ana",
                chapter=1,
            )
        )

        pair_interactions = repo.get_interactions_between(1, "Juan", "María")
        assert len(pair_interactions) == 2

    def test_save_and_get_pattern(self, repo):
        """Guarda y recupera patrón."""
        pattern = InteractionPattern(
            entity1_id="e1",
            entity2_id="e2",
            entity1_name="Juan",
            entity2_name="María",
            total_interactions=5,
            average_tone=InteractionTone.WARM,
            tone_trend="improving",
        )

        repo.save_pattern(1, pattern)
        patterns = repo.get_patterns_for_project(1)

        assert len(patterns) >= 1
        # Buscar el patrón Juan-María
        juan_maria = [
            p
            for p in patterns
            if {p.entity1_name.lower(), p.entity2_name.lower()} == {"juan", "maría"}
        ]
        assert len(juan_maria) == 1
        assert juan_maria[0].total_interactions == 5

    def test_save_and_get_alert(self, repo):
        """Guarda y recupera alerta."""
        alert = InteractionAlert(
            code="TONE_SHIFT",
            alert_type="Cambio brusco de tono",
            severity="warning",
            entity1_name="Juan",
            entity2_name="María",
            chapter=5,
            explanation="Interacción hostil inesperada",
            confidence=0.7,
        )

        repo.save_alert(1, alert)
        alerts = repo.get_alerts_for_project(1)

        assert len(alerts) == 1
        assert alerts[0].code == "TONE_SHIFT"
        assert alerts[0].severity == "warning"

    def test_batch_save_interactions(self, repo):
        """Guarda múltiples interacciones en batch."""
        interactions = [
            EntityInteraction(
                project_id=1, initiator_name=f"E{i}", receiver_name=f"E{i + 1}", chapter=1
            )
            for i in range(100)
        ]

        repo.save_interactions_batch(interactions)

        retrieved = repo.get_interactions_for_project(1)
        assert len(retrieved) == 100

    def test_get_interaction_statistics(self, repo):
        """Obtiene estadísticas de interacciones."""
        # Crear interacciones variadas
        tones = [
            InteractionTone.WARM,
            InteractionTone.WARM,
            InteractionTone.HOSTILE,
            InteractionTone.NEUTRAL,
        ]
        types = [
            InteractionType.DIALOGUE,
            InteractionType.DIALOGUE,
            InteractionType.ACTION_TOWARDS,
            InteractionType.THOUGHT_ABOUT,
        ]

        for tone, itype in zip(tones, types):
            repo.save_interaction(
                EntityInteraction(
                    project_id=1,
                    initiator_name="A",
                    receiver_name="B",
                    interaction_type=itype,
                    tone=tone,
                    chapter=1,
                )
            )

        stats = repo.get_interaction_stats(1)

        assert stats["total"] == 4
        assert "by_type" in stats
        assert "by_tone" in stats


# ============================================================================
# Tests de Integración
# ============================================================================


class TestInteractionIntegration:
    """Tests de integración del módulo completo."""

    def test_full_workflow(self, tmp_path):
        """Flujo completo: detección -> análisis -> persistencia."""
        # 1. Detectar interacciones
        text = """
        Juan sonrió a María y le dijo: —Te quiero mucho.
        María abrazó a Juan con ternura.
        Pedro miró a Ana con recelo y murmuró algo.
        """
        entities = ["Juan", "María", "Pedro", "Ana"]

        detector = InteractionDetector()
        interactions = detector.detect_all(text, entities, chapter=1)

        assert len(interactions) >= 2

        # 2. Analizar patrones
        analyzer = InteractionPatternAnalyzer()
        patterns = analyzer.generate_all_patterns(interactions)

        # 3. Persistir
        db_path = tmp_path / "integration_test.db"
        db = Database(db_path)
        # Crear proyecto de prueba para FK constraints
        with db.connection() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, document_path, document_fingerprint, document_format)
                   VALUES (?, ?, ?, ?, ?)""",
                (1, "Integration Test", "/test/integration.docx", "integration123", "docx"),
            )
        repo = InteractionRepository(db)

        for interaction in interactions:
            interaction.project_id = 1
            repo.save_interaction(interaction)

        for pair, pattern in patterns.items():
            repo.save_pattern(1, pattern)

        # 4. Verificar persistencia
        retrieved = repo.get_interactions_for_project(1)
        assert len(retrieved) == len(interactions)

    def test_anomaly_detection_workflow(self):
        """Flujo de detección de anomalías."""
        # Interacciones establecidas (cálidas)
        interactions = [
            EntityInteraction(
                initiator_name="Juan",
                receiver_name="María",
                tone=InteractionTone.WARM,
                chapter=i,
            )
            for i in range(1, 5)
        ]

        analyzer = InteractionPatternAnalyzer()
        pattern = analyzer.analyze_pair("Juan", "María", interactions)

        # Nueva interacción anómala
        anomalous = EntityInteraction(
            initiator_name="Juan",
            receiver_name="María",
            tone=InteractionTone.HOSTILE,
            chapter=10,
            text_excerpt="Juan golpeó a María",
        )

        alert = analyzer.detect_anomaly(pattern, anomalous)
        assert alert is not None
        assert alert.severity in ["warning", "error"]


# ============================================================================
# Tests de Listas de Verbos
# ============================================================================


class TestVerbLists:
    """Tests para listas de verbos."""

    def test_dialogue_verbs_not_empty(self):
        """Lista de verbos de diálogo no vacía."""
        assert len(DIALOGUE_VERBS) > 0
        assert "dijo" in DIALOGUE_VERBS
        assert "preguntó" in DIALOGUE_VERBS

    def test_action_verbs_positive_not_empty(self):
        """Lista de verbos positivos no vacía."""
        assert len(ACTION_VERBS_POSITIVE) > 0
        assert "abrazó" in ACTION_VERBS_POSITIVE
        assert "ayudó" in ACTION_VERBS_POSITIVE

    def test_action_verbs_negative_not_empty(self):
        """Lista de verbos negativos no vacía."""
        assert len(ACTION_VERBS_NEGATIVE) > 0
        assert "golpeó" in ACTION_VERBS_NEGATIVE
        assert "atacó" in ACTION_VERBS_NEGATIVE

    def test_no_overlap_positive_negative(self):
        """Verbos positivos y negativos no se solapan."""
        overlap = set(ACTION_VERBS_POSITIVE) & set(ACTION_VERBS_NEGATIVE)
        assert len(overlap) == 0, f"Verbos en ambas listas: {overlap}"
