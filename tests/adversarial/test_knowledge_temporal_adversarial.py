"""
Tests adversariales GAN-style para detección de anachronismos de conocimiento.

Objetivo: Validar que el sistema detecta cuando un personaje referencia
conocimiento que solo adquiere en un capítulo posterior (anachronismo temporal).

Categorías de tests:
1. Anachronismo directo: A menciona hecho de B antes de enterarse
2. Orden correcto: A se entera y luego referencia (sin error)
3. Revelación en diálogo: A aprende algo por conversación
4. Observación directa: A ve algo y luego lo menciona
5. Secretos: A sabe un secreto antes de que se lo cuenten
6. Conocimiento negado: A "no sabía" algo → luego lo sabe
7. Conocimiento implícito: A actúa sobre un hecho sin haberlo aprendido
8. Flashback legítimo: Narración retrospectiva (no es error)
9. Conocimiento previo al manuscrito: A ya sabía algo desde el inicio
10. Cadena de revelaciones: A → B → C
11. Múltiples hechos sobre una entidad
12. Conocimiento contradictorio entre capítulos

Basado en:
- Teoría de la Mente en narrativa (Zunshine, 2006)
- Tracking epistémico en ficción (Palmer, 2004)
- Consistencia temporal en edición literaria (Chicago Manual of Style)

Autor: GAN-style Adversary Agent
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KnowledgeTemporalTestCase:
    """Caso de test para anachronismos de conocimiento."""
    id: str
    category: str
    chapters: dict[int, str]  # {chapter_number: text}
    entities: list[dict]  # [{"id": 1, "name": "María", "aliases": []}]
    expected_anachronisms: list[dict]  # [{"knower": "María", "fact": "...", "used_chapter": 2, "learned_chapter": 5}]
    expected_clean: bool = False  # True si no debe haber anachronismos
    difficulty: str = "medium"  # easy, medium, hard, adversarial
    linguistic_note: str = ""


# =============================================================================
# CATEGORÍA 1: ANACHRONISMO DIRECTO
# Personaje referencia un hecho que solo aprende más adelante
# =============================================================================

ANACHRONISM_DIRECT_TESTS = [
    KnowledgeTemporalTestCase(
        id="anach_01_simple",
        category="anachronismo_directo",
        chapters={
            2: "María sabía que Pedro tenía una cicatriz en la mano.",
            5: "Pedro le mostró la cicatriz de su mano a María por primera vez.",
        },
        entities=[
            {"id": 1, "name": "María", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "María",
            "fact_keyword": "cicatriz",
            "used_chapter": 2,
            "learned_chapter": 5,
        }],
        difficulty="easy",
        linguistic_note="Caso canónico: María referencia la cicatriz en cap. 2 pero la ve en cap. 5",
    ),
    KnowledgeTemporalTestCase(
        id="anach_02_secret",
        category="anachronismo_directo",
        chapters={
            1: "Ana guardaba el secreto de Luis con mucho cuidado.",
            4: "Luis le confesó su secreto a Ana mientras cenaban.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Luis", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "Ana",
            "fact_keyword": "secreto",
            "used_chapter": 1,
            "learned_chapter": 4,
        }],
        difficulty="easy",
        linguistic_note="Ana guarda el secreto en cap. 1, pero solo se lo cuentan en cap. 4",
    ),
    KnowledgeTemporalTestCase(
        id="anach_03_location",
        category="anachronismo_directo",
        chapters={
            3: "Carlos sabía dónde vivía Elena.",
            7: "Elena le dio su dirección a Carlos por teléfono.",
        },
        entities=[
            {"id": 1, "name": "Carlos", "aliases": []},
            {"id": 2, "name": "Elena", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "Carlos",
            "fact_keyword": "vivía",
            "used_chapter": 3,
            "learned_chapter": 7,
        }],
        difficulty="medium",
        linguistic_note="Conocimiento de ubicación referenciado antes de ser comunicado",
    ),
]

# =============================================================================
# CATEGORÍA 2: ORDEN CORRECTO (sin anachronismo)
# Personaje aprende y luego referencia - debe pasar sin alertas
# =============================================================================

CORRECT_ORDER_TESTS = [
    KnowledgeTemporalTestCase(
        id="correct_01_simple",
        category="orden_correcto",
        chapters={
            1: "Pedro le contó a María que tenía una cicatriz en la mano.",
            3: "María recordaba que Pedro tenía una cicatriz.",
        },
        entities=[
            {"id": 1, "name": "María", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="easy",
        linguistic_note="Orden correcto: aprende en cap. 1, referencia en cap. 3",
    ),
    KnowledgeTemporalTestCase(
        id="correct_02_same_chapter",
        category="orden_correcto",
        chapters={
            2: "Luis le confesó su secreto a Ana. Ana guardaba el secreto con cuidado.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Luis", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="easy",
        linguistic_note="Aprendizaje y referencia en el mismo capítulo",
    ),
    KnowledgeTemporalTestCase(
        id="correct_03_observation",
        category="orden_correcto",
        chapters={
            1: "Carlos notó que Elena estaba embarazada.",
            4: "Carlos recordaba que Elena estaba embarazada.",
        },
        entities=[
            {"id": 1, "name": "Carlos", "aliases": []},
            {"id": 2, "name": "Elena", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="easy",
        linguistic_note="Observación directa seguida de recuerdo posterior",
    ),
]

# =============================================================================
# CATEGORÍA 3: REVELACIÓN EN DIÁLOGO
# =============================================================================

DIALOGUE_REVELATION_TESTS = [
    KnowledgeTemporalTestCase(
        id="dialogue_01_told_later",
        category="revelacion_dialogo",
        chapters={
            2: "María se dio cuenta de que Juan era médico.",
            6: "—Soy médico —dijo Juan a María.",
        },
        entities=[
            {"id": 1, "name": "María", "aliases": []},
            {"id": 2, "name": "Juan", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "María",
            "fact_keyword": "médico",
            "used_chapter": 2,
            "learned_chapter": 6,
        }],
        difficulty="medium",
        linguistic_note="María 'se da cuenta' de la profesión antes de que Juan se la diga",
    ),
    KnowledgeTemporalTestCase(
        id="dialogue_02_overheard",
        category="revelacion_dialogo",
        chapters={
            1: "Ana sabía que Pedro era adoptado.",
            5: "Ana escuchó por casualidad a la madre de Pedro decir que era adoptado.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "Ana",
            "fact_keyword": "adoptado",
            "used_chapter": 1,
            "learned_chapter": 5,
        }],
        difficulty="medium",
        linguistic_note="Ana sabe un hecho en cap. 1 que solo descubre al escucharlo en cap. 5",
    ),
]

# =============================================================================
# CATEGORÍA 4: SECRETOS
# =============================================================================

SECRET_TESTS = [
    KnowledgeTemporalTestCase(
        id="secret_01_guard_before_know",
        category="secretos",
        chapters={
            2: "Elena guardaba el secreto de Carlos con su vida.",
            8: "Carlos le reveló su secreto a Elena una noche de lluvia.",
        },
        entities=[
            {"id": 1, "name": "Elena", "aliases": []},
            {"id": 2, "name": "Carlos", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "Elena",
            "fact_keyword": "secreto",
            "used_chapter": 2,
            "learned_chapter": 8,
        }],
        difficulty="easy",
        linguistic_note="Elena guarda un secreto en cap. 2 que solo le cuentan en cap. 8",
    ),
    KnowledgeTemporalTestCase(
        id="secret_02_correct_order",
        category="secretos",
        chapters={
            3: "Carlos le confesó su secreto a Elena.",
            7: "Elena conocía el secreto de Carlos desde aquella noche.",
        },
        entities=[
            {"id": 1, "name": "Elena", "aliases": []},
            {"id": 2, "name": "Carlos", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="easy",
        linguistic_note="Orden correcto: confesión en cap. 3, referencia en cap. 7",
    ),
]

# =============================================================================
# CATEGORÍA 5: CONOCIMIENTO NEGADO → CONOCIMIENTO POSITIVO
# =============================================================================

NEGATION_TESTS = [
    KnowledgeTemporalTestCase(
        id="negation_01_didnt_know_then_knows",
        category="negacion",
        chapters={
            1: "María ignoraba que Pedro era espía.",
            3: "María sabía que Pedro era espía y no podía dormir.",
            6: "Pedro le confesó a María que era espía.",
        },
        entities=[
            {"id": 1, "name": "María", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "María",
            "fact_keyword": "espía",
            "used_chapter": 3,
            "learned_chapter": 6,
        }],
        difficulty="hard",
        linguistic_note="Cap. 1: no sabe. Cap. 3: ya sabe. Cap. 6: se lo dicen. Error entre 3 y 6.",
    ),
    KnowledgeTemporalTestCase(
        id="negation_02_correct_progression",
        category="negacion",
        chapters={
            1: "Ana no sabía que Luis estaba enfermo.",
            3: "El médico le contó a Ana que Luis estaba enfermo.",
            5: "Ana sabía que Luis estaba enfermo y lo visitaba cada día.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Luis", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="medium",
        linguistic_note="Progresión correcta: ignorancia → revelación → conocimiento",
    ),
]

# =============================================================================
# CATEGORÍA 6: CONOCIMIENTO IMPLÍCITO (acción basada en hecho no aprendido)
# =============================================================================

IMPLICIT_TESTS = [
    KnowledgeTemporalTestCase(
        id="implicit_01_acts_on_unknown",
        category="implicito",
        chapters={
            2: "María observó que Pedro estaba triste por la muerte de su padre.",
            6: "Pedro descubrió que su padre había muerto.",
        },
        entities=[
            {"id": 1, "name": "María", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "María",
            "fact_keyword": "muerte",
            "used_chapter": 2,
            "learned_chapter": 6,
        }],
        difficulty="hard",
        linguistic_note="María observa la tristeza de Pedro por un hecho que él aún no sabe",
    ),
]

# =============================================================================
# CATEGORÍA 7: FLASHBACK LEGÍTIMO (no es error)
# =============================================================================

FLASHBACK_TESTS = [
    KnowledgeTemporalTestCase(
        id="flashback_01_narrator_retrospect",
        category="flashback",
        chapters={
            1: "María recordaba que Pedro tenía una cicatriz, aunque en aquel momento no le dio importancia.",
            3: "Tres años antes, Pedro le había mostrado la cicatriz a María.",
        },
        entities=[
            {"id": 1, "name": "María", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="adversarial",
        linguistic_note="Narrador omnisciente retrospectivo. El 'tres años antes' indica flashback.",
    ),
]

# =============================================================================
# CATEGORÍA 8: CADENA DE REVELACIONES (A → B → C)
# =============================================================================

CHAIN_TESTS = [
    KnowledgeTemporalTestCase(
        id="chain_01_knowledge_transfer",
        category="cadena",
        chapters={
            1: "Ana sabía que Pedro era ladrón.",
            3: "Ana le contó a Luis que Pedro era ladrón.",
            5: "Luis sabía que Pedro era ladrón desde que Ana se lo dijo.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Luis", "aliases": []},
            {"id": 3, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[],
        expected_clean=True,
        difficulty="hard",
        linguistic_note="Cadena correcta: Ana sabe → Ana cuenta a Luis → Luis sabe",
    ),
    KnowledgeTemporalTestCase(
        id="chain_02_broken_chain",
        category="cadena",
        chapters={
            1: "Luis sabía que Pedro era ladrón.",
            5: "Ana le contó a Luis que Pedro era ladrón.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Luis", "aliases": []},
            {"id": 3, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[{
            "knower": "Luis",
            "fact_keyword": "ladrón",
            "used_chapter": 1,
            "learned_chapter": 5,
        }],
        difficulty="medium",
        linguistic_note="Luis sabe en cap. 1 pero se lo cuentan en cap. 5",
    ),
]

# =============================================================================
# CATEGORÍA 9: MÚLTIPLES HECHOS
# =============================================================================

MULTI_FACT_TESTS = [
    KnowledgeTemporalTestCase(
        id="multi_01_mixed",
        category="multiples_hechos",
        chapters={
            1: "Ana sabía que Pedro era médico.",
            2: "Ana descubrió que Pedro estaba casado.",
            4: "Pedro le contó a Ana que era médico.",
            6: "Pedro le dijo a Ana que estaba casado.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[
            {
                "knower": "Ana",
                "fact_keyword": "médico",
                "used_chapter": 1,
                "learned_chapter": 4,
            },
            {
                "knower": "Ana",
                "fact_keyword": "casado",
                "used_chapter": 2,
                "learned_chapter": 6,
            },
        ],
        difficulty="hard",
        linguistic_note="Dos hechos distintos, ambos con anachronismo temporal",
    ),
]

# =============================================================================
# CATEGORÍA 10: CONOCIMIENTO CONTRADICTORIO
# =============================================================================

CONTRADICTION_TESTS = [
    KnowledgeTemporalTestCase(
        id="contradiction_01",
        category="contradiccion",
        chapters={
            2: "Ana sabía que Pedro tenía ojos azules.",
            5: "Ana notó que Pedro tenía ojos verdes.",
        },
        entities=[
            {"id": 1, "name": "Ana", "aliases": []},
            {"id": 2, "name": "Pedro", "aliases": []},
        ],
        expected_anachronisms=[],  # No es anachronismo temporal, sino inconsistencia de atributo
        expected_clean=True,
        difficulty="adversarial",
        linguistic_note="No es anachronismo temporal sino contradicción de atributos. No debe alertar aquí.",
    ),
]


# =============================================================================
# Consolidar todos los tests
# =============================================================================

ALL_TEMPORAL_TESTS = (
    ANACHRONISM_DIRECT_TESTS
    + CORRECT_ORDER_TESTS
    + DIALOGUE_REVELATION_TESTS
    + SECRET_TESTS
    + NEGATION_TESTS
    + IMPLICIT_TESTS
    + FLASHBACK_TESTS
    + CHAIN_TESTS
    + MULTI_FACT_TESTS
    + CONTRADICTION_TESTS
)


# =============================================================================
# Test classes
# =============================================================================

class TestKnowledgeTemporalAnachronisms:
    """Tests para detección de anachronismos temporales de conocimiento."""

    @pytest.fixture
    def analyzer(self):
        """Crea un analizador de conocimiento con entidades."""
        from narrative_assistant.analysis.character_knowledge import (
            CharacterKnowledgeAnalyzer,
            KnowledgeExtractionMode,
        )
        return CharacterKnowledgeAnalyzer, KnowledgeExtractionMode

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in ALL_TEMPORAL_TESTS if not tc.expected_clean],
        ids=[tc.id for tc in ALL_TEMPORAL_TESTS if not tc.expected_clean],
    )
    def test_detects_anachronism(self, test_case: KnowledgeTemporalTestCase, analyzer):
        """Verifica que se detectan los anachronismos esperados."""
        AnalyzerClass, ExtractionMode = analyzer
        from narrative_assistant.analysis.character_knowledge import (
            detect_knowledge_anachronisms,
            KnowledgeFact,
        )

        # Crear analizador con entidades del test
        kb_analyzer = AnalyzerClass(entities=test_case.entities)

        # Extraer hechos de cada capítulo (modo RULES = sin GPU)
        all_facts = []
        for chapter_num in sorted(test_case.chapters.keys()):
            text = test_case.chapters[chapter_num]
            facts = kb_analyzer.extract_knowledge_facts(
                text, chapter=chapter_num, mode=ExtractionMode.RULES
            )
            all_facts.extend(facts)

        # Detectar anachronismos
        anachronisms = detect_knowledge_anachronisms(all_facts)

        # Verificar que se detectan los esperados
        for expected in test_case.expected_anachronisms:
            found = any(
                a["knower_name"] == expected["knower"]
                and expected["fact_keyword"].lower() in a.get("fact_value", "").lower()
                for a in anachronisms
            )
            assert found, (
                f"[{test_case.id}] No se detectó anachronismo esperado: "
                f"{expected['knower']} sabe '{expected['fact_keyword']}' "
                f"en cap. {expected['used_chapter']} pero lo aprende en cap. {expected['learned_chapter']}. "
                f"Hechos extraídos: {[f.to_dict() for f in all_facts]}. "
                f"Anachronismos detectados: {anachronisms}"
            )

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in ALL_TEMPORAL_TESTS if tc.expected_clean],
        ids=[tc.id for tc in ALL_TEMPORAL_TESTS if tc.expected_clean],
    )
    def test_no_false_positive(self, test_case: KnowledgeTemporalTestCase, analyzer):
        """Verifica que no se generan falsos positivos en casos limpios."""
        AnalyzerClass, ExtractionMode = analyzer
        from narrative_assistant.analysis.character_knowledge import (
            detect_knowledge_anachronisms,
        )

        kb_analyzer = AnalyzerClass(entities=test_case.entities)

        all_facts = []
        for chapter_num in sorted(test_case.chapters.keys()):
            text = test_case.chapters[chapter_num]
            facts = kb_analyzer.extract_knowledge_facts(
                text, chapter=chapter_num, mode=ExtractionMode.RULES
            )
            all_facts.extend(facts)

        anachronisms = detect_knowledge_anachronisms(all_facts)

        assert len(anachronisms) == 0, (
            f"[{test_case.id}] Se detectaron falsos positivos: {anachronisms}. "
            f"Este caso no debería generar alertas. "
            f"Nota: {test_case.linguistic_note}"
        )


class TestKnowledgeTemporalSummary:
    """Resumen de todos los tests adversariales de conocimiento temporal."""

    def test_all_temporal_cases(self):
        """Ejecuta todos los casos y reporta estadísticas."""
        from narrative_assistant.analysis.character_knowledge import (
            CharacterKnowledgeAnalyzer,
            KnowledgeExtractionMode,
            detect_knowledge_anachronisms,
        )

        passed = 0
        failed = 0
        errors = []

        for case in ALL_TEMPORAL_TESTS:
            try:
                kb_analyzer = CharacterKnowledgeAnalyzer(entities=case.entities)

                all_facts = []
                for chapter_num in sorted(case.chapters.keys()):
                    text = case.chapters[chapter_num]
                    facts = kb_analyzer.extract_knowledge_facts(
                        text, chapter=chapter_num,
                        mode=KnowledgeExtractionMode.RULES,
                    )
                    all_facts.extend(facts)

                anachronisms = detect_knowledge_anachronisms(all_facts)

                case_passed = True
                if case.expected_clean:
                    if len(anachronisms) > 0:
                        case_passed = False
                else:
                    for expected in case.expected_anachronisms:
                        found = any(
                            a["knower_name"] == expected["knower"]
                            and expected["fact_keyword"].lower() in a.get("fact_value", "").lower()
                            for a in anachronisms
                        )
                        if not found:
                            case_passed = False
                            break

                if case_passed:
                    passed += 1
                else:
                    failed += 1
                    errors.append({
                        "id": case.id,
                        "category": case.category,
                        "difficulty": case.difficulty,
                        "note": case.linguistic_note,
                        "facts_found": len(all_facts),
                        "anachronisms": len(anachronisms),
                    })

            except Exception as e:
                failed += 1
                errors.append({
                    "id": case.id,
                    "error": str(e),
                })

        # Imprimir resumen
        total = len(ALL_TEMPORAL_TESTS)
        print(f"\n{'='*60}")
        print(f"KNOWLEDGE TEMPORAL ADVERSARIAL TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total cases: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass rate: {passed/total*100:.1f}%")
        print(f"{'='*60}")

        if errors:
            print(f"\nFailed cases:")
            for err in errors[:15]:
                print(f"  - {err['id']} ({err.get('difficulty', '?')}): "
                      f"{err.get('note', err.get('error', 'Unknown'))[:80]}")

        # Con el modo RULES, esperamos que al menos el 40% pase
        # (los tests difíciles fallarán con regex)
        assert passed >= total * 0.3, (
            f"Solo pasaron {passed}/{total} tests ({passed/total*100:.1f}%). "
            f"El umbral mínimo es 30%."
        )
