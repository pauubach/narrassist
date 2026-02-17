"""
Middlewares de seguridad para la API de Narrative Assistant.

Incluye:
- RateLimitMiddleware: Limitador de tasa in-memory para prevenir DoS accidentales
- CSRFProtectionMiddleware: Validación de Origin/Referer contra orígenes permitidos

Diseñado para una aplicación de escritorio local (Tauri), por lo que los
controles son ligeros pero suficientes para evitar abusos.
"""

import logging
import threading
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("narrative_assistant.api.middleware")


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

class _TokenBucket:
    """
    Implementación simple de token bucket para rate limiting.

    Cada bucket se identifica por IP del cliente y permite un número máximo
    de requests por ventana de tiempo. Los tokens se regeneran continuamente.
    """

    def __init__(self, max_tokens: int, refill_rate: float):
        """
        Args:
            max_tokens: Capacidad máxima del bucket (burst máximo)
            refill_rate: Tokens añadidos por segundo
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = float(max_tokens)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Intenta consumir un token. Retorna True si hay tokens disponibles."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def retry_after(self) -> float:
        """Segundos estimados hasta que haya un token disponible."""
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting basado en token bucket.

    Aplica límites diferenciados según el tipo de endpoint:
    - Endpoints de análisis (costosos): límite estricto (ej: 10 req/min)
    - Resto de endpoints: límite permisivo (ej: 100 req/min)

    Diseñado para app de escritorio local - previene DoS accidentales
    por requests repetidos del frontend o abuso externo.
    """

    # Prefijos de rutas consideradas "costosas" (análisis NLP)
    EXPENSIVE_PREFIXES = (
        "/api/projects/",  # Se filtra más abajo por sufijo
    )
    EXPENSIVE_SUFFIXES = (
        "/analyze",
        "/reanalyze",
        "/analyze/partial",
    )
    # Rutas explícitamente excluidas del rate limiting estricto
    # (polling endpoints de solo lectura)
    POLLING_PATHS = (
        "/analysis/progress",
        "/analysis/status",
    )

    def __init__(
        self,
        app,
        analysis_rpm: int = 10,
        default_rpm: int = 100,
        cleanup_interval: int = 300,
    ):
        """
        Args:
            app: Aplicación ASGI
            analysis_rpm: Requests por minuto para endpoints de análisis
            default_rpm: Requests por minuto para el resto de endpoints
            cleanup_interval: Segundos entre limpiezas de buckets inactivos
        """
        super().__init__(app)
        self.analysis_rpm = analysis_rpm
        self.default_rpm = default_rpm
        self.cleanup_interval = cleanup_interval

        # Buckets separados para análisis y endpoints generales
        # Clave: IP del cliente
        self._analysis_buckets: dict[str, _TokenBucket] = {}
        self._default_buckets: dict[str, _TokenBucket] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()

        logger.info(
            f"Rate limiting activado: análisis={analysis_rpm} rpm, "
            f"general={default_rpm} rpm"
        )

    def _is_expensive_endpoint(self, path: str) -> bool:
        """Determina si la ruta corresponde a un endpoint costoso."""
        # Excluir endpoints de polling (solo lectura, muy frecuentes)
        if any(polling in path for polling in self.POLLING_PATHS):
            return False
        # Solo rutas de análisis son consideradas costosas
        return any(path.endswith(suffix) for suffix in self.EXPENSIVE_SUFFIXES)

    def _get_client_ip(self, request: Request) -> str:
        """Obtiene la IP del cliente desde el request."""
        # En app local, casi siempre será 127.0.0.1
        if request.client:
            return request.client.host
        return "unknown"

    def _get_bucket(self, client_ip: str, is_expensive: bool) -> _TokenBucket:
        """Obtiene o crea el token bucket para un cliente."""
        with self._lock:
            # Limpieza periódica de buckets inactivos
            now = time.monotonic()
            if now - self._last_cleanup > self.cleanup_interval:
                self._cleanup_buckets(now)
                self._last_cleanup = now

            if is_expensive:
                buckets = self._analysis_buckets
                rpm = self.analysis_rpm
            else:
                buckets = self._default_buckets
                rpm = self.default_rpm

            if client_ip not in buckets:
                # refill_rate = tokens por segundo = rpm / 60
                buckets[client_ip] = _TokenBucket(
                    max_tokens=rpm,
                    refill_rate=rpm / 60.0,
                )
            return buckets[client_ip]

    def _cleanup_buckets(self, now: float) -> None:
        """Elimina buckets que llevan tiempo inactivos (ya dentro del lock)."""
        threshold = now - self.cleanup_interval
        for buckets in (self._analysis_buckets, self._default_buckets):
            inactive = [
                ip for ip, bucket in buckets.items()
                if bucket.last_refill < threshold
            ]
            for ip in inactive:
                del buckets[ip]
            if inactive:
                logger.debug(f"Rate limiter: eliminados {len(inactive)} buckets inactivos")

    async def dispatch(self, request: Request, call_next):
        """Procesa el request aplicando rate limiting."""
        path = request.url.path

        # No limitar health check ni OPTIONS (preflight CORS)
        if path == "/api/health" or request.method == "OPTIONS":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        is_expensive = self._is_expensive_endpoint(path)
        bucket = self._get_bucket(client_ip, is_expensive)

        if not bucket.consume():
            retry_after = max(1.0, bucket.retry_after)
            limit_type = "análisis" if is_expensive else "general"
            logger.warning(
                f"Rate limit excedido ({limit_type}) para {client_ip}: "
                f"{path} — retry en {retry_after:.1f}s"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Demasiadas solicitudes. Intenta de nuevo en unos segundos.",
                    "retry_after": round(retry_after, 1),
                },
                headers={"Retry-After": str(int(retry_after))},
            )

        return await call_next(request)


# ============================================================================
# CSRF Protection Middleware
# ============================================================================

# Orígenes permitidos para la aplicación Tauri local
ALLOWED_ORIGINS: set[str] = {
    "http://localhost:5173",    # Vite dev server
    "http://localhost:8008",    # API server (mismo origen)
    "http://127.0.0.1:5173",   # Vite dev server (IP)
    "http://127.0.0.1:8008",   # API server (IP)
    "tauri://localhost",        # Tauri producción
    "http://tauri.localhost",   # Tauri alternativo
}


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware de protección CSRF mediante validación de Origin/Referer.

    Para una app de escritorio Tauri local, el riesgo de CSRF es bajo,
    pero esta capa previene requests desde páginas web maliciosas que
    intenten interactuar con la API local.

    Reglas:
    - GET/HEAD/OPTIONS: Siempre permitidos (safe methods, no modifican estado)
    - Sin header Origin: Permitido (requests same-origin desde Tauri WebView)
    - Con Origin válido: Permitido
    - Con Origin inválido: Rechazado con 403
    - Fallback a Referer si no hay Origin
    """

    # Métodos HTTP que no modifican estado (RFC 7231 §4.2.1)
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, app, extra_origins: Optional[set[str]] = None):
        """
        Args:
            app: Aplicación ASGI
            extra_origins: Orígenes adicionales a permitir
        """
        super().__init__(app)
        self.allowed_origins = set(ALLOWED_ORIGINS)
        if extra_origins:
            self.allowed_origins.update(extra_origins)
        logger.info(
            f"CSRF protection activada. Orígenes permitidos: {self.allowed_origins}"
        )

    def _extract_origin(self, request: Request) -> Optional[str]:
        """
        Extrae el origen del request desde Origin o Referer.

        Retorna None si no hay header de origen (same-origin / Tauri WebView).
        """
        origin = request.headers.get("origin")
        if origin:
            return origin.rstrip("/")

        # Fallback a Referer (extraer solo scheme://host:port)
        referer = request.headers.get("referer")
        if referer:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    port_part = f":{parsed.port}" if parsed.port else ""
                    return f"{parsed.scheme}://{parsed.hostname}{port_part}"
            except Exception:
                pass

        return None

    def _is_origin_allowed(self, origin: str) -> bool:
        """Verifica si el origen está en la lista de permitidos."""
        # Normalizar: quitar trailing slash
        normalized = origin.rstrip("/")
        return normalized in self.allowed_origins

    async def dispatch(self, request: Request, call_next):
        """Valida el origen para métodos que modifican estado."""
        # Métodos seguros no necesitan validación CSRF
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        origin = self._extract_origin(request)

        # Sin Origin ni Referer → same-origin (Tauri WebView) → permitir
        if origin is None:
            return await call_next(request)

        # Validar origen
        if not self._is_origin_allowed(origin):
            logger.warning(
                f"CSRF: origen no permitido '{origin}' para "
                f"{request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Origen no autorizado.",
                },
            )

        return await call_next(request)
