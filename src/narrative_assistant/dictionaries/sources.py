"""
Fuentes de diccionario para consulta offline.

Cada fuente implementa la interfaz BaseDictionarySource y proporciona
métodos para buscar palabras, cargar datos y verificar disponibilidad.

Fuentes implementadas:
- WiktionarySource: Datos de Wiktionary español (definiciones)
- SynonymSource: Diccionario de sinónimos/antónimos
- CustomDictionarySource: Diccionarios personalizados del usuario
"""

import json
import logging
import sqlite3
import threading
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path

from .models import (
    Definition,
    DictionaryEntry,
    DictionarySource,
    Etymology,
    GrammaticalCategory,
    WordRelation,
    WordRelationType,
)

logger = logging.getLogger(__name__)


def normalize_word(word: str) -> str:
    """
    Normaliza una palabra para búsqueda.

    - Convierte a minúsculas
    - Elimina acentos opcionales (mantiene ñ)
    - Elimina espacios extra
    """
    word = word.lower().strip()
    # Normalizar unicode (NFD descompone, NFC recompone)
    # Mantener ñ pero normalizar otros caracteres
    normalized = ""
    for char in unicodedata.normalize("NFD", word):
        if unicodedata.category(char) != "Mn" or char == "\u0303":  # Mantener tilde de ñ
            normalized += char
    return unicodedata.normalize("NFC", normalized)


class BaseDictionarySource(ABC):
    """
    Clase base abstracta para fuentes de diccionario.

    Cada fuente debe implementar:
    - lookup(): Buscar una palabra
    - is_available(): Verificar si la fuente está disponible
    - get_source_type(): Obtener el tipo de fuente
    """

    @abstractmethod
    def lookup(self, word: str) -> DictionaryEntry | None:
        """
        Busca una palabra en esta fuente.

        Args:
            word: Palabra a buscar

        Returns:
            DictionaryEntry si se encuentra, None si no existe
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si la fuente está disponible para consultas."""
        pass

    @abstractmethod
    def get_source_type(self) -> DictionarySource:
        """Obtiene el tipo de fuente."""
        pass

    def search_prefix(self, prefix: str, limit: int = 20) -> list[str]:
        """
        Busca palabras que empiecen con un prefijo.

        Args:
            prefix: Prefijo a buscar
            limit: Máximo de resultados

        Returns:
            Lista de palabras que coinciden
        """
        return []  # Implementación por defecto: vacío

    def search_similar(self, word: str, limit: int = 10) -> list[str]:
        """
        Busca palabras similares (para sugerencias de corrección).

        Args:
            word: Palabra de referencia
            limit: Máximo de resultados

        Returns:
            Lista de palabras similares
        """
        return []


class WiktionarySource(BaseDictionarySource):
    """
    Fuente de datos de Wiktionary español.

    Los datos se almacenan en una base de datos SQLite local
    que se descarga/actualiza desde dumps de Wiktionary.

    Estructura de la BD:
    - words: palabra, lema, pronunciación, sílabas
    - definitions: palabra_id, texto, categoría, dominio, registro
    - examples: definición_id, texto
    - etymology: palabra_id, idioma_origen, palabra_original, significado
    """

    def __init__(self, db_path: Path):
        """
        Inicializa la fuente Wiktionary.

        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene conexión thread-local a la BD."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def is_available(self) -> bool:
        """Verifica si la BD existe y es válida."""
        if not self.db_path.exists():
            return False

        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT COUNT(*) FROM words")
            count = cursor.fetchone()[0]
            return bool(count > 0)
        except Exception as e:
            logger.warning(f"Wiktionary DB not available: {e}")
            return False

    def get_source_type(self) -> DictionarySource:
        return DictionarySource.WIKTIONARY

    def lookup(self, word: str) -> DictionaryEntry | None:
        """Busca una palabra en Wiktionary."""
        if not self.is_available():
            return None

        normalized = normalize_word(word)

        try:
            conn = self._get_connection()

            # Buscar palabra
            cursor = conn.execute(
                """
                SELECT id, word, lemma, pronunciation, syllables
                FROM words
                WHERE normalized = ? OR lemma = ?
                LIMIT 1
                """,
                (normalized, normalized),
            )
            row = cursor.fetchone()

            if not row:
                return None

            word_id = row["id"]

            # Obtener definiciones
            definitions = []
            def_cursor = conn.execute(
                """
                SELECT id, text, category, domain, register, region, notes
                FROM definitions
                WHERE word_id = ?
                ORDER BY position
                """,
                (word_id,),
            )

            for def_row in def_cursor:
                # Obtener ejemplos de esta definición
                ex_cursor = conn.execute(
                    "SELECT text FROM examples WHERE definition_id = ?",
                    (def_row["id"],),
                )
                examples = [ex["text"] for ex in ex_cursor]

                category = None
                if def_row["category"]:
                    try:
                        category = GrammaticalCategory(def_row["category"])
                    except ValueError:
                        category = GrammaticalCategory.OTHER

                definitions.append(
                    Definition(
                        text=def_row["text"],
                        category=category,
                        domain=def_row["domain"],
                        register=def_row["register"],
                        region=def_row["region"],
                        examples=examples,
                        notes=def_row["notes"],
                    )
                )

            # Obtener etimología
            etymology = None
            etym_cursor = conn.execute(
                """
                SELECT origin_language, original_word, meaning, notes
                FROM etymology
                WHERE word_id = ?
                """,
                (word_id,),
            )
            etym_row = etym_cursor.fetchone()
            if etym_row:
                etymology = Etymology(
                    origin_language=etym_row["origin_language"],
                    original_word=etym_row["original_word"],
                    meaning=etym_row["meaning"],
                    notes=etym_row["notes"],
                )

            return DictionaryEntry(
                word=row["word"],
                lemma=row["lemma"] or row["word"],
                definitions=definitions,
                etymology=etymology,
                pronunciation=row["pronunciation"],
                syllables=row["syllables"],
                sources=[DictionarySource.WIKTIONARY],
            )

        except Exception as e:
            logger.error(f"Error looking up '{word}' in Wiktionary: {e}")
            return None

    def search_prefix(self, prefix: str, limit: int = 20) -> list[str]:
        """Busca palabras por prefijo."""
        if not self.is_available():
            return []

        normalized = normalize_word(prefix)

        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT DISTINCT word FROM words
                WHERE normalized LIKE ? || '%'
                ORDER BY length(word), word
                LIMIT ?
                """,
                (normalized, limit),
            )
            return [row["word"] for row in cursor]
        except Exception as e:
            logger.error(f"Error searching prefix '{prefix}': {e}")
            return []

    def get_word_count(self) -> int:
        """Obtiene el número total de palabras."""
        if not self.is_available():
            return 0

        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT COUNT(*) FROM words")
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0


class SynonymSource(BaseDictionarySource):
    """
    Fuente de sinónimos y antónimos.

    Datos almacenados en SQLite con estructura simple:
    - synonyms: palabra, sinónimos (JSON array)
    - antonyms: palabra, antónimos (JSON array)
    """

    def __init__(self, db_path: Path):
        """
        Inicializa la fuente de sinónimos.

        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene conexión a la BD."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def is_available(self) -> bool:
        """Verifica si la BD existe."""
        if not self.db_path.exists():
            return False

        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT COUNT(*) FROM synonyms")
            count = cursor.fetchone()[0]
            return bool(count > 0)
        except Exception:
            return False

    def get_source_type(self) -> DictionarySource:
        return DictionarySource.SYNONYMS

    def lookup(self, word: str) -> DictionaryEntry | None:
        """Busca sinónimos/antónimos de una palabra."""
        if not self.is_available():
            return None

        normalized = normalize_word(word)

        try:
            conn = self._get_connection()

            # Buscar sinónimos
            cursor = conn.execute(
                "SELECT synonyms, antonyms FROM synonyms WHERE word = ?",
                (normalized,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            synonyms = json.loads(row["synonyms"]) if row["synonyms"] else []
            antonyms = json.loads(row["antonyms"]) if row["antonyms"] else []

            # Crear relaciones
            relations = []
            for syn in synonyms:
                relations.append(WordRelation(word=syn, relation_type=WordRelationType.SYNONYM))
            for ant in antonyms:
                relations.append(WordRelation(word=ant, relation_type=WordRelationType.ANTONYM))

            return DictionaryEntry(
                word=word,
                lemma=word,
                synonyms=synonyms,
                antonyms=antonyms,
                relations=relations,
                sources=[DictionarySource.SYNONYMS],
            )

        except Exception as e:
            logger.error(f"Error looking up synonyms for '{word}': {e}")
            return None

    def get_synonyms(self, word: str) -> list[str]:
        """Obtiene solo sinónimos de una palabra."""
        entry = self.lookup(word)
        return entry.synonyms if entry else []

    def get_antonyms(self, word: str) -> list[str]:
        """Obtiene solo antónimos de una palabra."""
        entry = self.lookup(word)
        return entry.antonyms if entry else []


class CustomDictionarySource(BaseDictionarySource):
    """
    Fuente de diccionario personalizado del usuario.

    Permite al usuario añadir definiciones, términos específicos
    del proyecto, jerga técnica, etc.

    Los datos se almacenan en JSON para fácil edición manual.
    """

    def __init__(self, dictionary_path: Path):
        """
        Inicializa el diccionario personalizado.

        Args:
            dictionary_path: Ruta al archivo JSON del diccionario
        """
        self.dictionary_path = dictionary_path
        self._data: dict | None = None
        self._lock = threading.Lock()

    def _load_data(self) -> dict:
        """Carga los datos del diccionario."""
        if self._data is not None:
            return self._data

        with self._lock:
            if self._data is not None:
                return self._data

            if not self.dictionary_path.exists():
                self._data = {"words": {}}
                return self._data

            try:
                with open(self.dictionary_path, encoding="utf-8") as f:
                    self._data = json.load(f)
                return self._data
            except Exception as e:
                logger.error(f"Error loading custom dictionary: {e}")
                self._data = {"words": {}}
                return self._data

    def _save_data(self) -> None:
        """Guarda los datos del diccionario."""
        if self._data is None:
            return

        try:
            self.dictionary_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dictionary_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving custom dictionary: {e}")

    def is_available(self) -> bool:
        """El diccionario personalizado siempre está disponible."""
        return True

    def get_source_type(self) -> DictionarySource:
        return DictionarySource.CUSTOM

    def lookup(self, word: str) -> DictionaryEntry | None:
        """Busca una palabra en el diccionario personalizado."""
        data = self._load_data()
        normalized = normalize_word(word)

        word_data = data.get("words", {}).get(normalized)
        if not word_data:
            return None

        # Convertir datos JSON a DictionaryEntry
        definitions = []
        for def_data in word_data.get("definitions", []):
            category = None
            if def_data.get("category"):
                try:
                    category = GrammaticalCategory(def_data["category"])
                except ValueError:
                    category = GrammaticalCategory.OTHER

            definitions.append(
                Definition(
                    text=def_data.get("text", ""),
                    category=category,
                    domain=def_data.get("domain"),
                    register=def_data.get("register"),
                    examples=def_data.get("examples", []),
                    notes=def_data.get("notes"),
                )
            )

        return DictionaryEntry(
            word=word_data.get("word", word),
            lemma=word_data.get("lemma", word),
            definitions=definitions,
            synonyms=word_data.get("synonyms", []),
            antonyms=word_data.get("antonyms", []),
            sources=[DictionarySource.CUSTOM],
        )

    def add_word(
        self,
        word: str,
        definition: str,
        category: str | None = None,
        synonyms: list[str] | None = None,
        antonyms: list[str] | None = None,
    ) -> None:
        """
        Añade una palabra al diccionario personalizado.

        Args:
            word: Palabra a añadir
            definition: Definición
            category: Categoría gramatical
            synonyms: Lista de sinónimos
            antonyms: Lista de antónimos
        """
        data = self._load_data()
        normalized = normalize_word(word)

        if "words" not in data:
            data["words"] = {}

        # Si ya existe, añadir definición
        if normalized in data["words"]:
            existing = data["words"][normalized]
            existing["definitions"].append(
                {
                    "text": definition,
                    "category": category,
                }
            )
            if synonyms:
                existing["synonyms"] = list(set(existing.get("synonyms", []) + synonyms))
            if antonyms:
                existing["antonyms"] = list(set(existing.get("antonyms", []) + antonyms))
        else:
            data["words"][normalized] = {
                "word": word,
                "lemma": word,
                "definitions": [{"text": definition, "category": category}],
                "synonyms": synonyms or [],
                "antonyms": antonyms or [],
            }

        self._save_data()

    def remove_word(self, word: str) -> bool:
        """
        Elimina una palabra del diccionario.

        Returns:
            True si se eliminó, False si no existía
        """
        data = self._load_data()
        normalized = normalize_word(word)

        if normalized in data.get("words", {}):
            del data["words"][normalized]
            self._save_data()
            return True
        return False

    def list_words(self) -> list[str]:
        """Lista todas las palabras del diccionario personalizado."""
        data = self._load_data()
        return sorted(data.get("words", {}).keys())

    def get_word_count(self) -> int:
        """Obtiene el número de palabras."""
        data = self._load_data()
        return len(data.get("words", {}))

    def reload(self) -> None:
        """Recarga los datos del archivo."""
        with self._lock:
            self._data = None
