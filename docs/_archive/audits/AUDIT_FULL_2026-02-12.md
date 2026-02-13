# Auditoría Integral del Proyecto (Frontend + Backend + Tauri + QA + Producto)

Fecha: 2026-02-12  
Repositorio: `d:\repos\tfm`  
Versión observada en código: `0.9.3` (`pyproject.toml`, `frontend/package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`)

## 1. Alcance y método

Esta auditoría cubre:
- Arquitectura y modularidad.
- Calidad de código y riesgos técnicos.
- Funcionalidad de producto desde perspectiva de cliente editorial/corrector.
- Frontend (UX/UI, robustez, seguridad).
- Backend/API/pipeline NLP.
- Tauri (desktop runtime, procesos, estabilidad Windows/macOS).
- Configuración, CI/CD, calidad y estrategia de testing.
- Rendimiento, memoria y protección ante degradación/cuelgues.

Se ha realizado una revisión estática del repositorio y documentación principal. No se han implementado cambios.

## 2. Resumen ejecutivo

Estado general: **sólido pero con deuda operativa importante**.

Fortalezas:
- Producto técnicamente ambicioso, con cobertura funcional muy amplia (NLP, editorial, UX de trabajo real).
- Buena separación por dominios en `src/narrative_assistant/*`.
- Buen trabajo de robustez en sanitización y controles de recursos/memoria.
- Integración desktop realista (Tauri + backend sidecar + watchdog).
- Suite de tests extensa (unit/integration/adversarial/performance/security/e2e).

Riesgos principales:
- **Desalineación documental significativa**: varios documentos se contradicen entre sí en estado/versionado/completitud.
- **Pipeline API y orquestación con complejidad elevada** (riesgo de regresión y mantenimiento).
- **CI con tolerancia a fallos en puntos críticos** (`|| true` en etapas relevantes), debilitando la señal de calidad.
- **Volumen de xfail/skip alto** en pruebas adversariales/integración, lo que limita la confianza en “cobertura efectiva”.
- **Modelo de proceso desktop exigente en recursos**: hay defensas, pero requiere endurecer degradación progresiva y observabilidad.

Conclusión ejecutiva:
- El producto está cercano a una base comercial usable, pero no está en un estado “sin sorpresas” para escalar equipo, releases frecuentes o soporte enterprise sin reforzar gobernanza técnica y disciplina de calidad operativa.

## 3. Hallazgos críticos y altos (priorizados)

## 3.1 Crítico — Gobernanza documental inconsistente

Evidencia:
- `docs/IMPROVEMENT_PLAN.md` declara estado y roadmap muy avanzados (incluyendo SP-1/SP-2/SP-3 completados).
- `docs/PROJECT_STATUS.md` presenta versión/estado y narrativa parcialmente distinta.
- Existen múltiples documentos activos y archivo histórico con información solapada.

Impacto:
- Decisiones de producto y desarrollo basadas en información contradictoria.
- Riesgo de prometer capacidades no verificadas en runtime real.
- Coste de onboarding alto.

Recomendación:
- Definir una única fuente de verdad (SoT) obligatoria para estado de release y matriz de funcionalidades.
- Marcar documentos como `authoritative` vs `informative`.
- Añadir check de CI que detecte contradicciones obvias de versión/estado entre docs clave.

## 3.2 Crítico — Señal de CI degradada por “falsos verdes”

Evidencia:
- En ` .github/workflows/ci.yml` hay pasos con tolerancia explícita a fallo (`|| true`) en secciones que deberían bloquear.
- Estrategia de integración/performance condicionada, no siempre ejecutada.

Impacto:
- Riesgo de introducir regresiones sin freno.
- Confianza reducida en pipeline de release.

Recomendación:
- Eliminar `|| true` en checks críticos.
- Mantener “allow-failure” solo en jobs experimentales explícitos.
- Definir política mínima de calidad: unit + lint + typecheck + smoke integration obligatorios para merge.

## 3.3 Alto — Complejidad de orquestación backend/API

Evidencia:
- `api-server/main.py` centraliza bootstrap complejo, carga de módulos, comportamiento embedded y arranque.
- `api-server/routers/_analysis_phases.py` concentra mucha lógica de negocio/orquestación.
- Flujo de análisis combina múltiples fases, colas, slots “heavy”, invalidación, persistencia y reanálisis.

Impacto:
- Mayor probabilidad de bugs transversales.
- Testabilidad más difícil en casos límite de concurrencia/cancelación.

Recomendación:
- Extraer un “application service layer” más explícito para análisis.
- Reducir responsabilidades de router a “adaptadores HTTP”.
- Aislar motor de scheduling (queue/heavy-slot/watchdog) con contrato y tests dedicados.

## 3.4 Alto — Cobertura efectiva vs cobertura nominal

Evidencia:
- Gran suite de tests, pero con numerosos `xfail`/`skip` en áreas adversariales e integración.
- Parte de tests depende de entorno/modelos/fixtures no siempre presentes.

Impacto:
- Riesgo de asumir robustez mayor que la real.
- Problemas tardíos en producción en edge cases lingüísticos/temporales/dialogados.

Recomendación:
- Dashboard de calidad con:
  - tests totales,
  - tests ejecutados reales por pipeline,
  - xfail activos justificados y fecha de caducidad.
- Política de “xfail debt budget” por release.
- Segmentación clara: “must-pass suite” para PR y “extended suite” nocturna.

## 4. Arquitectura (visión global)

Fortalezas:
- Dominios bien identificados (`entities`, `alerts`, `analysis`, `voice`, `temporal`, `licensing`, `exporters`, etc.).
- Backend core reutilizable y API separada.
- Frontend moderno (Vue3/TS/Pinia/Vite) con componentes y stores extensos.
- Tauri con sidecar backend y menú/gestión de proceso.

Riesgos:
- Alta acoplación implícita entre fases del pipeline.
- Varias capas de “estado global mutable” en API (`deps.py`) que aumentan complejidad de concurrencia.
- Riesgo de drift entre contratos API y transformadores frontend.

Recomendaciones:
- Contratos API versionados + tests de contrato FE/BE.
- Límite explícito de tamaño por módulo/archivo y refactor plan.
- Observabilidad estructurada (métricas por fase, latencias, fallos por detector, retries).

## 5. Backend y pipeline NLP

Puntos positivos:
- Pipeline de fases extenso y conceptualmente sólido.
- Soporte de análisis progresivo y gating por licencias.
- Controles de recursos:
  - `src/narrative_assistant/core/resource_manager.py`
  - `src/narrative_assistant/core/memory_monitor.py`
- Gestión de modelos bajo demanda con fallback:
  - `src/narrative_assistant/core/model_manager.py`

Riesgos técnicos:
- Lógica muy densa en orquestación (fácil romper invariantes).
- Dependencia elevada de heurísticas + modelos opcionales + estados parciales.
- Riesgo de degradación de UX cuando faltan componentes (modelos, runtime, entorno).

Optimización recomendada:
- Introducir “quality gates” por fase (si falla precondición, fallback explícito y telemetría).
- Definir SLO internos:
  - tiempo máximo por fase,
  - memoria pico por perfil,
  - ratio de fallback por módulo.
- Endurecer idempotencia y reentrancia en reanálisis/cancelación.

## 6. Frontend (UX/funcionalidad/seguridad)

Fortalezas:
- Cobertura funcional muy amplia para workflows editoriales.
- Componentización extensa y estructura razonable.
- Sanitización explícita de HTML para `v-html`:
  - `frontend/src/utils/sanitizeHtml.ts`
  - uso observado en `frontend/src/components/DocumentViewer.vue`.

Riesgos:
- Complejidad elevada en componentes grandes (p. ej. visualizador documental con mucha lógica).
- Potencial de regresiones UI en features avanzadas por alto acoplamiento estado-eventos.
- Mantenimiento difícil en tabs/inspección/selección si no se controla deuda.

Recomendaciones:
- Limitar tamaño por componente y extraer lógica a composables puros.
- Añadir tests de interacción críticos por flujo editorial (no solo snapshot).
- Definir mapa de experiencia por rol:
  - corrector individual,
  - coordinador editorial,
  - equipo multi-corrector.

## 7. Tauri / Desktop runtime (Windows y macOS)

Fortalezas:
- Gestión explícita de ciclo de vida del backend sidecar.
- Watchdog de backend en release.
- Integración de menú nativo y eventos a frontend.

Riesgos:
- Complejidad alta en bootstrap multiplataforma (pathing, embedded Python, entorno).
- Riesgo de edge cases en distribución y soporte OS-version specific.

Recomendaciones:
- Matriz de compatibilidad oficial por SO/arquitectura.
- Smoke tests automáticos post-build por plataforma.
- Telemetría local de fallos de arranque y recuperación de watchdog.

## 8. Seguridad

Fortalezas:
- Sanitización de inputs/path traversal:
  - `src/narrative_assistant/parsers/sanitization.py`
- Sanitización de prompts/respuestas LLM:
  - `src/narrative_assistant/llm/sanitization.py`
- Dependencias de frontend con DOMPurify para contenido HTML dinámico.
- Suite específica de tests de seguridad:
  - `tests/security/test_input_validation.py`
  - `tests/unit/test_xss_sanitization.py`

Riesgos:
- Superficie amplia por gran cantidad de endpoints y features.
- Posible seguridad “correcta por fragmentos” pero sin threat model unificado.

Recomendaciones:
- Threat model formal por capas (FE, API, sidecar, modelos, almacenamiento local).
- Checklist de seguridad release-ready (input/output validation, secrets, file access, update chain).
- Revisión específica de permisos y rutas en contexto Tauri.

## 9. Rendimiento y memoria (riesgo de cuelgues/degradación)

Observación:
- El proyecto sí contiene mecanismos de control (semaforización de tareas pesadas, detección de presión de memoria, GC agresivo, límites de batch/chunking).

Riesgos:
- El volumen funcional total puede superar recursos de equipos modestos.
- Riesgo de latencias altas y UX degradada en manuscritos grandes con perfiles profundos.

Recomendaciones:
- Perfiles de ejecución más estrictos por hardware (auto-fallback visible al usuario).
- Presupuesto de memoria por fase y límites duros de operación.
- Benchmarks continuos por tamaño de manuscrito y por SO.
- Indicadores UX de “degradación controlada” (no bloquear UI, cancelación fiable, retomado seguro).

## 10. QA y estrategia de pruebas

Fortalezas:
- Suite grande y variada (unit, integration, adversarial, performance, security, e2e).
- Cobertura de casos lingüísticos no triviales.

Gaps:
- Parte de la suite no siempre ejecutable en CI estándar.
- Necesidad de distinguir mejor:
  - “calidad de merge”,
  - “calidad profunda de nightly”.

Plan recomendado:
- Tier 1 (obligatorio PR): lint, typecheck, unit core, contrato API, smoke e2e.
- Tier 2 (nightly): adversarial completo, performance, corpus ampliado.
- Tier 3 (release): validación multiplataforma y dataset de aceptación editorial.

## 11. Perspectiva cliente editorial/corrector

Valor percibido:
- Alto potencial diferencial por amplitud funcional y enfoque workflow editorial.

Riesgos de adopción:
- Si la persistencia/reanálisis o consistencia de resultados falla en casos reales, la confianza cae rápido.
- Complejidad de producto puede penalizar curva de aprendizaje.

Recomendaciones de producto:
- Definir “ruta feliz” ultra clara para primer valor en <15 minutos.
- Priorizar fiabilidad y predictibilidad sobre nuevas funciones.
- Añadir métricas de confianza por detector y feedback loop visible al usuario.

## 12. Plan de optimización propuesto (priorizado)

P0 (inmediato):
- Corregir gobernanza documental (SoT única).
- Endurecer CI eliminando tolerancia a fallos en checks críticos.
- Definir suite mínima obligatoria de merge.

P1 (corto plazo):
- Refactor de orquestación API/pipeline (separar scheduling/negocio/transporte).
- Mejorar observabilidad de fases, memoria, errores y reintentos.
- Reducir tamaño/complexidad de componentes frontend más cargados.

P2 (medio plazo):
- Threat model formal + hardening checklist release.
- Matriz de compatibilidad y tests smoke multiplataforma automatizados.
- Presupuestos de rendimiento y memoria por perfil/hardware.

P3 (continuo):
- Reducir deuda de `xfail`/`skip` con objetivos por release.
- Auditorías periódicas de contrato FE/BE y regresión UX editorial.

## 13. Opinión técnica final

Proyecto técnicamente potente y con dirección correcta para producto editorial profesional.  
No obstante, para minimizar riesgo real en producción (especialmente en Windows/macOS con cargas NLP intensivas), el foco debe pasar de “más funcionalidad” a “fiabilidad operativa verificable”: coherencia documental, CI estricta, simplificación de orquestación, observabilidad y calidad efectiva de test suite.

Con ese ajuste de disciplina, el proyecto puede evolucionar a una base muy competitiva y sostenible.
