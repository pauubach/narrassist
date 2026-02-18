#!/usr/bin/env python3
"""Script para verificar estado del proyecto en DB."""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".narrative_assistant" / "narrative_assistant.db"

def main():
    if not DB_PATH.exists():
        print(f"ERROR: Base de datos no encontrada: {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        project_id = int(sys.argv[1]) if len(sys.argv) > 1 else 7

        cursor.execute(
            "SELECT id, name, analysis_status, analysis_progress FROM projects WHERE id = ?",
            (project_id,)
        )
        row = cursor.fetchone()

        if not row:
            print(f"ERROR: Proyecto {project_id} no encontrado")
            return 1

        print(f"Proyecto {row[0]}: {row[1]}")
        print(f"  analysis_status: {row[2]}")
        print(f"  analysis_progress: {row[3]}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
