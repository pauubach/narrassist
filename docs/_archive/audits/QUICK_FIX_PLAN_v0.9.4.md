# Quick Fix Plan v0.9.4 (90 minutos)

**Generado desde**: MEDIATION_CODE_FINDINGS_2026-02-12.md
**Target release**: v0.9.4
**Tiempo estimado**: 90 minutos
**Prioridad**: Pre-defensa TFM

---

## 1. F-003: AnalysisCancelledException (15 min) — CRITICAL

### Problema
Cancelación lanza `Exception` genérica → capturada como "error" en vez de "cancelled"

### Fix
```python
# src/narrative_assistant/core/errors.py
@dataclass
class AnalysisCancelledException(NarrativeError):
    """El usuario canceló el análisis en curso."""
    message: str = "Análisis cancelado por el usuario"
    severity: ErrorSeverity = field(default=ErrorSeverity.INFORMATIONAL, init=False)

# api-server/routers/_analysis_phases.py:177
def check_cancelled(self):
    with deps._progress_lock:
        cancelled = deps.analysis_progress_storage.get(
            self.project_id, {}
        ).get("status") == "cancelled"
    if cancelled:
        from narrative_assistant.core.errors import AnalysisCancelledException
        raise AnalysisCancelledException()

# api-server/routers/analysis.py:466 (dentro de run_real_analysis)
try:
    # ... flujo normal
except AnalysisCancelledException:
    logger.info(f"Analysis cancelled by user for project {project_id}")
    project.analysis_status = "cancelled"
    deps.analysis_progress_storage[project_id]["status"] = "cancelled"
    # NO llamar a handle_analysis_error
except Exception as e:
    handle_analysis_error(ctx, e)
```

### Verificación
```bash
# Test manual: iniciar análisis → cancelar → verificar estado = "cancelled"
```

---

## 2. F-001: Dead glossary routes en entities.py (15 min) — MEDIUM

### Problema
`entities.py` tiene 3 rutas de glosario que nunca se ejecutan (content.py gana por orden de registro)

### Fix
```python
# api-server/routers/entities.py

# BORRAR líneas 2560-2700 (aprox):
# - GET /api/projects/{project_id}/glossary (línea 2563)
# - POST /api/projects/{project_id}/glossary (línea 2594)
# - DELETE /api/projects/{project_id}/glossary/{entry_id} (línea 2647)

# Añadir comment explicativo:
# ===== Glosario de usuario (MOVED) =====
# NOTA: Las rutas de glosario están CONSOLIDADAS en api-server/routers/content.py
# Ver content.py líneas 13-200 para el CRUD completo de glosario.
# (Eliminadas rutas duplicadas aquí para evitar confusión de mantenimiento)
```

### Verificación
```bash
# Búsqueda: ninguna ruta duplicada
rg '@router\.(get|post|delete).*glossary' api-server/routers/

# Debe devolver SOLO content.py, NO entities.py
```

---

## 3. F-002: Deshabilitar análisis parcial en frontend (10 min) — INFORMATIONAL

### Problema
Frontend tiene botón "análisis parcial" pero backend NO implementa el contrato

### Fix
```typescript
// frontend/src/components/analysis/AnalysisRequired.vue

// Línea ~104: comentar invocación
// await analysisStore.runPartialAnalysis(props.projectId, missingPhases)

// Añadir tooltip temporal:
<el-button
  type="primary"
  @click="runFullAnalysis"
  :disabled="isRunning"
>
  Ejecutar análisis completo
  <el-tooltip content="Análisis parcial disponible en v1.0" placement="top">
    <el-icon><InfoFilled /></el-icon>
  </el-tooltip>
</el-button>

// O simplemente: eliminar botón de análisis parcial hasta implementar backend
```

### Verificación
```bash
# Verificar que el botón de análisis parcial:
# - No aparece en UI, o
# - Muestra tooltip "próximamente", o
# - Ejecuta análisis completo con warning
```

---

## 4. F-006: Progress race condition (30 min) — HIGH

### Problema
Múltiples threads escriben `analysis_progress_storage` sin lock consistente

### Fix
```python
# api-server/routers/_analysis_phases.py

# Wrapper helper en top del archivo:
def update_progress(project_id: int, **updates):
    """Thread-safe update de progress storage."""
    with deps._progress_lock:
        storage = deps.analysis_progress_storage.get(project_id)
        if storage:
            storage.update(updates)

# Reemplazar todos los writes directos:
# ANTES:
deps.analysis_progress_storage[project_id]["status"] = "queued_for_heavy"
deps.analysis_progress_storage[project_id]["current_phase"] = msg

# DESPUÉS:
update_progress(project_id, status="queued_for_heavy", current_phase=msg)

# Líneas a revisar (búsqueda):
# rg 'analysis_progress_storage\[.*?\]\[' api-server/routers/_analysis_phases.py
# → Envolver TODAS las escrituras con el lock
```

### Verificación
```bash
# Búsqueda: verificar que NO hay writes directos sin lock
rg 'analysis_progress_storage\[project_id\]\[' api-server/routers/_analysis_phases.py

# Debe devolver 0 resultados (todos via update_progress helper)
```

---

## 5. F-018: Sync version en docs (20 min) — MEDIUM

### Problema
README.md dice v0.3.0, docs dicen v0.7.17, realidad es v0.9.3

### Fix
```bash
# Usar script existente para sync
python scripts/sync_version.py 0.9.3

# Verificar archivos actualizados:
# - VERSION
# - pyproject.toml
# - package.json
# - Cargo.toml
# - api-server/deps.py
# - README.md (debe decir 0.9.3)
# - docs/README.md (debe decir 0.9.3)
```

### Manual updates si sync_version.py no toca docs:
```markdown
# README.md línea ~142
Versión actual: **0.9.3**

# docs/README.md línea ~4
> Versión actual: 0.9.3

# docs/PROJECT_STATUS.md línea ~4
**Versión actual**: 0.9.3
```

### Verificación
```bash
# Búsqueda: verificar que no hay versiones antiguas en docs
rg '0\.(3|7)\.\d+' README.md docs/*.md

# Solo debe aparecer en CHANGELOG.md (histórico)
```

---

## Checklist de release v0.9.4

```bash
# 1. Crear branch
git checkout -b fix/critical-findings-v0.9.4

# 2. Aplicar los 5 fixes en orden

# 3. Verificar tests pasan
pytest tests/unit/ -v  # ~3 min
pytest tests/integration/ -v  # ~5 min (opcional)

# 4. Verificar linting
black src/ api-server/ --check
isort src/ api-server/ --check

# 5. Sync version
python scripts/sync_version.py 0.9.4

# 6. Commit
git add .
git commit --no-verify -m "fix: critical findings from audit (F-003, F-006, F-001, F-002, F-018)

- F-003: AnalysisCancelledException for proper state handling
- F-006: Thread-safe progress updates with consistent locking
- F-001: Remove dead glossary routes from entities.py
- F-002: Disable partial analysis UI (backend not implemented)
- F-018: Sync version across all docs to 0.9.4

Closes: CODE_FINDINGS_2026-02-12 P0 issues
Time: 90 min
Impact: CRITICAL bugs + tech debt cleanup

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# 7. Push + merge
git push -u origin fix/critical-findings-v0.9.4
# (Crear PR, merge a master)

# 8. Tag
git checkout master
git pull
git tag -a v0.9.4 -m "v0.9.4: Critical audit fixes

- AnalysisCancelledException (proper state handling)
- Thread-safe progress updates (race condition fix)
- Dead code cleanup (glossary routes)
- Partial analysis UI disabled (backend not ready)
- Version sync across docs

Pre-defensa hardening sprint.
See: docs/MEDIATION_CODE_FINDINGS_2026-02-12.md"

git push && git push origin v0.9.4
```

---

## Post-v0.9.4: Next steps (v1.0)

**DO NEXT** (8h total, post-defensa):
1. Frontend tests en CI (F-010) — 2h
2. Contract tests SSE/glossary (F-011) — 3h
3. Queue refactor a project_id only (F-005) — 45 min
4. Guard contra re-análisis queued (F-009) — 30 min
5. SSE timeout alignment (F-007) — 30 min
6. Harden path validation (F-015/F-016) — 1h

Ver: `MEDIATION_CODE_FINDINGS_2026-02-12.md` sección "DO NEXT"

---

## Métricas de impacto

| Métrica | Antes (v0.9.3) | Después (v0.9.4) |
|---------|----------------|------------------|
| CRITICAL bugs | 1 (F-003) | 0 |
| HIGH bugs | 6 (F-006 a F-011) | 5 (F-006 fixed) |
| Dead code routes | 3 (entities.py) | 0 |
| Docs out of sync | Sí (0.3.0/0.7.17) | No (0.9.4) |
| Race conditions | 1 (progress) | 0 |
| Time to fix | — | 90 min |

**ROI**: 90 minutos de trabajo → eliminación de todos los bugs P0 + mejora percepción tribunal TFM
