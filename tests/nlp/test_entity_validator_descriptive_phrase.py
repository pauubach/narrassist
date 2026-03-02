"""
Tests para filtrar frases descriptivas mal detectadas como personas.
"""

from narrative_assistant.nlp.entity_validator import EntityValidator
from narrative_assistant.nlp.ner import EntityLabel, ExtractedEntity


def test_rejects_article_plus_profession_as_person() -> None:
    """Debe rechazar frases tipo 'el carpintero' como entidad PER."""
    validator = EntityValidator()
    full_text = "Pedro, el carpintero, llegó."
    entity = ExtractedEntity(
        text="el carpintero",
        label=EntityLabel.PER,
        start_char=7,
        end_char=20,
        confidence=0.9,
        source="llm",
    )

    result = validator.validate([entity], full_text)

    assert not any(e.text == "el carpintero" for e in result.valid_entities)
    assert any(e.text == "el carpintero" for e in result.rejected_entities)
    score = result.scores.get("el carpintero")
    assert score is not None
    assert score.rejection_reason is not None
    assert "rol/profesión" in score.rejection_reason


def test_keeps_article_plus_proper_name() -> None:
    """No debe rechazar entidades válidas tipo 'El Cid'."""
    validator = EntityValidator()
    full_text = "El Cid cabalgó al amanecer."
    entity = ExtractedEntity(
        text="El Cid",
        label=EntityLabel.PER,
        start_char=0,
        end_char=6,
        confidence=0.9,
        source="spacy",
    )

    result = validator.validate([entity], full_text)

    assert any(e.text == "El Cid" for e in result.valid_entities)
    assert not any(e.text == "El Cid" for e in result.rejected_entities)
