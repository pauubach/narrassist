"""
Glosario de términos por proyecto.

Almacena términos específicos del manuscrito con sus definiciones,
permitiendo:
1. Detección de usos inconsistentes
2. Contexto para el chat LLM
3. Generación de glosario para publicación
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .database import Database, get_database

logger = logging.getLogger(__name__)


@dataclass
class GlossaryEntry:
    """
    Entrada del glosario de un proyecto.

    Diseñado para ser útil tanto en detección de inconsistencias
    como en contexto para el LLM.
    """

    # Identificación
    id: int | None = None
    project_id: int = 0

    # Término principal
    term: str = ""  # Forma canónica del término
    definition: str = ""  # Definición clara para humanos y LLM

    # Variantes aceptadas (para fuzzy matching)
    variants: list[str] = field(default_factory=list)  # ["variante1", "variante2"]

    # Clasificación
    category: str = "general"  # "personaje", "lugar", "objeto", "concepto", "técnico"
    subcategory: str | None = None  # Más específico si es necesario

    # Metadata para el LLM
    context_notes: str = ""  # Notas adicionales para el LLM (ej: "Solo aparece en capítulos 3-5")
    related_terms: list[str] = field(default_factory=list)  # Términos relacionados
    usage_example: str = ""  # Ejemplo de uso correcto

    # Flags
    is_technical: bool = False  # Término técnico que puede necesitar explicación
    is_invented: bool = False  # Término inventado por el autor (fantasía, ciencia ficción)
    is_proper_noun: bool = False  # Nombre propio (persona, lugar)
    include_in_publication_glossary: bool = False  # Incluir en glosario de la publicación

    # Estadísticas (actualizadas durante análisis)
    usage_count: int = 0  # Veces que aparece en el texto
    first_chapter: int | None = None  # Primer capítulo donde aparece

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        d = asdict(self)
        if self.created_at:
            d["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            d["updated_at"] = self.updated_at.isoformat()
        return d

    def to_llm_context(self) -> str:
        """
        Genera texto de contexto para el LLM.

        Formato optimizado para que el LLM entienda el término.
        """
        parts = [f"**{self.term}**"]

        if self.category != "general":
            parts.append(f"({self.category})")

        parts.append(f": {self.definition}")

        if self.variants:
            parts.append(f" [También: {', '.join(self.variants)}]")

        if self.context_notes:
            parts.append(f" Nota: {self.context_notes}")

        if self.related_terms:
            parts.append(f" Relacionado con: {', '.join(self.related_terms)}")

        return "".join(parts)

    @classmethod
    def from_row(cls, row: dict) -> "GlossaryEntry":
        """Crea desde fila de base de datos."""
        return cls(
            id=row.get("id"),
            project_id=row.get("project_id", 0),
            term=row.get("term", ""),
            definition=row.get("definition", ""),
            variants=json.loads(row.get("variants_json", "[]")),
            category=row.get("category", "general"),
            subcategory=row.get("subcategory"),
            context_notes=row.get("context_notes", ""),
            related_terms=json.loads(row.get("related_terms_json", "[]")),
            usage_example=row.get("usage_example", ""),
            is_technical=bool(row.get("is_technical", 0)),
            is_invented=bool(row.get("is_invented", 0)),
            is_proper_noun=bool(row.get("is_proper_noun", 0)),
            include_in_publication_glossary=bool(row.get("include_in_publication_glossary", 0)),
            usage_count=row.get("usage_count", 0),
            first_chapter=row.get("first_chapter"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None,
        )


class GlossaryRepository:
    """
    Repositorio para gestionar el glosario de un proyecto.

    Proporciona operaciones CRUD y métodos especializados para
    detección de inconsistencias y generación de contexto LLM.
    """

    # SQL para crear la tabla (se ejecuta en migración)
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS project_glossary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,

        -- Término y definición
        term TEXT NOT NULL,
        definition TEXT NOT NULL,
        variants_json TEXT DEFAULT '[]',

        -- Clasificación
        category TEXT DEFAULT 'general',
        subcategory TEXT,

        -- Metadata para LLM
        context_notes TEXT DEFAULT '',
        related_terms_json TEXT DEFAULT '[]',
        usage_example TEXT DEFAULT '',

        -- Flags
        is_technical INTEGER DEFAULT 0,
        is_invented INTEGER DEFAULT 0,
        is_proper_noun INTEGER DEFAULT 0,
        include_in_publication_glossary INTEGER DEFAULT 0,

        -- Estadísticas
        usage_count INTEGER DEFAULT 0,
        first_chapter INTEGER,

        -- Timestamps
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),

        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        UNIQUE (project_id, term)
    );

    CREATE INDEX IF NOT EXISTS idx_glossary_project ON project_glossary(project_id);
    CREATE INDEX IF NOT EXISTS idx_glossary_term ON project_glossary(term COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_glossary_category ON project_glossary(category);
    """

    def __init__(self, db: Database | None = None):
        """Inicializa el repositorio."""
        self.db = db or get_database()
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Crea la tabla si no existe."""
        try:
            # Verificar si la tabla existe
            row = self.db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='project_glossary'"
            )
            if row is None:
                # Crear tabla
                with self.db.connection() as conn:
                    for statement in self.CREATE_TABLE_SQL.split(";"):
                        statement = statement.strip()
                        if statement:
                            conn.execute(statement)
                logger.info("Tabla project_glossary creada")
        except Exception as e:
            logger.error(f"Error creando tabla glossary: {e}")

    def create(self, entry: GlossaryEntry) -> GlossaryEntry:
        """
        Crea una nueva entrada en el glosario.

        Args:
            entry: Entrada a crear

        Returns:
            Entrada con ID asignado

        Raises:
            ValueError: Si el término ya existe en el proyecto
        """
        now = datetime.now().isoformat()

        try:
            with self.db.connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO project_glossary (
                        project_id, term, definition, variants_json,
                        category, subcategory, context_notes, related_terms_json,
                        usage_example, is_technical, is_invented, is_proper_noun,
                        include_in_publication_glossary, usage_count, first_chapter,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.project_id,
                        entry.term,
                        entry.definition,
                        json.dumps(entry.variants),
                        entry.category,
                        entry.subcategory,
                        entry.context_notes,
                        json.dumps(entry.related_terms),
                        entry.usage_example,
                        int(entry.is_technical),
                        int(entry.is_invented),
                        int(entry.is_proper_noun),
                        int(entry.include_in_publication_glossary),
                        entry.usage_count,
                        entry.first_chapter,
                        now,
                        now,
                    ),
                )

            entry.id = cursor.lastrowid
            entry.created_at = datetime.fromisoformat(now)
            entry.updated_at = datetime.fromisoformat(now)

            logger.debug(f"Glosario: creado término '{entry.term}' (id={entry.id})")
            return entry

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"El término '{entry.term}' ya existe en el glosario")
            raise

    def get(self, entry_id: int) -> GlossaryEntry | None:
        """Obtiene una entrada por ID."""
        row = self.db.fetchone(
            "SELECT * FROM project_glossary WHERE id = ?",
            (entry_id,),
        )
        return GlossaryEntry.from_row(dict(row)) if row else None

    def get_by_term(self, project_id: int, term: str) -> GlossaryEntry | None:
        """Busca una entrada por término exacto (case insensitive)."""
        row = self.db.fetchone(
            "SELECT * FROM project_glossary WHERE project_id = ? AND term = ? COLLATE NOCASE",
            (project_id, term),
        )
        return GlossaryEntry.from_row(dict(row)) if row else None

    def find_by_term_or_variant(self, project_id: int, search_term: str) -> GlossaryEntry | None:
        """
        Busca una entrada por término principal o variantes.

        Útil para el detector de inconsistencias.
        """
        search_term = search_term.strip()
        if not search_term:
            return None

        # Primero buscar por término principal
        entry = self.get_by_term(project_id, search_term)
        if entry:
            return entry

        # Buscar en variantes con matching exacto usando JSON1.
        try:
            row = self.db.fetchone(
                """
                SELECT DISTINCT pg.* FROM project_glossary pg
                JOIN json_each(pg.variants_json) v
                WHERE pg.project_id = ?
                  AND LOWER(CAST(v.value AS TEXT)) = LOWER(?)
                LIMIT 1
                """,
                (project_id, search_term),
            )
            if row:
                return GlossaryEntry.from_row(dict(row))
        except Exception:
            logger.debug("json_each no disponible; usando fallback LIKE en variants_json")
            # Fallback para SQLite sin JSON1: prefiltro por LIKE + verificación precisa en Python.
            row = self.db.fetchone(
                """
                SELECT * FROM project_glossary
                WHERE project_id = ?
                AND (
                    variants_json LIKE ?
                    OR variants_json LIKE ?
                    OR variants_json LIKE ?
                )
                """,
                (
                    project_id,
                    f'["{search_term.lower()}",%',  # Primer elemento
                    f'%,"{search_term.lower()}"%',  # Elemento medio
                    f'%,"{search_term.lower()}"]',  # Último elemento
                ),
            )
            if row:
                entry = GlossaryEntry.from_row(dict(row))
                if search_term.lower() in [v.lower() for v in entry.variants]:
                    return entry

        return None

    def list_by_project(
        self,
        project_id: int,
        category: str | None = None,
        only_technical: bool = False,
        only_invented: bool = False,
        only_for_publication: bool = False,
    ) -> list[GlossaryEntry]:
        """
        Lista todas las entradas de un proyecto.

        Args:
            project_id: ID del proyecto
            category: Filtrar por categoría
            only_technical: Solo términos técnicos
            only_invented: Solo términos inventados
            only_for_publication: Solo para glosario de publicación
        """
        sql = "SELECT * FROM project_glossary WHERE project_id = ?"
        params: list[Any] = [project_id]

        if category:
            sql += " AND category = ?"
            params.append(category)
        if only_technical:
            sql += " AND is_technical = 1"
        if only_invented:
            sql += " AND is_invented = 1"
        if only_for_publication:
            sql += " AND include_in_publication_glossary = 1"

        sql += " ORDER BY term COLLATE NOCASE"

        rows = self.db.fetchall(sql, tuple(params))
        return [GlossaryEntry.from_row(dict(row)) for row in rows]

    def update(self, entry: GlossaryEntry) -> bool:
        """Actualiza una entrada existente."""
        if entry.id is None:
            return False

        now = datetime.now().isoformat()

        self.db.execute(
            """
            UPDATE project_glossary SET
                term = ?, definition = ?, variants_json = ?,
                category = ?, subcategory = ?, context_notes = ?,
                related_terms_json = ?, usage_example = ?,
                is_technical = ?, is_invented = ?, is_proper_noun = ?,
                include_in_publication_glossary = ?,
                usage_count = ?, first_chapter = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                entry.term,
                entry.definition,
                json.dumps(entry.variants),
                entry.category,
                entry.subcategory,
                entry.context_notes,
                json.dumps(entry.related_terms),
                entry.usage_example,
                int(entry.is_technical),
                int(entry.is_invented),
                int(entry.is_proper_noun),
                int(entry.include_in_publication_glossary),
                entry.usage_count,
                entry.first_chapter,
                now,
                entry.id,
            ),
        )

        entry.updated_at = datetime.fromisoformat(now)
        return True

    def delete(self, entry_id: int) -> bool:
        """Elimina una entrada del glosario."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM project_glossary WHERE id = ?",
                (entry_id,),
            )
            return cursor.rowcount > 0

    def delete_all_for_project(self, project_id: int) -> int:
        """Elimina todas las entradas de un proyecto."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM project_glossary WHERE project_id = ?",
                (project_id,),
            )
            return cursor.rowcount

    def increment_usage(self, entry_id: int, count: int = 1) -> None:
        """Incrementa el contador de uso de un término."""
        self.db.execute(
            "UPDATE project_glossary SET usage_count = usage_count + ? WHERE id = ?",
            (count, entry_id),
        )

    def get_all_terms(self, project_id: int) -> set[str]:
        """
        Obtiene todos los términos y variantes como un set.

        Útil para detección rápida de términos del glosario en el texto.
        """
        entries = self.list_by_project(project_id)
        terms = set()

        for entry in entries:
            terms.add(entry.term.lower())
            for variant in entry.variants:
                terms.add(variant.lower())

        return terms

    def generate_llm_context(
        self,
        project_id: int,
        max_entries: int = 50,
        categories: list[str] | None = None,
    ) -> str:
        """
        Genera contexto de glosario para el LLM.

        Args:
            project_id: ID del proyecto
            max_entries: Máximo de entradas a incluir
            categories: Categorías a incluir (None = todas)

        Returns:
            Texto formateado para usar como contexto del LLM
        """
        entries = self.list_by_project(project_id)

        # Filtrar por categorías si se especifican
        if categories:
            entries = [e for e in entries if e.category in categories]

        # Limitar cantidad
        if len(entries) > max_entries:
            # Priorizar términos inventados y técnicos
            entries.sort(
                key=lambda e: (
                    not e.is_invented,  # Inventados primero
                    not e.is_technical,  # Técnicos segundo
                    -e.usage_count,  # Más usados después
                )
            )
            entries = entries[:max_entries]

        if not entries:
            return ""

        lines = ["## Glosario del Proyecto", ""]

        # Agrupar por categoría
        by_category: dict[str, list[GlossaryEntry]] = {}
        for entry in entries:
            cat = entry.category or "general"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(entry)

        # Formatear
        for category, cat_entries in sorted(by_category.items()):
            lines.append(f"### {category.title()}")
            for entry in sorted(cat_entries, key=lambda e: e.term.lower()):
                lines.append(entry.to_llm_context())
            lines.append("")

        return "\n".join(lines)

    def export_for_publication(self, project_id: int) -> str:
        """
        Exporta el glosario para incluir en la publicación.

        Solo incluye términos marcados para publicación.
        """
        entries = self.list_by_project(project_id, only_for_publication=True)

        if not entries:
            return ""

        lines = ["# Glosario", ""]

        for entry in sorted(entries, key=lambda e: e.term.lower()):
            lines.append(f"**{entry.term}**: {entry.definition}")
            if entry.usage_example:
                lines.append(f"  _Ejemplo: {entry.usage_example}_")
            lines.append("")

        return "\n".join(lines)

    def import_from_dict(
        self, project_id: int, data: list[dict], merge: bool = True
    ) -> tuple[int, int]:
        """
        Importa entradas desde una lista de diccionarios.

        Args:
            project_id: ID del proyecto
            data: Lista de diccionarios con entradas
            merge: Si True, actualiza existentes; si False, salta

        Returns:
            Tupla (creados, actualizados)
        """
        created = 0
        updated = 0

        for item in data:
            term = item.get("term", "").strip()
            if not term:
                continue

            existing = self.get_by_term(project_id, term)

            entry = GlossaryEntry(
                id=existing.id if existing else None,
                project_id=project_id,
                term=term,
                definition=item.get("definition", ""),
                variants=item.get("variants", []),
                category=item.get("category", "general"),
                subcategory=item.get("subcategory"),
                context_notes=item.get("context_notes", ""),
                related_terms=item.get("related_terms", []),
                usage_example=item.get("usage_example", ""),
                is_technical=item.get("is_technical", False),
                is_invented=item.get("is_invented", False),
                is_proper_noun=item.get("is_proper_noun", False),
                include_in_publication_glossary=item.get("include_in_publication_glossary", False),
            )

            if existing:
                if merge:
                    self.update(entry)
                    updated += 1
            else:
                self.create(entry)
                created += 1

        return created, updated
