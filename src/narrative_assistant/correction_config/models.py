"""
Modelos para configuración de corrección con herencia.

Define las estructuras de datos para todos los parámetros de corrección,
organizados por categoría con soporte para herencia tipo → subtipo.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class InheritanceSource(str, Enum):
    """Origen de un valor de configuración."""

    DEFAULT = "default"  # Valor por defecto global
    TYPE = "type"  # Heredado del tipo
    SUBTYPE = "subtype"  # Heredado del subtipo
    CUSTOM = "custom"  # Personalizado por el usuario


class DashType(str, Enum):
    """Tipos de guiones/rayas para diálogos."""

    EM_DASH = "em_dash"  # Raya española (—) U+2014
    EN_DASH = "en_dash"  # Guión largo (–) U+2013
    HYPHEN = "hyphen"  # Guión simple (-) U+002D
    NONE = "none"  # No usar guiones para diálogo
    AUTO = "auto"  # Detectar automáticamente del documento

    @property
    def char(self) -> str:
        """Devuelve el carácter Unicode correspondiente."""
        return {
            DashType.EM_DASH: "—",
            DashType.EN_DASH: "–",
            DashType.HYPHEN: "-",
            DashType.NONE: "",
            DashType.AUTO: "",  # Se determina en tiempo de análisis
        }.get(self, "")

    @property
    def label(self) -> str:
        """Etiqueta para mostrar en UI."""
        return {
            DashType.EM_DASH: "Raya española (—)",
            DashType.EN_DASH: "Guión largo (–)",
            DashType.HYPHEN: "Guión simple (-)",
            DashType.NONE: "No usar guiones",
            DashType.AUTO: "Detectar automáticamente",
        }.get(self, "")


class QuoteType(str, Enum):
    """Tipos de comillas para diálogos/pensamientos."""

    ANGULAR = "angular"  # Comillas angulares/latinas («»)
    DOUBLE = "double"  # Comillas inglesas dobles ("")
    SINGLE = "single"  # Comillas simples ('')
    NONE = "none"  # No usar comillas
    AUTO = "auto"  # Detectar automáticamente del documento

    @property
    def chars(self) -> tuple[str, str]:
        """Devuelve tupla (apertura, cierre)."""
        return {  # type: ignore[return-value]
            QuoteType.ANGULAR: ("«", "»"),
            QuoteType.DOUBLE: (""", """),
            QuoteType.SINGLE: ("'", "'"),
            QuoteType.NONE: ("", ""),
            QuoteType.AUTO: ("", ""),  # Se determina en tiempo de análisis
        }.get(self, ("", ""))

    @property
    def label(self) -> str:
        """Etiqueta para mostrar en UI."""
        return {
            QuoteType.ANGULAR: "Comillas angulares («»)",
            QuoteType.DOUBLE: "Comillas inglesas ()",
            QuoteType.SINGLE: "Comillas simples ('')",
            QuoteType.NONE: "No usar comillas",
            QuoteType.AUTO: "Detectar automáticamente",
        }.get(self, "")


class MarkerDetectionMode(str, Enum):
    """Modo de detección de marcadores."""

    AUTO = "auto"  # Detectar automáticamente del documento
    PRESET = "preset"  # Usar un preset predefinido
    CUSTOM = "custom"  # Configuración manual del usuario


class MarkerPreset(str, Enum):
    """Presets de configuración de marcadores."""

    SPANISH_TRADITIONAL = "spanish_traditional"  # Raya + angulares (RAE)
    ANGLO_SAXON = "anglo_saxon"  # Comillas dobles
    SPANISH_QUOTES = "spanish_quotes"  # Comillas angulares (sin raya)
    DETECT = "detect"  # Detectar del documento


@dataclass
class ParameterValue:
    """
    Valor de un parámetro con información de herencia.

    Permite saber de dónde viene cada valor para mostrarlo en la UI.
    """

    value: Any
    source: InheritanceSource
    source_name: str | None = None  # "Infantil", "Middle Grade", etc.

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "source": self.source.value,
            "source_name": self.source_name,
        }


# =============================================================================
# Configuraciones por categoría
# =============================================================================


@dataclass
class DialogConfig:
    """
    Configuración de análisis de diálogos.

    Soporta configuración por función (diálogo hablado, pensamientos, citas)
    con detección automática y presets predefinidos.
    """

    # ===== Modo de configuración =====
    # Cómo se determinan los marcadores
    detection_mode: MarkerDetectionMode = MarkerDetectionMode.PRESET
    preset: MarkerPreset = MarkerPreset.SPANISH_TRADITIONAL

    # ===== Marcadores por función =====
    # Diálogo hablado (parlamentos de personajes)
    spoken_dialogue_dash: DashType = DashType.EM_DASH
    spoken_dialogue_quote: QuoteType = QuoteType.NONE  # Alternativa si no se usa guión

    # Pensamientos internos
    thoughts_quote: QuoteType = QuoteType.ANGULAR
    thoughts_use_italics: bool = True

    # Diálogo dentro de diálogo (cita dentro de parlamento)
    nested_dialogue_quote: QuoteType = QuoteType.DOUBLE

    # Citas textuales
    textual_quote: QuoteType = QuoteType.ANGULAR

    # ===== Detección automática =====
    # ¿Se detectó automáticamente?
    auto_detected: bool = False
    detection_confidence: float = 0.0

    # ===== Consistencia =====
    # ¿Alertar cuando se use un marcador diferente al configurado?
    flag_inconsistent_markers: bool = True

    # ===== Análisis de verbos dicendi =====
    # ¿Analizar variación de verbos dicendi? (dijo, exclamó, murmuró...)
    analyze_dialog_tags: bool = True

    # Mínimo de tags únicos antes de alertar por repetición
    dialog_tag_variation_min: int = 3

    # ¿Alertar por tags repetidos consecutivos?
    flag_consecutive_same_tag: bool = True

    # ===== General =====
    # ¿Habilitar análisis de diálogo?
    enabled: bool = True

    # Legacy: mantener para compatibilidad (deprecated)
    dialog_markers: list[str] = field(default_factory=lambda: ["—", "«", "»", '"', '"', '"'])
    preferred_marker: str | None = None

    def _get_dash_char(self, dash) -> str:
        """Helper para obtener carácter de guión (enum o string)."""
        if hasattr(dash, "char"):
            return dash.char  # type: ignore[no-any-return]
        # Es un string, convertir manualmente
        return {"em_dash": "—", "en_dash": "–", "hyphen": "-"}.get(dash, "")

    def _get_quote_chars(self, quote) -> tuple[str, str]:
        """Helper para obtener comillas (enum o string)."""
        if hasattr(quote, "chars"):
            return quote.chars  # type: ignore[no-any-return]
        # Es un string, convertir manualmente
        return {  # type: ignore[return-value]
            "angular": ("«", "»"),
            "double": (""", """),
            "single": ("'", "'"),
        }.get(quote, ("", ""))

    def get_accepted_markers(self) -> list[str]:
        """Obtiene lista de todos los marcadores aceptados según la configuración."""
        markers = []

        # Guiones
        dash_val = self._get_value(self.spoken_dialogue_dash)
        if dash_val not in ("none", "auto"):
            char = self._get_dash_char(self.spoken_dialogue_dash)
            if char:
                markers.append(char)

        # Comillas para diálogo
        quote_val = self._get_value(self.spoken_dialogue_quote)
        if quote_val not in ("none", "auto"):
            open_q, close_q = self._get_quote_chars(self.spoken_dialogue_quote)
            if open_q:
                markers.extend([open_q, close_q])

        # Comillas para pensamientos
        thought_val = self._get_value(self.thoughts_quote)
        if thought_val not in ("none", "auto"):
            open_q, close_q = self._get_quote_chars(self.thoughts_quote)
            if open_q and open_q not in markers:
                markers.extend([open_q, close_q])

        # Comillas para nested
        nested_val = self._get_value(self.nested_dialogue_quote)
        if nested_val not in ("none", "auto"):
            open_q, close_q = self._get_quote_chars(self.nested_dialogue_quote)
            if open_q and open_q not in markers:
                markers.extend([open_q, close_q])

        return markers

    def _get_value(self, field) -> str:
        """Helper para obtener valor de un campo que puede ser enum o string."""
        if hasattr(field, "value"):
            return field.value  # type: ignore[no-any-return]
        return field  # type: ignore[no-any-return]

    def to_dict(self) -> dict:
        return {
            # Modo y preset
            "detection_mode": self._get_value(self.detection_mode),
            "preset": self._get_value(self.preset),
            # Marcadores por función
            "spoken_dialogue_dash": self._get_value(self.spoken_dialogue_dash),
            "spoken_dialogue_quote": self._get_value(self.spoken_dialogue_quote),
            "thoughts_quote": self._get_value(self.thoughts_quote),
            "thoughts_use_italics": self.thoughts_use_italics,
            "nested_dialogue_quote": self._get_value(self.nested_dialogue_quote),
            "textual_quote": self._get_value(self.textual_quote),
            # Detección
            "auto_detected": self.auto_detected,
            "detection_confidence": self.detection_confidence,
            # Consistencia y análisis
            "flag_inconsistent_markers": self.flag_inconsistent_markers,
            "analyze_dialog_tags": self.analyze_dialog_tags,
            "dialog_tag_variation_min": self.dialog_tag_variation_min,
            "flag_consecutive_same_tag": self.flag_consecutive_same_tag,
            "enabled": self.enabled,
            # Legacy (deprecated pero mantenido para compatibilidad)
            "dialog_markers": self.get_accepted_markers(),
            "preferred_marker": self.preferred_marker,
        }


@dataclass
class RepetitionConfig:
    """
    Configuración de detección de repeticiones.
    """

    # Tolerancia: cuántas ocurrencias antes de alertar
    # very_high = 5+, high = 4+, medium = 3+, low = 2+
    tolerance: Literal["very_high", "high", "medium", "low"] = "medium"

    # Ventana de proximidad en caracteres
    proximity_window_chars: int = 150

    # Longitud mínima de palabra para rastrear
    min_word_length: int = 4

    # Palabras a ignorar siempre (además de stopwords)
    ignore_words: list[str] = field(default_factory=list)

    # ¿Alertar por FALTA de repetición? (útil para infantil 0-6)
    flag_lack_of_repetition: bool = False

    # ¿Habilitar análisis de repeticiones?
    enabled: bool = True

    def get_threshold(self) -> int:
        """Convierte tolerancia a número de ocurrencias."""
        return {
            "very_high": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
        }.get(self.tolerance, 3)

    def to_dict(self) -> dict:
        return {
            "tolerance": self.tolerance,
            "threshold": self.get_threshold(),
            "proximity_window_chars": self.proximity_window_chars,
            "min_word_length": self.min_word_length,
            "ignore_words": self.ignore_words,
            "flag_lack_of_repetition": self.flag_lack_of_repetition,
            "enabled": self.enabled,
        }


@dataclass
class SentenceConfig:
    """
    Configuración de análisis de oraciones.
    """

    # Longitud máxima en palabras (None = sin límite)
    max_length_words: int | None = None

    # Longitud recomendada (soft warning)
    recommended_length_words: int | None = 25

    # ¿Analizar complejidad sintáctica?
    analyze_complexity: bool = True

    # Tolerancia a voz pasiva (%)
    passive_voice_tolerance_pct: float = 15.0

    # Tolerancia a adverbios en -mente (%)
    adverb_ly_tolerance_pct: float = 5.0

    # ¿Habilitar análisis de oraciones?
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "max_length_words": self.max_length_words,
            "recommended_length_words": self.recommended_length_words,
            "analyze_complexity": self.analyze_complexity,
            "passive_voice_tolerance_pct": self.passive_voice_tolerance_pct,
            "adverb_ly_tolerance_pct": self.adverb_ly_tolerance_pct,
            "enabled": self.enabled,
        }


@dataclass
class StyleConfig:
    """
    Configuración de análisis de estilo general.
    """

    # ¿Analizar variación de inicios de oración?
    analyze_sentence_starts: bool = True

    # ¿Analizar "sticky sentences" (oraciones pegajosas)?
    analyze_sticky_sentences: bool = True

    # Umbral de "pegajosidad" (% palabras comunes)
    sticky_threshold_pct: float = 45.0

    # ¿Analizar registro (formal/informal)?
    analyze_register: bool = True

    # ¿Analizar emociones en el texto?
    analyze_emotions: bool = True

    # ¿Habilitar análisis de estilo?
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "analyze_sentence_starts": self.analyze_sentence_starts,
            "analyze_sticky_sentences": self.analyze_sticky_sentences,
            "sticky_threshold_pct": self.sticky_threshold_pct,
            "analyze_register": self.analyze_register,
            "analyze_emotions": self.analyze_emotions,
            "enabled": self.enabled,
        }


@dataclass
class StructureConfig:
    """
    Configuración de análisis estructural.
    """

    # ¿Analizar timeline/cronología?
    timeline_enabled: bool = True

    # ¿Analizar relaciones entre personajes?
    relationships_enabled: bool = True

    # ¿Analizar consistencia de comportamiento?
    behavior_consistency_enabled: bool = True

    # ¿Detectar escenas/cambios de escena?
    scenes_enabled: bool = True

    # ¿Seguir ubicaciones de personajes?
    location_tracking_enabled: bool = True

    # ¿Rastrear estado vital (muertes/reapariciones)?
    vital_status_enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "timeline_enabled": self.timeline_enabled,
            "relationships_enabled": self.relationships_enabled,
            "behavior_consistency_enabled": self.behavior_consistency_enabled,
            "scenes_enabled": self.scenes_enabled,
            "location_tracking_enabled": self.location_tracking_enabled,
            "vital_status_enabled": self.vital_status_enabled,
        }


@dataclass
class ReadabilityConfig:
    """
    Configuración de legibilidad (especialmente para infantil).
    """

    # Rango de edad objetivo
    target_age_min: int | None = None
    target_age_max: int | None = None

    # ¿Analizar vocabulario por edad?
    analyze_vocabulary_age: bool = False

    # Vocabulario máximo (número de palabras únicas esperadas)
    max_vocabulary_size: int | None = None

    # ¿Habilitar análisis de legibilidad?
    enabled: bool = False

    def to_dict(self) -> dict:
        return {
            "target_age_min": self.target_age_min,
            "target_age_max": self.target_age_max,
            "analyze_vocabulary_age": self.analyze_vocabulary_age,
            "max_vocabulary_size": self.max_vocabulary_size,
            "enabled": self.enabled,
        }


@dataclass
class RegionalConfig:
    """
    Configuración de variantes regionales del español.
    """

    # ¿Habilitar análisis regional?
    enabled: bool = True

    # Variante objetivo (es_ES, es_MX, es_AR, etc.)
    target_region: str = "es_ES"

    # ¿Detectar mezcla de variantes?
    detect_mixed_variants: bool = True

    # ¿Sugerir alternativas regionales?
    suggest_regional_alternatives: bool = True

    # Confianza mínima para alertas regionales
    min_confidence: float = 0.7

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target_region": self.target_region,
            "detect_mixed_variants": self.detect_mixed_variants,
            "suggest_regional_alternatives": self.suggest_regional_alternatives,
            "min_confidence": self.min_confidence,
        }


# =============================================================================
# Reglas Editoriales
# =============================================================================


@dataclass
class EditorialRule:
    """
    Una regla editorial individual con soporte para herencia.

    Las reglas pueden heredarse del tipo/subtipo y ser habilitadas/deshabilitadas
    o sobreescritas a nivel de documento.
    """

    # Identificador único de la regla
    id: str = ""

    # Texto de la regla
    text: str = ""

    # ¿Está habilitada?
    enabled: bool = True

    # Origen de la regla
    source: InheritanceSource = InheritanceSource.CUSTOM

    # Nombre del origen (para mostrar en UI)
    source_name: str | None = None

    # ¿Ha sido modificada respecto al origen?
    overridden: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "enabled": self.enabled,
            "source": self.source.value,
            "source_name": self.source_name,
            "overridden": self.overridden,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EditorialRule":
        """Crea una regla desde un diccionario."""
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            enabled=data.get("enabled", True),
            source=InheritanceSource(data.get("source", "custom")),
            source_name=data.get("source_name"),
            overridden=data.get("overridden", False),
        )


@dataclass
class EditorialRulesConfig:
    """
    Configuración de reglas editoriales con herencia.

    Las reglas se heredan de tipo → subtipo → documento.
    A nivel de documento se pueden:
    - Deshabilitar reglas heredadas
    - Añadir nuevas reglas
    - Modificar reglas heredadas (crea copia local)
    """

    rules: list[EditorialRule] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rules": [rule.to_dict() for rule in self.rules],
        }

    def get_enabled_rules(self) -> list[EditorialRule]:
        """Devuelve solo las reglas habilitadas."""
        return [r for r in self.rules if r.enabled]

    def add_rule(
        self, text: str, source: InheritanceSource = InheritanceSource.CUSTOM
    ) -> EditorialRule:
        """Añade una nueva regla."""
        import uuid

        rule = EditorialRule(
            id=str(uuid.uuid4())[:8],
            text=text,
            source=source,
        )
        self.rules.append(rule)
        return rule

    def disable_rule(self, rule_id: str) -> bool:
        """Deshabilita una regla por ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = False
                if rule.source != InheritanceSource.CUSTOM:
                    rule.overridden = True
                return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Habilita una regla por ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = True
                return True
        return False


# =============================================================================
# Configuración completa
# =============================================================================


@dataclass
class CorrectionConfig:
    """
    Configuración completa de corrección para un documento.

    Agrupa todas las categorías de configuración con soporte
    para herencia tipo → subtipo → personalización.
    """

    # Metadatos
    type_code: str = "FIC"
    type_name: str = "Ficción"
    subtype_code: str | None = None
    subtype_name: str | None = None

    # Configuraciones por categoría
    dialog: DialogConfig = field(default_factory=DialogConfig)
    repetition: RepetitionConfig = field(default_factory=RepetitionConfig)
    sentence: SentenceConfig = field(default_factory=SentenceConfig)
    style: StyleConfig = field(default_factory=StyleConfig)
    structure: StructureConfig = field(default_factory=StructureConfig)
    readability: ReadabilityConfig = field(default_factory=ReadabilityConfig)
    regional: RegionalConfig = field(default_factory=RegionalConfig)

    # Reglas editoriales (también heredan)
    editorial_rules: EditorialRulesConfig = field(default_factory=EditorialRulesConfig)

    # Track de qué valores fueron heredados vs personalizados
    _inheritance_info: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serializa la configuración completa."""
        return {
            "type_code": self.type_code,
            "type_name": self.type_name,
            "subtype_code": self.subtype_code,
            "subtype_name": self.subtype_name,
            "dialog": self.dialog.to_dict(),
            "repetition": self.repetition.to_dict(),
            "sentence": self.sentence.to_dict(),
            "style": self.style.to_dict(),
            "structure": self.structure.to_dict(),
            "readability": self.readability.to_dict(),
            "regional": self.regional.to_dict(),
            "editorial_rules": self.editorial_rules.to_dict(),
            "inheritance": self._inheritance_info,
        }

    def get_inheritance_info(self, category: str, param: str) -> InheritanceSource:
        """Obtiene información de herencia de un parámetro."""
        key = f"{category}.{param}"
        return self._inheritance_info.get(key, InheritanceSource.DEFAULT)  # type: ignore[no-any-return]

    def set_inheritance_info(
        self, category: str, param: str, source: InheritanceSource, source_name: str = None  # type: ignore[assignment]
    ):
        """Registra información de herencia de un parámetro."""
        key = f"{category}.{param}"
        self._inheritance_info[key] = {
            "source": source.value,
            "source_name": source_name,
        }
