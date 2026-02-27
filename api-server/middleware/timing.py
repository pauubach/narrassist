"""
Timing middleware para medir performance de endpoints.

Agrega headers HTTP con tiempo de respuesta y logging para endpoints lentos.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Umbral en segundos para considerar un endpoint lento
SLOW_ENDPOINT_THRESHOLD = 1.0


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que mide el tiempo de ejecución de cada request.

    - Agrega header `X-Response-Time` con milisegundos
    - Logea warnings para endpoints lentos (>1s)
    - Logea info para todos los requests con timing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Ejecutar request
        response = await call_next(request)

        # Calcular tiempo transcurrido
        elapsed = time.perf_counter() - start_time
        elapsed_ms = elapsed * 1000

        # Agregar header con timing
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

        # Logging según tiempo de respuesta
        method = request.method
        path = request.url.path
        status = response.status_code

        if elapsed > SLOW_ENDPOINT_THRESHOLD:
            logger.warning(
                f"🐌 SLOW: {method} {path} - {elapsed_ms:.0f}ms [{status}]"
            )
        else:
            logger.info(
                f"⚡ {method} {path} - {elapsed_ms:.0f}ms [{status}]"
            )

        return response
