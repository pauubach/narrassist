#!/usr/bin/env python3
"""
Script de inicio para el servidor FastAPI.

Uso:
    python start_server.py              # Modo desarrollo (auto-reload)
    python start_server.py --production # Modo producción
"""

import logging
import sys
from pathlib import Path

# Añadir el directorio src/ al path para importar narrative_assistant
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def start_server(production: bool = False):
    """
    Inicia el servidor FastAPI.

    Args:
        production: Si es True, desactiva auto-reload
    """
    import uvicorn

    logger.info("=" * 60)
    logger.info("Narrative Assistant - API Server")
    logger.info("=" * 60)
    logger.info(f"Modo: {'PRODUCTION' if production else 'DEVELOPMENT'}")
    logger.info("URL: http://127.0.0.1:8008")
    logger.info("Docs: http://127.0.0.1:8008/docs")
    logger.info("=" * 60)

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8008,
        reload=not production,
        log_level="info",
        access_log=True,
    )

if __name__ == "__main__":
    production_mode = "--production" in sys.argv or "--prod" in sys.argv

    try:
        start_server(production=production_mode)
    except KeyboardInterrupt:
        logger.info("\nServidor detenido por usuario")
    except Exception as e:
        logger.error(f"Error al iniciar servidor: {e}", exc_info=True)
        sys.exit(1)
