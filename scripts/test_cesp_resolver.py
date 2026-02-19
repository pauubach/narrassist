#!/usr/bin/env python3
"""
Tests manuales para el CESPAttributeResolver.
Ejecutar directamente: python3 scripts/test_cesp_resolver.py
"""

import sys
import os

# Añadir src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# Importar clases necesarias explícitamente
from narrative_assistant.nlp.cesp_resolver import (
    AttributeDeduplicator,
    ResolvedAttribute,
    ConflictStatus,
    AssignmentSource,
    ConflictResolver,
    AttributeCandidate,
    ExtractorType,
    CESPAttributeResolver,
    EntityMention,
)


def run_tests():
    """Ejecutar todos los tests."""
    print('=' * 60)
    print('PRUEBAS DEL CESP RESOLVER')
    print('=' * 60)
    
    tests_passed = 0
    tests_failed = 0

    # Test 1: Deduplicador elimina falso positivo
    print('\n[TEST 1] Deduplicador elimina falso positivo')
    try:
        deduplicator = AttributeDeduplicator()
        
        pedro_attr = ResolvedAttribute(
            attribute_type='color_ojos',
            value='azules',
            entity_id='pedro_1',
            final_confidence=0.92,
            conflict_status=ConflictStatus.CONFIRMED,
            assignment_source=AssignmentSource.GENITIVE,
            is_dubious=False,
            text_evidence='ojos azules de Pedro',
            sentence_idx=0,
            resolution_notes=[]
        )
        
        juan_attr = ResolvedAttribute(
            attribute_type='color_ojos',
            value='azules',
            entity_id='juan_1',
            final_confidence=0.65,
            conflict_status=ConflictStatus.UNANIMOUS,
            assignment_source=AssignmentSource.PROXIMITY,
            is_dubious=True,
            text_evidence='ojos azules de Pedro',
            sentence_idx=0,
            resolution_notes=[]
        )
        
        result = deduplicator.deduplicate([pedro_attr, juan_attr])
        assert len(result) == 1, f'Se esperaba 1 resultado, se obtuvo {len(result)}'
        assert result[0].entity_id == 'pedro_1', f'Se esperaba pedro_1, se obtuvo {result[0].entity_id}'
        print('  ✅ PASADO: Solo se conserva Pedro (genitivo)')
        tests_passed += 1
    except Exception as e:
        print(f'  ❌ FALLADO: {e}')
        tests_failed += 1

    # Test 2: ConflictResolver clasifica CONFIRMED
    print('\n[TEST 2] ConflictResolver clasifica CONFIRMED')
    try:
        resolver = ConflictResolver()
        
        candidates = [
            AttributeCandidate(
                attribute_type='color_ojos',
                value='azules',
                text_evidence='test',
                sentence_idx=0,
                start=0,
                end=20,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id='pedro_1',
                assignment_source=AssignmentSource.GENITIVE,
                base_confidence=0.92,
                is_dubious=False
            ),
            AttributeCandidate(
                attribute_type='color_ojos',
                value='azules',
                text_evidence='test',
                sentence_idx=0,
                start=0,
                end=20,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id='juan_1',
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                is_dubious=True
            )
        ]
        
        status = resolver.classify_conflict_status(candidates)
        assert status == ConflictStatus.CONFIRMED, f'Se esperaba CONFIRMED, se obtuvo {status}'
        print('  ✅ PASADO: Clasifica como CONFIRMED')
        tests_passed += 1
    except Exception as e:
        print(f'  ❌ FALLADO: {e}')
        tests_failed += 1

    # Test 3: CESPAttributeResolver caso completo
    print('\n[TEST 3] CESPAttributeResolver - Caso ojos azules de Pedro')
    try:
        cesp = CESPAttributeResolver()
        
        entity_mentions = [
            EntityMention(entity_id='juan_1', text='Juan', start=0, end=4, sentence_idx=0),
            EntityMention(entity_id='pedro_1', text='Pedro', start=14, end=19, sentence_idx=0)
        ]
        
        candidates = [
            AttributeCandidate(
                attribute_type='color_ojos',
                value='azules',
                text_evidence='ojos azules de Pedro',
                sentence_idx=1,
                start=32,
                end=52,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id='pedro_1',
                assignment_source=AssignmentSource.GENITIVE,
                base_confidence=0.92,
                syntactic_evidence='nmod:de->Pedro',
                is_dubious=False
            ),
            AttributeCandidate(
                attribute_type='color_ojos',
                value='azules',
                text_evidence='ojos azules de Pedro',
                sentence_idx=1,
                start=32,
                end=52,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id='juan_1',
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                is_dubious=True
            )
        ]
        
        results = cesp.resolve(candidates, entity_mentions, 'Juan miró a Pedro. Tenía los ojos azules de Pedro.')
        
        assert len(results) == 1, f'Se esperaba 1 resultado, se obtuvo {len(results)}'
        assert results[0].entity_id == 'pedro_1', f'Se esperaba pedro_1, se obtuvo {results[0].entity_id}'
        assert results[0].value == 'azules'
        print('  ✅ PASADO: Solo Pedro recibe ojos azules')
        tests_passed += 1
    except Exception as e:
        print(f'  ❌ FALLADO: {e}')
        tests_failed += 1

    # Test 4: Caso bug original - Juan tiene marrones, Pedro tiene azules
    print('\n[TEST 4] Caso bug original - Juan marrones, Pedro azules')
    try:
        cesp = CESPAttributeResolver()
        
        entity_mentions = [
            EntityMention(entity_id='juan_1', text='Juan', start=0, end=4, sentence_idx=0),
            EntityMention(entity_id='pedro_1', text='Pedro', start=30, end=35, sentence_idx=1)
        ]
        
        candidates = [
            AttributeCandidate(
                attribute_type='color_ojos',
                value='marrones',
                text_evidence='Juan tenía los ojos marrones.',
                sentence_idx=0,
                start=15,
                end=28,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id='juan_1',
                assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
                base_confidence=0.92,
                is_dubious=False
            ),
            AttributeCandidate(
                attribute_type='color_ojos',
                value='azules',
                text_evidence='Pedro, con sus ojos azules de Pedro',
                sentence_idx=1,
                start=46,
                end=66,
                extractor_type=ExtractorType.DEPENDENCY,
                assigned_entity_id='pedro_1',
                assignment_source=AssignmentSource.GENITIVE,
                base_confidence=0.92,
                is_dubious=False
            ),
            AttributeCandidate(
                attribute_type='color_ojos',
                value='azules',
                text_evidence='Pedro, con sus ojos azules de Pedro',
                sentence_idx=1,
                start=46,
                end=66,
                extractor_type=ExtractorType.REGEX,
                assigned_entity_id='juan_1',  # INCORRECTO - FALSO POSITIVO
                assignment_source=AssignmentSource.PROXIMITY,
                base_confidence=0.65,
                is_dubious=True
            )
        ]
        
        results = cesp.resolve(candidates, entity_mentions, 'Juan tenía los ojos marrones. Pedro, con sus ojos azules de Pedro, lo miraba.')
        
        juan_attrs = [r for r in results if r.entity_id == 'juan_1']
        pedro_attrs = [r for r in results if r.entity_id == 'pedro_1']
        
        assert len(results) == 2, f'Se esperaban 2 resultados, se obtuvo {len(results)}'
        assert len(juan_attrs) == 1, f'Juan debe tener 1 atributo, tiene {len(juan_attrs)}'
        assert juan_attrs[0].value == 'marrones', 'Juan debe tener ojos marrones'
        assert len(pedro_attrs) == 1, f'Pedro debe tener 1 atributo, tiene {len(pedro_attrs)}'
        assert pedro_attrs[0].value == 'azules', 'Pedro debe tener ojos azules'
        
        # Verificar que NO hay falso positivo
        juan_azules = [r for r in results if r.entity_id == 'juan_1' and r.value == 'azules']
        assert len(juan_azules) == 0, 'BUG: Juan no debe tener ojos azules!'
        
        print('  ✅ PASADO: Juan tiene marrones, Pedro tiene azules, NO hay falso positivo')
        tests_passed += 1
    except Exception as e:
        print(f'  ❌ FALLADO: {e}')
        tests_failed += 1

    # Resumen
    print('\n' + '=' * 60)
    print(f'RESUMEN: {tests_passed} pasados, {tests_failed} fallados')
    if tests_failed == 0:
        print('✅ TODOS LOS TESTS PASARON')
    else:
        print('❌ ALGUNOS TESTS FALLARON')
    print('=' * 60)
    
    return tests_failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
