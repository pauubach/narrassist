"""Tests para BK-17: Glosario de usuario → inyección en NER pipeline."""

import re
from unittest.mock import MagicMock, patch

import pytest

from narrative_assistant.nlp.ner import EntityLabel, ExtractedEntity, NERExtractor


class _FakeNERExtractor:
    """Subconjunto de NERExtractor para testear _inject_glossary_entities sin spaCy."""

    def __init__(self):
        import threading

        self._gazetteer_lock = threading.RLock()
        self.dynamic_gazetteer: dict[str, EntityLabel] = {}

    _inject_glossary_entities = NERExtractor._inject_glossary_entities


def _make_extractor():
    return _FakeNERExtractor()


def _mock_db_rows(rows):
    """Crea un mock de get_database() que retorna rows."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = rows
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_db = MagicMock()
    mock_db.connection.return_value = mock_conn
    return mock_db


class TestGlossaryInjection:
    """Tests para _inject_glossary_entities."""

    @patch("narrative_assistant.persistence.database.get_database")
    def test_case_insensitive_match(self, mock_get_db):
        """El glosario encuentra términos independientemente del case."""
        mock_get_db.return_value = _mock_db_rows(
            [
                ("Winterfell", "LOC", 1.0),
            ]
        )
        ext = _make_extractor()
        entities_found: set[tuple[int, int]] = set()

        result = ext._inject_glossary_entities(
            "Los personajes llegaron a winterfell al amanecer.",
            project_id=1,
            existing_entities=[],
            entities_found=entities_found,
        )

        assert len(result) == 1
        assert result[0].label == EntityLabel.LOC
        assert result[0].confidence == 1.0
        assert result[0].source == "glossary"
        # El texto debe preservar el case original del documento
        assert result[0].text == "winterfell"

    @patch("narrative_assistant.persistence.database.get_database")
    def test_word_boundary_respected(self, mock_get_db):
        """'Stark' no debe encontrarse dentro de 'Starkiller'."""
        mock_get_db.return_value = _mock_db_rows(
            [
                ("Stark", "PER", 1.0),
            ]
        )
        ext = _make_extractor()
        entities_found: set[tuple[int, int]] = set()

        result = ext._inject_glossary_entities(
            "El Starkiller destruyó el planeta.",
            project_id=1,
            existing_entities=[],
            entities_found=entities_found,
        )

        assert len(result) == 0

    @patch("narrative_assistant.persistence.database.get_database")
    def test_glossary_priority_over_existing(self, mock_get_db):
        """El glosario no solapa con entidades ya detectadas."""
        mock_get_db.return_value = _mock_db_rows(
            [
                ("Juan", "PER", 1.0),
            ]
        )
        ext = _make_extractor()
        # Simular que spaCy ya detectó "Juan" en pos (0, 4)
        entities_found: set[tuple[int, int]] = {(0, 4)}

        result = ext._inject_glossary_entities(
            "Juan caminó por Madrid. Juan volvió a casa.",
            project_id=1,
            existing_entities=[],
            entities_found=entities_found,
        )

        # Solo la segunda ocurrencia (la primera ya estaba ocupada)
        assert len(result) == 1
        assert result[0].start_char == 24

    @patch("narrative_assistant.persistence.database.get_database")
    def test_multiple_occurrences(self, mock_get_db):
        """Encuentra todas las ocurrencias de un término."""
        mock_get_db.return_value = _mock_db_rows(
            [
                ("Mordor", "LOC", 1.0),
            ]
        )
        ext = _make_extractor()
        entities_found: set[tuple[int, int]] = set()

        text = "Mordor era oscuro. El camino a Mordor era largo."
        result = ext._inject_glossary_entities(
            text,
            project_id=1,
            existing_entities=[],
            entities_found=entities_found,
        )

        assert len(result) == 2
        assert all(e.label == EntityLabel.LOC for e in result)

    @patch("narrative_assistant.persistence.database.get_database")
    def test_long_term_matched_first(self, mock_get_db):
        """'House Stark' se busca antes que 'Stark' (longitud DESC)."""
        mock_get_db.return_value = _mock_db_rows(
            [
                ("House Stark", "ORG", 1.0),
                ("Stark", "PER", 1.0),
            ]
        )
        ext = _make_extractor()
        entities_found: set[tuple[int, int]] = set()

        text = "La House Stark dominaba el Norte."
        result = ext._inject_glossary_entities(
            text,
            project_id=1,
            existing_entities=[],
            entities_found=entities_found,
        )

        # "House Stark" matchea primero, ocupa esas posiciones
        # "Stark" no debe matchear dentro de "House Stark"
        assert len(result) == 1
        assert result[0].text == "House Stark"
        assert result[0].label == EntityLabel.ORG

    @patch("narrative_assistant.persistence.database.get_database")
    def test_empty_glossary_no_effect(self, mock_get_db):
        """Un glosario vacío no produce resultados."""
        mock_get_db.return_value = _mock_db_rows([])
        ext = _make_extractor()
        entities_found: set[tuple[int, int]] = set()

        result = ext._inject_glossary_entities(
            "Un texto cualquiera sin términos especiales.",
            project_id=1,
            existing_entities=[],
            entities_found=entities_found,
        )

        assert result == []
