# Auditoría Integral — Narrative Assistant v0.7.16

> **Fecha**: 2026-02-10
> **Auditors**: Panel de expertos (QA, Backend, Frontend, UX, Copy)
> **Alcance**: Licensing, pipeline, features, UX, copy, accesibilidad

---

## Resumen Ejecutivo

La aplicación es sólida y profesional. Sin embargo, hay **desalineaciones críticas** entre el nuevo modelo de licencias y el código existente, **features vendidas pero no accesibles** desde el frontend, y **problemas de UX** que afectan a la primera experiencia de usuario.

**Hallazgos totales**: 68
- Críticos: 14
- Importantes: 28
- Menores: 16
- Fortalezas identificadas: 10

---

## PARTE 1: LICENSING — Código vs Documentación

El `LICENSING.md` fue actualizado a 3 tiers sin módulos, pero el código sigue con el modelo antiguo.

### L1. Enums obsoletos en models.py [CRÍTICO]

- `LicenseModule` (CORE, NARRATIVA, VOZ_ESTILO, AVANZADO) → **ELIMINAR**
- `LicenseBundle` (SOLO_CORE, PROFESIONAL, COMPLETO) → **ELIMINAR**
- `LicenseTier`: FREELANCE/AGENCIA → renombrar a CORRECTOR/PROFESIONAL
- **Archivo**: `src/narrative_assistant/licensing/models.py:21-93`

### L2. TierLimits mide manuscritos, no páginas [CRÍTICO]

- `max_manuscripts_per_month` → debe ser `max_pages_per_month`
- Valores incorrectos: FREELANCE=5, AGENCIA=15 → CORRECTOR=1500, PROFESIONAL=3000
- EDITORIAL `max_devices=100` → debe ser 10
- No hay campo `rollover_pages`
- **Archivo**: `src/narrative_assistant/licensing/models.py:119-147`

### L3. License y Subscription referencian bundle [CRÍTICO]

- `License.bundle: LicenseBundle` → eliminar campo
- `License.has_module()` → eliminar método
- `License.modules` property → eliminar
- `Subscription.bundle` → eliminar campo
- **Archivo**: `src/narrative_assistant/licensing/models.py:277-677`

### L4. Schema SQL tiene columnas obsoletas [CRÍTICO]

- `licenses.bundle TEXT` → eliminar columna
- `subscriptions.bundle TEXT` → eliminar columna
- Default `tier='freelance'` → cambiar a `'corrector'`
- Faltan: `pages_per_month`, `rollover_pages_available`
- **Archivo**: `src/narrative_assistant/licensing/models.py:685-779`

### L5. Verificación cuenta manuscritos, no páginas [CRÍTICO]

- `_calculate_quota_remaining()`: hace `COUNT(*)` de registros, no `SUM(word_count)/250`
- `check_quota()`: devuelve manuscritos restantes, no páginas
- `record_usage()`: no convierte word_count a páginas
- No hay lógica de rollover
- **Archivo**: `src/narrative_assistant/licensing/verification.py:685-829`

### L6. check_module_access() debe ser check_tier_feature() [CRÍTICO]

- `check_module()` recibe `LicenseModule` que será eliminado
- `check_module_access()` función pública → renombrar
- **Archivo**: `src/narrative_assistant/licensing/verification.py:835-858, 1098-1109`

### L7. ModuleNotLicensedError duplicado + falta TierFeatureError [CRÍTICO]

- Error definido en DOS sitios: `core/errors.py:491` y `verification.py:170`
- `ModuleNotLicensedError` → renombrar a `TierFeatureError`
- Mensaje dice "módulo X" → debe decir "plan Profesional"
- `QuotaExceededError` dice "manuscritos" → debe decir "páginas"
- **Archivos**: `src/narrative_assistant/core/errors.py:463-507`, `verification.py:150-187`

### L8. Exports de licensing/__init__.py obsoletos [IMPORTANTE]

- Exporta `LicenseModule`, `LicenseBundle`, `ModuleNotLicensedError`
- Falta exportar `TierFeatureError`
- **Archivo**: `src/narrative_assistant/licensing/__init__.py:29-50`

### L9. API endpoints usan modelo antiguo [CRÍTICO]

- `/api/license/check-module/{module_name}` → debe ser `/check-feature/{feature_name}`
- `/api/license/record-manuscript` → debe aceptar `word_count`, convertir a páginas
- Status devuelve `manuscripts_used/max` → debe ser `pages_used/max`
- **Archivo**: `api-server/routers/license.py:44-344`

### L10. Frontend license store tiene tipos obsoletos [CRÍTICO]

- `LicenseTier = 'freelance' | 'agencia'` → `'corrector' | 'profesional' | 'editorial'`
- `LicenseModule` type → ELIMINAR
- `LicenseInfo.modules: LicenseModule[]` → ELIMINAR
- `manuscripts_used/max` → `pages_used/pages_max`
- Tier display names incorrectos: "Freelance", "Agencia"
- **Archivo**: `frontend/src/stores/license.ts:9-83`

### L11. LicenseDialog.vue muestra módulos obsoletos [CRÍTICO]

- Sección "Módulos incluidos" con tags → ELIMINAR
- `moduleNames` mapping → ELIMINAR
- Cuota dice "Manuscritos este mes" → "Páginas este mes"
- **Archivo**: `frontend/src/components/LicenseDialog.vue:67-85, 330-342`

---

## PARTE 2: FEATURES — Accesibilidad y Completitud

### F1. Feature gating NO implementado [CRÍTICO]

Ningún feature Pro tiene gate de tier. Cualquier usuario puede usar todo:
- `character_profiling.py` → sin check de tier
- `character_network.py` → sin check de tier
- `out_of_character.py` → sin check de tier
- `classical_spanish.py` → sin check de tier
- Coreference multi-model → sin check de tier
- **Acción**: Implementar `check_tier_feature()` antes de cada feature Pro

### F2. OOC Detection NO integrado en pipeline [IMPORTANTE]

- Módulo existe: `src/narrative_assistant/analysis/out_of_character.py`
- Pero `run_real_analysis()` **no lo llama** en ninguna fase
- Sin endpoint API
- Frontend lo muestra implícitamente via BehaviorExpectations pero sin etiqueta "OOC"
- **Acción**: Integrar en pipeline (fase 7 o post-consistency) + crear endpoint

### F3. Classical Spanish sin control UI [IMPORTANTE]

- Backend existe: `src/narrative_assistant/nlp/classical_spanish.py`
- Normalizer implementado pero NO integrado en pipeline principal
- Sin toggle en Settings ni en CorrectionConfigModal
- **Acción**: Integrar en pipeline + añadir toggle en Settings → Métodos de análisis

### F4. Anachronism endpoint huérfano [IMPORTANTE]

- Backend: `/api/projects/{id}/knowledge/anachronisms` existe
- Frontend: **nunca lo llama**
- Timeline tab muestra eventos temporales pero no usa este endpoint específico
- **Acción**: Conectar endpoint con frontend o eliminar si redundante

### F5. Character Profiling disperso en UI [IMPORTANTE]

- 6 indicadores implementados correctamente en backend
- Pero en frontend están repartidos en 5+ tabs diferentes:
  - Presencia → EntitiesTab (conteo de menciones)
  - Acciones → Alertas de comportamiento
  - Habla → DialogueAttributionPanel
  - Definición → Character Sheet
  - Sentimiento → EmotionalAnalysisTab
  - Entornos → CharacterLocationTab
- Falta: Vista unificada de perfil de personaje con los 6 indicadores
- **Acción**: Crear CharacterProfileModal o panel consolidado

### F6. Settings no llegan al backend durante análisis [CRÍTICO]

- Frontend muestra settings de sensibilidad, métodos, consenso
- `start_analysis()` NO recibe parámetros de settings
- `unified_analysis.py` tiene `UnifiedConfig` con flags (`run_relationships`, `run_voice_profiles`, etc.) que están siempre en False
- **Impacto**: Features Pro (Relationships, Interactions, Knowledge, Voice) siempre desactivadas
- **Acción**: Pasar settings de UI al endpoint `/analyze` y mapearlos a `UnifiedConfig`

### F7. Componentes huérfanos [MENOR]

- `StoryBibleTab.vue` — definido pero no importado ni exportado
- `DataManagementDialog.vue` — creado pero nunca referenciado
- `src-tauri/src/cleanup.rs` — módulo Rust no integrado en main.rs
- **Acción**: Integrar o eliminar

---

## PARTE 3: PIPELINE — Integridad y Edge Cases

### P1. Cola pesada se pierde al reiniciar servidor [CRÍTICO]

- `_heavy_analysis_queue` es in-memory (lista Python)
- Si el servidor se reinicia, proyectos en cola quedan en status "queued_for_heavy" para siempre
- **Acción**: Persistir cola en BD o al menos marcar status al reiniciar

### P2. Coreference usa chapters_data en vez de chapters_with_ids [IMPORTANTE]

- Línea 1200: `chapters=chapters_data` → debería usar `chapters_with_ids` (con IDs de BD)
- Impacto: Menciones de correferencia no se vinculan correctamente a `chapter_id`
- **Archivo**: `api-server/routers/analysis.py:1200`

### P3. Fallo silencioso en persistencia de capítulos [IMPORTANTE]

- Si `_persist_chapters_to_db()` falla, se captura la excepción y se continúa
- Fase 5 (Coreference) corre sin datos de capítulos → resultados degradados sin aviso
- **Archivo**: `api-server/routers/analysis.py:382-420`

### P4. Sin manejo de documento vacío [IMPORTANTE]

- Si `full_text = ""`, `word_count = 0`, pipeline continúa
- Debería lanzar `EmptyDocumentError` tempranamente
- **Acción**: Validar en fase 1 (parsing)

### P5. Sin health check de Ollama antes de fase 5 [IMPORTANTE]

- Si Ollama no corre, coreference falla silenciosamente o hace timeout
- **Acción**: Verificar Ollama antes de iniciar fase 5, mostrar warning si no disponible

### P6. Columnas BD nunca populadas [MENOR]

- `chapters.dialogue_ratio` — nunca se escribe
- `chapters.scene_count` — nunca se escribe
- `chapters.pov_character` — nunca se escribe
- `projects.detected_document_type` — nunca se lee
- `projects.settings_json` — se escribe, nunca se lee
- **Acción**: Poblar o eliminar del schema

### P7. Settings de proyecto se guardan pero nunca se leen [MENOR]

- `project_settings["recommended_analysis"]` se persiste tras clasificación
- Nunca se recupera para fases subsiguientes
- **Archivo**: `api-server/routers/analysis.py:500-517`

---

## PARTE 4: UX — Primera Experiencia y Flujos

### U1. Tutorial mezcla guía con setup de producto [IMPORTANTE]

- Paso 4 instala Ollama/LanguageTool (descarga de ~2GB) dentro del tutorial
- Debería separarse: Tutorial = guía, Setup = configuración
- **Archivo**: `frontend/src/components/TutorialDialog.vue:156-323`

### U2. Análisis arranca sin contexto para usuario nuevo [CRÍTICO]

- Al crear proyecto, análisis inicia automáticamente
- Usuario ve tabs vacías (Entidades, Alertas) sin explicación
- No hay banner "Análisis en progreso" visible
- **Acción**: Mostrar skeleton/loading en tabs + banner explicativo

### U3. Nombres de tabs inconsistentes entre UI y guía [CRÍTICO]

- UserGuideDialog usa: "Revisión", "Cronología", "Escritura"
- ProjectDetailView usa: "Alertas", "Timeline", "Estilo"
- **Impacto**: Usuario busca "Cronología" según la guía pero encuentra "Timeline"
- **Acción**: Unificar terminología en toda la app

### U4. Empty states sin acción ni contexto [IMPORTANTE]

| Estado | Mensaje actual | Problema |
|--------|---------------|----------|
| Sin proyectos | "No hay proyectos" | No explica qué es un proyecto |
| Sin entidades | (genérico) | No dice si es normal o error |
| Sin alertas | (genérico) | No confirma que el análisis acabó bien |
| Ollama caído | (error técnico) | No dice cómo solucionarlo |
| Sin internet | (genérico) | No explica modo offline |

### U5. "Entidad" vs "Personaje" vs "Manuscrito" vs "Documento" [IMPORTANTE]

- "Manuscrito" en marketing, "Documento" en UI → inconsistente
- "Entidad" en código, "Personaje" en UI cuando es character → confuso
- **Acción**: Crear guía de terminología interna

### U6. No hay "Deshacer" ni soft delete para proyectos [IMPORTANTE]

- Eliminar proyecto es irreversible sin confirmación adicional
- **Acción**: Implementar "Archivar" o papelera de 30 días

### U7. Settings sin feedback de guardado [MENOR]

- Cambiar settings no muestra confirmación visual
- **Acción**: Toast "Configuración guardada"

### U8. Sin breadcrumb en ProjectDetailView [IMPORTANTE]

- Usuario no sabe cómo volver, botón atrás sin label
- **Acción**: Añadir "← Proyectos > Mi Novela"

### U9. Re-análisis no aclara qué pasa con resultados previos [IMPORTANTE]

- Confirmación dice "Se volverá a analizar" pero no aclara: ¿se pierden alertas previas?
- **Acción**: Añadir "Los resultados anteriores se reemplazarán"

### U10. Tutorial sin "Saltar" en todos los pasos [IMPORTANTE]

- Solo el paso 0 tiene "No mostrar de nuevo"
- Resto de pasos no tienen opción de saltar
- **Acción**: Añadir "Saltar tutorial" en todos los pasos

---

## PARTE 5: ACCESIBILIDAD (WCAG)

### A1. Color como único indicador de severidad [CRÍTICO]

- Puntos rojo/naranja/amarillo/azul para severidad de alertas
- 8% de hombres con daltonismo no distinguen
- **Acción**: Añadir texto/icono junto al color

### A2. Botones solo con icono, sin texto ni aria-label [CRÍTICO]

- Sidebar tabs son solo iconos
- StatusBar indicadores sin texto
- **Acción**: Añadir `aria-label` y/o `<span class="sr-only">`

### A3. Focus visible insuficiente [IMPORTANTE]

- Componentes PrimeVue pueden tener focus states de bajo contraste
- **Acción**: Añadir `outline: 2px solid` en `:focus-visible`

### A4. Errores de formulario no vinculados a campos [IMPORTANTE]

- `<small class="p-error">` sin `aria-describedby` → lectores de pantalla no lo asocian
- **Acción**: Vincular con `id` + `aria-describedby`

### A5. Texto menor a 14px en metadatos [MENOR]

- StatusBar y metadatos usan `0.75rem` (12px)
- WCAG recomienda mínimo 14px
- **Acción**: Revisar tamaños mínimos

---

## PARTE 6: COPY — Revisión de textos

### C1. CorrectionConfigModal: "Heredado" sin contexto [IMPORTANTE]

- Tag "Heredado" aparece sin explicar de qué se hereda
- **Acción**: Cambiar a "Por defecto" con tooltip explicativo

### C2. AboutDialog demasiado técnico [IMPORTANTE]

- "Backend Python: Conectado", "Base de datos: SQLite"
- Un corrector no entiende ni le importa
- **Acción**: Simplificar a "Aplicación: Funcionando" / "Análisis: Disponible"

### C3. Paso 2 del tutorial referencia Ctrl+K sin implementar [MENOR]

- Menciona "paleta de comandos Ctrl+K" que no existe
- **Acción**: Eliminar referencia o implementar

### C4. Settings técnicos expuestos [IMPORTANTE]

- "Métodos NLP", "batch size", "embedding model" → jargón técnico
- **Acción**: Renombrar a lenguaje de corrector ("Métodos de detección", etc.)

### C5. DataManagementDialog: "automaticamente" sin tilde [MENOR]

- Línea 233: falta acento
- **Archivo**: `frontend/src/components/DataManagementDialog.vue:233`

---

## PLAN DE TRABAJO

### Sprint S7a: Licensing Migration (5 días)

| # | Tarea | Archivos | Prioridad |
|---|-------|----------|-----------|
| 1 | Eliminar `LicenseModule`, `LicenseBundle` de models.py | models.py | CRÍTICO |
| 2 | Renombrar tiers FREELANCE→CORRECTOR, AGENCIA→PROFESIONAL | models.py, verification.py | CRÍTICO |
| 3 | Cambiar cuota de manuscritos a páginas (250 words=1 page) | models.py, verification.py | CRÍTICO |
| 4 | Implementar rollover (1 mes) | verification.py | CRÍTICO |
| 5 | Renombrar ModuleNotLicensedError → TierFeatureError | core/errors.py | CRÍTICO |
| 6 | Crear check_tier_feature() | verification.py | CRÍTICO |
| 7 | Actualizar schema SQL (drop bundle, add pages_per_month) | models.py | CRÍTICO |
| 8 | Actualizar API endpoints (check-feature, record-usage) | license.py | CRÍTICO |
| 9 | Actualizar frontend store (tipos, tier names) | license.ts | CRÍTICO |
| 10 | Actualizar LicenseDialog (eliminar módulos, cambiar cuota) | LicenseDialog.vue | CRÍTICO |
| 11 | Actualizar exports de licensing/__init__.py | __init__.py | IMPORTANTE |
| 12 | Tests unitarios de nuevo modelo | tests/unit/ | IMPORTANTE |

### Sprint S7b: Feature Gating + Integration (5 días)

| # | Tarea | Archivos | Prioridad |
|---|-------|----------|-----------|
| 13 | Implementar feature gating en character_profiling | character_profiling.py | CRÍTICO |
| 14 | Implementar feature gating en character_network | character_network.py | CRÍTICO |
| 15 | Implementar feature gating en anachronism detection | temporal/ | CRÍTICO |
| 16 | Implementar feature gating en classical_spanish | classical_spanish.py | CRÍTICO |
| 17 | Implementar feature gating en multi-model voting | coreference_resolver.py | CRÍTICO |
| 18 | Integrar OOC detection en pipeline | analysis.py, out_of_character.py | IMPORTANTE |
| 19 | Integrar Classical Spanish en pipeline | analysis.py, classical_spanish.py | IMPORTANTE |
| 20 | Pasar settings de frontend a backend durante análisis | analysis.ts, analysis.py | CRÍTICO |
| 21 | Conectar endpoint de anachronisms con frontend | relationships.py, TimelineView.vue | IMPORTANTE |
| 22 | Crear CharacterProfileModal unificado (6 indicadores) | Nuevo componente | IMPORTANTE |

### Sprint S7c: Pipeline Fixes (3 días)

| # | Tarea | Archivos | Prioridad |
|---|-------|----------|-----------|
| 23 | Persistir cola pesada en BD | deps.py, analysis.py | CRÍTICO |
| 24 | Fix: chapters_with_ids en coreference | analysis.py:1200 | IMPORTANTE |
| 25 | Validar documento vacío en fase 1 | analysis.py | IMPORTANTE |
| 26 | Health check de Ollama antes de fase 5 | analysis.py | IMPORTANTE |
| 27 | Fix: fallo silencioso en persistencia de capítulos | analysis.py:382-420 | IMPORTANTE |
| 28 | Limpiar columnas BD no usadas | database.py | MENOR |
| 29 | Limpiar componentes huérfanos | StoryBibleTab, etc. | MENOR |

### Sprint S7d: UX + Copy (5 días)

| # | Tarea | Archivos | Prioridad |
|---|-------|----------|-----------|
| 30 | Unificar nombres de tabs (Alertas/Timeline/Estilo) | Múltiples | CRÍTICO |
| 31 | Banner de "Análisis en progreso" para usuario nuevo | ProjectDetailView.vue | CRÍTICO |
| 32 | Indicadores de severidad: color + texto + icono | Múltiples | CRÍTICO |
| 33 | aria-labels en botones de solo icono | Múltiples | CRÍTICO |
| 34 | Separar setup de Ollama del tutorial | TutorialDialog.vue | IMPORTANTE |
| 35 | Mejorar empty states con contexto y acciones | Múltiples | IMPORTANTE |
| 36 | Guía de terminología: Entidad/Personaje/Manuscrito/Doc | Interno | IMPORTANTE |
| 37 | Breadcrumb en ProjectDetailView | ProjectDetailView.vue | IMPORTANTE |
| 38 | "Saltar tutorial" en todos los pasos | TutorialDialog.vue | IMPORTANTE |
| 39 | Simplificar AboutDialog (sin jargón técnico) | AboutDialog.vue | IMPORTANTE |
| 40 | Renombrar settings técnicos a lenguaje de corrector | SettingsView.vue | IMPORTANTE |
| 41 | "Restaurar valores por defecto" en Settings | SettingsView.vue | IMPORTANTE |
| 42 | Fix copy: "Heredado"→"Por defecto", tildes | CorrectionConfigModal, DataMgmt | MENOR |

---

## Fortalezas Identificadas

1. Excelente localización al español — profesional y consistente en general
2. Confirmaciones claras para acciones destructivas
3. Diseño responsive con paneles redimensionables
4. ARIA roles implementados en MenuBar (keyboard navigation)
5. Progressive disclosure en settings y modales
6. Sistema de alertas bien categorizado con severidades
7. Export system completo (DOCX, PDF, MD, JSON, CSV)
8. Network graph interactivo con filtros avanzados
9. Multi-model voting visible en UI (MethodVotingBar, ConfidenceBadge)
10. Arquitectura modular Vue 3 + Pinia bien separada

---

## Estimación Total

| Sprint | Duración | Tareas |
|--------|----------|--------|
| S7a: Licensing Migration | 5 días | 12 tareas |
| S7b: Feature Gating + Integration | 5 días | 10 tareas |
| S7c: Pipeline Fixes | 3 días | 7 tareas |
| S7d: UX + Copy | 5 días | 13 tareas |
| **Total** | **18 días** | **42 tareas** |
