"""Script para borrar la caché de enriquecimientos y forzar regeneración de resúmenes."""

import sqlite3
from pathlib import Path


def clear_enrichment_cache():
    """Borra toda la caché de enriquecimientos."""
    # Ubicación de la DB
    home = Path.home()
    db_path = home / ".narrative_assistant" / "narrative_assistant.db"

    if not db_path.exists():
        print(f"[ERROR] No se encontro la base de datos en: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Contar registros antes de borrar
        cursor.execute("SELECT COUNT(*) FROM enrichment_cache")
        count_before = cursor.fetchone()[0]

        # Borrar toda la caché
        cursor.execute("DELETE FROM enrichment_cache")
        conn.commit()

        print(f"[OK] Cache de enriquecimientos borrada ({count_before} registros eliminados)")
        print("[INFO] Los resumenes se regeneraran la proxima vez que se analice el proyecto")

        conn.close()

    except Exception as e:
        print(f"[ERROR] Error al borrar cache: {e}")


if __name__ == "__main__":
    clear_enrichment_cache()
