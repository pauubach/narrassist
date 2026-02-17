# Fuentes de Datos por Tab - Auditoría Completa

## Resumen Ejecutivo

| Tab | Datos Pre-construidos? | Fase de Construcción | Estado |
|-----|------------------------|----------------------|--------|
| **Texto** | ✅ SÍ | `structure` | ✅ OK |
| **Entidades** | ✅ SÍ | `fusion` | ✅ OK (con fix) |
| **Relaciones** | ❌ **ON-DEMAND** | N/A | ❌ **PROBLEMA** |
| **Alertas** | ✅ SÍ | `alerts` | ✅ OK |
| **Timeline** | ✅ SÍ (con fix) | `timeline` | ✅ OK (con fix) |
| **Estilo** | ⚠️ MIXTO | Varias fases | ⚠️ REVISAR |
| **Glosario** | ⚠️ MANUAL | Usuario | ⚠️ N/A |
| **Resumen** | ✅ SÍ | `completion` | ✅ OK |

---

## 1. Tab TEXTO ✅

**Endpoint**: `/api/projects/{id}/chapters`

**Fuente de datos**: Tabla `chapters` (BD)

**Construcción**: Fase `structure` (línea 685 en `_analysis_phases.py`)
- Detecta estructura de capítulos
- Persiste en BD
- ✅ **Pre-construido durante análisis**

---

## 2. Tab ENTIDADES ✅

**Endpoint**: `/api/projects/{id}/entities`

**Fuente de datos**: Tabla `entities` + `entity_mentions` (BD)

**Construcción**: Fase `fusion` (línea 1244 en `_analysis_phases.py`)
- NER extrae entidades
- MentionFinder busca menciones adicionales
- Fusión semántica
- ✅ **Pre-construido durante análisis** (con fix aplicado)

**Fix aplicado**: `entities_found` metric se marca DESPUÉS de MentionFinder completar

---

## 3. Tab RELACIONES ❌ **PROBLEMA**

**Endpoint**: `/api/projects/{id}/relationships`

**Fuente de datos**: **Construido on-demand** (routers/relationships.py:13)

**Proceso on-demand** (líneas 117-300):
1. `RelationshipClusteringEngine` - Analiza co-ocurrencias de menciones
2. `CharacterKnowledgeAnalyzer` - Analiza conocimiento inter-personaje
3. Detección de asimetrías
4. ⏱️ **Tiempo de construcción**: ~5-15 segundos para documentos medianos

**Cache**: Sí, mediante `enrichment_cache` (S8a-13), pero no se construye durante análisis inicial

### **Solución Requerida**:
- Agregar fase `relationships` al pipeline
- Ejecutar después de `timeline` (requiere entidades + menciones completas)
- Persistir resultados en BD o cache

---

## 4. Tab ALERTAS ✅

**Endpoint**: `/api/projects/{id}/alerts`

**Fuente de datos**: Tabla `alerts` (BD)

**Construcción**: Fases `alerts_grammar` + `alerts` (líneas 2458, 2827)
- Alertas de gramática (parcial)
- Alertas de consistencia (completo)
- ✅ **Pre-construido durante análisis**

---

## 5. Tab TIMELINE ✅ (con fix)

**Endpoint**: `/api/projects/{id}/timeline`

**Fuente de datos**: Tablas `timeline_events` + `temporal_markers` (BD)

**Construcción**: Fase `timeline` (línea ~1720 en `_analysis_phases.py`)
- Extrae marcadores temporales
- Construye timeline con TimelineBuilder
- Persiste eventos y marcadores
- ✅ **Pre-construido durante análisis** (con fix aplicado)

**Fix aplicado**: Nueva fase `run_timeline()` agregada al pipeline después de `fusion`

---

## 6. Tab ESTILO ⚠️ **MIXTO**

**Múltiples endpoints**:
- `/api/projects/{id}/chapters/{ch}/register-analysis`
- `/api/projects/{id}/chapters/{ch}/emotional-analysis`
- `/api/projects/{id}/style-guide`

**Fuente de datos**: ⚠️ **MIXTO** - Algunos pre-construidos, otros on-demand

### Revisar:
- **Registro**: ¿Se construye durante análisis?
- **Emociones**: ¿On-demand o pre-construido?
- **Guía de estilo**: ¿Pre-construida?

---

## 7. Tab GLOSARIO ⚠️

**Endpoint**: `/api/projects/{id}/glossary`

**Fuente de datos**: Tabla `glossary` (BD)

**Construcción**: ⚠️ **MANUAL por el usuario**
- No se construye automáticamente durante análisis
- El usuario crea entradas manualmente
- ✅ **OK** - Es contenido editorial, no analítico

---

## 8. Tab RESUMEN ✅

**Endpoint**: `/api/projects/{id}` (métricas del proyecto)

**Fuente de datos**: Tabla `projects` + agregaciones

**Construcción**: Fase `completion` (línea 3224)
- Agrega métricas finales
- Actualiza proyecto
- ✅ **Pre-construido durante análisis**

---

## Problemas Identificados

### ❌ **CRÍTICO: Tab Relaciones construye on-demand**

**Impacto**:
- Primera carga lenta (5-15 segundos)
- Usuario ve tick verde pero luego spinner
- UX inconsistente

**Solución**: Agregar fase `relationships` al pipeline

---

## Acciones Requeridas

1. ✅ **Entidades** - Fix aplicado (entities_found timing)
2. ✅ **Timeline** - Fix aplicado (fase timeline agregada)
3. ❌ **Relaciones** - **PENDIENTE**: Agregar fase al pipeline
4. ⚠️ **Estilo** - **REVISAR**: Verificar análisis de registro/emociones

---

## Recomendaciones

### Fase `relationships` (nueva)

**Ubicación**: Después de `timeline`, antes de `attributes`

**Responsabilidad**:
- Ejecutar `RelationshipClusteringEngine`
- Ejecutar `CharacterKnowledgeAnalyzer`
- Persistir en cache de enrichment o tabla dedicada

**Duración estimada**: ~5-10 segundos

**Beneficio**: Primera carga instantánea del tab Relaciones
