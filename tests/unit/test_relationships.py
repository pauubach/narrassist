"""
Tests para el módulo de relaciones entre entidades.
"""

import pytest

from narrative_assistant.relationships.analyzer import (
    EXPECTED_TONES,
    EntityInteraction,
    InteractionCoherenceChecker,
    InteractionTone,
    RelationshipAnalyzer,
)
from narrative_assistant.relationships.detector import (
    DetectedRelation,
    RelationshipDetector,
    detect_relationships_from_text,
)
from narrative_assistant.relationships.models import (
    INVERSE_RELATIONS,
    RELATION_TYPE_VALENCE,
    SYMMETRIC_RELATIONS,
    CoherenceAlert,
    EntityRelationship,
    InferredExpectations,
    RelationCategory,
    RelationshipChange,
    RelationshipEvidence,
    RelationshipType,
    RelationType,
    RelationValence,
    TextReference,
)


class TestRelationTypeEnums:
    """Tests para enums de tipos de relación."""

    def test_relation_type_values(self):
        """Verifica que los tipos de relación tienen valores correctos."""
        assert RelationType.FRIEND.value == "friend"
        assert RelationType.ENEMY.value == "enemy"
        assert RelationType.PARENT.value == "parent"
        assert RelationType.CHILD.value == "child"
        assert RelationType.FEARS.value == "fears"
        assert RelationType.OWNS.value == "owns"

    def test_relation_category_values(self):
        """Verifica categorías de relación."""
        assert RelationCategory.FAMILY.value == "family"
        assert RelationCategory.SOCIAL.value == "social"
        assert RelationCategory.ROMANTIC.value == "romantic"
        assert RelationCategory.EMOTIONAL.value == "emotional"

    def test_relation_valence_values(self):
        """Verifica valencias de relación."""
        assert RelationValence.POSITIVE.value == 1
        assert RelationValence.NEGATIVE.value == -1
        assert RelationValence.NEUTRAL.value == 0
        assert RelationValence.FEAR.value == 3


class TestRelationMappings:
    """Tests para mapeos de relaciones."""

    def test_valence_mapping_exists(self):
        """Verifica que tipos comunes tienen valencia definida."""
        assert RelationType.FRIEND in RELATION_TYPE_VALENCE
        assert RelationType.ENEMY in RELATION_TYPE_VALENCE
        assert RelationType.FEARS in RELATION_TYPE_VALENCE

    def test_valence_values_correct(self):
        """Verifica que las valencias son correctas."""
        assert RELATION_TYPE_VALENCE[RelationType.FRIEND] == RelationValence.POSITIVE
        assert RELATION_TYPE_VALENCE[RelationType.ENEMY] == RelationValence.VERY_NEGATIVE
        assert RELATION_TYPE_VALENCE[RelationType.FEARS] == RelationValence.FEAR

    def test_inverse_relations_exist(self):
        """Verifica que hay relaciones inversas definidas."""
        assert RelationType.PARENT in INVERSE_RELATIONS
        assert INVERSE_RELATIONS[RelationType.PARENT] == RelationType.CHILD
        assert INVERSE_RELATIONS[RelationType.CHILD] == RelationType.PARENT

    def test_symmetric_relations(self):
        """Verifica relaciones simétricas."""
        assert RelationType.FRIEND in SYMMETRIC_RELATIONS
        assert RelationType.ENEMY in SYMMETRIC_RELATIONS
        assert RelationType.SIBLING in SYMMETRIC_RELATIONS
        assert RelationType.SPOUSE in SYMMETRIC_RELATIONS
        # No simétricas
        assert RelationType.PARENT not in SYMMETRIC_RELATIONS
        assert RelationType.OWNS not in SYMMETRIC_RELATIONS


class TestTextReference:
    """Tests para TextReference."""

    def test_create_reference(self):
        """Verifica creación de referencia textual."""
        ref = TextReference(
            chapter=5,
            chapter_title="El encuentro",
            page=42,
            char_start=1000,
            char_end=1100,
        )
        assert ref.chapter == 5
        assert ref.chapter_title == "El encuentro"
        assert ref.page == 42
        assert ref.char_start == 1000

    def test_reference_to_dict(self):
        """Verifica serialización a diccionario."""
        ref = TextReference(chapter=3, char_start=100, char_end=200)
        d = ref.to_dict()
        assert d["chapter"] == 3
        assert d["char_start"] == 100

    def test_reference_from_dict(self):
        """Verifica deserialización desde diccionario."""
        data = {"chapter": 7, "char_start": 500, "char_end": 600}
        ref = TextReference.from_dict(data)
        assert ref.chapter == 7
        assert ref.char_start == 500


class TestInferredExpectations:
    """Tests para InferredExpectations."""

    def test_create_expectations(self):
        """Verifica creación de expectativas."""
        exp = InferredExpectations(
            expected_behaviors=["ayuda", "apoya"],
            forbidden_behaviors=["traiciona"],
            expected_consequences=[],
            confidence=0.8,
            reasoning="Basado en amistad",
            inference_source="rule_based",
        )
        assert len(exp.expected_behaviors) == 2
        assert "traiciona" in exp.forbidden_behaviors
        assert exp.confidence == 0.8

    def test_expectations_to_dict(self):
        """Verifica serialización."""
        exp = InferredExpectations(
            expected_behaviors=["evita"],
            forbidden_behaviors=["abraza"],
            confidence=0.7,
        )
        d = exp.to_dict()
        assert "evita" in d["expected_behaviors"]
        assert d["confidence"] == 0.7

    def test_expectations_from_dict(self):
        """Verifica deserialización."""
        data = {
            "expected_behaviors": ["huye"],
            "forbidden_behaviors": [],
            "expected_consequences": [],
            "confidence": 0.6,
            "reasoning": "",
            "inference_source": "rule_based",
        }
        exp = InferredExpectations.from_dict(data)
        assert "huye" in exp.expected_behaviors
        assert exp.confidence == 0.6


class TestRelationshipType:
    """Tests para RelationshipType."""

    def test_create_relationship_type(self):
        """Verifica creación de tipo de relación."""
        rt = RelationshipType(
            project_id=1,
            name="enemy",
            description="Relación de enemistad",
            relation_type=RelationType.ENEMY,
            category=RelationCategory.SOCIAL,
        )
        assert rt.name == "enemy"
        assert rt.relation_type == RelationType.ENEMY
        assert rt.project_id == 1

    def test_auto_valence(self):
        """Verifica que la valencia se asigna automáticamente."""
        rt = RelationshipType(
            relation_type=RelationType.FRIEND,
        )
        # Se asigna en __post_init__
        assert rt.default_valence == RelationValence.POSITIVE

    def test_auto_bidirectional(self):
        """Verifica que bidireccionalidad se asigna para tipos simétricos."""
        rt = RelationshipType(
            relation_type=RelationType.FRIEND,
        )
        assert rt.is_bidirectional is True

        rt2 = RelationshipType(
            relation_type=RelationType.PARENT,
        )
        assert rt2.is_bidirectional is False

    def test_get_expectations_rule_based(self):
        """Verifica generación de expectativas desde reglas."""
        rt = RelationshipType(
            relation_type=RelationType.FRIEND,
        )
        exp = rt.get_expectations()
        assert exp is not None
        assert "ayuda" in exp.expected_behaviors
        assert "traiciona" in exp.forbidden_behaviors

    def test_to_dict(self):
        """Verifica serialización."""
        rt = RelationshipType(
            project_id=1,
            name="test",
            relation_type=RelationType.RIVAL,
        )
        d = rt.to_dict()
        assert d["relation_type"] == "rival"
        assert d["project_id"] == 1


class TestEntityRelationship:
    """Tests para EntityRelationship."""

    def test_create_relationship(self):
        """Verifica creación de relación."""
        rel = EntityRelationship(
            project_id=1,
            source_entity_id="e1",
            target_entity_id="e2",
            source_entity_name="Juan",
            target_entity_name="María",
            relation_type=RelationType.FRIEND,
            confidence=0.85,
        )
        assert rel.source_entity_name == "Juan"
        assert rel.target_entity_name == "María"
        assert rel.relation_type == RelationType.FRIEND
        assert rel.bidirectional is True  # Amigos es simétrico

    def test_get_valence(self):
        """Verifica obtención de valencia."""
        rel = EntityRelationship(
            relation_type=RelationType.ENEMY,
        )
        assert rel.get_valence() == RelationValence.VERY_NEGATIVE

    def test_get_inverse_type(self):
        """Verifica obtención de tipo inverso."""
        rel = EntityRelationship(
            relation_type=RelationType.PARENT,
        )
        assert rel.get_inverse_type() == RelationType.CHILD

    def test_to_dict(self):
        """Verifica serialización."""
        rel = EntityRelationship(
            source_entity_name="Pedro",
            target_entity_name="Ana",
            relation_type=RelationType.MENTOR,
            intensity=0.8,
        )
        d = rel.to_dict()
        assert d["source_entity_name"] == "Pedro"
        assert d["relation_type"] == "mentor"
        assert d["intensity"] == 0.8


class TestRelationshipDetector:
    """Tests para RelationshipDetector."""

    def test_detector_creation(self):
        """Verifica creación del detector."""
        detector = RelationshipDetector()
        assert detector is not None

    def test_detect_family_mother(self):
        """Detecta relación madre-hijo."""
        detector = RelationshipDetector()
        text = "María, la madre de Juan, entró en la habitación."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        rel = relations[0]
        assert rel.source_name == "María"
        assert rel.target_name == "Juan"
        assert rel.relation_type == RelationType.PARENT

    def test_detect_family_father(self):
        """Detecta relación padre-hijo."""
        detector = RelationshipDetector()
        text = "Pedro, padre de Luis, era un hombre severo."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.PARENT

    def test_detect_siblings(self):
        """Detecta relación de hermanos."""
        detector = RelationshipDetector()
        text = "Carlos, hermano de Elena, la defendió siempre."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.SIBLING

    def test_detect_friends(self):
        """Detecta relación de amistad."""
        detector = RelationshipDetector()
        text = "Pedro y Luis eran los mejores amigos desde la infancia."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.FRIEND

    def test_detect_enemy(self):
        """Detecta relación de enemistad."""
        detector = RelationshipDetector()
        text = "Ana, enemigo de Carlos, planeaba su venganza."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.ENEMY

    def test_detect_hate_verb(self):
        """Detecta odio mediante verbo."""
        detector = RelationshipDetector()
        text = "Juan odiaba a Pedro con toda su alma."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.HATES

    def test_detect_fear(self):
        """Detecta miedo."""
        detector = RelationshipDetector()
        text = "María temía a la oscuridad desde niña."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.FEARS

    def test_detect_love(self):
        """Detecta amor."""
        detector = RelationshipDetector()
        text = "Pedro estaba enamorado de Ana desde hace años."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.LOVER

    def test_detect_spatial_lives(self):
        """Detecta relación espacial vive_en."""
        detector = RelationshipDetector()
        text = "Carlos vivía en Madrid desde hace diez años."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        assert relations[0].relation_type == RelationType.LIVES_IN

    def test_detect_from_dialogue(self):
        """Detecta relación desde diálogo."""
        detector = RelationshipDetector()
        dialogue = "Mi hermano Juan siempre fue el favorito de mamá."
        relations = detector.detect_from_dialogue(
            dialogue,
            speaker="María",
            context_entities=["Juan"],
            chapter=1,
        )

        # Debería detectar que María tiene un hermano llamado Juan
        assert len(relations) >= 1

    def test_known_entities_boost_confidence(self):
        """Verifica que entidades conocidas aumentan confianza."""
        detector = RelationshipDetector(known_entities=["María", "Juan"])
        text = "María, madre de Juan, sonrió."
        relations = detector.detect_from_text(text)

        assert len(relations) >= 1
        # Con entidades conocidas, la confianza debería ser mayor
        assert relations[0].confidence > 0.9

    def test_convert_to_relationships(self):
        """Verifica conversión a EntityRelationship."""
        detector = RelationshipDetector()
        text = "Ana, amiga de Luis, llegó temprano."
        detected = detector.detect_from_text(text)

        relationships = detector.convert_to_relationships(
            detected,
            project_id=1,
            entity_id_map={"ana": "e1", "luis": "e2"},
        )

        assert len(relationships) >= 1
        assert relationships[0].project_id == 1

    def test_convenience_function(self):
        """Verifica función de conveniencia."""
        relations = detect_relationships_from_text(
            "Pedro, padre de María, era estricto.",
            chapter=5,
        )
        assert len(relations) >= 1
        assert relations[0].chapter == 5


class TestInteractionTone:
    """Tests para InteractionTone y clasificación."""

    def test_tone_values(self):
        """Verifica valores de tono."""
        assert InteractionTone.HOSTILE.value == "hostile"
        assert InteractionTone.WARM.value == "warm"

    def test_expected_tones_mapping(self):
        """Verifica mapeo de tonos esperados."""
        assert InteractionTone.WARM in EXPECTED_TONES[RelationType.FRIEND]
        assert InteractionTone.HOSTILE in EXPECTED_TONES[RelationType.ENEMY]


class TestInteractionCoherenceChecker:
    """Tests para InteractionCoherenceChecker."""

    def test_checker_creation(self):
        """Verifica creación del checker."""
        checker = InteractionCoherenceChecker()
        assert checker is not None

    def test_classify_hostile_tone(self):
        """Clasifica tono hostil."""
        checker = InteractionCoherenceChecker()
        text = "Juan golpeó a Pedro con rabia y lo insultó."
        tone = checker.classify_tone(text)
        assert tone == InteractionTone.HOSTILE

    def test_classify_warm_tone(self):
        """Clasifica tono cálido."""
        checker = InteractionCoherenceChecker()
        text = "María sonrió amablemente y ayudó a su amigo."
        tone = checker.classify_tone(text)
        assert tone == InteractionTone.WARM

    def test_classify_affectionate_tone(self):
        """Clasifica tono afectuoso."""
        checker = InteractionCoherenceChecker()
        text = "La abrazó con cariño y la besó en la frente."
        tone = checker.classify_tone(text)
        assert tone == InteractionTone.AFFECTIONATE

    def test_classify_neutral_no_keywords(self):
        """Clasifica tono neutral sin palabras clave."""
        checker = InteractionCoherenceChecker()
        text = "Juan caminó hacia la puerta y salió."
        tone = checker.classify_tone(text)
        assert tone == InteractionTone.NEUTRAL

    def test_check_coherence_friend_warm(self):
        """Verifica coherencia amigo-cálido (coherente)."""
        checker = InteractionCoherenceChecker()

        interaction = EntityInteraction(
            initiator_name="Juan",
            receiver_name="Pedro",
            interaction_type="dialogue",
            tone=InteractionTone.WARM,
            chapter=1,
            text_excerpt="Juan sonrió a Pedro.",
        )

        relationship = EntityRelationship(
            source_entity_name="Juan",
            target_entity_name="Pedro",
            relation_type=RelationType.FRIEND,
            evidence_texts=["Eran amigos desde la infancia."],
        )

        alert = checker.check_coherence(interaction, relationship)
        assert alert is None  # Coherente

    def test_check_coherence_friend_hostile(self):
        """Verifica coherencia amigo-hostil (incoherente)."""
        checker = InteractionCoherenceChecker()

        interaction = EntityInteraction(
            initiator_name="Juan",
            receiver_name="Pedro",
            interaction_type="action",
            tone=InteractionTone.HOSTILE,
            chapter=5,
            text_excerpt="Juan atacó a Pedro.",
        )

        relationship = EntityRelationship(
            source_entity_name="Juan",
            target_entity_name="Pedro",
            relation_type=RelationType.FRIEND,
            first_mention_chapter=1,
            evidence_texts=["Eran amigos."],
        )

        alert = checker.check_coherence(interaction, relationship)
        assert alert is not None
        assert alert.code == "INT_FRIEND_HOSTILE"

    def test_check_coherence_enemy_friendly(self):
        """Verifica coherencia enemigo-amistoso (incoherente)."""
        checker = InteractionCoherenceChecker()

        interaction = EntityInteraction(
            initiator_name="Ana",
            receiver_name="María",
            interaction_type="action",
            tone=InteractionTone.AFFECTIONATE,
            chapter=10,
            text_excerpt="Ana abrazó a María con cariño.",
        )

        relationship = EntityRelationship(
            source_entity_name="Ana",
            target_entity_name="María",
            relation_type=RelationType.ENEMY,
            evidence_texts=["Se odiaban desde siempre."],
        )

        alert = checker.check_coherence(interaction, relationship)
        assert alert is not None
        assert alert.code == "INT_ENEMY_FRIENDLY"

    def test_check_forbidden_behavior(self):
        """Verifica detección de comportamiento prohibido."""
        checker = InteractionCoherenceChecker()

        relationship = EntityRelationship(
            source_entity_name="Pedro",
            target_entity_name="cementerio",
            relation_type=RelationType.FEARS,
            expectations=InferredExpectations(
                expected_behaviors=["evita", "huye"],
                forbidden_behaviors=["se acercó tranquilamente", "disfrutó"],
                confidence=0.8,
            ),
        )

        text = "Pedro se acercó tranquilamente al cementerio silbando."

        alert = checker.check_forbidden_behavior(
            text,
            relationship,
            chapter=5,
        )

        assert alert is not None
        assert alert.code == "COHERENCE_FORBIDDEN_BEHAVIOR"


class TestRelationshipAnalyzer:
    """Tests para RelationshipAnalyzer."""

    def test_analyzer_creation(self):
        """Verifica creación del analizador."""
        analyzer = RelationshipAnalyzer()
        assert analyzer is not None

    def test_detect_interaction(self):
        """Detecta interacción entre entidades."""
        analyzer = RelationshipAnalyzer()

        text = "Juan sonrió y abrazó a María con cariño."
        interaction = analyzer.detect_interaction(
            text,
            entity1_name="Juan",
            entity2_name="María",
            chapter=1,
        )

        assert interaction is not None
        # Both WARM and AFFECTIONATE are positive tones, acceptable for this text
        assert interaction.tone in [InteractionTone.WARM, InteractionTone.AFFECTIONATE]

    def test_detect_interaction_dialogue(self):
        """Detecta interacción de diálogo."""
        analyzer = RelationshipAnalyzer()

        text = 'Juan dijo a María: "Te quiero mucho".'
        interaction = analyzer.detect_interaction(
            text,
            entity1_name="Juan",
            entity2_name="María",
        )

        assert interaction is not None
        assert interaction.interaction_type == "dialogue"

    def test_check_scene_consistency(self):
        """Verifica coherencia de escena."""
        analyzer = RelationshipAnalyzer()

        scene_text = "Juan atacó a Pedro con furia."

        relationships = [
            EntityRelationship(
                source_entity_name="Juan",
                target_entity_name="Pedro",
                relation_type=RelationType.FRIEND,
                intensity=0.8,
                expectations=InferredExpectations(
                    expected_behaviors=["ayuda"],
                    forbidden_behaviors=["atacó"],
                    confidence=0.8,
                ),
            ),
        ]

        alerts = analyzer.check_scene_consistency(
            scene_text,
            relationships,
            chapter=5,
        )

        assert len(alerts) >= 1

    def test_generate_relationship_report(self):
        """Genera reporte de relaciones."""
        analyzer = RelationshipAnalyzer()

        relationships = [
            EntityRelationship(
                source_entity_name="Juan",
                target_entity_name="Pedro",
                relation_type=RelationType.FRIEND,
                intensity=0.9,
            ),
            EntityRelationship(
                source_entity_name="Ana",
                target_entity_name="María",
                relation_type=RelationType.ENEMY,
                intensity=0.8,
            ),
            EntityRelationship(
                source_entity_name="Carlos",
                target_entity_name="Elena",
                relation_type=RelationType.FRIEND,
                intensity=0.5,
            ),
        ]

        report = analyzer.generate_relationship_report(relationships)

        assert report["total_relationships"] == 3
        assert "friend" in report["by_type"]
        assert len(report["by_type"]["friend"]) == 2
        assert len(report["high_intensity_relationships"]) == 2


class TestCoherenceAlert:
    """Tests para CoherenceAlert."""

    def test_create_alert(self):
        """Verifica creación de alerta."""
        alert = CoherenceAlert(
            code="INT_TONE_MISMATCH",
            alert_type="Tono no corresponde",
            severity="warning",
            source_entity="Juan",
            target_entity="Pedro",
            relationship_type="friend",
            explanation="El tono hostil no corresponde con amistad.",
            suggestion="Verificar si hay cambio de relación.",
        )

        assert alert.code == "INT_TONE_MISMATCH"
        assert alert.severity == "warning"

    def test_alert_to_dict(self):
        """Verifica serialización de alerta."""
        alert = CoherenceAlert(
            code="TEST",
            alert_type="Test",
            source_entity="A",
            target_entity="B",
        )
        d = alert.to_dict()
        assert d["code"] == "TEST"
        assert d["source_entity"] == "A"


class TestRelationshipChange:
    """Tests para RelationshipChange."""

    def test_create_change(self):
        """Verifica creación de cambio de relación."""
        change = RelationshipChange(
            relationship_id="rel_123",
            chapter=5,
            change_type="transformed",
            old_relation_type=RelationType.FRIEND,
            new_relation_type=RelationType.ENEMY,
            trigger_text="La traición de Juan cambió todo.",
        )

        assert change.change_type == "transformed"
        assert change.old_relation_type == RelationType.FRIEND
        assert change.new_relation_type == RelationType.ENEMY

    def test_change_to_dict(self):
        """Verifica serialización."""
        change = RelationshipChange(
            relationship_id="r1",
            chapter=3,
            change_type="intensified",
            old_intensity=0.5,
            new_intensity=0.9,
        )
        d = change.to_dict()
        assert d["change_type"] == "intensified"
        assert d["old_intensity"] == 0.5
        assert d["new_intensity"] == 0.9
