from __future__ import annotations

from types import SimpleNamespace

from narrative_assistant.nlp.alias_resolver import (
    AliasDetector,
    AliasType,
    detect_and_resolve_aliases,
)


def _find_cluster(result, canonical_name: str):
    for cluster in result.clusters:
        if cluster.canonical_name.lower() == canonical_name.lower():
            return cluster
    return None


def test_appositive_role_is_reused_as_alias_reference():
    text = (
        "Pedro, el carpintero, llego al pueblo. "
        "Horas despues, el carpintero hablo con todos."
    )

    result = detect_and_resolve_aliases(text, known_entities=["Pedro"])

    pedro_cluster = _find_cluster(result, "Pedro")
    assert pedro_cluster is not None
    alias_texts = [a.text.lower() for a in pedro_cluster.aliases]
    assert "el carpintero" in alias_texts
    assert alias_texts.count("el carpintero") >= 2


def test_physical_descriptor_and_contracted_variant_are_resolved():
    text = (
        "Cervantes, el manco de Lepanto, escribio durante anos. "
        "Todos hablaban del manco de Lepanto en la taberna."
    )

    result = detect_and_resolve_aliases(text, known_entities=["Cervantes"])

    cluster = _find_cluster(result, "Cervantes")
    assert cluster is not None
    alias_texts = [a.text.lower() for a in cluster.aliases]
    assert "el manco de lepanto" in alias_texts
    assert "del manco de lepanto" in alias_texts


def test_generic_descriptor_detection_in_person_context():
    detector = AliasDetector()
    text = "La rubia respondio sin dudar y la joven sonrio."

    aliases = detector.detect_aliases(text)
    alias_to_type = {alias.text.lower(): alias.alias_type for alias in aliases}

    assert alias_to_type.get("la rubia") == AliasType.DESCRIPTIVE
    assert alias_to_type.get("la joven") == AliasType.DESCRIPTIVE


def test_context_resolution_supports_entity_objects_with_aliases():
    text = "Pedro Gomez entro al taller. La joven saludo a Pedro Gomez."
    known_entities = [SimpleNamespace(canonical_name="Pedro Gomez", aliases=["Pedro"])]

    result = detect_and_resolve_aliases(text, known_entities=known_entities)

    cluster = _find_cluster(result, "Pedro Gomez")
    assert cluster is not None
    assert any(a.text.lower() == "la joven" for a in cluster.aliases)
