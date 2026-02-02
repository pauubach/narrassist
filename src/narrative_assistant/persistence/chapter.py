"""
Repositorio de capítulos.

Gestiona el almacenamiento y recuperación de capítulos detectados en documentos.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .database import Database, get_database

logger = logging.getLogger(__name__)


@dataclass
class ChapterData:
    """Datos de un capítulo almacenado."""

    id: Optional[int]
    project_id: int
    chapter_number: int
    title: Optional[str]
    content: str
    start_char: int
    end_char: int
    word_count: int
    structure_type: str = "chapter"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # --- Métricas de enriquecimiento (computadas post-análisis) ---
    # Pacing & estructura
    dialogue_ratio: Optional[float] = None  # Porcentaje de diálogo (0.0-1.0)
    avg_sentence_length: Optional[float] = None  # Longitud media de oración (palabras)
    scene_count: Optional[int] = None  # Número de escenas detectadas

    # Personajes
    characters_present_count: Optional[int] = None  # Personajes únicos presentes
    pov_character: Optional[str] = None  # Personaje POV principal (si detectado)

    # Tono emocional
    dominant_tone: Optional[str] = None  # "positive", "negative", "neutral", "tense", etc.
    tone_intensity: Optional[float] = None  # Intensidad emocional (0.0-1.0)

    # Legibilidad
    reading_time_minutes: Optional[int] = None  # Tiempo estimado de lectura

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        d = {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_number": self.chapter_number,
            "title": self.title or f"Capítulo {self.chapter_number}",
            "content": self.content,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "word_count": self.word_count,
            "structure_type": self.structure_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        # Incluir métricas solo si están computadas
        metrics = {
            "dialogue_ratio": self.dialogue_ratio,
            "avg_sentence_length": self.avg_sentence_length,
            "scene_count": self.scene_count,
            "characters_present_count": self.characters_present_count,
            "pov_character": self.pov_character,
            "dominant_tone": self.dominant_tone,
            "tone_intensity": self.tone_intensity,
            "reading_time_minutes": self.reading_time_minutes,
        }
        # Solo incluir métricas que tengan valor
        d["metrics"] = {k: v for k, v in metrics.items() if v is not None}
        return d

    @classmethod
    def from_row(cls, row) -> "ChapterData":
        """Crea desde una fila de SQLite."""
        keys = row.keys() if hasattr(row, "keys") else []
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter_number=row["chapter_number"],
            title=row["title"],
            content=row["content"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            word_count=row["word_count"],
            structure_type=row["structure_type"] or "chapter",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            # Métricas (pueden no existir en esquemas antiguos)
            dialogue_ratio=row["dialogue_ratio"] if "dialogue_ratio" in keys else None,
            avg_sentence_length=row["avg_sentence_length"] if "avg_sentence_length" in keys else None,
            scene_count=row["scene_count"] if "scene_count" in keys else None,
            characters_present_count=row["characters_present_count"] if "characters_present_count" in keys else None,
            pov_character=row["pov_character"] if "pov_character" in keys else None,
            dominant_tone=row["dominant_tone"] if "dominant_tone" in keys else None,
            tone_intensity=row["tone_intensity"] if "tone_intensity" in keys else None,
            reading_time_minutes=row["reading_time_minutes"] if "reading_time_minutes" in keys else None,
        )


class ChapterRepository:
    """
    Repositorio para gestionar capítulos en la base de datos.

    Permite crear, leer, actualizar y eliminar capítulos de un proyecto.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database. Si es None, usa singleton.
        """
        self.db = db or get_database()

    def create(self, chapter: ChapterData) -> ChapterData:
        """
        Crea un nuevo capítulo.

        Args:
            chapter: Datos del capítulo a crear

        Returns:
            Capítulo creado con ID asignado
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chapters (
                    project_id, chapter_number, title, content,
                    start_char, end_char, word_count, structure_type,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter.project_id,
                    chapter.chapter_number,
                    chapter.title,
                    chapter.content,
                    chapter.start_char,
                    chapter.end_char,
                    chapter.word_count,
                    chapter.structure_type,
                    now,
                    now,
                ),
            )
            chapter.id = cursor.lastrowid
            chapter.created_at = now
            chapter.updated_at = now

        logger.debug(f"Creado capítulo {chapter.chapter_number} para proyecto {chapter.project_id}")
        return chapter

    def create_many(self, chapters: list[ChapterData]) -> list[ChapterData]:
        """
        Crea múltiples capítulos en una transacción.

        Args:
            chapters: Lista de capítulos a crear

        Returns:
            Lista de capítulos creados con IDs asignados
        """
        if not chapters:
            return []

        now = datetime.now().isoformat()
        created = []

        with self.db.transaction() as conn:
            for chapter in chapters:
                cursor = conn.execute(
                    """
                    INSERT INTO chapters (
                        project_id, chapter_number, title, content,
                        start_char, end_char, word_count, structure_type,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chapter.project_id,
                        chapter.chapter_number,
                        chapter.title,
                        chapter.content,
                        chapter.start_char,
                        chapter.end_char,
                        chapter.word_count,
                        chapter.structure_type,
                        now,
                        now,
                    ),
                )
                chapter.id = cursor.lastrowid
                chapter.created_at = now
                chapter.updated_at = now
                created.append(chapter)

        logger.info(f"Creados {len(created)} capítulos para proyecto {chapters[0].project_id if chapters else 'N/A'}")
        return created

    def get_by_id(self, chapter_id: int) -> Optional[ChapterData]:
        """
        Obtiene un capítulo por su ID.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Capítulo encontrado o None
        """
        row = self.db.fetchone(
            "SELECT * FROM chapters WHERE id = ?",
            (chapter_id,)
        )
        return ChapterData.from_row(row) if row else None

    def get_by_project(self, project_id: int) -> list[ChapterData]:
        """
        Obtiene todos los capítulos de un proyecto ordenados por número.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de capítulos ordenados
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM chapters
            WHERE project_id = ?
            ORDER BY chapter_number ASC
            """,
            (project_id,)
        )
        return [ChapterData.from_row(row) for row in rows]

    def delete_by_project(self, project_id: int) -> int:
        """
        Elimina todos los capítulos de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de capítulos eliminados
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM chapters WHERE project_id = ?",
                (project_id,)
            )
            count = cursor.rowcount

        logger.info(f"Eliminados {count} capítulos del proyecto {project_id}")
        return count

    def update_metrics(self, chapter_id: int, metrics: dict) -> bool:
        """
        Actualiza las métricas de enriquecimiento de un capítulo.

        Args:
            chapter_id: ID del capítulo
            metrics: Diccionario con las métricas a actualizar.
                Claves válidas: dialogue_ratio, avg_sentence_length, scene_count,
                characters_present_count, pov_character, dominant_tone,
                tone_intensity, reading_time_minutes.

        Returns:
            True si se actualizó, False si no existe o no hay métricas
        """
        valid_keys = {
            "dialogue_ratio", "avg_sentence_length", "scene_count",
            "characters_present_count", "pov_character", "dominant_tone",
            "tone_intensity", "reading_time_minutes",
        }
        filtered = {k: v for k, v in metrics.items() if k in valid_keys}
        if not filtered:
            return False

        now = datetime.now().isoformat()
        set_clauses = [f"{k} = ?" for k in filtered]
        set_clauses.append("updated_at = ?")
        values = list(filtered.values()) + [now, chapter_id]

        sql = f"UPDATE chapters SET {', '.join(set_clauses)} WHERE id = ?"

        with self.db.connection() as conn:
            cursor = conn.execute(sql, values)
            return cursor.rowcount > 0

    def update_content(self, chapter_id: int, content: str, word_count: int) -> bool:
        """
        Actualiza el contenido de un capítulo.

        Args:
            chapter_id: ID del capítulo
            content: Nuevo contenido
            word_count: Nuevo conteo de palabras

        Returns:
            True si se actualizó, False si no existe
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE chapters
                SET content = ?, word_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (content, word_count, now, chapter_id)
            )
            return cursor.rowcount > 0


# Función de conveniencia para obtener instancia
def get_chapter_repository(db: Optional[Database] = None) -> ChapterRepository:
    """Obtiene una instancia del repositorio de capítulos."""
    return ChapterRepository(db)


@dataclass
class SectionData:
    """Datos de una sección (H2, H3, H4) dentro de un capítulo."""

    id: Optional[int]
    project_id: int
    chapter_id: int
    parent_section_id: Optional[int]  # None si es sección de nivel superior
    section_number: int
    title: Optional[str]
    heading_level: int  # 2=H2, 3=H3, 4=H4
    start_char: int
    end_char: int
    created_at: Optional[str] = None
    # Campo calculado para hijos (no persistido)
    subsections: list["SectionData"] = None

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "parent_section_id": self.parent_section_id,
            "section_number": self.section_number,
            "title": self.title or f"Sección {self.section_number}",
            "heading_level": self.heading_level,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "created_at": self.created_at,
            "subsections": [s.to_dict() for s in self.subsections],
        }

    @classmethod
    def from_row(cls, row) -> "SectionData":
        """Crea desde una fila de SQLite."""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            chapter_id=row["chapter_id"],
            parent_section_id=row["parent_section_id"],
            section_number=row["section_number"],
            title=row["title"],
            heading_level=row["heading_level"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            created_at=row["created_at"],
        )


class SectionRepository:
    """
    Repositorio para gestionar secciones en la base de datos.

    Las secciones son subdivisiones dentro de capítulos (H2, H3, H4).
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Inicializa el repositorio.

        Args:
            db: Instancia de Database. Si es None, usa singleton.
        """
        self.db = db or get_database()

    def create(self, section: SectionData) -> SectionData:
        """
        Crea una nueva sección.

        Args:
            section: Datos de la sección a crear

        Returns:
            Sección creada con ID asignado
        """
        now = datetime.now().isoformat()

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sections (
                    project_id, chapter_id, parent_section_id, section_number,
                    title, heading_level, start_char, end_char, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    section.project_id,
                    section.chapter_id,
                    section.parent_section_id,
                    section.section_number,
                    section.title,
                    section.heading_level,
                    section.start_char,
                    section.end_char,
                    now,
                ),
            )
            section.id = cursor.lastrowid
            section.created_at = now

        logger.debug(f"Creada sección {section.section_number} para capítulo {section.chapter_id}")
        return section

    def create_many(self, sections: list[SectionData]) -> list[SectionData]:
        """
        Crea múltiples secciones en una transacción.

        Args:
            sections: Lista de secciones a crear

        Returns:
            Lista de secciones creadas con IDs asignados
        """
        if not sections:
            return []

        now = datetime.now().isoformat()
        created = []

        with self.db.transaction() as conn:
            for section in sections:
                cursor = conn.execute(
                    """
                    INSERT INTO sections (
                        project_id, chapter_id, parent_section_id, section_number,
                        title, heading_level, start_char, end_char, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        section.project_id,
                        section.chapter_id,
                        section.parent_section_id,
                        section.section_number,
                        section.title,
                        section.heading_level,
                        section.start_char,
                        section.end_char,
                        now,
                    ),
                )
                section.id = cursor.lastrowid
                section.created_at = now
                created.append(section)

        logger.info(f"Creadas {len(created)} secciones")
        return created

    def get_by_chapter(self, chapter_id: int) -> list[SectionData]:
        """
        Obtiene todas las secciones de un capítulo ordenadas por posición.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Lista de secciones ordenadas (flat, sin jerarquía)
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM sections
            WHERE chapter_id = ?
            ORDER BY start_char ASC
            """,
            (chapter_id,)
        )
        return [SectionData.from_row(row) for row in rows]

    def get_by_chapter_hierarchical(self, chapter_id: int) -> list[SectionData]:
        """
        Obtiene secciones de un capítulo organizadas jerárquicamente.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Lista de secciones de nivel superior con subsections pobladas
        """
        all_sections = self.get_by_chapter(chapter_id)

        # Crear mapa id -> sección
        section_map = {s.id: s for s in all_sections}

        # Organizar en árbol
        top_level = []
        for section in all_sections:
            if section.parent_section_id is None:
                top_level.append(section)
            else:
                parent = section_map.get(section.parent_section_id)
                if parent:
                    parent.subsections.append(section)

        return top_level

    def get_by_project(self, project_id: int) -> list[SectionData]:
        """
        Obtiene todas las secciones de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de todas las secciones ordenadas por capítulo y posición
        """
        rows = self.db.fetchall(
            """
            SELECT * FROM sections
            WHERE project_id = ?
            ORDER BY chapter_id ASC, start_char ASC
            """,
            (project_id,)
        )
        return [SectionData.from_row(row) for row in rows]

    def delete_by_project(self, project_id: int) -> int:
        """
        Elimina todas las secciones de un proyecto.

        Args:
            project_id: ID del proyecto

        Returns:
            Número de secciones eliminadas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sections WHERE project_id = ?",
                (project_id,)
            )
            count = cursor.rowcount

        logger.info(f"Eliminadas {count} secciones del proyecto {project_id}")
        return count

    def delete_by_chapter(self, chapter_id: int) -> int:
        """
        Elimina todas las secciones de un capítulo.

        Args:
            chapter_id: ID del capítulo

        Returns:
            Número de secciones eliminadas
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sections WHERE chapter_id = ?",
                (chapter_id,)
            )
            count = cursor.rowcount

        logger.debug(f"Eliminadas {count} secciones del capítulo {chapter_id}")
        return count


def get_section_repository(db: Optional[Database] = None) -> SectionRepository:
    """Obtiene una instancia del repositorio de secciones."""
    return SectionRepository(db)


# =============================================================================
# Computación de métricas de enriquecimiento
# =============================================================================

# Palabras por minuto de lectura (media en español)
_WPM_READING = 200

# Patrones para detección de diálogo
import re
_DIALOGUE_PATTERN = re.compile(
    r'(?:'
    r'[—–]\s*.+?(?=[—–\n]|$)'  # Raya o semi-raya seguida de texto
    r'|'
    r'"[^"]*"'  # Comillas dobles
    r'|'
    r'«[^»]*»'  # Comillas angulares
    r')',
    re.MULTILINE,
)

# Patrones para cambio de escena
_SCENE_BREAK_PATTERNS = [
    re.compile(r'^\s*\*\s*\*\s*\*\s*$', re.MULTILINE),  # ***
    re.compile(r'^\s*#\s*$', re.MULTILINE),  # Markdown scene break
    re.compile(r'^\s*[-–—]{3,}\s*$', re.MULTILINE),  # ---
    re.compile(r'\n\s*\n\s*\n', re.MULTILINE),  # Triple newline
]


def compute_chapter_metrics(content: str, entity_names: Optional[list[str]] = None) -> dict:
    """
    Computa métricas de enriquecimiento para un capítulo.

    Análisis ligero basado en patrones (sin NLP ni LLM) para ser rápido
    y ejecutable durante el pipeline de análisis.

    Args:
        content: Texto del capítulo
        entity_names: Nombres de entidades conocidas en este capítulo (opcional)

    Returns:
        Diccionario con métricas: dialogue_ratio, avg_sentence_length,
        scene_count, characters_present_count, dominant_tone, tone_intensity,
        reading_time_minutes
    """
    if not content or not content.strip():
        return {}

    metrics: dict = {}
    words = content.split()
    word_count = len(words)

    if word_count == 0:
        return {}

    # --- Tiempo de lectura ---
    metrics["reading_time_minutes"] = max(1, round(word_count / _WPM_READING))

    # --- Ratio de diálogo ---
    dialogue_chars = sum(len(m.group()) for m in _DIALOGUE_PATTERN.finditer(content))
    total_chars = len(content.strip())
    if total_chars > 0:
        metrics["dialogue_ratio"] = round(dialogue_chars / total_chars, 3)

    # --- Longitud media de oración ---
    # Aproximación rápida: dividir por puntos finales (. ! ?)
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        total_words_in_sentences = sum(len(s.split()) for s in sentences)
        metrics["avg_sentence_length"] = round(total_words_in_sentences / len(sentences), 1)

    # --- Conteo de escenas ---
    scene_breaks = 0
    for pattern in _SCENE_BREAK_PATTERNS:
        scene_breaks += len(pattern.findall(content))
    metrics["scene_count"] = scene_breaks + 1  # Al menos 1 escena

    # --- Personajes presentes ---
    if entity_names:
        present = sum(1 for name in entity_names if name in content)
        metrics["characters_present_count"] = present

    # --- Tono dominante (heurística básica) ---
    _compute_tone_metrics(content, metrics)

    return metrics


def _compute_tone_metrics(content: str, metrics: dict) -> None:
    """Computa tono dominante e intensidad con heurísticas léxicas."""
    content_lower = content.lower()

    # Palabras de tensión/conflicto
    tension_words = {
        "muerte", "matar", "sangre", "gritó", "grito", "golpe", "pelea",
        "amenaza", "peligro", "miedo", "terror", "huir", "arma", "violencia",
        "guerra", "enemigo", "odio", "destruir", "herida", "dolor", "trampa",
    }
    # Palabras positivas
    positive_words = {
        "amor", "feliz", "alegría", "risa", "sonrisa", "abrazo", "beso",
        "esperanza", "paz", "tranquilo", "amable", "cariño", "ternura",
        "amistad", "celebrar", "fiesta", "victoria", "triunfo",
    }
    # Palabras melancólicas
    melancholy_words = {
        "triste", "tristeza", "llorar", "lágrima", "soledad", "nostalgia",
        "melancolía", "vacío", "ausencia", "pérdida", "recuerdo", "añoranza",
        "abandono", "silencio", "olvido",
    }

    words = content_lower.split()
    word_set = set(words)

    tension_count = len(word_set & tension_words)
    positive_count = len(word_set & positive_words)
    melancholy_count = len(word_set & melancholy_words)

    total_signal = tension_count + positive_count + melancholy_count
    if total_signal == 0:
        metrics["dominant_tone"] = "neutral"
        metrics["tone_intensity"] = 0.3
        return

    if tension_count > positive_count and tension_count > melancholy_count:
        metrics["dominant_tone"] = "tense"
        metrics["tone_intensity"] = round(min(1.0, tension_count / 5), 2)
    elif positive_count > tension_count and positive_count > melancholy_count:
        metrics["dominant_tone"] = "positive"
        metrics["tone_intensity"] = round(min(1.0, positive_count / 5), 2)
    elif melancholy_count > 0:
        metrics["dominant_tone"] = "melancholic"
        metrics["tone_intensity"] = round(min(1.0, melancholy_count / 5), 2)
    else:
        metrics["dominant_tone"] = "neutral"
        metrics["tone_intensity"] = 0.3
