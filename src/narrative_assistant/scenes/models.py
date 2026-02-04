"""
Modelos de datos para escenas y etiquetas.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SceneType(str, Enum):
    """Tipos de escena predefinidos."""

    ACTION = "action"  # Acción, movimiento, eventos
    DIALOGUE = "dialogue"  # Conversación predominante
    EXPOSITION = "exposition"  # Descripción, worldbuilding
    INTROSPECTION = "introspection"  # Pensamientos, reflexiones internas
    FLASHBACK = "flashback"  # Recuerdo, escena del pasado
    DREAM = "dream"  # Sueño, visión
    TRANSITION = "transition"  # Escena de transición
    MIXED = "mixed"  # Combinación de tipos


class SceneTone(str, Enum):
    """Tonos emocionales predefinidos."""

    TENSE = "tense"  # Tenso, suspense
    CALM = "calm"  # Calmo, tranquilo
    HAPPY = "happy"  # Alegre, positivo
    SAD = "sad"  # Triste, melancólico
    ROMANTIC = "romantic"  # Romántico
    MYSTERIOUS = "mysterious"  # Misterioso
    OMINOUS = "ominous"  # Ominoso, presagio
    HOPEFUL = "hopeful"  # Esperanzador
    NOSTALGIC = "nostalgic"  # Nostálgico
    NEUTRAL = "neutral"  # Neutro


@dataclass
class Scene:
    """
    Escena dentro de un capítulo.

    Representa una unidad narrativa continua, detectada automáticamente
    por separadores visuales (* * *, ---, etc.) o cambios de escenario.
    """

    id: int
    project_id: int
    chapter_id: int
    scene_number: int  # 1-indexed dentro del capítulo
    start_char: int
    end_char: int
    separator_type: str | None = None  # asterisk, dash, hash, blank_lines, none
    word_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def char_count(self) -> int:
        """Número de caracteres en la escena."""
        return self.end_char - self.start_char

    def get_text(self, full_text: str) -> str:
        """Extrae el texto de la escena del documento completo."""
        return full_text[self.start_char : self.end_char]


@dataclass
class SceneTag:
    """
    Etiquetas predefinidas de una escena.

    Cada escena tiene como máximo un registro de tags predefinidos
    que incluye tipo, tono, ubicación y participantes.
    """

    id: int
    scene_id: int
    scene_type: SceneType | None = None
    tone: SceneTone | None = None
    location_entity_id: int | None = None
    participant_ids: list[int] = field(default_factory=list)
    summary: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class SceneCustomTag:
    """
    Etiqueta personalizada asignada por el usuario.

    Una escena puede tener múltiples etiquetas personalizadas.
    """

    id: int
    scene_id: int
    tag_name: str
    tag_color: str | None = None  # Hex color: #FF5733
    created_at: datetime | None = None


@dataclass
class CustomTagCatalog:
    """
    Catálogo de etiquetas personalizadas del proyecto.

    Permite reutilizar etiquetas y mantener consistencia.
    """

    id: int
    project_id: int
    tag_name: str
    tag_color: str | None = None
    usage_count: int = 0
    created_at: datetime | None = None


@dataclass
class SceneWithTags:
    """
    Escena con todas sus etiquetas (para API responses).
    """

    scene: Scene
    tags: SceneTag | None = None
    custom_tags: list[SceneCustomTag] = field(default_factory=list)

    # Datos adicionales para UI
    chapter_number: int | None = None
    chapter_title: str | None = None
    location_name: str | None = None  # Nombre de la ubicación (de entity)
    participant_names: list[str] = field(default_factory=list)  # Nombres de participantes
    excerpt: str = ""  # Primeras líneas del texto
