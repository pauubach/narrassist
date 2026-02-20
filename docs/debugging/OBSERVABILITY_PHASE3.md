# Observabilidad Fase 3 (A/B/C/D)

## Objetivo
Tener trazabilidad operativa de:
- identidad de manuscrito (bloqueos y `uncertain`),
- decisiones del planner incremental,
- tiempos por fase y modo de ejecución (`full`/`incremental`/`fast_path`).

## Señales a revisar en logs
1. `replace_project_document`:
- clasificación (`same_document` / `uncertain` / `different_document`),
- confianza,
- `uncertain_count_30d` y umbral activo.

2. `[INCREMENTAL_PLAN]`:
- `mode`,
- `reason`,
- `impacted`,
- `chapter_diff`.

3. cierre de análisis:
- `run_mode`,
- `duration_total_sec`,
- `phase_durations_json`.

## Consultas SQL de diagnóstico
1. Últimos checks de identidad:
```sql
SELECT project_id, classification, confidence, score, created_at
FROM manuscript_identity_checks
ORDER BY id DESC
LIMIT 50;
```

2. Riesgo por licencia (`uncertain` rolling):
```sql
SELECT license_subject, uncertain_count_30d, review_required, updated_at
FROM manuscript_identity_risk_state
ORDER BY updated_at DESC;
```

3. Versiones y modo de ejecución:
```sql
SELECT project_id, version_num, run_mode, duration_total_sec, created_at
FROM version_metrics
ORDER BY id DESC
LIMIT 100;
```

4. Renombres detectados por versión:
```sql
SELECT evl.project_id, evl.snapshot_id, evl.old_name, evl.new_name, evl.confidence, evl.created_at
FROM entity_version_links evl
WHERE evl.link_type = 'renamed'
ORDER BY evl.created_at DESC
LIMIT 100;
```

## Playbook rápido de incidentes
1. Reanálisis no acelera:
- comprobar log `[INCREMENTAL_PLAN]` y si se está yendo a `full`,
- verificar `chapter_diff.changed_ratio` y capítulos añadidos/eliminados.

2. Muchos `uncertain` en poco tiempo:
- revisar `manuscript_identity_risk_state`,
- confirmar umbral (`identity_uncertain_limit_30d`),
- validar si la licencia debe pasar a revisión manual.

3. Renombres no aparecen en historial:
- verificar `entity_version_links` para `snapshot_id` de la versión,
- revisar que `version_diffs.snapshot_id` esté poblado.

4. Diferencias UI vs backend en versiones:
- contrastar `/api/projects/{id}/versions` con SQL directo de `version_metrics` y `version_diffs`.
