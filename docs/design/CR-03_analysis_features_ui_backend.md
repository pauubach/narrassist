# Diseno corregido CR-03: configuracion de metodos NLP UI<->Backend

Fecha: 2026-03-03
Estado: DISENO CORREGIDO (sin implementacion)
Prioridad: P0
Relacionados: CR-03, HI-08, HI-20, HI-21

---

## 0) Objetivo y alcance

Cerrar de forma real el gap CR-03:

- El usuario configura metodos en UI.
- La configuracion se persiste por proyecto en backend.
- El analisis usa esa configuracion de forma verificable.
- Si algo no esta disponible en runtime, hay degradacion controlada y mensaje claro.

Este documento NO implementa codigo. Define contrato, flujo y plan ejecutable.

---

## 1) Baseline validado en codigo actual

### 1.1 Hechos confirmados

1. Frontend guarda metodos en localStorage global (`enabledNLPMethods`).
- Evidencia: `frontend/src/composables/useSettingsPersistence.ts:2,40,68,119,189`.

2. El inicio de analisis no envia settings de metodos.
- Evidencia: `frontend/src/stores/analysis.ts:272-320` (solo `file` y `mode`).

3. Backend ya intenta leer `project.settings.analysis_features`.
- Evidencia: `api-server/routers/_analysis_phases.py:1132-1152`.

4. `GET /api/projects/{id}` devuelve `ApiResponse` con `data`, sin `settings` en payload actual.
- Evidencia: `api-server/routers/projects.py:298-409`.

5. No existe `PATCH /api/projects/{id}/settings` en router de proyectos.
- Evidencia: `api-server/routers/projects.py` (sin ruta PATCH de settings).

6. Capabilities reales usan `nlp_methods` por categoria, no claves planas tipo `nlp_llm`.
- Evidencia: `api-server/routers/system.py:888-1118`, `frontend/src/stores/system.ts:57-86`.

7. `quality_level` y `sensitivity` hoy viven en `llm_config` global.
- Evidencia: `api-server/routers/services.py:1141-1212`, `api-server/routers/_analysis_phases.py:1158-1175`.

8. En frontend, `api.patch()` parsea respuesta raw y no valida envelope `success`.
- Evidencia: `frontend/src/services/apiClient.ts:417`.

### 1.2 Conclusiones de baseline

- CR-03 sigue abierto.
- El diseno anterior tenia varios supuestos incompatibles con el contrato real.
- Hay que corregir contrato, schema, validacion y migracion.

---

## 2) Principios de diseno corregidos

1. Source of truth por proyecto en backend para `analysis_features`.
2. Sin ruptura del contrato actual `ApiResponse`.
3. Separar configuracion deseada del estado efectivo runtime.
4. No mover `quality_level` de `llm_config` en esta fase.
5. Validacion server-side basada en schema real de capabilities.
6. Degradacion sin fallos silenciosos y con mensajes no tecnicos.
7. Migracion sin magia: no intentar leer localStorage desde backend.

---

## 3) Modelo de datos corregido (project.settings)

## 3.1 Schema propuesto para `analysis_features`

```json
{
  "schema_version": 1,
  "pipeline_flags": {
    "character_profiling": true,
    "network_analysis": true,
    "anachronism_detection": true,
    "ooc_detection": true,
    "classical_spanish": true,
    "name_variants": true,
    "multi_model_voting": true,
    "spelling": true,
    "grammar": true,
    "consistency": true,
    "speech_tracking": true
  },
  "nlp_methods": {
    "coreference": ["embeddings", "llm", "morpho", "heuristics"],
    "ner": ["spacy", "gazetteer", "llm"],
    "grammar": ["spacy_rules", "languagetool", "llm"],
    "spelling": ["patterns", "symspell", "hunspell", "pyspellchecker", "languagetool", "beto", "llm_arbitrator"],
    "character_knowledge": ["rules", "llm", "hybrid"]
  },
  "updated_at": "2026-03-03T00:00:00Z",
  "updated_by": "ui"
}
```

Notas de campos de auditoria:
- `updated_by` admite: `ui` | `migration` | `api`.
- Su objetivo es trazabilidad de origen del cambio (no control de permisos).

## 3.2 Que se usa de inmediato vs posterior

Uso inmediato (MVP CR-03):
- `pipeline_flags` se aplica en backend via `_SETTINGS_MAP` ya existente.
- Esto cierra el gap "UI configura -> backend obedece" de forma trazable.
- Alcance MVP de `pipeline_flags`: solo las 11 claves existentes hoy en `_SETTINGS_MAP`.
- `UnifiedConfig` expone mas `run_*`, pero su apertura a UI queda para fase posterior controlada.

Uso en iteracion posterior:
- `nlp_methods` por categoria/metodo se consume donde el motor ya lo soporte.
- Si un modulo no soporta aun override fino, se registra warning explicito.

## 3.3 Lo que NO entra en CR-03

No incluir en `analysis_features` en esta fase:
- `quality_level`
- `sensitivity`

Razon:
- Ya tienen fuente de verdad global en `llm_config`.
- Mezclar dos autoridades en la misma fase aumenta inconsistencia.

---

## 4) Contrato API corregido

## 4.1 GET /api/projects/{id} (extender, no romper)

Mantener envelope actual:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "...",
    "...": "...",
    "settings": {
      "analysis_features": { "...": "..." }
    }
  }
}
```

Regla:
- Si el proyecto no tiene `analysis_features`, devolver defaults calculados (sin escribir DB automaticamente).
- Definicion de defaults calculados (MVP):
  - `pipeline_flags`: las 11 claves en `true` (preferencia deseada por defecto).
  - `nlp_methods`: por categoria, solo metodos con `default_enabled=true` en `capabilities`.

## 4.2 PATCH /api/projects/{id}/settings (nuevo)

Request:

```json
{
  "analysis_features": {
    "schema_version": 1,
    "pipeline_flags": { "grammar": false },
    "nlp_methods": {
      "coreference": ["morpho", "heuristics"]
    }
  }
}
```

Response (ApiResponse):

```json
{
  "success": true,
  "data": {
    "settings": {
      "analysis_features": { "...sanitized..." }
    },
    "runtime_warnings": [
      "El metodo avanzado de contexto no esta disponible ahora. Se usara modo estandar."
    ]
  }
}
```

Importante:
- Merge profundo de `settings` (no `dict.update()` superficial).
- Preservar otras ramas de settings existentes.
- Semantica de arrays en merge profundo:
  - En `nlp_methods`, cada categoria enviada reemplaza COMPLETA esa lista.
  - No hay union/interseccion implicita entre listas viejas y nuevas.

## 4.3 Validacion corregida

Validar contra `capabilities.nlp_methods[category][method]`.

Reglas:
1. Si categoria/metodo no existe en schema conocido: eliminar y reportar warning.
2. MVP: toda no disponibilidad se trata como transitoria para persistencia (no borrar de `desired`).
3. Si metodo no disponible por estado runtime (ej. servicio apagado): degradar solo en ejecucion.
4. Si una categoria queda sin metodos efectivos en runtime: aplicar fallback por `default_enabled` de esa categoria.
5. Si no hay fallback posible: desactivar subcomponente afectado y notificar en lenguaje no tecnico.
6. Clasificacion fina transitorio vs estructural se introduce en fase posterior, cuando haya senales confiables explicitas.

---

## 5) Flujo funcional corregido

## 5.1 Carga de proyecto

1. UI carga capabilities (`/api/system/capabilities`).
2. UI carga proyecto (`/api/projects/{id}`) y extrae `data.settings.analysis_features`.
3. UI muestra toggles por proyecto con estado deseado y avisos de disponibilidad actual.

## 5.2 Guardado

1. Usuario cambia metodos/flags.
2. UI envia PATCH de settings del proyecto.
3. Backend valida y sanea.
4. UI recibe settings saneados + warnings de degradacion runtime.
5. Concurrencia MVP: estrategia `last-write-wins` (ultima escritura valida prevalece).

## 5.3 Analisis

1. `startAnalysis` se mantiene (multipart actual).
2. Backend lee `project.settings.analysis_features` al iniciar.
3. Backend calcula `effective_config` para esa corrida (sin sobreescribir `desired`).
4. Progreso y mensajes reflejan degradaciones aplicadas.
5. Si settings cambian durante una corrida activa, aplican a la siguiente corrida (no a la actual).

---

## 6) UX y mensajes no tecnicos (obligatorio)

## 6.1 Reglas de mensaje

- Nunca exponer stacktrace o nombre de libreria.
- Explicar en 3 capas:
  - Que paso.
  - Que hara el sistema ahora.
  - Que puede hacer el usuario.

## 6.2 Copys propuestos

1. "Estamos preparando el analisis avanzado."
2. "Un metodo avanzado no esta disponible ahora. Continuamos con modo estandar para no detener el analisis."
3. "Si quieres usar el modo avanzado, abre Configuracion y pulsa Reintentar."

---

## 7) Migracion corregida (sin backend script)

Problema del diseno anterior:
- Un script backend no puede leer localStorage del navegador.

Estrategia corregida:

1. Primera apertura de un proyecto sin `analysis_features`:
- Si existe `enabledNLPMethods` global en localStorage, UI ofrece importacion explicita al proyecto.
- Botones: "Importar configuracion" o "Usar recomendada".

2. Si usuario importa:
- UI convierte estructura legacy -> schema nuevo.
- UI hace PATCH a proyecto.
- UI puede registrar log de diagnostico (debug) indicando que detecto config legacy y si se importo o no.

3. Si usuario no importa:
- UI usa defaults recomendados por capabilities y los guarda al confirmar.

4. Tras rollout estable:
- eliminar definitivamente `enabledNLPMethods` global de localStorage.

---

## 8) Frontend corregido (arquitectura)

## 8.1 Ajustes de contrato tipos

- Extender `ApiProject` para incluir `settings` opcional.
- Extender transformer API->domain para mapear settings.
- Mantener compatibilidad con proyectos antiguos sin settings.

## 8.2 Ajustes de cliente API

- Para PATCH de settings, usar parsing que valide envelope `success`.
- Evitar `api.patch()` raw para este endpoint si no valida `success`.
- Propuesta: helper `patchChecked` o wrapper dedicado de settings.

## 8.3 Ubicacion de UI

- Mantener Settings global para preferencias de app.
- Gestion de `analysis_features` por proyecto en vista de proyecto (no global).

---

## 9) Backend corregido (arquitectura)

## 9.1 Reuso de lo ya existente

- Reusar aplicacion de `_SETTINGS_MAP` en `_analysis_phases.py` para `pipeline_flags`.
- No introducir campos inexistentes en `UnifiedConfig` (ej. `use_embeddings`, `use_morpho`, `use_heuristics`).
- Limitacion actual de `_SETTINGS_MAP`: en codigo vigente solo fuerza `False` (deshabilita), no fuerza `True`.

## 9.2 Semantica de aplicacion de `pipeline_flags` (decision MVP)

1. `flag=false`: desactivar siempre en `effective_config`.
2. `flag=true`: interpretar como preferencia de activacion, no como override forzado.
3. Activacion efectiva de `true` solo si capacidades y politicas de seguridad lo permiten.
4. Si un perfil protector o constraint de runtime impide activar, se mantiene degradado y se emite warning no tecnico.

## 9.3 Funcion de normalizacion

Definir normalizacion central:
- entrada: `requested_analysis_features`, `capabilities`, `runtime_status`.
- salida:
  - `persisted_desired_features` (estable)
  - `effective_runtime_features` (solo corrida actual)
  - `warnings`

---

## 10) Estrategia de fallbacks (sin silencios)

## 10.1 Politica

1. Fallo transitorio (servicio no iniciado):
- no modificar deseado persistido.
- degradar solo en ejecucion.

2. Fallo estructural (metodo no soportado en maquina):
- marcar metodo como no aplicable para ese equipo.
- sugerir alternativa automatica.

3. Categoria sin metodos efectivos:
- fallback por `default_enabled`.
- si sigue vacia, desactivar submodulo y notificar.

## 10.2 Trazabilidad

Registrar por corrida:
- `desired_methods`
- `effective_methods`
- `degradation_reasons`

Esto permite auditar falsos positivos y performance.

---

## 11) Plan de pruebas exhaustivo

## 11.1 Backend

1. Contract test GET proyecto incluye `settings.analysis_features` en envelope `data`.
2. Contract test PATCH settings con merge profundo.
3. Validacion category/method contra `nlp_methods` real (mockeando capabilities con y sin GPU/servicios).
4. Runtime transitorio (ollama off): no borrar persistido.
5. Runtime fallback aplicado y warning emitido.
6. Proyecto sin settings: defaults estables.

## 11.2 Frontend

1. Carga y guardado por proyecto (no localStorage global).
2. Avisos no tecnicos ante degradacion.
3. Importacion one-shot desde legacy localStorage.
4. Confirmar que guardar usa wrapper con chequeo `success`.

## 11.3 E2E

1. Toggle en UI -> PATCH proyecto -> analisis usa flags.
2. Metodo avanzado habilitado pero servicio apagado -> degradacion runtime + mensaje.
3. Reanalisis posterior con servicio disponible -> recupera metodo deseado.
4. Cancelar y relanzar sin cambios -> no perder settings.

## 11.4 No funcional

1. Sin fallos silenciosos en guardado/settings.
2. Mensajeria continua en operaciones largas.
3. Sin sobrecargar CPU por reintentos agresivos de validacion.

---

## 12) Rollout recomendado

Fase A (P0, cierre real CR-03)
- Contrato GET/PATCH settings por proyecto.
- Persistencia `analysis_features`.
- Aplicacion inmediata de `pipeline_flags` en backend.
- UI por proyecto conectada a backend.

Fase B (P1, metodo fino)
- Consumir `nlp_methods` por categoria en modulos que soporten override.
- `effective_runtime_features` + telemetria de degradacion.

Fase C (P1/P2)
- Retirar legado global `enabledNLPMethods`.
- Endurecer tests de regresion y observabilidad.

---

## 13) Decisiones cerradas para evitar ambiguedad

1. `quality_level`/`sensitivity` permanecen en `llm_config` en CR-03.
2. No se usa script backend para migrar localStorage.
3. Validacion de metodos contra schema real `nlp_methods` anidado.
4. Degradacion runtime no sobrescribe configuracion deseada persistida.
5. Endpoint de settings responde con `ApiResponse` y warnings de degradacion.
6. `pipeline_flags` MVP cubre solo las 11 claves de `_SETTINGS_MAP` actual.
7. Semantica de arrays en `nlp_methods`: reemplazo completo por categoria.
8. Concurrencia MVP: `last-write-wins`; cambios durante analisis aplican a la siguiente corrida.
9. Distincion transitorio/estructural fina se difiere; en MVP no se borra `desired` por indisponibilidad.

---

## 14) Riesgos residuales y mitigacion

Riesgo 1: desalineacion UI/backend por naming (camelCase/snake_case).
- Mitigacion: mapear en transformer y fijar tests de contrato.

Riesgo 2: settings parciales pisan otras ramas.
- Mitigacion: merge profundo con allowlist.

Riesgo 3: confusion usuario entre global y por proyecto.
- Mitigacion: copy explicito y migracion guiada en primera apertura.

Riesgo 4: degradaciones repetidas generan ruido.
- Mitigacion: deduplicar warnings por corrida y exponer resumen legible.

---

## 15) Definition of Done (CR-03)

CR-03 se considera cerrado solo si:

1. La configuracion de metodos se guarda en `project.settings.analysis_features`.
2. El backend la aplica en analisis de forma observable.
3. Los fallos de disponibilidad generan fallback + mensaje no tecnico.
4. No hay dependencia de localStorage global para metodos por proyecto.
5. Tests backend, frontend y e2e del flujo pasan.

---

## 16) Referencias de codigo usadas para esta correccion

- `api-server/routers/projects.py:298-409,445`
- `api-server/routers/_analysis_phases.py:1132-1175`
- `src/narrative_assistant/pipelines/unified_analysis.py:80-161`
- `api-server/routers/system.py:888-1118`
- `api-server/routers/services.py:1141-1212`
- `frontend/src/composables/useSettingsPersistence.ts:2-189`
- `frontend/src/stores/analysis.ts:272-320`
- `frontend/src/stores/system.ts:57-86`
- `frontend/src/services/apiClient.ts:417`

