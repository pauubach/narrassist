"""
Monitor de memoria para el pipeline de análisis.

Proporciona utilidades para:
- Medir uso de memoria RSS del proceso
- Loguear deltas de memoria entre fases
- Emitir warnings cuando se superan umbrales configurables
"""

import logging
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Umbral por defecto: 2 GB
DEFAULT_MEMORY_WARNING_MB = 2048

# Lock para acceso thread-safe al historial
_monitor_lock = threading.Lock()


def get_process_memory_mb() -> float:
    """
    Obtiene el uso de memoria RSS del proceso actual en MB.

    Returns:
        Memoria RSS en megabytes, o -1.0 si no se puede obtener.
    """
    try:
        import psutil

        process = psutil.Process(os.getpid())
        rss = process.memory_info().rss
        return float(rss) / (1024 * 1024)
    except ImportError:
        pass

    # Fallback: resource module (Unix only)
    try:
        import resource

        getrusage = getattr(resource, "getrusage", None)
        rusage_self = getattr(resource, "RUSAGE_SELF", None)
        if callable(getrusage) and rusage_self is not None:
            usage = getrusage(rusage_self)
        else:
            raise AttributeError(
                "resource module missing getrusage/RUSAGE_SELF attributes"
            )
        maxrss = usage.ru_maxrss
        import platform

        if platform.system() == "Darwin":
            return float(maxrss) / (1024 * 1024)  # bytes → MB
        else:
            return float(maxrss) / 1024  # KB → MB
    except (ImportError, AttributeError):
        pass

    return -1.0


@dataclass
class MemorySnapshot:
    """Snapshot de memoria en un punto del pipeline."""

    phase_name: str
    timestamp: datetime
    memory_mb: float
    delta_mb: float = 0.0
    label: str = ""  # "start" o "end"


@dataclass
class MemoryReport:
    """Reporte de uso de memoria del pipeline completo."""

    snapshots: list[MemorySnapshot] = field(default_factory=list)
    peak_mb: float = 0.0
    warning_threshold_mb: float = DEFAULT_MEMORY_WARNING_MB
    warnings_emitted: int = 0

    @property
    def total_delta_mb(self) -> float:
        """Delta total desde la primera medición."""
        if len(self.snapshots) < 2:
            return 0.0
        return self.snapshots[-1].memory_mb - self.snapshots[0].memory_mb

    def get_phase_deltas(self) -> dict[str, float]:
        """Retorna {phase_name: delta_mb} para cada fase."""
        deltas: dict[str, float] = {}
        start_by_phase: dict[str, float] = {}

        for snap in self.snapshots:
            if snap.label == "start":
                start_by_phase[snap.phase_name] = snap.memory_mb
            elif snap.label == "end" and snap.phase_name in start_by_phase:
                deltas[snap.phase_name] = snap.memory_mb - start_by_phase[snap.phase_name]

        return deltas

    def summary(self) -> str:
        """Genera resumen legible del uso de memoria."""
        if not self.snapshots:
            return "No memory data collected"

        lines = [
            f"Memory Report (peak: {self.peak_mb:.1f} MB, total delta: {self.total_delta_mb:+.1f} MB)"
        ]
        for phase, delta in self.get_phase_deltas().items():
            sign = "+" if delta >= 0 else ""
            lines.append(f"  {phase}: {sign}{delta:.1f} MB")

        if self.warnings_emitted > 0:
            lines.append(
                f"  Warnings: {self.warnings_emitted} (threshold: {self.warning_threshold_mb:.0f} MB)"
            )

        return "\n".join(lines)


class MemoryMonitor:
    """
    Monitor de memoria para el pipeline.

    Uso:
        monitor = MemoryMonitor(warning_threshold_mb=2048)

        with monitor.track_phase("parsing"):
            # ... código de la fase ...

        report = monitor.get_report()
        logger.info(report.summary())
    """

    def __init__(self, warning_threshold_mb: float = DEFAULT_MEMORY_WARNING_MB):
        """
        Args:
            warning_threshold_mb: Umbral para emitir warnings (MB).
        """
        self._report = MemoryReport(warning_threshold_mb=warning_threshold_mb)
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def snapshot(self, phase_name: str, label: str = "") -> MemorySnapshot | None:
        """
        Toma un snapshot de memoria.

        Args:
            phase_name: Nombre de la fase
            label: Etiqueta ("start", "end", o libre)

        Returns:
            MemorySnapshot o None si no se pudo medir.
        """
        if not self._enabled:
            return None

        mem = get_process_memory_mb()
        if mem < 0:
            return None

        # Calcular delta desde la última medición
        delta = 0.0
        with _monitor_lock:
            if self._report.snapshots:
                delta = mem - self._report.snapshots[-1].memory_mb

            snap = MemorySnapshot(
                phase_name=phase_name,
                timestamp=datetime.now(),
                memory_mb=mem,
                delta_mb=delta,
                label=label,
            )
            self._report.snapshots.append(snap)

            # Actualizar peak
            if mem > self._report.peak_mb:
                self._report.peak_mb = mem

            # Emitir warning si se supera umbral
            if mem > self._report.warning_threshold_mb:
                self._report.warnings_emitted += 1
                logger.warning(
                    f"Memory usage {mem:.0f} MB exceeds threshold "
                    f"{self._report.warning_threshold_mb:.0f} MB "
                    f"(phase: {phase_name}, delta: {delta:+.1f} MB)"
                )

        return snap

    @contextmanager
    def track_phase(self, phase_name: str):
        """
        Context manager que mide memoria antes y después de una fase.

        Args:
            phase_name: Nombre de la fase

        Yields:
            None

        Example:
            with monitor.track_phase("parsing"):
                do_parsing()
        """
        start_snap = self.snapshot(phase_name, label="start")
        try:
            yield
        finally:
            end_snap = self.snapshot(phase_name, label="end")

            if start_snap and end_snap and self._enabled:
                delta = end_snap.memory_mb - start_snap.memory_mb
                logger.debug(
                    f"Phase '{phase_name}' memory: "
                    f"{start_snap.memory_mb:.0f} -> {end_snap.memory_mb:.0f} MB "
                    f"(delta: {delta:+.1f} MB)"
                )

    def get_report(self) -> MemoryReport:
        """Retorna el reporte de memoria acumulado."""
        with _monitor_lock:
            return self._report

    def reset(self):
        """Resetea el monitor."""
        with _monitor_lock:
            threshold = self._report.warning_threshold_mb
            self._report = MemoryReport(warning_threshold_mb=threshold)
