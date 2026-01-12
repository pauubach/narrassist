"""
Gestión de base de datos SQLite.

Incluye:
- Conexión segura con permisos restrictivos
- Migraciones de schema
- Transacciones y rollback
"""

import logging
import sqlite3
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from ..core.config import get_config

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_database_lock = threading.Lock()

# Versión del schema actual
SCHEMA_VERSION = 1

# SQL de creación de tablas
SCHEMA_SQL = """
-- Proyectos (un manuscrito = un proyecto)
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    document_path TEXT,
    document_fingerprint TEXT NOT NULL,
    document_format TEXT NOT NULL,
    word_count INTEGER,
    chapter_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_opened_at TEXT,
    analysis_status TEXT DEFAULT 'pending',
    analysis_progress REAL DEFAULT 0.0,
    settings_json TEXT
);

-- Índice para búsqueda por fingerprint
CREATE INDEX IF NOT EXISTS idx_projects_fingerprint ON projects(document_fingerprint);

-- Capítulos detectados
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_number INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    word_count INTEGER,
    structure_type TEXT DEFAULT 'chapter',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id);

-- Entidades (personajes, lugares, objetos)
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,  -- character, location, object, organization
    canonical_name TEXT NOT NULL,
    importance TEXT DEFAULT 'secondary',  -- protagonist, secondary, minor, mentioned
    description TEXT,
    first_appearance_char INTEGER,
    mention_count INTEGER DEFAULT 0,
    merged_from_ids TEXT,  -- JSON array de IDs fusionados
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

-- Menciones de entidades en el texto
CREATE TABLE IF NOT EXISTS entity_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    chapter_id INTEGER,
    surface_form TEXT NOT NULL,  -- Texto tal como aparece
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    context_before TEXT,
    context_after TEXT,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'ner',  -- ner, coref, manual, gazetteer
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_mentions_entity ON entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_chapter ON entity_mentions(chapter_id);

-- Atributos de entidades
CREATE TABLE IF NOT EXISTS entity_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    attribute_type TEXT NOT NULL,  -- physical, psychological, social, role
    attribute_key TEXT NOT NULL,
    attribute_value TEXT NOT NULL,
    source_mention_id INTEGER,
    confidence REAL DEFAULT 1.0,
    is_verified INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (source_mention_id) REFERENCES entity_mentions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_attributes_entity ON entity_attributes(entity_id);

-- Evidencias de atributos (múltiples ubicaciones para un mismo atributo)
CREATE TABLE IF NOT EXISTS attribute_evidences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attribute_id INTEGER NOT NULL,

    -- Ubicación en el documento
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    chapter INTEGER,
    page INTEGER,           -- Calculado con calculate_page_and_line()
    line INTEGER,           -- Calculado con calculate_page_and_line()

    -- Contexto
    excerpt TEXT NOT NULL,

    -- Metadata de extracción
    extraction_method TEXT NOT NULL,  -- direct_description, action_inference, dialogue, unknown
    keywords TEXT,                    -- JSON array: ["decidida", "determinación"]
    confidence REAL DEFAULT 1.0,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (attribute_id) REFERENCES entity_attributes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_attribute ON attribute_evidences(attribute_id);
CREATE INDEX IF NOT EXISTS idx_evidence_chapter ON attribute_evidences(chapter);

-- Alertas generadas (sistema centralizado)
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,

    -- Clasificación
    category TEXT NOT NULL,  -- consistency, style, focalization, structure, world, entity, other
    severity TEXT NOT NULL,  -- critical, warning, info, hint
    alert_type TEXT NOT NULL,  -- Tipo específico (attribute_inconsistency, lexical_repetition, etc.)

    -- Contenido
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    explanation TEXT NOT NULL,
    suggestion TEXT,

    -- Ubicación
    chapter INTEGER,
    scene INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    excerpt TEXT DEFAULT '',

    -- Entidades relacionadas (JSON array de IDs)
    entity_ids TEXT DEFAULT '[]',

    -- Metadata
    confidence REAL DEFAULT 0.8,
    source_module TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,

    -- Estado
    status TEXT DEFAULT 'new',  -- new, open, acknowledged, in_progress, resolved, dismissed, auto_resolved
    resolved_at TEXT,
    resolution_note TEXT DEFAULT '',

    -- Datos adicionales específicos del tipo (JSON)
    extra_data TEXT DEFAULT '{}',

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_project ON alerts(project_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON alerts(category);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_chapter ON alerts(chapter);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_project_status ON alerts(project_id, status);

-- Historial de acciones del revisor
CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- alert_resolved, alert_dismissed, entity_merged, etc.
    target_type TEXT,  -- alert, entity, attribute
    target_id INTEGER,
    old_value_json TEXT,
    new_value_json TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_project ON review_history(project_id);
CREATE INDEX IF NOT EXISTS idx_history_action ON review_history(action_type);

-- Sesiones de trabajo
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT,
    duration_seconds INTEGER,
    alerts_reviewed INTEGER DEFAULT 0,
    alerts_resolved INTEGER DEFAULT 0,
    entities_merged INTEGER DEFAULT 0,
    last_position_char INTEGER,
    last_chapter_id INTEGER,
    notes TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);

-- Metadatos del schema
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Insertar versión del schema
INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', '1');
"""


class Database:
    """
    Conexión a base de datos SQLite con medidas de seguridad.

    Características:
    - Permisos restrictivos en archivo (solo owner)
    - WAL mode para mejor concurrencia
    - Foreign keys habilitadas
    - Transacciones explícitas
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa conexión a base de datos.

        Args:
            db_path: Ruta al archivo SQLite. Si None, usa config.
        """
        config = get_config()
        self.db_path = db_path or config.db_path
        self._is_memory = self.db_path == ":memory:" or (
            isinstance(self.db_path, str) and self.db_path.startswith(":")
        )
        # Para :memory: mantenemos una conexión persistente
        self._shared_connection: Optional[sqlite3.Connection] = None
        self._ensure_secure_permissions()
        self._initialize_schema()

    def _ensure_secure_permissions(self) -> None:
        """Asegura que solo el owner pueda acceder al archivo (Unix only)."""
        # chmod no funciona en Windows
        if sys.platform == "win32":
            return

        # Si es :memory: o db_path es un string especial, no hacer nada
        if isinstance(self.db_path, str):
            if self.db_path == ":memory:" or self.db_path.startswith(":"):
                return
            self.db_path = Path(self.db_path)

        if self.db_path.exists():
            self.db_path.chmod(0o600)

        # Lo mismo para WAL y journal
        for suffix in ["-wal", "-shm", "-journal"]:
            aux_path = Path(str(self.db_path) + suffix)
            if aux_path.exists():
                aux_path.chmod(0o600)

    def _initialize_schema(self) -> None:
        """Crea tablas si no existen."""
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
            logger.info(f"Schema inicializado en {self.db_path}")

    def _create_connection(self) -> sqlite3.Connection:
        """Crea y configura una nueva conexión."""
        conn = sqlite3.connect(
            str(self.db_path),
            isolation_level="DEFERRED",
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.execute("PRAGMA foreign_keys = ON")
        # WAL no funciona con :memory:
        if not self._is_memory:
            conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager para conexión segura.

        Para bases de datos en memoria, reutiliza la misma conexión.
        Para bases de datos en archivo, crea una nueva conexión por operación.

        Yields:
            Conexión SQLite configurada
        """
        if self._is_memory:
            # Para :memory: usamos conexión compartida
            if self._shared_connection is None:
                self._shared_connection = self._create_connection()
            try:
                yield self._shared_connection
                self._shared_connection.commit()
            except Exception:
                self._shared_connection.rollback()
                raise
        else:
            # Para archivos, nueva conexión por operación
            conn = self._create_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager para transacción explícita.

        Uso:
            with db.transaction() as conn:
                conn.execute("INSERT ...")
                conn.execute("UPDATE ...")
                # Commit automático al salir, rollback si excepción
        """
        if self._is_memory:
            # Para :memory: usamos conexión compartida
            if self._shared_connection is None:
                self._shared_connection = self._create_connection()
            try:
                self._shared_connection.execute("BEGIN IMMEDIATE")
                yield self._shared_connection
                self._shared_connection.commit()
            except Exception:
                self._shared_connection.rollback()
                raise
        else:
            # Para archivos, nueva conexión
            conn = self._create_connection()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecuta SQL y retorna cursor."""
        with self.connection() as conn:
            return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Ejecuta SQL múltiples veces."""
        with self.connection() as conn:
            return conn.executemany(sql, params_list)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Ejecuta y retorna una fila."""
        with self.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Ejecuta y retorna todas las filas."""
        with self.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def get_schema_version(self) -> int:
        """Retorna versión actual del schema."""
        row = self.fetchone("SELECT value FROM schema_info WHERE key = 'version'")
        return int(row["value"]) if row else 0


# Singleton
_database: Optional[Database] = None


def get_database(db_path: Optional[Path] = None) -> Database:
    """Obtiene instancia singleton de base de datos (thread-safe)."""
    global _database
    if _database is None or (db_path and db_path != _database.db_path):
        with _database_lock:
            # Double-checked locking
            if _database is None or (db_path and db_path != _database.db_path):
                _database = Database(db_path)
    return _database


def reset_database() -> None:
    """Resetea el singleton de base de datos (thread-safe, para testing)."""
    global _database
    with _database_lock:
        _database = None
