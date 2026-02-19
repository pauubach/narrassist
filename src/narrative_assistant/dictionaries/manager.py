"""
Gestor de diccionarios con descarga bajo demanda.

Este módulo coordina múltiples fuentes de diccionario y gestiona
la descarga inicial de datos. Todo funciona 100% offline después
de la primera descarga.

Los datos se almacenan en ~/.narrative_assistant/dictionaries/

Uso:
    from narrative_assistant.dictionaries import get_dictionary_manager

    manager = get_dictionary_manager()
    result = manager.lookup("efímero")
"""

import json
import logging
import os
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from .models import (
    EXTERNAL_DICTIONARIES,
    DictionaryEntry,
    DictionarySource,
)
from .sources import (
    BaseDictionarySource,
    CustomDictionarySource,
    SynonymSource,
    WiktionarySource,
    normalize_word,
)

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_manager_lock = threading.Lock()
_dictionary_manager: Optional["DictionaryManager"] = None


# URLs de descarga de datos (fuentes libres)
# Nota: Estos son placeholders. En producción usaríamos mirrors propios
# o descargaríamos de fuentes oficiales como dumps de Wiktionary.
DICTIONARY_DATA_SOURCES = {
    "wiktionary": {
        "url": "https://dumps.wikimedia.org/eswiktionary/latest/",
        "filename": "eswiktionary.db",
        "description": "Wiktionary español - Definiciones",
        "size_mb": 80,
    },
    "synonyms": {
        "url": "https://github.com/lexibank/spanish-synonyms/",
        "filename": "synonyms.db",
        "description": "Sinónimos y antónimos del español",
        "size_mb": 20,
    },
}


@dataclass
class DictionaryDownloadError(NarrativeError):
    """Error al descargar datos de diccionario."""

    source_name: str = ""
    reason: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: str | None = None

    def __post_init__(self):
        if not self.message:
            self.message = f"Error descargando diccionario '{self.source_name}': {self.reason}"
        if self.user_message is None:
            self.user_message = (
                f"No se pudo descargar el diccionario '{self.source_name}'.\n"
                f"Razón: {self.reason}\n\n"
                "El diccionario funcionará sin esta fuente."
            )
        super().__post_init__()


class DictionaryManager:
    """
    Gestor principal de diccionarios.

    Características:
    - Combina múltiples fuentes de datos
    - Descarga bajo demanda
    - Cache en ~/.narrative_assistant/dictionaries/
    - Thread-safe
    - 100% offline después de descarga inicial
    """

    def __init__(self, data_dir: Path | None = None):
        """
        Inicializa el gestor de diccionarios.

        Args:
            data_dir: Directorio para almacenar datos.
                     Default: NA_DATA_DIR/dictionaries o ~/.narrative_assistant/dictionaries/
        """
        # Determinar directorio de datos
        if data_dir is not None:
            self.data_dir = Path(data_dir)
        elif env_dir := os.getenv("NA_DATA_DIR"):
            self.data_dir = Path(env_dir) / "dictionaries"
        else:
            self.data_dir = Path.home() / ".narrative_assistant" / "dictionaries"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Inicializar fuentes
        self._sources: dict[DictionarySource, BaseDictionarySource] = {}
        self._init_sources()

        # Lock para descargas
        self._download_lock = threading.Lock()

        logger.info(f"DictionaryManager initialized. Data dir: {self.data_dir}")

    def _init_sources(self) -> None:
        """Inicializa las fuentes de diccionario."""
        # Wiktionary
        wiktionary_db = self.data_dir / "wiktionary.db"
        self._sources[DictionarySource.WIKTIONARY] = WiktionarySource(wiktionary_db)

        # Sinónimos (auto-build from WordNet if empty)
        synonyms_db = self.data_dir / "synonyms.db"
        self._ensure_synonyms_db(synonyms_db)
        self._sources[DictionarySource.SYNONYMS] = SynonymSource(synonyms_db)

        # Diccionario personalizado
        custom_path = self.data_dir / "custom_dictionary.json"
        self._sources[DictionarySource.CUSTOM] = CustomDictionarySource(custom_path)

    def _ensure_synonyms_db(self, db_path: Path) -> None:
        """Auto-build synonyms.db from WordNet OMW 1.4 if empty or missing."""
        try:
            count = 0
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                try:
                    count = conn.execute("SELECT COUNT(*) FROM synonyms").fetchone()[0]
                except Exception:
                    count = 0
                finally:
                    conn.close()

            if count >= 100:
                return  # Already populated

            logger.info("synonyms.db vacío o no existe. Intentando auto-build desde WordNet OMW 1.4...")
            try:
                from scripts.build_thesaurus_db import build
                build(force=True)
                logger.info("synonyms.db generado exitosamente desde WordNet.")
            except ImportError:
                # Try direct import path
                try:
                    import importlib.util
                    # Find scripts/build_thesaurus_db.py relative to project root
                    script_candidates = [
                        Path(__file__).parent.parent.parent.parent / "scripts" / "build_thesaurus_db.py",
                        Path.cwd() / "scripts" / "build_thesaurus_db.py",
                    ]
                    for script_path in script_candidates:
                        if script_path.exists():
                            spec = importlib.util.spec_from_file_location("build_thesaurus_db", str(script_path))
                            if spec and spec.loader:
                                mod = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(mod)
                                mod.build(force=True)
                                logger.info("synonyms.db generado exitosamente desde WordNet.")
                                return
                    logger.warning(
                        "No se encontró scripts/build_thesaurus_db.py. "
                        "Ejecuta manualmente: python scripts/build_thesaurus_db.py"
                    )
                except Exception as e:
                    logger.warning(f"Auto-build de synonyms.db falló: {e}. La app funcionará sin sinónimos.")
            except Exception as e:
                logger.warning(f"Auto-build de synonyms.db falló: {e}. La app funcionará sin sinónimos.")
        except Exception as e:
            logger.warning(f"Error verificando synonyms.db: {e}. La app funcionará sin sinónimos.")

    def lookup(
        self,
        word: str,
        sources: list[DictionarySource] | None = None,
        merge_results: bool = True,
    ) -> Result[DictionaryEntry]:
        """
        Busca una palabra en los diccionarios.

        Args:
            word: Palabra a buscar
            sources: Fuentes a consultar (None = todas disponibles)
            merge_results: Si True, combina resultados de múltiples fuentes

        Returns:
            Result con DictionaryEntry si se encuentra
        """
        if not word or not word.strip():
            return Result.failure(
                NarrativeError(
                    message="Palabra vacía",
                    severity=ErrorSeverity.RECOVERABLE,
                    user_message="Por favor, introduce una palabra para buscar.",
                )
            )

        # Determinar fuentes a consultar
        if sources is None:
            sources = [
                DictionarySource.CUSTOM,  # Prioridad a personalizado
                DictionarySource.WIKTIONARY,
                DictionarySource.SYNONYMS,
            ]

        results: list[DictionaryEntry] = []

        for source_type in sources:
            source = self._sources.get(source_type)
            if source and source.is_available():
                entry = source.lookup(word)
                if entry:
                    results.append(entry)
                    if not merge_results:
                        break

        if not results:
            return Result.failure(
                NarrativeError(
                    message=f"Palabra no encontrada: {word}",
                    severity=ErrorSeverity.DEGRADED,
                    user_message=f"No se encontró '{word}' en los diccionarios locales.",
                )
            )

        # Combinar resultados si hay múltiples
        if len(results) == 1:
            return Result.success(results[0])

        merged = self._merge_entries(word, results)
        return Result.success(merged)

    def _merge_entries(self, word: str, entries: list[DictionaryEntry]) -> DictionaryEntry:
        """Combina múltiples entradas en una sola."""
        if not entries:
            return DictionaryEntry(word=word, lemma=word)

        # Usar la primera como base
        merged = DictionaryEntry(
            word=entries[0].word,
            lemma=entries[0].lemma,
        )

        all_definitions = []
        all_synonyms = set()
        all_antonyms = set()
        all_relations = []
        all_sources = set()

        for entry in entries:
            all_definitions.extend(entry.definitions)
            all_synonyms.update(entry.synonyms)
            all_antonyms.update(entry.antonyms)
            all_relations.extend(entry.relations)
            all_sources.update(entry.sources)

            # Usar etimología de la primera que la tenga
            if not merged.etymology and entry.etymology:
                merged.etymology = entry.etymology

            # Usar pronunciación de la primera que la tenga
            if not merged.pronunciation and entry.pronunciation:
                merged.pronunciation = entry.pronunciation

            if not merged.syllables and entry.syllables:
                merged.syllables = entry.syllables

        merged.definitions = all_definitions
        merged.synonyms = sorted(all_synonyms)
        merged.antonyms = sorted(all_antonyms)
        merged.relations = all_relations
        merged.sources = list(all_sources)

        return merged

    def get_synonyms(self, word: str) -> list[str]:
        """
        Obtiene sinónimos de una palabra.

        Args:
            word: Palabra a buscar

        Returns:
            Lista de sinónimos
        """
        result = self.lookup(word, sources=[DictionarySource.SYNONYMS])
        if result.is_success and result.value is not None:
            return result.value.synonyms
        return []

    def get_antonyms(self, word: str) -> list[str]:
        """
        Obtiene antónimos de una palabra.

        Args:
            word: Palabra a buscar

        Returns:
            Lista de antónimos
        """
        result = self.lookup(word, sources=[DictionarySource.SYNONYMS])
        if result.is_success and result.value is not None:
            return result.value.antonyms
        return []

    def search_prefix(self, prefix: str, limit: int = 20) -> list[str]:
        """
        Busca palabras que empiecen con un prefijo.

        Args:
            prefix: Prefijo a buscar
            limit: Máximo de resultados

        Returns:
            Lista de palabras que coinciden
        """
        results = set()

        for source in self._sources.values():
            if source.is_available():
                words = source.search_prefix(prefix, limit)
                results.update(words)
                if len(results) >= limit:
                    break

        return sorted(results)[:limit]

    def get_external_link(self, word: str, dictionary: str = "rae") -> str | None:
        """
        Genera un enlace a un diccionario externo.

        Args:
            word: Palabra a buscar
            dictionary: Diccionario externo (rae, moliner, etc.)

        Returns:
            URL para consultar en el diccionario externo
        """
        ext_dict = EXTERNAL_DICTIONARIES.get(dictionary)
        if ext_dict:
            return ext_dict.get_word_url(word)
        return None

    def get_all_external_links(self, word: str) -> dict[str, str]:
        """
        Genera enlaces a todos los diccionarios externos.

        Args:
            word: Palabra a buscar

        Returns:
            Dict {nombre: url}
        """
        return {
            name: ext_dict.get_word_url(word) for name, ext_dict in EXTERNAL_DICTIONARIES.items()
        }

    def get_status(self) -> dict:
        """
        Obtiene el estado de todas las fuentes.

        Returns:
            Dict con información de cada fuente
        """
        status = {}

        for source_type, source in self._sources.items():
            is_available = source.is_available()
            word_count = 0

            if is_available and hasattr(source, "get_word_count"):
                word_count = source.get_word_count()

            status[source_type.value] = {
                "available": is_available,
                "word_count": word_count,
                "type": source_type.value,
            }

        return status

    def ensure_dictionaries(
        self,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> Result[None]:
        """
        Asegura que los diccionarios estén disponibles.

        Si no existen localmente, intenta crearlos con datos básicos.
        En el futuro, esto podría descargar datos de fuentes públicas.

        Args:
            progress_callback: Callback para reportar progreso

        Returns:
            Result indicando éxito o fallo
        """
        with self._download_lock:
            # Verificar/crear Wiktionary
            wiktionary_source = self._sources.get(DictionarySource.WIKTIONARY)
            if wiktionary_source and not wiktionary_source.is_available():
                if progress_callback:
                    progress_callback("Inicializando diccionario Wiktionary...", 0.1)
                self._init_wiktionary_db()

            # Verificar/crear Sinónimos
            synonyms_source = self._sources.get(DictionarySource.SYNONYMS)
            if synonyms_source and not synonyms_source.is_available():
                if progress_callback:
                    progress_callback("Inicializando diccionario de sinónimos...", 0.5)
                self._init_synonyms_db()

            if progress_callback:
                progress_callback("Diccionarios listos", 1.0)

        return Result.success(None)

    def _init_wiktionary_db(self) -> None:
        """
        Inicializa la base de datos de Wiktionary con datos básicos.

        En el futuro, esto podría descargar datos completos.
        Por ahora, crea una BD con estructura y palabras de ejemplo.
        """
        db_path = self.data_dir / "wiktionary.db"

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Crear tablas
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    normalized TEXT NOT NULL,
                    lemma TEXT,
                    pronunciation TEXT,
                    syllables TEXT,
                    UNIQUE(normalized)
                );

                CREATE INDEX IF NOT EXISTS idx_words_normalized ON words(normalized);
                CREATE INDEX IF NOT EXISTS idx_words_lemma ON words(lemma);

                CREATE TABLE IF NOT EXISTS definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    category TEXT,
                    domain TEXT,
                    register TEXT,
                    region TEXT,
                    notes TEXT,
                    position INTEGER DEFAULT 0,
                    FOREIGN KEY (word_id) REFERENCES words(id)
                );

                CREATE INDEX IF NOT EXISTS idx_definitions_word ON definitions(word_id);

                CREATE TABLE IF NOT EXISTS examples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    definition_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (definition_id) REFERENCES definitions(id)
                );

                CREATE TABLE IF NOT EXISTS etymology (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word_id INTEGER NOT NULL UNIQUE,
                    origin_language TEXT,
                    original_word TEXT,
                    meaning TEXT,
                    notes TEXT,
                    FOREIGN KEY (word_id) REFERENCES words(id)
                );

                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

            # Insertar metadatos
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("version", "1.0"),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("source", "initial_setup"),
            )

            # Insertar algunas palabras de ejemplo
            sample_words = [
                ("efímero", "efímero", "adjective", "Que dura poco tiempo."),
                ("ubicuo", "ubicuo", "adjective", "Que está presente en todas partes."),
                ("prolijo", "prolijo", "adjective", "Largo, dilatado con exceso."),
                (
                    "parsimonia",
                    "parsimonia",
                    "noun",
                    "Lentitud y calma en el modo de hablar o actuar.",
                ),
                ("diáfano", "diáfano", "adjective", "Dicho de un cuerpo: Que deja pasar la luz."),
                ("incólume", "incólume", "adjective", "Sano, sin lesión ni menoscabo."),
                ("diatriba", "diatriba", "noun", "Discurso o escrito violento e injurioso."),
                ("acendrado", "acendrado", "adjective", "Puro, sin mancha ni defecto."),
                ("sempiterno", "sempiterno", "adjective", "Que durará siempre."),
                ("lacónico", "lacónico", "adjective", "Breve, conciso, que usa de pocas palabras."),
            ]

            for word, lemma, category, definition in sample_words:
                normalized = normalize_word(word)
                cursor.execute(
                    "INSERT OR IGNORE INTO words (word, normalized, lemma) VALUES (?, ?, ?)",
                    (word, normalized, lemma),
                )
                word_id = (
                    cursor.lastrowid
                    or cursor.execute(
                        "SELECT id FROM words WHERE normalized = ?", (normalized,)
                    ).fetchone()[0]
                )

                cursor.execute(
                    "INSERT INTO definitions (word_id, text, category, position) VALUES (?, ?, ?, 0)",
                    (word_id, definition, category),
                )

            conn.commit()
            conn.close()

            logger.info(f"Wiktionary DB initialized at {db_path}")

        except Exception as e:
            logger.error(f"Error initializing Wiktionary DB: {e}")

    def _init_synonyms_db(self) -> None:
        """
        Inicializa la base de datos de sinónimos con datos básicos.
        """
        db_path = self.data_dir / "synonyms.db"

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Crear tablas
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS synonyms (
                    word TEXT PRIMARY KEY,
                    synonyms TEXT,
                    antonyms TEXT
                );

                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

            # Insertar metadatos
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("version", "1.0"),
            )

            # Insertar algunos sinónimos de ejemplo
            sample_synonyms = [
                (
                    "grande",
                    ["enorme", "vasto", "amplio", "extenso", "inmenso"],
                    ["pequeño", "diminuto"],
                ),
                ("pequeño", ["diminuto", "minúsculo", "reducido", "chico"], ["grande", "enorme"]),
                ("rápido", ["veloz", "raudo", "presto", "ligero", "ágil"], ["lento", "pausado"]),
                ("lento", ["pausado", "calmado", "tardo", "perezoso"], ["rápido", "veloz"]),
                ("bueno", ["excelente", "óptimo", "bondadoso", "benévolo"], ["malo", "pésimo"]),
                ("malo", ["pésimo", "terrible", "nefasto", "perverso"], ["bueno", "excelente"]),
                ("feliz", ["contento", "alegre", "dichoso", "jubiloso"], ["triste", "infeliz"]),
                ("triste", ["afligido", "apesadumbrado", "melancólico"], ["feliz", "alegre"]),
                ("hermoso", ["bello", "bonito", "precioso", "lindo", "guapo"], ["feo", "horrible"]),
                ("feo", ["horrible", "espantoso", "horroroso"], ["hermoso", "bello"]),
                (
                    "comenzar",
                    ["empezar", "iniciar", "principiar"],
                    ["terminar", "acabar", "finalizar"],
                ),
                (
                    "terminar",
                    ["acabar", "finalizar", "concluir"],
                    ["comenzar", "empezar", "iniciar"],
                ),
                (
                    "hablar",
                    ["decir", "expresar", "comunicar", "conversar"],
                    ["callar", "silenciar"],
                ),
                ("callar", ["silenciar", "enmudecer", "omitir"], ["hablar", "decir"]),
                ("crear", ["inventar", "generar", "producir", "idear"], ["destruir", "eliminar"]),
                ("destruir", ["demoler", "aniquilar", "arruinar"], ["crear", "construir"]),
            ]

            for word, syns, ants in sample_synonyms:
                cursor.execute(
                    "INSERT OR REPLACE INTO synonyms (word, synonyms, antonyms) VALUES (?, ?, ?)",
                    (word, json.dumps(syns), json.dumps(ants)),
                )

            conn.commit()
            conn.close()

            logger.info(f"Synonyms DB initialized at {db_path}")

        except Exception as e:
            logger.error(f"Error initializing synonyms DB: {e}")

    def add_custom_word(
        self,
        word: str,
        definition: str,
        category: str | None = None,
        synonyms: list[str] | None = None,
        antonyms: list[str] | None = None,
    ) -> Result[None]:
        """
        Añade una palabra al diccionario personalizado.

        Args:
            word: Palabra a añadir
            definition: Definición
            category: Categoría gramatical
            synonyms: Sinónimos
            antonyms: Antónimos

        Returns:
            Result indicando éxito
        """
        try:
            custom_source = self._sources.get(DictionarySource.CUSTOM)
            if custom_source and isinstance(custom_source, CustomDictionarySource):
                custom_source.add_word(word, definition, category, synonyms, antonyms)
                return Result.success(None)
            return Result.failure(
                NarrativeError(
                    message="Custom dictionary not available",
                    severity=ErrorSeverity.FATAL,
                )
            )
        except Exception as e:
            return Result.failure(
                NarrativeError(
                    message=f"Error adding word: {e}",
                    severity=ErrorSeverity.FATAL,
                )
            )

    def remove_custom_word(self, word: str) -> Result[bool]:
        """
        Elimina una palabra del diccionario personalizado.

        Args:
            word: Palabra a eliminar

        Returns:
            Result con True si se eliminó
        """
        try:
            custom_source = self._sources.get(DictionarySource.CUSTOM)
            if custom_source and isinstance(custom_source, CustomDictionarySource):
                removed = custom_source.remove_word(word)
                return Result.success(removed)
            return Result.failure(
                NarrativeError(
                    message="Custom dictionary not available",
                    severity=ErrorSeverity.FATAL,
                )
            )
        except Exception as e:
            return Result.failure(
                NarrativeError(
                    message=f"Error removing word: {e}",
                    severity=ErrorSeverity.FATAL,
                )
            )

    def list_custom_words(self) -> list[str]:
        """Lista todas las palabras del diccionario personalizado."""
        custom_source = self._sources.get(DictionarySource.CUSTOM)
        if custom_source and isinstance(custom_source, CustomDictionarySource):
            return custom_source.list_words()
        return []


def get_dictionary_manager() -> DictionaryManager:
    """
    Obtiene el gestor de diccionarios singleton (thread-safe).

    Returns:
        Instancia de DictionaryManager
    """
    global _dictionary_manager

    if _dictionary_manager is None:
        with _manager_lock:
            # Double-checked locking
            if _dictionary_manager is None:
                _dictionary_manager = DictionaryManager()

    return _dictionary_manager


def reset_dictionary_manager() -> None:
    """Resetea el singleton del gestor de diccionarios (para testing)."""
    global _dictionary_manager
    with _manager_lock:
        _dictionary_manager = None
