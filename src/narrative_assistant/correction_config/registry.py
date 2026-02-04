"""
Registro de configuraciones por tipo y subtipo.

Define los valores por defecto para cada tipo de documento
y los overrides específicos de cada subtipo.
"""

from copy import deepcopy
from typing import Any

from .models import (
    CorrectionConfig,
    DashType,
    InheritanceSource,
    MarkerDetectionMode,
    MarkerPreset,
    QuoteType,
)

# =============================================================================
# Presets de Marcadores de Diálogo
# =============================================================================

MARKER_PRESETS = {
    MarkerPreset.SPANISH_TRADITIONAL: {
        "detection_mode": MarkerDetectionMode.PRESET.value,
        "preset": MarkerPreset.SPANISH_TRADITIONAL.value,
        "spoken_dialogue_dash": DashType.EM_DASH.value,
        "spoken_dialogue_quote": QuoteType.NONE.value,
        "thoughts_quote": QuoteType.ANGULAR.value,
        "thoughts_use_italics": True,
        "nested_dialogue_quote": QuoteType.DOUBLE.value,
        "textual_quote": QuoteType.ANGULAR.value,
    },
    MarkerPreset.ANGLO_SAXON: {
        "detection_mode": MarkerDetectionMode.PRESET.value,
        "preset": MarkerPreset.ANGLO_SAXON.value,
        "spoken_dialogue_dash": DashType.NONE.value,
        "spoken_dialogue_quote": QuoteType.DOUBLE.value,
        "thoughts_quote": QuoteType.SINGLE.value,
        "thoughts_use_italics": True,
        "nested_dialogue_quote": QuoteType.SINGLE.value,
        "textual_quote": QuoteType.DOUBLE.value,
    },
    MarkerPreset.SPANISH_QUOTES: {
        "detection_mode": MarkerDetectionMode.PRESET.value,
        "preset": MarkerPreset.SPANISH_QUOTES.value,
        "spoken_dialogue_dash": DashType.NONE.value,
        "spoken_dialogue_quote": QuoteType.ANGULAR.value,
        "thoughts_quote": QuoteType.DOUBLE.value,
        "thoughts_use_italics": True,
        "nested_dialogue_quote": QuoteType.SINGLE.value,
        "textual_quote": QuoteType.ANGULAR.value,
    },
    MarkerPreset.DETECT: {
        "detection_mode": MarkerDetectionMode.AUTO.value,
        "preset": MarkerPreset.DETECT.value,
        # Defaults que se usarán si la detección falla
        "spoken_dialogue_dash": DashType.EM_DASH.value,
        "spoken_dialogue_quote": QuoteType.NONE.value,
        "thoughts_quote": QuoteType.ANGULAR.value,
        "thoughts_use_italics": True,
        "nested_dialogue_quote": QuoteType.DOUBLE.value,
        "textual_quote": QuoteType.ANGULAR.value,
        # Alertar inconsistencias respecto a lo detectado
        "flag_inconsistent_markers": True,
    },
}


def get_preset_config(preset: MarkerPreset) -> dict:
    """Obtiene la configuración de diálogo para un preset."""
    return MARKER_PRESETS.get(preset, MARKER_PRESETS[MarkerPreset.SPANISH_TRADITIONAL])


# =============================================================================
# Registro de Tipos
# =============================================================================

TYPES_REGISTRY = {
    "FIC": {
        "name": "Ficción",
        "description": "Novela, relatos, ciencia ficción, fantasía, romance, thriller...",
        "icon": "pi-book",
        "color": "#6366f1",
        "config": {
            "dialog": {
                "enabled": True,
                "analyze_dialog_tags": True,
                "flag_inconsistent_markers": True,
                **MARKER_PRESETS[MarkerPreset.SPANISH_TRADITIONAL],
            },
            "repetition": {"tolerance": "medium", "proximity_window_chars": 150},
            "sentence": {"max_length_words": None, "recommended_length_words": 25},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "relationships_enabled": True,
                "behavior_consistency_enabled": True,
                "scenes_enabled": True,
            },
            "readability": {"enabled": False},
        },
    },
    "MEM": {
        "name": "Memorias",
        "description": "Autobiografía, memorias personales, diarios",
        "icon": "pi-heart",
        "color": "#ec4899",
        "config": {
            "dialog": {"enabled": True, "analyze_dialog_tags": False},
            "repetition": {"tolerance": "medium"},
            "sentence": {"max_length_words": None},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "relationships_enabled": True,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "BIO": {
        "name": "Biografía",
        "description": "Biografías de terceros, perfiles, semblanzas",
        "icon": "pi-user",
        "color": "#8b5cf6",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {"tolerance": "medium"},
            "sentence": {"max_length_words": None},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "relationships_enabled": True,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "CEL": {
        "name": "Famosos/Influencers",
        "description": "Libros de celebridades, youtubers, deportistas...",
        "icon": "pi-star",
        "color": "#f59e0b",
        "config": {
            "dialog": {"enabled": True, "analyze_dialog_tags": False},
            "repetition": {"tolerance": "high"},  # Más tolerante
            "sentence": {"max_length_words": None},
            "style": {"enabled": True, "analyze_register": False},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "DIV": {
        "name": "Divulgación",
        "description": "Divulgación científica, histórica, cultural",
        "icon": "pi-globe",
        "color": "#0ea5e9",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {"tolerance": "high"},  # Repetición de términos es normal
            "sentence": {"max_length_words": None},
            "style": {"enabled": True, "analyze_emotions": False},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "ENS": {
        "name": "Ensayo",
        "description": "Ensayo académico, literario, filosófico",
        "icon": "pi-file-edit",
        "color": "#64748b",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {"tolerance": "high"},
            "sentence": {"max_length_words": None},
            "style": {"enabled": True, "analyze_emotions": False},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "AUT": {
        "name": "Autoayuda",
        "description": "Desarrollo personal, coaching, bienestar",
        "icon": "pi-sparkles",
        "color": "#22c55e",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {"tolerance": "high"},  # Repetición intencional
            "sentence": {"max_length_words": 30},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "TEC": {
        "name": "Manual técnico",
        "description": "Documentación técnica, manuales de software/hardware",
        "icon": "pi-cog",
        "color": "#71717a",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {"tolerance": "very_high"},  # Terminología repetida es normal
            "sentence": {"max_length_words": 25, "analyze_complexity": True},
            "style": {"enabled": False},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "PRA": {
        "name": "Libro práctico",
        "description": "Cocina, jardinería, manualidades, guías de viaje",
        "icon": "pi-wrench",
        "color": "#f97316",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {"tolerance": "very_high"},
            "sentence": {"max_length_words": 20},
            "style": {"enabled": False},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "behavior_consistency_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "GRA": {
        "name": "Novela gráfica",
        "description": "Cómic, manga, novela gráfica, libro ilustrado",
        "icon": "pi-image",
        "color": "#a855f7",
        "config": {
            "dialog": {"enabled": True, "analyze_dialog_tags": False},
            "repetition": {"tolerance": "high"},  # Poco texto
            "sentence": {"max_length_words": 15},  # Bocadillos cortos
            "style": {"enabled": False},
            "structure": {
                "timeline_enabled": True,
                "relationships_enabled": True,
                "behavior_consistency_enabled": True,
                "scenes_enabled": False,
            },
            "readability": {"enabled": False},
        },
    },
    "INF": {
        "name": "Infantil/Juvenil",
        "description": "Literatura para niños y adolescentes",
        "icon": "pi-face-smile",
        "color": "#14b8a6",
        "config": {
            "dialog": {"enabled": True, "analyze_dialog_tags": True},
            "repetition": {"tolerance": "high"},  # Base, se ajusta por subtipo
            "sentence": {"max_length_words": 20},  # Base, se ajusta por subtipo
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "relationships_enabled": True,
                "behavior_consistency_enabled": True,
                "scenes_enabled": True,
            },
            "readability": {"enabled": True},
        },
    },
    "DRA": {
        "name": "Teatro/Guion",
        "description": "Obras de teatro, guiones de cine/TV",
        "icon": "pi-video",
        "color": "#ef4444",
        "config": {
            "dialog": {
                "enabled": True,
                "analyze_dialog_tags": False,  # Formato diferente
                "dialog_markers": [],  # No usa marcadores tradicionales
            },
            "repetition": {"tolerance": "medium"},
            "sentence": {"max_length_words": None},
            "style": {"enabled": False},
            "structure": {
                "timeline_enabled": True,
                "relationships_enabled": True,
                "behavior_consistency_enabled": True,
                "scenes_enabled": True,
            },
            "readability": {"enabled": False},
        },
    },
}


# =============================================================================
# Registro de Subtipos con Overrides
# =============================================================================

SUBTYPES_REGISTRY = {
    # =========================================================================
    # FICCIÓN
    # =========================================================================
    "FIC_LIT": {
        "name": "Novela literaria",
        "parent": "FIC",
        "config": {
            "repetition": {"tolerance": "low"},  # Más exigente
            "sentence": {"recommended_length_words": 30},
        },
    },
    "FIC_GEN": {
        "name": "Novela de género",
        "parent": "FIC",
        "config": {},  # Hereda todo del tipo
    },
    "FIC_HIS": {
        "name": "Novela histórica",
        "parent": "FIC",
        "config": {
            "repetition": {"tolerance": "medium"},  # Términos de época
        },
    },
    "FIC_COR": {
        "name": "Relato/Cuento",
        "parent": "FIC",
        "config": {
            "structure": {"scenes_enabled": False},
        },
    },
    "FIC_MIC": {
        "name": "Microrrelatos",
        "parent": "FIC",
        "config": {
            "repetition": {"tolerance": "low"},
            "sentence": {"max_length_words": 20},
            "structure": {
                "timeline_enabled": False,
                "scenes_enabled": False,
            },
        },
    },
    # =========================================================================
    # MEMORIAS
    # =========================================================================
    "MEM_AUT": {
        "name": "Autobiografía completa",
        "parent": "MEM",
        "config": {
            "structure": {"timeline_enabled": True},
        },
    },
    "MEM_PAR": {
        "name": "Memorias parciales",
        "parent": "MEM",
        "config": {},
    },
    "MEM_DIA": {
        "name": "Diario/Epistolario",
        "parent": "MEM",
        "config": {
            "structure": {"timeline_enabled": True},
            "style": {"analyze_register": False},  # Variación natural
        },
    },
    # =========================================================================
    # BIOGRAFÍA
    # =========================================================================
    "BIO_AUT": {
        "name": "Biografía autorizada",
        "parent": "BIO",
        "config": {},
    },
    "BIO_HIS": {
        "name": "Biografía histórica",
        "parent": "BIO",
        "config": {
            "repetition": {"tolerance": "high"},  # Términos históricos
        },
    },
    "BIO_COL": {
        "name": "Biografía colectiva",
        "parent": "BIO",
        "config": {},
    },
    # =========================================================================
    # FAMOSOS
    # =========================================================================
    "CEL_MEM": {
        "name": "Memorias de famoso",
        "parent": "CEL",
        "config": {},
    },
    "CEL_CON": {
        "name": "Consejos/Método",
        "parent": "CEL",
        "config": {
            "repetition": {"tolerance": "very_high"},  # Énfasis intencional
        },
    },
    "CEL_ENT": {
        "name": "Entrevistas/Anécdotas",
        "parent": "CEL",
        "config": {
            "dialog": {"enabled": True},
        },
    },
    # =========================================================================
    # DIVULGACIÓN
    # =========================================================================
    "DIV_CIE": {
        "name": "Divulgación científica",
        "parent": "DIV",
        "config": {},
    },
    "DIV_HIS": {
        "name": "Divulgación histórica",
        "parent": "DIV",
        "config": {
            "structure": {"timeline_enabled": True},
        },
    },
    "DIV_CUL": {
        "name": "Divulgación cultural",
        "parent": "DIV",
        "config": {},
    },
    # =========================================================================
    # ENSAYO
    # =========================================================================
    "ENS_ACA": {
        "name": "Ensayo académico",
        "parent": "ENS",
        "config": {
            "repetition": {"tolerance": "very_high"},  # Terminología
        },
    },
    "ENS_LIT": {
        "name": "Ensayo literario",
        "parent": "ENS",
        "config": {
            "style": {"enabled": True},
        },
    },
    "ENS_FIL": {
        "name": "Ensayo filosófico",
        "parent": "ENS",
        "config": {},
    },
    "ENS_POL": {
        "name": "Ensayo político/social",
        "parent": "ENS",
        "config": {},
    },
    # =========================================================================
    # AUTOAYUDA
    # =========================================================================
    "AUT_DES": {
        "name": "Desarrollo personal",
        "parent": "AUT",
        "config": {},
    },
    "AUT_PRO": {
        "name": "Productividad/Negocios",
        "parent": "AUT",
        "config": {},
    },
    "AUT_BIE": {
        "name": "Bienestar/Salud",
        "parent": "AUT",
        "config": {},
    },
    "AUT_REL": {
        "name": "Relaciones/Familia",
        "parent": "AUT",
        "config": {},
    },
    # =========================================================================
    # TÉCNICO
    # =========================================================================
    "TEC_SOF": {
        "name": "Manual de software",
        "parent": "TEC",
        "config": {},
    },
    "TEC_HAR": {
        "name": "Manual de hardware",
        "parent": "TEC",
        "config": {},
    },
    "TEC_PRO": {
        "name": "Manual de procedimientos",
        "parent": "TEC",
        "config": {},
    },
    # =========================================================================
    # PRÁCTICO
    # =========================================================================
    "PRA_COC": {
        "name": "Libro de cocina",
        "parent": "PRA",
        "config": {},
    },
    "PRA_JAR": {
        "name": "Jardinería",
        "parent": "PRA",
        "config": {},
    },
    "PRA_MAN": {
        "name": "Manualidades/DIY",
        "parent": "PRA",
        "config": {},
    },
    "PRA_VIA": {
        "name": "Guía de viajes",
        "parent": "PRA",
        "config": {},
    },
    "PRA_DEP": {
        "name": "Deportes/Fitness",
        "parent": "PRA",
        "config": {},
    },
    # =========================================================================
    # GRÁFICO
    # =========================================================================
    "GRA_COM": {
        "name": "Cómic occidental",
        "parent": "GRA",
        "config": {},
    },
    "GRA_MAN": {
        "name": "Manga",
        "parent": "GRA",
        "config": {
            "sentence": {"max_length_words": 20},  # Más texto que cómic
        },
    },
    "GRA_NOV": {
        "name": "Novela gráfica",
        "parent": "GRA",
        "config": {
            "sentence": {"max_length_words": 25},
        },
    },
    "GRA_ILU": {
        "name": "Libro ilustrado",
        "parent": "GRA",
        "config": {},
    },
    # =========================================================================
    # INFANTIL/JUVENIL - Ajustes críticos por edad
    # =========================================================================
    "INF_CAR": {
        "name": "Cartoné (0-3 años)",
        "parent": "INF",
        "config": {
            "dialog": {"enabled": False},
            "repetition": {
                "tolerance": "very_high",
                "flag_lack_of_repetition": True,  # ¡Avisar si NO hay repetición!
            },
            "sentence": {"max_length_words": 5},
            "style": {"enabled": False},
            "structure": {
                "timeline_enabled": False,
                "relationships_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {
                "enabled": True,
                "target_age_min": 0,
                "target_age_max": 3,
                "max_vocabulary_size": 200,
            },
        },
    },
    "INF_ALB": {
        "name": "Álbum ilustrado (3-5 años)",
        "parent": "INF",
        "config": {
            "dialog": {"enabled": True, "analyze_dialog_tags": False},
            "repetition": {
                "tolerance": "very_high",
                "flag_lack_of_repetition": True,
            },
            "sentence": {"max_length_words": 8},
            "style": {"enabled": False},
            "structure": {
                "timeline_enabled": False,
                "scenes_enabled": False,
            },
            "readability": {
                "enabled": True,
                "target_age_min": 3,
                "target_age_max": 5,
                "max_vocabulary_size": 500,
            },
        },
    },
    "INF_PRI": {
        "name": "Primeras lecturas (5-8 años)",
        "parent": "INF",
        "config": {
            "dialog": {"enabled": True},
            "repetition": {"tolerance": "high"},
            "sentence": {"max_length_words": 12},
            "style": {"enabled": True, "analyze_sticky_sentences": False},
            "structure": {
                "timeline_enabled": True,
                "scenes_enabled": False,
            },
            "readability": {
                "enabled": True,
                "target_age_min": 5,
                "target_age_max": 8,
                "max_vocabulary_size": 2000,
            },
        },
    },
    "INF_CAP": {
        "name": "Novela por capítulos (6-10 años)",
        "parent": "INF",
        "config": {
            "dialog": {"enabled": True},
            "repetition": {"tolerance": "medium"},
            "sentence": {"max_length_words": 15},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "scenes_enabled": True,
            },
            "readability": {
                "enabled": True,
                "target_age_min": 6,
                "target_age_max": 10,
                "max_vocabulary_size": 5000,
            },
        },
    },
    "INF_MID": {
        "name": "Middle grade (8-12 años)",
        "parent": "INF",
        "config": {
            "dialog": {"enabled": True},
            "repetition": {"tolerance": "medium"},
            "sentence": {"max_length_words": 20},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "scenes_enabled": True,
            },
            "readability": {
                "enabled": True,
                "target_age_min": 8,
                "target_age_max": 12,
            },
        },
    },
    "INF_YA": {
        "name": "Young Adult (12+ años)",
        "parent": "INF",
        "config": {
            # Casi como ficción adulta
            "dialog": {"enabled": True, "analyze_dialog_tags": True},
            "repetition": {"tolerance": "medium"},
            "sentence": {"max_length_words": 25},
            "style": {"enabled": True},
            "structure": {
                "timeline_enabled": True,
                "scenes_enabled": True,
                "behavior_consistency_enabled": True,
            },
            "readability": {
                "enabled": True,
                "target_age_min": 12,
                "target_age_max": 18,
            },
        },
    },
    # =========================================================================
    # TEATRO/GUION
    # =========================================================================
    "DRA_TEA": {
        "name": "Teatro",
        "parent": "DRA",
        "config": {},
    },
    "DRA_GUI": {
        "name": "Guion de cine/TV",
        "parent": "DRA",
        "config": {},
    },
    "DRA_RAD": {
        "name": "Guion de radio/podcast",
        "parent": "DRA",
        "config": {
            "dialog": {"enabled": True},  # Todo es diálogo
        },
    },
}


# =============================================================================
# Funciones de acceso
# =============================================================================


def get_type_defaults(type_code: str) -> dict:
    """
    Obtiene la configuración por defecto de un tipo.

    Args:
        type_code: Código del tipo (FIC, MEM, etc.)

    Returns:
        Dict con la configuración del tipo
    """
    type_info = TYPES_REGISTRY.get(type_code.upper())
    if not type_info:
        # Default a ficción si no se encuentra
        type_info = TYPES_REGISTRY["FIC"]
    return type_info.get("config", {})


def get_subtype_overrides(subtype_code: str) -> dict:
    """
    Obtiene los overrides específicos de un subtipo.

    Args:
        subtype_code: Código del subtipo (FIC_LIT, INF_MID, etc.)

    Returns:
        Dict con los overrides del subtipo
    """
    subtype_info = SUBTYPES_REGISTRY.get(subtype_code.upper())
    if not subtype_info:
        return {}
    return subtype_info.get("config", {})


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Merge profundo de dos diccionarios.

    Los valores de override sobreescriben los de base.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _apply_config_to_dataclass(
    config_obj: Any,
    config_dict: dict,
    category: str,
    source: InheritanceSource,
    source_name: str,
    correction_config: CorrectionConfig,
):
    """
    Aplica un diccionario de configuración a un dataclass.

    También registra la información de herencia.
    """
    for key, value in config_dict.items():
        if hasattr(config_obj, key):
            setattr(config_obj, key, value)
            correction_config.set_inheritance_info(category, key, source, source_name)


def _load_user_overrides(type_code: str, subtype_code: str | None = None) -> dict | None:
    """
    Carga overrides de usuario desde la base de datos.

    Args:
        type_code: Código del tipo.
        subtype_code: Código del subtipo (opcional).

    Returns:
        Dict con los overrides o None si no hay.
    """
    try:
        from .defaults_repository import get_defaults_repository

        repo = get_defaults_repository()
        result = repo.get_override(type_code, subtype_code)
        return result["overrides"] if result else None
    except Exception:
        # Si hay error (ej: tabla no existe todavía), continuar sin overrides
        return None


def _apply_section_overrides(
    config: "CorrectionConfig", overrides: dict, source: InheritanceSource, source_name: str
) -> None:
    """
    Aplica overrides a todas las secciones de configuración.

    Args:
        config: Configuración a modificar.
        overrides: Dict con los overrides por sección.
        source: Fuente del override.
        source_name: Nombre de la fuente para mostrar en UI.
    """
    sections = ["dialog", "repetition", "sentence", "style", "structure", "readability"]
    section_attrs = {
        "dialog": config.dialog,
        "repetition": config.repetition,
        "sentence": config.sentence,
        "style": config.style,
        "structure": config.structure,
        "readability": config.readability,
    }

    for section in sections:
        if section in overrides:
            _apply_config_to_dataclass(
                section_attrs[section], overrides[section], section, source, source_name, config
            )


def get_correction_config(
    type_code: str, subtype_code: str | None = None, custom_overrides: dict | None = None
) -> CorrectionConfig:
    """
    Construye una configuración de corrección con herencia aplicada.

    Orden de aplicación:
    1. Defaults globales
    2. Configuración del tipo
    3. Configuración del subtipo (si existe)
    4. Overrides personalizados (si existen)

    Args:
        type_code: Código del tipo (FIC, MEM, INF, etc.)
        subtype_code: Código del subtipo opcional (INF_MID, FIC_LIT, etc.)
        custom_overrides: Dict con overrides personalizados del usuario

    Returns:
        CorrectionConfig completo con herencia aplicada

    Example:
        >>> config = get_correction_config("INF", "INF_MID")
        >>> config.sentence.max_length_words
        20
        >>> config.readability.target_age_min
        8
    """
    type_code = type_code.upper()
    subtype_code = subtype_code.upper() if subtype_code else None

    # Obtener info del tipo
    type_info = TYPES_REGISTRY.get(type_code, TYPES_REGISTRY["FIC"])
    type_name = type_info.get("name", "Ficción")

    # Obtener info del subtipo
    subtype_info = SUBTYPES_REGISTRY.get(subtype_code) if subtype_code else None
    subtype_name = subtype_info.get("name") if subtype_info else None

    # Crear config base
    config = CorrectionConfig(
        type_code=type_code,
        type_name=type_name,
        subtype_code=subtype_code,
        subtype_name=subtype_name,
    )

    # 1. Aplicar defaults del tipo
    type_config = get_type_defaults(type_code)

    if "dialog" in type_config:
        _apply_config_to_dataclass(
            config.dialog,
            type_config["dialog"],
            "dialog",
            InheritanceSource.TYPE,
            type_name,
            config,
        )
    if "repetition" in type_config:
        _apply_config_to_dataclass(
            config.repetition,
            type_config["repetition"],
            "repetition",
            InheritanceSource.TYPE,
            type_name,
            config,
        )
    if "sentence" in type_config:
        _apply_config_to_dataclass(
            config.sentence,
            type_config["sentence"],
            "sentence",
            InheritanceSource.TYPE,
            type_name,
            config,
        )
    if "style" in type_config:
        _apply_config_to_dataclass(
            config.style, type_config["style"], "style", InheritanceSource.TYPE, type_name, config
        )
    if "structure" in type_config:
        _apply_config_to_dataclass(
            config.structure,
            type_config["structure"],
            "structure",
            InheritanceSource.TYPE,
            type_name,
            config,
        )
    if "readability" in type_config:
        _apply_config_to_dataclass(
            config.readability,
            type_config["readability"],
            "readability",
            InheritanceSource.TYPE,
            type_name,
            config,
        )

    # 1b. Aplicar overrides de usuario para el tipo (si existen)
    user_type_overrides = _load_user_overrides(type_code, None)
    if user_type_overrides:
        _apply_section_overrides(
            config, user_type_overrides, InheritanceSource.TYPE, f"{type_name} (personalizado)"
        )

    # 2. Aplicar overrides del subtipo
    if subtype_code and subtype_info:
        subtype_config = subtype_info.get("config", {})

        if "dialog" in subtype_config:
            _apply_config_to_dataclass(
                config.dialog,
                subtype_config["dialog"],
                "dialog",
                InheritanceSource.SUBTYPE,
                subtype_name,
                config,
            )
        if "repetition" in subtype_config:
            _apply_config_to_dataclass(
                config.repetition,
                subtype_config["repetition"],
                "repetition",
                InheritanceSource.SUBTYPE,
                subtype_name,
                config,
            )
        if "sentence" in subtype_config:
            _apply_config_to_dataclass(
                config.sentence,
                subtype_config["sentence"],
                "sentence",
                InheritanceSource.SUBTYPE,
                subtype_name,
                config,
            )
        if "style" in subtype_config:
            _apply_config_to_dataclass(
                config.style,
                subtype_config["style"],
                "style",
                InheritanceSource.SUBTYPE,
                subtype_name,
                config,
            )
        if "structure" in subtype_config:
            _apply_config_to_dataclass(
                config.structure,
                subtype_config["structure"],
                "structure",
                InheritanceSource.SUBTYPE,
                subtype_name,
                config,
            )
        if "readability" in subtype_config:
            _apply_config_to_dataclass(
                config.readability,
                subtype_config["readability"],
                "readability",
                InheritanceSource.SUBTYPE,
                subtype_name,
                config,
            )

        # 2b. Aplicar overrides de usuario para el subtipo (si existen)
        user_subtype_overrides = _load_user_overrides(type_code, subtype_code)
        if user_subtype_overrides:
            _apply_section_overrides(
                config,
                user_subtype_overrides,
                InheritanceSource.SUBTYPE,
                f"{subtype_name} (personalizado)",
            )

    # 3. Aplicar overrides personalizados
    if custom_overrides:
        if "dialog" in custom_overrides:
            _apply_config_to_dataclass(
                config.dialog,
                custom_overrides["dialog"],
                "dialog",
                InheritanceSource.CUSTOM,
                "Personalizado",
                config,
            )
        if "repetition" in custom_overrides:
            _apply_config_to_dataclass(
                config.repetition,
                custom_overrides["repetition"],
                "repetition",
                InheritanceSource.CUSTOM,
                "Personalizado",
                config,
            )
        if "sentence" in custom_overrides:
            _apply_config_to_dataclass(
                config.sentence,
                custom_overrides["sentence"],
                "sentence",
                InheritanceSource.CUSTOM,
                "Personalizado",
                config,
            )
        if "style" in custom_overrides:
            _apply_config_to_dataclass(
                config.style,
                custom_overrides["style"],
                "style",
                InheritanceSource.CUSTOM,
                "Personalizado",
                config,
            )
        if "structure" in custom_overrides:
            _apply_config_to_dataclass(
                config.structure,
                custom_overrides["structure"],
                "structure",
                InheritanceSource.CUSTOM,
                "Personalizado",
                config,
            )
        if "readability" in custom_overrides:
            _apply_config_to_dataclass(
                config.readability,
                custom_overrides["readability"],
                "readability",
                InheritanceSource.CUSTOM,
                "Personalizado",
                config,
            )

    return config
