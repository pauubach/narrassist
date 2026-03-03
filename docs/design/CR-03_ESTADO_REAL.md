# CR-03 - Estado Real (Actualizado)

Fecha: 2026-03-03  
Estado: Re-evaluado tras fixes de runtime/UI/tests

---

## Resumen ejecutivo

CR-03 ya no esta en el estado "60%".  
El gap principal (persistencia sin aplicacion real en pipeline) esta cerrado para los flags y metodos del MVP.

Estado actual:

- Backend settings (`GET/PATCH`) estable y validado.
- UI conectada al backend en el flujo de analisis (`startAnalysis` y `runPartialAnalysis`).
- `pipeline_flags` con efecto runtime en las fases relevantes.
- `nlp_methods` consumidos en runtime (no solo persistidos).
- Cobertura de tests ampliada (API + runtime + frontend store).

---

## Cambios confirmados

### 1) UI conectada al backend en ejecucion

Archivo:
- `frontend/src/stores/analysis.ts`

Hecho:
- Antes de lanzar analisis completo o parcial se sincronizan settings locales hacia:
  - `PATCH /api/projects/{id}/settings`
- Si la sincronizacion falla, el analisis continua (best-effort, sin bloquear al usuario).

Cobertura:
- `frontend/src/stores/__tests__/analysis.spec.ts`
  - test de sync previo en `startAnalysis`
  - test de sync previo en `runPartialAnalysis`
  - test de degradacion cuando falla el sync

### 2) pipeline_flags aplicados con efecto real

Archivo:
- `api-server/routers/_analysis_phases.py`
- `api-server/routers/analysis.py`
- `api-server/routers/_enrichment_phases.py`

Estado por flag MVP:

- `character_profiling`: gating efectivo (enrichment)
- `network_analysis`: gating efectivo (enrichment)
- `anachronism_detection`: gating efectivo (consistency)
- `ooc_detection`: gating efectivo (consistency)
- `classical_spanish`: gating efectivo (consistency)
- `name_variants`: gating efectivo (NER aliases + alias enrichment)
- `multi_model_voting`: gating efectivo (resolucion de metodos coref)
- `spelling`: gating efectivo en fase grammar/corrections
- `grammar`: gating efectivo en fase grammar
- `consistency`: gating efectivo en pipeline
- `speech_tracking`: gating efectivo (consistency)

### 3) nlp_methods consumidos en runtime

Archivo:
- `api-server/routers/_analysis_phases.py`

Hecho:
- `apply_license_and_settings` normaliza y guarda `selected_nlp_methods` en `ctx`.
- Gating disable-only por categorias vacias:
  - `ner`, `coreference`, `grammar`, `spelling`, `character_knowledge`
- Consumo por fase:
  - NER: aplica seleccion `ner` (llm/gazetteer)
  - Coreference/Fusion: aplica `coreference` y `multi_model_voting`
  - Grammar: aplica `grammar` (`languagetool`, `llm`) y gating de `spelling`

Nota:
- En `character_knowledge`, la seleccion fina `rules/llm/hybrid` sigue con cobertura parcial (la implementacion actual de enrichment usa base rules).  
- No bloquea CR-03 MVP porque ya existe consumo real y degradacion controlada.

---

## Tests ejecutados

Backend:

```bash
pytest tests/api/test_project_settings.py \
       tests/api/test_project_settings_e2e.py \
       tests/unit/test_cr03_runtime_settings.py -q
```

Resultado:
- 17 passed

Frontend:

```bash
npm --prefix frontend run test:run -- src/stores/__tests__/analysis.spec.ts
```

Resultado:
- 52 passed

---

## Estado actual de conformidad

- Persistencia por proyecto: `OK`
- Validacion robusta payload: `OK`
- Aplicacion runtime de flags: `OK`
- Consumo runtime de nlp_methods: `OK`
- Sincronizacion UI->backend en ejecucion: `OK`
- Tests contract + runtime/store: `OK`

Veredicto:
- CR-03 MVP: **cerrado funcionalmente**.
- Mejora posterior recomendada: ampliar control fino de `character_knowledge` (`llm/hybrid`) y extender sync directo desde la vista de settings global si se quiere evitar dependencia de localStorage antes de analizar.
