# Auditoria Integral de la Aplicacion (Codex)

Fecha: 2026-02-14
Repositorio auditado: `d:\repos\tfm`
Rama/estado: `master` con cambios locales no relacionados ya presentes

## 1. Resumen ejecutivo

Esta auditoria cubre arquitectura, code review, tipado/firmas, testing, pipelines, documentacion, funcionalidad, optimizacion de BD, riesgos de seguridad, compatibilidad Win/mac y deuda tecnica.

Conclusion global:
- El producto tiene amplitud funcional alta y una base de tests unitarios extensa.
- La calidad de entrega real esta limitada por deuda de tipado severa, puertas de CI no bloqueantes, deriva documentacion-codigo y fragilidad de build desktop local.
- Hay riesgos de rendimiento/escala en consultas SQL basadas en `LIKE` sobre campos serializados.
- Se confirma que hay funcionalidades marcadas como "por implementar", por lo que no debe afirmarse "completo" sin matizar alcance.

## 2. Alcance revisado

Se revisaron:
- Arquitectura monorepo (Python core + FastAPI + Vue/TS + Tauri/Rust).
- Calidad de codigo (lint, type checks, firmas, contratos).
- Calidad de pruebas y cobertura.
- Pipeline CI/CD y release.
- Consistencia documentacion vs implementacion.
- Seguridad de dependencias.
- Persistencia y patrones de consulta BD.
- Compatibilidad de build para Windows y macOS.
- Deuda tecnica y riesgos futuros.
- Propuesta de nuevas ideas.

## 3. Metodologia y comprobaciones ejecutadas

### Backend Python
- `python -m ruff check src tests api-server`
- `python -m mypy src/narrative_assistant --ignore-missing-imports`
- `pytest tests/unit -q`
- `pytest tests/integration -m integration -q`
- `pytest tests/unit --cov=src/narrative_assistant --cov-report=term --maxfail=1`

### Frontend Vue/TS
- `npm run type-check`
- `npm run test:coverage`
- `npm run build`
- `npm audit --audit-level=high`

### Desktop Rust/Tauri
- `cargo check` en `src-tauri`

### Revision de codigo/documentacion
- Analisis de rutas API en `api-server/routers/**`
- Contraste con `docs/api-reference/http-endpoints.md`
- Revision de workflows en `.github/workflows/*.yml`
- Revision de configuraciones de test (`pytest.ini`, `frontend/vitest.config.ts`)

## 4. Resultados objetivos de ejecucion

### 4.1 Backend: calidad y tipos
- `ruff`: OK (sin errores).
- `mypy`: FALLA con **1136 errores en 145 archivos**.
- Principal concentracion de errores: `analysis_pipeline.py`, `cli.py`, varios modulos NLP/style/licensing.

### 4.2 Backend: tests y cobertura
- Unit tests: **1890 passed, 4 skipped, 198 deselected**.
- Integration (`-m integration`): **5 passed, 61 deselected**.
- Cobertura backend total (`src/narrative_assistant`): **39%**.

### 4.3 Frontend: build, tipos, tests, cobertura
- `type-check`: OK.
- Tests: **16 files, 452 tests passed**.
- Build: OK.
- Cobertura reportada: **0% global** (indicador no fiable, pipeline de cobertura roto/mal instrumentado).

### 4.4 Seguridad dependencias
- `npm audit`: **1 vulnerabilidad alta** en `axios` (instalado `1.13.4`), advisory `GHSA-43fc-jf86-j433`.

### 4.5 Desktop Win/mac
- `cargo check` falla por recurso faltante:
  - `resource path binaries\\python-embed doesn't exist`
- El bundle Tauri exige recursos:
  - `src-tauri/tauri.conf.json` incluye `binaries/python-embed/` y `binaries/backend/`.

## 5. Hallazgos (priorizados por severidad)

## Criticos

1. Deuda de tipado severa y contratos no confiables
- Evidencia:
  - `mypy` falla con 1136 errores.
  - El pipeline legacy aun se exporta y usa:
    - `src/narrative_assistant/pipelines/__init__.py`
    - `src/narrative_assistant/cli.py`
- Impacto:
  - Riesgo alto de regresiones silenciosas, APIs internas inconsistentes y baja mantenibilidad.

2. Inconsistencias de modelo en pipeline legacy deprecado
- Evidencia:
  - `AlertSeverity` define `CRITICAL`, `WARNING`, `INFO`, `HINT` en `src/narrative_assistant/alerts/models.py`.
  - Se usa `AlertSeverity.SUGGESTION` en `src/narrative_assistant/pipelines/analysis_pipeline.py` (lineas ~2398 y ~2557).
- Impacto:
  - Riesgo de fallo en tiempo de ejecucion si esos caminos se activan.

3. CI no bloquea checks clave
- Evidencia en `.github/workflows/ci.yml`:
  - `mypy ... || true`
  - `npm run test:run || true`
  - `pytest tests/integration ... || true`
  - `pytest tests/performance ... || true`
- Impacto:
  - El pipeline puede aparecer "verde" aun con regresiones reales.

4. Build desktop local no reproducible por dependencia de recursos externos
- Evidencia:
  - `cargo check` falla por falta de `binaries/python-embed`.
  - Configuracion Tauri requiere recursos en bundle.
- Impacto:
  - Fragilidad de release y de onboarding tecnico Win/mac.

## Altos

5. Cobertura backend insuficiente para el tamano del sistema
- Evidencia:
  - Total 39%.
  - Modulos de alto riesgo con coberturas bajas (pipelines/NLP/exporters/scenes en rangos bajos).
- Impacto:
  - Riesgo elevado de regresion funcional y de precision algoritimica.

6. Cobertura frontend no usable (0% con tests pasando)
- Evidencia:
  - `vitest` reporta 452 tests OK y cobertura 0%.
  - Config en `frontend/vitest.config.ts` parece definida, pero el resultado no representa ejecucion real.
- Impacto:
  - No existe medicion real de riesgo en frontend.

7. Deriva documentacion-codigo (versionado y API)
- Evidencia:
  - Version runtime/paquetes: 0.9.5 (`README.md`, `pyproject.toml`, `frontend/package.json`, `src-tauri/tauri.conf.json`).
  - `docs/BUILD_AND_DEPLOY.md` mantiene `0.9.4` y comandos historicos `v0.3.x`.
  - `docs/api-reference/http-endpoints.md` documenta ~23 endpoints mientras se detectan ~236 rutas en routers.
- Impacto:
  - Mala trazabilidad, errores de integracion y soporte.

8. Completitud funcional no cerrada en todos los ambitos
- Evidencia:
  - En `api-server/routers/projects.py` (`analysis-status`) aparecen en `False` y comentados "Por implementar":
    - `interactions`, `emotional`, `sentiment`, `focalization`.
- Impacto:
  - Riesgo de sobrepromesa funcional y expectativas no cumplidas.

9. Riesgo de rendimiento BD por `LIKE` sobre datos serializados
- Evidencia:
  - `scene_tags.participant_ids LIKE ?` en `src/narrative_assistant/scenes/repository.py`.
  - `variants_json LIKE ?` en `src/narrative_assistant/persistence/glossary.py`.
  - `merged_from_ids LIKE ?` en `src/narrative_assistant/entities/repository.py`.
- Impacto:
  - Escala deficiente, planes de consulta suboptimos y falsos positivos de matching.

## Medios

10. Inconsistencia de prefijos API (`/api` vs rutas sin prefijo)
- Evidencia:
  - `collections.py` define rutas `/collections` y `/projects/...` sin `/api`.
  - El frontend/base y docs referencian base `/api`.
- Impacto:
  - Potenciales desajustes de consumo, proxy y documentacion.

11. Modulos sobredimensionados (complejidad ciclomatica operativa)
- Ejemplos:
  - `analysis_pipeline.py` ~2786 lineas
  - `prose.py` ~2070 lineas
  - `relationships.py` ~1913 lineas
- Impacto:
  - Dificultad de mantenimiento, revision y testeo incremental.

12. Riesgo de seguridad por dependencia vulnerable
- Evidencia:
  - `axios 1.13.4` afectado por advisory alta severidad.
- Impacto:
  - Superficie de ataque en cliente (DoS via mergeConfig + `__proto__`).

## 6. Revision por dominios solicitados

### 6.1 Arquitectura
- Fortalezas:
  - Separacion clara de capas (core, API, frontend, desktop).
  - Dominio rico y amplio.
- Debilidades:
  - Acoplamiento historico por coexistencia de pipeline legacy y unificado.
  - Routers muy grandes y alta dispersion de endpoints sin catalogo fuente unico.

### 6.2 Peer review de codigo
- Fortalezas:
  - Estilo/lint relativamente limpio.
  - Numerosos tests de unidad.
- Debilidades:
  - Contratos de tipos muy degradados.
  - Uso de APIs potencialmente no existentes desde legacy.
  - Complejidad excesiva en algunos modulos.

### 6.3 Algoritmos (optimos/no optimos)
- Lo observado:
  - Muchos analizadores especializados y heuristicas.
  - No hay evidencia de benchmark continuo centralizado por detector en CI.
- Riesgo:
  - Dificil validar "optimo" sin baseline de precision/latencia y corpus de regresion estable.

### 6.4 Funcionalidad
- Cobertura funcional amplia.
- Existen capacidades aun marcadas "por implementar", por tanto no todo el alcance esta cerrado.

### 6.5 Pipeline y release
- CI ejecuta varios checks importantes como informativos no bloqueantes.
- Build desktop depende de artefactos/resources externos al flujo local limpio.

### 6.6 Textos y documentacion
- Hay deriva de version y deriva de catalogo de endpoints.
- Riesgo de que documentacion no refleje comportamiento real.

### 6.7 Firmas, tipos y contratos
- Este es uno de los puntos mas debiles del estado actual (mypy muy lejos de verde).
- Inconsistencias de enums/atributos detectadas en legacy.

### 6.8 Testing
- Gran volumen de tests unitarios.
- Cobertura total aun baja para el tamano de codigo.
- Frontend coverage report no refleja la realidad.

### 6.9 Optimizacion BD
- Existen indices de esquema en muchas tablas, lo cual es positivo.
- Persisten patrones de busqueda textual sobre campos serializados no normalizados.

### 6.10 Win y mac
- Objetivo cross-platform esta planteado (NSIS + DMG en Tauri).
- Falta robustez local/reproducible del empaquetado por recursos requeridos no presentes.

## 7. Deuda tecnica y riesgos futuros

Deuda tecnica principal:
- Tipado estatico y contratos de dominio.
- Legacy path aun activo.
- Coverage gaps.
- Documentacion de API/version no sincronizada.
- Consultas SQL no escalables en campos serializados.

Riesgos futuros probables si no se corrige:
- Regresiones frecuentes detectadas tarde.
- Incidencias de produccion por caminos legacy.
- Aumento de tiempos de desarrollo y QA.
- Problemas de performance al crecer datos de proyectos.
- Dificultad de soporte por docs desactualizadas.

## 8. Lista de nuevas ideas (incluida y priorizada)

1. Convertir CI a "quality gate" real (eliminar `|| true` en checks criticos).
2. Retirar definitivamente pipeline legacy con plan de migracion y flag temporal.
3. Generar documentacion API automaticamente desde OpenAPI en cada build.
4. Reparar instrumentacion de cobertura frontend y establecer umbral minimo obligatorio.
5. Plan por fases para bajar errores mypy (dominios: pipelines -> cli -> nlp/style).
6. Introducir benchmark nocturno por detector (precision, recall, latencia) con corpus fijo.
7. Normalizar campos serializados consultados con `LIKE` hacia tablas relacionales auxiliares.
8. Definir "feature maturity matrix" (implemented/partial/planned) visible en producto y docs.
9. Añadir smoke tests cross-platform de release (arranque sidecar + health + flujo basico).
10. Automatizar gestion de dependencias (renovate/dependabot + politica de severidad bloqueante).
11. Dividir routers monoliticos por subdominios para mejorar mantenibilidad.
12. Introducir contract tests backend-frontend para endpoints criticos.
13. Introducir "golden datasets" por idioma/genero para regresion de calidad NLP.
14. Instrumentar trazabilidad de decisiones del usuario sobre alertas para aprendizaje adaptativo robusto.
15. Consolidar una guia de "Definition of Done" tecnico (tipos, tests, docs, seguridad, performance).

## 9. Plan de remediacion recomendado (30/60/90 dias)

### 0-30 dias
- Hacer bloqueante: `mypy` (aunque sea por paquete objetivo), frontend tests, integration smoke.
- Corregir `AlertSeverity.SUGGESTION` y blindar uso de enums.
- Corregir vulnerabilidad `axios`.
- Arreglar cobertura frontend para obtener metricas reales.
- Publicar snapshot de API docs generado automaticamente.

### 31-60 dias
- Reducir al menos 50% de errores mypy en modulos de mayor riesgo.
- Extraer piezas del pipeline legacy y congelarlo para solo lectura.
- Refactor de consultas SQL `LIKE` mas sensibles (escenas/glossary/entities).
- Simplificar y estandarizar flujo de build desktop reproducible local.

### 61-90 dias
- Retirada completa del path legacy.
- Coverage backend > 55% con foco en modulos criticos.
- Contract tests backend-frontend para endpoints top.
- Matriz de madurez funcional publicada y enlazada con roadmap.

## 10. Estado final de esta auditoria

- Auditoria completada sobre el estado actual del workspace.
- Sin cambios de codigo funcional aplicados por esta auditoria.
- Documento unico generado con hallazgos, riesgos, deuda tecnica y nuevas ideas.

