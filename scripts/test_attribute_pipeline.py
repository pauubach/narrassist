#!/usr/bin/env python
"""
Test script that emulates the EXACT flow used by the API server for attribute extraction.
This helps debug why "ojos verdes" is being assigned to Juan instead of María.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from narrative_assistant.nlp.attributes import (
    AttributeExtractor,
    resolve_attributes_with_coreferences,
)
from narrative_assistant.nlp.coreference_resolver import resolve_coreferences_voting
from narrative_assistant.core.result import Result


def load_test_document():
    """Load the test document."""
    test_file = project_root / "test_books" / "test_document_fresh.txt"
    with open(test_file, "r", encoding="utf-8") as f:
        return f.read()


def detect_chapters(text: str) -> list[dict]:
    """Simple chapter detection for test."""
    import re
    chapters = []
    pattern = r"Capítulo\s+(\d+):\s+([^\n]+)"

    matches = list(re.finditer(pattern, text))
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapters.append({
            "chapter_number": int(match.group(1)),
            "title": match.group(2).strip(),
            "start_char": start,
            "end_char": end,
        })

    return chapters


def main():
    print("=" * 80)
    print("EMULANDO FLUJO DEL API SERVER PARA EXTRACCIÓN DE ATRIBUTOS")
    print("=" * 80)

    # 1. Load document
    text = load_test_document()
    print(f"\n[1] Documento cargado: {len(text)} caracteres")

    # 2. Detect chapters
    chapters = detect_chapters(text)
    print(f"\n[2] Capítulos detectados: {len(chapters)}")
    for ch in chapters:
        print(f"    Cap {ch['chapter_number']}: {ch['title']} (chars {ch['start_char']}-{ch['end_char']})")

    # 3. Define entities (simulating NER result)
    # In the real flow, these come from NER extraction
    entities = [
        {"canonical_name": "María", "first_appearance_char": text.find("María")},
        {"canonical_name": "Juan", "first_appearance_char": text.find("Juan")},
    ]
    print(f"\n[3] Entidades (simulando NER): {[e['canonical_name'] for e in entities]}")

    # 4. Run coreference resolution (FASE 4: FUSION in the real flow)
    print(f"\n[4] Ejecutando resolución de correferencias...")
    coref_result = resolve_coreferences_voting(text, chapters=chapters)

    if coref_result.chains:
        print(f"    Cadenas encontradas: {len(coref_result.chains)}")
        for i, chain in enumerate(coref_result.chains):
            mentions_str = ", ".join([f"'{m.text}' ({m.start_char}-{m.end_char})" for m in chain.mentions[:5]])
            if len(chain.mentions) > 5:
                mentions_str += f"... (+{len(chain.mentions)-5} más)"
            print(f"    Chain {i+1}: main='{chain.main_mention}' -> [{mentions_str}]")
    else:
        print("    [!] No se encontraron cadenas de correferencia!")

    # 5. Prepare entity_mentions (as done in main.py lines 6164-6186)
    print(f"\n[5] Preparando menciones de entidades...")
    entity_mentions = [
        (e["canonical_name"], e["first_appearance_char"], e["first_appearance_char"] + len(e["canonical_name"]))
        for e in entities
    ]

    # Add coreference mentions
    if coref_result.chains:
        for chain in coref_result.chains:
            matching_entity = next(
                (e for e in entities
                 if e["canonical_name"] and chain.main_mention and
                 e["canonical_name"].lower() == chain.main_mention.lower()),
                None
            )
            if matching_entity:
                for mention in chain.mentions:
                    entity_mentions.append(
                        (matching_entity["canonical_name"], mention.start_char, mention.end_char)
                    )

    print(f"    Total menciones: {len(entity_mentions)}")
    for name, start, end in entity_mentions[:10]:
        snippet = text[max(0, start-10):min(len(text), end+20)]
        print(f"    - '{name}' @ {start}-{end}: ...{snippet}...")
    if len(entity_mentions) > 10:
        print(f"    ... y {len(entity_mentions) - 10} más")

    # 6. Extract attributes (FASE 5: ATRIBUTOS)
    # Test with LLM to verify bug doesn't appear with any method
    import os
    use_llm = os.environ.get("TEST_WITH_LLM", "0") == "1"
    print(f"\n[6] Extrayendo atributos (LLM={'ON' if use_llm else 'OFF'}, embeddings=OFF)...")
    attr_extractor = AttributeExtractor(use_embeddings=False, use_llm=use_llm)

    result = attr_extractor.extract_attributes(text, entity_mentions, chapter_id=None)

    if result.is_failure:
        print(f"    [FAIL] Error: {result.error}")
        return

    extracted_attrs = result.value.attributes
    print(f"    Atributos extraídos: {len(extracted_attrs)}")

    # 7. Assign chapters to attributes (as in main.py lines 6259-6275)
    print(f"\n[7] Asignando capítulos a atributos...")

    def find_chapter_for_position(char_pos: int) -> int | None:
        for ch in chapters:
            if ch["start_char"] <= char_pos <= ch["end_char"]:
                return ch["chapter_number"]
        return None

    for attr in extracted_attrs:
        if attr.start_char is not None and attr.start_char > 0:
            chapter_num = find_chapter_for_position(attr.start_char)
            if chapter_num is not None:
                attr.chapter_id = chapter_num

    # 8. CRITICAL: Check eye color before coreference resolution
    print(f"\n[8] Atributos de COLOR DE OJOS ANTES de resolucion de correferencias:")
    eye_attrs_before = [a for a in extracted_attrs if "eye" in str(a.key).lower() or "ojo" in str(a.key).lower()]
    for attr in eye_attrs_before:
        print(f"    >> {attr.entity_name}.{attr.key} = '{attr.value}' (cap {attr.chapter_id}, confianza {attr.confidence:.2f})")
        print(f"       Fuente: '{attr.source_text}'")
        print(f"       Posicion: {attr.start_char}-{attr.end_char}")

    # 9. Resolve attributes with coreferences (as in main.py lines 6277-6316)
    print(f"\n[9] Resolviendo atributos con correferencias...")
    if coref_result.chains:
        resolved_attrs = resolve_attributes_with_coreferences(
            attributes=extracted_attrs,
            coref_chains=coref_result.chains,
            text=text,
        )
    else:
        resolved_attrs = extracted_attrs
        print("    [!] Sin cadenas de correferencia - no se resolvieron pronombres")

    # 10. CRITICAL: Check eye color AFTER coreference resolution
    print(f"\n[10] Atributos de COLOR DE OJOS DESPUÉS de resolución de correferencias:")
    eye_attrs_after = [a for a in resolved_attrs if "eye" in str(a.key).lower() or "ojo" in str(a.key).lower()]

    # Mostrar todos, con especial atención al color verde
    for attr in eye_attrs_after:
        is_green = "verde" in attr.value.lower()
        marker = "[BUG] BUG?" if is_green and "juan" in attr.entity_name.lower() else "[OK]"
        marker = "[OK]" if is_green and "mar" in attr.entity_name.lower() else marker

        print(f"    {marker} {attr.entity_name}.{attr.key} = '{attr.value}' (cap {attr.chapter_id}, confianza {attr.confidence:.2f})")
        print(f"       Fuente: '{attr.source_text}'")

    # 11. Summary by entity
    print(f"\n[11] RESUMEN POR PERSONAJE:")
    print("-" * 60)

    for entity in entities:
        name = entity["canonical_name"]
        entity_attrs = [a for a in resolved_attrs if a.entity_name and a.entity_name.lower() == name.lower()]

        print(f"\n{name}:")
        eye_attrs = [a for a in entity_attrs if "eye" in str(a.key).lower() or "ojo" in str(a.key).lower()]
        hair_attrs = [a for a in entity_attrs if "hair" in str(a.key).lower() or "cabel" in str(a.key).lower()]

        if eye_attrs:
            print(f"  [OJO] Ojos:")
            for a in sorted(eye_attrs, key=lambda x: x.chapter_id or 0):
                print(f"     Cap {a.chapter_id}: {a.value} ({a.confidence:.2f})")

        if hair_attrs:
            print(f"  [PELO] Cabello:")
            for a in sorted(hair_attrs, key=lambda x: x.chapter_id or 0):
                print(f"     Cap {a.chapter_id}: {a.value} ({a.confidence:.2f})")

    # 12. Verify expected vs actual
    print(f"\n[12] VERIFICACIÓN DE RESULTADOS ESPERADOS:")
    print("-" * 60)

    expected = {
        "María": {
            1: {"eye_color": "azules"},
            2: {"eye_color": "verdes"},  # BUG: This is often assigned to Juan
            3: {"eye_color": "azules"},
        },
        "Juan": {
            1: {"eye_color": "marrones"},
            2: {"eye_color": "azules"},
            3: {},  # No eye color mentioned
        }
    }

    issues = []
    for name, chapters_expected in expected.items():
        entity_attrs = [a for a in resolved_attrs if a.entity_name and a.entity_name.lower() == name.lower()]

        for ch_num, attrs_expected in chapters_expected.items():
            for attr_key, expected_value in attrs_expected.items():
                matching = [a for a in entity_attrs
                           if a.chapter_id == ch_num and attr_key in str(a.key).lower()]

                if matching:
                    actual_value = matching[0].value
                    if expected_value.lower() in actual_value.lower():
                        print(f"  [OK] {name} cap {ch_num} {attr_key}: '{actual_value}' (esperado: '{expected_value}')")
                    else:
                        print(f"  [FAIL] {name} cap {ch_num} {attr_key}: '{actual_value}' (esperado: '{expected_value}')")
                        issues.append(f"{name} cap {ch_num}: got '{actual_value}', expected '{expected_value}'")
                else:
                    print(f"  [!] {name} cap {ch_num} {attr_key}: NO ENCONTRADO (esperado: '{expected_value}')")
                    issues.append(f"{name} cap {ch_num}: missing {attr_key}")

    # Check for incorrectly assigned attributes
    for attr in resolved_attrs:
        if "verde" in attr.value.lower() and "ojo" in str(attr.key).lower():
            if "juan" in attr.entity_name.lower():
                issues.append(f"BUG: 'ojos verdes' asignado a Juan en cap {attr.chapter_id}")

    print(f"\n[13] CONCLUSIÓN:")
    print("-" * 60)
    if issues:
        print(f"  [FAIL] Se encontraron {len(issues)} problemas:")
        for issue in issues:
            print(f"     - {issue}")
    else:
        print(f"  [OK] Todos los atributos asignados correctamente")

    return issues


if __name__ == "__main__":
    issues = main()
    sys.exit(1 if issues else 0)
