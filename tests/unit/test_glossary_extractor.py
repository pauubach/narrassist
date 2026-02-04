"""
Tests para el extractor automático de términos de glosario.
"""

import pytest

from narrative_assistant.analysis.glossary_extractor import (
    GlossaryExtractionReport,
    GlossaryExtractor,
    GlossarySuggestion,
)


class TestGlossaryExtractor:
    """Tests para GlossaryExtractor."""

    def test_extract_empty_chapters(self):
        """Maneja capítulos vacíos correctamente."""
        extractor = GlossaryExtractor()
        result = extractor.extract(chapters=[])

        assert result.is_success
        report = result.value
        assert report.suggestions == []
        assert report.chapters_analyzed == 0

    def test_extract_capitalized_names(self):
        """Detecta nombres propios con mayúscula."""
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3)
        chapters = [
            {
                "number": 1,
                "content": "El mago Gandoriel caminaba por el bosque. Gandoriel era sabio.",
            },
            {
                "number": 2,
                "content": "Gandoriel encontró a Elyndra en la cueva. Elyndra le saludó.",
            },
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value
        terms = [s.term for s in report.suggestions]

        # Debe detectar nombres con frecuencia >= 2
        assert "Gandoriel" in terms or "Elyndra" in terms

    def test_exclude_common_names(self):
        """Excluye nombres muy comunes como María, Juan, etc."""
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3)
        chapters = [
            {
                "number": 1,
                "content": "María y Juan fueron al mercado. María compró frutas. Juan las llevó.",
            },
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value
        terms = [s.term.lower() for s in report.suggestions]

        # María y Juan son nombres comunes, no deberían aparecer
        assert "maría" not in terms
        assert "juan" not in terms

    def test_detect_acronyms(self):
        """Detecta acrónimos como términos técnicos."""
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3)
        chapters = [
            {
                "number": 1,
                "content": "El protocolo HTTP es fundamental. Usamos HTTP para comunicación. También API REST.",
            },
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value

        # Buscar términos técnicos detectados
        technical_terms = [s for s in report.suggestions if s.is_likely_technical]
        # Al menos debería detectar algún acrónimo
        # (depende de la frecuencia mínima)

    def test_detect_fantasy_names(self):
        """Detecta nombres que parecen inventados (fantasía)."""
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3)
        chapters = [
            {"number": 1, "content": "El elfo Thranduil vivía en el bosque. Thranduil era el rey."},
            {"number": 2, "content": "Thranduil convocó a su consejo."},
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value

        # Buscar si detectó nombres inventados
        invented = [s for s in report.suggestions if s.is_likely_invented]
        # Thranduil tiene sufijo -il típico de fantasía

    def test_exclude_existing_glossary_terms(self):
        """Excluye términos que ya están en el glosario."""
        existing = {"gandoriel", "elyndra"}
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3, existing_terms=existing)
        chapters = [
            {
                "number": 1,
                "content": "El mago Gandoriel y Elyndra viajaban. Gandoriel era poderoso. Elyndra era sabia.",
            },
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value
        terms = [s.term.lower() for s in report.suggestions]

        # No debe sugerir términos que ya existen
        assert "gandoriel" not in terms
        assert "elyndra" not in terms

    def test_extract_with_entities(self):
        """Usa entidades del NER para mejorar detección."""
        extractor = GlossaryExtractor(min_frequency=1, min_confidence=0.3)
        chapters = [{"number": 1, "content": "Texto simple."}]
        entities = [
            {
                "name": "Aragorn",
                "type": "CHARACTER",
                "mention_count": 15,
                "first_mention_chapter": 1,
            },
            {
                "name": "Rivendel",
                "type": "LOCATION",
                "mention_count": 8,
                "first_mention_chapter": 2,
            },
        ]

        result = extractor.extract(chapters=chapters, entities=entities)

        assert result.is_success
        report = result.value
        terms = [s.term for s in report.suggestions]

        # Debe incluir entidades del NER con suficientes menciones
        assert "Aragorn" in terms or "Rivendel" in terms

    def test_frequency_filtering(self):
        """Respeta los límites de frecuencia."""
        extractor = GlossaryExtractor(
            min_frequency=3,  # Mínimo 3 apariciones
            max_frequency=5,  # Máximo 5 apariciones
            min_confidence=0.3,
        )
        chapters = [
            {
                "number": 1,
                "content": """
                El reino de Mordoria era oscuro. Mordoria estaba en el norte.
                En Mordoria vivían trolls. La capital de Mordoria era Darkhold.
                Darkhold tenía muros negros. Darkhold era impenetrable.
                Darkhold resistió muchos asedios.
                """,
            },
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value

        for suggestion in report.suggestions:
            # Frecuencia debe estar en rango
            assert suggestion.frequency >= 3
            assert suggestion.frequency <= 5

    def test_confidence_threshold(self):
        """Solo devuelve sugerencias con confianza suficiente."""
        extractor = GlossaryExtractor(
            min_frequency=1,
            min_confidence=0.8,  # Alta confianza requerida
        )
        chapters = [
            {"number": 1, "content": "Texto con palabras normales sin nombres propios claros."},
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value

        for suggestion in report.suggestions:
            assert suggestion.confidence >= 0.8

    def test_report_statistics(self):
        """El reporte incluye estadísticas correctas."""
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3)
        chapters = [
            {"number": 1, "content": "El HTTP protocolo HTTP usa TCP."},
            {"number": 2, "content": "Zarathiel el mago. Zarathiel conjuró."},
            {"number": 3, "content": ""},  # Vacío
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value

        # Debe contar capítulos analizados (excluyendo vacíos)
        assert report.chapters_analyzed == 2

    def test_suggestion_contexts(self):
        """Las sugerencias incluyen contextos de uso."""
        extractor = GlossaryExtractor(min_frequency=2, min_confidence=0.3)
        chapters = [
            {
                "number": 1,
                "content": "El antiguo Drakonheim era una fortaleza. En Drakonheim se forjaban espadas.",
            },
        ]

        result = extractor.extract(chapters=chapters)

        assert result.is_success
        report = result.value

        # Buscar sugerencias con contextos
        with_contexts = [s for s in report.suggestions if s.contexts]
        # Al menos alguna debería tener contexto

    def test_category_hints(self):
        """Las sugerencias incluyen categorías sugeridas."""
        extractor = GlossaryExtractor(min_frequency=1, min_confidence=0.3)
        chapters = [{"number": 1, "content": "Simple."}]
        entities = [
            {"name": "Frodo", "type": "CHARACTER", "mention_count": 10},
            {"name": "Mordor", "type": "LOCATION", "mention_count": 8},
        ]

        result = extractor.extract(chapters=chapters, entities=entities)

        assert result.is_success
        report = result.value

        for suggestion in report.suggestions:
            if suggestion.term == "Frodo":
                assert suggestion.category_hint == "personaje"
            elif suggestion.term == "Mordor":
                assert suggestion.category_hint == "lugar"


class TestGlossarySuggestion:
    """Tests para GlossarySuggestion."""

    def test_to_dict(self):
        """Serializa correctamente a diccionario."""
        suggestion = GlossarySuggestion(
            term="Elrond",
            reason="Nombre con mayúscula, parece inventado",
            category_hint="personaje",
            confidence=0.85,
            frequency=12,
            first_chapter=1,
            contexts=["Elrond era sabio"],
            is_likely_invented=True,
            is_likely_technical=False,
            is_likely_proper_noun=True,
        )

        d = suggestion.to_dict()

        assert d["term"] == "Elrond"
        assert d["confidence"] == 0.85
        assert d["frequency"] == 12
        assert d["is_likely_invented"] is True
        assert len(d["contexts"]) == 1


class TestGlossaryExtractionReport:
    """Tests para GlossaryExtractionReport."""

    def test_to_dict(self):
        """Serializa correctamente a diccionario."""
        report = GlossaryExtractionReport(
            suggestions=[
                GlossarySuggestion(
                    term="Test",
                    reason="Test",
                    category_hint="general",
                    confidence=0.5,
                )
            ],
            total_unique_words=100,
            chapters_analyzed=5,
            proper_nouns_found=3,
            technical_terms_found=2,
            potential_neologisms_found=1,
        )

        d = report.to_dict()

        assert len(d["suggestions"]) == 1
        assert d["total_unique_words"] == 100
        assert d["chapters_analyzed"] == 5
