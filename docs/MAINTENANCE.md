# Mantenimiento y Actualización de Dependencias

Checklist de dependencias y datos a revisar periódicamente para mantener
Narrative Assistant actualizado y seguro.

---

## Dependencias NLP (revisar cada 6 meses)

- [ ] **spaCy** (`es_core_news_lg`): verificar nuevas versiones del modelo español
  - Repo: https://github.com/explosion/spacy-models
  - Actual: v3.x — comprobar compatibilidad con pipeline existente
- [ ] **sentence-transformers** (`paraphrase-multilingual-MiniLM-L12-v2`):
  - HuggingFace: https://huggingface.co/sentence-transformers/
  - Verificar si hay modelos multilingües más precisos o ligeros
- [ ] **Ollama**: comprobar nuevos modelos disponibles
  - `llama3.2` (3B, default), `qwen2.5` (7B, mejor español), `mistral` (7B)
  - https://ollama.com/library — evaluar nuevos modelos con buen soporte español

## Datos lingüísticos (revisar anualmente)

- [ ] **WordNet OMW**: versión actual 1.4 — verificar nuevas releases en https://omwn.org
  - Regenerar `synonyms.db`: `python scripts/build_thesaurus_db.py --force`
- [ ] **NLTK**: compatibilidad con versión actual de Python
  - Solo se usa como herramienta de build (genera `synonyms.db`), no en runtime
- [ ] **Diccionarios RAE/externos**: los endpoints solo generan URLs, verificar que siguen activas
  - RAE DLE: `https://dle.rae.es/{palabra}`
  - WordReference: `https://www.wordreference.com/definicion/{palabra}`

## Frontend (revisar cada 3 meses)

- [ ] **Vue 3**: major/minor updates — https://github.com/vuejs/core/releases
- [ ] **PrimeVue**: nuevos componentes, breaking changes — https://primevue.org/changelog
- [ ] **Vite**: mejoras de rendimiento — https://github.com/vitejs/vite/releases
- [ ] **TypeScript**: versión — verificar compatibilidad con vue-tsc
- [ ] **Tauri**: actualizaciones del runtime — https://github.com/tauri-apps/tauri/releases

## Backend (revisar cada 3 meses)

- [ ] **FastAPI**: versión, nuevas features — https://github.com/tiangolo/fastapi/releases
- [ ] **Pydantic v2**: verificar si hay v3 en el horizonte
- [ ] **SQLite**: verificar WAL mode sigue óptimo, nuevas features útiles
- [ ] **Python**: compatibilidad 3.11+ — testar con nuevas minor versions

## Seguridad

- [ ] `pip audit` — vulnerabilidades en dependencias Python
- [ ] `npm audit` — vulnerabilidades en dependencias frontend
- [ ] Revisar CVEs en dependencias directas (spaCy, FastAPI, Pydantic, sentence-transformers)
- [ ] Verificar que no hay datos de manuscritos en logs o telemetría

## Cómo actualizar dependencias

```bash
# 1. Crear branch
git checkout -b chore/update-deps

# 2. Backend
pip install --upgrade -e ".[dev]"
python -m pytest  # verificar

# 3. Frontend
cd frontend && npm update
npm run build     # verificar compilación
npm audit fix     # corregir vulnerabilidades

# 4. Modelos NLP (si hay nuevas versiones)
python scripts/download_models.py --force

# 5. Thesaurus (si hay nueva versión de WordNet OMW)
python scripts/build_thesaurus_db.py --force

# 6. Revisar CHANGELOG de cada dependencia por breaking changes
# 7. Commit y PR
```

---

## Features diferidas para sprints futuros

### Eventos contradictorios cross-book (~59h)

Detectar automáticamente cuando un evento en Libro A contradice un evento en
Libro B (ej: personaje muere en Libro 2 pero aparece vivo en Libro 3).

**Infraestructura ya existente**:
- `analysis/event_types.py` — Taxonomía de 45+ tipos de eventos en 3 tiers
- `analysis/event_detection.py` — Detección NLP (spaCy + regex) para Tier 1
- `analysis/event_detection_llm.py` — Detección LLM (Ollama) para eventos complejos
- `analysis/event_continuity.py` — EventContinuityTracker (intra-libro)
- `llm/prompts.py` — Prompts NoT para razonamiento temporal + self-reflection

**Fases de implementación**:

| Fase | Componente | Descripción | Horas |
|------|-----------|-------------|-------|
| 3a | Event persistence | Tabla `events` en SQLite + migración | 8h |
| 3b | Cross-book matcher | Encontrar eventos relacionados entre libros por entidad + tipo | 12h |
| 3c | LLM contradiction | Prompts especializados para comparar pares de eventos | 16h |
| 3d | API + frontend | Endpoint + vista de reporte | 11h |
| 3e | Temporal cross-ref | Comparar timelines entre libros (requiere qwen2.5 32K context) | 12h |

**Riesgos**: Falsos positivos altos sin fine-tuning; requiere LLM ≥7B params.

### ~~Wire-ups pendientes~~ ✅ COMPLETADO (S17)

| Feature | Componente(s) | Dónde cableado | Estado |
|---------|--------------|----------------|--------|
| VersionHistory | `VersionHistory.vue`, `VersionComparison.vue`, `VersionSparkline.vue` | `ResumenTab.vue` — stat-card + full card | ✅ S17 |
| LicenseDialog | `LicenseDialog.vue` | `SettingsView.vue` — sección "Licencia" | ✅ S17 |
| HomeView | `HomeView.vue` | Router `/` → component, MenuBar "Inicio" | ✅ S17 |
| Suppression Rules | `SuppressionRulesDialog.vue` | `AlertsDashboard.vue` — toolbar button | ✅ S17 |

### Mejoras de componentes (baja prioridad)

- `CharacterView.vue` → migrar a `useEntityCrud` composable
- `CharacterSheet.vue` → usar `useEntityUtils` para `ATTRIBUTE_LABELS`
