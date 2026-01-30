"""
Modelos para el sistema de perfiles de features por tipo de documento.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocumentType(str, Enum):
    """Tipos principales de documento."""
    FICTION = "FIC"           # Ficción narrativa
    MEMOIR = "MEM"            # Memorias y autobiografías
    BIOGRAPHY = "BIO"         # Biografías
    CELEBRITY = "CEL"         # Libros de famosos/influencers
    DIVULGATION = "DIV"       # Divulgación científica/histórica
    ESSAY = "ENS"             # Ensayo académico/literario
    SELF_HELP = "AUT"         # Autoayuda y desarrollo personal
    TECHNICAL = "TEC"         # Manuales técnicos
    PRACTICAL = "PRA"         # Libros prácticos (cocina, DIY, etc.)
    GRAPHIC = "GRA"           # Novela gráfica y cómic
    CHILDREN = "INF"          # Literatura infantil/juvenil
    DRAMA = "DRA"             # Teatro/guion


# Mapeo bidireccional entre códigos cortos (BD) y largos (clasificador/frontend)
_TYPE_CODE_TO_LONG = {
    "FIC": "fiction",
    "MEM": "memoir",
    "BIO": "biography",
    "CEL": "celebrity",
    "DIV": "divulgation",
    "ENS": "essay",
    "AUT": "self_help",
    "TEC": "technical",
    "PRA": "practical",
    "GRA": "graphic",
    "INF": "children",
    "DRA": "drama",
}
_TYPE_LONG_TO_CODE = {v: k for k, v in _TYPE_CODE_TO_LONG.items()}


def normalize_document_type(type_str: str) -> str:
    """
    Normaliza un código de tipo de documento al formato corto (FIC, MEM, etc.)

    Acepta tanto códigos cortos como largos:
    - "FIC" -> "FIC"
    - "fiction" -> "FIC"
    - "FICTION" -> "FIC"

    Args:
        type_str: Código de tipo en cualquier formato

    Returns:
        Código corto normalizado o el original si no se reconoce
    """
    if not type_str:
        return "FIC"  # Default

    upper = type_str.upper()
    lower = type_str.lower()

    # Ya es código corto
    if upper in _TYPE_CODE_TO_LONG:
        return upper

    # Es código largo
    if lower in _TYPE_LONG_TO_CODE:
        return _TYPE_LONG_TO_CODE[lower]

    # Intentar por nombre del enum
    try:
        return DocumentType[upper].value
    except KeyError:
        pass

    return type_str  # No reconocido, devolver original


def type_code_to_long(code: str) -> str:
    """Convierte código corto (FIC) a largo (fiction)."""
    return _TYPE_CODE_TO_LONG.get(code.upper(), code.lower())


def type_long_to_code(long_name: str) -> str:
    """Convierte código largo (fiction) a corto (FIC)."""
    return _TYPE_LONG_TO_CODE.get(long_name.lower(), long_name.upper())


class FeatureAvailability(str, Enum):
    """Niveles de disponibilidad de una feature."""
    ENABLED = "enabled"       # Activa por defecto
    OPTIONAL = "optional"     # Disponible pero desactivada
    DISABLED = "disabled"     # No disponible para este tipo


# Información de tipos de documento
DOCUMENT_TYPES = {
    DocumentType.FICTION: {
        "name": "Ficción narrativa",
        "description": "Novela, relatos, ciencia ficción, fantasía, romance, thriller...",
        "icon": "pi-book",
        "color": "#6366f1",  # Indigo
    },
    DocumentType.MEMOIR: {
        "name": "Memorias",
        "description": "Autobiografía, memorias personales, diarios",
        "icon": "pi-heart",
        "color": "#ec4899",  # Pink
    },
    DocumentType.BIOGRAPHY: {
        "name": "Biografía",
        "description": "Biografías de terceros, perfiles, semblanzas",
        "icon": "pi-user",
        "color": "#8b5cf6",  # Violet
    },
    DocumentType.CELEBRITY: {
        "name": "Famosos/Influencers",
        "description": "Libros de celebridades, youtubers, deportistas...",
        "icon": "pi-star",
        "color": "#f59e0b",  # Amber
    },
    DocumentType.DIVULGATION: {
        "name": "Divulgación",
        "description": "Divulgación científica, histórica, cultural",
        "icon": "pi-globe",
        "color": "#0ea5e9",  # Sky
    },
    DocumentType.ESSAY: {
        "name": "Ensayo",
        "description": "Ensayo académico, literario, filosófico",
        "icon": "pi-file-edit",
        "color": "#64748b",  # Slate
    },
    DocumentType.SELF_HELP: {
        "name": "Autoayuda",
        "description": "Desarrollo personal, coaching, bienestar",
        "icon": "pi-sparkles",
        "color": "#22c55e",  # Green
    },
    DocumentType.TECHNICAL: {
        "name": "Manual técnico",
        "description": "Documentación técnica, manuales de software/hardware",
        "icon": "pi-cog",
        "color": "#71717a",  # Zinc
    },
    DocumentType.PRACTICAL: {
        "name": "Libro práctico",
        "description": "Cocina, jardinería, manualidades, guías de viaje",
        "icon": "pi-wrench",
        "color": "#f97316",  # Orange
    },
    DocumentType.GRAPHIC: {
        "name": "Novela gráfica",
        "description": "Cómic, manga, novela gráfica, libro ilustrado",
        "icon": "pi-image",
        "color": "#a855f7",  # Purple
    },
    DocumentType.CHILDREN: {
        "name": "Infantil/Juvenil",
        "description": "Literatura para niños y adolescentes",
        "icon": "pi-face-smile",
        "color": "#14b8a6",  # Teal
    },
    DocumentType.DRAMA: {
        "name": "Teatro/Guion",
        "description": "Obras de teatro, guiones de cine/TV",
        "icon": "pi-video",
        "color": "#ef4444",  # Red
    },
}

# Subtipos por categoría
DOCUMENT_SUBTYPES = {
    DocumentType.FICTION: [
        {"code": "FIC_LIT", "name": "Novela literaria"},
        {"code": "FIC_GEN", "name": "Novela de género"},
        {"code": "FIC_HIS", "name": "Novela histórica"},
        {"code": "FIC_COR", "name": "Relato/Cuento"},
        {"code": "FIC_MIC", "name": "Microrrelatos"},
    ],
    DocumentType.MEMOIR: [
        {"code": "MEM_AUT", "name": "Autobiografía completa"},
        {"code": "MEM_PAR", "name": "Memorias parciales"},
        {"code": "MEM_DIA", "name": "Diario/Epistolario"},
    ],
    DocumentType.BIOGRAPHY: [
        {"code": "BIO_AUT", "name": "Biografía autorizada"},
        {"code": "BIO_HIS", "name": "Biografía histórica"},
        {"code": "BIO_COL", "name": "Biografía colectiva"},
    ],
    DocumentType.CELEBRITY: [
        {"code": "CEL_MEM", "name": "Memorias de famoso"},
        {"code": "CEL_CON", "name": "Consejos/Método"},
        {"code": "CEL_ENT", "name": "Entrevistas/Anécdotas"},
    ],
    DocumentType.DIVULGATION: [
        {"code": "DIV_CIE", "name": "Divulgación científica"},
        {"code": "DIV_HIS", "name": "Divulgación histórica"},
        {"code": "DIV_CUL", "name": "Divulgación cultural"},
    ],
    DocumentType.ESSAY: [
        {"code": "ENS_ACA", "name": "Ensayo académico"},
        {"code": "ENS_LIT", "name": "Ensayo literario"},
        {"code": "ENS_FIL", "name": "Ensayo filosófico"},
        {"code": "ENS_POL", "name": "Ensayo político/social"},
    ],
    DocumentType.SELF_HELP: [
        {"code": "AUT_DES", "name": "Desarrollo personal"},
        {"code": "AUT_PRO", "name": "Productividad/Negocios"},
        {"code": "AUT_BIE", "name": "Bienestar/Salud"},
        {"code": "AUT_REL", "name": "Relaciones/Familia"},
    ],
    DocumentType.TECHNICAL: [
        {"code": "TEC_SOF", "name": "Manual de software"},
        {"code": "TEC_HAR", "name": "Manual de hardware"},
        {"code": "TEC_PRO", "name": "Manual de procedimientos"},
    ],
    DocumentType.PRACTICAL: [
        {"code": "PRA_COC", "name": "Libro de cocina"},
        {"code": "PRA_JAR", "name": "Jardinería"},
        {"code": "PRA_MAN", "name": "Manualidades/DIY"},
        {"code": "PRA_VIA", "name": "Guía de viajes"},
        {"code": "PRA_DEP", "name": "Deportes/Fitness"},
    ],
    DocumentType.GRAPHIC: [
        {"code": "GRA_COM", "name": "Cómic occidental"},
        {"code": "GRA_MAN", "name": "Manga"},
        {"code": "GRA_NOV", "name": "Novela gráfica"},
        {"code": "GRA_ILU", "name": "Libro ilustrado"},
    ],
    DocumentType.CHILDREN: [
        {"code": "INF_CAR", "name": "Cartoné (0-3 años)"},
        {"code": "INF_ALB", "name": "Álbum ilustrado (3-5 años)"},
        {"code": "INF_PRI", "name": "Primeras lecturas (5-8 años)"},
        {"code": "INF_CAP", "name": "Novela por capítulos (6-10 años)"},
        {"code": "INF_MID", "name": "Middle grade (8-12 años)"},
        {"code": "INF_YA", "name": "Young Adult (12+ años)"},
    ],
    DocumentType.DRAMA: [
        {"code": "DRA_TEA", "name": "Teatro"},
        {"code": "DRA_GUI", "name": "Guion de cine/TV"},
        {"code": "DRA_RAD", "name": "Guion de radio/podcast"},
    ],
}


@dataclass
class FeatureProfile:
    """
    Perfil de features disponibles para un tipo de documento.

    Define qué herramientas de análisis están disponibles
    según el tipo de manuscrito.
    """
    document_type: DocumentType
    document_subtype: Optional[str] = None

    # Features de estructura narrativa
    characters: FeatureAvailability = FeatureAvailability.ENABLED
    relationships: FeatureAvailability = FeatureAvailability.ENABLED
    timeline: FeatureAvailability = FeatureAvailability.ENABLED
    scenes: FeatureAvailability = FeatureAvailability.ENABLED
    pov_focalization: FeatureAvailability = FeatureAvailability.ENABLED

    # Features de estilo
    pacing: FeatureAvailability = FeatureAvailability.ENABLED
    register_analysis: FeatureAvailability = FeatureAvailability.ENABLED
    voice_profiles: FeatureAvailability = FeatureAvailability.ENABLED
    sticky_sentences: FeatureAvailability = FeatureAvailability.ENABLED
    echo_repetitions: FeatureAvailability = FeatureAvailability.ENABLED
    sentence_variation: FeatureAvailability = FeatureAvailability.ENABLED
    emotional_analysis: FeatureAvailability = FeatureAvailability.ENABLED
    age_readability: FeatureAvailability = FeatureAvailability.DISABLED  # Solo para INF
    sensory_report: FeatureAvailability = FeatureAvailability.ENABLED  # Reporte sensorial (5 sentidos)
    sentence_energy: FeatureAvailability = FeatureAvailability.ENABLED  # Energía de oraciones
    narrative_templates: FeatureAvailability = FeatureAvailability.ENABLED  # Plantillas narrativas (diagnóstico)
    narrative_health: FeatureAvailability = FeatureAvailability.ENABLED  # Salud narrativa (12 dimensiones)
    character_archetypes: FeatureAvailability = FeatureAvailability.ENABLED  # Arquetipos Jung/Campbell
    vital_status: FeatureAvailability = FeatureAvailability.ENABLED  # Muertes y reapariciones
    character_location: FeatureAvailability = FeatureAvailability.ENABLED  # Seguimiento de ubicaciones
    chapter_progress: FeatureAvailability = FeatureAvailability.ENABLED  # Resumen de avance por capítulo

    # Features de consistencia
    attribute_consistency: FeatureAvailability = FeatureAvailability.ENABLED
    world_consistency: FeatureAvailability = FeatureAvailability.ENABLED

    # Features técnicos
    glossary: FeatureAvailability = FeatureAvailability.ENABLED
    terminology: FeatureAvailability = FeatureAvailability.ENABLED
    editorial_rules: FeatureAvailability = FeatureAvailability.ENABLED

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "document_type": self.document_type.value,
            "document_subtype": self.document_subtype,
            "type_info": DOCUMENT_TYPES.get(self.document_type, {}),
            "features": {
                # Estructura narrativa
                "characters": self.characters.value,
                "relationships": self.relationships.value,
                "timeline": self.timeline.value,
                "scenes": self.scenes.value,
                "pov_focalization": self.pov_focalization.value,
                # Estilo
                "pacing": self.pacing.value,
                "register_analysis": self.register_analysis.value,
                "voice_profiles": self.voice_profiles.value,
                "sticky_sentences": self.sticky_sentences.value,
                "echo_repetitions": self.echo_repetitions.value,
                "sentence_variation": self.sentence_variation.value,
                "emotional_analysis": self.emotional_analysis.value,
                "age_readability": self.age_readability.value,
                "sensory_report": self.sensory_report.value,
                "sentence_energy": self.sentence_energy.value,
                "narrative_templates": self.narrative_templates.value,
                "narrative_health": self.narrative_health.value,
                "character_archetypes": self.character_archetypes.value,
                "vital_status": self.vital_status.value,
                "character_location": self.character_location.value,
                "chapter_progress": self.chapter_progress.value,
                # Consistencia
                "attribute_consistency": self.attribute_consistency.value,
                "world_consistency": self.world_consistency.value,
                # Técnicos
                "glossary": self.glossary.value,
                "terminology": self.terminology.value,
                "editorial_rules": self.editorial_rules.value,
            }
        }

    def is_enabled(self, feature: str) -> bool:
        """Comprueba si una feature está habilitada."""
        val = getattr(self, feature, None)
        return val == FeatureAvailability.ENABLED if val else False

    def is_available(self, feature: str) -> bool:
        """Comprueba si una feature está disponible (enabled u optional)."""
        val = getattr(self, feature, None)
        return val in (FeatureAvailability.ENABLED, FeatureAvailability.OPTIONAL) if val else False


# Perfiles predefinidos por tipo de documento
# Basados en el análisis con expertos editoriales

def _create_fiction_profile() -> FeatureProfile:
    """Perfil para ficción narrativa - todas las features activadas."""
    return FeatureProfile(
        document_type=DocumentType.FICTION,
    )


def _create_memoir_profile() -> FeatureProfile:
    """Perfil para memorias - similar a ficción pero con matices."""
    return FeatureProfile(
        document_type=DocumentType.MEMOIR,
        scenes=FeatureAvailability.OPTIONAL,  # Menos estructurado que ficción
        voice_profiles=FeatureAvailability.OPTIONAL,  # Voz única del autor
    )


def _create_biography_profile() -> FeatureProfile:
    """Perfil para biografías."""
    return FeatureProfile(
        document_type=DocumentType.BIOGRAPHY,
        pov_focalization=FeatureAvailability.OPTIONAL,  # Típicamente omnisciente
        scenes=FeatureAvailability.OPTIONAL,
        voice_profiles=FeatureAvailability.DISABLED,  # No hay diálogos ficticios
    )


def _create_celebrity_profile() -> FeatureProfile:
    """Perfil para libros de famosos/influencers."""
    return FeatureProfile(
        document_type=DocumentType.CELEBRITY,
        timeline=FeatureAvailability.OPTIONAL,
        scenes=FeatureAvailability.DISABLED,
        pov_focalization=FeatureAvailability.DISABLED,
        voice_profiles=FeatureAvailability.DISABLED,
        world_consistency=FeatureAvailability.DISABLED,
        narrative_health=FeatureAvailability.OPTIONAL,
        narrative_templates=FeatureAvailability.OPTIONAL,
        character_archetypes=FeatureAvailability.OPTIONAL,
    )


def _create_divulgation_profile() -> FeatureProfile:
    """Perfil para divulgación científica/histórica."""
    return FeatureProfile(
        document_type=DocumentType.DIVULGATION,
        characters=FeatureAvailability.OPTIONAL,  # Puede tener figuras históricas
        relationships=FeatureAvailability.OPTIONAL,
        timeline=FeatureAvailability.OPTIONAL,  # Para narrativas históricas
        scenes=FeatureAvailability.DISABLED,
        pov_focalization=FeatureAvailability.DISABLED,
        voice_profiles=FeatureAvailability.DISABLED,
        pacing=FeatureAvailability.OPTIONAL,
        attribute_consistency=FeatureAvailability.OPTIONAL,
        terminology=FeatureAvailability.ENABLED,  # Muy relevante
        narrative_health=FeatureAvailability.OPTIONAL,
        narrative_templates=FeatureAvailability.OPTIONAL,
        character_archetypes=FeatureAvailability.OPTIONAL,
    )


def _create_essay_profile() -> FeatureProfile:
    """Perfil para ensayos."""
    return FeatureProfile(
        document_type=DocumentType.ESSAY,
        characters=FeatureAvailability.DISABLED,
        relationships=FeatureAvailability.DISABLED,
        timeline=FeatureAvailability.DISABLED,
        scenes=FeatureAvailability.DISABLED,
        pov_focalization=FeatureAvailability.DISABLED,
        voice_profiles=FeatureAvailability.DISABLED,
        pacing=FeatureAvailability.OPTIONAL,
        attribute_consistency=FeatureAvailability.DISABLED,
        world_consistency=FeatureAvailability.DISABLED,
        emotional_analysis=FeatureAvailability.OPTIONAL,
        narrative_health=FeatureAvailability.DISABLED,
        narrative_templates=FeatureAvailability.DISABLED,
        character_archetypes=FeatureAvailability.DISABLED,
    )


def _create_self_help_profile() -> FeatureProfile:
    """Perfil para autoayuda."""
    return FeatureProfile(
        document_type=DocumentType.SELF_HELP,
        characters=FeatureAvailability.DISABLED,
        relationships=FeatureAvailability.DISABLED,
        timeline=FeatureAvailability.DISABLED,
        scenes=FeatureAvailability.DISABLED,
        pov_focalization=FeatureAvailability.DISABLED,
        voice_profiles=FeatureAvailability.DISABLED,
        pacing=FeatureAvailability.OPTIONAL,
        attribute_consistency=FeatureAvailability.DISABLED,
        world_consistency=FeatureAvailability.DISABLED,
        narrative_health=FeatureAvailability.DISABLED,
        narrative_templates=FeatureAvailability.DISABLED,
        character_archetypes=FeatureAvailability.DISABLED,
    )


def _create_technical_profile() -> FeatureProfile:
    """Perfil para manuales técnicos."""
    return FeatureProfile(
        document_type=DocumentType.TECHNICAL,
        characters=FeatureAvailability.DISABLED,
        relationships=FeatureAvailability.DISABLED,
        timeline=FeatureAvailability.DISABLED,
        scenes=FeatureAvailability.DISABLED,
        pov_focalization=FeatureAvailability.DISABLED,
        voice_profiles=FeatureAvailability.DISABLED,
        pacing=FeatureAvailability.DISABLED,
        emotional_analysis=FeatureAvailability.DISABLED,
        attribute_consistency=FeatureAvailability.DISABLED,
        world_consistency=FeatureAvailability.DISABLED,
        terminology=FeatureAvailability.ENABLED,  # Crítico
        glossary=FeatureAvailability.ENABLED,  # Crítico
        narrative_health=FeatureAvailability.DISABLED,
        narrative_templates=FeatureAvailability.DISABLED,
        character_archetypes=FeatureAvailability.DISABLED,
    )


def _create_practical_profile() -> FeatureProfile:
    """Perfil para libros prácticos (cocina, DIY, etc.)."""
    return FeatureProfile(
        document_type=DocumentType.PRACTICAL,
        characters=FeatureAvailability.DISABLED,
        relationships=FeatureAvailability.DISABLED,
        timeline=FeatureAvailability.DISABLED,
        scenes=FeatureAvailability.DISABLED,
        pov_focalization=FeatureAvailability.DISABLED,
        voice_profiles=FeatureAvailability.DISABLED,
        pacing=FeatureAvailability.DISABLED,
        emotional_analysis=FeatureAvailability.DISABLED,
        attribute_consistency=FeatureAvailability.DISABLED,
        world_consistency=FeatureAvailability.DISABLED,
        terminology=FeatureAvailability.ENABLED,
        glossary=FeatureAvailability.ENABLED,
        narrative_health=FeatureAvailability.DISABLED,
        narrative_templates=FeatureAvailability.DISABLED,
        character_archetypes=FeatureAvailability.DISABLED,
    )


def _create_graphic_profile() -> FeatureProfile:
    """Perfil para novela gráfica/cómic."""
    return FeatureProfile(
        document_type=DocumentType.GRAPHIC,
        scenes=FeatureAvailability.OPTIONAL,  # Las viñetas son diferentes
        pacing=FeatureAvailability.OPTIONAL,  # Análisis de texto limitado
        register_analysis=FeatureAvailability.OPTIONAL,
        sticky_sentences=FeatureAvailability.OPTIONAL,
        echo_repetitions=FeatureAvailability.OPTIONAL,
        sentence_variation=FeatureAvailability.DISABLED,  # Poco texto
    )


def _create_children_profile() -> FeatureProfile:
    """Perfil para literatura infantil/juvenil."""
    # El perfil base - se ajusta según subtipo (edad)
    return FeatureProfile(
        document_type=DocumentType.CHILDREN,
        scenes=FeatureAvailability.OPTIONAL,  # Depende de la edad
        terminology=FeatureAvailability.OPTIONAL,  # Vocabulario adaptado
        age_readability=FeatureAvailability.ENABLED,  # Legibilidad por edad
    )


def _create_drama_profile() -> FeatureProfile:
    """Perfil para teatro/guion."""
    return FeatureProfile(
        document_type=DocumentType.DRAMA,
        scenes=FeatureAvailability.ENABLED,  # Escenas = actos/escenas teatrales
        pov_focalization=FeatureAvailability.DISABLED,  # No aplica
        pacing=FeatureAvailability.OPTIONAL,  # Diferente concepto
        sticky_sentences=FeatureAvailability.OPTIONAL,  # Principalmente diálogo
        sentence_variation=FeatureAvailability.OPTIONAL,
    )


# Mapping de tipos a funciones de creación
PROFILE_CREATORS = {
    DocumentType.FICTION: _create_fiction_profile,
    DocumentType.MEMOIR: _create_memoir_profile,
    DocumentType.BIOGRAPHY: _create_biography_profile,
    DocumentType.CELEBRITY: _create_celebrity_profile,
    DocumentType.DIVULGATION: _create_divulgation_profile,
    DocumentType.ESSAY: _create_essay_profile,
    DocumentType.SELF_HELP: _create_self_help_profile,
    DocumentType.TECHNICAL: _create_technical_profile,
    DocumentType.PRACTICAL: _create_practical_profile,
    DocumentType.GRAPHIC: _create_graphic_profile,
    DocumentType.CHILDREN: _create_children_profile,
    DocumentType.DRAMA: _create_drama_profile,
}


def create_feature_profile(
    document_type: DocumentType,
    document_subtype: Optional[str] = None
) -> FeatureProfile:
    """
    Crea un perfil de features para un tipo de documento.

    Args:
        document_type: Tipo principal de documento
        document_subtype: Subtipo específico (opcional)

    Returns:
        FeatureProfile configurado según el tipo
    """
    creator = PROFILE_CREATORS.get(document_type, _create_fiction_profile)
    profile = creator()
    profile.document_subtype = document_subtype

    # Ajustes específicos por subtipo
    if document_subtype:
        _apply_subtype_adjustments(profile, document_subtype)

    return profile


def _apply_subtype_adjustments(profile: FeatureProfile, subtype: str) -> None:
    """Aplica ajustes específicos según el subtipo."""

    # Ajustes para infantil por edad
    if subtype.startswith("INF_"):
        if subtype in ("INF_CAR", "INF_ALB"):
            # Cartoné y álbum ilustrado - muy poco texto
            profile.sticky_sentences = FeatureAvailability.DISABLED
            profile.echo_repetitions = FeatureAvailability.OPTIONAL
            profile.sentence_variation = FeatureAvailability.DISABLED
            profile.scenes = FeatureAvailability.DISABLED
            profile.timeline = FeatureAvailability.DISABLED
            profile.pacing = FeatureAvailability.DISABLED
        elif subtype == "INF_PRI":
            # Primeras lecturas
            profile.scenes = FeatureAvailability.OPTIONAL
            profile.timeline = FeatureAvailability.OPTIONAL
        elif subtype in ("INF_MID", "INF_YA"):
            # Middle grade y YA - casi como adulto
            profile.scenes = FeatureAvailability.ENABLED
            profile.timeline = FeatureAvailability.ENABLED

    # Ajustes para novela histórica
    if subtype == "FIC_HIS":
        profile.terminology = FeatureAvailability.ENABLED  # Términos de época
        profile.glossary = FeatureAvailability.ENABLED

    # Ajustes para microrrelatos
    if subtype == "FIC_MIC":
        profile.scenes = FeatureAvailability.DISABLED
        profile.timeline = FeatureAvailability.OPTIONAL
        profile.pacing = FeatureAvailability.OPTIONAL

    # Ajustes para manga (más texto que cómic occidental)
    if subtype == "GRA_MAN":
        profile.sentence_variation = FeatureAvailability.OPTIONAL
