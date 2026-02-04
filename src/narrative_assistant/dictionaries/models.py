"""
Modelos de datos para el sistema de diccionarios.

Define las estructuras de datos para entradas de diccionario,
sinónimos, relaciones entre palabras, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DictionarySource(Enum):
    """Fuentes de diccionario disponibles."""

    WIKTIONARY = "wiktionary"  # Wiktionary español
    SYNONYMS = "synonyms"  # Diccionario de sinónimos/antónimos
    CUSTOM = "custom"  # Diccionario personalizado del usuario
    EXTERNAL = "external"  # Referencia a diccionario externo (RAE, etc.)


class WordRelationType(Enum):
    """Tipos de relación entre palabras."""

    SYNONYM = "synonym"  # Sinónimo
    ANTONYM = "antonym"  # Antónimo
    HYPERNYM = "hypernym"  # Hiperónimo (categoría más general)
    HYPONYM = "hyponym"  # Hipónimo (categoría más específica)
    RELATED = "related"  # Relacionado semánticamente
    VARIANT = "variant"  # Variante ortográfica


class GrammaticalCategory(Enum):
    """Categorías gramaticales."""

    NOUN = "noun"  # Sustantivo
    VERB = "verb"  # Verbo
    ADJECTIVE = "adjective"  # Adjetivo
    ADVERB = "adverb"  # Adverbio
    PRONOUN = "pronoun"  # Pronombre
    PREPOSITION = "preposition"  # Preposición
    CONJUNCTION = "conjunction"  # Conjunción
    INTERJECTION = "interjection"  # Interjección
    DETERMINER = "determiner"  # Determinante
    OTHER = "other"  # Otra categoría


@dataclass
class Definition:
    """Una definición de una palabra."""

    text: str  # Texto de la definición
    category: GrammaticalCategory | None = None  # Categoría gramatical
    domain: str | None = None  # Dominio/campo (medicina, derecho, etc.)
    register: str | None = None  # Registro (formal, coloquial, etc.)
    region: str | None = None  # Región (España, México, etc.)
    examples: list[str] = field(default_factory=list)  # Ejemplos de uso
    notes: str | None = None  # Notas adicionales


@dataclass
class WordRelation:
    """Relación entre dos palabras."""

    word: str  # Palabra relacionada
    relation_type: WordRelationType  # Tipo de relación
    confidence: float = 1.0  # Confianza en la relación (0.0-1.0)
    context: str | None = None  # Contexto en que aplica


@dataclass
class Etymology:
    """Información etimológica de una palabra."""

    origin_language: str | None = None  # Idioma de origen
    original_word: str | None = None  # Palabra original
    meaning: str | None = None  # Significado original
    notes: str | None = None  # Notas adicionales


@dataclass
class DictionaryEntry:
    """
    Entrada completa de diccionario para una palabra.

    Combina información de múltiples fuentes.
    """

    word: str  # Palabra normalizada (minúsculas, sin acentos opcionales)
    lemma: str  # Lema (forma canónica)
    definitions: list[Definition] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    relations: list[WordRelation] = field(default_factory=list)
    etymology: Etymology | None = None
    pronunciation: str | None = None  # Pronunciación IPA
    syllables: str | None = None  # División silábica
    frequency: float | None = None  # Frecuencia de uso (0.0-1.0)
    sources: list[DictionarySource] = field(default_factory=list)
    last_updated: datetime | None = None

    def has_definitions(self) -> bool:
        """Verifica si tiene definiciones."""
        return len(self.definitions) > 0

    def has_synonyms(self) -> bool:
        """Verifica si tiene sinónimos."""
        return len(self.synonyms) > 0

    def get_primary_definition(self) -> str | None:
        """Obtiene la definición principal."""
        if self.definitions:
            return self.definitions[0].text
        return None

    def get_categories(self) -> list[GrammaticalCategory]:
        """Obtiene las categorías gramaticales de las definiciones."""
        categories = set()
        for defn in self.definitions:
            if defn.category:
                categories.add(defn.category)
        return list(categories)

    def to_dict(self) -> dict:
        """Convierte a diccionario serializable."""
        return {
            "word": self.word,
            "lemma": self.lemma,
            "definitions": [
                {
                    "text": d.text,
                    "category": d.category.value if d.category else None,
                    "domain": d.domain,
                    "register": d.register,
                    "region": d.region,
                    "examples": d.examples,
                    "notes": d.notes,
                }
                for d in self.definitions
            ],
            "synonyms": self.synonyms,
            "antonyms": self.antonyms,
            "relations": [
                {
                    "word": r.word,
                    "type": r.relation_type.value,
                    "confidence": r.confidence,
                    "context": r.context,
                }
                for r in self.relations
            ],
            "etymology": {
                "origin_language": self.etymology.origin_language,
                "original_word": self.etymology.original_word,
                "meaning": self.etymology.meaning,
                "notes": self.etymology.notes,
            }
            if self.etymology
            else None,
            "pronunciation": self.pronunciation,
            "syllables": self.syllables,
            "frequency": self.frequency,
            "sources": [s.value for s in self.sources],
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass
class SynonymEntry:
    """Entrada específica para sinónimos/antónimos."""

    word: str
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)


@dataclass
class ExternalDictionaryLink:
    """Enlace a diccionario externo."""

    name: str  # Nombre del diccionario (RAE, María Moliner, etc.)
    base_url: str  # URL base para consultas
    word_url_template: str  # Template para URL de palabra (e.g., "{base}/{word}")
    description: str  # Descripción del diccionario
    requires_license: bool = True  # Si requiere licencia/compra

    def get_word_url(self, word: str) -> str:
        """Genera URL para una palabra específica."""
        import urllib.parse

        encoded_word = urllib.parse.quote(word)
        return self.word_url_template.format(base=self.base_url, word=encoded_word)


# Diccionarios externos conocidos (para enlaces, no para datos)
EXTERNAL_DICTIONARIES = {
    "rae": ExternalDictionaryLink(
        name="Diccionario de la RAE",
        base_url="https://dle.rae.es",
        word_url_template="{base}/{word}",
        description="Diccionario de la lengua española de la Real Academia Española",
        requires_license=False,  # Consulta web gratuita
    ),
    "moliner": ExternalDictionaryLink(
        name="María Moliner",
        base_url="https://www.diccionariodemariamoliner.com",
        word_url_template="{base}/buscar?q={word}",
        description="Diccionario de uso del español de María Moliner",
        requires_license=True,
    ),
    "oxford_spanish": ExternalDictionaryLink(
        name="Oxford Spanish Dictionary",
        base_url="https://www.lexico.com/es",
        word_url_template="{base}/definicion/{word}",
        description="Diccionario Oxford de español",
        requires_license=False,
    ),
    "wordreference": ExternalDictionaryLink(
        name="WordReference",
        base_url="https://www.wordreference.com",
        word_url_template="{base}/definicion/{word}",
        description="WordReference - Definiciones y sinónimos",
        requires_license=False,
    ),
}
