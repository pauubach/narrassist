#!/usr/bin/env python3
"""
Script para limpiar análisis colgados.

Uso:
    python scripts/clear_stuck_analysis.py <project_id>
    python scripts/clear_stuck_analysis.py --all
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".narrative_assistant" / "narrative_assistant.db"


def clear_stuck_analysis(project_id: int | None = None, all_projects: bool = False):
    """Limpia estado de análisis bloqueado."""

    if not DB_PATH.exists():
        print(f"❌ Base de datos no encontrada: {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        if all_projects:
            # Limpiar todos los proyectos con status 'analyzing'
            cursor.execute(
                "UPDATE projects SET analysis_status = 'completed' WHERE analysis_status = 'analyzing'"
            )
            affected = cursor.rowcount
            conn.commit()
            print(f"✅ Limpiados {affected} proyectos bloqueados")

        elif project_id is not None:
            # Verificar estado actual
            cursor.execute(
                "SELECT id, name, analysis_status FROM projects WHERE id = ?",
                (project_id,)
            )
            row = cursor.fetchone()

            if not row:
                print(f"❌ Proyecto {project_id} no encontrado")
                return 1

            old_status = row[2]
            print(f"📊 Proyecto: {row[1]} (ID: {row[0]})")
            print(f"   Estado actual: {old_status}")

            if old_status != 'analyzing':
                print(f"ℹ️  No está bloqueado (status: {old_status})")
                return 0

            # Limpiar
            cursor.execute(
                "UPDATE projects SET analysis_status = 'completed' WHERE id = ?",
                (project_id,)
            )
            conn.commit()
            print(f"✅ Estado actualizado: analyzing → completed")

        else:
            print("❌ Debes especificar --all o un <project_id>")
            return 1

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Limpiar análisis colgados")
    parser.add_argument("project_id", nargs="?", type=int, help="ID del proyecto a limpiar")
    parser.add_argument("--all", action="store_true", help="Limpiar todos los proyectos bloqueados")

    args = parser.parse_args()

    sys.exit(clear_stuck_analysis(args.project_id, args.all))


if __name__ == "__main__":
    main()
