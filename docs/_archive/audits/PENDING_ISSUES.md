# 📋 Issues Pendientes de Resolución

**Última actualización**: 4 de febrero de 2026
**Versión**: 0.4.5+

---

## ✅ Issues Resueltos (26 → 26 resueltos)

Los siguientes issues fueron resueltos en sesiones de debugging:

| Issue | Descripción | Fix Aplicado |
|-------|-------------|--------------|
| #1 | "algo extraño" como concepto | Filtrado de frases genéricas en NER |
| #2-3 | María Sánchez como concepto + atributos cruzados | Fusión CHARACTER↔CONCEPT mejorada |
| #4 | Versión incorrecta 0.3.34 | Eliminado fallback hardcodeado |
| #5 | **Relaciones sin datos** | **Corregido matching chapter_id + contexto relativo** |
| #6 | Corrección de "y" (LanguageTool) | Añadido disabled_rules para WORD_REPEAT |
| #7 | Menús nativos no funcionan | Refactorizado useNativeMenu.ts con @tauri-apps/api/event |
| #8 | **Timeline flashback incorrecto** | **Añadida validación evidencia retrospectiva** |
| #9 | Solo línea "poetic" visible | Añadido toggle pie/bars en RegisterAnalysisTab |
| #10 | Cambios registro por diálogo/narración | Tooltip explicativo añadido |
| #11 | Focalización sin declarar | Tooltip explicativo sobre focalización declarativa |
| #12-13 | Feedback estado análisis | Añadidos indicadores lastAnalysis/analysisError |
| #14 | SQL "no such column from_entity_id" | Corregido a entity1_id/entity2_id |
| #15-17 | Plantillas/Salud/Arquetipos error | Resuelto al arreglar #14 |
| #18 | Sticky sentences muy sensible | YA TENÍA slider de umbral configurable |
| #19 | Ecos error | Corregido report.total_words → processed_words |
| #20 | Variación sin promedios | YA TENÍA protección división por cero |
| #21 | "gustoso" sensorial | Añadido a exclusiones con variantes |
| #23 | Resumen sin color alertas | YA TENÍA barras coloreadas por severidad |
| #24 | Tab Entidades confuso | Añadido header explicativo vs Story Bible |
| #25 | Navegación primera vez falla | Añadido nextTick + timeout aumentado |
| #26 | Menciones duplicadas | Añadido deduplicateMentions() |
| #22 | **Glosario extracción automática** | **Implementado GlossaryExtractor + endpoint sugerencias** |

### Sesión 2026-02-04: Fixes Detallados

**Issue #5: Relaciones sin datos** ✅

Causa raíz:
- El endpoint `/api/projects/{id}/relationships` buscaba menciones por posición absoluta
- Las posiciones de menciones son absolutas, pero el contexto se extraía del contenido del capítulo (relativo)

Fix aplicado (`api-server/routers/relationships.py`):
1. Crear mapeo `chapter_id` → `chapter_number` usando el ID de BD de menciones
2. Convertir posiciones absolutas a relativas al extraer contexto
3. Añadir fallback y logging para menciones no coincidentes

**Issue #8: Timeline flashback incorrecto** ✅

Causa raíz:
- El algoritmo "high water mark" clasificaba como ANALEPSIS cualquier evento con posición cronológica menor
- No verificaba evidencia narrativa de flashback

Fix aplicado (`src/narrative_assistant/temporal/timeline.py`):
1. Añadido `_has_retrospective_evidence()` - detecta marcadores de memoria/flashback
2. Añadido `_has_prospective_evidence()` - detecta marcadores de anticipación
3. ANALEPSIS solo si: marcadores retrospectivos OR salto >90 días al pasado
4. PROLEPSIS solo si: >1 año con marcador OR >2 años sin marcador

**Issue #22: Glosario extracción automática** ✅

Causa raíz:
- El glosario era 100% manual, sin capacidad de sugerencias automáticas
- Los usuarios esperaban detección de términos candidatos

Fix aplicado:
1. Creado `src/narrative_assistant/analysis/glossary_extractor.py`:
   - `GlossaryExtractor` detecta términos candidatos basándose en:
     - Nombres propios con mayúscula (frecuencia baja)
     - Patrones técnicos (acrónimos, sufijos -ismo, -logía, etc.)
     - Neologismos/nombres de fantasía (sufijos -iel, -wen, -thor, etc.)
     - Entidades del NER con frecuencia significativa
   - Excluye nombres comunes (María, Juan, Madrid, etc.)
   - Excluye términos ya en el glosario

2. Añadidos endpoints en `api-server/routers/content.py`:
   - `GET /api/projects/{id}/glossary/suggestions` - extrae sugerencias
   - `POST /api/projects/{id}/glossary/suggestions/accept` - acepta sugerencia

3. Actualizado `frontend/src/components/workspace/GlossaryTab.vue`:
   - Botón "Sugerir términos" con icono sparkles
   - Panel horizontal con tarjetas de sugerencias
   - Cada tarjeta muestra: término, categoría, frecuencia, confianza, contexto
   - Acciones: Añadir (abre editor) / Ignorar

4. Tests: `tests/unit/test_glossary_extractor.py` (14 tests)

---

## ✅ Todos los Issues Resueltos

**Estado**: 26/26 issues resueltos

---

## ✅ Features Implementadas

### Feature: Detección de Redundancia Semántica ✅

**Estado**: IMPLEMENTADA (2026-02-04)

**Descripción**: Detecta contenido que se repite semánticamente aunque esté escrito con palabras diferentes, usando embeddings y FAISS para búsqueda ANN optimizada.

**Archivos creados**:
- `src/narrative_assistant/analysis/semantic_redundancy.py` - Detector con FAISS/linear fallback
- `tests/unit/test_semantic_redundancy.py` - 30 tests unitarios
- `api-server/routers/prose.py` - Endpoint `/api/projects/{id}/semantic-redundancy`
- `src/narrative_assistant/core/resource_manager.py` - Gestión de recursos del sistema

**Características**:
- **Habilitado por defecto** en configuración
- **Tres modos**: fast (~5s), balanced (~30s), thorough (~5min)
- **Tipos de duplicados**: textual, temático, acción
- **Filtros anti falsos positivos**: diálogos cortos, frases comunes, proximidad
- **Optimizado**: FAISS para O(n log n) o linear fallback O(n²)
- **Integrado con ResourceManager**: control de tareas pesadas concurrentes

**Configuración** (`NLPConfig`):
```python
semantic_redundancy_enabled: bool = True  # Habilitado por defecto
semantic_redundancy_threshold: float = 0.85
semantic_redundancy_mode: str = "balanced"
```

**Variables de entorno**:
- `NA_SEMANTIC_REDUNDANCY_ENABLED=true`
- `NA_SEMANTIC_REDUNDANCY_THRESHOLD=0.85`
- `NA_SEMANTIC_REDUNDANCY_MODE=balanced`

---

## 🚀 Features Futuras (Backlog)

### Feature: Frontend para Redundancia Semántica

**Descripción**: Crear componente Vue para visualizar redundancias detectadas.

**Archivos a crear**:
- `frontend/src/components/workspace/SemanticRedundancyTab.vue`

**Prioridad**: Media (backend completo, falta UI)

---

## 🔧 Logging Mejorado Añadido

Para diagnosticar los issues pendientes, se ha añadido logging detallado en:

1. **Relationships detector**: `detector.py` - logs al detectar/no detectar relaciones
2. **Relationships endpoint**: `main.py` - logs del endpoint con conteos
3. **Timeline**: `timeline.py` - logs de clasificación flashback/prolepsis

**Cómo revisar**:
1. Rebuild en GitHub Actions
2. Instalar nueva versión
3. Analizar un documento de prueba
4. Revisar logs en `~/.narrative_assistant/logs/` o consola del servidor

---

## 📁 Archivo Obsoleto

El archivo `INVESTIGATION_REPORT_26_ISSUES.md` puede ser eliminado ya que:
- 23/26 issues están resueltos
- Los 3 pendientes están documentados aquí
- Este archivo es más conciso y actionable

