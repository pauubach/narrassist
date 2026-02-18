#!/usr/bin/env python3
"""
Build thesaurus database from WordNet OMW 1.4 (Spanish).

Generates a SQLite database of Spanish synonyms using the Open Multilingual
Wordnet data accessed via NLTK. The database is stored in the user's
~/.narrative_assistant/dictionaries/ directory.

Usage:
    python scripts/build_thesaurus_db.py          # Build if not exists
    python scripts/build_thesaurus_db.py --force   # Rebuild from scratch
    python scripts/build_thesaurus_db.py --status   # Check current state

NLTK data is downloaded once to ~/.narrative_assistant/nltk_data/
and reused on subsequent runs.
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Directories
NA_DATA_DIR = Path(os.environ.get("NA_DATA_DIR", Path.home() / ".narrative_assistant"))
NLTK_DATA_DIR = NA_DATA_DIR / "nltk_data"
DICTIONARIES_DIR = NA_DATA_DIR / "dictionaries"
SYNONYMS_DB_PATH = DICTIONARIES_DIR / "synonyms.db"

MIN_ENTRIES_THRESHOLD = 100  # DB with fewer entries is considered empty


def _ensure_nltk():
    """Ensure NLTK and WordNet data are available. Downloads if needed."""
    try:
        import nltk
    except ImportError:
        raise RuntimeError(
            "NLTK no está instalado. Instala con: pip install nltk\n"
            "O: pip install -e '.[thesaurus]'"
        )

    # Set NLTK data path to our own directory (don't pollute ~/nltk_data)
    nltk_data_str = str(NLTK_DATA_DIR)
    if nltk_data_str not in nltk.data.path:
        nltk.data.path.insert(0, nltk_data_str)

    NLTK_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Download WordNet + OMW (idempotent: skips if already present)
    for package in ("wordnet", "omw-1.4"):
        try:
            nltk.data.find(f"corpora/{package.replace('-', '_').replace('.', '_')}")
            logger.info(f"NLTK '{package}' ya disponible")
        except LookupError:
            logger.info(f"Descargando NLTK '{package}'...")
            nltk.download(package, download_dir=nltk_data_str, quiet=True)

    return nltk


def _get_entry_count() -> int:
    """Get number of entries in existing synonyms.db."""
    if not SYNONYMS_DB_PATH.exists():
        return 0
    try:
        conn = sqlite3.connect(str(SYNONYMS_DB_PATH))
        count = conn.execute("SELECT COUNT(*) FROM synonyms").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def build(force: bool = False) -> Path:
    """
    Build the synonyms database from WordNet OMW 1.4.

    Args:
        force: If True, rebuild even if database already exists.

    Returns:
        Path to the generated database file.
    """
    # Check if already built
    if not force:
        count = _get_entry_count()
        if count >= MIN_ENTRIES_THRESHOLD:
            logger.info(f"synonyms.db ya tiene {count} entradas. Usa --force para reconstruir.")
            return SYNONYMS_DB_PATH

    nltk = _ensure_nltk()
    from nltk.corpus import wordnet as wn

    logger.info("Extrayendo sinónimos del WordNet español (OMW 1.4)...")

    # Collect all Spanish lemmas and their synsets
    synonyms_map: dict[str, set[str]] = {}
    antonyms_map: dict[str, set[str]] = {}

    # Get all synsets that have Spanish lemmas
    processed = 0
    for synset in wn.all_synsets():
        spa_lemmas = synset.lemma_names("spa")
        if not spa_lemmas:
            continue

        # Each pair of lemmas in the same synset are synonyms
        spa_lemmas_clean = [
            lemma.replace("_", " ").lower() for lemma in spa_lemmas
        ]

        for lemma in spa_lemmas_clean:
            if lemma not in synonyms_map:
                synonyms_map[lemma] = set()
            # Add all other lemmas as synonyms
            for other in spa_lemmas_clean:
                if other != lemma:
                    synonyms_map[lemma].add(other)

        # Also collect synonyms from hypernyms (broader terms have related words)
        for hypernym in synset.hypernyms():
            hyper_spa = [
                l.replace("_", " ").lower() for l in hypernym.lemma_names("spa")
            ]
            for lemma in spa_lemmas_clean:
                for hyper in hyper_spa:
                    if hyper != lemma:
                        synonyms_map[lemma].add(hyper)

        # Collect antonyms
        for lemma_obj in synset.lemmas("spa"):
            lemma_name = lemma_obj.name().replace("_", " ").lower()
            for antonym in lemma_obj.antonyms():
                ant_name = antonym.name().replace("_", " ").lower()
                if lemma_name not in antonyms_map:
                    antonyms_map[lemma_name] = set()
                antonyms_map[lemma_name].add(ant_name)

        processed += 1

    logger.info(
        f"Procesados {processed} synsets → {len(synonyms_map)} palabras con sinónimos"
    )

    # Write to SQLite
    DICTIONARIES_DIR.mkdir(parents=True, exist_ok=True)

    if SYNONYMS_DB_PATH.exists():
        SYNONYMS_DB_PATH.unlink()

    conn = sqlite3.connect(str(SYNONYMS_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS synonyms (
            word TEXT PRIMARY KEY,
            synonyms TEXT NOT NULL,
            antonyms TEXT NOT NULL DEFAULT '[]'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_synonyms_word ON synonyms(word)")

    # Batch insert
    batch = []
    for word, syns in synonyms_map.items():
        ants = sorted(antonyms_map.get(word, set()))
        batch.append((word, json.dumps(sorted(syns), ensure_ascii=False), json.dumps(ants, ensure_ascii=False)))

    conn.executemany(
        "INSERT OR REPLACE INTO synonyms (word, synonyms, antonyms) VALUES (?, ?, ?)",
        batch,
    )
    conn.commit()

    final_count = conn.execute("SELECT COUNT(*) FROM synonyms").fetchone()[0]
    conn.close()

    db_size_mb = SYNONYMS_DB_PATH.stat().st_size / (1024 * 1024)
    logger.info(
        f"synonyms.db generado: {final_count} entradas, {db_size_mb:.1f} MB"
    )

    return SYNONYMS_DB_PATH


def status():
    """Show current thesaurus database status."""
    count = _get_entry_count()
    if count == 0:
        print("Estado: No hay base de datos de sinónimos")
        print(f"  Ruta esperada: {SYNONYMS_DB_PATH}")
        print("  Ejecuta: python scripts/build_thesaurus_db.py")
    else:
        size_mb = SYNONYMS_DB_PATH.stat().st_size / (1024 * 1024)
        print(f"Estado: synonyms.db disponible")
        print(f"  Ruta: {SYNONYMS_DB_PATH}")
        print(f"  Entradas: {count:,}")
        print(f"  Tamaño: {size_mb:.1f} MB")

    # Check NLTK data
    nltk_exists = NLTK_DATA_DIR.exists() and any(NLTK_DATA_DIR.iterdir()) if NLTK_DATA_DIR.exists() else False
    print(f"  NLTK data: {'disponible' if nltk_exists else 'no descargado'} ({NLTK_DATA_DIR})")


def main():
    parser = argparse.ArgumentParser(description="Build thesaurus database from WordNet OMW 1.4")
    parser.add_argument("--force", action="store_true", help="Rebuild even if database exists")
    parser.add_argument("--status", action="store_true", help="Show current database status")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.status:
        status()
        return

    try:
        path = build(force=args.force)
        print(f"\nBase de datos de sinónimos lista: {path}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
