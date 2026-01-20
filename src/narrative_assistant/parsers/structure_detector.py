"""
Detector de estructura narrativa.

Detecta capítulos y escenas en documentos usando:
1. Estilos de Word (Heading 1, Heading 2, etc.) - más fiable
2. Patrones regex (Capítulo 1, CAPÍTULO I, etc.) - fallback
3. Separadores de escena (* * *, ---, ###, etc.)

El detector es configurable para adaptarse a diferentes convenciones
de formato de manuscrito.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from .base import RawDocument, RawParagraph

logger = logging.getLogger(__name__)


class StructureType(Enum):
    """Tipo de elemento estructural."""

    CHAPTER = "chapter"
    SCENE = "scene"
    PART = "part"  # Partes (agrupan capítulos)
    PROLOGUE = "prologue"
    EPILOGUE = "epilogue"
    INTERLUDE = "interlude"


# =============================================================================
# Patrones de detección
# =============================================================================

# Patrones para detectar inicio de capítulo (case insensitive)
# NOTA: Los patrones deben ser flexibles para capturar variaciones comunes:
# - Con o sin número: "Capítulo 1", "Capítulo Uno", "Capítulo Primero"
# - Con título: "Capítulo 1: El comienzo", "Capítulo 1 - El comienzo"
# - Solo título de capítulo: "1. El comienzo" (con punto)
# - Variantes sin tilde: "Capitulo" (sin tilde en 'i')
CHAPTER_PATTERNS = [
    # Español con número arábigo
    r"^Cap[íi]tulo\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
    r"^CAP[ÍI]TULO\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
    r"^Cap\.?\s*(\d+)(?:\s*[:\.\-—]\s*(.+))?$",
    # Con número escrito: "Capítulo Uno", "Capítulo Primero"
    r"^Cap[íi]tulo\s+(uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|primero|segundo|tercero|cuarto|quinto|sexto|séptimo|octavo|noveno|décimo)(?:\s*[:\.\-—]\s*(.+))?$",
    # Inglés (para manuscritos en inglés)
    r"^Chapter\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
    r"^CHAPTER\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
    # Solo número seguido de punto y título (muy común)
    # "1. El comienzo" o "1 - El comienzo"
    r"^(\d{1,3})\s*[:\.\-—]\s*([A-ZÁÉÍÓÚÑ].*)$",
    # Solo número (menos fiable, requiere contexto)
    r"^(\d{1,3})\s*$",
    # Solo número romano
    r"^([IVXLCDM]+)\s*$",
    # Solo número romano con punto
    r"^([IVXLCDM]+)\s*\.\s*(.+)?$",
]

# Patrones para prólogo/epílogo
PROLOGUE_PATTERNS = [
    r"^Prólogo\s*$",
    r"^PRÓLOGO\s*$",
    r"^Prologue\s*$",
    r"^PROLOGUE\s*$",
]

EPILOGUE_PATTERNS = [
    r"^Epílogo\s*$",
    r"^EPÍLOGO\s*$",
    r"^Epilogue\s*$",
    r"^EPILOGUE\s*$",
]

# Patrones para partes
PART_PATTERNS = [
    r"^Parte\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
    r"^PARTE\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
    r"^Part\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$",
]

# Patrones para separadores de escena
SCENE_SEPARATOR_PATTERNS = [
    r"^\*\s*\*\s*\*\s*$",  # * * *
    r"^\*{3,}\s*$",  # ***
    r"^-{3,}\s*$",  # ---
    r"^#{3,}\s*$",  # ###
    r"^~{3,}\s*$",  # ~~~
    r"^[•·]{3,}\s*$",  # •••
    # NOTA: Líneas vacías múltiples se detectan con patrón especial abajo
]

# Patrón para múltiples líneas vacías consecutivas (separador de escena)
BLANK_LINES_SCENE_PATTERN = r"\n{3,}"  # 3+ saltos de línea consecutivos

# Constantes para valores mágicos
EPILOGUE_NUMBER = 999
MIN_SCENE_CHARS = 10
AVG_CHARS_PER_WORD = 5


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class Section:
    """
    Sección dentro de un capítulo.

    Representa subniveles estructurales (H2, H3, H4, etc.) dentro de un capítulo.
    Pueden anidarse jerárquicamente.

    Attributes:
        number: Número de sección dentro del capítulo (1-indexed)
        title: Título de la sección
        heading_level: Nivel del heading (2 para H2, 3 para H3, etc.)
        start_char: Posición de inicio en el texto del documento
        end_char: Posición de fin en el texto del documento
        subsections: Subsecciones anidadas (nivel inferior)
    """

    number: int
    title: str
    heading_level: int
    start_char: int
    end_char: int
    subsections: list["Section"] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        """Número de caracteres en la sección."""
        return self.end_char - self.start_char

    def get_text(self, full_text: str) -> str:
        """Extrae el texto de la sección del documento completo."""
        return full_text[self.start_char : self.end_char]

    def to_dict(self) -> dict:
        """Convierte la sección a diccionario."""
        return {
            "number": self.number,
            "title": self.title,
            "heading_level": self.heading_level,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": self.char_count,
            "subsections": [s.to_dict() for s in self.subsections],
        }


@dataclass
class Scene:
    """
    Escena dentro de un capítulo.

    Una escena es una unidad narrativa continua, separada de otras
    por marcadores visuales (* * *, ---, etc.) o cambios de escenario.

    Attributes:
        number: Número de escena dentro del capítulo (1-indexed)
        start_char: Posición de inicio en el texto del documento
        end_char: Posición de fin en el texto del documento
        text: Texto de la escena (lazy, se calcula si se necesita)
    """

    number: int
    start_char: int
    end_char: int
    separator_type: Optional[str] = None  # Tipo de separador que la precede

    @property
    def char_count(self) -> int:
        """Número de caracteres en la escena."""
        return self.end_char - self.start_char

    def get_text(self, full_text: str) -> str:
        """Extrae el texto de la escena del documento completo."""
        return full_text[self.start_char : self.end_char]


@dataclass
class Chapter:
    """
    Capítulo del documento.

    Attributes:
        number: Número del capítulo (1-indexed, o 0 para prólogo)
        title: Título del capítulo (puede ser None)
        start_char: Posición de inicio en el texto del documento
        end_char: Posición de fin en el texto del documento
        scenes: Lista de escenas dentro del capítulo
        sections: Lista de secciones (subniveles H2, H3, etc.)
        structure_type: Tipo (chapter, prologue, epilogue, etc.)
        heading_level: Nivel del heading en Word (1-6) si aplica
        detected_by: Método de detección ("style", "pattern", "heuristic")
    """

    number: int
    title: Optional[str]
    start_char: int
    end_char: int
    scenes: list[Scene] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    structure_type: StructureType = StructureType.CHAPTER
    heading_level: Optional[int] = None
    detected_by: str = "pattern"

    @property
    def char_count(self) -> int:
        """Número de caracteres en el capítulo."""
        return self.end_char - self.start_char

    @property
    def scene_count(self) -> int:
        """Número de escenas en el capítulo."""
        return len(self.scenes)

    @property
    def section_count(self) -> int:
        """Número de secciones directas en el capítulo."""
        return len(self.sections)

    def get_all_sections(self) -> list[Section]:
        """Retorna todas las secciones incluyendo subsecciones anidadas."""
        all_sections = []
        for section in self.sections:
            all_sections.append(section)
            all_sections.extend(self._get_nested_sections(section))
        return all_sections

    def _get_nested_sections(self, section: Section) -> list[Section]:
        """Recursivamente obtiene todas las subsecciones."""
        nested = []
        for sub in section.subsections:
            nested.append(sub)
            nested.extend(self._get_nested_sections(sub))
        return nested

    def get_text(self, full_text: str, include_title: bool = False) -> str:
        """
        Extrae el texto del capítulo del documento completo.

        Args:
            full_text: Texto completo del documento
            include_title: Si True, incluye la primera línea (título). Por defecto False.

        Returns:
            Texto del capítulo, opcionalmente sin la primera línea del título
        """
        chapter_text = full_text[self.start_char : self.end_char]

        if include_title:
            return chapter_text

        # Excluir la primera línea (título del capítulo) del contenido
        first_newline = chapter_text.find('\n')
        if first_newline == -1:
            # Solo hay una línea (el título), retornar vacío
            return ""

        # Saltar la primera línea y cualquier línea vacía siguiente
        content = chapter_text[first_newline:].lstrip('\n')
        return content


@dataclass
class DocumentStructure:
    """
    Estructura completa del documento.

    Attributes:
        chapters: Lista de capítulos detectados
        total_scenes: Total de escenas en todo el documento
        detection_method: Método principal usado ("style", "pattern", "mixed")
        warnings: Advertencias durante la detección
    """

    chapters: list[Chapter] = field(default_factory=list)
    detection_method: str = "unknown"
    warnings: list[str] = field(default_factory=list)

    @property
    def total_scenes(self) -> int:
        """Total de escenas en el documento."""
        return sum(c.scene_count for c in self.chapters)

    @property
    def chapter_count(self) -> int:
        """Número de capítulos."""
        return len(self.chapters)

    def get_chapter(self, number: int) -> Optional[Chapter]:
        """Obtiene un capítulo por número."""
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None

    def add_warning(self, message: str) -> None:
        """Añade una advertencia."""
        self.warnings.append(message)
        logger.warning(f"StructureDetector: {message}")


@dataclass
class StructureDetectionError(NarrativeError):
    """Error durante la detección de estructura."""

    document_path: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        self.message = f"Structure detection error: {self.original_error}"
        self.user_message = (
            "Error al detectar la estructura del documento. "
            "Se continuará tratando el documento como un solo capítulo."
        )
        super().__post_init__()


# =============================================================================
# Detector
# =============================================================================


class StructureDetector:
    """
    Detector de estructura narrativa.

    Detecta capítulos y escenas usando estilos de Word y/o patrones regex.

    Uso:
        detector = StructureDetector()
        result = detector.detect(parsed_document)
        for chapter in result.chapters:
            print(f"Capítulo {chapter.number}: {chapter.title}")
    """

    def __init__(
        self,
        prefer_styles: bool = True,
        detect_scenes: bool = True,
        min_chapter_words: int = 100,
        custom_chapter_patterns: Optional[list[str]] = None,
        custom_scene_patterns: Optional[list[str]] = None,
    ):
        """
        Inicializa el detector.

        Args:
            prefer_styles: Preferir estilos de Word sobre patrones regex
            detect_scenes: Detectar escenas dentro de capítulos
            min_chapter_words: Mínimo de palabras para considerar un capítulo válido
            custom_chapter_patterns: Patrones adicionales para capítulos
            custom_scene_patterns: Patrones adicionales para escenas
        """
        self.prefer_styles = prefer_styles
        self.detect_scenes = detect_scenes
        self.min_chapter_words = min_chapter_words

        # Compilar patrones
        self.chapter_patterns = [re.compile(p, re.IGNORECASE) for p in CHAPTER_PATTERNS]
        self.prologue_patterns = [re.compile(p, re.IGNORECASE) for p in PROLOGUE_PATTERNS]
        self.epilogue_patterns = [re.compile(p, re.IGNORECASE) for p in EPILOGUE_PATTERNS]
        self.part_patterns = [re.compile(p, re.IGNORECASE) for p in PART_PATTERNS]
        self.scene_patterns = [re.compile(p, re.MULTILINE) for p in SCENE_SEPARATOR_PATTERNS]
        # Añadir patrón para múltiples líneas vacías (separador de escena común)
        self.scene_patterns.append(re.compile(BLANK_LINES_SCENE_PATTERN))

        # Añadir patrones custom
        if custom_chapter_patterns:
            self.chapter_patterns.extend(
                re.compile(p, re.IGNORECASE) for p in custom_chapter_patterns
            )
        if custom_scene_patterns:
            self.scene_patterns.extend(
                re.compile(p, re.MULTILINE) for p in custom_scene_patterns
            )

        logger.debug(
            f"StructureDetector inicializado "
            f"(styles={prefer_styles}, scenes={detect_scenes})"
        )

    def detect(self, document: RawDocument) -> Result[DocumentStructure]:
        """
        Detecta la estructura del documento.

        Args:
            document: Documento parseado

        Returns:
            Result con DocumentStructure
        """
        structure = DocumentStructure()

        if not document.paragraphs:
            structure.add_warning("Documento sin párrafos")
            return Result.success(structure)

        try:
            # 1. Intentar detectar por estilos de Word
            if self.prefer_styles:
                chapters = self._detect_by_styles(document)
                if chapters:
                    structure.chapters = chapters
                    structure.detection_method = "style"
                    logger.debug(f"Detectados {len(chapters)} capítulos por estilos")

            # 2. Si no hay capítulos por estilos, usar patrones
            if not structure.chapters:
                chapters = self._detect_by_patterns(document)
                if chapters:
                    structure.chapters = chapters
                    structure.detection_method = "pattern"
                    logger.debug(f"Detectados {len(chapters)} capítulos por patrones")

            # 3. Si aún no hay capítulos, crear uno con todo el documento
            if not structure.chapters:
                structure.chapters = [self._create_single_chapter(document)]
                structure.detection_method = "fallback"
                structure.add_warning(
                    "No se detectaron capítulos. El documento se trata como un solo capítulo."
                )

            # 4. Detectar secciones (subniveles) dentro de cada capítulo
            self._detect_sections_in_chapters(document, structure.chapters)

            # 5. Detectar escenas dentro de cada capítulo
            if self.detect_scenes:
                full_text = document.full_text
                for chapter in structure.chapters:
                    chapter.scenes = self._detect_scenes_in_chapter(chapter, full_text)

            # 6. Validar estructura
            self._validate_structure(structure)

            logger.info(
                f"Estructura detectada: {structure.chapter_count} capítulos, "
                f"{structure.total_scenes} escenas (método: {structure.detection_method})"
            )

            return Result.success(structure)

        except Exception as e:
            error = StructureDetectionError(
                document_path=str(document.source_path) if document.source_path else "",
                original_error=str(e),
            )
            # Crear estructura mínima como fallback
            structure.chapters = [self._create_single_chapter(document)]
            structure.detection_method = "error_fallback"
            return Result.partial(structure, [error])

    def _detect_by_styles(self, document: RawDocument) -> list[Chapter]:
        """Detecta capítulos usando estilos de Word."""
        chapters: list[Chapter] = []

        # Filtrar párrafos que son headings
        # IMPORTANTE: Excluir párrafos marcados como "is_chapter_title" (son títulos
        # de capítulo, no marcadores de capítulo), párrafos vacíos, y párrafos
        # con start_char=-1 (no tienen posición válida en el documento)
        headings = [
            p for p in document.paragraphs
            if p.is_heading
            and p.heading_level
            and not p.metadata.get("is_chapter_title")
            and p.text.strip()
            and p.start_char >= 0
        ]

        if not headings:
            # También buscar párrafos con estilo que contenga "Heading" o "Título"
            # aunque no estén marcados como is_heading (bug en algunos DOCX)
            for p in document.paragraphs:
                if p.metadata.get("is_chapter_title") or not p.text.strip() or p.start_char < 0:
                    continue
                style = p.style_name.lower() if p.style_name else ""
                if any(s in style for s in ("heading", "título", "titulo", "chapter", "capítulo")):
                    if p.heading_level is None:
                        # Inferir nivel del nombre del estilo
                        match = re.search(r'(\d)', p.style_name)
                        p.heading_level = int(match.group(1)) if match else 1
                        p.is_heading = True
                        headings.append(p)

        if not headings:
            return chapters

        # Determinar el nivel principal de capítulos
        # (asumimos que el nivel más alto usado es para capítulos)
        min_level = min(h.heading_level for h in headings if h.heading_level)

        chapter_headings = [h for h in headings if h.heading_level == min_level]

        for i, heading in enumerate(chapter_headings):
            # Calcular fin del capítulo
            if i + 1 < len(chapter_headings):
                end_char = chapter_headings[i + 1].start_char
            else:
                end_char = self._get_document_end(document)

            # Detectar tipo y número
            struct_type, number, title = self._parse_chapter_heading(
                heading.text, i + 1
            )

            # Usar título del metadata si está disponible (detectado por docx_parser)
            if heading.metadata.get("chapter_title"):
                title = heading.metadata["chapter_title"]

            # Usar número del metadata si está disponible
            if heading.metadata.get("chapter_number"):
                number = heading.metadata["chapter_number"]

            chapter = Chapter(
                number=number,
                title=title,
                start_char=heading.start_char,
                end_char=end_char,
                structure_type=struct_type,
                heading_level=heading.heading_level,
                detected_by="style",
            )
            chapters.append(chapter)

        return chapters

    def _detect_by_patterns(self, document: RawDocument) -> list[Chapter]:
        """Detecta capítulos usando patrones regex."""
        chapters: list[Chapter] = []
        chapter_paragraphs: list[tuple[RawParagraph, StructureType, int, Optional[str]]] = []

        for para in document.paragraphs:
            if para.is_empty:
                continue

            text = para.text.strip()

            # Eliminar prefijo Markdown (# ## ### etc.) si existe
            md_match = re.match(r"^#{1,6}\s+(.+)$", text)
            if md_match:
                text = md_match.group(1).strip()

            # Verificar prólogo
            for pattern in self.prologue_patterns:
                if pattern.match(text):
                    chapter_paragraphs.append(
                        (para, StructureType.PROLOGUE, 0, "Prólogo")
                    )
                    break
            else:
                # Verificar epílogo
                for pattern in self.epilogue_patterns:
                    if pattern.match(text):
                        chapter_paragraphs.append(
                            (para, StructureType.EPILOGUE, EPILOGUE_NUMBER, "Epílogo")
                        )
                        break
                else:
                    # Verificar capítulo
                    for pattern in self.chapter_patterns:
                        match = pattern.match(text)
                        if match:
                            number = self._parse_number(match.group(1))
                            title = match.group(2) if match.lastindex >= 2 else None
                            chapter_paragraphs.append(
                                (para, StructureType.CHAPTER, number, title)
                            )
                            break

        # Construir capítulos
        for i, (para, struct_type, number, title) in enumerate(chapter_paragraphs):
            # Calcular fin
            if i + 1 < len(chapter_paragraphs):
                end_char = chapter_paragraphs[i + 1][0].start_char
            else:
                end_char = self._get_document_end(document)

            chapter = Chapter(
                number=number,
                title=title,
                start_char=para.start_char,
                end_char=end_char,
                structure_type=struct_type,
                detected_by="pattern",
            )
            chapters.append(chapter)

        # Renumerar capítulos si es necesario
        self._renumber_chapters(chapters)

        return chapters

    def _detect_sections_in_chapters(
        self, document: RawDocument, chapters: list[Chapter]
    ) -> None:
        """
        Detecta secciones (subniveles H2, H3, H4...) dentro de cada capítulo.

        Las secciones se organizan jerárquicamente según su nivel de heading.
        Modifica los capítulos in-place añadiendo sus secciones.
        """
        if not chapters:
            return

        # Obtener todos los headings de subnivel (H2+)
        subheadings = [
            p for p in document.paragraphs
            if p.is_heading
            and p.heading_level
            and p.heading_level > 1  # Solo H2, H3, H4, etc.
            and not p.metadata.get("is_chapter_title")
            and p.text.strip()
            and p.start_char >= 0
        ]

        if not subheadings:
            return

        # Asignar cada subheading a su capítulo correspondiente
        for chapter in chapters:
            chapter_subheadings = [
                h for h in subheadings
                if chapter.start_char <= h.start_char < chapter.end_char
            ]

            if not chapter_subheadings:
                continue

            # Construir árbol de secciones jerárquicamente
            chapter.sections = self._build_section_tree(
                chapter_subheadings, chapter.end_char
            )

            logger.debug(
                f"Capítulo {chapter.number}: {len(chapter.sections)} secciones "
                f"({sum(1 for s in chapter.get_all_sections())} total con subsecciones)"
            )

    def _build_section_tree(
        self, headings: list[RawParagraph], chapter_end: int
    ) -> list[Section]:
        """
        Construye un árbol de secciones a partir de los headings.

        Los headings de nivel superior (H2) contienen a los de nivel inferior (H3, H4, etc.)
        """
        if not headings:
            return []

        sections: list[Section] = []
        i = 0

        while i < len(headings):
            heading = headings[i]
            level = heading.heading_level

            # Calcular fin de esta sección
            # La sección termina cuando:
            # 1. Encontramos un heading del mismo nivel o superior
            # 2. Llegamos al final del capítulo
            end_char = chapter_end
            subsection_headings: list[RawParagraph] = []

            j = i + 1
            while j < len(headings):
                next_heading = headings[j]
                next_level = next_heading.heading_level

                if next_level <= level:
                    # Heading del mismo nivel o superior: fin de sección
                    end_char = next_heading.start_char
                    break
                else:
                    # Heading de nivel inferior: es una subsección
                    subsection_headings.append(next_heading)
                j += 1

            # Crear la sección
            section = Section(
                number=len(sections) + 1,
                title=heading.text.strip(),
                heading_level=level,
                start_char=heading.start_char,
                end_char=end_char,
                subsections=self._build_section_tree(subsection_headings, end_char),
            )
            sections.append(section)

            # Avanzar al siguiente heading del mismo nivel
            i = j

        return sections

    def _detect_scenes_in_chapter(
        self, chapter: Chapter, full_text: str
    ) -> list[Scene]:
        """Detecta escenas dentro de un capítulo."""
        scenes: list[Scene] = []
        chapter_text = full_text[chapter.start_char : chapter.end_char]

        # Encontrar todos los separadores
        separator_positions: list[tuple[int, int, str]] = []  # (start, end, type)

        for pattern in self.scene_patterns:
            for match in pattern.finditer(chapter_text):
                separator_positions.append(
                    (match.start(), match.end(), pattern.pattern)
                )

        # Ordenar por posición
        separator_positions.sort(key=lambda x: x[0])

        # Eliminar separadores duplicados/solapados
        filtered_separators: list[tuple[int, int, str]] = []
        last_end = -1
        for start, end, sep_type in separator_positions:
            if start >= last_end:
                filtered_separators.append((start, end, sep_type))
                last_end = end

        # Crear escenas
        # scene_starts: posición donde empieza cada escena (después del separador)
        # scene_ends: posición donde termina cada escena (antes del siguiente separador)
        scene_starts = [0] + [end for _, end, _ in filtered_separators]
        scene_ends = [start for start, _, _ in filtered_separators] + [len(chapter_text)]

        for i in range(len(scene_starts)):
            start = scene_starts[i]
            end = scene_ends[i]

            # Ignorar escenas muy pequeñas (solo whitespace)
            scene_text = chapter_text[start:end].strip()
            if len(scene_text) < MIN_SCENE_CHARS:
                continue

            # El tipo de separador es el que precede a esta escena (no aplica para la primera)
            separator_type = filtered_separators[i - 1][2] if 0 < i <= len(filtered_separators) else None

            scene = Scene(
                number=len(scenes) + 1,
                start_char=chapter.start_char + start,
                end_char=chapter.start_char + end,
                separator_type=separator_type,
            )
            scenes.append(scene)

        # Si no hay separadores, todo el capítulo es una escena
        if not scenes:
            scenes.append(
                Scene(
                    number=1,
                    start_char=chapter.start_char,
                    end_char=chapter.end_char,
                )
            )

        return scenes

    def _create_single_chapter(self, document: RawDocument) -> Chapter:
        """Crea un capítulo único con todo el documento."""
        end_char = self._get_document_end(document)
        return Chapter(
            number=1,
            title=None,
            start_char=0,
            end_char=end_char,
            structure_type=StructureType.CHAPTER,
            detected_by="fallback",
        )

    def _get_document_end(self, document: RawDocument) -> int:
        """Obtiene la posición final del documento."""
        if document.paragraphs:
            last_para = document.paragraphs[-1]
            return last_para.end_char
        return len(document.full_text)

    def _parse_chapter_heading(
        self, text: str, default_number: int
    ) -> tuple[StructureType, int, Optional[str]]:
        """Parsea el texto de un heading para extraer tipo, número y título."""
        text = text.strip()

        # Eliminar prefijo Markdown (# ## ### etc.) si existe
        md_match = re.match(r"^#{1,6}\s+(.+)$", text)
        if md_match:
            text = md_match.group(1).strip()

        # Prólogo
        for pattern in self.prologue_patterns:
            if pattern.match(text):
                return StructureType.PROLOGUE, 0, "Prólogo"

        # Epílogo
        for pattern in self.epilogue_patterns:
            if pattern.match(text):
                return StructureType.EPILOGUE, EPILOGUE_NUMBER, "Epílogo"

        # Capítulo con patrón
        for pattern in self.chapter_patterns:
            match = pattern.match(text)
            if match:
                number = self._parse_number(match.group(1))
                title = match.group(2) if match.lastindex and match.lastindex >= 2 else None
                return StructureType.CHAPTER, number, title

        # Default: usar el texto completo como título
        return StructureType.CHAPTER, default_number, text if text else None

    def _parse_number(self, num_str: str) -> int:
        """Convierte string numérico (arábigo, romano o escrito) a int."""
        num_str = num_str.strip()
        num_upper = num_str.upper()
        num_lower = num_str.lower()

        # Intentar como número arábigo
        try:
            return int(num_str)
        except ValueError:
            pass

        # Intentar como número escrito en español
        spanish_numbers = {
            "uno": 1, "una": 1, "primero": 1, "primera": 1,
            "dos": 2, "segundo": 2, "segunda": 2,
            "tres": 3, "tercero": 3, "tercera": 3,
            "cuatro": 4, "cuarto": 4, "cuarta": 4,
            "cinco": 5, "quinto": 5, "quinta": 5,
            "seis": 6, "sexto": 6, "sexta": 6,
            "siete": 7, "séptimo": 7, "séptima": 7, "septimo": 7,
            "ocho": 8, "octavo": 8, "octava": 8,
            "nueve": 9, "noveno": 9, "novena": 9,
            "diez": 10, "décimo": 10, "décima": 10, "decimo": 10,
            "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
            "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
            "veinte": 20, "veintiuno": 21, "veintidós": 22,
        }
        if num_lower in spanish_numbers:
            return spanish_numbers[num_lower]

        # Intentar como número romano
        roman_values = {
            "I": 1,
            "V": 5,
            "X": 10,
            "L": 50,
            "C": 100,
            "D": 500,
            "M": 1000,
        }
        result = 0
        prev_value = 0

        for char in reversed(num_upper):
            if char not in roman_values:
                return 1  # Default si no es válido
            value = roman_values[char]
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value

        return result if result > 0 else 1

    def _renumber_chapters(self, chapters: list[Chapter]) -> None:
        """Renumera capítulos si hay inconsistencias."""
        # Separar prólogo/epílogo de capítulos normales
        regular_chapters = [
            c
            for c in chapters
            if c.structure_type == StructureType.CHAPTER
        ]

        # Verificar si los números son consecutivos
        numbers = [c.number for c in regular_chapters]
        if numbers and (numbers != list(range(1, len(numbers) + 1))):
            # Renumerar
            for i, chapter in enumerate(regular_chapters):
                chapter.number = i + 1

    def _validate_structure(self, structure: DocumentStructure) -> None:
        """Valida la estructura detectada y añade advertencias."""
        # Verificar capítulos muy cortos
        for chapter in structure.chapters:
            if chapter.char_count < self.min_chapter_words * AVG_CHARS_PER_WORD:
                structure.add_warning(
                    f"Capítulo {chapter.number} es muy corto "
                    f"({chapter.char_count} caracteres)"
                )

        # Verificar capítulos sin escenas
        for chapter in structure.chapters:
            if not chapter.scenes:
                structure.add_warning(
                    f"Capítulo {chapter.number} no tiene escenas detectadas"
                )

        # Verificar saltos en numeración
        numbers = [
            c.number
            for c in structure.chapters
            if c.structure_type == StructureType.CHAPTER
        ]
        for i in range(len(numbers) - 1):
            if numbers[i + 1] - numbers[i] > 1:
                structure.add_warning(
                    f"Posible capítulo faltante entre {numbers[i]} y {numbers[i+1]}"
                )


# =============================================================================
# Funciones de conveniencia
# =============================================================================


def detect_structure(document: RawDocument) -> Result[DocumentStructure]:
    """
    Detecta la estructura de un documento.

    Atajo para usar StructureDetector con configuración por defecto.

    Args:
        document: Documento parseado

    Returns:
        Result con DocumentStructure
    """
    detector = StructureDetector()
    return detector.detect(document)


def detect_chapters(document: RawDocument) -> list[Chapter]:
    """
    Detecta solo capítulos (sin escenas).

    Args:
        document: Documento parseado

    Returns:
        Lista de capítulos
    """
    detector = StructureDetector(detect_scenes=False)
    result = detector.detect(document)
    if result.is_success and result.value:
        return result.value.chapters
    return []
