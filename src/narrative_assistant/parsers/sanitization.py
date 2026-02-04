"""
Sanitización de inputs del usuario.

Previene:
- Path traversal attacks
- Nombres de archivo peligrosos
- Inputs malformados
"""

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from ..core.config import get_config
from ..core.errors import ErrorSeverity, NLPError
from ..core.result import Result

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitización de inputs del usuario."""

    # Caracteres peligrosos en nombres de archivo
    DANGEROUS_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    # Nombres reservados en Windows
    WINDOWS_RESERVED = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    # Longitudes máximas
    MAX_PROJECT_NAME_LENGTH = 100
    MAX_NOTE_LENGTH = 10000
    MAX_ENTITY_NAME_LENGTH = 200
    MAX_FILENAME_LENGTH = 255
    MAX_TEXT_LENGTH = 10 * 1024 * 1024  # 10MB para texto general
    MAX_CHAPTER_LENGTH = 5 * 1024 * 1024  # 5MB para capítulos

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitiza un nombre de archivo.

        - Remueve caracteres peligrosos
        - Limita longitud
        - Evita nombres reservados
        """
        # Remover caracteres peligrosos
        safe = cls.DANGEROUS_FILENAME_CHARS.sub("_", filename)

        # Remover puntos iniciales (archivos ocultos en Unix)
        safe = safe.lstrip(".")

        # Limitar longitud
        if len(safe) > cls.MAX_FILENAME_LENGTH:
            # Preservar extensión si existe
            parts = safe.rsplit(".", 1)
            if len(parts) == 2:
                name, ext = parts
                max_name_len = cls.MAX_FILENAME_LENGTH - len(ext) - 1
                safe = f"{name[:max_name_len]}.{ext}"
            else:
                safe = safe[: cls.MAX_FILENAME_LENGTH]

        # Evitar nombres reservados en Windows
        name_without_ext = safe.rsplit(".", 1)[0].upper()
        if name_without_ext in cls.WINDOWS_RESERVED:
            safe = f"_{safe}"

        # Si quedó vacío, usar un nombre por defecto
        if not safe or safe == ".":
            safe = "unnamed"

        return safe

    @classmethod
    def sanitize_project_name(cls, name: str) -> str:
        """
        Sanitiza un nombre de proyecto.

        - Strip whitespace
        - Limita longitud
        - Solo caracteres imprimibles
        """
        # Strip whitespace
        name = name.strip()

        # Limitar longitud
        if len(name) > cls.MAX_PROJECT_NAME_LENGTH:
            name = name[: cls.MAX_PROJECT_NAME_LENGTH]

        # Solo caracteres imprimibles
        name = "".join(c for c in name if c.isprintable())

        # Si quedó vacío
        return name or "Proyecto sin nombre"

    @classmethod
    def sanitize_user_note(cls, note: str) -> str:
        """
        Sanitiza una nota del usuario.

        - Limita longitud
        - Mantiene saltos de línea pero normaliza
        """
        # Normalizar saltos de línea
        note = note.replace("\r\n", "\n").replace("\r", "\n")

        # Limitar longitud
        if len(note) > cls.MAX_NOTE_LENGTH:
            note = note[: cls.MAX_NOTE_LENGTH - 15] + "\n[... truncado]"

        return note

    @classmethod
    def sanitize_entity_name(cls, name: str) -> str:
        """
        Sanitiza un nombre de entidad (personaje, lugar).

        - Strip whitespace
        - Limita longitud
        - Normaliza espacios múltiples
        - Elimina caracteres SQL peligrosos
        """
        # Strip y normalizar espacios
        name = " ".join(name.split())

        # Limitar longitud
        if len(name) > cls.MAX_ENTITY_NAME_LENGTH:
            name = name[: cls.MAX_ENTITY_NAME_LENGTH]

        # Eliminar secuencias SQL peligrosas
        # (aunque el ORM usa queries parametrizadas, esto añade defensa en profundidad)
        name = name.replace("--", "")
        name = name.replace(";", "")

        return name or "Sin nombre"

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitiza texto genérico (contenido de manuscrito).

        No modifica el contenido significativamente ya que puede ser
        legítimamente cualquier cosa. Solo:
        - Limita longitud
        - Elimina bytes nulos
        - Normaliza saltos de línea
        """
        if not text:
            return ""

        # Eliminar bytes nulos
        text = text.replace("\x00", "")

        # Normalizar saltos de línea
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Limitar longitud
        if len(text) > cls.MAX_TEXT_LENGTH:
            text = text[: cls.MAX_TEXT_LENGTH]

        return text


def sanitize_filename(filename: str) -> str:
    """Atajo para sanitizar nombre de archivo."""
    return InputSanitizer.sanitize_filename(filename)


def sanitize_chapter_content(content: str) -> str:
    """
    Sanitiza el contenido de un capítulo.

    Args:
        content: Contenido del capítulo

    Returns:
        Contenido sanitizado
    """
    if not content:
        return ""

    # Eliminar bytes nulos
    content = content.replace("\x00", "")

    # Normalizar saltos de línea
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Limitar longitud
    max_len = InputSanitizer.MAX_CHAPTER_LENGTH
    if len(content) > max_len:
        content = content[:max_len]

    return content


def validate_file_path(
    path: Path,
    must_exist: bool = True,
    allowed_extensions: set[str] | None = None,
) -> Path:
    """
    Valida y resuelve una ruta de archivo.

    Previene path traversal attacks.

    Args:
        path: Ruta a validar
        must_exist: Si True, verifica que el archivo existe
        allowed_extensions: Set de extensiones permitidas (ej: {'.docx', '.pdf'})

    Returns:
        Path resuelto y validado

    Raises:
        FileNotFoundError: Si must_exist=True y no existe
        ValueError: Si la extensión no está permitida
        PermissionError: Si hay un intento de path traversal
    """
    # Resolver a path absoluto
    resolved = path.resolve()

    # Verificar que existe (si requerido)
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    if must_exist and not resolved.is_file():
        raise ValueError(f"No es un archivo: {path}")

    # Verificar extensión permitida
    if allowed_extensions:
        ext = resolved.suffix.lower()
        if ext not in allowed_extensions:
            raise ValueError(
                f"Extensión '{ext}' no permitida. "
                f"Extensiones válidas: {', '.join(sorted(allowed_extensions))}"
            )

    # Verificar que no escapa del directorio actual o home
    # (prevención de path traversal)
    config = get_config()
    safe_dirs = [
        Path.cwd(),
        Path.home(),
        config.data_dir,
    ]

    # Añadir directorios adicionales configurados por el usuario
    if hasattr(config, "security") and hasattr(config.security, "additional_safe_dirs"):
        for extra_dir in config.security.additional_safe_dirs:
            try:
                safe_dirs.append(Path(extra_dir).resolve())
            except Exception:
                pass

    # Verificar que el archivo está en algún directorio seguro
    is_safe = any(_is_path_under(resolved, safe_dir) for safe_dir in safe_dirs)

    # SEGURIDAD: Bloquear TODO lo que no esté en directorios seguros
    # Esto previene acceso a archivos del sistema como /etc/passwd
    if not is_safe:
        logger.warning(
            f"Acceso denegado a ruta fuera de directorios seguros: {path} "
            f"(resuelto: {resolved}). Directorios permitidos: {safe_dirs}"
        )
        raise PermissionError(
            f"Ruta fuera de directorios permitidos: {path}. "
            f"El archivo debe estar en: directorio actual, home, o directorio de datos."
        )

    # Validación adicional: rechazar paths con ".." aunque estén en safe_dirs
    # (por seguridad en profundidad)
    if ".." in str(path):
        logger.warning(f"Path traversal attempt con '..': {path}")
        raise PermissionError(f"Ruta con componentes '..' no permitida: {path}")

    return resolved


def _is_path_under(path: Path, parent: Path) -> bool:
    """Verifica si un path está bajo un directorio padre."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def get_allowed_document_extensions() -> set[str]:
    """Retorna extensiones de documento permitidas según config."""
    config = get_config()
    extensions = set()

    format_to_ext = {
        "docx": {".docx", ".doc"},
        "txt": {".txt"},
        "md": {".md", ".markdown"},
        "pdf": {".pdf"},
        "epub": {".epub"},
        "odt": {".odt"},
    }

    for fmt in config.parsing.enabled_formats:
        extensions.update(format_to_ext.get(fmt, set()))

    return extensions


@dataclass
class PathValidationError(NLPError):
    """Error de validación de ruta de archivo."""

    message: str = "Error de validación de ruta"
    severity: ErrorSeverity = field(
        default=ErrorSeverity.FATAL, init=False
    )  # Path errors are security-critical


def validate_file_path_safe(
    path: str | Path,
    allowed_dir: Path | None = None,
    must_exist: bool = False,
) -> Result[Path]:
    """
    Valida una ruta de archivo contra path traversal y otros ataques.

    Versión que retorna Result para manejo seguro de errores.
    Ver también: validate_file_path() que lanza excepciones.

    Args:
        path: Ruta a validar (string o Path)
        allowed_dir: Directorio permitido (si se especifica, el path debe estar dentro)
        must_exist: Si True, verifica que el archivo existe

    Returns:
        Result con el Path resuelto o error
    """
    try:
        # Convertir a string para análisis
        path_str = str(path)

        # Detectar null byte injection
        if "\x00" in path_str:
            return Result.failure(
                PathValidationError(message="Null byte detectado en ruta - posible ataque")
            )

        # Decodificar URL encoding (detectar %2e%2e = ..)
        try:
            decoded = urllib.parse.unquote(path_str)
            # Double decode
            decoded2 = urllib.parse.unquote(decoded)
        except Exception:
            decoded = path_str
            decoded2 = path_str

        # Detectar path traversal en versiones encoded
        traversal_patterns = ["..", "%2e%2e", "%252e", "%c0%af"]
        for pattern in traversal_patterns:
            if (
                pattern in path_str.lower()
                or pattern in decoded.lower()
                or pattern in decoded2.lower()
            ):
                return Result.failure(
                    PathValidationError(
                        message=f"Path traversal detectado en ruta: {path_str[:50]}"
                    )
                )

        # Convertir a Path y resolver
        path_obj = Path(path_str)

        # Si es path absoluto fuera del allowed_dir, bloquear
        if allowed_dir is not None:
            allowed_resolved = allowed_dir.resolve()

            # Resolver el path (esto expande .. y similares)
            try:
                resolved = path_obj.resolve()
            except Exception as e:
                return Result.failure(
                    PathValidationError(message=f"No se puede resolver la ruta: {e}")
                )

            # Verificar que está dentro del directorio permitido
            try:
                resolved.relative_to(allowed_resolved)
            except ValueError:
                return Result.failure(
                    PathValidationError(
                        message=f"Ruta outside del directorio permitido: {path_str[:50]}"
                    )
                )

            # Verificar existencia si requerido
            if must_exist and not resolved.exists():
                return Result.failure(
                    PathValidationError(message=f"Archivo no encontrado: {path_str[:50]}")
                )

            return Result.success(resolved)

        else:
            # Sin directorio permitido, solo validar básico
            resolved = path_obj.resolve()

            if must_exist and not resolved.exists():
                return Result.failure(
                    PathValidationError(message=f"Archivo no encontrado: {path_str[:50]}")
                )

            return Result.success(resolved)

    except Exception as e:
        return Result.failure(PathValidationError(message=f"Error validando ruta: {e}"))
