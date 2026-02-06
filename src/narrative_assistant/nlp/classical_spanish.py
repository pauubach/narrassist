"""
Modo español clásico (Siglo de Oro).

Adapta el procesamiento NLP para manejar textos del español de los
siglos XV-XVII (Cervantes, Lope de Vega, Calderón, Quevedo, etc.):
- Variantes ortográficas históricas
- Vocabulario arcaico
- Conjugaciones verbales antiguas
- Formas de tratamiento clásicas
- Títulos nobiliarios de la época

Uso: Se activa como preprocessor antes del pipeline NLP, normalizando
el texto para que spaCy y los modelos transformer puedan procesarlo.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClassicalNormalization:
    """Resultado de la normalización de español clásico."""

    original: str
    normalized: str
    replacements: list[tuple[str, str, int]] = field(default_factory=list)
    # (original, replacement, position)
    detected_period: str = ""  # "siglo_de_oro", "medieval", etc.
    confidence: float = 0.0


# Variantes ortográficas históricas → forma moderna
ORTHOGRAPHIC_VARIANTS: list[tuple[str, str]] = [
    # Consonantes
    (r"\bvuestra\s+merced\b", "usted"),
    (r"\bvuessa\s+merced\b", "usted"),
    (r"\bvuesamerced\b", "usted"),
    (r"\bvoacé\b", "usted"),
    # x → j (antes de vocal) - incluye raíz + conjugaciones comunes
    (r"\bdixo\b", "dijo"),
    (r"\btruxo\b", "trajo"),
    (r"\bdexar\b", "dejar"),
    (r"\bdexó\b", "dejó"),
    (r"\bdexaría\b", "dejaría"),
    (r"\bdexaba\b", "dejaba"),
    (r"\bdexando\b", "dejando"),
    (r"\bbaxar\b", "bajar"),
    (r"\bbaxó\b", "bajó"),
    (r"\bbaxaría\b", "bajaría"),
    (r"\brelox\b", "reloj"),
    (r"\bcaxón\b", "cajón"),
    (r"\bxamás\b", "jamás"),
    # ss → s - incluye raíz + conjugaciones
    (r"\bpassar\b", "pasar"),
    (r"\bpassó\b", "pasó"),
    (r"\bpassaría\b", "pasaría"),
    (r"\bpassaba\b", "pasaba"),
    (r"\bpassando\b", "pasando"),
    (r"\bassí\b", "así"),
    (r"\bpudiesse\b", "pudiese"),
    (r"\bdixesse\b", "dijese"),
    (r"\bfuesse\b", "fuese"),
    (r"\bquisiesse\b", "quisiese"),
    (r"\bhiziesse\b", "hiciese"),
    # f → h (arcaísmo medieval persistente)
    (r"\bfijo\b", "hijo"),
    (r"\bfazer\b", "hacer"),
    (r"\bfecho\b", "hecho"),
    (r"\bfermoso\b", "hermoso"),
    (r"\bfambre\b", "hambre"),
    (r"\bfallar\b", "hallar"),
    (r"\bfasta\b", "hasta"),
    # Otros cambios
    (r"\bagora\b", "ahora"),
    (r"\bansí\b", "así"),
    (r"\bansimismo\b", "asimismo"),
    (r"\baquesta\b", "esta"),
    (r"\baqueste\b", "este"),
    (r"\baquestos\b", "estos"),
    (r"\baquestas\b", "estas"),
    (r"\bdo\b", "donde"),
    (r"\bescuro\b", "oscuro"),
    (r"\bmesmo\b", "mismo"),
    (r"\bmesma\b", "misma"),
    (r"\bnadie\b", "nadie"),  # ya moderno, incluido por completitud
    (r"\bnaide\b", "nadie"),
    (r"\bpriesa\b", "prisa"),
    (r"\brecelar\b", "recelar"),
    (r"\bvueso\b", "vuestro"),
    (r"\bvuesa\b", "vuestra"),
    # y/i alternancia
    (r"\byo\b", "yo"),  # ya moderno
    (r"\bhay\b", "hay"),
    # Contracciones arcaicas
    (r"\bdel\b", "del"),
    (r"\bdeste\b", "de este"),
    (r"\bdesta\b", "de esta"),
    (r"\bdestos\b", "de estos"),
    (r"\bdestas\b", "de estas"),
    (r"\bdél\b", "de él"),
    (r"\bdella\b", "de ella"),
    (r"\bdellos\b", "de ellos"),
    (r"\bdellas\b", "de ellas"),
    (r"\bestotro\b", "este otro"),
    (r"\besotra\b", "esa otra"),
]

# Vocabulario arcaico → equivalente moderno
ARCHAIC_VOCABULARY: dict[str, str] = {
    # Sustantivos
    "alguacil": "agente",
    "aljaba": "carcaj",
    "aposento": "habitación",
    "ardid": "estratagema",
    "ayo": "tutor",
    "botica": "farmacia",
    "buhonero": "vendedor ambulante",
    "celada": "emboscada",
    "desaguisado": "agravio",
    "escudero": "sirviente noble",
    "faltriquera": "bolsillo",
    "ganapán": "mozo de cuerda",
    "hidalgo": "hidalgo",
    "maese": "maestro",
    "mancebo": "joven",
    "mesonero": "posadero",
    "paje": "sirviente joven",
    "yantar": "comida",
    "zagal": "muchacho pastor",
    "zurrón": "bolsa de cuero",
    # Verbos
    "acaecer": "suceder",
    "asaz": "bastante",
    "atañer": "concernir",
    "departir": "conversar",
    "holgar": "descansar",
    "menester": "necesidad",
    "platicar": "conversar",
    "plugo": "agradó",
    "yantar": "comer",
    # Adjetivos/Adverbios
    "antaño": "antiguamente",
    "asaz": "bastante",
    "magüer": "aunque",
    "otrora": "en otro tiempo",
    "recio": "fuerte",
    "apriesa": "deprisa",
    "luengo": "largo",
    # Interjecciones
    "pardiez": "por Dios",
    "vive Dios": "por Dios",
    "válame Dios": "Dios mío",
    "a fe mía": "de verdad",
}

# Formas de tratamiento y títulos de la época
CLASSICAL_TITLES: dict[str, str] = {
    "vuestra merced": "usted",
    "vuessa merced": "usted",
    "vuesamerced": "usted",
    "su excelencia": "excelencia",
    "su ilustrísima": "ilustrísima",
    "su señoría": "señoría",
    "vuestra majestad": "majestad",
    "vuestra alteza": "alteza",
    "vuestra señoría": "señoría",
    "vuestra excelencia": "excelencia",
    "vuestra reverencia": "reverencia",
    "su merced": "usted",
}

# Conjugaciones arcaicas → modernas
ARCHAIC_CONJUGATIONS: list[tuple[str, str]] = [
    # Segunda persona plural (vos → tú)
    (r"\btenéis\b", "tenéis"),  # Se mantiene
    (r"\bhabéis\b", "habéis"),
    (r"\bsois\b", "sois"),
    (r"\bestáis\b", "estáis"),
    # Formas con -ades, -edes, -ides (medievales)
    (r"\b(\w+)ades\b", r"\1áis"),
    (r"\b(\w+)edes\b", r"\1éis"),
    (r"\b(\w+)ides\b", r"\1ís"),
    # Imperativo con -d (medieval: dezid → decid)
    (r"\bdezid\b", "decid"),
    (r"\bfazed\b", "haced"),
    (r"\bvení\b", "venid"),
    # Futuro sintético con pronombre intercalado
    # "deciros he" → "os diré" (complejo, solo detectar)
]

# Patrones para detectar si un texto es español clásico
CLASSICAL_MARKERS = [
    r"\bvuestra\s+merced\b",
    r"\bdixo\b",
    r"\bassí\b",
    r"\bfermoso\b",
    r"\bmenester\b",
    r"\bholgar\b",
    r"\bdeste\b",
    r"\baquesta\b",
    r"\bmaese\b",
    r"\bhidalgo\b",
    r"\bescudero\b",
    r"\baposento\b",
    r"\bpardiez\b",
    r"\bvuessa\b",
    r"\bpassar\b",
    r"\bpriesa\b",
    r"\bagora\b",
]


class ClassicalSpanishNormalizer:
    """
    Normaliza textos de español clásico para mejorar el procesamiento NLP.

    El texto original se preserva para presentación al usuario;
    la versión normalizada se usa internamente por spaCy/transformer.
    """

    def __init__(self):
        # Compilar patrones
        self._ortho_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in ORTHOGRAPHIC_VARIANTS
        ]
        self._conjugation_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in ARCHAIC_CONJUGATIONS
        ]
        self._marker_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in CLASSICAL_MARKERS
        ]

    def is_classical(self, text: str, threshold: int = 3) -> bool:
        """
        Determina si un texto parece ser español clásico.

        Args:
            text: Texto a analizar (primeros ~2000 caracteres bastan)
            threshold: Número mínimo de marcadores para considerar clásico

        Returns:
            True si el texto tiene suficientes marcadores de español clásico.
        """
        sample = text[:2000].lower()
        matches = sum(
            1 for pattern in self._marker_patterns
            if pattern.search(sample)
        )
        return matches >= threshold

    def detect_period(self, text: str) -> str:
        """
        Detecta el periodo aproximado del texto.

        Returns:
            "medieval" (< 1500), "siglo_de_oro" (1500-1700),
            "ilustracion" (1700-1800), "moderno" (> 1800)
        """
        sample = text[:3000].lower()

        # Indicadores medievales (f→h, -ades, etc.)
        medieval_markers = [
            r"\bfazer\b", r"\bfermoso\b", r"\bfasta\b", r"\bmagüer\b",
            r"\bfijo\b", r"\bfecho\b", r"\bfambre\b", r"\bfallar\b",
        ]
        medieval_count = sum(
            1 for p in medieval_markers
            if re.search(p, sample, re.IGNORECASE)
        )

        # Indicadores Siglo de Oro (vuestra merced, dixo, passó, etc.)
        golden_markers = [
            r"\bvuestra\s+merced\b", r"\bdixo\b", r"\bpassar\b", r"\basaz\b",
            r"\bdexar\b", r"\bdexó\b", r"\bdexaría\b", r"\bpassó\b", r"\bpassaría\b",
        ]
        golden_count = sum(
            1 for p in golden_markers
            if re.search(p, sample, re.IGNORECASE)
        )

        if medieval_count >= 2:
            return "medieval"
        if golden_count >= 2 or self.is_classical(text, threshold=3):
            return "siglo_de_oro"

        return "moderno"

    def normalize(self, text: str) -> ClassicalNormalization:
        """
        Normaliza texto de español clásico a español moderno.

        El texto original se preserva; la versión normalizada se usa
        para procesamiento NLP.

        Args:
            text: Texto en español clásico.

        Returns:
            ClassicalNormalization con texto original y normalizado.
        """
        result = ClassicalNormalization(
            original=text,
            normalized=text,
        )

        if not text:
            return result

        # Detectar periodo
        result.detected_period = self.detect_period(text)

        if result.detected_period == "moderno":
            result.confidence = 0.1
            return result

        normalized = text
        replacements = []

        # 1. Normalización ortográfica
        for pattern, replacement in self._ortho_patterns:
            for match in pattern.finditer(normalized):
                if match.group().lower() != replacement.lower():
                    replacements.append((match.group(), replacement, match.start()))
            normalized = pattern.sub(replacement, normalized)

        # 2. Normalización de conjugaciones
        for pattern, replacement in self._conjugation_patterns:
            for match in pattern.finditer(normalized):
                replaced = pattern.sub(replacement, match.group())
                if match.group() != replaced:
                    replacements.append((match.group(), replaced, match.start()))
            normalized = pattern.sub(replacement, normalized)

        result.normalized = normalized
        result.replacements = replacements
        result.confidence = min(0.95, 0.3 + len(replacements) * 0.05)

        logger.info(
            f"Normalización español clásico ({result.detected_period}): "
            f"{len(replacements)} reemplazos"
        )

        return result

    def get_archaic_glossary(self, text: str) -> dict[str, str]:
        """
        Genera un glosario de palabras arcaicas encontradas en el texto.

        Returns:
            Dict de palabra arcaica → significado moderno.
        """
        glossary = {}
        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        for archaic, modern in ARCHAIC_VOCABULARY.items():
            if archaic in words:
                glossary[archaic] = modern

        return glossary
