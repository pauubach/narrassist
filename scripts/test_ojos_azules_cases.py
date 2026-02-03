#!/usr/bin/env python
"""
Test script para verificar la diferenciación entre:
1. "Miró a los ojos azules de Pedro" → ojos = Pedro
2. "Miró con los ojos azules a Pedro" → ojos = Juan (sujeto)

Y otros casos problemáticos con posesivos.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_dependency_extractor():
    """Test the dependency extractor directly."""
    print("=" * 80)
    print("TEST 1: DEPENDENCY EXTRACTOR DIRECTO")
    print("=" * 80)
    
    try:
        from narrative_assistant.nlp.extraction.extractors.dependency_extractor import DependencyExtractor
        from narrative_assistant.nlp.extraction.base import ExtractionContext
        
        extractor = DependencyExtractor()
        
        test_cases = [
            {
                "name": "ojos DE Pedro (genitivo explícito)",
                "text": "Juan era un hombre agradable. Miró a los ojos azules de Pedro.",
                "entities": ["Juan", "Pedro"],
                "expected_entity": "Pedro",
                "expected_value": "azules",
            },
            {
                "name": "ojos CON Juan (instrumental, sujeto elidido)",
                "text": "Juan era un hombre agradable. Miró con los ojos azules a Pedro.",
                "entities": ["Juan", "Pedro"],
                "expected_entity": "Juan",
                "expected_value": "azules",
            },
            {
                "name": "SUS ojos (posesivo, sujeto en oración anterior)",
                "text": "Juan entró poco después. Era un hombre muy alto. Sus ojos azules miraban con curiosidad a María.",
                "entities": ["Juan", "María"],
                "expected_entity": "Juan",
                "expected_value": "azules",
            },
            {
                "name": "SUS ojos con entidad después (bug conocido)",
                "text": "María sonrió. Sus ojos verdes miraban a Juan.",
                "entities": ["María", "Juan"],
                "expected_entity": "María",
                "expected_value": "verdes",
            },
            {
                "name": "Tenía ojos (verbo descriptivo)",
                "text": "Juan tenía los ojos marrones.",
                "entities": ["Juan"],
                "expected_entity": "Juan",
                "expected_value": "marrones",
            },
            {
                "name": "Era alto CON ojos (copulativo + preposicional)",
                "text": "Pedro era alto, con ojos negros y barba espesa.",
                "entities": ["Pedro"],
                "expected_entity": "Pedro",
                "expected_value": "negros",
            },
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n--- Caso {i}: {case['name']} ---")
            print(f"Texto: {case['text']}")
            print(f"Entidades: {case['entities']}")
            print(f"Esperado: {case['expected_entity']}.eye_color = {case['expected_value']}")
            
            context = ExtractionContext(
                text=case["text"],
                entity_names=case["entities"],
                entity_mentions=None,
                chapter=1,
            )
            
            result = extractor.extract(context)
            
            eye_attrs = [a for a in result.attributes if a.attribute_type == "eye_color"]
            
            if eye_attrs:
                for attr in eye_attrs:
                    status = "✅" if attr.entity_name == case["expected_entity"] and attr.value == case["expected_value"] else "❌"
                    print(f"{status} Resultado: {attr.entity_name}.eye_color = {attr.value} (confianza: {attr.confidence:.2f})")
            else:
                print("❌ No se detectaron atributos de color de ojos")
            
            # Mostrar todos los atributos detectados
            if result.attributes:
                print(f"   Todos los atributos: {[(a.entity_name, a.attribute_type, a.value) for a in result.attributes]}")
                
    except Exception as e:
        print(f"Error en test de dependency extractor: {e}")
        import traceback
        traceback.print_exc()


def test_full_pipeline():
    """Test the full attribute extraction pipeline."""
    print("\n" + "=" * 80)
    print("TEST 2: PIPELINE COMPLETO (AttributeExtractor)")
    print("=" * 80)
    
    try:
        from narrative_assistant.nlp.attributes import AttributeExtractor
        
        # Desactivar LLM y embeddings para test rápido
        extractor = AttributeExtractor(
            filter_metaphors=True,
            min_confidence=0.4,
            use_llm=False,  # Más rápido sin Ollama
            use_embeddings=False,  # Más rápido sin embeddings
            use_dependency_extraction=True,
            use_patterns=True,
        )
        
        test_cases = [
            {
                "name": "ojos DE Pedro",
                "text": "Juan era un hombre agradable. Miró a los ojos azules de Pedro.",
                "entities": [("Juan", 0, 4), ("Pedro", 55, 60)],
                "expected_entity": "Pedro",
            },
            {
                "name": "ojos CON Juan",
                "text": "Juan era un hombre agradable. Miró con los ojos azules a Pedro.",
                "entities": [("Juan", 0, 4), ("Pedro", 57, 62)],
                "expected_entity": "Juan",
            },
            {
                "name": "SUS ojos - Juan antes, María después",
                "text": "Juan entró poco después. Era un hombre muy alto. Sus ojos azules miraban con curiosidad a María.",
                "entities": [("Juan", 0, 4), ("María", 89, 94)],
                "expected_entity": "Juan",
            },
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n--- Caso {i}: {case['name']} ---")
            print(f"Texto: {case['text']}")
            print(f"Esperado: {case['expected_entity']}")
            
            result = extractor.extract_attributes(
                text=case["text"],
                entity_mentions=case["entities"],
                chapter_id=1,
            )
            
            if result.is_success and result.value:
                eye_attrs = [a for a in result.value.attributes 
                            if hasattr(a.key, 'value') and 'eye' in a.key.value.lower()]
                
                if eye_attrs:
                    for attr in eye_attrs:
                        status = "✅" if attr.entity_name == case["expected_entity"] else "❌"
                        print(f"{status} Resultado: {attr.entity_name}.{attr.key.value} = {attr.value} (conf: {attr.confidence:.2f})")
                else:
                    print("❌ No se detectaron atributos de color de ojos")
                
                # Mostrar todos los atributos
                all_attrs = [(a.entity_name, a.key.value if hasattr(a.key, 'value') else str(a.key), a.value) 
                            for a in result.value.attributes]
                if all_attrs:
                    print(f"   Todos: {all_attrs}")
            else:
                print(f"❌ Error: {result.error if hasattr(result, 'error') else 'desconocido'}")
                
    except Exception as e:
        print(f"Error en test de pipeline completo: {e}")
        import traceback
        traceback.print_exc()


def test_scope_resolver():
    """Test the scope resolver directly for possessive resolution."""
    print("\n" + "=" * 80)
    print("TEST 3: SCOPE RESOLVER (resolución de posesivos)")
    print("=" * 80)
    
    try:
        from narrative_assistant.nlp.scope_resolver import ScopeResolver
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model
        
        nlp = load_spacy_model()
        
        test_cases = [
            {
                "name": "Sus ojos - antecedente antes, entidad después",
                "text": "Juan entró poco después. Era un hombre muy alto. Sus ojos azules miraban con curiosidad a María.",
                "position": 50,  # Posición aproximada de "Sus"
                "entities": [("Juan", 0, 4, "PER"), ("María", 89, 94, "PER")],
                "expected": "Juan",
            },
            {
                "name": "Sus ojos - solo entidad antes",
                "text": "María sonrió. Sus ojos verdes brillaban.",
                "position": 14,  # Posición de "Sus"
                "entities": [("María", 0, 5, "PER")],
                "expected": "María",
            },
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n--- Caso {i}: {case['name']} ---")
            print(f"Texto: {case['text']}")
            print(f"Esperado: {case['expected']}")
            
            doc = nlp(case["text"])
            resolver = ScopeResolver(doc, case["text"])
            
            result = resolver.find_nearest_entity_by_scope(
                position=case["position"],
                entity_mentions=case["entities"],
                prefer_subject=True,
            )
            
            if result:
                entity_name, confidence = result
                status = "✅" if entity_name == case["expected"] else "❌"
                print(f"{status} Resultado: {entity_name} (confianza: {confidence:.2f})")
            else:
                print("❌ No se encontró entidad")
                
    except Exception as e:
        print(f"Error en test de scope resolver: {e}")
        import traceback
        traceback.print_exc()


def test_spacy_parsing():
    """Verify how spaCy parses the key sentences."""
    print("\n" + "=" * 80)
    print("TEST 4: ANÁLISIS DE PARSING DE SPACY")
    print("=" * 80)
    
    try:
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model
        
        nlp = load_spacy_model()
        
        sentences = [
            "Miró a los ojos azules de Pedro.",
            "Miró con los ojos azules a Pedro.",
            "Sus ojos azules miraban con curiosidad a María.",
        ]
        
        for sent in sentences:
            print(f"\n--- Oración: '{sent}' ---")
            doc = nlp(sent)
            
            print("Token          | POS    | DEP      | HEAD")
            print("-" * 55)
            for token in doc:
                print(f"{token.text:14} | {token.pos_:6} | {token.dep_:8} | {token.head.text}")
                
    except Exception as e:
        print(f"Error en test de spaCy: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🔬 SUITE DE TESTS PARA RESOLUCIÓN DE ATRIBUTOS")
    print("=" * 80)
    
    # Test 4 primero para entender el parsing
    test_spacy_parsing()
    
    # Test 3: Scope resolver
    test_scope_resolver()
    
    # Test 1: Dependency extractor
    test_dependency_extractor()
    
    # Test 2: Pipeline completo
    test_full_pipeline()
    
    print("\n" + "=" * 80)
    print("FIN DE TESTS")
    print("=" * 80)
