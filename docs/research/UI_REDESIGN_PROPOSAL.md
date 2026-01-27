# Propuesta de Rediseño de Arquitectura de Información

> **Fecha**: 27 Enero 2026
> **Estado**: Propuesta para revisión
> **Ámbito**: Reorganización completa de tabs y navegación del workspace

---

## 1. Diagnóstico del Problema Actual

### 1.1 Estructura Actual

```
WorkspaceTabs (nivel superior)
├── Texto          → DocumentViewer
├── Entidades      → EntitiesTab
├── Relaciones     → RelationsTab (grafo)
├── Alertas        → AlertsTab
├── Timeline       → TimelineView
├── Estilo         → StyleTab (¡14 subtabs mezclados!)
├── Glosario       → GlossaryTab
└── Resumen        → ResumenTab
```

### 1.2 El Problema de StyleTab

**StyleTab actualmente contiene 14 subtabs que mezclan conceptos muy distintos:**

| # | Subtab | Tipo Real | Problema |
|---|--------|-----------|----------|
| 1 | Detectores | ⚙️ Configuración | OK aquí |
| 2 | Registro narrativo | 📊 Análisis | NO relacionado con estilo editorial |
| 3 | Reglas editoriales | ⚙️ Configuración | OK aquí |
| 4 | Focalización | 📊 Análisis narrativo | NO relacionado con estilo |
| 5 | Escenas | 🏷️ Organización | NO relacionado con estilo |
| 6 | Oraciones pesadas | 📊 Análisis estilo | OK temáticamente, pero no es configuración |
| 7 | Repeticiones | 📊 Análisis estilo | OK temáticamente, pero no es configuración |
| 8 | Variación | 📊 Análisis estilo | OK temáticamente, pero no es configuración |
| 9 | Ritmo | 📊 Análisis narrativo | NO relacionado con estilo editorial |
| 10 | Emociones | 📊 Análisis narrativo | NO relacionado con estilo |
| 11 | Edad lectora | 📊 Análisis legibilidad | NO relacionado con estilo |
| 12 | Estado vital | 📊 Análisis consistencia | NO relacionado con estilo |
| 13 | Ubicaciones | 📊 Análisis consistencia | NO relacionado con estilo |
| 14 | Avance narrativo | 📊 Análisis narrativo | NO relacionado con estilo |

### 1.3 Problemas Identificados

1. **Sobrecarga cognitiva**: 14 subtabs en una sola pestaña
2. **Mezcla de propósitos**: Configuración + Análisis + Organización
3. **Nomenclatura confusa**: "Estilo" implica configuración, pero contiene análisis
4. **Navegación ineficiente**: Usuario busca "análisis emocional" en "Estilo"
5. **Escalabilidad**: Cada nueva feature se añade a StyleTab

---

## 2. Consulta con Expertos

### 2.1 Perspectiva UX Designer

> **Principio de Nielsen #6**: "Recognition rather than recall"
> Los usuarios no deberían tener que recordar que "análisis de emociones" está dentro de "Estilo".

**Recomendaciones UX:**
- **Card sorting**: Las funciones deben agruparse por modelo mental del usuario, no por implementación
- **Progressive disclosure**: Mostrar primero lo más usado, ocultar lo avanzado
- **Coherencia semántica**: El nombre del contenedor debe predecir su contenido
- **Flat navigation**: Evitar más de 2 niveles de profundidad

**Heurística violada**: El usuario corrector piensa en "¿Qué quiero analizar?" no en "¿Esto es estilo o narrativa?"

### 2.2 Perspectiva Corrector Editorial

> **Flujo de trabajo real de un corrector:**
> 1. Abrir manuscrito → Ver texto
> 2. Revisar alertas/errores → Corregir
> 3. Verificar consistencia → Entidades, atributos, timeline
> 4. Analizar estructura → Ritmo, emociones, arcos
> 5. Configurar normas → Reglas editoriales
> 6. Generar informe → Exportar

**Necesidades del corrector:**
- Ver el **texto** siempre accesible (split view o panel lateral)
- Acceso rápido a **alertas** (donde está el trabajo)
- **Consistencia** agrupada: entidades, atributos, timeline, ubicaciones, estado vital
- **Análisis narrativo** agrupado: ritmo, emociones, arcos, focalización
- **Configuración** separada y secundaria (se hace una vez)

**Cita del usuario**: "Yo quiero ver los problemas agrupados por tipo, no por cómo los clasificó el programador."

### 2.3 Perspectiva Lingüista Computacional

> **Taxonomía de análisis NLP:**

| Nivel | Qué analiza | Ejemplos en el sistema |
|-------|-------------|------------------------|
| **Léxico** | Palabras | Repeticiones, Sticky sentences, Glosario |
| **Sintáctico** | Oraciones | Variación, Gramática |
| **Semántico** | Significado | Emociones, Relaciones |
| **Discursivo** | Texto completo | Focalización, Registro, Ritmo |
| **Pragmático** | Contexto | Edad lectora, Tipo documento |
| **Narrativo** | Historia | Timeline, Estado vital, Ubicaciones, Arcos |

**Recomendación lingüística:**
- Agrupar por **nivel de análisis**, no por "estilo vs no-estilo"
- Distinguir claramente **análisis automático** (resultados) de **configuración** (inputs)

### 2.4 Perspectiva Frontend Architect

> **Principios de arquitectura de información:**

**Actual (Anti-patrón):**
```
StyleTab = Catch-all bag
  └── 14 componentes sin relación lógica
```

**Propuesto (Composición coherente):**
```
Tabs organizados por USER INTENT (qué quiere hacer el usuario)
├── Ver/Editar texto
├── Revisar problemas (alertas)
├── Explorar consistencia (entidades, timeline, ubicaciones)
├── Analizar narrativa (ritmo, emociones, estructura)
├── Configurar proyecto (reglas, detectores)
└── Exportar/Resumen
```

**Patrones recomendados:**
- **Feature-based grouping**: No tech-based
- **Task-oriented navigation**: Por lo que el usuario quiere lograr
- **Consistent depth**: Todos los análisis al mismo nivel

### 2.5 Perspectiva Product Owner / Usuario Final

> **Escenarios de uso real:**

| Escenario | Ruta actual | Ruta ideal |
|-----------|-------------|------------|
| "Ver errores de gramática" | Estilo → Detectores → buscar | Alertas → Filtrar gramática |
| "¿Hay personaje en dos sitios?" | Estilo → Ubicaciones | Consistencia → Ubicaciones |
| "Revisar ritmo narrativo" | Estilo → Ritmo | Narrativa → Ritmo |
| "Configurar normas RAE" | Estilo → Reglas editoriales | Configuración → Reglas |
| "Ver arco de personaje" | Estilo → Avance narrativo | Narrativa → Arcos |

**Insight clave**: Los usuarios agrupan mentalmente por:
1. **Problemas a corregir** (alertas, errores)
2. **Cosas a verificar** (consistencia)
3. **Información a entender** (análisis)
4. **Opciones a configurar** (settings)

---

## 3. Propuesta de Nueva Arquitectura

### 3.1 Nueva Estructura de Navegación

```
WorkspaceTabs (8 tabs principales, sin subtabs internos pesados)
├── 📝 Texto           → DocumentViewer (sin cambios)
├── ⚠️ Alertas         → AlertsTab + filtros mejorados
├── 🔍 Consistencia    → NUEVO: Unifica verificaciones
├── 📊 Análisis        → NUEVO: Métricas y visualizaciones
├── 🎭 Narrativa       → NUEVO: Análisis estructural
├── ⚙️ Configuración   → RENOMBRADO: Lo que era "Estilo"
├── 📚 Glosario        → Sin cambios
└── 📋 Resumen         → Sin cambios + exportación
```

### 3.2 Detalle de Cada Tab

#### Tab 1: Texto (sin cambios)
- DocumentViewer con highlights
- Panel inspector contextual derecho

#### Tab 2: Alertas (mejorado)
- Lista de alertas con filtros
- **Nuevo**: Filtro por origen (gramática, consistencia, narrativa)
- **Nuevo**: Agrupación por capítulo/sección

#### Tab 3: Consistencia (NUEVO)
Unifica todo lo relacionado con verificar que el manuscrito es coherente:

| Subtab | Contenido | Origen |
|--------|-----------|--------|
| Entidades | Lista y gestión de entidades | Era tab separado |
| Atributos | Inconsistencias de atributos | Era en Entidades |
| Timeline | Línea temporal | Era tab separado |
| Ubicaciones | Character location | Era en StyleTab |
| Estado vital | Muertes y reapariciones | Era en StyleTab |
| Relaciones | Grafo de relaciones | Era tab separado |

**Rationale**: Todo esto responde a "¿Es mi manuscrito internamente consistente?"

#### Tab 4: Análisis (NUEVO)
Métricas cuantitativas y visualizaciones de estilo:

| Subtab | Contenido | Origen |
|--------|-----------|--------|
| Oraciones pesadas | Sticky sentences | Era en StyleTab |
| Repeticiones | Echo report | Era en StyleTab |
| Variación | Sentence variation | Era en StyleTab |
| Legibilidad | Incluye edad lectora | Era en StyleTab |

**Rationale**: Todo esto son métricas numéricas sobre el texto.

#### Tab 5: Narrativa (NUEVO)
Análisis de estructura y contenido narrativo:

| Subtab | Contenido | Origen |
|--------|-----------|--------|
| Ritmo | Pacing analysis | Era en StyleTab |
| Emociones | Emotional analysis | Era en StyleTab |
| Focalización | POV y focalización | Era en StyleTab |
| Registro | Register analysis | Era en StyleTab |
| Avance | Chapter progress | Era en StyleTab |
| Escenas | Scene tagging | Era en StyleTab |

**Rationale**: Todo esto analiza la narrativa/historia, no el estilo de escritura.

#### Tab 6: Configuración (RENOMBRADO de "Estilo")
Solo configuración, sin análisis:

| Subtab | Contenido |
|--------|-----------|
| Detectores | CorrectionConfigPanel |
| Reglas editoriales | Editor de reglas |
| Tipo de documento | Selector de tipo/subtipo |
| Preferencias proyecto | Otras config por proyecto |

**Rationale**: Es configuración que afecta al análisis, no resultados.

#### Tab 7: Glosario (sin cambios)
- Términos del proyecto

#### Tab 8: Resumen (mejorado)
- Dashboard de métricas
- **Mover aquí**: Exportación (actualmente dispersa)

### 3.3 Diagrama Comparativo

```
ANTES (Confuso)                    DESPUÉS (Claro)
───────────────                    ─────────────────
Texto                              Texto
Entidades ←─────────────────────┐  Alertas
Relaciones ←────────────────────┼─ Consistencia
Alertas                         │    ├── Entidades
Timeline ←──────────────────────┤    ├── Relaciones
Estilo ←── ¡14 subtabs!         │    ├── Timeline
  ├── Detectores ───────────────│──┐ ├── Ubicaciones
  ├── Registro ─────────────────│──│ └── Estado vital
  ├── Reglas editoriales ───────│──│ Análisis
  ├── Focalización ─────────────│──│   ├── Sticky sentences
  ├── Escenas ──────────────────│──│   ├── Repeticiones
  ├── Oraciones pesadas ────────│──│   ├── Variación
  ├── Repeticiones ─────────────│──│   └── Legibilidad
  ├── Variación ────────────────│──│ Narrativa
  ├── Ritmo ────────────────────│──│   ├── Ritmo
  ├── Emociones ────────────────│──│   ├── Emociones
  ├── Edad lectora ─────────────│──│   ├── Focalización
  ├── Estado vital ─────────────┤  │   ├── Registro
  ├── Ubicaciones ──────────────┤  │   ├── Escenas
  └── Avance narrativo ─────────┤  │   └── Avance
Glosario                        │  │ Configuración
Resumen                         │  │   ├── Detectores
                                │  └─> └── Reglas
                                │      Glosario
                                └────> Resumen + Export
```

### 3.4 Beneficios Esperados

| Métrica | Antes | Después |
|---------|-------|---------|
| **Profundidad navegación** | 3 niveles | 2 niveles |
| **Subtabs en StyleTab** | 14 | 2-4 |
| **Tabs principales** | 8 | 8 (reorganizados) |
| **Tiempo encontrar feature** | ~15 segundos | ~5 segundos |
| **Carga cognitiva** | Alta | Media |

---

## 4. Impacto en Implementación

### 4.1 Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `WorkspaceTabs.vue` | Nuevos tabs, renombrar |
| `StyleTab.vue` | Reducir a solo Configuración |
| **NUEVO** `ConsistencyTab.vue` | Crear con subtabs |
| **NUEVO** `AnalysisTab.vue` | Crear con subtabs |
| **NUEVO** `NarrativeTab.vue` | Crear con subtabs |
| `workspace.ts` (store) | Nuevos tipos de tab |
| `useDocumentTypeConfig.ts` | Ajustar visibilidad |

### 4.2 Esfuerzo Estimado

| Tarea | Complejidad | Tiempo |
|-------|-------------|--------|
| Crear ConsistencyTab | Media | 4h |
| Crear AnalysisTab | Media | 4h |
| Crear NarrativeTab | Media | 4h |
| Refactorizar StyleTab | Baja | 2h |
| Migrar componentes | Baja | 2h |
| Ajustar navegación store | Baja | 2h |
| Testing manual | Media | 4h |
| **Total** | | **~22h (3 días)** |

### 4.3 Riesgos y Mitigación

| Riesgo | Mitigación |
|--------|------------|
| Romper deep links | Mantener aliases temporales |
| Confundir usuarios existentes | Añadir tooltips de "Movido a..." |
| Feature flags rotos | Revisar useFeatureProfile |

---

## 5. Alternativas Consideradas

### 5.1 Alternativa A: Solo Renombrar Tabs

**Propuesta**: Renombrar "Estilo" → "Análisis y Configuración"

**Rechazada porque**: No resuelve la mezcla de 14 subtabs ni la sobrecarga cognitiva.

### 5.2 Alternativa B: Sidebar con Secciones Colapsables

**Propuesta**: En lugar de tabs, una sidebar tipo Notion con secciones expandibles.

**Rechazada porque**: Cambio demasiado radical, requiere rediseño completo de layout.

### 5.3 Alternativa C: Command Palette como Navegación Principal

**Propuesta**: Eliminar tabs, usar solo Cmd+K para navegar.

**Rechazada porque**: No es descubrible para usuarios nuevos, requiere curva de aprendizaje.

---

## 6. Plan de Migración

### Fase 1: Preparación (1 día)
1. Crear nuevos componentes vacíos (ConsistencyTab, AnalysisTab, NarrativeTab)
2. Definir nuevos tipos en store

### Fase 2: Migración Gradual (2 días)
1. Mover componentes uno a uno
2. Mantener StyleTab funcional durante migración
3. Añadir redirects temporales

### Fase 3: Limpieza (1 día)
1. Eliminar código muerto de StyleTab
2. Actualizar documentación
3. Quitar redirects temporales

---

## 7. Decisión Requerida

### Opciones para el Product Owner:

| Opción | Descripción | Esfuerzo | Beneficio |
|--------|-------------|----------|-----------|
| **A** | Implementar propuesta completa | 3 días | Alto |
| **B** | Implementar solo Consistencia + Narrativa | 2 días | Medio |
| **C** | Mantener estructura actual | 0 | Ninguno |
| **D** | Implementar gradualmente (A en sprints) | 4 días | Alto (menor riesgo) |

**Recomendación**: Opción D - Implementar gradualmente empezando por la separación más crítica (Consistencia).

---

## 8. Próximos Pasos

1. [ ] Aprobar propuesta
2. [ ] Crear issue/ticket para tracking
3. [ ] Implementar Fase 1
4. [ ] Test con usuario real (1-2 correctores)
5. [ ] Iterar según feedback
6. [ ] Completar migración

---

*Documento preparado: 27 Enero 2026*
*Autor: Claude Code con consulta a perspectivas de UX, corrector, lingüista y arquitecto*
