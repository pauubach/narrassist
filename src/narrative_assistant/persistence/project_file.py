"""
Exportación e importación de archivos de proyecto (.nra).

Un archivo .nra es una base de datos SQLite que contiene todos los datos
de un proyecto de análisis narrativo. Permite portabilidad completa
entre máquinas y backup offline.

Formato:
    - Schema idéntico al de la DB principal (SCHEMA_SQL)
    - Tabla extra `nra_metadata` con metadatos del archivo
    - Contiene solo datos de UN proyecto (project_id normalizado a 1)
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ..core.result import Result
from .database import SCHEMA_SQL, SCHEMA_VERSION, Database

logger = logging.getLogger(__name__)

# Versión del formato .nra (incrementar si cambia la estructura del archivo)
NRA_FORMAT_VERSION = 1

# Tamaño máximo aceptable para importar (500 MB)
MAX_NRA_FILE_SIZE = 500 * 1024 * 1024

# Schema version mínimo compatible para importar
MIN_COMPATIBLE_SCHEMA_VERSION = 28


# ─────────────────────────────────────────────────────────────────────
# Metadatos
# ─────────────────────────────────────────────────────────────────────

@dataclass
class NraMetadata:
    """Metadatos almacenados dentro del archivo .nra."""
    nra_format_version: int
    app_version: str
    schema_version: int
    export_date: str
    original_project_name: str


# ─────────────────────────────────────────────────────────────────────
# Mapas de IDs para remapeo de FK en importación
# ─────────────────────────────────────────────────────────────────────

@dataclass
class IdMap:
    """Mapa de traducción old_id → new_id para cada tabla con PK."""
    projects: dict[int, int] = field(default_factory=dict)
    chapters: dict[int, int] = field(default_factory=dict)
    entities: dict[int, int] = field(default_factory=dict)
    sessions: dict[int, int] = field(default_factory=dict)
    runs: dict[int, int] = field(default_factory=dict)
    scenes: dict[int, int] = field(default_factory=dict)
    snapshots: dict[int, int] = field(default_factory=dict)
    attributes: dict[int, int] = field(default_factory=dict)
    mentions: dict[int, int] = field(default_factory=dict)
    sections: dict[int, int] = field(default_factory=dict)
    dialogues: dict[int, int] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# Tablas project-scoped y su configuración de exportación/importación
# ─────────────────────────────────────────────────────────────────────

# Cada entrada: (tabla, columna_project_id, fk_columns)
# fk_columns: dict de columna → nombre del mapa en IdMap
# Si project_id_col es None, la tabla se filtra por FK chain (ver INDIRECT_TABLES)

_DIRECT_TABLES: list[tuple[str, str, dict[str, str]]] = [
    # ── Core ──
    ("chapters", "project_id", {}),
    ("sections", "project_id", {"chapter_id": "chapters", "parent_section_id": "sections"}),
    ("dialogues", "project_id", {"chapter_id": "chapters", "speaker_entity_id": "entities"}),
    ("speaker_corrections", "project_id", {"original_speaker_id": "entities", "corrected_speaker_id": "entities"}),
    # ── Entities ──
    ("entities", "project_id", {}),
    # ── Alerts ──
    ("alerts", "project_id", {}),
    ("alert_dismissals", "project_id", {}),
    # ── Sessions & runs ──
    ("sessions", "project_id", {"last_chapter_id": "chapters"}),
    ("analysis_runs", "project_id", {"session_id": "sessions"}),
    ("review_history", "project_id", {}),
    # ── Relationships ──
    ("relationships", "project_id", {"entity1_id": "entities", "entity2_id": "entities", "chapter_id": "chapters"}),
    ("interactions", "project_id", {"entity1_id": "entities", "entity2_id": "entities", "chapter_id": "chapters"}),
    # ── Timeline ──
    ("timeline_events", "project_id", {}),
    ("temporal_markers", "project_id", {"entity_id": "entities"}),
    # ── Style & voice ──
    ("voice_profiles", "project_id", {"entity_id": "entities"}),
    ("emotional_arcs", "project_id", {"chapter_id": "chapters"}),
    ("pacing_metrics", "project_id", {"chapter_id": "chapters"}),
    ("register_changes", "project_id", {"chapter_id": "chapters"}),
    # ── Scenes ──
    ("scenes", "project_id", {"chapter_id": "chapters"}),
    ("project_custom_tag_catalog", "project_id", {}),
    # ── Events ──
    ("narrative_events", "project_id", {}),
    ("vital_status_events", "project_id", {"entity_id": "entities"}),
    ("character_location_events", "project_id", {"entity_id": "entities"}),
    ("ooc_events", "project_id", {"entity_id": "entities"}),
    # ── Focalization & editorial ──
    ("focalization_declarations", "project_id", {}),
    ("editorial_rules", "project_id", {}),
    # ── Entity management ──
    ("rejected_entities", "project_id", {}),
    ("project_entity_overrides", "project_id", {}),
    ("coreference_corrections", "project_id", {"original_entity_id": "entities", "corrected_entity_id": "entities"}),
    # ── Calibration ──
    ("detector_calibration", "project_id", {}),
    ("project_detector_weights", "project_id", {}),
    # ── Enrichment ──
    ("enrichment_cache", "project_id", {}),
    ("invalidation_events", "project_id", {}),
    ("user_glossary", "project_id", {}),
    # ── Snapshots & versions ──
    ("analysis_snapshots", "project_id", {}),
    ("snapshot_chapters", "project_id", {"snapshot_id": "snapshots"}),
    ("snapshot_alerts", "project_id", {"snapshot_id": "snapshots"}),
    ("snapshot_entities", "project_id", {"snapshot_id": "snapshots", "original_entity_id": "entities"}),
    ("version_metrics", "project_id", {"snapshot_id": "snapshots"}),
    ("version_diffs", "project_id", {"snapshot_id": "snapshots"}),
    ("entity_version_links", "project_id", {"snapshot_id": "snapshots", "old_entity_id": "entities", "new_entity_id": "entities"}),
    # ── Caches ──
    ("ner_cache", "project_id", {}),
    ("coreference_cache", "project_id", {}),
    ("attribute_cache", "project_id", {}),
    ("coref_checkpoint", "project_id", {}),
    ("ner_chapter_cache", "project_id", {}),
    # ── Identity ──
    ("manuscript_identity_checks", "project_id", {}),
]

# Tablas con FK indirecta (sin project_id propio)
_INDIRECT_TABLES: list[tuple[str, str, str, dict[str, str]]] = [
    # (tabla, fk_col, tabla_padre, fk_columns_adicionales)
    ("entity_mentions", "entity_id", "entities", {"chapter_id": "chapters"}),
    ("entity_attributes", "entity_id", "entities", {"source_mention_id": "mentions", "chapter_id": "chapters"}),
    ("attribute_evidences", "attribute_id", "entity_attributes", {}),
    ("analysis_phases", "run_id", "analysis_runs", {}),
    ("scene_tags", "scene_id", "scenes", {"location_entity_id": "entities"}),
    ("scene_custom_tags", "scene_id", "scenes", {}),
    ("character_speech_snapshots", "character_id", "entities", {}),
]

# Columnas JSON que contienen entity_ids que necesitan remapeo
_JSON_ENTITY_COLUMNS: dict[str, list[str]] = {
    "alerts": ["entity_ids"],
    "focalization_declarations": ["focalizer_ids"],
    "entities": ["merged_from_ids"],
    "narrative_events": ["entity_ids"],
    "invalidation_events": ["entity_ids"],
    "snapshot_alerts": ["entity_ids"],
    "scene_tags": ["participant_ids"],
}

# Tablas que NO se exportan (globales / cross-project)
_EXCLUDED_TABLES = {
    "schema_info",
    "system_entity_patterns",
    "user_rejected_entities",
    "collections",
    "collection_entity_links",
    "llm_config",
    "model_benchmarks",
    "manuscript_identity_risk_state",
    "manuscript_identity_risk_events",
    "suppression_rules",
    "correction_config_overrides",
    "nra_metadata",
}


def _get_app_version() -> str:
    """Obtiene la versión de la aplicación."""
    try:
        from .. import __version__
        return __version__
    except Exception:
        return "unknown"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Comprueba si una tabla existe en la DB."""
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row[0] > 0) if row else False


def _get_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """Obtiene los nombres de columnas de una tabla."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [r[1] for r in rows]


def _get_indirect_parent_fk(table: str) -> tuple[str, str] | None:
    """Obtiene (fk_col, parent_table) para una tabla indirecta."""
    for t, fk_col, parent_table, _ in _INDIRECT_TABLES:
        if t == table:
            return (fk_col, parent_table)
    return None


def _remap_json_ids(json_str: str | None, id_map: dict[int, int]) -> str | None:
    """Remapea IDs dentro de un JSON array string como '[1, 5, 12]'."""
    if not json_str or json_str in ("[]", "null", ""):
        return json_str
    try:
        ids = json.loads(json_str)
        if isinstance(ids, list):
            remapped = [id_map.get(int(i), int(i)) for i in ids if i is not None]
            return json.dumps(remapped)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return json_str


# ─────────────────────────────────────────────────────────────────────
# Exportador
# ─────────────────────────────────────────────────────────────────────

class NraExporter:
    """Exporta un proyecto a un archivo .nra."""

    def __init__(self, db: Database):
        self.db = db

    def export_project(self, project_id: int, output_path: Path) -> Result[Path]:
        """
        Exporta un proyecto completo a un archivo .nra.

        Args:
            project_id: ID del proyecto a exportar.
            output_path: Ruta destino del archivo .nra.

        Returns:
            Result con la ruta del archivo creado.
        """
        # Validar proyecto existe
        row = self.db.fetchone("SELECT id, name FROM projects WHERE id = ?", (project_id,))
        if not row:
            return Result.failure(
                NarrativeError(f"Proyecto {project_id} no encontrado", severity=ErrorSeverity.FATAL)
            )

        project_name = row["name"]
        logger.info(f"Exportando proyecto '{project_name}' (ID {project_id}) a {output_path}")

        # Asegurar extensión .nra
        if output_path.suffix.lower() != ".nra":
            output_path = output_path.with_suffix(".nra")

        tmp_path = output_path.with_suffix(".nra.tmp")
        nra_conn: sqlite3.Connection | None = None

        try:
            # Crear DB destino
            if tmp_path.exists():
                tmp_path.unlink()

            nra_conn = sqlite3.connect(str(tmp_path))
            nra_conn.execute("PRAGMA journal_mode=WAL")
            nra_conn.execute("PRAGMA foreign_keys=OFF")  # Desactivar FK para inserción masiva

            # Crear schema
            nra_conn.executescript(SCHEMA_SQL)

            # Crear tabla de metadatos
            nra_conn.execute("""
                CREATE TABLE IF NOT EXISTS nra_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            metadata = {
                "nra_format_version": str(NRA_FORMAT_VERSION),
                "app_version": _get_app_version(),
                "schema_version": str(SCHEMA_VERSION),
                "export_date": dt.datetime.now(dt.UTC).isoformat(),
                "original_project_name": project_name,
            }
            nra_conn.executemany(
                "INSERT INTO nra_metadata (key, value) VALUES (?, ?)",
                list(metadata.items()),
            )

            # Copiar datos tabla por tabla
            with self.db.connection() as src_conn:
                # Proyecto
                self._copy_project(src_conn, nra_conn, project_id)

                # Tablas directas (con project_id)
                for table, pid_col, _ in _DIRECT_TABLES:
                    self._copy_direct_table(src_conn, nra_conn, table, pid_col, project_id)

                # Tablas indirectas (sin project_id propio)
                for table, fk_col, parent_table, _ in _INDIRECT_TABLES:
                    self._copy_indirect_table(
                        src_conn, nra_conn, table, fk_col, parent_table, project_id
                    )

            nra_conn.commit()
            nra_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            nra_conn.close()
            nra_conn = None

            # Renombrar tmp → final
            if output_path.exists():
                output_path.unlink()
            tmp_path.rename(output_path)

            size = output_path.stat().st_size
            logger.info(f"Proyecto exportado: {output_path} ({size // 1024} KB)")
            return Result.success(output_path)

        except Exception as e:
            logger.error(f"Error exportando proyecto: {e}", exc_info=True)
            # Cerrar conexión antes de intentar borrar el tmp (Windows lock)
            try:
                if nra_conn is not None:
                    nra_conn.close()
            except Exception:
                pass
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            return Result.failure(
                NarrativeError(
                    f"Error al exportar proyecto: {e}",
                    severity=ErrorSeverity.FATAL,
                    user_message=f"No se pudo guardar el archivo: {e}",
                )
            )
        finally:
            if nra_conn is not None:
                try:
                    nra_conn.close()
                except Exception:
                    pass

    def _copy_project(
        self, src: sqlite3.Connection, dst: sqlite3.Connection, project_id: int
    ) -> None:
        """Copia la fila del proyecto."""
        cols = _get_columns(src, "projects")
        row = src.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            return

        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        values = list(row)
        dst.execute(f"INSERT INTO projects ({col_names}) VALUES ({placeholders})", values)

    def _copy_direct_table(
        self,
        src: sqlite3.Connection,
        dst: sqlite3.Connection,
        table: str,
        pid_col: str,
        project_id: int,
    ) -> None:
        """Copia filas de una tabla que tiene project_id directo."""
        if not _table_exists(src, table):
            return

        cols = _get_columns(src, table)
        if not cols:
            return

        # Verificar que la columna project_id existe en la tabla fuente
        if pid_col not in cols:
            logger.debug(f"  Skipping {table}: no column '{pid_col}'")
            return

        # Verificar que la tabla destino existe y tiene las mismas columnas
        if not _table_exists(dst, table):
            return
        dst_cols = set(_get_columns(dst, table))

        rows = src.execute(
            f"SELECT * FROM {table} WHERE {pid_col} = ?", (project_id,)
        ).fetchall()

        if not rows:
            return

        # Solo insertar columnas que existen en ambas DBs
        common_cols = [c for c in cols if c in dst_cols]
        col_indices = [cols.index(c) for c in common_cols]
        placeholders = ", ".join(["?"] * len(common_cols))
        col_names = ", ".join(common_cols)

        for row in rows:
            values = [row[i] for i in col_indices]
            try:
                dst.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values)
            except sqlite3.IntegrityError:
                pass  # Duplicado, skip

        logger.debug(f"  Exportado {table}: {len(rows)} filas")

    def _copy_indirect_table(
        self,
        src: sqlite3.Connection,
        dst: sqlite3.Connection,
        table: str,
        fk_col: str,
        parent_table: str,
        project_id: int,
    ) -> None:
        """Copia filas de una tabla sin project_id, filtrando por la tabla padre."""
        if not _table_exists(src, table) or not _table_exists(dst, table):
            return

        # Determinar la columna del parent para filtrar
        if parent_table == "entities":
            parent_query = "SELECT id FROM entities WHERE project_id = ?"
        elif parent_table == "entity_attributes":
            parent_query = (
                "SELECT ea.id FROM entity_attributes ea "
                "JOIN entities e ON ea.entity_id = e.id "
                "WHERE e.project_id = ?"
            )
        elif parent_table == "analysis_runs":
            parent_query = "SELECT id FROM analysis_runs WHERE project_id = ?"
        elif parent_table == "scenes":
            parent_query = "SELECT id FROM scenes WHERE project_id = ?"
        else:
            return

        parent_ids = [r[0] for r in src.execute(parent_query, (project_id,)).fetchall()]
        if not parent_ids:
            return

        cols = _get_columns(src, table)
        dst_cols = set(_get_columns(dst, table))
        common_cols = [c for c in cols if c in dst_cols]
        col_indices = [cols.index(c) for c in common_cols]
        placeholders = ", ".join(["?"] * len(common_cols))
        col_names = ", ".join(common_cols)

        # Batch por chunks de 500 IDs
        total = 0
        for i in range(0, len(parent_ids), 500):
            chunk = parent_ids[i : i + 500]
            in_clause = ", ".join(["?"] * len(chunk))
            rows = src.execute(
                f"SELECT * FROM {table} WHERE {fk_col} IN ({in_clause})", chunk
            ).fetchall()

            for row in rows:
                values = [row[idx] for idx in col_indices]
                try:
                    dst.execute(
                        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values
                    )
                except sqlite3.IntegrityError:
                    pass
            total += len(rows)

        if total:
            logger.debug(f"  Exportado {table}: {total} filas (indirecto via {parent_table})")


# ─────────────────────────────────────────────────────────────────────
# Importador
# ─────────────────────────────────────────────────────────────────────

class NraImporter:
    """Importa un proyecto desde un archivo .nra."""

    def __init__(self, db: Database):
        self.db = db

    def import_project(self, nra_path: Path) -> Result[int]:
        """
        Importa un proyecto desde un archivo .nra.

        Args:
            nra_path: Ruta al archivo .nra.

        Returns:
            Result con el ID del nuevo proyecto creado.
        """
        # Validar archivo
        validation = self._validate_file(nra_path)
        if validation.is_failure:
            assert validation.error is not None  # guaranteed by is_failure
            return Result.failure(validation.error)

        assert validation.value is not None  # guaranteed by is_success
        metadata: NraMetadata = validation.value
        warnings: list[str] = []

        nra_schema = metadata.schema_version
        if nra_schema > SCHEMA_VERSION:
            return Result.failure(NarrativeError(
                f"Archivo creado con versión más nueva (schema {nra_schema} > {SCHEMA_VERSION})",
                severity=ErrorSeverity.FATAL,
                user_message="Este archivo fue creado con una versión más nueva de la aplicación. Actualiza la app.",
            ))
        if nra_schema < MIN_COMPATIBLE_SCHEMA_VERSION:
            return Result.failure(NarrativeError(
                f"Archivo demasiado antiguo (schema {nra_schema})",
                severity=ErrorSeverity.FATAL,
                user_message="Este archivo fue creado con una versión muy antigua y no es compatible.",
            ))
        if nra_schema < SCHEMA_VERSION:
            warnings.append(
                f"Archivo exportado con versión anterior (schema {nra_schema}). "
                f"Algunos datos podrían no importarse completamente."
            )

        logger.info(
            f"Importando proyecto desde {nra_path} "
            f"(format_v{metadata.nra_format_version}, schema_v{nra_schema})"
        )

        # Abrir .nra como read-only
        nra_conn = sqlite3.connect(f"file:{nra_path}?mode=ro", uri=True)
        nra_conn.row_factory = sqlite3.Row

        id_map = IdMap()

        try:
            with self.db.transaction() as dest_conn:
                # 1. Importar proyecto
                old_project_id = self._import_project_row(nra_conn, dest_conn, id_map)
                if old_project_id is None:
                    return Result.failure(NarrativeError(
                        "No se encontró proyecto en el archivo .nra",
                        severity=ErrorSeverity.FATAL,
                    ))

                new_project_id = id_map.projects[old_project_id]

                # 2. Importar tablas directas en orden de dependencia
                for table, pid_col, fk_map in _DIRECT_TABLES:
                    self._import_direct_table(
                        nra_conn, dest_conn, table, pid_col, old_project_id, fk_map, id_map
                    )

                # 3. Importar tablas indirectas
                for table, fk_col, parent_table, fk_map in _INDIRECT_TABLES:
                    self._import_indirect_table(
                        nra_conn, dest_conn, table, fk_col, parent_table, fk_map, id_map
                    )

                # 4. Remapear columnas JSON con entity_ids
                self._remap_json_columns(dest_conn, new_project_id, id_map)

            logger.info(f"Proyecto importado con ID {new_project_id}")
            result = Result.success(new_project_id)
            for w in warnings:
                result.add_warning(w)
            return result

        except Exception as e:
            logger.error(f"Error importando proyecto: {e}", exc_info=True)
            return Result.failure(NarrativeError(
                f"Error al importar: {e}",
                severity=ErrorSeverity.FATAL,
                user_message=f"No se pudo abrir el archivo: {e}",
            ))
        finally:
            nra_conn.close()

    def _validate_file(self, nra_path: Path) -> Result[NraMetadata]:
        """Valida que el archivo es un .nra válido."""
        if not nra_path.exists():
            return Result.failure(NarrativeError(
                f"Archivo no encontrado: {nra_path}",
                severity=ErrorSeverity.FATAL,
                user_message="El archivo no existe.",
            ))

        if nra_path.stat().st_size > MAX_NRA_FILE_SIZE:
            return Result.failure(NarrativeError(
                f"Archivo demasiado grande: {nra_path.stat().st_size} bytes",
                severity=ErrorSeverity.FATAL,
                user_message="El archivo es demasiado grande (máximo 500 MB).",
            ))

        # Verificar que es SQLite válido
        try:
            conn = sqlite3.connect(f"file:{nra_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except Exception as e:
            return Result.failure(NarrativeError(
                f"No es un archivo SQLite válido: {e}",
                severity=ErrorSeverity.FATAL,
                user_message="El archivo no es un proyecto válido.",
            ))

        try:
            # Integrity check
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return Result.failure(NarrativeError(
                    "Archivo corrupto (integrity check falló)",
                    severity=ErrorSeverity.FATAL,
                    user_message="El archivo de proyecto está corrupto.",
                ))

            # Verificar nra_metadata
            if not _table_exists(conn, "nra_metadata"):
                return Result.failure(NarrativeError(
                    "No es un archivo .nra (falta tabla nra_metadata)",
                    severity=ErrorSeverity.FATAL,
                    user_message="Este archivo no es un proyecto de Narrative Assistant.",
                ))

            meta_rows = conn.execute("SELECT key, value FROM nra_metadata").fetchall()
            meta = {r["key"]: r["value"] for r in meta_rows}

            metadata = NraMetadata(
                nra_format_version=int(meta.get("nra_format_version", "0")),
                app_version=meta.get("app_version", "unknown"),
                schema_version=int(meta.get("schema_version", "0")),
                export_date=meta.get("export_date", ""),
                original_project_name=meta.get("original_project_name", ""),
            )

            # Verificar que tiene tabla projects con al menos 1 fila
            if not _table_exists(conn, "projects"):
                return Result.failure(NarrativeError(
                    "Archivo .nra sin tabla projects",
                    severity=ErrorSeverity.FATAL,
                    user_message="El archivo de proyecto está incompleto.",
                ))

            project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            if project_count == 0:
                return Result.failure(NarrativeError(
                    "Archivo .nra sin proyectos",
                    severity=ErrorSeverity.FATAL,
                    user_message="El archivo de proyecto está vacío.",
                ))

            return Result.success(metadata)

        except sqlite3.DatabaseError as e:
            return Result.failure(NarrativeError(
                f"Error leyendo archivo: {e}",
                severity=ErrorSeverity.FATAL,
                user_message="No se pudo leer el archivo de proyecto.",
            ))
        finally:
            conn.close()

    def _import_project_row(
        self,
        nra_conn: sqlite3.Connection,
        dest_conn: sqlite3.Connection,
        id_map: IdMap,
    ) -> int | None:
        """Importa la fila del proyecto. Retorna el old_project_id."""
        row = nra_conn.execute("SELECT * FROM projects LIMIT 1").fetchone()
        if not row:
            return None

        cols = _get_columns(nra_conn, "projects")
        values = dict(zip(cols, row, strict=False))
        old_id: int = values["id"]

        # Limpiar campos que no aplican en la nueva máquina
        values.pop("id")
        values["document_path"] = None
        values["last_opened_at"] = dt.datetime.now(dt.UTC).isoformat()

        # Renombrar si ya existe uno con el mismo nombre
        existing = dest_conn.execute(
            "SELECT COUNT(*) FROM projects WHERE name = ?", (values["name"],)
        ).fetchone()[0]
        if existing > 0:
            values["name"] = f"{values['name']} (importado)"

        # Solo insertar columnas que existen en el destino
        dest_cols = set(_get_columns(dest_conn, "projects"))
        insert_cols = [c for c in values if c in dest_cols]
        placeholders = ", ".join(["?"] * len(insert_cols))
        col_names = ", ".join(insert_cols)
        insert_values = [values[c] for c in insert_cols]

        cursor = dest_conn.execute(
            f"INSERT INTO projects ({col_names}) VALUES ({placeholders})", insert_values
        )
        new_id: int = cursor.lastrowid  # type: ignore[assignment]  # lastrowid always set after INSERT
        id_map.projects[old_id] = new_id

        logger.debug(f"  Proyecto: old_id={old_id} → new_id={new_id}")
        return old_id

    def _import_direct_table(
        self,
        nra_conn: sqlite3.Connection,
        dest_conn: sqlite3.Connection,
        table: str,
        pid_col: str,
        old_project_id: int,
        fk_map: dict[str, str],
        id_map: IdMap,
    ) -> None:
        """Importa filas de una tabla con project_id directo, remapeando FKs."""
        if not _table_exists(nra_conn, table) or not _table_exists(dest_conn, table):
            return

        nra_cols = _get_columns(nra_conn, table)
        dest_cols_set = set(_get_columns(dest_conn, table))
        common_cols = [c for c in nra_cols if c in dest_cols_set]

        rows = nra_conn.execute(
            f"SELECT * FROM {table} WHERE {pid_col} = ?", (old_project_id,)
        ).fetchall()

        if not rows:
            return

        # Determinar qué mapa de IDs usar para esta tabla (para su PK)
        table_id_map = self._get_id_map_for_table(table, id_map)

        insert_cols = [c for c in common_cols if c != "id"]
        placeholders = ", ".join(["?"] * len(insert_cols))
        col_names = ", ".join(insert_cols)

        imported = 0
        for row in rows:
            row_dict = dict(zip(nra_cols, row, strict=False))
            old_id = row_dict.get("id")

            # Remapear project_id
            row_dict[pid_col] = id_map.projects.get(row_dict[pid_col], row_dict[pid_col])

            # Remapear FKs
            for fk_col, map_name in fk_map.items():
                if fk_col in row_dict and row_dict[fk_col] is not None:
                    fk_id_map = getattr(id_map, map_name, {})
                    old_fk = row_dict[fk_col]
                    row_dict[fk_col] = fk_id_map.get(old_fk)
                    # Si no está en el mapa, poner NULL (referencia perdida)
                    if row_dict[fk_col] is None and old_fk is not None:
                        row_dict[fk_col] = None

            values = [row_dict.get(c) for c in insert_cols]

            try:
                cursor = dest_conn.execute(
                    f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values
                )
                new_row_id = cursor.lastrowid
                if old_id is not None and table_id_map is not None and new_row_id is not None:
                    table_id_map[old_id] = new_row_id
                imported += 1
            except sqlite3.IntegrityError as e:
                logger.debug(f"  Skip duplicate in {table}: {e}")

        if imported:
            logger.debug(f"  Importado {table}: {imported}/{len(rows)} filas")

    def _import_indirect_table(
        self,
        nra_conn: sqlite3.Connection,
        dest_conn: sqlite3.Connection,
        table: str,
        fk_col: str,
        parent_table: str,
        fk_map: dict[str, str],
        id_map: IdMap,
    ) -> None:
        """Importa filas de tabla con FK indirecta."""
        if not _table_exists(nra_conn, table) or not _table_exists(dest_conn, table):
            return

        parent_id_map = self._get_id_map_for_table(parent_table, id_map)
        if parent_id_map is None:
            return

        old_parent_ids = list(parent_id_map.keys())
        if not old_parent_ids:
            return

        # Mapa de IDs para esta tabla (para que downstream indirectas puedan usarlo)
        table_id_map = self._get_id_map_for_table(table, id_map)

        nra_cols = _get_columns(nra_conn, table)
        dest_cols_set = set(_get_columns(dest_conn, table))
        common_cols = [c for c in nra_cols if c in dest_cols_set]
        insert_cols = [c for c in common_cols if c != "id"]
        placeholders = ", ".join(["?"] * len(insert_cols))
        col_names = ", ".join(insert_cols)

        imported = 0
        for i in range(0, len(old_parent_ids), 500):
            chunk = old_parent_ids[i : i + 500]
            in_clause = ", ".join(["?"] * len(chunk))
            rows = nra_conn.execute(
                f"SELECT * FROM {table} WHERE {fk_col} IN ({in_clause})", chunk
            ).fetchall()

            for row in rows:
                row_dict = dict(zip(nra_cols, row, strict=False))
                old_id = row_dict.get("id")

                # Remapear FK principal
                old_fk = row_dict.get(fk_col)
                if old_fk is not None:
                    row_dict[fk_col] = parent_id_map.get(old_fk)
                    if row_dict[fk_col] is None:
                        continue  # Padre no encontrado, skip

                # Remapear FKs adicionales
                for additional_fk, map_name in fk_map.items():
                    if additional_fk in row_dict and row_dict[additional_fk] is not None:
                        fk_id_map = getattr(id_map, map_name, {})
                        row_dict[additional_fk] = fk_id_map.get(
                            row_dict[additional_fk], row_dict[additional_fk]
                        )

                values = [row_dict.get(c) for c in insert_cols]
                try:
                    cursor = dest_conn.execute(
                        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values
                    )
                    new_row_id = cursor.lastrowid
                    if old_id is not None and table_id_map is not None and new_row_id is not None:
                        table_id_map[old_id] = new_row_id
                    imported += 1
                except sqlite3.IntegrityError:
                    pass

        if imported:
            logger.debug(f"  Importado {table}: {imported} filas (indirecto via {parent_table})")

    def _remap_json_columns(
        self, dest_conn: sqlite3.Connection, new_project_id: int, id_map: IdMap
    ) -> None:
        """Remapea entity_ids dentro de columnas JSON tras la importación."""
        entity_map = id_map.entities
        if not entity_map:
            return

        for table, json_cols in _JSON_ENTITY_COLUMNS.items():
            if not _table_exists(dest_conn, table):
                continue

            dest_table_cols = set(_get_columns(dest_conn, table))
            has_project_id = "project_id" in dest_table_cols

            for col in json_cols:
                if col not in dest_table_cols:
                    continue

                if has_project_id:
                    rows = dest_conn.execute(
                        f"SELECT id, {col} FROM {table} WHERE project_id = ? AND {col} IS NOT NULL AND {col} != '[]'",
                        (new_project_id,),
                    ).fetchall()
                else:
                    # Tabla indirecta: buscar por FK a tabla padre
                    parent_fk = _get_indirect_parent_fk(table)
                    if parent_fk:
                        fk_col, parent_table = parent_fk
                        parent_map = self._get_id_map_for_table(parent_table, id_map)
                        if parent_map:
                            new_parent_ids = list(parent_map.values())
                            if not new_parent_ids:
                                continue
                            in_clause = ", ".join(["?"] * len(new_parent_ids))
                            rows = dest_conn.execute(
                                f"SELECT id, {col} FROM {table} WHERE {fk_col} IN ({in_clause}) AND {col} IS NOT NULL AND {col} != '[]'",
                                new_parent_ids,
                            ).fetchall()
                        else:
                            continue
                    else:
                        continue

                for row in rows:
                    row_id, json_val = row
                    remapped = _remap_json_ids(json_val, entity_map)
                    if remapped != json_val:
                        dest_conn.execute(
                            f"UPDATE {table} SET {col} = ? WHERE id = ?",
                            (remapped, row_id),
                        )

    @staticmethod
    def _get_id_map_for_table(table: str, id_map: IdMap) -> dict[int, int] | None:
        """Obtiene el mapa de IDs correspondiente a una tabla."""
        mapping = {
            "projects": id_map.projects,
            "chapters": id_map.chapters,
            "entities": id_map.entities,
            "entity_mentions": id_map.mentions,
            "entity_attributes": id_map.attributes,
            "sessions": id_map.sessions,
            "analysis_runs": id_map.runs,
            "analysis_snapshots": id_map.snapshots,
            "scenes": id_map.scenes,
            "sections": id_map.sections,
            "dialogues": id_map.dialogues,
        }
        return mapping.get(table)


# Importar tipos de error aquí para evitar circular imports
from ..core.errors import ErrorSeverity, NarrativeError  # noqa: E402
