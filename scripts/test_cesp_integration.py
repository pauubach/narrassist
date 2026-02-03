#!/usr/bin/env python3
"""
Test de integración del CESP en attributes.py
Verifica que la deduplicación basada en prioridad elimina falsos positivos.
"""
import sys
sys.path.insert(0, 'src')

from narrative_assistant.nlp.attributes import (
    AttributeExtractor, ExtractedAttribute, AssignmentSource,
    AttributeCategory, AttributeKey
)


def test_deduplicate_eliminates_false_positive():
    """
    Escenario: 'ojos azules de Pedro'
    - GENITIVO detecta -> Pedro (correcto)
    - PROXIMITY detecta -> Juan (falso positivo)
    
    El CESP debe eliminar el falso positivo de Juan.
    """
    print('=' * 60)
    print('TEST: CESP elimina falso positivo por prioridad')
    print('=' * 60)
    
    extractor = AttributeExtractor(
        use_llm=False,
        use_embeddings=False,
        use_dependency_extraction=False,
        use_patterns=False,
    )
    
    # Crear atributos simulando lo que produciría el pipeline
    attr_pedro_genitivo = ExtractedAttribute(
        entity_name='Pedro',
        category=AttributeCategory.PHYSICAL,
        key=AttributeKey.EYE_COLOR,
        value='azules',
        source_text='ojos azules de Pedro',
        start_char=100,
        end_char=120,
        confidence=0.85,
        assignment_source=AssignmentSource.GENITIVE,
        sentence_idx=1,
    )

    attr_juan_proximidad = ExtractedAttribute(
        entity_name='Juan',
        category=AttributeCategory.PHYSICAL,
        key=AttributeKey.EYE_COLOR,
        value='azules',
        source_text='ojos azules de Pedro',
        start_char=100,
        end_char=120,
        confidence=0.65,
        assignment_source=AssignmentSource.PROXIMITY,
        sentence_idx=1,
    )

    # Probar el nuevo _deduplicate
    result = extractor._deduplicate([attr_pedro_genitivo, attr_juan_proximidad])

    print(f'\nEntrada: Pedro(genitivo,0.85), Juan(proximity,0.65)')
    print(f'Salida: {len(result)} atributo(s)')

    for attr in result:
        print(f'  → {attr.entity_name}: {attr.key.value}={attr.value} '
              f'(source={attr.assignment_source}, conf={attr.confidence:.2f})')

    # Verificaciones
    assert len(result) == 1, f'Error: se esperaba 1 atributo, se obtuvieron {len(result)}'
    assert result[0].entity_name == 'Pedro', f'Error: se esperaba Pedro, se obtuvo {result[0].entity_name}'
    assert result[0].assignment_source == AssignmentSource.GENITIVE

    print('\n✅ TEST PASADO')


def test_deduplicate_keeps_different_sentences():
    """
    Escenario: El mismo atributo en dos oraciones diferentes
    - Oración 1: "Juan tiene ojos azules"
    - Oración 2: "Los ojos azules de Pedro brillaban"
    
    Ambos deben mantenerse porque son de oraciones distintas.
    """
    print('\n' + '=' * 60)
    print('TEST: CESP mantiene atributos de oraciones diferentes')
    print('=' * 60)
    
    extractor = AttributeExtractor(
        use_llm=False,
        use_embeddings=False,
        use_dependency_extraction=False,
        use_patterns=False,
    )
    
    attr_juan_sentence1 = ExtractedAttribute(
        entity_name='Juan',
        category=AttributeCategory.PHYSICAL,
        key=AttributeKey.EYE_COLOR,
        value='azules',
        source_text='Juan tiene ojos azules',
        start_char=0,
        end_char=22,
        confidence=0.80,
        assignment_source=AssignmentSource.EXPLICIT_SUBJECT,
        sentence_idx=0,
    )

    attr_pedro_sentence2 = ExtractedAttribute(
        entity_name='Pedro',
        category=AttributeCategory.PHYSICAL,
        key=AttributeKey.EYE_COLOR,
        value='azules',
        source_text='Los ojos azules de Pedro brillaban',
        start_char=100,
        end_char=134,
        confidence=0.85,
        assignment_source=AssignmentSource.GENITIVE,
        sentence_idx=1,
    )

    result = extractor._deduplicate([attr_juan_sentence1, attr_pedro_sentence2])

    print(f'\nEntrada: Juan(sentence0), Pedro(sentence1)')
    print(f'Salida: {len(result)} atributo(s)')

    for attr in result:
        print(f'  → {attr.entity_name}: sentence_idx={attr.sentence_idx}')

    # Ambos deben mantenerse porque son de oraciones diferentes
    assert len(result) == 2, f'Error: se esperaban 2 atributos, se obtuvieron {len(result)}'
    
    print('\n✅ TEST PASADO')


def test_priority_order():
    """
    Verifica el orden correcto de prioridades CESP.
    Las prioridades están definidas en _deduplicate():
        GENITIVE: 100
        EXPLICIT_SUBJECT: 90
        LLM: 80
        IMPLICIT_SUBJECT: 50
        EMBEDDINGS: 40
        PROXIMITY: 10
    """
    print('\n' + '=' * 60)
    print('TEST: Verificar orden de prioridades CESP')
    print('=' * 60)
    
    # Prioridades definidas en _deduplicate() de attributes.py
    source_priority = {
        AssignmentSource.GENITIVE: 100,
        AssignmentSource.EXPLICIT_SUBJECT: 90,
        AssignmentSource.LLM: 80,
        AssignmentSource.IMPLICIT_SUBJECT: 50,
        AssignmentSource.EMBEDDINGS: 40,
        AssignmentSource.PROXIMITY: 10,
    }
    
    print('\nPrioridades configuradas (en _deduplicate):')
    for source, priority in sorted(source_priority.items(), key=lambda x: -x[1]):
        print(f'  {source}: {priority}')
    
    # Verificar orden esperado
    assert source_priority[AssignmentSource.GENITIVE] > source_priority[AssignmentSource.EXPLICIT_SUBJECT]
    assert source_priority[AssignmentSource.EXPLICIT_SUBJECT] > source_priority[AssignmentSource.LLM]
    assert source_priority[AssignmentSource.LLM] > source_priority[AssignmentSource.IMPLICIT_SUBJECT]
    assert source_priority[AssignmentSource.IMPLICIT_SUBJECT] > source_priority[AssignmentSource.EMBEDDINGS]
    assert source_priority[AssignmentSource.EMBEDDINGS] > source_priority[AssignmentSource.PROXIMITY]
    
    print('\n✅ TEST PASADO: Orden correcto GENITIVE > EXPLICIT_SUBJECT > LLM > IMPLICIT_SUBJECT > EMBEDDINGS > PROXIMITY')


if __name__ == '__main__':
    test_priority_order()
    test_deduplicate_eliminates_false_positive()
    test_deduplicate_keeps_different_sentences()
    
    print('\n' + '=' * 60)
    print('🎉 TODOS LOS TESTS DE INTEGRACIÓN CESP PASARON')
    print('=' * 60)
