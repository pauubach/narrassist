"""
Repositorio de colecciones / sagas (BK-07).

Gestiona agrupaciones de proyectos y enlaces de entidades entre libros.
Sin límites artificiales - usa soft warnings para colecciones grandes.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Umbrales para warnings (NO hard limits)
WARN_PROJECTS_THRESHOLD = 10
WARN_ENTITY_LINKS_THRESHOLD = 100

# Tipos válidos de cache en workspace (previene path traversal)
VALID_CACHE_TYPES = frozenset({"cross_book_analysis", "entity_suggestions", "collection_summary"})


@dataclass
class Collection:
    """Una colección / saga de proyectos."""

    id: int | None = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    project_count: int = 0


@dataclass
class EntityLink:
    """Enlace entre dos entidades de distintos libros."""

    id: int | None = None
    collection_id: int = 0
    source_entity_id: int = 0
    target_entity_id: int = 0
    source_project_id: int = 0
    target_project_id: int = 0
    similarity: float = 1.0
    match_type: str = "manual"
    created_at: str = ""
    # Campos denormalizados para display
    source_entity_name: str = ""
    target_entity_name: str = ""
    source_project_name: str = ""
    target_project_name: str = ""


@dataclass
class LinkSuggestion:
    """Sugerencia de enlace entre entidades de distintos libros."""

    source_entity_id: int
    source_entity_name: str
    source_entity_type: str
    source_project_id: int
    source_project_name: str
    target_entity_id: int
    target_entity_name: str
    target_entity_type: str
    target_project_id: int
    target_project_name: str
    similarity: float
    match_type: str  # 'exact', 'fuzzy'


class CollectionRepository:
    """CRUD para colecciones y enlaces de entidades."""

    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is not None:
            return self._db
        from narrative_assistant.persistence.database import get_database
        return get_database()

    # ==================== Collection CRUD ====================

    def create(self, name: str, description: str = "") -> int:
        """Crea una colección. Retorna el ID."""
        db = self._get_db()
        with db.connection() as conn:
            cursor = conn.execute(
                """INSERT INTO collections (name, description)
                   VALUES (?, ?)""",
                (name, description),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get(self, collection_id: int) -> Collection | None:
        """Obtiene una colección por ID."""
        db = self._get_db()
        with db.connection() as conn:
            row = conn.execute(
                """SELECT id, name, description, created_at, updated_at
                   FROM collections WHERE id = ?""",
                (collection_id,),
            ).fetchone()
            if not row:
                return None

            project_count = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE collection_id = ?",
                (collection_id,),
            ).fetchone()[0]

            return Collection(
                id=row[0], name=row[1], description=row[2] or "",
                created_at=row[3], updated_at=row[4],
                project_count=project_count,
            )

    def list_all(self) -> list[Collection]:
        """Lista todas las colecciones."""
        db = self._get_db()
        with db.connection() as conn:
            rows = conn.execute(
                "SELECT id, name, description, created_at, updated_at FROM collections"
            ).fetchall()
            collections = []
            for row in rows:
                pc = conn.execute(
                    "SELECT COUNT(*) FROM projects WHERE collection_id = ?",
                    (row[0],),
                ).fetchone()[0]
                collections.append(Collection(
                    id=row[0], name=row[1], description=row[2] or "",
                    created_at=row[3], updated_at=row[4],
                    project_count=pc,
                ))
            return collections

    def update(self, collection_id: int, name: str | None = None, description: str | None = None) -> bool:
        """Actualiza nombre y/o descripción."""
        db = self._get_db()
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if not updates:
            return False

        updates.append("updated_at = datetime('now')")
        params.append(collection_id)

        with db.connection() as conn:
            conn.execute(
                f"UPDATE collections SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
        return True

    def delete(self, collection_id: int) -> bool:
        """Elimina colección (CASCADE borra entity links)."""
        db = self._get_db()
        with db.connection() as conn:
            # Primero desvincula proyectos
            conn.execute(
                "UPDATE projects SET collection_id = NULL, collection_order = 0 WHERE collection_id = ?",
                (collection_id,),
            )
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
            conn.commit()

            # Limpiar workspace auxiliar
            self._cleanup_workspace(collection_id)
        return True

    # ==================== Project membership ====================

    def add_project(self, collection_id: int, project_id: int, order: int = 0) -> dict:
        """
        Añade un proyecto a una colección.

        Retorna dict con posible warning si la colección es grande.
        """
        db = self._get_db()
        with db.connection() as conn:
            # Verificar que colección existe
            coll = conn.execute(
                "SELECT id FROM collections WHERE id = ?", (collection_id,)
            ).fetchone()
            if not coll:
                return {"success": False, "error": "Collection not found"}

            # Contar proyectos actuales
            count = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE collection_id = ?",
                (collection_id,),
            ).fetchone()[0]

            conn.execute(
                "UPDATE projects SET collection_id = ?, collection_order = ? WHERE id = ?",
                (collection_id, order or count, project_id),
            )
            conn.commit()

            result = {"success": True}
            if count + 1 > WARN_PROJECTS_THRESHOLD:
                result["warning"] = (
                    f"Colección con {count + 1} proyectos. "
                    f"El análisis cross-book puede tardar más."
                )
            return result

    def remove_project(self, collection_id: int, project_id: int) -> bool:
        """
        Quita un proyecto de la colección y limpia sus entity links.
        """
        db = self._get_db()
        with db.connection() as conn:
            conn.execute(
                "UPDATE projects SET collection_id = NULL, collection_order = 0 WHERE id = ? AND collection_id = ?",
                (project_id, collection_id),
            )
            # Limpiar entity links que referencian entidades de este proyecto
            conn.execute(
                """DELETE FROM collection_entity_links
                   WHERE collection_id = ?
                     AND (source_project_id = ? OR target_project_id = ?)""",
                (collection_id, project_id, project_id),
            )
            conn.commit()
        return True

    def get_projects(self, collection_id: int) -> list[dict]:
        """Lista proyectos de una colección."""
        db = self._get_db()
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT id, name, document_format, word_count, analysis_status,
                          collection_order
                   FROM projects WHERE collection_id = ?
                   ORDER BY collection_order""",
                (collection_id,),
            ).fetchall()
            return [
                {"id": r[0], "name": r[1], "document_format": r[2],
                 "word_count": r[3], "analysis_status": r[4],
                 "collection_order": r[5]}
                for r in rows
            ]

    # ==================== Entity links ====================

    def create_entity_link(
        self,
        collection_id: int,
        source_entity_id: int,
        target_entity_id: int,
        source_project_id: int,
        target_project_id: int,
        similarity: float = 1.0,
        match_type: str = "manual",
    ) -> dict:
        """
        Crea un enlace entre entidades de distintos libros.

        Valida que ambos proyectos pertenezcan a la colección.
        """
        db = self._get_db()
        with db.connection() as conn:
            # Validar pertenencia
            for pid in (source_project_id, target_project_id):
                row = conn.execute(
                    "SELECT collection_id FROM projects WHERE id = ?", (pid,)
                ).fetchone()
                if not row or row[0] != collection_id:
                    return {
                        "success": False,
                        "error": f"Project {pid} does not belong to collection {collection_id}",
                    }

            try:
                cursor = conn.execute(
                    """INSERT INTO collection_entity_links
                       (collection_id, source_entity_id, target_entity_id,
                        source_project_id, target_project_id, similarity, match_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (collection_id, source_entity_id, target_entity_id,
                     source_project_id, target_project_id, similarity, match_type),
                )
                conn.commit()
                link_id = cursor.lastrowid

                # Check warning threshold
                count = conn.execute(
                    "SELECT COUNT(*) FROM collection_entity_links WHERE collection_id = ?",
                    (collection_id,),
                ).fetchone()[0]

                result = {"success": True, "link_id": link_id}
                if count > WARN_ENTITY_LINKS_THRESHOLD:
                    result["warning"] = (
                        f"Colección con {count} enlaces de entidades. "
                        f"Esto es normal para sagas grandes."
                    )
                return result

            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    return {"success": False, "error": "Link already exists"}
                raise

    def delete_entity_link(self, link_id: int) -> bool:
        """Elimina un enlace de entidades."""
        db = self._get_db()
        with db.connection() as conn:
            conn.execute(
                "DELETE FROM collection_entity_links WHERE id = ?", (link_id,)
            )
            conn.commit()
        return True

    def get_entity_links(self, collection_id: int) -> list[EntityLink]:
        """Lista todos los enlaces de entidades de una colección."""
        db = self._get_db()
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT l.id, l.collection_id, l.source_entity_id, l.target_entity_id,
                          l.source_project_id, l.target_project_id,
                          l.similarity, l.match_type, l.created_at,
                          se.canonical_name, te.canonical_name,
                          sp.name, tp.name
                   FROM collection_entity_links l
                   LEFT JOIN entities se ON se.id = l.source_entity_id
                   LEFT JOIN entities te ON te.id = l.target_entity_id
                   LEFT JOIN projects sp ON sp.id = l.source_project_id
                   LEFT JOIN projects tp ON tp.id = l.target_project_id
                   WHERE l.collection_id = ?""",
                (collection_id,),
            ).fetchall()
            return [
                EntityLink(
                    id=r[0], collection_id=r[1],
                    source_entity_id=r[2], target_entity_id=r[3],
                    source_project_id=r[4], target_project_id=r[5],
                    similarity=r[6], match_type=r[7], created_at=r[8] or "",
                    source_entity_name=r[9] or "(eliminada)",
                    target_entity_name=r[10] or "(eliminada)",
                    source_project_name=r[11] or "(eliminado)",
                    target_project_name=r[12] or "(eliminado)",
                )
                for r in rows
            ]

    def get_link_suggestions(self, collection_id: int, threshold: float = 0.7) -> list[LinkSuggestion]:
        """
        Sugiere posibles enlaces entre entidades de distintos libros.

        Compara entidades del mismo tipo entre todos los pares de proyectos.
        """
        from ..analysis.entity_matcher import find_matches

        db = self._get_db()
        with db.connection() as conn:
            # Obtener proyectos de la colección
            projects = conn.execute(
                "SELECT id, name FROM projects WHERE collection_id = ?",
                (collection_id,),
            ).fetchall()

            if len(projects) < 2:
                return []

            # Obtener entidades por proyecto
            entities_by_project = {}
            for pid, pname in projects:
                rows = conn.execute(
                    """SELECT id, canonical_name, entity_type, importance
                       FROM entities WHERE project_id = ? AND is_active = 1""",
                    (pid,),
                ).fetchall()
                entities_by_project[pid] = {
                    "name": pname,
                    "entities": [
                        {"id": r[0], "canonical_name": r[1],
                         "entity_type": r[2], "importance": r[3]}
                        for r in rows
                    ],
                }

            # Obtener links existentes
            existing = set()
            links = conn.execute(
                """SELECT source_entity_id, target_entity_id
                   FROM collection_entity_links WHERE collection_id = ?""",
                (collection_id,),
            ).fetchall()
            for link in links:
                existing.add((link[0], link[1]))
                existing.add((link[1], link[0]))

        # Comparar pares de proyectos
        suggestions = []
        project_ids = list(entities_by_project.keys())

        for i, pid_a in enumerate(project_ids):
            for pid_b in project_ids[i + 1:]:
                data_a = entities_by_project[pid_a]
                data_b = entities_by_project[pid_b]

                matches = find_matches(
                    data_a["entities"], data_b["entities"],
                    threshold=threshold,
                )

                for match in matches:
                    # Find entity IDs
                    src_id = next(
                        (e["id"] for e in data_a["entities"]
                         if e["canonical_name"] == match.source_name),
                        None,
                    )
                    tgt_id = next(
                        (e["id"] for e in data_b["entities"]
                         if e["canonical_name"] == match.target_name),
                        None,
                    )
                    if not src_id or not tgt_id:
                        continue
                    if (src_id, tgt_id) in existing:
                        continue

                    suggestions.append(LinkSuggestion(
                        source_entity_id=src_id,
                        source_entity_name=match.source_name,
                        source_entity_type=match.source_type,
                        source_project_id=pid_a,
                        source_project_name=data_a["name"],
                        target_entity_id=tgt_id,
                        target_entity_name=match.target_name,
                        target_entity_type=match.target_type,
                        target_project_id=pid_b,
                        target_project_name=data_b["name"],
                        similarity=match.similarity,
                        match_type=match.match_type,
                    ))

        # Sort by similarity
        suggestions.sort(key=lambda s: s.similarity, reverse=True)
        return suggestions

    # ==================== Workspace auxiliar ====================

    @staticmethod
    def _get_workspace_dir(collection_id: int) -> Path:
        """Directorio de workspace auxiliar para una colección."""
        import os
        data_dir = os.environ.get("NA_DATA_DIR", str(Path.home() / ".narrative_assistant"))
        workspace = Path(data_dir) / "collections" / str(collection_id)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    @staticmethod
    def _cleanup_workspace(collection_id: int) -> None:
        """Elimina el workspace auxiliar de una colección."""
        import os
        import shutil
        data_dir = os.environ.get("NA_DATA_DIR", str(Path.home() / ".narrative_assistant"))
        workspace = Path(data_dir) / "collections" / str(collection_id)
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)

    def save_workspace_cache(self, collection_id: int, cache_type: str, data: dict) -> None:
        """Guarda datos en el workspace auxiliar (JSON)."""
        if cache_type not in VALID_CACHE_TYPES:
            logger.warning(f"Invalid cache_type rejected: {cache_type!r}")
            return
        workspace = self._get_workspace_dir(collection_id)
        cache_file = workspace / f"{cache_type}.json"
        cache_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_workspace_cache(self, collection_id: int, cache_type: str) -> dict | None:
        """Carga datos del workspace auxiliar."""
        if cache_type not in VALID_CACHE_TYPES:
            logger.warning(f"Invalid cache_type rejected: {cache_type!r}")
            return None
        import os
        data_dir = os.environ.get("NA_DATA_DIR", str(Path.home() / ".narrative_assistant"))
        cache_file = Path(data_dir) / "collections" / str(collection_id) / f"{cache_type}.json"
        if not cache_file.exists():
            return None
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
