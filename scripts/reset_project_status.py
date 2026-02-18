#!/usr/bin/env python3
"""Script para resetear el estado de análisis de un proyecto."""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".narrative_assistant" / "narrative_assistant.db"

def main():
    if len(sys.argv) < 2:
        print("Uso: python reset_project_status.py <project_id>")
        return 1

    project_id = int(sys.argv[1])

    if not DB_PATH.exists():
        print(f"ERROR: Base de datos no encontrada: {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Ver estado actual
        cursor.execute(
            "SELECT id, name, analysis_status, analysis_progress FROM projects WHERE id = ?",
            (project_id,)
        )
        row = cursor.fetchone()

        if not row:
            print(f"ERROR: Proyecto {project_id} no encontrado")
            return 1

        print(f"Proyecto {row[0]}: {row[1]}")
        print(f"  Estado actual: {row[2]} ({row[3]*100:.0f}%)")

        # Resetear a pending
        cursor.execute(
            "UPDATE projects SET analysis_status = 'pending', analysis_progress = 0 WHERE id = ?",
            (project_id,)
        )
        conn.commit()

        print(f"  Nuevo estado: pending (0%)")
        print("OK: Proyecto reseteado correctamente")

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
