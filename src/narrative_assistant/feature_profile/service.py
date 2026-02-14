"""
Servicio de gestión de perfiles de features.
"""

import logging

from ..persistence.database import get_database
from .models import (
    DOCUMENT_SUBTYPES,
    DOCUMENT_TYPES,
    DocumentType,
    FeatureProfile,
    create_feature_profile,
)

logger = logging.getLogger(__name__)


class FeatureProfileService:
    """
    Servicio para gestionar perfiles de features por tipo de documento.

    Proporciona:
    - Obtención de perfil de features para un proyecto
    - Cambio de tipo de documento
    - Listado de tipos de documento disponibles
    - Detección sugerida de tipo de documento
    """

    def __init__(self, db=None):
        """
        Inicializa el servicio.

        Args:
            db: Instancia de Database (opcional)
        """
        self._db = db

    @property
    def db(self):
        """Obtiene la instancia de base de datos."""
        if self._db is None:
            self._db = get_database()
        return self._db

    # =========================================================================
    # Tipos de documento
    # =========================================================================

    def get_document_types(self) -> list[dict]:
        """
        Obtiene la lista de tipos de documento disponibles.

        Returns:
            Lista de diccionarios con información de cada tipo
        """
        result = []
        for doc_type in DocumentType:
            info = DOCUMENT_TYPES.get(doc_type, {})
            subtypes = DOCUMENT_SUBTYPES.get(doc_type, [])
            result.append(
                {
                    "code": doc_type.value,
                    "name": info.get("name", doc_type.value),
                    "description": info.get("description", ""),
                    "icon": info.get("icon", "pi-file"),
                    "color": info.get("color", "#6b7280"),
                    "subtypes": subtypes,
                }
            )
        return result

    def get_document_type_info(self, type_code: str) -> dict | None:
        """
        Obtiene información de un tipo de documento específico.

        Args:
            type_code: Código del tipo (FIC, MEM, etc.)

        Returns:
            Diccionario con información o None si no existe
        """
        try:
            doc_type = DocumentType(type_code)
            info = DOCUMENT_TYPES.get(doc_type, {})
            subtypes = DOCUMENT_SUBTYPES.get(doc_type, [])
            return {
                "code": doc_type.value,
                "name": info.get("name", doc_type.value),
                "description": info.get("description", ""),
                "icon": info.get("icon", "pi-file"),
                "color": info.get("color", "#6b7280"),
                "subtypes": subtypes,
            }
        except ValueError:
            return None

    # =========================================================================
    # Perfil de features
    # =========================================================================

    def get_project_profile(self, project_id: int) -> FeatureProfile | None:
        """
        Obtiene el perfil de features para un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            FeatureProfile o None si el proyecto no existe
        """
        row = self.db.fetchone(
            "SELECT document_type, document_subtype FROM projects WHERE id = ?",
            (project_id,),
        )
        if not row:
            return None

        doc_type_str = row["document_type"] or "FIC"
        doc_subtype = row["document_subtype"]

        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            doc_type = DocumentType.FICTION

        return create_feature_profile(doc_type, doc_subtype)

    def get_project_document_type(self, project_id: int) -> dict | None:
        """
        Obtiene el tipo de documento actual de un proyecto.

        Returns:
            Diccionario con type, subtype, confirmed, detected
        """
        row = self.db.fetchone(
            """SELECT document_type, document_subtype,
                      document_type_confirmed, detected_document_type
               FROM projects WHERE id = ?""",
            (project_id,),
        )
        if not row:
            return None

        doc_type_str = row["document_type"] or "FIC"
        type_info = self.get_document_type_info(doc_type_str)

        # Encontrar nombre del subtipo
        subtype_name = None
        if row["document_subtype"]:
            try:
                doc_type = DocumentType(doc_type_str)
                subtypes = DOCUMENT_SUBTYPES.get(doc_type, [])
                for st in subtypes:
                    if st["code"] == row["document_subtype"]:
                        subtype_name = st["name"]
                        break
            except ValueError:
                pass

        return {
            "type": doc_type_str,
            "type_name": type_info["name"] if type_info else doc_type_str,
            "type_icon": type_info["icon"] if type_info else "pi-file",
            "type_color": type_info["color"] if type_info else "#6b7280",
            "subtype": row["document_subtype"],
            "subtype_name": subtype_name,
            "confirmed": bool(row["document_type_confirmed"]),
            "detected_type": row["detected_document_type"],
            "has_mismatch": (
                row["detected_document_type"] is not None
                and row["detected_document_type"] != doc_type_str
            ),
        }

    def set_project_document_type(
        self,
        project_id: int,
        document_type: str,
        document_subtype: str | None = None,
        confirmed: bool = True,
    ) -> bool:
        """
        Establece el tipo de documento de un proyecto.

        Args:
            project_id: ID del proyecto
            document_type: Código del tipo (FIC, MEM, etc.)
            document_subtype: Código del subtipo (opcional)
            confirmed: Si el usuario ha confirmado explícitamente

        Returns:
            True si se actualizó correctamente
        """
        # Validar tipo
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            logger.warning(f"Invalid document type: {document_type}")
            return False

        # Validar subtipo si se proporciona
        if document_subtype:
            valid_subtypes = [st["code"] for st in DOCUMENT_SUBTYPES.get(doc_type, [])]
            if document_subtype not in valid_subtypes:
                logger.warning(f"Invalid subtype {document_subtype} for type {document_type}")
                document_subtype = None

        self.db.execute(
            """UPDATE projects
               SET document_type = ?,
                   document_subtype = ?,
                   document_type_confirmed = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (document_type, document_subtype, 1 if confirmed else 0, project_id),
        )

        logger.info(
            f"Updated project {project_id} document type: {document_type}"
            + (f"/{document_subtype}" if document_subtype else "")
        )
        return True

    def set_detected_document_type(
        self,
        project_id: int,
        detected_type: str,
    ) -> bool:
        """
        Establece el tipo de documento detectado por el sistema.

        No cambia el tipo actual, solo registra la sugerencia.

        Args:
            project_id: ID del proyecto
            detected_type: Código del tipo detectado

        Returns:
            True si se actualizó correctamente
        """
        # Validar tipo
        try:
            DocumentType(detected_type)
        except ValueError:
            logger.warning(f"Invalid detected document type: {detected_type}")
            return False

        self.db.execute(
            """UPDATE projects
               SET detected_document_type = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (detected_type, project_id),
        )

        logger.info(f"Set detected document type for project {project_id}: {detected_type}")
        return True

    # =========================================================================
    # Consultas de features
    # =========================================================================

    def is_feature_enabled(self, project_id: int, feature: str) -> bool:
        """
        Comprueba si una feature está habilitada para un proyecto.

        Args:
            project_id: ID del proyecto
            feature: Nombre de la feature (characters, timeline, scenes, etc.)

        Returns:
            True si la feature está habilitada
        """
        profile = self.get_project_profile(project_id)
        return profile.is_enabled(feature) if profile else False

    def is_feature_available(self, project_id: int, feature: str) -> bool:
        """
        Comprueba si una feature está disponible (enabled u optional).

        Args:
            project_id: ID del proyecto
            feature: Nombre de la feature

        Returns:
            True si la feature está disponible
        """
        profile = self.get_project_profile(project_id)
        return profile.is_available(feature) if profile else False

    def get_feature_availability(self, project_id: int, feature: str) -> str:
        """
        Obtiene el nivel de disponibilidad de una feature.

        Args:
            project_id: ID del proyecto
            feature: Nombre de la feature

        Returns:
            'enabled', 'optional', o 'disabled'
        """
        profile = self.get_project_profile(project_id)
        if not profile:
            return "disabled"

        val = getattr(profile, feature, None)
        return val.value if val else "disabled"  # type: ignore[no-any-return]

    def get_all_feature_availability(self, project_id: int) -> dict:
        """
        Obtiene la disponibilidad de todas las features.

        Args:
            project_id: ID del proyecto

        Returns:
            Diccionario feature -> availability
        """
        profile = self.get_project_profile(project_id)
        if not profile:
            return {}

        return profile.to_dict().get("features", {})  # type: ignore[no-any-return]

    # =========================================================================
    # Detección automática (placeholder para futuro ML)
    # =========================================================================

    def detect_document_type(self, project_id: int) -> str | None:
        """
        Detecta el tipo de documento basándose en el contenido.

        Por ahora usa heurísticas simples. En el futuro puede usar ML.

        Args:
            project_id: ID del proyecto

        Returns:
            Código del tipo detectado o None
        """
        # Obtener estadísticas del proyecto
        row = self.db.fetchone(
            """SELECT word_count, chapter_count FROM projects WHERE id = ?""",
            (project_id,),
        )
        if not row:
            return None

        word_count = row["word_count"] or 0
        chapter_count = row["chapter_count"] or 0

        # Contar entidades por tipo
        entity_counts = {}
        for row in self.db.fetchall(
            """SELECT entity_type, COUNT(*) as cnt
               FROM entities WHERE project_id = ? AND is_active = 1
               GROUP BY entity_type""",
            (project_id,),
        ):
            entity_counts[row["entity_type"]] = row["cnt"]

        character_count = entity_counts.get("character", 0)
        location_count = entity_counts.get("location", 0)

        # Heurísticas simples
        # Muchos personajes y ubicaciones -> probablemente ficción
        if character_count >= 5 and location_count >= 3:
            return DocumentType.FICTION.value

        # Pocos personajes, pocas ubicaciones, texto largo -> probablemente ensayo
        if character_count <= 2 and location_count <= 2 and word_count > 20000:
            return DocumentType.ESSAY.value

        # Texto corto con estructura -> podría ser práctico
        if word_count < 30000 and chapter_count > 10:
            return DocumentType.PRACTICAL.value

        # Por defecto asumimos ficción (el tipo más común)
        return DocumentType.FICTION.value
