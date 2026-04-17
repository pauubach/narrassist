"""
Auto-install de dependencias opcionales en tiempo de ejecución.

Si una dependencia no está instalada cuando se necesita, se instala
automáticamente con pip y se reintenta el import.
"""

import importlib
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

# Mapa: nombre de import → nombre del paquete pip (cuando difieren)
_IMPORT_TO_PIP: dict[str, str] = {
    "docx": "python-docx",
    "ebooklib": "ebooklib",
    "pdfplumber": "pdfplumber",
    "reportlab": "reportlab",
    "symspellpy": "symspellpy",
    "chunspell": "chunspell",
    "language_tool_python": "language-tool-python",
    "pypdf": "pypdf",
    "httpx": "httpx",
    "odf": "odfpy",
    "chardet": "chardet",
}


def ensure_package(import_name: str, pip_name: str | None = None) -> bool:
    """
    Asegura que un paquete esté instalado. Si no lo está, lo instala con pip.

    Args:
        import_name: Nombre del módulo para import (ej: 'pdfplumber')
        pip_name: Nombre del paquete pip si difiere del import (ej: 'python-docx')

    Returns:
        True si el paquete está disponible (ya estaba o se instaló con éxito)
    """
    # Intentar import directo primero
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        pass

    # Resolver nombre pip
    if pip_name is None:
        pip_name = _IMPORT_TO_PIP.get(import_name, import_name)

    logger.info(f"Auto-instalando dependencia: {pip_name}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pip_name],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"Error instalando {pip_name}: {result.stderr}")
            return False

        # Limpiar caché de imports e intentar de nuevo
        importlib.invalidate_caches()
        importlib.import_module(import_name)
        logger.info(f"Dependencia {pip_name} instalada correctamente")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout instalando {pip_name}")
        return False
    except ImportError:
        logger.error(f"Instalación de {pip_name} completada pero import sigue fallando")
        return False
    except Exception as e:
        logger.error(f"Error inesperado instalando {pip_name}: {e}")
        return False
