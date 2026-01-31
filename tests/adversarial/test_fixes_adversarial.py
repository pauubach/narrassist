"""
Tests adversariales para verificar las correcciones de issues de producción.

Este archivo cubre correcciones específicas hechas para resolver issues
reportados durante testing de producción. Cada test documenta:
1. El issue original
2. La corrección aplicada
3. Casos de regresión para prevenir recurrencias

Issues cubiertos:
- Issue #1: Atributos "algo extraño" clasificados como entidades
- Issue #2-3: Fusión entidades CONCEPT→CHARACTER incorrectas
- Issue #14: Tiempos verbales no conjugados en análisis sensorial
- Issue #19: Exclusiones sensoriales (gusto/disgusto)
- Issue #21: Atributos no procesados correctamente

Autor: Test Adversarial Agent
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional
import re


# =============================================================================
# TEST CASES PARA ISSUE #1: "Algo extraño" como entidad
# =============================================================================

class TestIssue01AlgoExtranoNotEntity:
    """
    Issue #1: Frases genéricas como "algo extraño" se detectaban como entidades.
    
    Corrección: Se añadieron patrones en entity_validator.py para filtrar
    frases indefinidas + adjetivos genéricos.
    """
    
    @pytest.fixture
    def validator_patterns(self) -> list[re.Pattern]:
        """Patrones de NOT_ENTITY_PATTERNS relevantes para este issue."""
        from narrative_assistant.nlp.entity_validator import NOT_ENTITY_PATTERNS
        return [re.compile(p, re.IGNORECASE) for p in NOT_ENTITY_PATTERNS]
    
    GENERIC_PHRASES_TO_REJECT = [
        # algo + adjetivo
        "algo extraño",
        "algo raro",
        "algo diferente",
        "algo especial",
        "algo terrible",
        "algo horrible",
        "algo malo",
        "algo bueno",
        "algo nuevo",
        "algo viejo",
        "algo grande",
        "algo pequeño",
        "algo oscuro",
        "algo claro",
        "algo misterioso",
        "algo sospechoso",
        "algo inquietante",
        "algo inesperado",
        "algo sorprendente",
        # lo + adjetivo sustantivado
        "lo extraño",
        "lo raro",
        "lo peor",
        "lo mejor",
        "lo malo",
        "lo bueno",
        "lo importante",
        "lo difícil",
        "lo fácil",
        "lo curioso",
        "lo interesante",
        "lo terrible",
        "lo horrible",
        "lo posible",
        "lo imposible",
        "lo increíble",
        "lo absurdo",
        "lo lógico",
        "lo normal",
        # eso/esto/aquello + adjetivo
        "eso extraño",
        "esto extraño",
        "aquello extraño",
        "eso raro",
        "esto terrible",
        "aquello horrible",
        # nada/todo + adjetivo  
        "nada extraño",
        "todo extraño",
        "nada especial",
        "todo nuevo",
        # cualquier + sustantivo
        "cualquier cosa",
        "cualquier persona",
        "cualquier lugar",
        "cualquier momento",
        "cualquier día",
        "cualquier forma",
        "cualquier manera",
        "cualquier caso",
    ]
    
    @pytest.mark.parametrize("phrase", GENERIC_PHRASES_TO_REJECT)
    def test_generic_phrase_rejected(self, phrase: str, validator_patterns: list[re.Pattern]):
        """Verificar que frases genéricas son rechazadas por al menos un patrón."""
        matched = any(p.search(phrase) for p in validator_patterns)
        assert matched, f"Frase genérica '{phrase}' debería ser rechazada pero no lo fue"
    
    VALID_ENTITIES_TO_ACCEPT = [
        # Nombres propios reales
        "María Sánchez",
        "Don Quijote",
        "Sancho Panza",
        "El Cid",
        "La Mancha",
        "España",
        "Madrid",
        # Títulos que son personajes
        "El Capitán",
        "La Duquesa",
    ]
    
    @pytest.mark.parametrize("entity", VALID_ENTITIES_TO_ACCEPT)
    def test_valid_entities_not_rejected(self, entity: str, validator_patterns: list[re.Pattern]):
        """Verificar que entidades válidas NO son rechazadas incorrectamente."""
        matched = any(p.search(entity) for p in validator_patterns)
        assert not matched, f"Entidad válida '{entity}' fue rechazada incorrectamente"


# =============================================================================
# TEST CASES PARA ISSUES #2-3: Fusión CONCEPT → CHARACTER incorrecta
# =============================================================================

class TestIssue02_03EntityFusionTypes:
    """
    Issues #2-3: El sistema sugería fusionar CONCEPT con CHARACTER incorrectamente.
    
    Ejemplo: "algo extraño" (CONCEPT) con "María Sánchez" (CHARACTER).
    
    Corrección: Se añadió verificación _looks_like_person_name() en fusion.py
    que valida que ambas entidades parezcan nombres de persona antes de
    sugerir fusión CONCEPT↔CHARACTER.
    """
    
    @pytest.fixture
    def fusion_service(self):
        """Crear servicio de fusión."""
        from narrative_assistant.entities.fusion import EntityFusionService
        return EntityFusionService()
    
    def test_looks_like_person_name_valid(self, fusion_service):
        """Verificar nombres válidos."""
        valid_names = [
            "María",
            "Juan Pérez",
            "Ana María López",
            "Don Quijote",
        ]
        for name in valid_names:
            result = fusion_service._looks_like_person_name(name)
            assert result, f"'{name}' debería parecer nombre de persona"
    
    def test_looks_like_person_name_invalid(self, fusion_service):
        """Verificar que frases genéricas NO parecen nombres."""
        invalid_names = [
            "algo extraño",
            "lo mismo",
            "eso raro",
            "cualquier cosa",
            "nada especial",
            "123 números",
            "esto es una frase muy larga que no puede ser nombre",
        ]
        for phrase in invalid_names:
            result = fusion_service._looks_like_person_name(phrase)
            assert not result, f"'{phrase}' NO debería parecer nombre de persona"
    
    def test_types_compatible_concept_character_with_names(self, fusion_service):
        """Verificar que CONCEPT↔CHARACTER requiere validación de nombre."""
        from narrative_assistant.entities.models import Entity, EntityType
        
        # Caso válido: ambos parecen nombres (NER clasificó mal)
        e1 = Entity(
            id=1, 
            canonical_name="María Sánchez",
            entity_type=EntityType.CHARACTER,
            project_id=1
        )
        e2 = Entity(
            id=2,
            canonical_name="Doña María",
            entity_type=EntityType.CONCEPT,  # NER clasificó mal
            project_id=1
        )
        result = fusion_service._types_compatible_for_entities(e1, e2)
        assert result, "Deberían poder fusionarse si ambos parecen nombres"
        
        # Caso inválido: CONCEPT es frase genérica
        e3 = Entity(
            id=3,
            canonical_name="algo extraño",
            entity_type=EntityType.CONCEPT,
            project_id=1
        )
        result = fusion_service._types_compatible_for_entities(e1, e3)
        assert not result, "NO deberían fusionarse si uno es frase genérica"


# =============================================================================
# TEST CASES PARA ISSUE #14: Tiempos verbales en análisis sensorial
# =============================================================================

class TestIssue14SensoryVerbConjugations:
    """
    Issue #14: El análisis sensorial no detectaba verbos conjugados.
    
    Ejemplo: "degustó" no era detectado, solo "degustar".
    
    Corrección: Se añadieron conjugaciones comunes (pretérito, imperfecto,
    gerundio) a TASTE_KEYWORDS en sensory_report.py.
    """
    
    def test_taste_verb_infinitives_present(self):
        """Verificar que los infinitivos existen."""
        from narrative_assistant.nlp.style.sensory_report import TASTE_KEYWORDS
        
        infinitives = [
            "saborear", "degustar", "paladear", "probar", "catar",
            "tragar", "masticar", "morder", "lamer", "sorber", 
            "beber", "comer"
        ]
        for verb in infinitives:
            assert verb in TASTE_KEYWORDS, f"Infinitivo '{verb}' debe estar en TASTE_KEYWORDS"
    
    def test_taste_verb_preterite_present(self):
        """Verificar que las formas pretéritas existen."""
        from narrative_assistant.nlp.style.sensory_report import TASTE_KEYWORDS
        
        preterites = [
            "saboreó", "degustó", "paladeó", "probó", "cató",
            "tragó", "masticó", "mordió", "lamió", "sorbió",
            "bebió", "comió"
        ]
        for verb in preterites:
            assert verb in TASTE_KEYWORDS, f"Pretérito '{verb}' debe estar en TASTE_KEYWORDS"
    
    def test_taste_verb_imperfect_present(self):
        """Verificar que las formas imperfectas existen."""
        from narrative_assistant.nlp.style.sensory_report import TASTE_KEYWORDS
        
        imperfects = [
            "saboreaba", "degustaba", "paladeaba", "probaba", "cataba",
            "tragaba", "masticaba", "mordía", "lamía", "sorbía",
            "bebía", "comía"
        ]
        for verb in imperfects:
            assert verb in TASTE_KEYWORDS, f"Imperfecto '{verb}' debe estar en TASTE_KEYWORDS"
    
    def test_taste_verb_gerund_present(self):
        """Verificar que al menos un gerundio existe."""
        from narrative_assistant.nlp.style.sensory_report import TASTE_KEYWORDS
        
        assert "degustando" in TASTE_KEYWORDS, "Gerundio 'degustando' debe estar"


# =============================================================================
# TEST CASES PARA ISSUE #19: Exclusiones sensoriales (gusto ≠ sabor)
# =============================================================================

class TestIssue19SensoryExclusions:
    """
    Issue #19: "Con gusto" se detectaba como sensorial (sabor) cuando
    realmente significa "placer/agrado".
    
    Corrección: Se añadieron SENSE_EXCLUSION_PATTERNS y SENSE_EXCLUSIONS
    en sensory_report.py para filtrar usos metafóricos.
    """
    
    def test_exclusion_patterns_exist(self):
        """Verificar que existen patrones de exclusión."""
        from narrative_assistant.nlp.style.sensory_report import SENSE_EXCLUSION_PATTERNS
        assert len(SENSE_EXCLUSION_PATTERNS) > 0, "Debe haber patrones de exclusión"
    
    def test_exclusion_set_exists(self):
        """Verificar que existe el set de exclusiones."""
        from narrative_assistant.nlp.style.sensory_report import SENSE_EXCLUSIONS
        assert isinstance(SENSE_EXCLUSIONS, set), "SENSE_EXCLUSIONS debe ser un set"
    
    PHRASES_TO_EXCLUDE = [
        "con gusto",
        "con mucho gusto",
        "a gusto",
        "a disgusto",
        "gustosamente",
        "gustoso",
        "gustosa",
        "gustosos",
        "gustosas",
        "disgustado",
        "disgustada",
        "de buen gusto",
        "de mal gusto",
    ]
    
    @pytest.mark.parametrize("phrase", PHRASES_TO_EXCLUDE)
    def test_phrase_matched_by_exclusion_pattern(self, phrase: str):
        """Verificar que la frase es capturada por al menos un patrón de exclusión."""
        from narrative_assistant.nlp.style.sensory_report import SENSE_EXCLUSION_PATTERNS
        
        matched = any(p.search(phrase) for p in SENSE_EXCLUSION_PATTERNS)
        assert matched, f"'{phrase}' debería ser excluido pero no lo fue"
    
    SENSORY_TASTE_PHRASES = [
        "sabor dulce",
        "degustó el vino",
        "paladeó el chocolate",
        "masticó lentamente",
    ]
    
    @pytest.mark.parametrize("phrase", SENSORY_TASTE_PHRASES)
    def test_real_taste_not_excluded(self, phrase: str):
        """Verificar que referencias reales al gusto NO son excluidas."""
        from narrative_assistant.nlp.style.sensory_report import SENSE_EXCLUSION_PATTERNS
        
        matched = any(p.search(phrase) for p in SENSE_EXCLUSION_PATTERNS)
        assert not matched, f"'{phrase}' es referencia real al sabor, no debería ser excluida"


# =============================================================================
# TEST CASES PARA ISSUE #21: LanguageTool disabled_rules
# =============================================================================

class TestIssue21LanguageToolDisabledRules:
    """
    Issue #21: LanguageTool reportaba falsos positivos con conjunciones
    repetidas (y...y, que...que) que son válidas en español literario.
    
    Corrección: Se añadió DEFAULT_DISABLED_RULES en voting_checker.py
    y parámetro disabled_rules al constructor de LanguageToolVoter.
    """
    
    def test_default_disabled_rules_exist(self):
        """Verificar que existen reglas deshabilitadas por defecto."""
        from narrative_assistant.nlp.orthography.voting_checker import LanguageToolVoter
        
        expected_rules = [
            "SPANISH_WORD_REPEAT_RULE",
            "WORD_REPEAT_RULE",
            "MORFOLOGIK_RULE_ES",
        ]
        for rule in expected_rules:
            assert rule in LanguageToolVoter.DEFAULT_DISABLED_RULES, \
                f"Regla '{rule}' debe estar en DEFAULT_DISABLED_RULES"
    
    def test_voter_accepts_custom_disabled_rules(self):
        """Verificar que el constructor acepta reglas personalizadas."""
        from narrative_assistant.nlp.orthography.voting_checker import LanguageToolVoter
        
        custom_rules = ["CUSTOM_RULE_1", "CUSTOM_RULE_2"]
        voter = LanguageToolVoter(disabled_rules=custom_rules)
        assert voter._disabled_rules == custom_rules
    
    def test_voter_uses_defaults_when_none(self):
        """Verificar que usa defaults cuando no se especifican reglas."""
        from narrative_assistant.nlp.orthography.voting_checker import LanguageToolVoter
        
        voter = LanguageToolVoter(disabled_rules=None)
        assert voter._disabled_rules == LanguageToolVoter.DEFAULT_DISABLED_RULES


# =============================================================================
# TEST CASES PARA LOGGING EN RELATIONSHIPS (Issues #5, #8 prep)
# =============================================================================

class TestRelationshipsLogging:
    """
    Preparación para Issues #5 y #8: Verificar que el logging está configurado
    correctamente para diagnosticar problemas de relaciones y timeline.
    
    Estos tests solo verifican que las funciones de logging existen y se
    pueden llamar sin errores.
    """
    
    def test_unified_analysis_has_relationships_logging(self):
        """Verificar que el código de relaciones tiene logging."""
        import inspect
        from narrative_assistant.pipelines.unified_analysis import UnifiedAnalysisPipeline
        
        source = inspect.getsource(UnifiedAnalysisPipeline._extract_relationships)
        assert "[RELATIONSHIPS]" in source, \
            "_extract_relationships debe tener logging con prefijo [RELATIONSHIPS]"
    
    def test_timeline_has_logging(self):
        """Verificar que el código de timeline tiene logging."""
        import inspect
        from narrative_assistant.temporal.timeline import TimelineBuilder
        
        source = inspect.getsource(TimelineBuilder._detect_narrative_order)
        assert "[TIMELINE]" in source, \
            "_detect_narrative_order debe tener logging con prefijo [TIMELINE]"


# =============================================================================
# TEST CASES PARA CHAPTER_SUMMARY (column name fix)
# =============================================================================

class TestChapterSummaryColumnNames:
    """
    Corrección: Las columnas de interactions eran from_entity_id/to_entity_id
    pero la tabla usa entity1_id/entity2_id.
    
    Este test verifica que las queries usan los nombres correctos.
    """
    
    def test_correct_column_names_in_source(self):
        """Verificar que el código usa entity1_id y entity2_id."""
        import inspect
        from narrative_assistant.analysis.chapter_summary import ChapterSummaryAnalyzer
        
        source = inspect.getsource(ChapterSummaryAnalyzer)
        
        # Debe usar entity1_id y entity2_id
        assert "entity1_id" in source, "Debe usar entity1_id"
        assert "entity2_id" in source, "Debe usar entity2_id"
        
        # No debe usar from_entity_id en queries (excepto como alias)
        # El código usa "i.entity1_id" en la query, no "i.from_entity_id"
        # Verificamos que la query SQL correcta está presente
        assert "i.entity1_id = e1.id" in source or "i.entity1_id" in source


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegrationValidatorPatterns:
    """Tests de integración para validación de entidades."""
    
    def test_validator_not_entity_patterns_compile(self):
        """Verificar que todos los patrones compilan sin errores."""
        from narrative_assistant.nlp.entity_validator import NOT_ENTITY_PATTERNS
        
        for i, pattern in enumerate(NOT_ENTITY_PATTERNS):
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Pattern {i} failed to compile: {pattern}\nError: {e}")
    
    def test_sensory_exclusion_patterns_compile(self):
        """Verificar que los patrones sensoriales compilan."""
        from narrative_assistant.nlp.style.sensory_report import SENSE_EXCLUSION_PATTERNS
        
        # Los patrones ya están compilados, verificar que son válidos
        for i, pattern in enumerate(SENSE_EXCLUSION_PATTERNS):
            assert hasattr(pattern, 'search'), \
                f"Pattern {i} debe ser un patrón regex compilado"


# =============================================================================
# REGRESSION TESTS: Verificar que fixes no rompen funcionalidad existente
# =============================================================================

class TestRegressionEntityValidation:
    """Tests de regresión para validación de entidades."""
    
    SHOULD_BE_VALID_ENTITIES = [
        # Nombres españoles comunes
        "María",
        "Juan",
        "José Antonio",
        "María del Carmen",
        # Nombres con títulos
        "Don Quijote",
        "Doña Juana",
        "El Cid",
        "La Celestina",
        # Lugares
        "España",
        "Madrid",
        "La Mancha",
        "Sierra Nevada",
        # Organizaciones
        "La Corona",
        "El Imperio",
    ]
    
    @pytest.mark.parametrize("entity", SHOULD_BE_VALID_ENTITIES)
    def test_valid_entities_pass_validation(self, entity: str):
        """Verificar que entidades válidas pasan validación."""
        from narrative_assistant.nlp.entity_validator import NOT_ENTITY_PATTERNS
        
        patterns = [re.compile(p, re.IGNORECASE) for p in NOT_ENTITY_PATTERNS]
        matched = any(p.search(entity) for p in patterns)
        
        assert not matched, f"Entidad válida '{entity}' fue rechazada incorrectamente"


class TestRegressionSensoryAnalysis:
    """Tests de regresión para análisis sensorial."""
    
    def test_sensory_types_all_present(self):
        """Verificar que todos los tipos sensoriales están definidos."""
        from narrative_assistant.nlp.style.sensory_report import (
            SensoryType, SENSE_KEYWORDS, SENSE_NAMES
        )
        
        expected_senses = [
            SensoryType.SIGHT,
            SensoryType.HEARING,  # No SOUND
            SensoryType.SMELL,
            SensoryType.TASTE,
            SensoryType.TOUCH,
        ]
        
        for sense in expected_senses:
            assert sense in SENSE_KEYWORDS, f"{sense} debe estar en SENSE_KEYWORDS"
            assert sense in SENSE_NAMES, f"{sense} debe estar en SENSE_NAMES"


class TestRegressionFusion:
    """Tests de regresión para fusión de entidades."""
    
    def test_same_type_always_compatible(self):
        """Verificar que mismo tipo siempre es compatible."""
        from narrative_assistant.entities.fusion import EntityFusionService
        from narrative_assistant.entities.models import EntityType
        
        service = EntityFusionService()
        
        for entity_type in EntityType:
            result = service._types_compatible(entity_type, entity_type)
            assert result, f"Mismo tipo {entity_type} debe ser compatible consigo mismo"
    
    def test_character_concept_compatible(self):
        """Verificar que CHARACTER y CONCEPT pueden ser compatibles."""
        from narrative_assistant.entities.fusion import EntityFusionService
        from narrative_assistant.entities.models import EntityType
        
        service = EntityFusionService()
        
        # La compatibilidad básica debe permitirlo
        result = service._types_compatible(EntityType.CHARACTER, EntityType.CONCEPT)
        assert result, "CHARACTER y CONCEPT deben ser compatibles a nivel de tipo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
