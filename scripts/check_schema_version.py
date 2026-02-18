#!/usr/bin/env python3
"""Script para verificar SCHEMA_VERSION de la DB."""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".narrative_assistant" / "narrative_assistant.db"

def main():
    if not DB_PATH.exists():
        print(f"ERROR: Base de datos no encontrada: {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA user_version")
        schema_version = cursor.fetchone()[0]

        print(f"SCHEMA_VERSION actual: {schema_version}")

        # Ver si existen las tablas de cache
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%cache%'"
        )
        tables = cursor.fetchall()

        print(f"\nTablas de cache encontradas: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    sys.exit(main())
