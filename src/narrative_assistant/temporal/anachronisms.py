"""
Detección de anacronismos en textos narrativos.

Detecta menciones a tecnologías, objetos, eventos o conceptos que no
corresponden a la época en la que se ambienta la narración.

Ejemplo: Un personaje en la España del siglo XVI usando un teléfono móvil.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Anachronism:
    """Un anacronismo detectado en el texto."""

    term: str  # Término anacrónico encontrado
    context: str  # Fragmento de texto donde aparece
    position: int  # Posición en el texto
    earliest_year: int  # Año más temprano en que el concepto existe
    category: str  # Categoría (tecnología, transporte, etc.)
    confidence: float  # Confianza de la detección (0-1)
    narrative_year: int | None = None  # Año narrativo estimado


@dataclass
class AnachronismReport:
    """Resultado del análisis de anacronismos."""

    anachronisms: list[Anachronism] = field(default_factory=list)
    narrative_period: str = ""  # Época detectada (ej: "siglo XVI")
    estimated_year_range: tuple[int, int] | None = None


# Base de datos de tecnologías/conceptos con su año de aparición
# Organizada por categorías para facilitar mantenimiento
TECHNOLOGY_DB: dict[str, list[tuple[str, int]]] = {
    "comunicaciones": [
        (r"\bteléfono(?:s)?\b", 1876),
        (r"\bteléfono(?:s)?\s+móvil(?:es)?\b", 1983),
        (r"\bmóvil(?:es)?\b", 1983),
        (r"\bsmartphone(?:s)?\b", 2007),
        (r"\bcelu?lar(?:es)?\b", 1983),
        (r"\btelegrama(?:s)?\b", 1844),
        (r"\btelégrafo(?:s)?\b", 1837),
        (r"\bradio(?:s)?\b", 1895),
        (r"\btelevisión\b", 1927),
        (r"\btelevisor(?:es)?\b", 1927),
        (r"\binternet\b", 1991),
        (r"\bcorreo\s+electrónico\b", 1971),
        (r"\be-?mail(?:s)?\b", 1971),
        (r"\bwhatsapp\b", 2009),
        (r"\bredes\s+sociales\b", 2004),
        (r"\bfacebook\b", 2004),
        (r"\btwitter\b", 2006),
        (r"\binstagram\b", 2010),
        (r"\bwifi\b", 1997),
        (r"\bbluetooth\b", 1998),
    ],
    "transporte": [
        (r"\bautomóvil(?:es)?\b", 1886),
        (r"\bcoche(?:s)?\b", 1886),  # Nota: "coche" también = carruaje (pre-1886)
        (r"\bcarro(?:s)?\b", 1886),  # En Latam = auto
        (r"\bavión(?:es)?\b", 1903),
        (r"\bavioneta(?:s)?\b", 1903),
        (r"\bhelicóptero(?:s)?\b", 1936),
        (r"\btren(?:es)?\b", 1825),
        (r"\bferrocarril(?:es)?\b", 1825),
        (r"\bmetro\b", 1863),
        (r"\bmotocicleta(?:s)?\b", 1885),
        (r"\bmoto(?:s)?\b", 1885),
        (r"\bbicicleta(?:s)?\b", 1817),
        (r"\bsubmarino(?:s)?\b", 1620),  # Concepto, práctico ~1880
        (r"\bcohete(?:s)?\s+espacial(?:es)?\b", 1942),
    ],
    "iluminacion_energia": [
        (r"\bbombilla(?:s)?\b", 1879),
        (r"\bluz\s+eléctrica\b", 1879),
        (r"\belectricidad\b", 1752),  # Concepto; distribución ~1882
        (r"\bcentral\s+(?:eléctrica|nuclear)\b", 1882),
        (r"\benergía\s+nuclear\b", 1942),
        (r"\bplaca(?:s)?\s+solar(?:es)?\b", 1954),
    ],
    "medicina": [
        (r"\bantibiótico(?:s)?\b", 1928),
        (r"\bpenicilina\b", 1928),
        (r"\bvacuna(?:s)?\b", 1796),
        (r"\banestesia\b", 1846),
        (r"\brasografía\b", 1895),
        (r"\bradioterapia\b", 1903),
        (r"\btrasplante(?:s)?\b", 1954),
        (r"\bADN\b", 1953),
    ],
    "informatica": [
        (r"\bordenador(?:es)?\b", 1946),
        (r"\bcomputador(?:a|es)?\b", 1946),
        (r"\bportátil(?:es)?\b", 1981),
        (r"\blaptop(?:s)?\b", 1981),
        (r"\btablet(?:s|a|as)?\b", 2010),
        (r"\biPad(?:s)?\b", 2010),
        (r"\bpágina(?:s)?\s+web\b", 1991),
        (r"\bsitio(?:s)?\s+web\b", 1991),
        (r"\bbuscador(?:es)?\b", 1993),
        (r"\bGoogle\b", 1998),
        (r"\binteligencia\s+artificial\b", 1956),
        (r"\brobot(?:s)?\b", 1920),  # Término acuñado por Čapek
        (r"\bsoftware\b", 1958),
        (r"\bhacker(?:s)?\b", 1960),
        (r"\bvideojuego(?:s)?\b", 1958),
    ],
    "armas": [
        (r"\bpólvora\b", 850),  # China, llega a Europa ~1300
        (r"\bfusil(?:es)?\b", 1610),
        (r"\bpistola(?:s)?\b", 1540),
        (r"\bametralladora(?:s)?\b", 1862),
        (r"\btanque(?:s)?\s+(?:de\s+guerra|militar(?:es)?|blindado(?:s)?)\b", 1916),
        (r"\bbomba(?:s)?\s+atómica(?:s)?\b", 1945),
        (r"\bbomba(?:s)?\s+nuclear(?:es)?\b", 1945),
        (r"\bmisil(?:es)?\b", 1944),
        (r"\bsubfusil(?:es)?\b", 1918),
    ],
    "cotidiano": [
        (r"\bgafas?\s+de\s+sol\b", 1929),
        (r"\breloj(?:es)?\s+de\s+pulsera\b", 1868),
        (r"\bascensor(?:es)?\b", 1853),
        (r"\bcremallera(?:s)?\b", 1913),
        (r"\bbolígrafo(?:s)?\b", 1938),
        (r"\bfotografía(?:s)?\b", 1826),
        (r"\bcámara(?:s)?\s+fotográfica(?:s)?\b", 1826),
        (r"\bcámara(?:s)?\s+de\s+fotos\b", 1826),
        (r"\bcigarrillo(?:s)?\b", 1832),  # Industrialización
        (r"\bperiódico(?:s)?\b", 1605),
    ],
}

# Patrones para detectar la época de la narración
EPOCH_PATTERNS: list[tuple[str, int, int]] = [
    # Siglos específicos
    (r"\bsiglo\s+I\b", 1, 100),
    (r"\bsiglo\s+II\b", 101, 200),
    (r"\bsiglo\s+III\b", 201, 300),
    (r"\bsiglo\s+IV\b", 301, 400),
    (r"\bsiglo\s+V\b", 401, 500),
    (r"\bsiglo\s+VI\b", 501, 600),
    (r"\bsiglo\s+VII\b", 601, 700),
    (r"\bsiglo\s+VIII\b", 701, 800),
    (r"\bsiglo\s+IX\b", 801, 900),
    (r"\bsiglo\s+X\b", 901, 1000),
    (r"\bsiglo\s+XI\b", 1001, 1100),
    (r"\bsiglo\s+XII\b", 1101, 1200),
    (r"\bsiglo\s+XIII\b", 1201, 1300),
    (r"\bsiglo\s+XIV\b", 1301, 1400),
    (r"\bsiglo\s+XV\b", 1401, 1500),
    (r"\bsiglo\s+XVI\b", 1501, 1600),
    (r"\bsiglo\s+XVII\b", 1601, 1700),
    (r"\bsiglo\s+XVIII\b", 1701, 1800),
    (r"\bsiglo\s+XIX\b", 1801, 1900),
    (r"\bsiglo\s+XX\b", 1901, 2000),
    (r"\bsiglo\s+XXI\b", 2001, 2100),
    # Épocas históricas españolas
    (r"\bReconquista\b", 722, 1492),
    (r"\bSiglo\s+de\s+Oro\b", 1492, 1681),
    (r"\bGuerra\s+Civil\b", 1936, 1939),
    (r"\bposguerra\b", 1939, 1959),
    (r"\bfranquismo\b", 1939, 1975),
    (r"\btransición\b", 1975, 1982),
    (r"\bEdad\s+Media\b", 476, 1453),
    (r"\bRenacimiento\b", 1400, 1600),
    (r"\bIlustración\b", 1685, 1815),
    # Años explícitos
    (r"\ben\s+(?:el\s+año\s+)?(\d{3,4})\b", 0, 0),  # Especial: se extrae del match
]


class AnachronismDetector:
    """Detecta anacronismos comparando tecnologías con la época narrativa."""

    def __init__(self):
        # Compilar patrones para eficiencia
        self._compiled_techs: list[tuple[re.Pattern, int, str]] = []
        for category, items in TECHNOLOGY_DB.items():
            for pattern_str, year in items:
                self._compiled_techs.append(
                    (re.compile(pattern_str, re.IGNORECASE), year, category)
                )

        self._compiled_epochs: list[tuple[re.Pattern, int, int]] = []
        for pattern_str, start, end in EPOCH_PATTERNS:
            self._compiled_epochs.append(
                (re.compile(pattern_str, re.IGNORECASE), start, end)
            )

    def detect_narrative_period(self, text: str) -> tuple[int, int] | None:
        """
        Detecta el periodo temporal de la narración.

        Returns:
            Tupla (año_inicio, año_fin) o None si no se puede determinar.
        """
        periods_found: list[tuple[int, int]] = []

        for pattern, start_year, end_year in self._compiled_epochs:
            match = pattern.search(text)
            if match:
                if start_year == 0 and end_year == 0:
                    # Patrón de año explícito: extraer del grupo
                    try:
                        year = int(match.group(1))
                        periods_found.append((year - 10, year + 10))
                    except (IndexError, ValueError):
                        continue
                else:
                    periods_found.append((start_year, end_year))

        if not periods_found:
            return None

        # Usar la intersección o el periodo más específico
        if len(periods_found) == 1:
            return periods_found[0]

        # Múltiples indicadores: usar el más restrictivo (menor rango)
        periods_found.sort(key=lambda p: p[1] - p[0])
        return periods_found[0]

    def detect(self, text: str, year_range: tuple[int, int] | None = None) -> AnachronismReport:
        """
        Detecta anacronismos en el texto.

        Args:
            text: Texto a analizar.
            year_range: Rango de años de la narración. Si None, se intenta detectar.

        Returns:
            AnachronismReport con los anacronismos encontrados.
        """
        report = AnachronismReport()

        # Detectar periodo si no se proporciona
        if year_range is None:
            year_range = self.detect_narrative_period(text)

        if year_range is None:
            return report  # No podemos detectar anacronismos sin época

        report.estimated_year_range = year_range
        report.narrative_period = f"{year_range[0]}-{year_range[1]}"
        narrative_end = year_range[1]

        # Buscar tecnologías que no existían en la época
        for pattern, earliest_year, category in self._compiled_techs:
            if earliest_year <= narrative_end:
                continue  # La tecnología ya existía en la época

            for match in pattern.finditer(text):
                # Extraer contexto
                ctx_start = max(0, match.start() - 50)
                ctx_end = min(len(text), match.end() + 50)
                context = text[ctx_start:ctx_end]

                # Confianza basada en cuán anacrónico es
                years_diff = earliest_year - narrative_end
                if years_diff > 200:
                    confidence = 0.95
                elif years_diff > 50:
                    confidence = 0.85
                else:
                    confidence = 0.7

                report.anachronisms.append(
                    Anachronism(
                        term=match.group(),
                        context=context,
                        position=match.start(),
                        earliest_year=earliest_year,
                        category=category,
                        confidence=confidence,
                        narrative_year=narrative_end,
                    )
                )

        # Ordenar por posición
        report.anachronisms.sort(key=lambda a: a.position)

        if report.anachronisms:
            logger.info(
                f"Detectados {len(report.anachronisms)} posibles anacronismos "
                f"para periodo {report.narrative_period}"
            )

        return report
