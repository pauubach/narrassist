"""
Reporte sensorial (Sensory Report).

Analiza la presencia de descripciones sensoriales en el texto (5 sentidos):
- Vista: colores, formas, luz, oscuridad, gestos visuales
- Oído: sonidos, música, silencio, ruido, onomatopeyas
- Tacto: texturas, temperatura, contacto físico
- Olfato: olores, aromas, fragancias
- Gusto: sabores, comida, bebida

Genera un reporte con:
- Distribución por sentido
- Densidad sensorial por capítulo
- Capítulos con baja/alta densidad sensorial
- Detalles sensoriales encontrados con contexto

Inspirado en ProWritingAid's Sensory Report.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...core.errors import ErrorSeverity, NLPError
from ...core.result import Result

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["SensoryAnalyzer"] = None


def get_sensory_analyzer() -> "SensoryAnalyzer":
    """Obtener instancia singleton del analizador sensorial."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SensoryAnalyzer()

    return _instance


def reset_sensory_analyzer() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================


class SensoryType(Enum):
    """Los 5 sentidos."""

    SIGHT = "sight"  # Vista
    HEARING = "hearing"  # Oído
    TOUCH = "touch"  # Tacto
    SMELL = "smell"  # Olfato
    TASTE = "taste"  # Gusto


class SensoryDensity(Enum):
    """Nivel de densidad sensorial."""

    RICH = "rich"  # >15 detalles por 1000 palabras
    ADEQUATE = "adequate"  # 5-15 detalles por 1000 palabras
    SPARSE = "sparse"  # 1-5 detalles por 1000 palabras
    ABSENT = "absent"  # 0 detalles


@dataclass
class SensoryDetail:
    """Un detalle sensorial detectado en el texto."""

    sense: SensoryType
    text: str  # Fragmento detectado
    context: str  # Contexto circundante (~50 chars antes/después)
    start_char: int
    end_char: int
    chapter: int | None = None
    keyword: str = ""  # Palabra clave que activó la detección
    confidence: float = 0.8


@dataclass
class ChapterSensoryStats:
    """Estadísticas sensoriales de un capítulo."""

    chapter: int
    word_count: int = 0
    details_count: int = 0
    density: float = 0.0  # Detalles por 1000 palabras
    density_level: SensoryDensity = SensoryDensity.ABSENT
    by_sense: dict = field(
        default_factory=lambda: {
            SensoryType.SIGHT: 0,
            SensoryType.HEARING: 0,
            SensoryType.TOUCH: 0,
            SensoryType.SMELL: 0,
            SensoryType.TASTE: 0,
        }
    )
    dominant_sense: SensoryType | None = None
    missing_senses: list[SensoryType] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "word_count": self.word_count,
            "details_count": self.details_count,
            "density": round(self.density, 2),
            "density_level": self.density_level.value,
            "by_sense": {s.value: c for s, c in self.by_sense.items()},
            "dominant_sense": self.dominant_sense.value if self.dominant_sense else None,
            "missing_senses": [s.value for s in self.missing_senses],
        }


@dataclass
class SensoryReport:
    """Reporte completo de análisis sensorial."""

    # Globales
    total_details: int = 0
    total_words: int = 0
    overall_density: float = 0.0
    overall_density_level: SensoryDensity = SensoryDensity.ABSENT

    # Distribución por sentido
    by_sense: dict = field(
        default_factory=lambda: {
            SensoryType.SIGHT: 0,
            SensoryType.HEARING: 0,
            SensoryType.TOUCH: 0,
            SensoryType.SMELL: 0,
            SensoryType.TASTE: 0,
        }
    )
    sense_percentages: dict = field(default_factory=dict)

    # Desequilibrio
    dominant_sense: SensoryType | None = None
    weakest_sense: SensoryType | None = None
    balance_score: float = 0.0  # 0-1, 1 = perfectamente equilibrado

    # Por capítulo
    chapter_stats: list[ChapterSensoryStats] = field(default_factory=list)
    sparse_chapters: list[int] = field(default_factory=list)
    rich_chapters: list[int] = field(default_factory=list)

    # Detalles encontrados
    details: list[SensoryDetail] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_details": self.total_details,
            "total_words": self.total_words,
            "overall_density": round(self.overall_density, 2),
            "overall_density_level": self.overall_density_level.value,
            "by_sense": {s.value: c for s, c in self.by_sense.items()},
            "sense_percentages": {s.value: round(p, 1) for s, p in self.sense_percentages.items()},
            "dominant_sense": self.dominant_sense.value if self.dominant_sense else None,
            "weakest_sense": self.weakest_sense.value if self.weakest_sense else None,
            "balance_score": round(self.balance_score, 2),
            "chapter_stats": [cs.to_dict() for cs in self.chapter_stats],
            "sparse_chapters": self.sparse_chapters,
            "rich_chapters": self.rich_chapters,
            "details": [
                {
                    "sense": d.sense.value,
                    "text": d.text,
                    "context": d.context,
                    "start_char": d.start_char,
                    "end_char": d.end_char,
                    "chapter": d.chapter,
                    "keyword": d.keyword,
                    "confidence": round(d.confidence, 2),
                }
                for d in self.details
            ],
        }


SENSE_LABELS: dict[SensoryType, str] = {
    SensoryType.SIGHT: "vista",
    SensoryType.HEARING: "oído",
    SensoryType.TOUCH: "tacto",
    SensoryType.SMELL: "olfato",
    SensoryType.TASTE: "gusto",
}


def generate_sensory_suggestions(report: "SensoryReport") -> list[dict]:
    """
    Genera sugerencias de enriquecimiento sensorial a partir del análisis.

    No genera texto — señala carencias y propone direcciones al corrector.
    """
    suggestions: list[dict] = []

    # Sugerencia por densidad global baja
    if report.overall_density_level in (SensoryDensity.SPARSE, SensoryDensity.ABSENT):
        suggestions.append(
            {
                "type": "density",
                "priority": "high"
                if report.overall_density_level == SensoryDensity.ABSENT
                else "medium",
                "message": f"El manuscrito tiene una densidad sensorial {report.overall_density_level.value} "
                f"({report.overall_density:.1f} detalles/1000 palabras). "
                f"Considere señalar al autor las escenas clave donde añadir detalles sensoriales "
                f"para mejorar la inmersión del lector.",
            }
        )

    # Sugerencia por desequilibrio sensorial
    if report.balance_score < 0.4 and report.dominant_sense and report.weakest_sense:
        dom = SENSE_LABELS.get(report.dominant_sense, report.dominant_sense.value)
        weak = SENSE_LABELS.get(report.weakest_sense, report.weakest_sense.value)
        suggestions.append(
            {
                "type": "balance",
                "priority": "medium",
                "message": f"Fuerte dependencia del sentido de la {dom}. "
                f"El {weak} está infrautilizado. Sugerir al autor diversificar "
                f"los sentidos usados en las descripciones para una experiencia más rica.",
            }
        )

    # Sugerencia por capítulos sin detalles sensoriales
    if report.sparse_chapters:
        ch_list = ", ".join(str(c) for c in report.sparse_chapters[:5])
        extra = (
            f" (y {len(report.sparse_chapters) - 5} más)" if len(report.sparse_chapters) > 5 else ""
        )
        suggestions.append(
            {
                "type": "sparse_chapters",
                "priority": "medium",
                "message": f"Los capítulos {ch_list}{extra} tienen escasa presencia sensorial. "
                f"Son candidatos prioritarios para enriquecimiento.",
            }
        )

    # Sugerencia por sentidos completamente ausentes
    for sense_type in SensoryType:
        count = report.by_sense.get(sense_type, 0)
        if count == 0 and report.total_details > 0:
            label = SENSE_LABELS.get(sense_type, sense_type.value)
            suggestions.append(
                {
                    "type": "missing_sense",
                    "priority": "low",
                    "sense": sense_type.value,
                    "message": f"El sentido del {label} está completamente ausente en el manuscrito. "
                    f"Según el tipo de historia, podría ser apropiado incluir alguna referencia.",
                }
            )

    # Sugerencia por capítulos con un solo sentido
    for cs in report.chapter_stats:
        if cs.details_count > 0 and len(cs.missing_senses) >= 4:
            dom_label = SENSE_LABELS.get(cs.dominant_sense, "") if cs.dominant_sense else ""
            suggestions.append(
                {
                    "type": "mono_sense_chapter",
                    "priority": "low",
                    "chapter": cs.chapter,
                    "message": f"El capítulo {cs.chapter} usa casi exclusivamente el {dom_label}. "
                    f"Variar los sentidos podría mejorar la escena.",
                }
            )

    return suggestions


# =============================================================================
# Vocabulario sensorial en español
# =============================================================================

# Vista: verbos, adjetivos, sustantivos relacionados con ver
SIGHT_KEYWORDS: dict[str, float] = {
    # Verbos
    "ver": 0.7,
    "mirar": 0.9,
    "observar": 0.9,
    "contemplar": 0.9,
    "vislumbrar": 0.95,
    "avistar": 0.95,
    "divisar": 0.95,
    "atisbar": 0.95,
    "otear": 0.95,
    "distinguir": 0.7,
    "brillar": 0.9,
    "relucir": 0.95,
    "resplandecer": 0.95,
    "centellear": 0.95,
    "destellar": 0.95,
    "fulgurar": 0.95,
    "parpadear": 0.8,
    "pestañear": 0.8,
    "enfocar": 0.8,
    # Colores
    "rojo": 0.9,
    "azul": 0.9,
    "verde": 0.9,
    "amarillo": 0.9,
    "blanco": 0.85,
    "negro": 0.85,
    "gris": 0.85,
    "rosa": 0.85,
    "morado": 0.9,
    "violeta": 0.9,
    "naranja": 0.85,
    "marrón": 0.9,
    "dorado": 0.9,
    "plateado": 0.9,
    "carmesí": 0.95,
    "escarlata": 0.95,
    "púrpura": 0.95,
    "turquesa": 0.95,
    "esmeralda": 0.95,
    "ocre": 0.95,
    "ámbar": 0.95,
    "bermellón": 0.95,
    "índigo": 0.95,
    "cobalto": 0.95,
    # Luz y oscuridad
    "luz": 0.85,
    "sombra": 0.85,
    "oscuridad": 0.9,
    "penumbra": 0.95,
    "brillo": 0.9,
    "destello": 0.95,
    "resplandor": 0.95,
    "fulgor": 0.95,
    "luminosidad": 0.95,
    "tinieblas": 0.95,
    "claroscuro": 0.95,
    "reflejo": 0.85,
    "silueta": 0.9,
    # Adjetivos visuales
    "luminoso": 0.9,
    "oscuro": 0.85,
    "brillante": 0.9,
    "opaco": 0.9,
    "transparente": 0.9,
    "translúcido": 0.95,
    "nítido": 0.9,
    "borroso": 0.9,
    "difuso": 0.85,
    "vívido": 0.9,
    "pálido": 0.85,
    "intenso": 0.7,
    "radiante": 0.9,
    "tenue": 0.85,
    "sombrío": 0.9,
}

# Oído: verbos, adjetivos, sustantivos relacionados con oír
HEARING_KEYWORDS: dict[str, float] = {
    # Verbos
    "oír": 0.9,
    "escuchar": 0.9,
    "sonar": 0.9,
    "resonar": 0.95,
    "retumbar": 0.95,
    "tronar": 0.9,
    "murmurar": 0.9,
    "susurrar": 0.95,
    "gritar": 0.85,
    "aullar": 0.9,
    "rugir": 0.9,
    "silbar": 0.9,
    "zumbar": 0.95,
    "crujir": 0.95,
    "chirriar": 0.95,
    "chasquear": 0.95,
    "tintinear": 0.95,
    "repicar": 0.95,
    "cantar": 0.8,
    "tararear": 0.9,
    "gemir": 0.8,
    # Sustantivos
    "sonido": 0.9,
    "ruido": 0.9,
    "silencio": 0.85,
    "estruendo": 0.95,
    "estrépito": 0.95,
    "fragor": 0.95,
    "murmullo": 0.95,
    "susurro": 0.95,
    "grito": 0.85,
    "eco": 0.9,
    "melodía": 0.9,
    "música": 0.85,
    "rumor": 0.85,
    "aullido": 0.9,
    "rugido": 0.9,
    "chasquido": 0.95,
    "crujido": 0.95,
    "estallido": 0.9,
    "zumbido": 0.95,
    "campanada": 0.95,
    "trueno": 0.9,
    # Adjetivos
    "ruidoso": 0.9,
    "silencioso": 0.85,
    "estridente": 0.95,
    "atronador": 0.95,
    "ensordecedor": 0.95,
    "melodioso": 0.95,
    "chirriante": 0.95,
    "ronco": 0.85,
    "agudo": 0.7,
    "grave": 0.7,
    "sordo": 0.8,
    "gutural": 0.9,
}

# Tacto: verbos, adjetivos, sustantivos relacionados con tocar
TOUCH_KEYWORDS: dict[str, float] = {
    # Verbos
    "tocar": 0.85,
    "acariciar": 0.95,
    "rozar": 0.95,
    "palpar": 0.95,
    "frotar": 0.9,
    "rascar": 0.9,
    "apretar": 0.85,
    "estrechar": 0.8,
    "abrazar": 0.85,
    "pellizcar": 0.9,
    "arañar": 0.9,
    "masajear": 0.95,
    "temblar": 0.8,
    "estremecerse": 0.85,
    "tiritar": 0.9,
    # Temperatura
    "frío": 0.8,
    "calor": 0.8,
    "caliente": 0.85,
    "helado": 0.9,
    "tibio": 0.9,
    "templado": 0.85,
    "ardiente": 0.85,
    "gélido": 0.95,
    "cálido": 0.85,
    "fresco": 0.75,
    "abrasador": 0.95,
    "glacial": 0.95,
    # Texturas
    "suave": 0.8,
    "áspero": 0.9,
    "rugoso": 0.95,
    "liso": 0.85,
    "pegajoso": 0.9,
    "resbaladizo": 0.9,
    "aterciopelado": 0.95,
    "sedoso": 0.95,
    "granuloso": 0.95,
    "esponjoso": 0.95,
    "duro": 0.7,
    "blando": 0.8,
    "húmedo": 0.8,
    "seco": 0.7,
    "mojado": 0.8,
    "empapado": 0.85,
    "viscoso": 0.95,
    "punzante": 0.9,
    # Sustantivos
    "textura": 0.95,
    "tacto": 0.95,
    "caricia": 0.95,
    "roce": 0.95,
    "contacto": 0.8,
    "presión": 0.8,
    "escalofrío": 0.9,
    "hormigueo": 0.95,
    "cosquilleo": 0.95,
    "pinchazo": 0.9,
    "ardor": 0.85,
    "comezón": 0.95,
}

# Olfato: verbos, adjetivos, sustantivos relacionados con oler
SMELL_KEYWORDS: dict[str, float] = {
    # Verbos
    "oler": 0.95,
    "olfatear": 0.95,
    "husmear": 0.95,
    "aspirar": 0.7,
    "inhalar": 0.8,
    "apestar": 0.95,
    "perfumar": 0.95,
    "aromatizar": 0.95,
    "heder": 0.95,
    # Sustantivos
    "olor": 0.95,
    "aroma": 0.95,
    "fragancia": 0.95,
    "perfume": 0.9,
    "hedor": 0.95,
    "tufo": 0.95,
    "esencia": 0.8,
    "efluvio": 0.95,
    "emanación": 0.9,
    "fetidez": 0.95,
    "pestilencia": 0.95,
    "bocanada": 0.8,
    "vaharada": 0.95,
    "bouquet": 0.95,
    # Adjetivos
    "aromático": 0.95,
    "fragante": 0.95,
    "perfumado": 0.95,
    "apestoso": 0.95,
    "maloliente": 0.95,
    "fétido": 0.95,
    "pestilente": 0.95,
    "rancio": 0.9,
    "acre": 0.9,
    "oloroso": 0.95,
    "nauseabundo": 0.95,
    "almizclado": 0.95,
    # Olores específicos
    "incienso": 0.9,
    "alcanfor": 0.95,
    "azufre": 0.9,
}

# Gusto: verbos, adjetivos, sustantivos relacionados con saborear
TASTE_KEYWORDS: dict[str, float] = {
    # Verbos (infinitivo + conjugaciones comunes)
    "saborear": 0.95,
    "saboreó": 0.95,
    "saboreaba": 0.95,
    "degustar": 0.95,
    "degustó": 0.95,
    "degustaba": 0.95,
    "degustando": 0.95,
    "paladear": 0.95,
    "paladeó": 0.95,
    "paladeaba": 0.95,
    "probar": 0.7,
    "probó": 0.7,
    "probaba": 0.7,
    "catar": 0.95,
    "cató": 0.95,
    "cataba": 0.95,
    "tragar": 0.8,
    "tragó": 0.8,
    "tragaba": 0.8,
    "masticar": 0.85,
    "masticó": 0.85,
    "masticaba": 0.85,
    "morder": 0.8,
    "mordió": 0.8,
    "mordía": 0.8,
    "lamer": 0.9,
    "lamió": 0.9,
    "lamía": 0.9,
    "sorber": 0.85,
    "sorbió": 0.85,
    "sorbía": 0.85,
    "beber": 0.7,
    "bebió": 0.7,
    "bebía": 0.7,
    "comer": 0.6,
    "comió": 0.6,
    "comía": 0.6,
    # Sabores básicos
    "dulce": 0.85,
    "amargo": 0.85,
    "salado": 0.9,
    "ácido": 0.85,
    "agrio": 0.9,
    "picante": 0.9,
    "umami": 0.95,
    "insípido": 0.95,
    "soso": 0.85,
    # Adjetivos de sabor
    "sabroso": 0.9,
    "delicioso": 0.85,
    "empalagoso": 0.95,
    "agridulce": 0.95,
    "acre": 0.85,
    "rancio": 0.85,
    "nauseabundo": 0.8,
    "apetitoso": 0.9,
    "suculento": 0.95,
    "exquisito": 0.8,
    "jugoso": 0.9,
    "crujiente": 0.8,
    # Sustantivos
    "sabor": 0.95,
    "gusto": 0.85,
    "paladar": 0.95,
    "bocado": 0.85,
    "sorbo": 0.9,
    "trago": 0.8,
    "mordisco": 0.85,
    "degustación": 0.95,
}

# Mapa de sentidos a sus keywords
SENSE_KEYWORDS: dict[SensoryType, dict[str, float]] = {
    SensoryType.SIGHT: SIGHT_KEYWORDS,
    SensoryType.HEARING: HEARING_KEYWORDS,
    SensoryType.TOUCH: TOUCH_KEYWORDS,
    SensoryType.SMELL: SMELL_KEYWORDS,
    SensoryType.TASTE: TASTE_KEYWORDS,
}

# Exclusiones: palabras que parecen sensoriales pero tienen significado diferente
# Evita falsos positivos donde derivados morfológicos cambian el significado
#
# NOTA: Usamos tanto un set (para coincidencias exactas rápidas) como patrones
# regex (para variantes morfológicas). Los patrones son más genéricos y capturan
# la mayoría de casos; el set captura casos especiales que los patrones no cubren.


# Patrones regex para exclusiones genéricas (compilados para eficiencia)
# Estos capturan la mayoría de casos y son más mantenibles que listas exhaustivas
SENSE_EXCLUSION_PATTERNS: list[re.Pattern] = [
    # Cualquier forma de "gusto" precedida de artículo/preposición (no es sabor)
    re.compile(r"\b(con|de|a|mucho|tanto|sumo|buen|mal)\s+(mucho\s+)?gusto\b", re.IGNORECASE),
    # Formas de "gustos-" (placer, no sabor): gustoso, gustosa, gustosos, gustosas, gustosísimo, etc.
    re.compile(r"\bgustoso?s?a?s?\b", re.IGNORECASE),  # gustoso, gustosa, gustosos, gustosas
    re.compile(
        r"\bgustosísim[oa]s?\b", re.IGNORECASE
    ),  # gustosísimo, gustosísima, gustosísimos, gustosísimas
    # Formas de "gustosamente"
    re.compile(r"\bgustosamente\b", re.IGNORECASE),
    # Formas de "disgusto": disgustado, disgustada, a disgusto, etc.
    re.compile(r"\b(a\s+)?disgust[oaei]\w*\b", re.IGNORECASE),
]

# Set para casos especiales que los patrones no capturan bien
# Mantener mínimo - preferir patrones regex
SENSE_EXCLUSIONS: set[str] = {
    # Derivados de "delicioso" usados metafóricamente
    "deliciosamente",  # A menudo no-sensorial: "deliciosamente irónico"
    # "Exquisito" usado para describir modales/educación
    "exquisitez",
}

# Nombres en español de cada sentido
SENSE_NAMES: dict[SensoryType, str] = {
    SensoryType.SIGHT: "Vista",
    SensoryType.HEARING: "Oído",
    SensoryType.TOUCH: "Tacto",
    SensoryType.SMELL: "Olfato",
    SensoryType.TASTE: "Gusto",
}


# =============================================================================
# Analizador
# =============================================================================


class SensoryAnalyzer:
    """
    Analizador de detalles sensoriales en texto narrativo.

    Detecta referencias a los 5 sentidos y genera un reporte
    de distribución y densidad sensorial.
    """

    # Contexto alrededor de cada detalle detectado
    CONTEXT_WINDOW = 60

    # Umbrales de densidad (detalles por 1000 palabras)
    DENSITY_RICH = 15.0
    DENSITY_ADEQUATE = 5.0
    DENSITY_SPARSE = 1.0

    def __init__(self):
        # Pre-compilar patrones para cada sentido
        self._patterns: dict[SensoryType, list[tuple[re.Pattern, str, float]]] = {}

        for sense, keywords in SENSE_KEYWORDS.items():
            patterns = []
            for keyword, confidence in keywords.items():
                # Construir patrón que busque la palabra completa
                # Considerar variantes morfológicas básicas (plural, femenino)
                base = re.escape(keyword)
                pattern = re.compile(rf"\b{base}[aeiouáéíóús]{{0,3}}\b", re.IGNORECASE)
                patterns.append((pattern, keyword, confidence))
            self._patterns[sense] = patterns

    def analyze(
        self,
        text: str,
        chapters: list[dict] | None = None,
    ) -> Result["SensoryReport"]:
        """
        Analiza el texto para detectar detalles sensoriales.

        Args:
            text: Texto completo del documento
            chapters: Lista de capítulos con {number, title, start_char, end_char, content}

        Returns:
            Result[SensoryReport] con el reporte de análisis sensorial
        """
        try:
            if not text or not text.strip():
                return Result.success(SensoryReport())

            # Detectar detalles en el texto completo
            details = self._detect_details(text, chapters)

            # Calcular estadísticas globales
            word_count = len(text.split())
            report = SensoryReport(
                total_details=len(details),
                total_words=word_count,
                details=details,
            )

            # Distribución por sentido
            for detail in details:
                report.by_sense[detail.sense] = report.by_sense.get(detail.sense, 0) + 1

            # Calcular densidad global
            if word_count > 0:
                report.overall_density = (len(details) / word_count) * 1000
                report.overall_density_level = self._classify_density(report.overall_density)

            # Porcentajes por sentido
            if details:
                for sense in SensoryType:
                    count = report.by_sense.get(sense, 0)
                    report.sense_percentages[sense] = (count / len(details)) * 100

                # Sentido dominante y más débil
                sorted_senses = sorted(report.by_sense.items(), key=lambda x: x[1], reverse=True)
                report.dominant_sense = sorted_senses[0][0]
                report.weakest_sense = sorted_senses[-1][0]

                # Balance score (0-1, usando coeficiente de variación inverso)
                counts = [report.by_sense.get(s, 0) for s in SensoryType]
                mean = sum(counts) / len(counts) if counts else 0
                if mean > 0:
                    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
                    cv = (variance**0.5) / mean
                    # Convertir a score 0-1 (cv=0 -> 1.0, cv>=2 -> 0.0)
                    report.balance_score = max(0.0, 1.0 - cv / 2)

            # Estadísticas por capítulo
            if chapters:
                for chapter_data in chapters:
                    ch_num = chapter_data.get("number", chapter_data.get("chapter_number", 0))
                    ch_content = chapter_data.get("content", "")
                    ch_word_count = len(ch_content.split()) if ch_content else 0

                    ch_details = [d for d in details if d.chapter == ch_num]

                    stats = ChapterSensoryStats(
                        chapter=ch_num,
                        word_count=ch_word_count,
                        details_count=len(ch_details),
                    )

                    if ch_word_count > 0:
                        stats.density = (len(ch_details) / ch_word_count) * 1000
                        stats.density_level = self._classify_density(stats.density)

                    for d in ch_details:
                        stats.by_sense[d.sense] = stats.by_sense.get(d.sense, 0) + 1

                    # Sentido dominante del capítulo
                    ch_sorted = sorted(stats.by_sense.items(), key=lambda x: x[1], reverse=True)
                    if ch_sorted and ch_sorted[0][1] > 0:
                        stats.dominant_sense = ch_sorted[0][0]

                    # Sentidos ausentes
                    stats.missing_senses = [s for s, c in stats.by_sense.items() if c == 0]

                    report.chapter_stats.append(stats)

                    if (
                        stats.density_level == SensoryDensity.SPARSE
                        or stats.density_level == SensoryDensity.ABSENT
                    ):
                        report.sparse_chapters.append(ch_num)
                    elif stats.density_level == SensoryDensity.RICH:
                        report.rich_chapters.append(ch_num)

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error en análisis sensorial: {e}", exc_info=True)
            return Result.failure(
                NLPError(
                    message=f"Error en análisis sensorial: {e}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
            )

    def _detect_details(
        self,
        text: str,
        chapters: list[dict] | None = None,
    ) -> list[SensoryDetail]:
        """Detecta todos los detalles sensoriales en el texto."""
        details = []
        seen_positions: set[int] = set()

        # Construir mapa de capítulos por posición
        chapter_map: list[tuple[int, int, int]] = []
        if chapters:
            for ch in chapters:
                start = ch.get("start_char", 0)
                end = ch.get("end_char", len(text))
                num = ch.get("number", ch.get("chapter_number", 0))
                chapter_map.append((start, end, num))

        for sense, patterns in self._patterns.items():
            for pattern, keyword, confidence in patterns:
                for match in pattern.finditer(text):
                    pos = match.start()

                    # Evitar duplicados en la misma posición
                    if pos in seen_positions:
                        continue

                    # Filtrar palabras en la lista de exclusión (set)
                    matched_word = match.group(0).lower()
                    if matched_word in SENSE_EXCLUSIONS:
                        continue

                    # Verificar exclusiones usando patrones regex (más genéricos)
                    # Tomamos contexto para verificar frases como "con gusto", "a disgusto", etc.
                    ctx_start_excl = max(0, pos - 20)
                    ctx_end_excl = min(len(text), match.end() + 10)
                    context_for_exclusion = text[ctx_start_excl:ctx_end_excl].lower()

                    if any(
                        pattern.search(context_for_exclusion)
                        for pattern in SENSE_EXCLUSION_PATTERNS
                    ):
                        continue

                    seen_positions.add(pos)

                    # Extraer contexto
                    ctx_start = max(0, pos - self.CONTEXT_WINDOW)
                    ctx_end = min(len(text), match.end() + self.CONTEXT_WINDOW)
                    context = text[ctx_start:ctx_end].replace("\n", " ").strip()

                    # Determinar capítulo
                    chapter_num = None
                    if chapter_map:
                        for ch_start, ch_end, ch_num in chapter_map:
                            if ch_start <= pos < ch_end:
                                chapter_num = ch_num
                                break

                    detail = SensoryDetail(
                        sense=sense,
                        text=match.group(0),
                        context=context,
                        start_char=pos,
                        end_char=match.end(),
                        chapter=chapter_num,
                        keyword=keyword,
                        confidence=confidence,
                    )
                    details.append(detail)

        # Ordenar por posición
        details.sort(key=lambda d: d.start_char)
        return details

    def _classify_density(self, density: float) -> SensoryDensity:
        """Clasifica el nivel de densidad sensorial."""
        if density >= self.DENSITY_RICH:
            return SensoryDensity.RICH
        elif density >= self.DENSITY_ADEQUATE:
            return SensoryDensity.ADEQUATE
        elif density >= self.DENSITY_SPARSE:
            return SensoryDensity.SPARSE
        else:
            return SensoryDensity.ABSENT
