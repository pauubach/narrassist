"""
Configuración para detectores de correcciones.

Permite al usuario personalizar qué tipos de correcciones detectar
y con qué parámetros (sensibilidad, estilos preferidos, etc.).

Incluye sistema de perfiles de documento para ajustar la detección
según el tipo de texto (literario, técnico, jurídico, etc.).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class DocumentField(Enum):
    """Campo o dominio del documento."""

    GENERAL = "general"  # Sin especialización
    LITERARY = "literary"  # Novela, cuento, poesía
    JOURNALISTIC = "journalistic"  # Periodismo, reportajes
    ACADEMIC = "academic"  # Ensayos, tesis, papers
    TECHNICAL = "technical"  # Manuales técnicos, informática
    LEGAL = "legal"  # Textos jurídicos, contratos
    MEDICAL = "medical"  # Textos médicos, científicos
    BUSINESS = "business"  # Empresarial, marketing
    SELFHELP = "selfhelp"  # Autoayuda, desarrollo personal
    CULINARY = "culinary"  # Recetas, gastronomía


class RegisterLevel(Enum):
    """Nivel de registro lingüístico."""

    FORMAL = "formal"  # Académico, oficial
    NEUTRAL = "neutral"  # Estándar
    COLLOQUIAL = "colloquial"  # Informal pero correcto
    VULGAR = "vulgar"  # Incluye palabras malsonantes (intencional)


class AudienceType(Enum):
    """Tipo de audiencia del documento."""

    GENERAL = "general"  # Público general
    CHILDREN = "children"  # Infantil/juvenil
    ADULT = "adult"  # Adultos
    SPECIALIST = "specialist"  # Profesionales del campo
    MIXED = "mixed"  # Audiencia mixta


@dataclass
class DocumentProfile:
    """
    Perfil del documento para ajustar detectores.

    Define el contexto editorial del manuscrito para que el sistema
    ajuste sus expectativas y reduzca falsos positivos.
    """

    # Campo/dominio principal del documento
    document_field: DocumentField = DocumentField.LITERARY

    # Campos secundarios (ej: novela con temas médicos)
    secondary_fields: list[DocumentField] = field(default_factory=list)

    # Nivel de registro esperado
    register: RegisterLevel = RegisterLevel.NEUTRAL

    # Tipo de audiencia
    audience: AudienceType = AudienceType.GENERAL

    # Variante regional principal
    region: str = "es_ES"

    # Permitir mezcla de registros (diálogos coloquiales en texto formal)
    allow_mixed_register: bool = True

    # Términos personalizados del autor/obra (no corregir)
    author_terms: list[str] = field(default_factory=list)

    # Alertar sobre tecnicismos que pueden requerir glosario
    alert_technical_terms: bool = False

    def is_field_relevant(self, check_field: DocumentField) -> bool:
        """Verifica si un campo es relevante para el documento."""
        return (
            check_field == self.document_field or
            check_field in self.secondary_fields or
            check_field == DocumentField.GENERAL
        )

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "document_field": self.document_field.value,
            "secondary_fields": [f.value for f in self.secondary_fields],
            "register": self.register.value,
            "audience": self.audience.value,
            "region": self.region,
            "allow_mixed_register": self.allow_mixed_register,
            "author_terms": self.author_terms,
            "alert_technical_terms": self.alert_technical_terms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentProfile":
        """Crea desde diccionario."""
        return cls(
            document_field=DocumentField(data.get("document_field", "literary")),
            secondary_fields=[
                DocumentField(f) for f in data.get("secondary_fields", [])
            ],
            register=RegisterLevel(data.get("register", "neutral")),
            audience=AudienceType(data.get("audience", "general")),
            region=data.get("region", "es_ES"),
            allow_mixed_register=data.get("allow_mixed_register", True),
            author_terms=data.get("author_terms", []),
            alert_technical_terms=data.get("alert_technical_terms", False),
        )


@dataclass
class FieldDictionaryConfig:
    """Configuración de diccionarios de campo especializado."""

    enabled: bool = True

    # Campos cuyos diccionarios cargar
    active_fields: list[DocumentField] = field(
        default_factory=lambda: [DocumentField.GENERAL]
    )

    # Alertar cuando se usa terminología de un campo no configurado
    alert_unexpected_field_terms: bool = True

    # Sugerir términos más accesibles para audiencia general
    suggest_accessible_alternatives: bool = False

    # Confianza mínima para detección de campo
    min_confidence: float = 0.7


@dataclass
class TypographyConfig:
    """Configuración del detector de tipografía."""

    enabled: bool = True

    # Estilo de guiones para diálogos
    # em: raya (—), en: semiraya (–), hyphen: guion (-)
    dialogue_dash: Literal["em", "en", "hyphen"] = "em"

    # Estilo de comillas preferido
    # angular: «», curly: "", straight: ""
    quote_style: Literal["angular", "curly", "straight"] = "angular"

    # Detectar problemas de espaciado
    check_spacing: bool = True

    # Detectar puntos suspensivos mal formados
    check_ellipsis: bool = True

    # Detectar espacios múltiples
    check_multiple_spaces: bool = True

    # Detectar secuencias de puntuación inválidas (,. !? ??)
    check_invalid_sequences: bool = True

    # Detectar pares de signos sin cerrar («, (, [)
    check_unclosed_pairs: bool = True

    # Detectar orden incorrecto de comilla y punto según RAE
    # RAE: el punto va DESPUÉS de la comilla de cierre
    check_quote_period_order: bool = True


@dataclass
class RepetitionConfig:
    """Configuración del detector de repeticiones."""

    enabled: bool = True

    # Distancia mínima entre repeticiones (en palabras)
    min_distance: int = 50

    # Longitud mínima de palabra para considerar (ignora artículos, etc.)
    min_word_length: int = 4

    # Ignorar repeticiones en diálogos (intencionales)
    ignore_dialogue: bool = True

    # Sensibilidad: cuántas repeticiones antes de alertar
    sensitivity: Literal["low", "medium", "high"] = "medium"


@dataclass
class AgreementConfig:
    """Configuración del detector de concordancia."""

    enabled: bool = True

    # Detectar discordancia de género
    check_gender: bool = True

    # Detectar discordancia de número
    check_number: bool = True

    # Confianza mínima para reportar (0.0-1.0)
    min_confidence: float = 0.7


@dataclass
class TerminologyConfig:
    """Configuración del detector de terminología."""

    enabled: bool = True

    # Longitud mínima de término a considerar
    min_term_length: int = 4

    # Número mínimo de ocurrencias para reportar
    min_occurrences: int = 3

    # Umbral de similitud para agrupar (0.0-1.0)
    similarity_threshold: float = 0.75

    # Usar embeddings para detección (más preciso pero lento)
    use_embeddings: bool = True

    # Máximo de variantes a reportar por grupo
    max_variants_to_report: int = 5


@dataclass
class RegionalConfig:
    """Configuración del detector de vocabulario regional."""

    enabled: bool = True

    # Variante regional del español a usar como referencia
    # es_ES: España, es_MX: México, es_AR: Argentina, etc.
    target_region: str = "es_ES"

    # Detectar mezcla de variantes regionales
    detect_mixed_variants: bool = True

    # Sugerir alternativas de la región configurada
    suggest_regional_alternatives: bool = True

    # Confianza mínima para reportar
    min_confidence: float = 0.7


@dataclass
class ClarityConfig:
    """Configuración del detector de claridad."""

    enabled: bool = True

    # Límites de longitud de oración
    max_sentence_words: int = 50  # Palabras máximas por oración
    max_sentence_chars: int = 300  # Caracteres máximos por oración
    warning_sentence_words: int = 35  # Umbral de advertencia

    # Subordinación
    max_subordinates: int = 3  # Máximo de subordinadas encadenadas

    # Párrafos
    min_pauses_per_100_words: int = 3  # Mínimo de comas/punto y coma por 100 palabras

    # Confianza base
    base_confidence: float = 0.85


@dataclass
class GrammarConfig:
    """Configuración del detector gramatical."""

    enabled: bool = True

    # Qué reglas aplicar
    check_dequeismo: bool = True
    check_queismo: bool = True
    check_laismo: bool = True
    check_loismo: bool = True
    check_gender_agreement: bool = True
    check_number_agreement: bool = True
    check_adjective_agreement: bool = True
    check_redundancy: bool = True
    check_other: bool = True  # habemos, gerundio de posterioridad, etc.

    # Umbral mínimo de confianza
    min_confidence: float = 0.5


@dataclass
class AnglicismsConfig:
    """Configuración del detector de anglicismos."""

    enabled: bool = True

    # Detectar anglicismos del diccionario
    check_dictionary: bool = True

    # Detectar por patrones morfológicos (-ing, -ness, etc.)
    check_morphological: bool = False  # Por defecto desactivado (muchos falsos positivos)

    # Confianza base para detecciones
    base_confidence: float = 0.85


@dataclass
class CrutchWordsConfig:
    """Configuración del detector de muletillas."""

    enabled: bool = True

    # Umbral de z-score para considerar sobreuso (2.0 = 2 desviaciones estándar)
    z_score_threshold: float = 2.0

    # Mínimo de ocurrencias para reportar
    min_occurrences: int = 5

    # Categorías a analizar
    check_adverbs: bool = True  # "realmente", "obviamente"
    check_connectors: bool = True  # "sin embargo", "por lo tanto"
    check_speech_verbs: bool = True  # "susurró", "exclamó"
    check_intensifiers: bool = True  # "muy", "bastante"
    check_filler_phrases: bool = True  # "es decir", "o sea"

    # Confianza base
    base_confidence: float = 0.75


@dataclass
class GlossaryConfig:
    """Configuración del detector de glosario."""

    enabled: bool = True

    # Alertar cuando se usa variante en lugar del término canónico
    alert_on_variants: bool = True

    # Alertar cuando un término inventado no está en el glosario
    alert_undefined_invented: bool = True

    # Alertar cuando un término técnico no tiene definición
    alert_undefined_technical: bool = True

    # Actualizar estadísticas de uso durante análisis
    update_usage_stats: bool = True

    # Umbral de similitud para coincidencia aproximada (fuzzy matching)
    fuzzy_threshold: float = 0.85

    # Confianza base
    base_confidence: float = 0.80


@dataclass
class AnacolutoConfig:
    """Configuración del detector de anacolutos."""

    enabled: bool = True

    # Detectar nominativus pendens (sujeto "colgado")
    check_nominativus_pendens: bool = True

    # Detectar cambios de construcción
    check_broken_construction: bool = True

    # Detectar cláusulas incompletas
    check_incomplete_clause: bool = True

    # Detectar cambios de sujeto problemáticos
    check_subject_shift: bool = True

    # Detectar modificadores "colgantes"
    check_dangling_modifier: bool = True

    # Longitud mínima de oración para analizar (en palabras)
    min_sentence_words: int = 8

    # Usar LLM para validación (reduce falsos positivos)
    use_llm_validation: bool = False

    # Confianza base
    base_confidence: float = 0.75


@dataclass
class POVConfig:
    """Configuración del detector de punto de vista narrativo."""

    enabled: bool = True

    # Detectar cambios de persona gramatical (yo -> él, etc.)
    check_person_shift: bool = True

    # Detectar cambios de focalizador (quién percibe/piensa)
    check_focalizer_shift: bool = True

    # Detectar mezcla de tú/usted
    check_tu_usted_mix: bool = True

    # Detectar omnisciencia inconsistente
    check_inconsistent_omniscience: bool = True

    # Número mínimo de párrafos para analizar cambios
    min_paragraphs: int = 2

    # Distancia mínima (en párrafos) para considerar un cambio como problema
    # (cambios muy cercanos pueden ser intencionales)
    min_distance_for_alert: int = 1

    # Usar LLM para validación avanzada (detecta focalizador)
    use_llm_validation: bool = False

    # Confianza base
    base_confidence: float = 0.70


@dataclass
class CorrectionConfig:
    """
    Configuración global de correcciones.

    Agrupa la configuración de todos los detectores.
    """

    # Perfil del documento
    profile: DocumentProfile = field(default_factory=DocumentProfile)

    # Detectores individuales
    typography: TypographyConfig = field(default_factory=TypographyConfig)
    repetition: RepetitionConfig = field(default_factory=RepetitionConfig)
    agreement: AgreementConfig = field(default_factory=AgreementConfig)
    terminology: TerminologyConfig = field(default_factory=TerminologyConfig)
    regional: RegionalConfig = field(default_factory=RegionalConfig)
    field_dictionary: FieldDictionaryConfig = field(default_factory=FieldDictionaryConfig)
    clarity: ClarityConfig = field(default_factory=ClarityConfig)
    grammar: GrammarConfig = field(default_factory=GrammarConfig)
    anglicisms: AnglicismsConfig = field(default_factory=AnglicismsConfig)
    crutch_words: CrutchWordsConfig = field(default_factory=CrutchWordsConfig)
    glossary: GlossaryConfig = field(default_factory=GlossaryConfig)
    anacoluto: AnacolutoConfig = field(default_factory=AnacolutoConfig)
    pov: POVConfig = field(default_factory=POVConfig)

    # Configuración global
    # Máximo de issues por categoría (para no abrumar)
    max_issues_per_category: int = 100

    # Usar LLM para revisar alertas (reduce falsos positivos)
    use_llm_review: bool = False
    llm_review_model: str = "llama3.2"

    @classmethod
    def default(cls) -> "CorrectionConfig":
        """Retorna configuración por defecto."""
        return cls()

    @classmethod
    def for_novel(cls) -> "CorrectionConfig":
        """Configuración optimizada para novela literaria."""
        return cls(
            profile=DocumentProfile(
                document_field=DocumentField.LITERARY,
                register=RegisterLevel.NEUTRAL,
                allow_mixed_register=True,  # Diálogos coloquiales permitidos
            ),
            typography=TypographyConfig(
                dialogue_dash="em",
                quote_style="angular",
            ),
            repetition=RepetitionConfig(
                min_distance=30,  # Más estricto en novela
                sensitivity="high",
            ),
            field_dictionary=FieldDictionaryConfig(
                active_fields=[DocumentField.LITERARY, DocumentField.GENERAL],
            ),
        )

    @classmethod
    def for_technical(cls) -> "CorrectionConfig":
        """Configuración optimizada para manual técnico."""
        return cls(
            profile=DocumentProfile(
                document_field=DocumentField.TECHNICAL,
                register=RegisterLevel.FORMAL,
                audience=AudienceType.SPECIALIST,
                allow_mixed_register=False,
            ),
            typography=TypographyConfig(
                dialogue_dash="em",
                quote_style="straight",  # Más común en técnico
            ),
            repetition=RepetitionConfig(
                min_distance=100,  # Menos estricto, repetición técnica es normal
                sensitivity="low",
            ),
            field_dictionary=FieldDictionaryConfig(
                active_fields=[DocumentField.TECHNICAL, DocumentField.GENERAL],
                alert_unexpected_field_terms=False,  # Tecnicismos esperados
            ),
        )

    @classmethod
    def for_legal(cls) -> "CorrectionConfig":
        """Configuración optimizada para textos jurídicos."""
        return cls(
            profile=DocumentProfile(
                document_field=DocumentField.LEGAL,
                register=RegisterLevel.FORMAL,
                audience=AudienceType.SPECIALIST,
                allow_mixed_register=False,
            ),
            typography=TypographyConfig(
                dialogue_dash="em",
                quote_style="angular",
            ),
            repetition=RepetitionConfig(
                min_distance=150,  # Muy permisivo - repetición legal es normal
                sensitivity="low",
            ),
            field_dictionary=FieldDictionaryConfig(
                active_fields=[DocumentField.LEGAL, DocumentField.GENERAL],
            ),
        )

    @classmethod
    def for_medical(cls) -> "CorrectionConfig":
        """Configuración optimizada para textos médicos."""
        return cls(
            profile=DocumentProfile(
                document_field=DocumentField.MEDICAL,
                register=RegisterLevel.FORMAL,
                audience=AudienceType.SPECIALIST,
            ),
            typography=TypographyConfig(
                dialogue_dash="em",
                quote_style="straight",
            ),
            repetition=RepetitionConfig(
                min_distance=100,
                sensitivity="low",
            ),
            field_dictionary=FieldDictionaryConfig(
                active_fields=[DocumentField.MEDICAL, DocumentField.GENERAL],
            ),
        )

    @classmethod
    def for_journalism(cls) -> "CorrectionConfig":
        """Configuración optimizada para periodismo."""
        return cls(
            profile=DocumentProfile(
                document_field=DocumentField.JOURNALISTIC,
                register=RegisterLevel.NEUTRAL,
                audience=AudienceType.GENERAL,
            ),
            typography=TypographyConfig(
                dialogue_dash="em",
                quote_style="angular",
            ),
            repetition=RepetitionConfig(
                min_distance=40,  # Moderado
                sensitivity="medium",
            ),
            field_dictionary=FieldDictionaryConfig(
                active_fields=[DocumentField.JOURNALISTIC, DocumentField.GENERAL],
                suggest_accessible_alternatives=True,  # Para público general
            ),
        )

    @classmethod
    def for_selfhelp(cls) -> "CorrectionConfig":
        """Configuración optimizada para autoayuda."""
        return cls(
            profile=DocumentProfile(
                document_field=DocumentField.SELFHELP,
                register=RegisterLevel.COLLOQUIAL,  # Más cercano al lector
                audience=AudienceType.GENERAL,
            ),
            typography=TypographyConfig(
                dialogue_dash="em",
                quote_style="angular",
            ),
            repetition=RepetitionConfig(
                min_distance=50,
                sensitivity="medium",
            ),
            field_dictionary=FieldDictionaryConfig(
                active_fields=[DocumentField.SELFHELP, DocumentField.GENERAL],
                suggest_accessible_alternatives=True,
            ),
        )

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización."""
        return {
            "profile": self.profile.to_dict(),
            "typography": {
                "enabled": self.typography.enabled,
                "dialogue_dash": self.typography.dialogue_dash,
                "quote_style": self.typography.quote_style,
                "check_spacing": self.typography.check_spacing,
                "check_ellipsis": self.typography.check_ellipsis,
                "check_multiple_spaces": self.typography.check_multiple_spaces,
            },
            "repetition": {
                "enabled": self.repetition.enabled,
                "min_distance": self.repetition.min_distance,
                "min_word_length": self.repetition.min_word_length,
                "ignore_dialogue": self.repetition.ignore_dialogue,
                "sensitivity": self.repetition.sensitivity,
            },
            "agreement": {
                "enabled": self.agreement.enabled,
                "check_gender": self.agreement.check_gender,
                "check_number": self.agreement.check_number,
                "min_confidence": self.agreement.min_confidence,
            },
            "terminology": {
                "enabled": self.terminology.enabled,
                "min_term_length": self.terminology.min_term_length,
                "min_occurrences": self.terminology.min_occurrences,
                "similarity_threshold": self.terminology.similarity_threshold,
                "use_embeddings": self.terminology.use_embeddings,
                "max_variants_to_report": self.terminology.max_variants_to_report,
            },
            "regional": {
                "enabled": self.regional.enabled,
                "target_region": self.regional.target_region,
                "detect_mixed_variants": self.regional.detect_mixed_variants,
                "suggest_regional_alternatives": self.regional.suggest_regional_alternatives,
                "min_confidence": self.regional.min_confidence,
            },
            "field_dictionary": {
                "enabled": self.field_dictionary.enabled,
                "active_fields": [f.value for f in self.field_dictionary.active_fields],
                "alert_unexpected_field_terms": self.field_dictionary.alert_unexpected_field_terms,
                "suggest_accessible_alternatives": self.field_dictionary.suggest_accessible_alternatives,
                "min_confidence": self.field_dictionary.min_confidence,
            },
            "anacoluto": {
                "enabled": self.anacoluto.enabled,
                "check_nominativus_pendens": self.anacoluto.check_nominativus_pendens,
                "check_broken_construction": self.anacoluto.check_broken_construction,
                "check_incomplete_clause": self.anacoluto.check_incomplete_clause,
                "check_subject_shift": self.anacoluto.check_subject_shift,
                "check_dangling_modifier": self.anacoluto.check_dangling_modifier,
                "use_llm_validation": self.anacoluto.use_llm_validation,
                "base_confidence": self.anacoluto.base_confidence,
            },
            "pov": {
                "enabled": self.pov.enabled,
                "check_person_shift": self.pov.check_person_shift,
                "check_focalizer_shift": self.pov.check_focalizer_shift,
                "check_tu_usted_mix": self.pov.check_tu_usted_mix,
                "check_inconsistent_omniscience": self.pov.check_inconsistent_omniscience,
                "use_llm_validation": self.pov.use_llm_validation,
                "base_confidence": self.pov.base_confidence,
            },
            "max_issues_per_category": self.max_issues_per_category,
            "use_llm_review": self.use_llm_review,
            "llm_review_model": self.llm_review_model,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CorrectionConfig":
        """Crea configuración desde diccionario."""
        # Parse field dictionary config specially due to enum list
        field_dict_data = data.get("field_dictionary", {})
        field_dict_config = FieldDictionaryConfig(
            enabled=field_dict_data.get("enabled", True),
            active_fields=[
                DocumentField(f) for f in field_dict_data.get("active_fields", ["general"])
            ],
            alert_unexpected_field_terms=field_dict_data.get("alert_unexpected_field_terms", True),
            suggest_accessible_alternatives=field_dict_data.get("suggest_accessible_alternatives", False),
            min_confidence=field_dict_data.get("min_confidence", 0.7),
        )

        # Parse anacoluto config
        anacoluto_data = data.get("anacoluto", {})
        anacoluto_config = AnacolutoConfig(
            enabled=anacoluto_data.get("enabled", True),
            check_nominativus_pendens=anacoluto_data.get("check_nominativus_pendens", True),
            check_broken_construction=anacoluto_data.get("check_broken_construction", True),
            check_incomplete_clause=anacoluto_data.get("check_incomplete_clause", True),
            check_subject_shift=anacoluto_data.get("check_subject_shift", True),
            check_dangling_modifier=anacoluto_data.get("check_dangling_modifier", True),
            use_llm_validation=anacoluto_data.get("use_llm_validation", False),
            base_confidence=anacoluto_data.get("base_confidence", 0.75),
        )

        # Parse pov config
        pov_data = data.get("pov", {})
        pov_config = POVConfig(
            enabled=pov_data.get("enabled", True),
            check_person_shift=pov_data.get("check_person_shift", True),
            check_focalizer_shift=pov_data.get("check_focalizer_shift", True),
            check_tu_usted_mix=pov_data.get("check_tu_usted_mix", True),
            check_inconsistent_omniscience=pov_data.get("check_inconsistent_omniscience", True),
            use_llm_validation=pov_data.get("use_llm_validation", False),
            base_confidence=pov_data.get("base_confidence", 0.70),
        )

        return cls(
            profile=DocumentProfile.from_dict(data.get("profile", {})),
            typography=TypographyConfig(**data.get("typography", {})),
            repetition=RepetitionConfig(**data.get("repetition", {})),
            agreement=AgreementConfig(**data.get("agreement", {})),
            terminology=TerminologyConfig(**data.get("terminology", {})),
            regional=RegionalConfig(**data.get("regional", {})),
            field_dictionary=field_dict_config,
            anacoluto=anacoluto_config,
            pov=pov_config,
            max_issues_per_category=data.get("max_issues_per_category", 100),
            use_llm_review=data.get("use_llm_review", False),
            llm_review_model=data.get("llm_review_model", "llama3.2"),
        )
