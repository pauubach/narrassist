"""
Preprocesador de títulos para spaCy.

El problema: Los títulos de capítulos (ej: "1: El Despertar") causan errores en el
análisis de dependencias de spaCy cuando se combinan directamente con la siguiente
oración. El parser confunde la estructura sintáctica.

Solución: Separar títulos y analizarlos por separado, luego recombinar los resultados.

Estrategia:
1. Detectar líneas que son títulos (patrones, longitud, ausencia de verbo principal)
2. Separar el contenido narrativo
3. Procesar cada párrafo de contenido independientemente
4. Recombinar resultados manteniendo posiciones originales

Uso:
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)

    for para in processed.paragraphs:
        print(f"Título: {para.is_title}, Contenido: {para.text}")
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Iterator

logger = logging.getLogger(__name__)


class TitleType(Enum):
    """Tipo de título detectado."""
    CHAPTER_NUMBERED = "chapter_numbered"      # "1: El Despertar", "Capítulo 1"
    CHAPTER_TITLED = "chapter_titled"          # Título sin número
    SCENE_SEPARATOR = "scene_separator"        # "* * *", "---"
    SECTION = "section"                        # Subnivel de capítulo
    UNKNOWN = "unknown"                        # Línea corta, probablemente título


@dataclass
class ProcessedParagraph:
    """
    Párrafo después del preprocesamiento.

    Attributes:
        text: Contenido del párrafo
        is_title: Si es un título
        title_type: Tipo de título (si aplica)
        original_start: Posición en el texto original
        original_end: Posición final en el texto original
        confidence: Confianza de que es un título (0.0 - 1.0)
    """
    text: str
    is_title: bool
    title_type: Optional[TitleType] = None
    original_start: int = 0
    original_end: int = 0
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """Número de palabras en el párrafo."""
        return len(self.text.split())

    @property
    def char_count(self) -> int:
        """Número de caracteres."""
        return len(self.text)


@dataclass
class ProcessedDocument:
    """
    Documento después del preprocesamiento.

    Attributes:
        paragraphs: Lista de párrafos procesados
        original_text: Texto original
        title_count: Número de títulos detectados
        content_count: Número de párrafos de contenido
    """
    paragraphs: list[ProcessedParagraph] = field(default_factory=list)
    original_text: str = ""
    title_count: int = 0
    content_count: int = 0

    def get_content_text(self) -> str:
        """Retorna solo el contenido (sin títulos)."""
        return "\n\n".join(
            p.text for p in self.paragraphs if not p.is_title
        )

    def get_titles(self) -> list[ProcessedParagraph]:
        """Retorna solo los títulos."""
        return [p for p in self.paragraphs if p.is_title]

    def get_content(self) -> list[ProcessedParagraph]:
        """Retorna solo el contenido."""
        return [p for p in self.paragraphs if not p.is_title]


class TitleDetector:
    """
    Detecta si una línea es un título basado en múltiples heurísticas.

    Heurísticas:
    1. Patrones explícitos (número: título, Capítulo N, etc.)
    2. Longitud corta (< 50 palabras, típicamente < 10)
    3. Ausencia de verbo conjugado (no es oración completa)
    4. No termina en puntuación de oración (. ! ?)
    5. Mayúscula al inicio (patrón de título)
    """

    # Patrones de títulos explícitos
    CHAPTER_PATTERNS = [
        # "1: El Despertar", "1 - El Despertar"
        r"^(\d{1,3})\s*[\:\.\-—]\s*(.+)$",
        # Números romanos: "I: El Despertar"
        r"^([IVXLCDM]+)\s*[\:\.\-—]\s*(.+)$",
        # "Capítulo 1", "CAPÍTULO 1", "Capitulo 1"
        r"^Cap[íi]tulo\s+(\d+|[IVXLCDM]+)(?:\s*[\:\.\-—]\s*(.+))?$",
        r"^CAPÍTULO\s+(\d+|[IVXLCDM]+)(?:\s*[\:\.\-—]\s*(.+))?$",
        # "Cap. 1"
        r"^Cap\.\s*(\d+)(?:\s*[\:\.\-—]\s*(.+))?$",
        # Inglés
        r"^Chapter\s+(\d+|[IVXLCDM]+)(?:\s*[\:\.\-—]\s*(.+))?$",
        r"^CHAPTER\s+(\d+|[IVXLCDM]+)(?:\s*[\:\.\-—]\s*(.+))?$",
    ]

    SECTION_PATTERNS = [
        # "2.1 Título de sección"
        r"^(\d+\.\d+)\s*[\:\.\-—]\s*(.+)$",
        # "Sección 1", "SECCIÓN 1"
        r"^[Ss]ección\s+(\d+)(?:\s*[\:\.\-—]\s*(.+))?$",
    ]

    SCENE_PATTERNS = [
        r"^\*\s*\*\s*\*\s*$",        # * * *
        r"^\*{3,}\s*$",              # ***
        r"^-{3,}\s*$",               # ---
        r"^_{3,}\s*$",               # ___
        r"^#{3,}\s*$",               # ###
        r"^~{3,}\s*$",               # ~~~
        r"^=={2,}\s*$",              # ===
    ]

    def __init__(self, max_title_length: int = 200):
        """
        Inicializa el detector.

        Args:
            max_title_length: Máximo de caracteres para considerar una línea como título
        """
        self.max_title_length = max_title_length

        # Compilar patrones
        self.chapter_patterns = [re.compile(p, re.IGNORECASE) for p in self.CHAPTER_PATTERNS]
        self.section_patterns = [re.compile(p, re.IGNORECASE) for p in self.SECTION_PATTERNS]
        self.scene_patterns = [re.compile(p) for p in self.SCENE_PATTERNS]

    def detect(self, text: str) -> tuple[bool, Optional[TitleType], float]:
        """
        Detecta si una línea es un título.

        Returns:
            (is_title, title_type, confidence)
        """
        text = text.strip()

        if not text:
            return False, None, 0.0

        # 1. Patrones explícitos (máxima confianza)
        for pattern in self.chapter_patterns:
            if pattern.match(text):
                return True, TitleType.CHAPTER_NUMBERED, 1.0

        for pattern in self.section_patterns:
            if pattern.match(text):
                return True, TitleType.SECTION, 1.0

        for pattern in self.scene_patterns:
            if pattern.match(text):
                return True, TitleType.SCENE_SEPARATOR, 1.0

        # 2. Heurísticas
        confidence = 0.0

        # H1: Longitud muy corta (< 50 palabras)
        word_count = len(text.split())
        if word_count <= 15:
            confidence += 0.3
        elif word_count <= 30:
            confidence += 0.15
        else:
            # Párrafos muy largos no son títulos
            return False, None, 0.0

        # H2: Longitud en caracteres (típicos títulos < 100 caracteres)
        char_count = len(text)
        if char_count < 50:
            confidence += 0.25
        elif char_count < 100:
            confidence += 0.1
        elif char_count > self.max_title_length:
            # Muy largo para ser título
            return False, None, 0.0

        # H3: Ausencia de verbo conjugado
        if not self._has_conjugated_verb(text):
            confidence += 0.25

        # H4: No termina en puntuación de fin de oración (típico en títulos)
        if text[-1] not in '.!?':
            confidence += 0.1

        # H5: Empieza en mayúscula (patrón de título)
        if text[0].isupper():
            confidence += 0.05

        # H6: Contiene estructuras de título (dos puntos, guiones)
        if ':' in text or '—' in text or ' - ' in text:
            confidence += 0.15

        # Determine title type based on heuristics
        title_type = TitleType.UNKNOWN if confidence > 0.5 else None
        is_title = confidence > 0.5

        return is_title, title_type, confidence

    def _has_conjugated_verb(self, text: str) -> bool:
        """
        Detecta si el texto contiene un verbo conjugado.

        Búsqueda simple basada en patrones comunes en español.
        Esto es una heurística, no análisis sintáctico completo.
        """
        # Verbos comunes conjugados en tiempo presente/pasado
        # Esta es una lista pequeña para velocidad; en producción usar spaCy
        verb_endings = [
            r'\b(soy|eres|es|somos|sois|son)\b',           # ser
            r'\b(estoy|estás|está|estamos|estáis|están)\b', # estar
            r'\b(tengo|tienes|tiene|tenemos|tenéis|tienen)\b', # tener
            r'\b(hago|haces|hace|hacemos|hacéis|hacen)\b',  # hacer
            r'\b(digo|dices|dice|decimos|decís|dicen)\b',   # decir
            r'\b(voy|vas|va|vamos|vais|van)\b',             # ir
            r'\b(vengo|vienes|viene|venimos|venís|vienen)\b', # venir
            r'\b(puedo|puedes|puede|podemos|podéis|pueden)\b', # poder
            r'\b(quiero|quieres|quiere|queremos|queréis|quieren)\b', # querer
            r'\b(debo|debes|debe|debemos|debéis|deben)\b',  # deber
            r'\b(veo|ves|ve|vemos|veis|ven)\b',             # ver
            r'\b(conozco|conoces|conoce|conocemos|conocéis|conocen)\b', # conocer
            r'\b(pienso|piensas|piensa|pensamos|pensáis|piensan)\b', # pensar
            r'\b(siento|sientes|siente|sentimos|sentís|sienten)\b', # sentir
            r'\b(llego|llegas|llega|llegamos|llegáis|llegan)\b', # llegar
            r'\b(dije|dijiste|dijo|dijimos|dijisteis|dijeron)\b', # decir pasado
            r'\b(fue|fuiste|fue|fuimos|fuisteis|fueron)\b',  # ir/ser pasado
            r'\b(era|eras|era|éramos|erais|eran)\b',        # ser imperfecto
            r'\b(estaba|estabas|estaba|estábamos|estabais|estaban)\b', # estar imperfecto
            # Terminaciones comunes de verbos conjugados
            r'\b\w+(aba|aban|ábamos|abais|ada|adas|ado|ados|ada|adas)$', # -ar imperfecto/pasado
            r'\b\w+(ía|ían|íamos|íais)$',                    # -ir/-er imperfecto
            r'\b\w+(é|aste|ó|amos|asteis|aron)$',           # -ar pretérito
        ]

        text_lower = text.lower()
        for pattern in verb_endings:
            if re.search(pattern, text_lower):
                return True

        return False


class TitlePreprocessor:
    """
    Preprocesador de títulos para spaCy.

    Separa títulos del contenido narrativo para evitar que spaCy
    intente analizar estructuras sintácticas incorrectas.

    Uso:
        preprocessor = TitlePreprocessor()
        processed = preprocessor.process(text)

        for para in processed.paragraphs:
            if para.is_title:
                print(f"[TÍTULO] {para.text}")
            else:
                print(f"[CONTENIDO] {para.text}")
    """

    def __init__(self, max_title_length: int = 200):
        """
        Inicializa el preprocesador.

        Args:
            max_title_length: Máximo de caracteres para un título
        """
        self.detector = TitleDetector(max_title_length)
        self.max_title_length = max_title_length

    def process(self, text: str) -> ProcessedDocument:
        """
        Procesa un texto y separa títulos del contenido.

        Args:
            text: Texto a procesar

        Returns:
            ProcessedDocument con párrafos clasificados
        """
        processed = ProcessedDocument(original_text=text)

        # Dividir en párrafos (múltiples saltos de línea)
        paragraphs = re.split(r'\n\n+', text)

        current_pos = 0
        for para_text in paragraphs:
            # Encontrar posición en el texto original
            start_pos = text.find(para_text, current_pos)
            end_pos = start_pos + len(para_text)
            current_pos = end_pos

            # Detectar si es título
            is_title, title_type, confidence = self.detector.detect(para_text)

            proc_para = ProcessedParagraph(
                text=para_text,
                is_title=is_title,
                title_type=title_type,
                original_start=start_pos,
                original_end=end_pos,
                confidence=confidence,
            )

            processed.paragraphs.append(proc_para)

            if is_title:
                processed.title_count += 1
            else:
                processed.content_count += 1

        logger.debug(
            f"Preprocesamiento completado: {processed.title_count} títulos, "
            f"{processed.content_count} párrafos de contenido"
        )

        return processed

    def separate_content_for_spacy(self, text: str) -> list[str]:
        """
        Procesa un texto y retorna lista de párrafos listos para spaCy.

        Cada elemento de la lista es un párrafo de contenido sin títulos,
        con separaciones claras entre párrafos.

        Args:
            text: Texto a procesar

        Returns:
            Lista de párrafos de contenido
        """
        processed = self.process(text)
        return processed.get_content_text().split('\n\n')

    def process_with_context(
        self,
        text: str,
        preserve_titles: bool = False
    ) -> Iterator[ProcessedParagraph]:
        """
        Procesa un texto y genera párrafos uno a uno.

        Permite iterar sobre los párrafos y procesar con contexto.

        Args:
            text: Texto a procesar
            preserve_titles: Si False, filtra títulos

        Yields:
            ProcessedParagraph
        """
        processed = self.process(text)

        for para in processed.paragraphs:
            if preserve_titles or not para.is_title:
                yield para


# =============================================================================
# Funciones de conveniencia
# =============================================================================


def is_title(text: str, max_length: int = 200) -> bool:
    """
    Detecta rápidamente si una línea es un título.

    Args:
        text: Línea a verificar
        max_length: Máximo de caracteres para considerar

    Returns:
        True si es probablemente un título
    """
    detector = TitleDetector(max_length)
    is_t, _, _ = detector.detect(text)
    return is_t


def preprocess_text_for_spacy(text: str) -> str:
    """
    Preprocesa un texto para spaCy, eliminando títulos.

    Args:
        text: Texto a preprocesar

    Returns:
        Texto sin títulos, listo para spaCy
    """
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)
    return processed.get_content_text()


def split_by_titles(text: str) -> dict:
    """
    Divide un texto en títulos y contenido.

    Args:
        text: Texto a dividir

    Returns:
        Dict con 'titles' y 'content'
    """
    preprocessor = TitlePreprocessor()
    processed = preprocessor.process(text)

    return {
        'titles': processed.get_titles(),
        'content': processed.get_content(),
        'total_paragraphs': len(processed.paragraphs),
    }
