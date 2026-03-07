# Auditoría Integral del Estado Actual de la Aplicación

Fecha: 2026-03-07
Alcance: aplicación desktop Tauri completa, backend FastAPI/Python, persistencia SQLite, frontend Vue, instalación/primer arranque, accesibilidad, testing y documentación.
Tipo de revisión: auditoría técnica y de producto, con foco en deuda técnica, consistencia, completitud, UX para usuario no técnico y trazabilidad documental.

---

## 1. Resumen ejecutivo

La aplicación está en un estado funcional alto, pero no está documentalmente ni arquitectónicamente cerrada. La parte más sólida hoy no es la documentación sino el código operativo: primer arranque, auto-configuración, pipeline de análisis, `.nra` y buena parte del endurecimiento reciente están bastante mejor que lo que cuentan los documentos públicos.

No he encontrado en esta revisión un P0 nuevo del tipo "corrupción inmediata de datos" o "flujo central roto" en las rutas muestreadas, pero sí varios P1 claros:

1. La documentación operativa está desalineada con el producto real.
2. Hay fuentes de verdad duplicadas en frontend, especialmente en tema/modo visual.
3. La conformidad WCAG se está sobreafirmando respecto a lo que realmente garantizan los tests.
4. El arranque sidecar Tauri/FastAPI está bastante endurecido, pero sigue siendo un área crítica con poca cobertura automatizada específica.

Conclusión operativa:

- El producto real está más avanzado que su documentación.
- La deuda principal ya no es "falta implementar X", sino "alinear contrato mental, documentación, pruebas y arquitectura con lo que ya existe".
- El siguiente salto de calidad no pasa por añadir features, sino por consolidar fuentes de verdad, limpiar documentos activos y endurecer los tests de sistema/UX/accesibilidad.

---

## 2. Metodología de la auditoría

### 2.1 Inspección estática realizada

Se revisaron, entre otros, estos bloques:

- `README.md`
- `CHANGELOG.md`
- `docs/README.md`
- `docs/index.md`
- `docs/PROJECT_STATUS.md`
- `docs/PLAN_ACTIVE.md`
- `docs/ROADMAP.md`
- `docs/FRONTEND_TESTS_STATUS.md`
- `docs/WCAG_COLOR_AUDIT.md`
- `docs/SETUP.md`
- `docs/user-manual/README.md`
- `src-tauri/src/main.rs`
- `api-server/main.py`
- `api-server/routers/system.py`
- `api-server/routers/analysis.py`
- `api-server/routers/_analysis_phases.py`
- `src/narrative_assistant/persistence/database.py`
- `src/narrative_assistant/persistence/project_file.py`
- `frontend/src/stores/system.ts`
- `frontend/src/stores/theme.ts`
- `frontend/src/stores/app.ts`
- `frontend/src/views/HomeView.vue`
- `frontend/src/views/SettingsView.vue`
- `frontend/src/views/ProjectDetailView.vue`
- `frontend/src/components/ModelSetupDialog.vue`
- `frontend/e2e/accessibility.spec.ts`

### 2.2 Validación dinámica mínima ejecutada

Se ejecutó:

1. `frontend`: `npm run type-check` -> OK
2. Backend/API: `pytest tests/api/test_project_file_endpoints.py -q` -> 4/4 OK
3. Backend/API: `pytest tests/api/test_project_settings.py -q` -> 14/14 OK

### 2.3 Métricas rápidas de repositorio usadas en la auditoría

Conteos por inspección estática:

- Definiciones `test()/it()` en `frontend/src` + `frontend/e2e`: aproximadamente 990
- Definiciones `def test_` en `tests/`: aproximadamente 4213

Nota:
- Estos conteos no equivalen a "tests ejecutados hoy", pero sirven para demostrar que varios documentos de estado de testing están claramente obsoletos.
- Las referencias de línea corresponden al árbol inspeccionado en esta fecha. En áreas de alta rotación conviene priorizar nombres de símbolos/funciones sobre rangos largos.

---

## 3. Lo que está sólido ahora mismo

Antes de listar deuda, conviene fijar lo que sí está bien:

1. **Primer arranque y setup inicial**:
   - `frontend/src/components/ModelSetupDialog.vue:464-514` comunica estados de inicio, instalación y descarga con lenguaje no técnico.
   - `frontend/src/stores/system.ts` expone progreso granular (`install_progress`) y warnings legibles.

2. **Sidecar Tauri / backend local**:
   - `src-tauri/src/main.rs:78-197` separa liveness y readiness.
   - `src-tauri/src/main.rs:229-344` añade watchdog y eventos `starting`/`restarting`.

3. **Detección de capacidades y degradación controlada**:
   - `api-server/routers/system.py:1313-1330` expone `detection_status` y `detection_warnings`.
   - `api-server/routers/_analysis_phases.py:1260-1262` y `1864` trasladan warnings de runtime al análisis y al progreso.

4. **Persistencia/exportación `.nra`**:
   - `src/narrative_assistant/persistence/project_file.py:35` define compatibilidad mínima.
   - `src/narrative_assistant/persistence/project_file.py:120-166` cubre remapeos directos, indirectos y JSON en tablas críticas.

5. **Volumen de testing**:
   - El repositorio sí tiene una base de tests amplia; el problema principal no es falta de tests en bruto, sino cobertura desigual, documentos de estado desfasados y falta de smoke/system tests en algunas zonas críticas.

---

## 4. Hallazgos prioritarios

## 4.1 P1 - Gobernanza documental rota

### H-01. La documentación activa no refleja el producto actual

Evidencia:

- `README.md:3`, `README.md:229`, `README.md:319` siguen en `0.10.15`
- `docs/index.md:38` sigue en `0.10.15`
- `docs/user-manual/README.md:73` sigue en `v0.10.15`
- `docs/README.md:3` dice `Version: 0.9.5`
- `pyproject.toml:3`, `frontend/package.json:3` y `api-server/deps.py:39` están en `0.11.12`

Impacto:

- Riesgo alto de que producto, manual, release notes y soporte hablen de aplicaciones distintas.
- Dificulta validación, onboarding, QA, soporte y presentación externa.
- Hace imposible saber qué documento es realmente canónico.

Recomendación:

1. Definir una única fuente de verdad de versión (`pyproject.toml` o `VERSION`) y derivar de ahí `README`, docs y changelog.
2. Hacer una pasada completa de documentación "versión actual / última revisión / alcance".
3. Prohibir en revisión que un documento canónico sobreviva con versión menor a la app real.

### H-02. Los documentos activos remiten a un archivo histórico que no existe

Evidencia:

- `docs/README.md`, `docs/AUDIT_INDEX.md`, `docs/PLAN_ACTIVE.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/00-overview/README.md` apuntan a `docs/_archive/...`
- En el repositorio actual `docs/_archive` no existe

Impacto:

- Navegación documental rota.
- Falsa sensación de limpieza/curación histórica.
- Referencias canónicas quebradas justo en los documentos que deberían orientar.

Recomendación:

Elegir una de estas dos vías y ejecutar una sola:

1. Crear `docs/_archive/` de verdad y mover ahí el histórico real.
2. Eliminar todas las referencias a `_archive` y reemplazarlas por ubicaciones existentes.

No conviene mantener el estado actual intermedio.

### H-03. `README.md` describe una aplicación anterior

Evidencia:

- `README.md:82` afirma "6 fases de análisis"
- El pipeline real tiene 14 fases explícitas en `api-server/routers/analysis.py:13-28`
- `README.md:161-162` simplifica `Auto` a umbrales de tamaño, mientras el sistema real también expone detección de hardware/capacidades en `api-server/routers/system.py:1313-1359` y `frontend/src/stores/system.ts:49-99`

Impacto:

- Marketing, onboarding y soporte arrancan desde un modelo mental falso.
- Un corrector/editor recibe expectativas incorrectas sobre tiempos, profundidad y modos.

Recomendación:

Reescribir `README.md` completo con foco en:

1. App desktop local Tauri.
2. Primer arranque y auto-configuración.
3. Pipeline real por fases.
4. Diferencia entre capacidades detectadas, motores opcionales y degradación controlada.
5. Estado real de timeline, reanálisis, exportación `.nra`, colecciones y configuración por proyecto.

---

## 4.2 P1 - Fuentes de verdad duplicadas en frontend

### H-04. El sistema de tema está duplicado y puede divergir

Evidencia:

- `frontend/src/stores/theme.ts:64` usa `narrative_assistant_theme_config`
- `frontend/src/stores/app.ts:27` y `:60` usan `narrative_assistant_theme`
- `frontend/src/components/settings/AppearanceSection.vue:10-14` usa `themeStore`
- `frontend/src/views/HomeView.vue:8-11` sigue usando `appStore.isDark` y `appStore.toggleTheme`

Impacto:

- El botón rápido de Home puede cambiar solo el estado legacy y no la configuración canónica de Apariencia.
- Riesgo de que Home, Settings y estado persistido no hablen del mismo tema.
- Mantener dos stores para el mismo dominio encarece cualquier cambio futuro y multiplica regresiones.

Recomendación:

1. Declarar `themeStore` como fuente única de verdad.
2. Eliminar tema/modo de `appStore`.
3. Mover el toggle de Home al `themeStore`.
4. Dejar `appStore` solo para shell/Tauri si sigue siendo necesario.

### H-05. `appStore` mezcla responsabilidades no relacionadas

Evidencia:

- `frontend/src/stores/app.ts` combina:
  - tema visual
  - listener Tauri `backend-status`
  - arranque del backend sidecar

Impacto:

- Store difícil de razonar.
- Acoplamiento entre shell desktop y presentación visual.
- Riesgo de side effects al tocar algo aparentemente inocuo.

Recomendación:

Separar en dos stores/composables:

1. `shell/desktop` para Tauri y sidecar.
2. `theme` para apariencia.

---

## 4.3 P1 - WCAG y accesibilidad: mejor de lo que estaba, pero no tan cerrada como dicen los documentos

### H-06. La documentación afirma conformidad WCAG total, pero la automatización real sigue permitiendo fallos

Evidencia:

- `docs/WCAG_COLOR_AUDIT.md:257` afirma `Estado General: CUMPLE WCAG 2.1 AA`
- `frontend/e2e/accessibility.spec.ts:249` y `:273` permiten hasta 3 violaciones serias de contraste
- `frontend/e2e/accessibility.spec.ts:171` y `:318` aceptan solo 80% de etiquetado/focus

Impacto:

- La frase "cumple WCAG 2.1 AA" hoy es demasiado fuerte para la evidencia automatizada disponible.
- Puede inducir a error en QA, ventas, compliance o auditoría externa.

Recomendación:

1. Rebajar el claim documental:
   - de "cumple WCAG 2.1 AA"
   - a "se han corregido áreas críticas y existe validación automatizada parcial"
2. Convertir las tolerancias blandas en backlog explícito:
   - contraste: 0 violaciones serias
   - labels: 100% en formularios críticos
   - focus: 100% en elementos interactivos críticos

### H-07. No todos los temas que el producto ofrece están cubiertos por tests de accesibilidad

Evidencia:

- `frontend/src/stores/theme.ts:76-101` define `PRIMEVUE_PRESETS` con `aura`, `lara`, `material`, `nora`
- `frontend/src/stores/theme.ts:158-171` define `CUSTOM_PRESETS` con `grammarly`, `scrivener`
- `frontend/e2e/accessibility.spec.ts:417` solo prueba `aura`, `lara`, `grammarly`, `scrivener`

Impacto:

- `material` y `nora` se envían sin cobertura específica de accesibilidad E2E.
- El producto puede anunciar soporte de temas que no están verificados al mismo nivel.

Recomendación:

1. Ampliar el spec a los 6 temas reales.
2. Si algún preset es experimental, marcarlo como tal en producto y docs.

### H-08. La auditoría de color está desfasada de versión y alcance

Evidencia:

- `docs/WCAG_COLOR_AUDIT.md:3` indica fecha `2026-02-04`
- `docs/WCAG_COLOR_AUDIT.md:4` indica `Versión: v0.4.45`

Impacto:

- Aunque parte del contenido siga siendo útil, el documento ya no puede presentarse como auditoría vigente del producto actual.

Recomendación:

Rehacer el documento como auditoría de accesibilidad actual, con:

1. alcance exacto por tema/preset,
2. páginas revisadas,
3. componentes críticos,
4. pruebas automáticas y manuales,
5. excepciones conocidas abiertas.

---

## 4.4 P1 - Arranque, sidecar e instalación: buen endurecimiento, poca cobertura de sistema

### H-09. El arranque sidecar es complejo y crítico, pero apenas tiene tests específicos

Evidencia:

- `src-tauri/src/main.rs:37-91` define `poll_health_alive`, `poll_health_ready`, `wait_for_alive` y `wait_for_ready`
- `src-tauri/src/main.rs:105-197` concentra `start_backend_server`
- `src-tauri/src/main.rs:229-353` concentra `backend_watchdog`
- En Rust solo aparecen tests en `src-tauri/src/menu.rs`; `main.rs` no tiene tests directos

Impacto:

- Una de las zonas más críticas de la app desktop depende sobre todo de validación manual.
- Alto riesgo de regresión en Windows/macOS precisamente en el punto más sensible para usuario final: "la app abre / no abre / parece bloqueada".

Recomendación:

Añadir smoke tests de shell/desktop para:

1. arranque inicial con backend vivo,
2. backend vivo pero no ready,
3. warming mode,
4. caída y restart,
5. error terminal de startup.

### H-10. La documentación de instalación mezcla setup de desarrollo con onboarding de producto

Evidencia:

- `docs/SETUP.md` está redactado como "Setup Completo" pero mezcla:
  - venv
  - build manual backend
  - `cargo tauri dev`
  - scripts de build

Impacto:

- El lector no tiene claro si está siguiendo una guía para desarrolladores o para despliegue real.
- Mala experiencia para onboarding interno y soporte técnico.

Recomendación:

Separar en tres documentos:

1. `SETUP_DEV.md`
2. `BUILD_RELEASE.md`
3. `FIRST_RUN_RUNTIME.md`

Y dejar `docs/SETUP.md` como índice corto, no como mezcla de todo.

### H-11. La capa de shell/health usa lógica propia fuera del cliente API común

Evidencia:

- `frontend/src/stores/system.ts:227-294` usa `fetch(apiUrl('/api/health'))` directamente

Impacto:

- Duplicación de lógica de transporte/errores.
- Inconsistencia con el resto del frontend, que ya usa `apiClient`.
- Más difícil unificar timeouts, logging y criterios de recuperación.

Recomendación:

Mantener una excepción solo si el health check necesita ser extremadamente minimalista. Si no, unificarlo con el cliente común o documentar explícitamente por qué el health vive fuera.

---

## 4.5 P2 - Deuda técnica estructural

### H-12. Hay varios archivos monolíticos por encima del tamaño razonable

Evidencia:

Top revisado por líneas en este snapshot del árbol:

- `api-server/routers/_analysis_phases.py` -> más de 5K líneas
- `src/narrative_assistant/nlp/attributes.py` -> más de 3.8K líneas
- `frontend/src/views/SettingsView.vue` -> más de 2.8K líneas
- `src/narrative_assistant/pipelines/analysis_pipeline.py` -> más de 2.5K líneas
- `src/narrative_assistant/alerts/engine.py` -> más de 2.3K líneas
- `api-server/routers/entities.py` -> más de 2.3K líneas
- `frontend/src/views/ProjectDetailView.vue` -> más de 2.2K líneas
- `frontend/src/components/DocumentViewer.vue` -> más de 2.2K líneas

Nota:
- Estas cifras deben entenderse como métricas de complejidad del snapshot auditado, no como números estables. En archivos de alta rotación es preferible vigilar rangos de magnitud que cifras exactas.

Impacto:

- Review difícil.
- Refactors costosos.
- Riesgo alto de regresión por cambios transversales.
- Onboarding lento incluso para quien ya conoce la app.

Recomendación:

No dividir "por dividir", pero sí por cost centers reales:

1. `_analysis_phases.py` por familia funcional.
2. `SettingsView.vue` por sección.
3. `ProjectDetailView.vue` por tab/concern.
4. `DocumentViewer.vue` por navegación, anotaciones, menciones y export.

### H-13. Sigue habiendo funcionalidad visible o semi-visible claramente incompleta

Evidencia:

- `api-server/routers/content.py:411` -> `first_mention_chapter` sigue en `None`
- `api-server/routers/content.py:1049` -> `chapter_id` sigue en `None` antes de mapear
- `frontend/src/views/ProjectDetailView.vue:1444` -> filtro por categoría en workspace no implementado
- `frontend/src/components/DocumentViewer.vue:264` -> endpoint de menciones aún pendiente
- `src/narrative_assistant/analysis/narrative_structure.py:316` -> analepsis sin marcador no implementada
- `src/narrative_assistant/nlp/mention_validation.py:677` -> `LLMValidator` pendiente
- `src/narrative_assistant/nlp/grammar/spanish_rules.py:894` -> detector de artículos futuro

Impacto:

- La app parece más completa desde fuera que desde dentro.
- Algunos tabs/endpoints ya existen, pero con campos incompletos o comportamientos placeholder.

Recomendación:

Crear una matriz de madurez por feature:

- `implemented`
- `partial`
- `planned`

Y usarla en docs internas y QA. Ahora mismo varias áreas parecen "done" cuando en realidad están "partial".

### H-14. Configuración de pytest duplicada

Evidencia:

- `pyproject.toml:222-229` define `[tool.pytest.ini_options]`
- `pytest.ini` define otra configuración distinta
- Al ejecutar pytest aparece: `ignoring pytest config in pyproject.toml!`

Impacto:

- Ambigüedad en CI/local.
- Fácil creer que una opción está activa cuando en realidad pytest está leyendo otra.

Recomendación:

Quedarse con una sola:

1. o `pytest.ini`,
2. o `pyproject.toml`.

Pero no ambas.

---

## 4.6 P2 - Testing: volumen alto, trazabilidad baja

### H-15. La documentación de testing está fuertemente desactualizada

Evidencia:

- `docs/FRONTEND_TESTS_STATUS.md:4,50,55` habla de `65 tests` y `555 tests`
- `docs/NEXT_STEPS.md:148` sigue anclado a `555 tests`
- `docs/SUMMARY_WORK_COMPLETED.md:54` sigue anclado a `555 tests`
- En el código actual hay aproximadamente:
  - 990 tests/its en frontend
  - 4213 tests Python

Impacto:

- Los documentos de testing ya no sirven como referencia de estado.
- Pueden llevar a decisiones erróneas sobre cobertura real, deuda o prioridades.

Recomendación:

1. Convertir `FRONTEND_TESTS_STATUS.md` en documento histórico o regenerarlo.
2. Si se quiere mantener un documento vivo, que sea generado o al menos derivado de una métrica reproducible.

### H-16. El área más crítica de la app desktop sigue sin smoke tests E2E reales de shell

Evidencia:

- Hay mucha cobertura de frontend y backend.
- No hay evidencia equivalente de tests automáticos para:
  - sidecar listo/no listo,
  - restart del backend,
  - primer arranque completo Tauri,
  - errores terminales de bootstrap.

Impacto:

- El usuario final sufre primero fallos de arranque, no fallos de transformadores.
- La distribución desktop sigue dependiendo demasiado de validación manual.

Recomendación:

Prioridad alta para un bloque de smoke tests de distribución/arranque, aunque sean pocos.

---

## 4.7 P2 - Documentación de arquitectura y estado de datos

### H-17. La documentación de esquema SQLite está desalineada

Evidencia:

- `src/narrative_assistant/persistence/database.py:27` -> `SCHEMA_VERSION = 34`
- `docs/adr/001-sqlite-database.md:84` sigue diciendo `SCHEMA_VERSION = 29`
- Auditorías/documentos viejos siguen hablando de `schema v24`

Impacto:

- Riesgo alto en soporte, migraciones, export/import y compatibilidad.
- Las decisiones de arquitectura pierden valor si la versión real del esquema ya es otra.

Recomendación:

Actualizar ADR y cualquier documento que presente el estado del esquema como actual, o marcarlos explícitamente como históricos.

### H-18. `PLAN_ACTIVE.md`, `PROJECT_STATUS.md` y `ROADMAP.md` ya no pueden considerarse fuentes canónicas

Evidencia:

- `docs/PLAN_ACTIVE.md:19-20` sigue dejando `S15 en curso` y `S16A pendiente`
- `docs/ROADMAP.md:16-17` repite ese mismo estado
- `docs/PROJECT_STATUS.md` dice que riesgo documental es bajo, pero hoy el riesgo documental es alto

Impacto:

- La "fuente de verdad operativa" no es fiable.

Recomendación:

No basta con editar dos líneas. Hace falta decidir:

1. o estos documentos siguen siendo canónicos y se actualizan ya,
2. o dejan de serlo y se reduce el set documental activo.

---

## 5. Evaluación por área

## 5.1 Instalación y primera ejecución

Estado:
- Bueno a nivel de UX operativa.
- Medio a nivel de documentación.
- Medio-bajo a nivel de test de sistema.

Observaciones:

1. El producto sí informa durante arranque/instalación:
   - `ModelSetupDialog.vue:464-514`
   - `system.ts` + `main.rs` emiten estados intermedios
2. La experiencia está bastante más cuidada que lo que indican varios documentos antiguos.
3. Falta trazabilidad automatizada de shell real.

Veredicto:
- Producto: bien encaminado.
- QA/release engineering: todavía frágil.

## 5.2 Pipeline y análisis

Estado:
- Fuerte.

Observaciones:

1. El pipeline actual tiene orden explícito y ya integra `timeline`.
2. Existe degradación por capacidades y warnings runtime.
3. La deuda aquí es más de tamaño y mantenibilidad que de concepto.

Veredicto:
- Área madura pero con coste creciente de mantenimiento.

## 5.3 DB y persistencia

Estado:
- Fuerte en código, débil en documentación.

Observaciones:

1. El esquema y `.nra` han avanzado bastante.
2. La documentación de schema/versionado no acompaña.
3. Esto es peligroso porque la base real ya está más evolucionada que lo que dicen ADRs y auditorías antiguas.

## 5.4 Frontend, usabilidad y consistencia

Estado:
- Funcionalmente bueno.
- Arquitectónicamente irregular.

Observaciones:

1. La UI principal está rica y ofrece mucho contexto.
2. Hay componentes muy grandes y stores con responsabilidades mezcladas.
3. La accesibilidad existe como preocupación real, pero todavía no conviene venderla como completamente cerrada.

## 5.5 Testing

Estado:
- Volumen alto.
- Estrategia desigual.

Observaciones:

1. Mucha cobertura unitaria e integración backend/frontend.
2. Menos cobertura de shell, distribución y primer arranque real.
3. Mucha documentación de tests ya no describe la suite real.

---

## 6. Documentos desfasados, innecesarios o que necesitan actualización

## 6.1 Actualización urgente

| Documento | Problema actual | Acción recomendada |
|---|---|---|
| `README.md` | Versión, changelog, fases y explicación del producto desfasados | Reescritura completa |
| `CHANGELOG.md` | No documenta `0.11.x` | Añadir releases reales o aclarar política |
| `docs/README.md` | Versión `0.9.5`, referencias a `_archive` roto | Rehacer como índice real |
| `docs/index.md` | Sigue en `0.10.15` | Actualizar versión y navegación |
| `docs/user-manual/README.md` | Sigue en `v0.10.15` | Actualizar versión y alcance |
| `docs/WCAG_COLOR_AUDIT.md` | Claim demasiado fuerte y versión antigua | Rehacer auditoría actual |
| `docs/adr/001-sqlite-database.md` | `SCHEMA_VERSION` desactualizada | Actualizar o marcar histórico |

## 6.2 Necesitan decisión editorial inmediata

| Documento | Problema actual | Acción recomendada |
|---|---|---|
| `docs/PLAN_ACTIVE.md` | Estado operativo obsoleto + referencias rotas a `_archive` | Actualizar o retirar como canónico |
| `docs/PROJECT_STATUS.md` | Resumen ejecutivo ya no fiable | Actualizar o retirar como canónico |
| `docs/ROADMAP.md` | Duplica `PLAN_ACTIVE.md` y también está obsoleto | Mantener uno solo o archivar |
| `docs/AUDIT_INDEX.md` | Apunta a archivos no existentes | Reparar o retirar |

## 6.3 Deberían archivarse o reclasificarse como histórico

Estos documentos ya no parecen "estado vivo", sino bitácora histórica:

- `docs/FRONTEND_TESTS_STATUS.md`
- `docs/NEXT_STEPS.md`
- `docs/SUMMARY_WORK_COMPLETED.md`
- `docs/SESSION_2026-02-22_FRONTEND_TESTS.md`
- `docs/RESUMEN_TRABAJO_2026-02-22.md`

Acción recomendada:

1. moverlos a un histórico real,
2. o añadir banner visible `DOCUMENTO HISTÓRICO / NO CANÓNICO`.

## 6.4 Necesitan aclaración de alcance, no necesariamente reescritura completa

| Documento | Aclaración necesaria |
|---|---|
| `docs/SETUP.md` | Dejar claro que es setup de desarrollo/build, no onboarding de usuario final |
| `docs/PYTHON_EMBED.md` | Confirmar que sigue reflejando el empaquetado actual |
| `docs/BUILD_AND_DEPLOY.md` | Revisar si los pasos manuales siguen siendo los vigentes |

---

## 7. Riesgos principales si no se actúa

1. **Riesgo de soporte**:
   - La app evoluciona más rápido que el manual y los docs canónicos.

2. **Riesgo de regresión visual/UX**:
   - Dos fuentes de verdad para tema/modo.

3. **Riesgo de compliance/comercial**:
   - Claims WCAG y de estado del producto más fuertes que la evidencia viva.

4. **Riesgo de release desktop**:
   - El arranque sidecar es robusto pero sigue demasiado poco blindado por smoke tests específicos.

5. **Riesgo de mantenimiento**:
   - Archivos monolíticos y stores mezclados elevan el coste de cada cambio.

---

## 8. Recomendaciones priorizadas

## Sprint A - Consolidación de fuentes de verdad

1. Unificar tema en `themeStore`.
2. Retirar tema legacy de `appStore`.
3. Decidir cuál es el documento canónico de estado real.
4. Crear o eliminar de verdad `docs/_archive/`.

## Sprint B - Documentación viva

1. Reescribir `README.md`.
2. Actualizar `CHANGELOG.md`.
3. Regenerar `docs/README.md`, `docs/index.md`, `docs/user-manual/README.md`.
4. Corregir `adr/001-sqlite-database.md`.

## Sprint C - Accesibilidad realista

1. Cubrir `material` y `nora` en E2E.
2. Endurecer thresholds de accesibilidad.
3. Rehacer `WCAG_COLOR_AUDIT.md` con alcance y evidencia actual.

## Sprint D - Hardening de distribución desktop

1. Añadir smoke tests del arranque Tauri.
2. Probar warming mode, restart y fallo terminal.
3. Formalizar checklist de release desktop.

## Sprint E - Deuda estructural

1. Trocear `_analysis_phases.py`.
2. Trocear `SettingsView.vue`.
3. Trocear `ProjectDetailView.vue`.
4. Eliminar configuración duplicada de pytest.

---

## 9. Veredicto final

La aplicación está más cerca de "producto serio" en código que en documentación y gobierno técnico.

Estado real por áreas:

- Código de análisis/persistencia: **alto**
- UX de primer arranque: **alto**
- Accesibilidad: **medio-alto**, pero no cerrada del todo
- Testing unitario/integración: **alto**
- Testing de sistema desktop: **medio-bajo**
- Documentación activa/canónica: **bajo**
- Consistencia arquitectónica frontend: **media**

Diagnóstico global:

- La app no necesita ahora mismo una oleada de features.
- Necesita consolidación.
- Si no se corrige la capa documental y de fuentes de verdad, el coste de seguir creciendo será desproporcionado y la percepción externa del producto irá por detrás o por delante de la realidad según el documento que se abra.

---

## 10. Anexo de evidencias rápidas

### Versionado

- App/package: `0.11.12`
- README/docs públicas: aún entre `0.9.5` y `0.10.15`

### Esquema

- Código real: `SCHEMA_VERSION = 34`
- ADR principal: sigue en `29`

### Testing

- `frontend`: aproximadamente 990 tests/its por conteo estático
- `tests/`: aproximadamente 4213 tests Python por conteo estático
- Docs activas de testing: siguen ancladas a `65` y `555`

### Validación dinámica ejecutada para esta auditoría

- `npm run type-check` -> OK
- `pytest tests/api/test_project_file_endpoints.py -q` -> 4/4 OK
- `pytest tests/api/test_project_settings.py -q` -> 14/14 OK
