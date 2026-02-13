# Análisis Progresivo y UX en Tiempo Real

[← Volver a Arquitectura](./README.md) | [← Índice principal](../../README.md)

> **DEPRECATED (2026-02-13)**: Este documento describe el diseño original del pipeline progresivo.
> La implementación actual usa `UnifiedAnalysisPipeline` con 8 fases
> (ver [enums-reference.md](./enums-reference.md#fases-de-análisis-analysisphase)).
> Los conceptos de progreso y event bus siguen vigentes pero las fases concretas,
> pesos y código de ejemplo NO reflejan el sistema actual.

---

## Principio Fundamental

> **El usuario debe poder trabajar desde el primer momento.**
> No esperar a que termine todo el análisis para empezar a revisar hallazgos.

---

## Arquitectura de Pipeline Progresivo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE DE ANÁLISIS PROGRESIVO                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  PASO 1  │───▶│  PASO 2  │───▶│  PASO 3  │───▶│  PASO N  │              │
│  │  Parser  │    │   NER    │    │  Coref   │    │   ...    │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │               │                     │
│       ▼               ▼               ▼               ▼                     │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    EVENT BUS (Pub/Sub)                       │           │
│  └─────────────────────────────────────────────────────────────┘           │
│       │               │               │               │                     │
│       ▼               ▼               ▼               ▼                     │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                         UI LAYER                             │           │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │           │
│  │  │ Status Bar  │  │   Results   │  │   Alerts    │          │           │
│  │  │ (progreso)  │  │   Panel     │  │   Panel     │          │           │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Fases de Análisis y Disponibilidad

| Fase | Paso | Qué detecta | Disponible para usuario |
|------|------|-------------|------------------------|
| 1 | Parser DOCX | Estructura básica | ✅ Inmediato |
| 1 | Detector capítulos | Divisiones | ✅ Tras ~2s |
| 1 | Detector diálogos | Intervenciones | ✅ Tras ~5s |
| 1 | NER básico | Entidades | ✅ Tras ~10s |
| 2 | Correferencia | Cadenas | ✅ Tras ~30s |
| 2 | Fusión entidades | Sugerencias | ✅ Tras ~35s |
| 2 | Atributos | Físicos, etc. | ✅ Tras ~45s |
| 2 | Inconsistencias | Alertas básicas | ✅ Tras ~60s |
| 3+ | Repeticiones | Alertas estilo | ✅ Progresivo |
| 3+ | Temporalidad | Timeline | ✅ Progresivo |
| 3+ | Voz | Perfiles | ✅ Progresivo |

**Tiempos estimados para novela de ~80.000 palabras**

---

## Estados de Análisis

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

class AnalysisPhase(Enum):
    PENDING = "pending"           # No iniciado
    PARSING = "parsing"           # Leyendo DOCX
    STRUCTURE = "structure"       # Detectando capítulos/escenas
    NER = "ner"                   # Reconocimiento de entidades
    COREFERENCE = "coreference"   # Resolución de correferencias
    ATTRIBUTES = "attributes"     # Extracción de atributos
    CONSISTENCY = "consistency"   # Verificación de consistencia
    STYLE = "style"               # Análisis de estilo
    VOICE = "voice"               # Perfiles de voz
    TEMPORAL = "temporal"         # Análisis temporal
    COMPLETE = "complete"         # Finalizado
    ERROR = "error"               # Error en algún paso

@dataclass
class AnalysisProgress:
    project_id: int
    current_phase: AnalysisPhase
    phase_progress: float  # 0.0 - 1.0 dentro de la fase
    overall_progress: float  # 0.0 - 1.0 total

    # Métricas parciales
    chapters_found: int = 0
    entities_found: int = 0
    dialogues_found: int = 0
    alerts_generated: int = 0

    # Timing
    started_at: Optional[datetime] = None
    estimated_remaining: Optional[int] = None  # segundos

    # Mensajes para UI
    status_message: str = ""
    current_action: str = ""

class ProgressTracker:
    """Rastrea y notifica el progreso del análisis."""

    PHASE_WEIGHTS = {
        AnalysisPhase.PARSING: 0.05,
        AnalysisPhase.STRUCTURE: 0.05,
        AnalysisPhase.NER: 0.15,
        AnalysisPhase.COREFERENCE: 0.20,
        AnalysisPhase.ATTRIBUTES: 0.15,
        AnalysisPhase.CONSISTENCY: 0.15,
        AnalysisPhase.STYLE: 0.10,
        AnalysisPhase.VOICE: 0.10,
        AnalysisPhase.TEMPORAL: 0.05,
    }

    def __init__(self, project_id: int, event_bus: 'EventBus'):
        self.project_id = project_id
        self.event_bus = event_bus
        self.progress = AnalysisProgress(
            project_id=project_id,
            current_phase=AnalysisPhase.PENDING,
            phase_progress=0.0,
            overall_progress=0.0
        )

    def start_phase(self, phase: AnalysisPhase) -> None:
        """Inicia una nueva fase de análisis."""
        self.progress.current_phase = phase
        self.progress.phase_progress = 0.0
        self.progress.status_message = self._get_phase_message(phase)
        self._notify()

    def update_phase_progress(
        self,
        progress: float,
        action: str = ""
    ) -> None:
        """Actualiza el progreso dentro de la fase actual."""
        self.progress.phase_progress = min(1.0, progress)
        self.progress.current_action = action
        self._calculate_overall_progress()
        self._notify()

    def complete_phase(self) -> None:
        """Marca la fase actual como completada."""
        self.progress.phase_progress = 1.0
        self._calculate_overall_progress()
        self._notify()

    def add_finding(self, finding_type: str, count: int = 1) -> None:
        """Registra un hallazgo (entidad, alerta, etc.)."""
        if finding_type == 'entity':
            self.progress.entities_found += count
        elif finding_type == 'chapter':
            self.progress.chapters_found += count
        elif finding_type == 'dialogue':
            self.progress.dialogues_found += count
        elif finding_type == 'alert':
            self.progress.alerts_generated += count

        # Notificar hallazgo inmediatamente
        self.event_bus.emit('finding_added', {
            'type': finding_type,
            'count': count,
            'total': getattr(self.progress, f'{finding_type}s_found', count)
        })

    def _calculate_overall_progress(self) -> None:
        """Calcula el progreso total basado en pesos de fases."""
        completed_weight = 0.0
        current_weight = 0.0

        phases = list(self.PHASE_WEIGHTS.keys())
        current_idx = phases.index(self.progress.current_phase) \
            if self.progress.current_phase in phases else 0

        # Sumar pesos de fases completadas
        for i, phase in enumerate(phases):
            if i < current_idx:
                completed_weight += self.PHASE_WEIGHTS[phase]
            elif i == current_idx:
                current_weight = self.PHASE_WEIGHTS[phase] * self.progress.phase_progress

        self.progress.overall_progress = completed_weight + current_weight

    def _get_phase_message(self, phase: AnalysisPhase) -> str:
        """Devuelve mensaje descriptivo para la UI."""
        messages = {
            AnalysisPhase.PARSING: "Leyendo documento...",
            AnalysisPhase.STRUCTURE: "Detectando estructura (capítulos, escenas)...",
            AnalysisPhase.NER: "Identificando personajes y lugares...",
            AnalysisPhase.COREFERENCE: "Resolviendo referencias (él, ella, etc.)...",
            AnalysisPhase.ATTRIBUTES: "Extrayendo características de personajes...",
            AnalysisPhase.CONSISTENCY: "Verificando consistencia...",
            AnalysisPhase.STYLE: "Analizando estilo y repeticiones...",
            AnalysisPhase.VOICE: "Construyendo perfiles de voz...",
            AnalysisPhase.TEMPORAL: "Analizando línea temporal...",
            AnalysisPhase.COMPLETE: "Análisis completado",
        }
        return messages.get(phase, "Procesando...")

    def _notify(self) -> None:
        """Notifica cambio de progreso a la UI."""
        self.event_bus.emit('progress_updated', self.progress)
```

---

## Event Bus para Comunicación

```python
from typing import Callable, Dict, List, Any
from collections import defaultdict
import threading

class EventBus:
    """Bus de eventos para comunicación entre análisis y UI."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Suscribe un callback a un tipo de evento."""
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Desuscribe un callback."""
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def emit(self, event_type: str, data: Any = None) -> None:
        """Emite un evento a todos los suscriptores."""
        with self._lock:
            callbacks = self._subscribers[event_type].copy()

        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                # Log error pero no detener el análisis
                print(f"Error en callback de evento {event_type}: {e}")

# Tipos de eventos
EVENTS = {
    'progress_updated': 'Progreso de análisis actualizado',
    'finding_added': 'Nuevo hallazgo (entidad, alerta, etc.)',
    'phase_started': 'Nueva fase iniciada',
    'phase_completed': 'Fase completada',
    'analysis_complete': 'Análisis finalizado',
    'analysis_error': 'Error en análisis',
    'entity_detected': 'Entidad detectada',
    'alert_created': 'Alerta creada',
    'inconsistency_found': 'Inconsistencia encontrada',
}
```

---

## Integración con UI (Barra de Estado)

```python
class StatusBarController:
    """Controlador para la barra de estado de la UI."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        self.event_bus.subscribe('progress_updated', self._on_progress)
        self.event_bus.subscribe('finding_added', self._on_finding)
        self.event_bus.subscribe('analysis_error', self._on_error)

    def _on_progress(self, progress: AnalysisProgress) -> None:
        """Actualiza la barra de estado con el progreso."""
        # Formato: [████████░░░░] 65% - Analizando estilo...
        bar_width = 20
        filled = int(bar_width * progress.overall_progress)
        empty = bar_width - filled

        bar = '█' * filled + '░' * empty
        percentage = int(progress.overall_progress * 100)

        status_line = f"[{bar}] {percentage}% - {progress.status_message}"

        if progress.current_action:
            status_line += f" ({progress.current_action})"

        # Enviar a UI (depende de implementación)
        self._update_ui_status_bar(status_line)

        # Mostrar métricas parciales
        metrics = []
        if progress.chapters_found:
            metrics.append(f"{progress.chapters_found} capítulos")
        if progress.entities_found:
            metrics.append(f"{progress.entities_found} entidades")
        if progress.alerts_generated:
            metrics.append(f"{progress.alerts_generated} alertas")

        if metrics:
            self._update_ui_metrics(", ".join(metrics))

    def _on_finding(self, data: dict) -> None:
        """Muestra notificación de nuevo hallazgo."""
        # Notificación sutil que no interrumpe el trabajo
        if data['type'] == 'alert' and data.get('severity') == 'critical':
            self._show_notification(f"⚠️ Alerta crítica detectada")

    def _on_error(self, error: dict) -> None:
        """Muestra error sin detener la UI."""
        self._show_error(f"Error en análisis: {error.get('message', 'desconocido')}")

    def _update_ui_status_bar(self, text: str) -> None:
        """Actualiza la barra de estado (implementar según UI)."""
        print(f"\r{text}", end='', flush=True)  # CLI simple

    def _update_ui_metrics(self, text: str) -> None:
        """Actualiza métricas en UI."""
        pass  # Implementar según UI

    def _show_notification(self, text: str) -> None:
        """Muestra notificación."""
        pass  # Implementar según UI

    def _show_error(self, text: str) -> None:
        """Muestra error."""
        pass  # Implementar según UI
```

---

## Ejemplo de Flujo Completo

```python
async def analyze_with_progress(file_path: str, project_id: int):
    """Análisis con progreso en tiempo real."""

    event_bus = EventBus()
    tracker = ProgressTracker(project_id, event_bus)
    status_bar = StatusBarController(event_bus)

    # El usuario ya puede ver la UI vacía y la barra de estado

    # Fase 1: Parsing
    tracker.start_phase(AnalysisPhase.PARSING)
    document = parse_docx(file_path)
    tracker.complete_phase()
    # Usuario ve: [██░░░░░░░░░░░░░░░░░░] 5% - Leyendo documento...

    # Fase 2: Estructura
    tracker.start_phase(AnalysisPhase.STRUCTURE)
    for i, chapter in enumerate(detect_chapters(document)):
        tracker.add_finding('chapter')
        tracker.update_phase_progress(i / estimated_chapters, f"Capítulo {i}")
        # Usuario puede ver capítulos detectados en tiempo real
    tracker.complete_phase()
    # Usuario ve: [████░░░░░░░░░░░░░░░░] 10% - Detectando estructura...
    # Y ya puede navegar por capítulos!

    # Fase 3: NER
    tracker.start_phase(AnalysisPhase.NER)
    for i, paragraph in enumerate(document.paragraphs):
        entities = ner_pipeline(paragraph)
        for entity in entities:
            tracker.add_finding('entity')
            # Usuario ve entidades aparecer en el panel
        tracker.update_phase_progress(i / len(document.paragraphs))
    tracker.complete_phase()
    # Usuario ya puede ver lista de personajes!

    # ... continúa con más fases ...

    event_bus.emit('analysis_complete', {'project_id': project_id})
```

---

## Siguiente

Ver [Sistema de Historial y Estados](./history-system.md) para entender cómo se gestionan los estados de las alertas y el historial de cambios.
