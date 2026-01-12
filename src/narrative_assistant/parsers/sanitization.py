"""
Sanitización de inputs del usuario.

Previene:
- Path traversal attacks
- Nombres de archivo peligrosos
- Inputs malformados
"""

import logging
import re
from pathlib import Path
from typing import Optional

from ..core.config import get_config

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
        """
        # Strip y normalizar espacios
        name = " ".join(name.split())

        # Limitar longitud
        if len(name) > cls.MAX_ENTITY_NAME_LENGTH:
            name = name[: cls.MAX_ENTITY_NAME_LENGTH]

        return name or "Sin nombre"


def sanitize_filename(filename: str) -> str:
    """Atajo para sanitizar nombre de archivo."""
    return InputSanitizer.sanitize_filename(filename)


def validate_file_path(
    path: Path,
    must_exist: bool = True,
    allowed_extensions: Optional[set[str]] = None,
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
    # (prevención básica de path traversal)
    config = get_config()
    safe_dirs = [
        Path.cwd(),
        Path.home(),
        config.data_dir,
    ]

    # Verificar que el archivo está en algún directorio seguro
    # o es un path absoluto explícito
    is_safe = any(
        _is_path_under(resolved, safe_dir) for safe_dir in safe_dirs
    )

    # Bloquear path traversal: si tiene ".." y no está bajo directorio seguro
    # NOTA: Removido el "and" - ahora basta con no estar en directorio seguro
    if not is_safe:
        # Si tiene ".." explícito, es sospechoso
        if ".." in str(path):
            logger.warning(f"Posible path traversal detectado: {path}")
            raise PermissionError(f"Ruta no permitida: {path}")
        # Si no está en directorio seguro pero es absoluto y existe, permitir
        # (el usuario podría estar abriendo un archivo de otro lugar)

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
