"""
Sistema de declaracion de focalizacion.

Permite al usuario declarar la focalizacion de cada capitulo/escena.
El sistema luego detecta violaciones a esa declaracion.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class FocalizationType(Enum):
    """Tipos de focalizacion segun Genette."""

    ZERO = "zero"  # Omnisciente, acceso a todo
    INTERNAL_FIXED = "internal_fixed"  # Un solo personaje
    INTERNAL_VARIABLE = "internal_variable"  # Cambia por escena
    INTERNAL_MULTIPLE = "internal_multiple"  # Varios simultaneos
    EXTERNAL = "external"  # Solo observable


@dataclass
class FocalizationDeclaration:
    """Declaracion de focalizacion para un capitulo/escena."""

    id: int
    project_id: int
    chapter: int
    scene: int | None = None  # None = todo el capitulo

    focalization_type: FocalizationType = FocalizationType.ZERO
    focalizer_ids: list[int] = field(default_factory=list)  # IDs de personajes focalizadores

    # Metadata
    declared_at: datetime = field(default_factory=datetime.now)
    declared_by: str = "user"  # 'user' o 'system_suggestion'
    notes: str = ""

    # Validacion
    is_validated: bool = False
    violations_count: int = 0

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter": self.chapter,
            "scene": self.scene,
            "focalization_type": self.focalization_type.value,
            "focalizer_ids": self.focalizer_ids,
            "declared_at": self.declared_at.isoformat(),
            "declared_by": self.declared_by,
            "notes": self.notes,
            "is_validated": self.is_validated,
            "violations_count": self.violations_count,
        }


@dataclass
class FocalizationScope:
    """Define el alcance de una focalizacion."""

    start_chapter: int
    start_scene: int | None = None
    end_chapter: int = 0
    end_scene: int | None = None

    def __post_init__(self):
        if self.end_chapter == 0:
            self.end_chapter = self.start_chapter

    def contains(self, chapter: int, scene: int | None = None) -> bool:
        """Verifica si una posicion esta dentro del alcance."""
        if chapter < self.start_chapter or chapter > self.end_chapter:
            return False
        if chapter == self.start_chapter and scene is not None:
            if self.start_scene is not None and scene < self.start_scene:
                return False
        if chapter == self.end_chapter and scene is not None:
            if self.end_scene is not None and scene > self.end_scene:
                return False
        return True


class FocalizationRepository(Protocol):
    """Protocolo para repositorio de focalizacion."""

    def get_entity(self, entity_id: int) -> Any | None:
        """Obtiene una entidad por ID."""
        ...

    def save_focalization(self, declaration: FocalizationDeclaration) -> FocalizationDeclaration:
        """Guarda una declaracion."""
        ...

    def get_focalization(
        self, project_id: int, chapter: int, scene: int | None
    ) -> FocalizationDeclaration | None:
        """Obtiene focalizacion para un capitulo/escena."""
        ...

    def get_focalization_by_id(self, declaration_id: int) -> FocalizationDeclaration | None:
        """Obtiene focalizacion por ID."""
        ...

    def get_all_focalizations(self, project_id: int) -> list[FocalizationDeclaration]:
        """Obtiene todas las focalizaciones de un proyecto."""
        ...

    def delete_focalization(self, declaration_id: int) -> bool:
        """Elimina una declaracion."""
        ...


class InMemoryFocalizationRepository:
    """Implementacion en memoria del repositorio de focalizacion."""

    def __init__(self):
        self.focalizations: dict[int, FocalizationDeclaration] = {}
        self.counter: int = 0
        self.entities: dict[int, Any] = {}

    def set_entities(self, entities: dict[int, Any]) -> None:
        """Configura las entidades disponibles."""
        self.entities = entities

    def get_entity(self, entity_id: int) -> Any | None:
        return self.entities.get(entity_id)

    def save_focalization(self, declaration: FocalizationDeclaration) -> FocalizationDeclaration:
        if declaration.id == 0:
            self.counter += 1
            declaration.id = self.counter
        self.focalizations[declaration.id] = declaration
        return declaration

    def get_focalization(
        self, project_id: int, chapter: int, scene: int | None
    ) -> FocalizationDeclaration | None:
        for f in self.focalizations.values():
            if f.project_id == project_id and f.chapter == chapter and f.scene == scene:
                return f
        return None

    def get_focalization_by_id(self, declaration_id: int) -> FocalizationDeclaration | None:
        return self.focalizations.get(declaration_id)

    def get_all_focalizations(self, project_id: int) -> list[FocalizationDeclaration]:
        return [f for f in self.focalizations.values() if f.project_id == project_id]

    def delete_focalization(self, declaration_id: int) -> bool:
        if declaration_id in self.focalizations:
            del self.focalizations[declaration_id]
            return True
        return False


class FocalizationDeclarationService:
    """Servicio para gestionar declaraciones de focalizacion."""

    def __init__(self, repository: FocalizationRepository | None = None):
        """
        Inicializa el servicio.

        Args:
            repository: Repositorio de focalizacion (opcional, usa en memoria si no se proporciona)
        """
        self.repo = repository or InMemoryFocalizationRepository()

    def declare_focalization(
        self,
        project_id: int,
        chapter: int,
        focalization_type: FocalizationType,
        focalizer_ids: list[int],
        scene: int | None = None,
        notes: str = "",
    ) -> FocalizationDeclaration:
        """
        Declara la focalizacion de un capitulo/escena.

        Args:
            project_id: ID del proyecto
            chapter: Numero de capitulo
            focalization_type: Tipo de focalizacion
            focalizer_ids: IDs de los personajes focalizadores
            scene: Numero de escena (opcional)
            notes: Notas adicionales

        Returns:
            Declaracion creada
        """
        # Validar que los focalizadores existen (si hay repositorio con entidades)
        if hasattr(self.repo, "get_entity"):
            for fid in focalizer_ids:
                entity = self.repo.get_entity(fid)
                if entity and hasattr(entity, "entity_type"):
                    if entity.entity_type not in ("person", "PERSON", "PER", "CHARACTER"):
                        raise ValueError(f"Entity {fid} is not a person")

        # Validar coherencia tipo-focalizadores
        self._validate_focalization_type(focalization_type, focalizer_ids)

        declaration = FocalizationDeclaration(
            id=0,  # Se asigna al guardar
            project_id=project_id,
            chapter=chapter,
            scene=scene,
            focalization_type=focalization_type,
            focalizer_ids=focalizer_ids,
            declared_at=datetime.now(),
            declared_by="user",
            notes=notes,
            is_validated=False,
            violations_count=0,
        )

        saved = self.repo.save_focalization(declaration)
        logger.info(f"Declared focalization for chapter {chapter}: {focalization_type.value}")
        return saved

    def _validate_focalization_type(
        self, foc_type: FocalizationType, focalizer_ids: list[int]
    ) -> None:
        """Valida coherencia entre tipo y focalizadores."""
        if foc_type == FocalizationType.ZERO:
            # Omnisciente: no necesita focalizadores especificos
            pass
        elif foc_type == FocalizationType.INTERNAL_FIXED:
            if len(focalizer_ids) != 1:
                raise ValueError("Internal fixed requires exactly 1 focalizer")
        elif foc_type == FocalizationType.INTERNAL_VARIABLE:
            if len(focalizer_ids) < 1:
                raise ValueError("Internal variable requires at least 1 focalizer")
        elif foc_type == FocalizationType.INTERNAL_MULTIPLE:
            if len(focalizer_ids) < 2:
                raise ValueError("Internal multiple requires at least 2 focalizers")
        elif foc_type == FocalizationType.EXTERNAL and focalizer_ids:
            raise ValueError("External focalization should not have focalizers")

    def get_focalization(
        self, project_id: int, chapter: int, scene: int | None = None
    ) -> FocalizationDeclaration | None:
        """Obtiene la focalizacion declarada para una posicion."""
        # Buscar declaracion especifica para escena
        if scene is not None:
            declaration = self.repo.get_focalization(project_id, chapter, scene)
            if declaration:
                return declaration

        # Buscar declaracion para capitulo completo
        return self.repo.get_focalization(project_id, chapter, None)

    def get_all_declarations(self, project_id: int) -> list[FocalizationDeclaration]:
        """Obtiene todas las declaraciones de un proyecto."""
        return self.repo.get_all_focalizations(project_id)

    def update_focalization(
        self,
        declaration_id: int,
        focalization_type: FocalizationType | None = None,
        focalizer_ids: list[int] | None = None,
        notes: str | None = None,
    ) -> FocalizationDeclaration:
        """Actualiza una declaracion existente."""
        declaration = self.repo.get_focalization_by_id(declaration_id)
        if not declaration:
            raise ValueError(f"Declaration {declaration_id} not found")

        if focalization_type is not None:
            ids = focalizer_ids if focalizer_ids is not None else declaration.focalizer_ids
            self._validate_focalization_type(focalization_type, ids)
            declaration.focalization_type = focalization_type

        if focalizer_ids is not None:
            ftype = (
                focalization_type
                if focalization_type is not None
                else declaration.focalization_type
            )
            self._validate_focalization_type(ftype, focalizer_ids)
            declaration.focalizer_ids = focalizer_ids

        if notes is not None:
            declaration.notes = notes

        # Resetear validacion al modificar
        declaration.is_validated = False
        declaration.violations_count = 0

        return self.repo.save_focalization(declaration)

    def delete_focalization(self, declaration_id: int) -> bool:
        """Elimina una declaracion."""
        return self.repo.delete_focalization(declaration_id)

    def suggest_focalization(
        self, project_id: int, chapter: int, text: str, entities: list[Any]
    ) -> dict[str, Any]:
        """
        Sugiere posible focalizacion basandose en el texto.

        Usa deteccion de persona gramatical y verbos de acceso mental
        del modulo de violaciones para mayor precision.

        Args:
            project_id: ID del proyecto
            chapter: Numero de capitulo
            text: Texto a analizar
            entities: Lista de entidades del proyecto

        Returns:
            Diccionario con sugerencia y evidencia
        """
        from narrative_assistant.focalization.violations import (
            MENTAL_ACCESS_PATTERNS,
            MENTAL_ACCESS_VERBS,
        )

        suggestions: dict[str, Any] = {
            "suggested_type": None,
            "suggested_focalizers": [],
            "confidence": 0.0,
            "evidence": [],
        }

        text_lower = text.lower()

        # --- Paso 1: Detectar persona gramatical ---
        first_person_markers = re.findall(
            r"\b(yo|me|mí|conmigo|soy|estoy|tengo|hago|voy|digo|sé|veo|"
            r"quiero|puedo|debo|pensé|sentí|miré|caminé|dije|vi|hice|fui|"
            r"pienso|siento|miro|camino|hablo|escribo)\b",
            text_lower,
        )
        third_person_markers = re.findall(
            r"\b(él|ella|ellos|ellas|lo|la|los|las|le|les|su|sus|"
            r"suyo|suya|suyos|suyas)\b",
            text_lower,
        )

        is_first_person = len(first_person_markers) >= 3
        is_third_person = len(third_person_markers) >= 3 and not is_first_person

        if is_first_person:
            suggestions["suggested_type"] = FocalizationType.INTERNAL_FIXED
            suggestions["confidence"] = 0.90
            suggestions["evidence"].append(
                f"Narrador en primera persona ({len(first_person_markers)} marcadores: "
                f"{', '.join(list(set(first_person_markers))[:5])})"
            )
            # El focalizador es el narrador (no podemos identificar entity_id aqui)
            return suggestions

        # --- Paso 2: Buscar verbos de acceso mental (diccionario completo) ---
        all_mental_verbs: set[str] = set()
        for verb_forms in MENTAL_ACCESS_VERBS.values():
            all_mental_verbs.update(v.lower() for v in verb_forms)

        found_verbs: list[str] = []
        for verb in all_mental_verbs:
            if verb in text_lower:
                found_verbs.append(verb)

        # --- Paso 3: Buscar patrones de acceso mental con sujeto ---
        characters_with_thoughts: dict[int, list[str]] = {}  # entity_id -> evidence
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in MENTAL_ACCESS_PATTERNS]

        for entity in entities:
            if not hasattr(entity, "entity_type"):
                continue
            etype = entity.entity_type
            if hasattr(etype, "value"):
                etype = etype.value
            if etype not in ("person", "PERSON", "PER", "CHARACTER"):
                continue

            name = getattr(entity, "canonical_name", getattr(entity, "name", "")).lower()
            entity_id = getattr(entity, "id", None)
            if not entity_id or not name:
                continue

            # Buscar nombre + verbo mental en proximidad (misma oracion)
            evidence_for_entity: list[str] = []
            for verb in found_verbs:
                # Patron: nombre cerca de verbo (max 60 chars)
                if re.search(
                    rf"\b{re.escape(name)}\b.{{0,60}}\b{re.escape(verb)}\b"
                    rf"|\b{re.escape(verb)}\b.{{0,60}}\b{re.escape(name)}\b",
                    text_lower,
                ):
                    evidence_for_entity.append(f"'{name}' + '{verb}'")

            # Buscar patrones estructurales con nombre como sujeto
            for pattern in compiled_patterns:
                for m in pattern.finditer(text_lower):
                    # Capturar grupo 1 (sujeto) si coincide con nombre
                    subject = m.group(1).lower() if m.groups() else ""
                    if subject and name.startswith(subject):
                        evidence_for_entity.append(f"patron: '{m.group()[:50]}'")

            if evidence_for_entity:
                characters_with_thoughts[entity_id] = evidence_for_entity

        # --- Paso 4: Clasificar ---
        n_focalizers = len(characters_with_thoughts)
        n_verbs = len(found_verbs)

        if n_verbs == 0:
            # Sin acceso mental → externa
            suggestions["suggested_type"] = FocalizationType.EXTERNAL
            suggestions["confidence"] = 0.75 if is_third_person else 0.50
            suggestions["evidence"].append(
                "No se detectan verbos de acceso mental (pensamiento, emocion, percepcion interna)"
            )
        elif n_focalizers == 0:
            # Verbos mentales pero sin sujeto claro → omnisciente
            suggestions["suggested_type"] = FocalizationType.ZERO
            suggestions["confidence"] = 0.60
            suggestions["evidence"].append(
                f"{n_verbs} verbos de acceso mental detectados sin sujeto claro"
            )
        elif n_focalizers == 1:
            # Un solo personaje con acceso mental → interna fija
            eid = next(iter(characters_with_thoughts))
            ev = characters_with_thoughts[eid]
            suggestions["suggested_type"] = FocalizationType.INTERNAL_FIXED
            suggestions["suggested_focalizers"] = [eid]
            suggestions["confidence"] = min(0.85, 0.65 + len(ev) * 0.05)
            suggestions["evidence"].extend(ev[:5])
        else:
            # Multiples personajes → variable o cero
            total_evidence = sum(len(v) for v in characters_with_thoughts.values())
            if total_evidence >= 4:
                suggestions["suggested_type"] = FocalizationType.INTERNAL_VARIABLE
                suggestions["suggested_focalizers"] = list(characters_with_thoughts.keys())
                suggestions["confidence"] = 0.70
            else:
                suggestions["suggested_type"] = FocalizationType.ZERO
                suggestions["confidence"] = 0.55
            for eid, ev in characters_with_thoughts.items():
                suggestions["evidence"].extend(ev[:3])

        return suggestions

    def generate_summary(self, project_id: int) -> str:
        """Genera resumen de focalizacion del proyecto."""
        declarations = self.get_all_declarations(project_id)

        if not declarations:
            return "No hay declaraciones de focalizacion registradas."

        lines = [
            "# Resumen de Focalizacion",
            "",
            f"Total de declaraciones: {len(declarations)}",
            "",
            "| Capitulo | Escena | Tipo | Focalizador(es) | Validado |",
            "|----------|--------|------|-----------------|----------|",
        ]

        for dec in sorted(declarations, key=lambda d: (d.chapter, d.scene or 0)):
            scene_str = str(dec.scene) if dec.scene else "-"
            focalizers = ", ".join(str(fid) for fid in dec.focalizer_ids) or "N/A"
            validated = "Si" if dec.is_validated else "No"

            lines.append(
                f"| {dec.chapter} | {scene_str} | {dec.focalization_type.value} | "
                f"{focalizers} | {validated} |"
            )

        return "\n".join(lines)


class SQLiteFocalizationRepository:
    """
    Implementación SQLite del repositorio de focalización.

    Persiste las declaraciones de focalización en la base de datos
    para que se mantengan entre sesiones.
    """

    def __init__(self, database=None):
        """
        Inicializa el repositorio.

        Args:
            database: Instancia de Database. Si None, usa singleton.
        """
        from ..persistence.database import get_database

        self.db = database or get_database()
        self._entities_cache: dict[int, Any] = {}

    def set_entities(self, entities: dict[int, Any]) -> None:
        """Configura las entidades disponibles."""
        self._entities_cache = entities

    def get_entity(self, entity_id: int) -> Any | None:
        """Obtiene una entidad por ID."""
        if entity_id in self._entities_cache:
            return self._entities_cache[entity_id]

        # Buscar en la base de datos
        from ..entities.repository import get_entity_repository

        entity_repo = get_entity_repository()
        return entity_repo.get_entity(entity_id)

    def save_focalization(self, declaration: FocalizationDeclaration) -> FocalizationDeclaration:
        """
        Guarda una declaración de focalización.

        Si id=0, crea nueva. Si id>0, actualiza existente.
        """
        import json

        focalizer_json = json.dumps(declaration.focalizer_ids)

        if declaration.id == 0:
            # Insertar nueva
            sql = """
                INSERT INTO focalization_declarations (
                    project_id, chapter, scene, focalization_type,
                    focalizer_ids, declared_at, declared_by, notes,
                    is_validated, violations_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            with self.db.connection() as conn:
                cursor = conn.execute(
                    sql,
                    (
                        declaration.project_id,
                        declaration.chapter,
                        declaration.scene,
                        declaration.focalization_type.value,
                        focalizer_json,
                        declaration.declared_at.isoformat(),
                        declaration.declared_by,
                        declaration.notes,
                        1 if declaration.is_validated else 0,
                        declaration.violations_count,
                    ),
                )
                declaration.id = cursor.lastrowid
                logger.debug(f"Created focalization declaration ID={declaration.id}")
        else:
            # Actualizar existente
            sql = """
                UPDATE focalization_declarations SET
                    focalization_type = ?,
                    focalizer_ids = ?,
                    notes = ?,
                    is_validated = ?,
                    violations_count = ?
                WHERE id = ?
            """
            with self.db.connection() as conn:
                conn.execute(
                    sql,
                    (
                        declaration.focalization_type.value,
                        focalizer_json,
                        declaration.notes,
                        1 if declaration.is_validated else 0,
                        declaration.violations_count,
                        declaration.id,
                    ),
                )
                logger.debug(f"Updated focalization declaration ID={declaration.id}")

        return declaration

    def get_focalization(
        self, project_id: int, chapter: int, scene: int | None
    ) -> FocalizationDeclaration | None:
        """Obtiene focalización para un capítulo/escena."""
        if scene is not None:
            row = self.db.fetchone(
                """SELECT * FROM focalization_declarations
                WHERE project_id = ? AND chapter = ? AND scene = ?""",
                (project_id, chapter, scene),
            )
        else:
            row = self.db.fetchone(
                """SELECT * FROM focalization_declarations
                WHERE project_id = ? AND chapter = ? AND scene IS NULL""",
                (project_id, chapter),
            )

        return self._row_to_declaration(row) if row else None

    def get_focalization_by_id(self, declaration_id: int) -> FocalizationDeclaration | None:
        """Obtiene focalización por ID."""
        row = self.db.fetchone(
            "SELECT * FROM focalization_declarations WHERE id = ?",
            (declaration_id,),
        )
        return self._row_to_declaration(row) if row else None

    def get_all_focalizations(self, project_id: int) -> list[FocalizationDeclaration]:
        """Obtiene todas las focalizaciones de un proyecto."""
        rows = self.db.fetchall(
            """SELECT * FROM focalization_declarations
            WHERE project_id = ?
            ORDER BY chapter, scene""",
            (project_id,),
        )
        return [self._row_to_declaration(row) for row in rows]

    def delete_focalization(self, declaration_id: int) -> bool:
        """Elimina una declaración."""
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM focalization_declarations WHERE id = ?",
                (declaration_id,),
            )
            return cursor.rowcount > 0  # type: ignore[no-any-return]

    def _row_to_declaration(self, row) -> FocalizationDeclaration:
        """Convierte una fila de SQLite a FocalizationDeclaration."""
        import json

        focalizer_ids = json.loads(row["focalizer_ids"]) if row["focalizer_ids"] else []

        return FocalizationDeclaration(
            id=row["id"],
            project_id=row["project_id"],
            chapter=row["chapter"],
            scene=row["scene"],
            focalization_type=FocalizationType(row["focalization_type"]),
            focalizer_ids=focalizer_ids,
            declared_at=datetime.fromisoformat(row["declared_at"])
            if row["declared_at"]
            else datetime.now(),
            declared_by=row["declared_by"] or "user",
            notes=row["notes"] or "",
            is_validated=bool(row["is_validated"]),
            violations_count=row["violations_count"] or 0,
        )


def get_focalization_service(use_sqlite: bool = True) -> FocalizationDeclarationService:
    """
    Obtiene el servicio de focalización con el repositorio apropiado.

    Args:
        use_sqlite: Si True, usa SQLite. Si False, usa memoria.

    Returns:
        FocalizationDeclarationService configurado
    """
    if use_sqlite:
        repo = SQLiteFocalizationRepository()
    else:
        repo = InMemoryFocalizationRepository()  # type: ignore[assignment]

    return FocalizationDeclarationService(repository=repo)
