"""
Detector de extranjerismos (anglicismos y galicismos).

Identifica palabras extranjeras innecesarias que tienen equivalentes
en español, con contexto para evitar falsos positivos en:
- Términos técnicos aceptados
- Préstamos ya adaptados por la RAE
- Nombres propios

Soporta:
- Anglicismos (inglés)
- Galicismos (francés)
"""

import re
from typing import Optional

from ..base import BaseDetector, CorrectionIssue
from ..config import AnglicismsConfig
from ..types import CorrectionCategory

# Anglicismos crudos (sin adaptación, tienen equivalente español claro)
ANGLICISMS_RAW = {
    # Negocios/Marketing
    "feedback": ("retroalimentación", "comentarios", "respuesta"),
    "meeting": ("reunión",),
    "deadline": ("fecha límite", "plazo"),
    "target": ("objetivo", "meta"),
    "performance": ("rendimiento", "desempeño"),
    "briefing": ("informe", "resumen"),
    "brainstorming": ("lluvia de ideas",),
    "approach": ("enfoque", "aproximación"),
    "insight": ("percepción", "idea clave"),
    "mindset": ("mentalidad",),
    "skills": ("habilidades", "competencias"),
    "background": ("antecedentes", "experiencia", "trasfondo"),
    "manager": ("gerente", "responsable", "director"),
    "staff": ("personal", "equipo"),
    "business": ("negocio", "empresa"),
    "partner": ("socio",),
    "sponsor": ("patrocinador",),
    # Tecnología (con equivalentes claros)
    "link": ("enlace", "vínculo"),
    "click": ("clic", "pulsar"),
    "post": ("publicación", "entrada"),
    "online": ("en línea",),
    "offline": ("sin conexión", "desconectado"),
    "email": ("correo electrónico", "correo"),
    "password": ("contraseña",),
    "username": ("nombre de usuario",),
    "login": ("inicio de sesión", "acceso"),
    "logout": ("cierre de sesión", "salir"),
    "streaming": ("transmisión en directo", "emisión"),
    "download": ("descarga", "descargar"),
    "upload": ("subida", "subir", "carga"),
    "update": ("actualización", "actualizar"),
    "upgrade": ("mejora", "actualización"),
    "backup": ("copia de seguridad", "respaldo"),
    "mouse": ("ratón",),
    "smartphone": ("teléfono inteligente", "móvil"),
    "tablet": ("tableta",),
    "laptop": ("portátil", "ordenador portátil"),
    # Vida cotidiana
    "shopping": ("compras",),
    "parking": ("aparcamiento", "estacionamiento"),
    "sandwich": ("emparedado", "bocadillo"),
    "coffee break": ("pausa para el café", "descanso"),
    "after work": ("después del trabajo",),
    "happy hour": ("hora feliz",),
    "weekend": ("fin de semana",),
    "hobby": ("pasatiempo", "afición"),
    "look": ("aspecto", "imagen", "estilo"),
    "fashion": ("moda",),
    "trendy": ("de moda", "moderno"),
    "cool": ("genial", "estupendo", "guay"),
    "fake": ("falso", "falsificación"),
    "feeling": ("sensación", "sentimiento"),
    "relax": ("relajarse", "descanso"),
    # Medios/Entretenimiento
    "show": ("espectáculo", "programa"),
    "casting": ("audición", "selección"),
    "fan": ("aficionado", "seguidor"),
    "hit": ("éxito",),
    "ranking": ("clasificación", "lista"),
    "spoiler": ("adelanto", "revelación"),
    "celebrity": ("celebridad", "famoso"),
    "influencer": ("influyente", "creador de contenido"),
    "selfie": ("autofoto",),
    "hater": ("detractor",),
    "follower": ("seguidor",),
    "like": ("me gusta",),
    # Trabajo/Oficina
    "freelance": ("autónomo", "independiente"),
    "outsourcing": ("externalización", "subcontratación"),
    "networking": ("contactos profesionales", "red de contactos"),
    "workshop": ("taller",),
    "coworking": ("trabajo compartido", "oficina compartida"),
    "empowerment": ("empoderamiento",),
    "leadership": ("liderazgo",),
    "feedback loop": ("ciclo de retroalimentación",),
    # Otros
    "ok": ("de acuerdo", "bien", "vale"),
    "stop": ("alto", "parar", "detener"),
    "test": ("prueba", "examen"),
    "top": ("mejor", "principal", "máximo"),
    "boom": ("auge", "explosión"),
    "bypass": ("derivación", "rodeo"),
    "check": ("verificación", "comprobación"),
    "tip": ("consejo", "sugerencia", "propina"),
    "coach": ("entrenador", "preparador"),
    "coaching": ("entrenamiento", "asesoramiento"),
    "break": ("descanso", "pausa"),
}

# Anglicismos aceptados por la RAE (no alertar)
ACCEPTED_BY_RAE = {
    "software",
    "hardware",
    "internet",
    "web",
    "wifi",
    "blues",
    "jazz",
    "rock",
    "pop",
    "punk",
    "hip-hop",
    "rap",
    "club",
    "bar",
    "pub",
    "hotel",
    "motel",
    "film",
    "set",
    "best seller",
    "thriller",
    "marketing",
    "stock",
    "holding",
    "sprint",
    "golf",
    "tenis",
    "rugby",
    "fútbol",
    "camping",
    "rally",
    "karting",
    "whisky",
    "gin",
    "vodka",
    "brandy",
    "jean",
    "jeans",
    "jersey",
    "pullover",
    "express",
    "vip",
    "airbag",
    "stop",  # señales de tráfico
}

# Patrones morfológicos de anglicismos no adaptados
ANGLICISM_PATTERNS = [
    # Terminaciones inglesas comunes
    (r"\b\w+ing\b", "Posible anglicismo con terminación -ing"),
    (r"\b\w+er\b(?!\s+(de|del|que|y|en|a))", "Posible anglicismo con terminación -er"),
    (r"\b\w+ness\b", "Anglicismo con terminación -ness"),
    (r"\b\w+ment\b(?!e|o)", "Posible anglicismo con terminación -ment"),
]

# Palabras que parecen anglicismos pero son válidas en español
FALSE_POSITIVES = {
    # Palabras españolas que terminan en -ing
    "ring",
    "ping",
    "bing",  # onomatopeyas
    # Palabras que terminan en -er
    "taller",
    "mujer",
    "poder",
    "saber",
    "hacer",
    "querer",
    "ver",
    "comer",
    "beber",
    "correr",
    "ser",
    "tener",
    "volver",
    "poner",
    "caer",
    "traer",
    "leer",
    "creer",
    "poseer",
    "proveer",
    "ayer",
    "primer",
    "tercer",
    "cualquier",
    # Otras
    "internet",
    "club",
    "film",
    "pub",
    "bar",
}


# ============================================================================
# GALICISMOS (préstamos del francés)
# ============================================================================

# Galicismos crudos (sin adaptación, tienen equivalente español claro)
GALICISMS_RAW = {
    # Gastronomía
    "chef": ("cocinero", "jefe de cocina"),
    "gourmet": ("gastrónomo", "sibarita"),
    "restaurant": ("restaurante",),  # versión no adaptada
    "menu": ("menú", "carta"),  # sin acento
    "buffet": ("bufé",),
    "croissant": ("cruasán", "medialuna"),
    "brioche": ("bollo", "pan dulce"),
    "pâté": ("paté",),
    "soufflé": ("suflé",),
    "mousse": ("espuma", "crema batida"),
    "consommé": ("consomé",),
    "sauté": ("salteado",),
    "julienne": ("juliana",),
    "entrée": ("entrante", "primer plato"),
    "dessert": ("postre",),
    "sommelier": ("sumiller",),
    "maître": ("jefe de sala", "metre"),
    # Moda y estética
    "chic": ("elegante", "sofisticado"),
    "glamour": ("encanto", "atractivo"),
    "boutique": ("tienda", "tienda de moda"),
    "prêt-à-porter": ("confección", "ropa lista para usar"),
    "haute couture": ("alta costura",),
    "lingerie": ("lencería", "ropa interior"),
    "maquillage": ("maquillaje",),
    "coiffure": ("peinado",),
    "décolleté": ("escote",),
    "silhouette": ("silueta",),
    "parure": ("aderezo", "juego de joyas"),
    "bijou": ("joya", "alhaja"),
    # Arte y cultura
    "atelier": ("taller", "estudio"),
    "soirée": ("velada", "fiesta nocturna"),
    "matinée": ("matiné", "función de tarde"),
    "vernissage": ("inauguración", "apertura de exposición"),
    "avant-garde": ("vanguardia",),
    "oeuvre": ("obra",),
    "chef-d'oeuvre": ("obra maestra",),
    "genre": ("género",),
    "cliché": ("tópico", "lugar común"),
    "naïf": ("ingenuo", "naíf"),
    "blasé": ("hastiado", "desencantado"),
    "ennui": ("tedio", "hastío", "aburrimiento"),
    # Sociedad y comportamiento
    "savoir-faire": ("saber hacer", "habilidad"),
    "savoir-vivre": ("saber vivir", "buenas maneras"),
    "faux pas": ("metedura de pata", "error social"),
    "vis-à-vis": ("cara a cara", "frente a frente"),
    "tête-à-tête": ("conversación privada", "encuentro íntimo"),
    "rendez-vous": ("cita", "encuentro"),
    "coup de grâce": ("golpe de gracia",),
    "coup d'état": ("golpe de Estado",),
    "fait accompli": ("hecho consumado",),
    "laissez-faire": ("liberalismo económico", "dejar hacer"),
    "noblesse oblige": ("la nobleza obliga",),
    "raison d'être": ("razón de ser",),
    "joie de vivre": ("alegría de vivir",),
    "bon vivant": ("vividor", "sibarita"),
    "enfant terrible": ("niño terrible",),
    # Decoración e interiorismo
    "boudoir": ("tocador", "gabinete íntimo"),
    "chaise longue": ("diván", "tumbona"),
    "bidet": ("bidé",),
    "armoire": ("armario",),
    "toilette": ("tocador", "aseo"),
    "parquet": ("parqué", "entarimado"),
    "plafond": ("techo", "límite"),
    # Otros
    "ambiance": ("ambiente", "atmósfera"),
    "cachet": ("caché", "distinción"),
    "debut": ("debut", "estreno"),
    "detour": ("rodeo", "desvío"),
    "ensemble": ("conjunto",),
    "fiancé": ("prometido", "novio"),
    "fiancée": ("prometida", "novia"),
    "massage": ("masaje",),
    "ménage à trois": ("trío amoroso",),
    "penchant": ("inclinación", "tendencia"),
    "protégé": ("protegido", "pupilo"),
    "rapport": ("relación", "conexión"),
    "recherché": ("rebuscado", "exquisito"),
    "renaissance": ("renacimiento",),
    "résumé": ("currículum", "resumen"),
    "risqué": ("atrevido", "arriesgado"),
    "rôle": ("papel", "rol"),
    "rouge": ("colorete", "carmín"),
    "sabotage": ("sabotaje",),
    "touché": ("tocado",),
    "vogue": ("moda", "boga"),
}

# Galicismos aceptados o muy usados (no alertar)
GALICISMS_ACCEPTED = {
    "hotel",
    "restaurante",
    "menú",
    "café",
    "ballet",
    "debut",
    "fiesta",
    "gala",
    "garage",
    "garaje",
    "bulevar",
    "jardín",
    "chófer",
    "chofer",
    "carné",
    "carnet",
    "comité",
    "corsé",
    "dossier",
    "élite",
    "equipaje",
    "etiqueta",
    "pantalón",
    "paté",
    "suflé",
    "consomé",
    "bidé",
    "parqué",
    "rol",
    "matiné",
}

# Patrones morfológicos de galicismos
GALICISM_PATTERNS = [
    # Terminaciones francesas comunes
    (r"\b\w+age\b", "Posible galicismo con terminación -age"),
    (r"\b\w+eur\b", "Posible galicismo con terminación -eur"),
    (r"\b\w+euse\b", "Posible galicismo con terminación -euse"),
    (r"\b\w+ette\b", "Posible galicismo con terminación -ette"),
    (r"\b\w+oir\b", "Posible galicismo con terminación -oir"),
]

# Falsos positivos para galicismos
GALICISM_FALSE_POSITIVES = {
    # Palabras españolas comunes
    "equipaje",
    "personaje",
    "paisaje",
    "viaje",
    "linaje",
    "coraje",
    "mensaje",
    "lenguaje",
    "homenaje",
    "pasaje",
    "arbitraje",
    "hospedaje",
    "aterrizaje",
    "embalaje",
    "coqueta",
    "silueta",
    "maleta",
    "carreta",
    "paleta",
    "jinete",
    "banquete",
    "paquete",
    "raqueta",
    "cohete",
}


class AnglicismsDetector(BaseDetector):
    """
    Detector de extranjerismos (anglicismos y galicismos).

    Detecta palabras en inglés y francés que tienen equivalentes en español,
    diferenciando entre:
    - Extranjerismos crudos evitables
    - Préstamos aceptados por la RAE
    - Términos técnicos necesarios

    Soporta:
    - Anglicismos (inglés): habilitado por defecto
    - Galicismos (francés): configurable via check_galicisms
    """

    def __init__(self, config: Optional["AnglicismsConfig"] = None):
        self.config = config or AnglicismsConfig()
        self._compiled_anglicism_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc) for pattern, desc in ANGLICISM_PATTERNS
        ]
        self._compiled_galicism_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc) for pattern, desc in GALICISM_PATTERNS
        ]

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.ANGLICISMS

    @property
    def requires_spacy(self) -> bool:
        return False  # Funciona con regex, spaCy es opcional

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        spacy_doc=None,
        **kwargs,
    ) -> list[CorrectionIssue]:
        """
        Detecta extranjerismos en el texto (anglicismos y galicismos).

        Args:
            text: Texto a analizar
            chapter_index: Índice del capítulo
            spacy_doc: Documento spaCy (opcional, mejora precisión)

        Returns:
            Lista de CorrectionIssue encontrados
        """
        if not self.config.enabled:
            return []

        issues: list[CorrectionIssue] = []

        # Detectar anglicismos del diccionario
        issues.extend(self._detect_dictionary_anglicisms(text, chapter_index))

        # Detectar patrones morfológicos de anglicismos (si está habilitado)
        if self.config.check_morphological:
            issues.extend(self._detect_pattern_anglicisms(text, chapter_index))

        # Detectar galicismos (si está habilitado)
        if getattr(self.config, "check_galicisms", False):
            issues.extend(self._detect_dictionary_galicisms(text, chapter_index))
            if self.config.check_morphological:
                issues.extend(self._detect_pattern_galicisms(text, chapter_index))

        return issues

    def _detect_dictionary_anglicisms(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta anglicismos del diccionario."""
        issues = []
        text.lower()

        for anglicism, alternatives in ANGLICISMS_RAW.items():
            # Buscar el anglicismo (case insensitive, palabra completa)
            pattern = re.compile(r"\b" + re.escape(anglicism) + r"\b", re.IGNORECASE)

            for match in pattern.finditer(text):
                # Verificar contexto para falsos positivos
                if self._is_false_positive(text, match.start(), match.end()):
                    continue

                original_text = match.group()
                start = match.start()
                end = match.end()

                # Crear sugerencia con alternativas
                if len(alternatives) == 1:
                    suggestion = alternatives[0]
                    explanation = (
                        f'"{original_text}" es un anglicismo. '
                        f'Considere usar "{suggestion}" en español.'
                    )
                else:
                    suggestion = alternatives[0]
                    explanation = (
                        f'"{original_text}" es un anglicismo. '
                        f"Alternativas en español: {', '.join(alternatives)}."
                    )

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type="raw_anglicism",
                        start_char=start,
                        end_char=end,
                        text=original_text,
                        explanation=explanation,
                        suggestion=suggestion,
                        confidence=self.config.base_confidence,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id=f"anglicism_{anglicism}",
                        extra_data={
                            "anglicism": anglicism,
                            "alternatives": alternatives,
                        },
                    )
                )

        return issues

    def _detect_pattern_anglicisms(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta anglicismos por patrones morfológicos."""
        issues = []

        for pattern, description in self._compiled_anglicism_patterns:
            for match in pattern.finditer(text):
                word = match.group().lower()

                # Filtrar falsos positivos
                if word in FALSE_POSITIVES:
                    continue
                if word in ACCEPTED_BY_RAE:
                    continue
                if word in ANGLICISMS_RAW:
                    continue  # Ya detectado arriba

                # Verificar que no es nombre propio (empieza con mayúscula después de espacio)
                if match.start() > 0 and text[match.start()].isupper():
                    prev_char = text[match.start() - 1]
                    if prev_char not in ".!?¿¡":  # No es inicio de oración
                        continue

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type="morphological_anglicism",
                        start_char=match.start(),
                        end_char=match.end(),
                        text=match.group(),
                        explanation=description,
                        suggestion=None,  # No tenemos sugerencia automática
                        confidence=self.config.base_confidence * 0.7,  # Menor confianza
                        context=self._extract_context(text, match.start(), match.end()),
                        chapter_index=chapter_index,
                        rule_id="pattern_anglicism",
                        extra_data={"pattern_type": description},
                    )
                )

        return issues

    def _is_false_positive(self, text: str, start: int, end: int) -> bool:
        """Verifica si es un falso positivo basándose en contexto."""
        word = text[start:end].lower()

        # Palabras aceptadas
        if word in ACCEPTED_BY_RAE:
            return True
        if word in FALSE_POSITIVES:
            return True

        # Verificar si está entre comillas (probablemente intencional)
        before = text[max(0, start - 10) : start]
        after = text[end : min(len(text), end + 10)]
        if '"' in before and '"' in after:
            return True
        if "«" in before and "»" in after:
            return True

        # Verificar si es parte de nombre propio (ej: "John Smith")
        return bool(start > 0 and text[start - 1] not in " \n\t.!?¿¡")

    # ========================================================================
    # GALICISMOS
    # ========================================================================

    def _detect_dictionary_galicisms(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta galicismos del diccionario."""
        issues = []

        for galicism, alternatives in GALICISMS_RAW.items():
            # Buscar el galicismo (case insensitive, palabra completa)
            pattern = re.compile(r"\b" + re.escape(galicism) + r"\b", re.IGNORECASE)

            for match in pattern.finditer(text):
                # Verificar contexto para falsos positivos
                if self._is_galicism_false_positive(text, match.start(), match.end()):
                    continue

                original_text = match.group()
                start = match.start()
                end = match.end()

                # Crear sugerencia con alternativas
                if len(alternatives) == 1:
                    suggestion = alternatives[0]
                    explanation = (
                        f'"{original_text}" es un galicismo. '
                        f'Considere usar "{suggestion}" en español.'
                    )
                else:
                    suggestion = alternatives[0]
                    explanation = (
                        f'"{original_text}" es un galicismo. '
                        f"Alternativas en español: {', '.join(alternatives)}."
                    )

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type="raw_galicism",
                        start_char=start,
                        end_char=end,
                        text=original_text,
                        explanation=explanation,
                        suggestion=suggestion,
                        confidence=self.config.base_confidence,
                        context=self._extract_context(text, start, end),
                        chapter_index=chapter_index,
                        rule_id=f"galicism_{galicism}",
                        extra_data={
                            "galicism": galicism,
                            "alternatives": alternatives,
                            "language": "french",
                        },
                    )
                )

        return issues

    def _detect_pattern_galicisms(
        self, text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta galicismos por patrones morfológicos."""
        issues = []

        for pattern, description in self._compiled_galicism_patterns:
            for match in pattern.finditer(text):
                word = match.group().lower()

                # Filtrar falsos positivos
                if word in GALICISM_FALSE_POSITIVES:
                    continue
                if word in GALICISMS_ACCEPTED:
                    continue
                if word in GALICISMS_RAW:
                    continue  # Ya detectado arriba

                # Verificar que no es nombre propio
                if match.start() > 0 and text[match.start()].isupper():
                    prev_char = text[match.start() - 1]
                    if prev_char not in ".!?¿¡":
                        continue

                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type="morphological_galicism",
                        start_char=match.start(),
                        end_char=match.end(),
                        text=match.group(),
                        explanation=description,
                        suggestion=None,
                        confidence=self.config.base_confidence * 0.6,  # Menor confianza
                        context=self._extract_context(text, match.start(), match.end()),
                        chapter_index=chapter_index,
                        rule_id="pattern_galicism",
                        extra_data={
                            "pattern_type": description,
                            "language": "french",
                        },
                    )
                )

        return issues

    def _is_galicism_false_positive(self, text: str, start: int, end: int) -> bool:
        """Verifica si es un falso positivo para galicismos."""
        word = text[start:end].lower()

        # Palabras aceptadas
        if word in GALICISMS_ACCEPTED:
            return True
        if word in GALICISM_FALSE_POSITIVES:
            return True

        # Verificar si está entre comillas
        before = text[max(0, start - 10) : start]
        after = text[end : min(len(text), end + 10)]
        if '"' in before and '"' in after:
            return True
        if "«" in before and "»" in after:
            return True

        # Verificar si es parte de nombre propio
        return bool(start > 0 and text[start - 1] not in " \n\t.!?¿¡")
