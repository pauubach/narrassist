"""
Módulo de gestión de escenas y etiquetado.

Proporciona:
- Persistencia de escenas detectadas
- Sistema de etiquetas predefinidas (tipo, tono, ubicación)
- Sistema de etiquetas personalizadas del usuario
- Consultas y filtrado de escenas por etiquetas

Nota: No todos los manuscritos tienen escenas (ej: libros de cocina,
autoayuda, ensayos). El sistema detecta automáticamente si el manuscrito
tiene estructura de escenas y solo activa esta funcionalidad cuando es
relevante.
"""

from .models import (
    Scene,
    SceneTag,
    SceneCustomTag,
    SceneType,
    SceneTone,
    SceneWithTags,
)
from .service import SceneService
from .repository import SceneRepository

__all__ = [
    # Models
    "Scene",
    "SceneTag",
    "SceneCustomTag",
    "SceneType",
    "SceneTone",
    "SceneWithTags",
    # Service
    "SceneService",
    # Repository
    "SceneRepository",
]
