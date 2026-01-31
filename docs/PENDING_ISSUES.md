# 📋 Issues Pendientes de Resolución

**Última actualización**: 31 de enero de 2025  
**Versión**: 0.4.5+

---

## ✅ Issues Resueltos (26 → 23 resueltos)

Los siguientes issues fueron resueltos en sesiones de debugging:

| Issue | Descripción | Fix Aplicado |
|-------|-------------|--------------|
| #1 | "algo extraño" como concepto | Filtrado de frases genéricas en NER |
| #2-3 | María Sánchez como concepto + atributos cruzados | Fusión CHARACTER↔CONCEPT mejorada |
| #4 | Versión incorrecta 0.3.34 | Eliminado fallback hardcodeado |
| #6 | Corrección de "y" (LanguageTool) | Añadido disabled_rules para WORD_REPEAT |
| #7 | Menús nativos no funcionan | Refactorizado useNativeMenu.ts con @tauri-apps/api/event |
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

---

## ❓ Issues Pendientes (3 restantes)

### Issue #5: Relaciones sin datos

**Síntoma**: El tab de Relaciones no muestra datos aunque hay entidades.

**Hipótesis**:
1. El pipeline no ejecutó la fase de detección de relaciones
2. Las entidades no cumplen requisitos mínimos (2+ PERSON/ORG/LOC)
3. Error silencioso en el detector de relaciones

**Diagnóstico necesario**:
- Verificar logs del pipeline al analizar documento
- Revisar si la tabla `relationships` tiene datos
- Comprobar endpoint `/api/projects/{id}/relationships`

**Archivos clave**:
- `src/narrative_assistant/relationships/detector.py`
- `src/narrative_assistant/relationships/repository.py`
- `frontend/src/components/workspace/RelationsTab.vue`

**Severidad**: ALTA  
**Logging añadido**: Sí, en detector.py y main.py

---

### Issue #8: Timeline asigna flashback incorrectamente

**Síntoma**: Eventos narrativos marcados como flashback cuando no lo son.

**Problema identificado**:
La clasificación flashback/prolepsis se basa en:
1. Marcadores léxicos ("recordó", "hacía tiempo") → flashback
2. Offset temporal negativo → flashback

**Pero no considera**:
- Contexto narrativo (¿es un recuerdo o la trama principal?)
- Anidamiento (flashback dentro de flashback)
- Verbos en pasado que no son flashback

**Archivos clave**:
- `src/narrative_assistant/temporal/timeline.py`
- `src/narrative_assistant/temporal/markers.py`

**Severidad**: MEDIA  
**Requiere**: Mejora algorítmica del clasificador temporal

---

### Issue #22: Glosario extracción automática

**Tipo**: Feature Request (no es bug)

**Síntoma**: El glosario está vacío, usuario esperaba extracción automática.

**Diseño actual**: El glosario es 100% manual por diseño.

**Feature propuesta**:
- Extracción automática de términos técnicos no comunes
- Detección de neologismos y nombres inventados
- Sugerencias basadas en frecuencia baja + mayúsculas

**Archivos clave**:
- `src/narrative_assistant/persistence/glossary.py`
- `frontend/src/components/workspace/GlossaryTab.vue`

**Severidad**: BAJA (mejora)  
**Prioridad**: Backlog

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

