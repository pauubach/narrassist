# Implementación F-003: AnalysisCancelledException

**Issue**: Cancelación lanza Exception genérica → manejada como "error"
**Severidad**: CRITICAL
**Time estimate**: 15 minutos
**Files affected**: 3

---

## Cambio 1: Definir excepción específica

**File**: `src/narrative_assistant/core/errors.py`

**Ubicación**: Después de línea ~320 (sección de errores operacionales)

```python
@dataclass
class AnalysisCancelledException(NarrativeError):
    """
    El usuario canceló el análisis en curso.

    Esta excepción NO es un error - es una operación normal solicitada
    por el usuario. Debe ser manejada fuera del flujo de error estándar.

    Args:
        message: Mensaje descriptivo de la cancelación

    Severity: INFORMATIONAL (no es un error real)
    """
    message: str = "Análisis cancelado por el usuario"
    severity: ErrorSeverity = field(default=ErrorSeverity.INFORMATIONAL, init=False)
```

**Actualizar exports** (si existe sección `__all__`):
```python
__all__ = [
    # ... existentes
    "AnalysisCancelledException",
]
```

---

## Cambio 2: Lanzar excepción tipada en check

**File**: `api-server/routers/_analysis_phases.py`

**Línea ~170-177** (método `ProgressTracker.check_cancelled`):

```python
def check_cancelled(self):
    """Verifica si el análisis fue cancelado por el usuario."""
    with deps._progress_lock:
        cancelled = deps.analysis_progress_storage.get(
            self.project_id, {}
        ).get("status") == "cancelled"
    if cancelled:
        # CAMBIO: usar excepción tipada en vez de Exception genérica
        from narrative_assistant.core.errors import AnalysisCancelledException
        raise AnalysisCancelledException(
            f"Análisis del proyecto {self.project_id} cancelado por el usuario"
        )
```

**Imports** (añadir al top del archivo si no existe):
```python
from narrative_assistant.core.errors import (
    AnalysisCancelledException,  # NUEVO
    # ... otros imports existentes
)
```

---

## Cambio 3: Captura específica en orquestador

**File**: `api-server/routers/analysis.py`

**Línea ~466-470** (dentro de función `run_real_analysis`, bloque try-except):

**ANTES**:
```python
try:
    # ... todo el flujo de análisis
    run_tier1_parsing(ctx, tracker)
    # ... etc
except Exception as e:
    handle_analysis_error(ctx, e)
finally:
    run_finally_cleanup(ctx)
```

**DESPUÉS**:
```python
try:
    # ... todo el flujo de análisis
    run_tier1_parsing(ctx, tracker)
    # ... etc

except AnalysisCancelledException as cancel_ex:
    # Cancelación del usuario - NO es un error, manejar aparte
    logger.info(
        f"Analysis for project {project_id} cancelled by user: {cancel_ex.message}"
    )

    # Asegurar estado final correcto
    with deps._progress_lock:
        deps.analysis_progress_storage[project_id]["status"] = "cancelled"
        deps.analysis_progress_storage[project_id]["current_phase"] = (
            "Análisis cancelado por el usuario"
        )
        deps.analysis_progress_storage[project_id]["current_action"] = ""

    # Actualizar BD
    try:
        project.analysis_status = "cancelled"
        deps.project_manager.update(project)
    except Exception as db_err:
        logger.warning(f"Could not persist cancelled status to DB: {db_err}")

    # NO llamar a handle_analysis_error (no es un error)

except Exception as e:
    # Error real - flujo existente
    handle_analysis_error(ctx, e)

finally:
    run_finally_cleanup(ctx)
```

**Imports** (añadir al top del archivo):
```python
from narrative_assistant.core.errors import AnalysisCancelledException
```

---

## Cambio 4 (OPCIONAL): Error handler más defensivo

**File**: `api-server/routers/_analysis_phases.py`

**Línea ~2886-2910** (función `handle_analysis_error`):

Añadir check explícito al inicio:
```python
def handle_analysis_error(ctx: dict, error: Exception):
    """Maneja errores durante el análisis."""
    from narrative_assistant.core.errors import (
        AnalysisCancelledException,
        ModelNotLoadedError,
    )
    from narrative_assistant.persistence.project import ProjectManager

    # NUEVO: sanity check - cancelación NO debe llegar aquí
    if isinstance(error, AnalysisCancelledException):
        logger.warning(
            "AnalysisCancelledException reached error handler - this should not happen. "
            "Check exception handling in run_real_analysis()"
        )
        # Manejar defensivamente de todas formas
        ctx["project"].analysis_status = "cancelled"
        deps.analysis_progress_storage[ctx["project_id"]]["status"] = "cancelled"
        return

    # ... resto del handler existente
    project_id = ctx["project_id"]
    project = ctx["project"]

    logger.exception(f"Error during analysis for project {project_id}: {error}")
    deps.analysis_progress_storage[project_id]["status"] = "error"
    # ... etc
```

---

## Testing

### Test manual (UI)

1. Iniciar análisis de un documento grande (>50 páginas)
2. Durante fase "Extrayendo entidades" → Click "Cancelar"
3. **Verificar**:
   - Estado final = "cancelled" (NO "error")
   - Mensaje = "Análisis cancelado por el usuario"
   - NO hay stack trace en logs
   - Log dice `INFO: Analysis cancelled by user` (NO `ERROR: ...`)

### Test unitario (opcional)

```python
# tests/unit/test_analysis_cancellation.py

import pytest
from narrative_assistant.core.errors import AnalysisCancelledException, ErrorSeverity


def test_analysis_cancelled_exception_severity():
    """Verificar que cancelación NO es un error (severity INFORMATIONAL)."""
    exc = AnalysisCancelledException()
    assert exc.severity == ErrorSeverity.INFORMATIONAL
    assert "cancelado" in exc.message.lower()


def test_analysis_cancelled_distinguishable():
    """Verificar que se puede capturar específicamente."""
    def raise_cancelled():
        raise AnalysisCancelledException("Test cancel")

    with pytest.raises(AnalysisCancelledException) as exc_info:
        raise_cancelled()

    assert exc_info.value.message == "Test cancel"
    assert not isinstance(exc_info.value, ValueError)  # No es Exception genérica
```

### Test de integración (opcional)

```python
# tests/integration/test_analysis_cancellation_flow.py

import time
import pytest
from api-server import deps
from api-server.routers.analysis import start_analysis, cancel_analysis


@pytest.mark.integration
def test_cancellation_sets_correct_state(test_project):
    """Verificar que cancelar análisis establece estado 'cancelled' (no 'error')."""
    project_id = test_project.id

    # Iniciar análisis
    response = start_analysis(project_id, file=None)
    assert response.success

    # Esperar que empiece
    time.sleep(1)

    # Cancelar
    cancel_response = cancel_analysis(project_id)
    assert cancel_response.success

    # Esperar a que el thread procese la cancelación
    time.sleep(2)

    # Verificar estado final
    storage = deps.analysis_progress_storage[project_id]
    assert storage["status"] == "cancelled", f"Expected 'cancelled', got {storage['status']}"
    assert "cancelado" in storage["current_phase"].lower()

    # Verificar BD
    project = deps.project_manager.get(project_id).value
    assert project.analysis_status == "cancelled"
```

---

## Verificación de código

### Pre-commit checks

```bash
# Linting
black src/narrative_assistant/core/errors.py api-server/routers/
isort src/narrative_assistant/core/errors.py api-server/routers/

# Type checking
mypy src/narrative_assistant/core/errors.py
mypy api-server/routers/analysis.py
mypy api-server/routers/_analysis_phases.py

# Tests
pytest tests/unit/test_analysis_cancellation.py -v
pytest tests/integration/test_analysis_cancellation_flow.py -v -m integration
```

### Búsqueda de regresiones

```bash
# Verificar que NO hay otros lugares lanzando Exception por cancelación
rg 'raise Exception.*cancel' --type py

# Debe devolver 0 resultados (todos cambiados a AnalysisCancelledException)
```

---

## Rollback plan

Si algo falla en producción:

```python
# Revertir cambio 3 (analysis.py) temporalmente:
except Exception as e:
    # Catch-all temporal mientras se debuggea
    if "cancel" in str(e).lower():
        logger.info(f"Analysis cancelled for project {project_id}")
        project.analysis_status = "cancelled"
        deps.analysis_progress_storage[project_id]["status"] = "cancelled"
    else:
        handle_analysis_error(ctx, e)
```

---

## Métricas de éxito

| Métrica | Target |
|---------|--------|
| Estado final de cancelación | `"cancelled"` (100%) |
| Log level de cancelación | `INFO` (no `ERROR`) |
| Stack traces por cancelación | 0 |
| Tests de regresión | Pass (100%) |
| Time to implement | <15 min |

---

## Referencias

- **Issue original**: CODE_FINDINGS_2026-02-12, F-003
- **Mediación**: MEDIATION_CODE_FINDINGS_2026-02-12.md
- **Severity**: CRITICAL → FIXED en v0.9.4
- **Related**: F-006 (race condition en progress storage - fix separado)

---

**Notas de implementación**:
- Este fix NO requiere cambios en frontend (ya maneja estado "cancelled")
- Frontend ya tiene lógica para mostrar "cancelado" vs "error" en UI
- La DB schema ya soporta `analysis_status = 'cancelled'`
- NO hay breaking changes de API

**Riesgo de regresión**: BAJO
- Exception handling es defense-in-depth (finally block siempre ejecuta)
- Si la nueva excepción no se captura, el catch-all Exception sigue funcionando
- Worst case: comportamiento = v0.9.3 actual (cancelled reportado como error)
