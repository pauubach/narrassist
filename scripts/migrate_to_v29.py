#!/usr/bin/env python3
"""
Migración manual a SCHEMA_VERSION 29 (cache tables).
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".narrative_assistant" / "narrative_assistant.db"

CACHE_TABLES_SQL = """
-- v29: Tablas de cache para NER, correferencias y atributos

CREATE TABLE IF NOT EXISTS ner_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_fingerprint TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    entities_json TEXT NOT NULL,
    entity_count INTEGER DEFAULT 0,
    mention_count INTEGER DEFAULT 0,
    processed_chars INTEGER DEFAULT 0,
    cache_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, document_fingerprint, config_hash)
);

CREATE INDEX IF NOT EXISTS idx_ner_cache_lookup ON ner_cache(
    project_id, document_fingerprint, config_hash
);

CREATE TABLE IF NOT EXISTS coreference_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_fingerprint TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    chains_json TEXT NOT NULL,
    chain_count INTEGER DEFAULT 0,
    mention_count INTEGER DEFAULT 0,
    cache_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, document_fingerprint, config_hash)
);

CREATE INDEX IF NOT EXISTS idx_coreference_cache_lookup ON coreference_cache(
    project_id, document_fingerprint, config_hash
);

CREATE TABLE IF NOT EXISTS attribute_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_fingerprint TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    attributes_json TEXT NOT NULL,
    attribute_count INTEGER DEFAULT 0,
    evidence_count INTEGER DEFAULT 0,
    cache_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, document_fingerprint, config_hash)
);

CREATE INDEX IF NOT EXISTS idx_attribute_cache_lookup ON attribute_cache(
    project_id, document_fingerprint, config_hash
);
"""

def main():
    if not DB_PATH.exists():
        print(f"ERROR: Base de datos no encontrada: {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Ver schema version actual
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]
        print(f"SCHEMA_VERSION actual: {current_version}")

        # Ejecutar SQL de creación de tablas
        print("\nCreando tablas de cache...")
        conn.executescript(CACHE_TABLES_SQL)
        conn.commit()

        # Actualizar schema version
        cursor.execute("PRAGMA user_version = 29")
        conn.commit()

        # Verificar
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%cache%'"
        )
        tables = cursor.fetchall()

        print(f"\nTablas de cache encontradas: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")

        cursor.execute("PRAGMA user_version")
        new_version = cursor.fetchone()[0]
        print(f"\nSCHEMA_VERSION actualizado: {new_version}")

        print("\nOK: Migración a v29 completada")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
