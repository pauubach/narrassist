# Sistema de Procesamiento de Documentos

[<- Volver a Arquitectura](./README.md) | [<- Indice principal](../../README.md)

---

## Resumen Ejecutivo

Este documento define el pipeline completo de importacion de documentos para el Asistente de Correccion Narrativa. El objetivo es convertir cualquier formato de entrada a una **representacion interna unificada** que preserve estructura, posiciones y metadatos necesarios para el analisis posterior.

---

## 1. Formatos de Entrada Soportados

### Matriz de Prioridad

| Formato | Prioridad | Complejidad | Uso Editorial | Recomendacion |
|---------|-----------|-------------|---------------|---------------|
| **DOCX** | P0 | Baja | 80%+ | MVP obligatorio |
| **TXT/MD** | P0 | Minima | 5% | MVP obligatorio |
| **ODT** | P1 | Baja | 5% | Post-MVP |
| **PDF nativo** | P2 | Alta | 8% | Post-MVP con advertencia |
| **EPUB** | P2 | Media | 2% | Post-MVP |
| **PDF escaneado** | P3 | Muy alta | <1% | No soportar inicialmente |
| **MOBI** | P3 | Media | <1% | Convertir a EPUB externamente |

### Justificacion de Prioridades

**DOCX (P0)**: El 80%+ de manuscritos editoriales llegan en Word. Es el formato canonico.

**TXT/Markdown (P0)**: Casos simples, util para testing y usuarios tecnicos.

**ODT (P1)**: LibreOffice. Similar a DOCX internamente (XML + ZIP). Facil de soportar.

**PDF nativo (P2)**: Problematico pero necesario. Muchos autores entregan PDF. Advertir sobre perdida de estructura.

**EPUB (P2)**: Menos comun en flujo editorial pre-publicacion. XHTML interno facilita extraccion.

**MOBI (P3)**: Formato Kindle propietario. **Recomendacion**: No soportar directamente. Instruir al usuario a convertir con Calibre a EPUB.

---

## 2. Arquitectura del Pipeline

```
                    ENTRADA
                       |
                       v
        +-----------------------------+
        |     FORMAT DETECTOR         |  <- Detecta tipo real (no extension)
        +-----------------------------+
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
   +--------+    +---------+    +--------+
   |  DOCX  |    |   PDF   |    |  EPUB  |  ... otros parsers
   | Parser |    | Parser  |    | Parser |
   +--------+    +---------+    +--------+
        |              |              |
        +--------------+--------------+
                       |
                       v
        +-----------------------------+
        |    RAW DOCUMENT MODEL       |  <- Estructura intermedia cruda
        +-----------------------------+
                       |
                       v
        +-----------------------------+
        |      NORMALIZER             |  <- Limpieza y normalizacion
        +-----------------------------+
                       |
                       v
        +-----------------------------+
        |   STRUCTURE DETECTOR        |  <- Capitulos, escenas
        +-----------------------------+
                       |
                       v
        +-----------------------------+
        |   UNIFIED DOCUMENT MODEL    |  <- Formato interno final
        +-----------------------------+
```

---

## 3. Modelo de Datos Interno

### 3.1 RawParagraph (salida de parsers)

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum, auto
from pathlib import Path
import hashlib

class ParagraphStyle(Enum):
    """Estilos detectados en el documento original."""
    HEADING_1 = auto()
    HEADING_2 = auto()
    HEADING_3 = auto()
    NORMAL = auto()
    QUOTE = auto()
    FOOTNOTE = auto()
    UNKNOWN = auto()

@dataclass
class RawParagraph:
    """Parrafo tal como sale del parser, antes de normalizacion."""
    text: str
    style: ParagraphStyle
    style_name_original: Optional[str]  # Nombre original del estilo (ej: "Heading 1")
    source_page: Optional[int]  # Pagina estimada (si disponible)
    is_empty: bool = False
    formatting: Dict[str, Any] = field(default_factory=dict)  # bold, italic, etc.

    def __post_init__(self):
        self.is_empty = not self.text.strip()
```

### 3.2 RawDocument (salida del parser)

```python
@dataclass
class RawDocument:
    """Documento crudo antes de normalizacion."""
    source_path: Path
    source_format: str  # 'docx', 'pdf', 'epub', 'txt', 'odt'
    paragraphs: List[RawParagraph]
    metadata: Dict[str, Any]  # Titulo, autor, etc. si disponible
    extraction_warnings: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs if not p.is_empty)

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.full_text.encode('utf-8')).hexdigest()
```

### 3.3 NormalizedParagraph (tras normalizacion)

```python
@dataclass
class NormalizedParagraph:
    """Parrafo normalizado con posiciones absolutas."""
    id: int
    text: str
    text_normalized: str  # Sin espacios extra, caracteres unificados
    style: ParagraphStyle
    start_char: int  # Posicion absoluta en texto plano
    end_char: int

    # Contexto estructural
    chapter_hint: Optional[str]  # Patron detectado que sugiere capitulo
    is_scene_break: bool = False
    is_dialogue: bool = False

    # Trazabilidad
    source_paragraph_index: int  # Indice en RawDocument.paragraphs

@dataclass
class UnifiedDocument:
    """Documento final normalizado, listo para analisis."""
    project_id: int
    source_path: Path
    source_format: str
    content_hash: str

    # Texto
    full_text: str  # Texto plano completo
    paragraphs: List[NormalizedParagraph]

    # Estructura (tras StructureDetector)
    chapters: List['Chapter'] = field(default_factory=list)

    # Metricas
    word_count: int = 0
    paragraph_count: int = 0

    # Advertencias
    import_warnings: List[str] = field(default_factory=list)
```

---

## 4. Parsers por Formato

### 4.1 Parser DOCX (P0 - MVP)

**Libreria**: `python-docx` (2.x)

```bash
pip install python-docx==1.1.0
```

**Ventajas**:
- Mantenida activamente
- API limpia
- Preserva estilos de Word
- Sin dependencias externas

**Implementacion**:

```python
# src/narrative_assistant/parsers/docx_parser.py

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pathlib import Path
from typing import Optional
import logging

from ..models.document import RawDocument, RawParagraph, ParagraphStyle

logger = logging.getLogger(__name__)

# Mapeo de estilos Word a nuestros estilos
STYLE_MAP = {
    'Heading 1': ParagraphStyle.HEADING_1,
    'Heading 2': ParagraphStyle.HEADING_2,
    'Heading 3': ParagraphStyle.HEADING_3,
    'Title': ParagraphStyle.HEADING_1,
    'Subtitle': ParagraphStyle.HEADING_2,
    'Quote': ParagraphStyle.QUOTE,
    'Normal': ParagraphStyle.NORMAL,
    'Body Text': ParagraphStyle.NORMAL,
}

def _map_style(style_name: Optional[str]) -> ParagraphStyle:
    """Mapea nombre de estilo Word a ParagraphStyle."""
    if not style_name:
        return ParagraphStyle.UNKNOWN

    # Busqueda exacta
    if style_name in STYLE_MAP:
        return STYLE_MAP[style_name]

    # Busqueda parcial (para variantes localizadas)
    style_lower = style_name.lower()
    if 'heading' in style_lower or 'titulo' in style_lower:
        if '1' in style_lower:
            return ParagraphStyle.HEADING_1
        if '2' in style_lower:
            return ParagraphStyle.HEADING_2
        if '3' in style_lower:
            return ParagraphStyle.HEADING_3

    if 'quote' in style_lower or 'cita' in style_lower:
        return ParagraphStyle.QUOTE

    return ParagraphStyle.NORMAL


def _extract_formatting(paragraph) -> dict:
    """Extrae informacion de formato (bold, italic) del parrafo."""
    formatting = {
        'has_bold': False,
        'has_italic': False,
        'has_underline': False,
    }

    for run in paragraph.runs:
        if run.bold:
            formatting['has_bold'] = True
        if run.italic:
            formatting['has_italic'] = True
        if run.underline:
            formatting['has_underline'] = True

    return formatting


def parse_docx(file_path: Path) -> RawDocument:
    """
    Parsea un archivo DOCX y extrae texto con metadatos.

    Args:
        file_path: Ruta al archivo .docx

    Returns:
        RawDocument con texto y metadatos

    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si el archivo no es un DOCX valido
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    if not file_path.suffix.lower() == '.docx':
        raise ValueError(f"Extension incorrecta: {file_path.suffix}. Se esperaba .docx")

    warnings = []

    try:
        doc = Document(file_path)
    except PackageNotFoundError:
        raise ValueError(f"Archivo corrupto o no es un DOCX valido: {file_path}")
    except Exception as e:
        raise ValueError(f"Error al abrir DOCX: {e}")

    paragraphs = []

    for para in doc.paragraphs:
        text = para.text
        style_name = para.style.name if para.style else None

        paragraphs.append(RawParagraph(
            text=text,
            style=_map_style(style_name),
            style_name_original=style_name,
            source_page=None,  # DOCX no tiene paginacion intrinseca
            formatting=_extract_formatting(para),
        ))

    # Extraer metadatos del documento
    metadata = {}
    try:
        core_props = doc.core_properties
        if core_props.title:
            metadata['title'] = core_props.title
        if core_props.author:
            metadata['author'] = core_props.author
        if core_props.created:
            metadata['created'] = core_props.created.isoformat()
    except Exception as e:
        warnings.append(f"No se pudieron extraer metadatos: {e}")

    # Detectar tablas (advertencia)
    if doc.tables:
        warnings.append(f"Documento contiene {len(doc.tables)} tabla(s). "
                       "El texto de tablas puede no preservar estructura.")

    return RawDocument(
        source_path=file_path,
        source_format='docx',
        paragraphs=paragraphs,
        metadata=metadata,
        extraction_warnings=warnings,
    )
```

**Limitaciones DOCX**:
- No hay informacion de paginas (Word pagina dinamicamente)
- Tablas complejas pueden perder estructura
- Cuadros de texto pueden no extraerse
- Track changes requiere manejo especial

### 4.2 Parser TXT/Markdown (P0 - MVP)

**Libreria**: Ninguna (stdlib)

```python
# src/narrative_assistant/parsers/txt_parser.py

from pathlib import Path
import re
from typing import List
import chardet

from ..models.document import RawDocument, RawParagraph, ParagraphStyle

# Patrones para detectar estructura en texto plano
CHAPTER_PATTERNS = [
    r'^#+\s+',  # Markdown headers
    r'^CAPITULO\s+\d+',
    r'^Capitulo\s+\d+',
    r'^CHAPTER\s+\d+',
    r'^\d+\.\s+[A-Z]',  # "1. Titulo"
]

SCENE_BREAK_PATTERNS = [
    r'^\*\s*\*\s*\*\s*$',
    r'^---+$',
    r'^___+$',
    r'^\s*$',  # Linea vacia (multiple = scene break)
]


def _detect_encoding(file_path: Path) -> str:
    """Detecta encoding del archivo."""
    with open(file_path, 'rb') as f:
        raw = f.read(10000)  # Primeros 10KB

    result = chardet.detect(raw)
    encoding = result['encoding']

    # Fallbacks seguros
    if not encoding or result['confidence'] < 0.7:
        # Intentar UTF-8 primero
        try:
            raw.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass

        # Luego latin-1 (nunca falla)
        return 'latin-1'

    return encoding


def _detect_paragraph_style(text: str) -> ParagraphStyle:
    """Detecta estilo basado en patrones de texto."""
    text_stripped = text.strip()

    # Markdown headers
    if text_stripped.startswith('# '):
        return ParagraphStyle.HEADING_1
    if text_stripped.startswith('## '):
        return ParagraphStyle.HEADING_2
    if text_stripped.startswith('### '):
        return ParagraphStyle.HEADING_3

    # Patrones de capitulo
    for pattern in CHAPTER_PATTERNS:
        if re.match(pattern, text_stripped, re.IGNORECASE):
            return ParagraphStyle.HEADING_1

    # Citas (markdown blockquote)
    if text_stripped.startswith('> '):
        return ParagraphStyle.QUOTE

    return ParagraphStyle.NORMAL


def parse_txt(file_path: Path) -> RawDocument:
    """
    Parsea archivo de texto plano o Markdown.

    Args:
        file_path: Ruta al archivo

    Returns:
        RawDocument
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    warnings = []

    # Detectar encoding
    encoding = _detect_encoding(file_path)
    if encoding.lower() not in ('utf-8', 'ascii'):
        warnings.append(f"Encoding detectado: {encoding}. Considere convertir a UTF-8.")

    # Leer contenido
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback a latin-1
        warnings.append(f"Error con encoding {encoding}, usando latin-1")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()

    # Normalizar saltos de linea
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Dividir en parrafos (doble salto = separador)
    raw_paragraphs = re.split(r'\n\n+', content)

    paragraphs = []
    for raw_para in raw_paragraphs:
        text = raw_para.strip()
        if not text:
            continue

        paragraphs.append(RawParagraph(
            text=text,
            style=_detect_paragraph_style(text),
            style_name_original=None,
            source_page=None,
            formatting={},
        ))

    # Determinar formato
    is_markdown = file_path.suffix.lower() in ('.md', '.markdown')

    return RawDocument(
        source_path=file_path,
        source_format='markdown' if is_markdown else 'txt',
        paragraphs=paragraphs,
        metadata={'encoding_detected': encoding},
        extraction_warnings=warnings,
    )
```

### 4.3 Parser PDF (P2 - Post-MVP)

**Libreria recomendada**: `pdfplumber` (para PDF nativos)

```bash
pip install pdfplumber==0.10.3
```

**Alternativas evaluadas**:

| Libreria | Pros | Contras |
|----------|------|---------|
| `pdfplumber` | Excelente extraccion, detecta tablas, coordenadas precisas | Lento en PDFs grandes |
| `pypdf` | Rapido, activamente mantenido | Extraccion de texto menos precisa |
| `pdfminer.six` | Muy preciso, layout analysis | API compleja, lento |
| `pymupdf` (fitz) | Muy rapido, buena extraccion | Licencia AGPL (problematica) |

**Recomendacion**: `pdfplumber` como default, con fallback a `pypdf` para PDFs problematicos.

```python
# src/narrative_assistant/parsers/pdf_parser.py

from pathlib import Path
from typing import List, Optional, Tuple
import re
import logging

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

from ..models.document import RawDocument, RawParagraph, ParagraphStyle

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Error durante extraccion de PDF."""
    pass


def _is_header_footer(text: str, page_num: int, total_pages: int) -> bool:
    """
    Heuristica para detectar headers/footers.

    Patrones comunes:
    - Solo numero de pagina
    - Titulo del libro repetido
    - Nombre del autor repetido
    - "Capitulo X" repetido en cada pagina
    """
    text_clean = text.strip()

    # Solo numero (footer tipico)
    if re.match(r'^\d{1,4}$', text_clean):
        return True

    # Numero con guiones o puntos
    if re.match(r'^[-\.]\s*\d{1,4}\s*[-\.]?$', text_clean):
        return True

    # Muy corto y en mayusculas (header tipico)
    if len(text_clean) < 50 and text_clean.isupper():
        return True

    return False


def _detect_page_number(text: str) -> Optional[int]:
    """Extrae numero de pagina si esta presente."""
    # Buscar al final de la pagina
    lines = text.strip().split('\n')
    if not lines:
        return None

    last_line = lines[-1].strip()

    # Numero solo
    if re.match(r'^\d{1,4}$', last_line):
        return int(last_line)

    # "Pagina X" o "Page X"
    match = re.search(r'(?:pagina|page)\s+(\d+)', last_line, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _merge_hyphenated_words(text: str) -> str:
    """
    Une palabras cortadas por guion al final de linea.

    "corre-\nsponsabilidad" -> "corresponsabilidad"
    """
    # Patron: guion + salto de linea + minuscula
    return re.sub(r'-\n([a-z])', r'\1', text)


def _clean_page_text(
    text: str,
    page_num: int,
    total_pages: int,
    header_pattern: Optional[str] = None,
    footer_pattern: Optional[str] = None,
) -> str:
    """
    Limpia texto de una pagina eliminando headers/footers.
    """
    lines = text.split('\n')
    cleaned_lines = []

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Saltar lineas vacias al principio/final
        if not line_stripped:
            if cleaned_lines:  # Solo agregar si ya tenemos contenido
                cleaned_lines.append(line)
            continue

        # Detectar header (primeras 3 lineas)
        if i < 3 and _is_header_footer(line_stripped, page_num, total_pages):
            continue

        # Detectar footer (ultimas 3 lineas)
        if i >= len(lines) - 3 and _is_header_footer(line_stripped, page_num, total_pages):
            continue

        # Patron personalizado de header
        if header_pattern and re.match(header_pattern, line_stripped):
            continue

        # Patron personalizado de footer
        if footer_pattern and re.match(footer_pattern, line_stripped):
            continue

        cleaned_lines.append(line)

    # Limpiar lineas vacias al inicio y final
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    return '\n'.join(cleaned_lines)


def _detect_repeated_headers(pages_text: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Analiza multiples paginas para detectar patrones repetitivos de header/footer.

    Retorna (header_pattern, footer_pattern) como regex strings.
    """
    if len(pages_text) < 5:
        return None, None

    # Extraer primeras y ultimas lineas de cada pagina
    first_lines = []
    last_lines = []

    for text in pages_text:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            first_lines.append(lines[0])
            last_lines.append(lines[-1])

    # Buscar patron repetitivo en headers
    header_pattern = _find_repetitive_pattern(first_lines)
    footer_pattern = _find_repetitive_pattern(last_lines)

    return header_pattern, footer_pattern


def _find_repetitive_pattern(lines: List[str], threshold: float = 0.7) -> Optional[str]:
    """
    Encuentra patron que se repite en >threshold de las lineas.
    """
    if not lines:
        return None

    # Contar ocurrencias exactas
    from collections import Counter
    counts = Counter(lines)
    most_common = counts.most_common(1)[0]

    if most_common[1] / len(lines) >= threshold:
        # Escapar para regex
        return re.escape(most_common[0])

    # Buscar patron numerico (ej: "Capitulo 1", "Capitulo 2", ...)
    # Reemplazar numeros por \d+
    normalized = []
    for line in lines:
        norm = re.sub(r'\d+', r'\\d+', line)
        normalized.append(norm)

    norm_counts = Counter(normalized)
    most_common_norm = norm_counts.most_common(1)[0]

    if most_common_norm[1] / len(lines) >= threshold:
        return most_common_norm[0]

    return None


def _extract_with_pdfplumber(file_path: Path) -> Tuple[List[str], List[dict]]:
    """Extrae texto usando pdfplumber."""
    pages_text = []
    pages_meta = []

    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_text.append(text)
            pages_meta.append({
                'page_num': i + 1,
                'width': page.width,
                'height': page.height,
            })

    return pages_text, pages_meta


def _extract_with_pypdf(file_path: Path) -> Tuple[List[str], List[dict]]:
    """Extrae texto usando pypdf (fallback)."""
    pages_text = []
    pages_meta = []

    reader = PdfReader(file_path)

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)
        pages_meta.append({
            'page_num': i + 1,
        })

    return pages_text, pages_meta


def parse_pdf(
    file_path: Path,
    remove_headers: bool = True,
    remove_footers: bool = True,
    merge_hyphenated: bool = True,
) -> RawDocument:
    """
    Parsea un archivo PDF.

    Args:
        file_path: Ruta al archivo PDF
        remove_headers: Intentar eliminar headers repetitivos
        remove_footers: Intentar eliminar footers/numeros de pagina
        merge_hyphenated: Unir palabras cortadas por guion

    Returns:
        RawDocument

    Raises:
        PDFExtractionError: Si no se puede extraer el PDF
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    warnings = []

    # Intentar con pdfplumber primero
    if PDFPLUMBER_AVAILABLE:
        try:
            pages_text, pages_meta = _extract_with_pdfplumber(file_path)
            extraction_method = 'pdfplumber'
        except Exception as e:
            logger.warning(f"pdfplumber fallo: {e}. Intentando pypdf...")
            warnings.append(f"pdfplumber fallo: {e}")
            pages_text = None
    else:
        pages_text = None
        warnings.append("pdfplumber no disponible, usando pypdf")

    # Fallback a pypdf
    if pages_text is None:
        if not PYPDF_AVAILABLE:
            raise PDFExtractionError(
                "No hay libreria PDF disponible. Instale pdfplumber o pypdf."
            )
        try:
            pages_text, pages_meta = _extract_with_pypdf(file_path)
            extraction_method = 'pypdf'
        except Exception as e:
            raise PDFExtractionError(f"No se pudo extraer PDF: {e}")

    # Verificar contenido
    total_text = ''.join(pages_text)
    if not total_text.strip():
        raise PDFExtractionError(
            "PDF sin texto extraible. Puede ser un PDF escaneado (imagen). "
            "Considere usar OCR externo primero."
        )

    # Detectar si es escaneado (muy poco texto por pagina)
    avg_chars_per_page = len(total_text) / len(pages_text) if pages_text else 0
    if avg_chars_per_page < 100:
        warnings.append(
            "Muy poco texto detectado. Posible PDF escaneado. "
            "La extraccion puede ser incompleta."
        )

    # Detectar patrones repetitivos
    header_pattern, footer_pattern = None, None
    if remove_headers or remove_footers:
        header_pattern, footer_pattern = _detect_repeated_headers(pages_text)
        if header_pattern:
            logger.info(f"Header detectado: {header_pattern}")
        if footer_pattern:
            logger.info(f"Footer detectado: {footer_pattern}")

    # Procesar cada pagina
    paragraphs = []

    for i, (page_text, meta) in enumerate(zip(pages_text, pages_meta)):
        page_num = meta.get('page_num', i + 1)

        # Limpiar headers/footers
        cleaned_text = _clean_page_text(
            page_text,
            page_num,
            len(pages_text),
            header_pattern if remove_headers else None,
            footer_pattern if remove_footers else None,
        )

        if merge_hyphenated:
            cleaned_text = _merge_hyphenated_words(cleaned_text)

        # Dividir en parrafos (doble salto de linea)
        raw_paras = re.split(r'\n\s*\n', cleaned_text)

        for para_text in raw_paras:
            para_text = para_text.strip()
            if not para_text:
                continue

            # Detectar estilo basico
            style = ParagraphStyle.NORMAL
            if para_text.isupper() and len(para_text) < 100:
                style = ParagraphStyle.HEADING_1
            elif re.match(r'^(CAPITULO|CHAPTER|PARTE|PART)\s+', para_text, re.IGNORECASE):
                style = ParagraphStyle.HEADING_1

            paragraphs.append(RawParagraph(
                text=para_text,
                style=style,
                style_name_original=None,
                source_page=page_num,
                formatting={},
            ))

    # Advertencia general sobre PDF
    warnings.append(
        "ADVERTENCIA: La extraccion de PDF puede perder formato y estructura. "
        "Se recomienda usar DOCX si esta disponible."
    )

    return RawDocument(
        source_path=file_path,
        source_format='pdf',
        paragraphs=paragraphs,
        metadata={
            'total_pages': len(pages_text),
            'extraction_method': extraction_method,
        },
        extraction_warnings=warnings,
    )
```

### 4.4 Parser EPUB (P2 - Post-MVP)

**Libreria**: `ebooklib`

```bash
pip install ebooklib==0.18
```

```python
# src/narrative_assistant/parsers/epub_parser.py

from pathlib import Path
from typing import List
import re
from html.parser import HTMLParser
import logging

try:
    import ebooklib
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

from ..models.document import RawDocument, RawParagraph, ParagraphStyle

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Extrae texto de HTML preservando estructura basica."""

    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self.current_text = []
        self.current_style = ParagraphStyle.NORMAL
        self.in_heading = False
        self.heading_level = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._flush_paragraph()
            self.in_heading = True
            self.heading_level = int(tag[1])

            if self.heading_level == 1:
                self.current_style = ParagraphStyle.HEADING_1
            elif self.heading_level == 2:
                self.current_style = ParagraphStyle.HEADING_2
            else:
                self.current_style = ParagraphStyle.HEADING_3

        elif tag == 'p':
            self._flush_paragraph()
            self.current_style = ParagraphStyle.NORMAL

        elif tag == 'blockquote':
            self._flush_paragraph()
            self.current_style = ParagraphStyle.QUOTE

        elif tag == 'br':
            self.current_text.append('\n')

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote', 'div'):
            self._flush_paragraph()
            self.in_heading = False
            self.current_style = ParagraphStyle.NORMAL

    def handle_data(self, data):
        # Limpiar espacios excesivos
        text = re.sub(r'\s+', ' ', data)
        if text.strip():
            self.current_text.append(text)

    def _flush_paragraph(self):
        text = ''.join(self.current_text).strip()
        if text:
            self.paragraphs.append(RawParagraph(
                text=text,
                style=self.current_style,
                style_name_original=None,
                source_page=None,
                formatting={},
            ))
        self.current_text = []


def parse_epub(file_path: Path) -> RawDocument:
    """
    Parsea un archivo EPUB.

    Args:
        file_path: Ruta al archivo .epub

    Returns:
        RawDocument
    """
    if not EBOOKLIB_AVAILABLE:
        raise ImportError("ebooklib no instalado. Ejecute: pip install ebooklib")

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    warnings = []

    try:
        book = epub.read_epub(str(file_path))
    except Exception as e:
        raise ValueError(f"Error al abrir EPUB: {e}")

    # Extraer metadatos
    metadata = {}
    try:
        title = book.get_metadata('DC', 'title')
        if title:
            metadata['title'] = title[0][0]

        creator = book.get_metadata('DC', 'creator')
        if creator:
            metadata['author'] = creator[0][0]

        language = book.get_metadata('DC', 'language')
        if language:
            metadata['language'] = language[0][0]
    except Exception as e:
        warnings.append(f"Error extrayendo metadatos: {e}")

    # Procesar documentos XHTML
    all_paragraphs = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode('utf-8', errors='replace')

        # Extraer texto del HTML
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(content)
            all_paragraphs.extend(extractor.paragraphs)
        except Exception as e:
            warnings.append(f"Error procesando {item.get_name()}: {e}")

    return RawDocument(
        source_path=file_path,
        source_format='epub',
        paragraphs=all_paragraphs,
        metadata=metadata,
        extraction_warnings=warnings,
    )
```

### 4.5 Parser ODT (P1 - Post-MVP)

**Libreria**: `odfpy`

```bash
pip install odfpy==1.4.1
```

```python
# src/narrative_assistant/parsers/odt_parser.py

from pathlib import Path
from typing import Optional
import logging

try:
    from odf import text as odf_text
    from odf.opendocument import load as load_odf
    ODFPY_AVAILABLE = True
except ImportError:
    ODFPY_AVAILABLE = False

from ..models.document import RawDocument, RawParagraph, ParagraphStyle

logger = logging.getLogger(__name__)

# Mapeo de estilos ODT
ODT_STYLE_MAP = {
    'Heading_20_1': ParagraphStyle.HEADING_1,
    'Heading_20_2': ParagraphStyle.HEADING_2,
    'Heading_20_3': ParagraphStyle.HEADING_3,
    'Heading 1': ParagraphStyle.HEADING_1,
    'Heading 2': ParagraphStyle.HEADING_2,
    'Heading 3': ParagraphStyle.HEADING_3,
    'Title': ParagraphStyle.HEADING_1,
    'Subtitle': ParagraphStyle.HEADING_2,
    'Quotations': ParagraphStyle.QUOTE,
}


def _get_paragraph_text(paragraph) -> str:
    """Extrae texto de un parrafo ODT."""
    text_parts = []

    for node in paragraph.childNodes:
        if node.nodeType == node.TEXT_NODE:
            text_parts.append(str(node))
        elif hasattr(node, 'childNodes'):
            # Recursivamente extraer texto de nodos hijos
            for child in node.childNodes:
                if child.nodeType == child.TEXT_NODE:
                    text_parts.append(str(child))

    return ''.join(text_parts)


def parse_odt(file_path: Path) -> RawDocument:
    """
    Parsea un archivo ODT (LibreOffice/OpenOffice).

    Args:
        file_path: Ruta al archivo .odt

    Returns:
        RawDocument
    """
    if not ODFPY_AVAILABLE:
        raise ImportError("odfpy no instalado. Ejecute: pip install odfpy")

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    warnings = []

    try:
        doc = load_odf(str(file_path))
    except Exception as e:
        raise ValueError(f"Error al abrir ODT: {e}")

    paragraphs = []

    # Iterar sobre parrafos
    for para in doc.getElementsByType(odf_text.P):
        text = _get_paragraph_text(para)

        # Obtener estilo
        style_name = para.getAttribute('stylename') or ''
        style = ODT_STYLE_MAP.get(style_name, ParagraphStyle.NORMAL)

        paragraphs.append(RawParagraph(
            text=text,
            style=style,
            style_name_original=style_name,
            source_page=None,
            formatting={},
        ))

    # Extraer metadatos
    metadata = {}
    try:
        meta = doc.meta
        if hasattr(meta, 'title') and meta.title:
            metadata['title'] = str(meta.title)
        if hasattr(meta, 'creator') and meta.creator:
            metadata['author'] = str(meta.creator)
    except Exception as e:
        warnings.append(f"Error extrayendo metadatos: {e}")

    return RawDocument(
        source_path=file_path,
        source_format='odt',
        paragraphs=paragraphs,
        metadata=metadata,
        extraction_warnings=warnings,
    )
```

---

## 5. Normalizador de Texto

El normalizador convierte RawDocument a UnifiedDocument aplicando:

1. **Normalizacion de caracteres**
2. **Calculo de posiciones absolutas**
3. **Deteccion de dialogos**
4. **Limpieza de espacios**

```python
# src/narrative_assistant/parsers/normalizer.py

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import re
import unicodedata

from ..models.document import (
    RawDocument, RawParagraph, ParagraphStyle,
    NormalizedParagraph, UnifiedDocument,
)


# Caracteres a normalizar
CHAR_REPLACEMENTS = {
    # Comillas
    '"': '"',
    '"': '"',
    '„': '"',
    '«': '"',
    '»': '"',
    ''': "'",
    ''': "'",
    '‚': "'",
    '‹': "'",
    '›': "'",

    # Guiones
    '–': '-',  # en-dash
    '—': '-',  # em-dash (raya de dialogo se preserva por separado)
    '‐': '-',  # guion unicode
    '−': '-',  # signo menos

    # Espacios
    '\u00A0': ' ',  # non-breaking space
    '\u2003': ' ',  # em space
    '\u2002': ' ',  # en space
    '\u2009': ' ',  # thin space
    '\u200B': '',   # zero-width space (eliminar)

    # Otros
    '…': '...',
    '•': '-',
}

# Patrones de dialogo en espanol
DIALOGUE_PATTERNS = [
    r'^—',           # Raya al inicio (dialogo espanol)
    r'^-\s*[A-Z]',   # Guion + espacio + mayuscula
    r'^"[^"]+"\s*$', # Linea solo de dialogo entre comillas
    r'^«[^»]+»\s*$', # Comillas latinas
]


def _normalize_char(char: str) -> str:
    """Normaliza un caracter individual."""
    if char in CHAR_REPLACEMENTS:
        return CHAR_REPLACEMENTS[char]
    return char


def _normalize_text(text: str) -> str:
    """
    Normaliza texto preservando semantica.

    - Unifica comillas y guiones
    - Elimina espacios multiples
    - Normaliza unicode (NFC)
    """
    # Normalizar unicode a forma canonica
    text = unicodedata.normalize('NFC', text)

    # Reemplazar caracteres
    result = []
    for char in text:
        result.append(_normalize_char(char))
    text = ''.join(result)

    # Limpiar espacios
    text = re.sub(r' +', ' ', text)  # Espacios multiples
    text = re.sub(r'\n +', '\n', text)  # Espacios tras salto
    text = re.sub(r' +\n', '\n', text)  # Espacios antes de salto

    return text.strip()


def _is_dialogue(text: str) -> bool:
    """Detecta si un parrafo es dialogo."""
    for pattern in DIALOGUE_PATTERNS:
        if re.match(pattern, text.strip()):
            return True
    return False


def _is_scene_break(text: str) -> bool:
    """Detecta separador de escena."""
    text_clean = text.strip()

    patterns = [
        r'^\*\s*\*\s*\*$',
        r'^-\s*-\s*-$',
        r'^_\s*_\s*_$',
        r'^#{3,}$',
        r'^\s*$',
    ]

    for pattern in patterns:
        if re.match(pattern, text_clean):
            return True

    return False


def _detect_chapter_hint(text: str, style: ParagraphStyle) -> Optional[str]:
    """
    Detecta indicios de que el parrafo es inicio de capitulo.
    Retorna el patron detectado o None.
    """
    text_clean = text.strip()

    # Por estilo
    if style in (ParagraphStyle.HEADING_1, ParagraphStyle.HEADING_2):
        return f"style:{style.name}"

    # Por patron textual
    patterns = [
        (r'^CAPITULO\s+(\d+|[IVXLCDM]+)', 'CAPITULO'),
        (r'^Capitulo\s+(\d+|[IVXLCDM]+)', 'Capitulo'),
        (r'^Cap[ií]tulo\s+(\d+|[IVXLCDM]+)', 'Capitulo'),
        (r'^CHAPTER\s+(\d+|[IVXLCDM]+)', 'CHAPTER'),
        (r'^PARTE\s+(\d+|[IVXLCDM]+)', 'PARTE'),
        (r'^\d+\.\s+[A-Z]', 'NUMBERED'),
        (r'^[IVXLCDM]+\.\s+[A-Z]', 'ROMAN'),
    ]

    for pattern, name in patterns:
        if re.match(pattern, text_clean, re.IGNORECASE):
            return f"pattern:{name}"

    return None


def normalize_document(raw_doc: RawDocument) -> UnifiedDocument:
    """
    Normaliza un RawDocument a UnifiedDocument.

    Args:
        raw_doc: Documento crudo del parser

    Returns:
        UnifiedDocument listo para analisis
    """
    normalized_paragraphs = []
    full_text_parts = []
    current_pos = 0

    for idx, raw_para in enumerate(raw_doc.paragraphs):
        # Saltar parrafos vacios
        if raw_para.is_empty:
            continue

        # Normalizar texto
        text_normalized = _normalize_text(raw_para.text)
        if not text_normalized:
            continue

        # Calcular posiciones
        start_char = current_pos
        end_char = current_pos + len(text_normalized)

        # Crear parrafo normalizado
        norm_para = NormalizedParagraph(
            id=len(normalized_paragraphs),
            text=raw_para.text,  # Original
            text_normalized=text_normalized,
            style=raw_para.style,
            start_char=start_char,
            end_char=end_char,
            chapter_hint=_detect_chapter_hint(text_normalized, raw_para.style),
            is_scene_break=_is_scene_break(text_normalized),
            is_dialogue=_is_dialogue(text_normalized),
            source_paragraph_index=idx,
        )

        normalized_paragraphs.append(norm_para)
        full_text_parts.append(text_normalized)

        # Avanzar posicion (+1 por salto de linea)
        current_pos = end_char + 1

    # Construir texto completo
    full_text = '\n'.join(full_text_parts)

    # Heredar warnings
    warnings = list(raw_doc.extraction_warnings)

    return UnifiedDocument(
        project_id=0,  # Se asigna al importar
        source_path=raw_doc.source_path,
        source_format=raw_doc.source_format,
        content_hash=raw_doc.content_hash,
        full_text=full_text,
        paragraphs=normalized_paragraphs,
        word_count=len(full_text.split()),
        paragraph_count=len(normalized_paragraphs),
        import_warnings=warnings,
    )
```

---

## 6. Detector de Formato

```python
# src/narrative_assistant/parsers/format_detector.py

from pathlib import Path
from typing import Optional
import zipfile
import struct

# Magic bytes para deteccion
MAGIC_BYTES = {
    'pdf': b'%PDF',
    'zip': b'PK\x03\x04',  # ZIP (DOCX, EPUB, ODT son ZIP)
    'epub': b'PK\x03\x04',
}


def _check_zip_contents(file_path: Path) -> Optional[str]:
    """
    Diferencia entre DOCX, EPUB y ODT (todos son ZIP).
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            names = z.namelist()

            # DOCX: contiene word/document.xml
            if any('word/document.xml' in n for n in names):
                return 'docx'

            # EPUB: contiene mimetype con 'application/epub+zip'
            if 'mimetype' in names:
                mimetype = z.read('mimetype').decode('utf-8', errors='ignore')
                if 'epub' in mimetype.lower():
                    return 'epub'

            # ODT: contiene content.xml y META-INF/manifest.xml
            if 'content.xml' in names and 'META-INF/manifest.xml' in names:
                return 'odt'

            # ZIP generico
            return 'zip'
    except zipfile.BadZipFile:
        return None


def detect_format(file_path: Path) -> str:
    """
    Detecta formato real del archivo (no por extension).

    Args:
        file_path: Ruta al archivo

    Returns:
        Formato detectado: 'docx', 'pdf', 'epub', 'odt', 'txt', 'unknown'
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    # Leer primeros bytes
    with open(file_path, 'rb') as f:
        header = f.read(8)

    # Detectar PDF
    if header.startswith(b'%PDF'):
        return 'pdf'

    # Detectar ZIP (puede ser DOCX, EPUB, ODT)
    if header.startswith(b'PK\x03\x04'):
        zip_format = _check_zip_contents(file_path)
        if zip_format:
            return zip_format

    # Por extension como fallback
    ext = file_path.suffix.lower()

    extension_map = {
        '.docx': 'docx',
        '.pdf': 'pdf',
        '.epub': 'epub',
        '.odt': 'odt',
        '.txt': 'txt',
        '.md': 'markdown',
        '.markdown': 'markdown',
    }

    if ext in extension_map:
        return extension_map[ext]

    # Asumir texto plano si parece texto
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1000)
        return 'txt'
    except UnicodeDecodeError:
        pass

    return 'unknown'
```

---

## 7. Orquestador de Importacion

```python
# src/narrative_assistant/parsers/importer.py

from pathlib import Path
from typing import Optional
import logging

from .format_detector import detect_format
from .docx_parser import parse_docx
from .txt_parser import parse_txt
from .pdf_parser import parse_pdf, PDFExtractionError
from .epub_parser import parse_epub
from .odt_parser import parse_odt
from .normalizer import normalize_document
from ..models.document import RawDocument, UnifiedDocument

logger = logging.getLogger(__name__)


class ImportError(Exception):
    """Error durante importacion de documento."""
    pass


class UnsupportedFormatError(ImportError):
    """Formato no soportado."""
    pass


def import_document(
    file_path: Path,
    project_id: int,
    force_format: Optional[str] = None,
) -> UnifiedDocument:
    """
    Importa un documento de cualquier formato soportado.

    Este es el punto de entrada principal para importar documentos.

    Args:
        file_path: Ruta al archivo
        project_id: ID del proyecto destino
        force_format: Forzar formato (omitir deteccion)

    Returns:
        UnifiedDocument listo para analisis

    Raises:
        ImportError: Si hay error de importacion
        UnsupportedFormatError: Si el formato no esta soportado
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise ImportError(f"Archivo no encontrado: {file_path}")

    # Detectar formato
    if force_format:
        format_type = force_format
    else:
        format_type = detect_format(file_path)

    logger.info(f"Importando {file_path} como {format_type}")

    # Parsear segun formato
    raw_doc: RawDocument

    if format_type == 'docx':
        raw_doc = parse_docx(file_path)

    elif format_type in ('txt', 'markdown'):
        raw_doc = parse_txt(file_path)

    elif format_type == 'pdf':
        try:
            raw_doc = parse_pdf(file_path)
        except PDFExtractionError as e:
            raise ImportError(str(e))

    elif format_type == 'epub':
        raw_doc = parse_epub(file_path)

    elif format_type == 'odt':
        raw_doc = parse_odt(file_path)

    elif format_type == 'unknown':
        raise UnsupportedFormatError(
            f"No se pudo detectar el formato de {file_path}. "
            "Formatos soportados: DOCX, TXT, MD, PDF, EPUB, ODT"
        )

    else:
        raise UnsupportedFormatError(
            f"Formato '{format_type}' no soportado. "
            "Formatos soportados: DOCX, TXT, MD, PDF, EPUB, ODT"
        )

    # Normalizar
    unified_doc = normalize_document(raw_doc)
    unified_doc.project_id = project_id

    # Log estadisticas
    logger.info(
        f"Importado: {unified_doc.word_count} palabras, "
        f"{unified_doc.paragraph_count} parrafos"
    )

    if unified_doc.import_warnings:
        for warning in unified_doc.import_warnings:
            logger.warning(f"  - {warning}")

    return unified_doc
```

---

## 8. Casos Edge y Manejo de Errores

### 8.1 PDFs Escaneados (Imagenes)

**Problema**: PDF sin texto extraible, solo imagenes.

**Deteccion**:
```python
def _is_scanned_pdf(pages_text: List[str]) -> bool:
    """Detecta si un PDF es escaneado."""
    total_chars = sum(len(t) for t in pages_text)
    avg_per_page = total_chars / len(pages_text) if pages_text else 0

    # Menos de 100 caracteres por pagina = probablemente escaneado
    return avg_per_page < 100
```

**Solucion recomendada**: No soportar OCR internamente. Instruir al usuario:

```
Este PDF parece ser un documento escaneado (imagen).

Para procesarlo, conviertalo primero a texto usando:
1. Adobe Acrobat Pro (OCR integrado)
2. OCRmyPDF (gratuito): ocrmypdf input.pdf output.pdf
3. Google Docs (importar PDF, exportar como DOCX)

Una vez convertido, importe el documento resultante.
```

### 8.2 Documentos Protegidos

```python
def _check_pdf_permissions(file_path: Path) -> dict:
    """Verifica permisos de un PDF."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)

    if reader.is_encrypted:
        return {
            'is_encrypted': True,
            'error': 'PDF protegido con contrasena. Desbloquee el documento primero.'
        }

    return {'is_encrypted': False}
```

### 8.3 Encodings Problematicos

**Estrategia de fallback**:
1. Detectar con `chardet`
2. Si confianza < 70%, intentar UTF-8
3. Si falla UTF-8, usar `latin-1` (nunca falla)
4. Advertir al usuario sobre posibles caracteres incorrectos

### 8.4 Archivos Corruptos

```python
def _validate_file_integrity(file_path: Path, format_type: str) -> List[str]:
    """Valida integridad basica del archivo."""
    errors = []

    # Verificar tamano minimo
    size = file_path.stat().st_size
    if size < 100:
        errors.append(f"Archivo muy pequeno ({size} bytes). Posiblemente corrupto.")

    # Verificar que ZIP sea valido (DOCX, EPUB, ODT)
    if format_type in ('docx', 'epub', 'odt'):
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                z.testzip()
        except zipfile.BadZipFile:
            errors.append("Archivo ZIP corrupto. Intente recuperar desde backup.")

    return errors
```

---

## 9. Dependencias y Requisitos

### requirements-parsers.txt

```
# Core (MVP)
python-docx>=1.1.0,<2.0.0
chardet>=5.0.0,<6.0.0

# PDF (Post-MVP)
pdfplumber>=0.10.0,<0.11.0
pypdf>=4.0.0,<5.0.0

# EPUB (Post-MVP)
ebooklib>=0.18,<0.19

# ODT (Post-MVP)
odfpy>=1.4.0,<1.5.0
```

### Instalacion por fases

```bash
# MVP (obligatorio)
pip install python-docx chardet

# Post-MVP (opcional)
pip install pdfplumber pypdf ebooklib odfpy
```

---

## 10. Testing

### Fixtures necesarios

```
tests/fixtures/
├── documents/
│   ├── sample_novel.docx          # DOCX con capitulos, dialogos
│   ├── sample_novel_headings.docx # DOCX con estilos Heading
│   ├── sample_plain.txt           # Texto plano
│   ├── sample_markdown.md         # Con headers MD
│   ├── sample_native.pdf          # PDF nativo (texto seleccionable)
│   ├── sample_scanned.pdf         # PDF escaneado (para test de error)
│   ├── sample_protected.pdf       # PDF con password
│   ├── sample.epub                # EPUB valido
│   ├── sample.odt                 # ODT LibreOffice
│   └── sample_corrupted.docx      # ZIP corrupto
└── expected/
    ├── sample_novel_normalized.json
    └── ...
```

### Tests unitarios

```python
# tests/test_parsers.py

import pytest
from pathlib import Path
from narrative_assistant.parsers import import_document
from narrative_assistant.parsers.format_detector import detect_format

FIXTURES = Path(__file__).parent / 'fixtures' / 'documents'


class TestFormatDetector:
    def test_detects_docx(self):
        assert detect_format(FIXTURES / 'sample_novel.docx') == 'docx'

    def test_detects_pdf(self):
        assert detect_format(FIXTURES / 'sample_native.pdf') == 'pdf'

    def test_detects_txt(self):
        assert detect_format(FIXTURES / 'sample_plain.txt') == 'txt'


class TestDOCXParser:
    def test_extracts_text(self):
        doc = import_document(FIXTURES / 'sample_novel.docx', project_id=1)
        assert doc.word_count > 0
        assert doc.paragraphs

    def test_preserves_headings(self):
        doc = import_document(FIXTURES / 'sample_novel_headings.docx', project_id=1)
        headings = [p for p in doc.paragraphs if 'HEADING' in p.style.name]
        assert len(headings) > 0

    def test_detects_dialogues(self):
        doc = import_document(FIXTURES / 'sample_novel.docx', project_id=1)
        dialogues = [p for p in doc.paragraphs if p.is_dialogue]
        assert len(dialogues) > 0


class TestPDFParser:
    def test_extracts_native_pdf(self):
        doc = import_document(FIXTURES / 'sample_native.pdf', project_id=1)
        assert doc.word_count > 0

    def test_warns_on_scanned(self):
        with pytest.raises(Exception) as exc_info:
            import_document(FIXTURES / 'sample_scanned.pdf', project_id=1)
        assert 'escaneado' in str(exc_info.value).lower()


class TestNormalizer:
    def test_normalizes_quotes(self):
        doc = import_document(FIXTURES / 'sample_novel.docx', project_id=1)
        # Verificar que no hay comillas tipograficas en texto normalizado
        for para in doc.paragraphs:
            assert '"' not in para.text_normalized
            assert '"' not in para.text_normalized

    def test_calculates_positions(self):
        doc = import_document(FIXTURES / 'sample_novel.docx', project_id=1)

        for para in doc.paragraphs:
            # Verificar que posiciones son correctas
            extracted = doc.full_text[para.start_char:para.end_char]
            assert extracted == para.text_normalized
```

---

## 11. Notas de Implementacion

### Orden de implementacion sugerido

1. **MVP (Fase 1)**:
   - `format_detector.py`
   - `docx_parser.py`
   - `txt_parser.py`
   - `normalizer.py`
   - `importer.py`
   - Tests para DOCX y TXT

2. **Post-MVP (Fase 2)**:
   - `pdf_parser.py` (con advertencias claras)
   - `odt_parser.py`
   - `epub_parser.py`

### Consideraciones de rendimiento

- Para documentos grandes (>100k palabras), considerar procesamiento en chunks
- PDF con muchas paginas: usar generadores en lugar de listas
- Cache de deteccion de formato para operaciones repetidas

### Compatibilidad

- Python 3.10+ requerido
- Testear en macOS y Windows
- Considerar diferencias de paths (usar `pathlib` siempre)

---

## Siguiente

Ver [Detector de Estructura](../steps/phase-1/step-1.2-structure-detector.md) para el siguiente paso del pipeline.
