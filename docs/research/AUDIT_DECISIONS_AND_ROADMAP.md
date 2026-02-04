# Decisiones de Auditoría y Hoja de Ruta de Correcciones

> **Fecha**: 29 Enero 2026 (Sesión 5)
> **Contexto**: Auditoría post-implementación de Sprints B-D
> **Metodología**: 4 auditores independientes + 3 paneles de expertos (9 perfiles)

---

## ⚡ Estado de Implementación (Verificado 2026-02-04)

**Progreso global: 100% completado** ✅

| Sprint/Solución | Estado | Notas |
|-----------------|--------|-------|
| **Sprint E: Hotfixes Críticos** | ✅ 5/5 | ErrorSeverity.MEDIUM era falsa alarma (ya usa RECOVERABLE) |
| **Sprint F: Calidad Frontend** | ✅ 6/6 | `response.ok` añadido en EchoReportTab.vue |
| **Sprint G: Lingüística Española** | ✅ 3/3 | - |
| **S-1: Fail-Fast** | ✅ Completo | PhasePreconditionError ya implementado |
| **S-2: morpho_utils.py** | ✅ Completo | - |
| **S-3: scope_resolver.py** | ✅ Completo | - |

### Correcciones adicionales (2026-02-04)

| Fix | Archivo | Descripción |
|-----|---------|-------------|
| Menús Tauri | `useNativeMenu.ts` | Race condition corregido con `tauriReadyPromise` |
| Panel responsive | `EntityInspector.vue`, `ProjectDetailView.vue` | `min-width: 0` para flexbox |
| mention_count | `fusion.py`, `repository.py` | Reconciliación + `cursor.rowcount` |
| Analepsis falsas | `timeline.py` | Algoritmo high-water mark |
| Chat timeout | `useChat.ts` | 30s → 120s |

---

## Paneles de Expertos Consultados

| Panel | Expertos | Foco |
|-------|----------|------|
| **A: Lingüística + Editorial** | Dra. Carmen Vidal (lingüista computacional), Miguel Á. Durán (corrector editorial 20+ años), Prof. Elena Sánchez (narratóloga) | Corrección conceptual NLP, teoría narrativa, precisión lingüística |
| **B: Backend + Seguridad** | Javier Ruiz (arquitecto Python/FastAPI), Ana Torres (AppSec), David Chen (QA/testing) | Crashes, API, seguridad, performance, testing |
| **C: Frontend + Producto** | Laura Martín (Product Owner), Tomás García (UX), Sofía Blanco (FE engineer Vue 3) | UX, interfaz, priorización de producto |

### Estadísticas del debate

- **Hallazgos evaluados**: 38 (algunos evaluados por múltiples paneles)
- **Rechazados**: 0
- **Aceptados sin reservas**: 28
- **Aceptados con matices**: 10
- **Consenso unánime en los 3 paneles**

---

## Tabla Maestra de Decisiones

### Leyenda de estados

| Estado | Significado |
|--------|-------------|
| ✅ HACER | Consenso unánime, se implementa |
| ⚠️ HACER CON MATICES | Se implementa pero con ajustes respecto al hallazgo original |
| 📋 BACKLOG | Válido pero no prioritario ahora |

---

## BLOQUE 1: CRASHES Y BUGS CRÍTICOS (Implementar inmediatamente)

Estos bugs impiden el funcionamiento correcto del software. Ningún experto los cuestionó.

### 1.1 — `ErrorSeverity.MEDIUM` no existe

| Campo | Valor |
|-------|-------|
| **ID** | C1 |
| **Archivo** | `sentence_energy.py:464` |
| **Decisión** | ✅ HACER |
| **Qué** | Cambiar `ErrorSeverity.MEDIUM` → `ErrorSeverity.RECOVERABLE` |
| **Por qué** | El enum solo tiene RECOVERABLE/DEGRADED/FATAL. El error handler crashea al intentar crear el error, perdiendo la excepción original. |
| **Consenso** | Unánime (Arquitecto: "La ironía es máxima: el código diseñado para manejar errores es el que crashea") |
| **Esfuerzo** | 1 línea |

### 1.2 — `ArchetypeId.GUARDIAN` no existe

| Campo | Valor |
|-------|-------|
| **ID** | C2 |
| **Archivo** | `character_archetypes.py:236` |
| **Decisión** | ✅ HACER |
| **Qué** | Reemplazar `ArchetypeId.GUARDIAN: 10 if hasattr(...)` → `ArchetypeId.THRESHOLD_GUARDIAN: 10` |
| **Por qué** | El módulo no puede importarse. La feature de arquetipos está completamente rota. El `try/except ImportError` en la API degrada graciosamente pero el feature nunca funciona. |
| **Consenso** | Unánime. QA: "Un smoke test de `import character_archetypes` lo habría detectado en 1 segundo" |
| **Esfuerzo** | 1 línea |

### 1.3 — Variable scoping bug en `_generate_recommendations()`

| Campo | Valor |
|-------|-------|
| **ID** | C3 |
| **Archivo** | `narrative_health.py:948` |
| **Decisión** | ✅ HACER |
| **Qué** | Cambiar `dim.suggestion` → `d.suggestion` |
| **Por qué** | Dos modos de fallo: (1) Crash con `NameError` si no hay dimensiones CRITICAL (manuscrito bien escrito). (2) Filtrado silencioso e incorrecto de warnings basado en la última dimensión crítica. |
| **Consenso** | Unánime. Lingüista: "Es un bug claro de copiar-pegar entre los dos bloques de filtraje" |
| **Esfuerzo** | 1 línea |

### 1.4 — XSS en `EchoReportTab.vue` vía `v-html`

| Campo | Valor |
|-------|-------|
| **ID** | C6 |
| **Archivo** | `EchoReportTab.vue:157, 305-309` |
| **Decisión** | ✅ HACER |
| **Qué** | HTML-escapar el texto ANTES de aplicar el reemplazo `<mark>` en `highlightWord()`. También escapar metacaracteres regex en `word`. |
| **Por qué** | En contexto Tauri, XSS puede escalar a RCE (Remote Code Execution) porque el webview tiene acceso al IPC bridge de Tauri. Vector: manuscrito .txt con `<script>` embebido. |
| **Consenso** | Seguridad: "Stored XSS (CWE-79). En Tauri, esto es potencialmente RCE." Arquitecto y QA aceptan. |
| **Esfuerzo** | ~10 líneas |

---

## BLOQUE 2: LINGÜÍSTICA ESPAÑOLA — ERRORES GRAVES (Sprint prioritario)

Los 3 lingüistas/correctores coinciden: estas son las carencias más graves del detector de energía para español. Afectan TODA oración analizada.

### 2.1 — Pasivas reflejas no detectadas

| Campo | Valor |
|-------|-------|
| **ID** | L8 |
| **Archivo** | `sentence_energy.py` |
| **Decisión** | ✅ HACER |
| **Qué** | Implementar detección de pasiva refleja: patrón "se + verbo en 3ª persona". Incluir lista de excepciones idiomáticas ("se trata de", "se dice que"). |
| **Por qué** | La pasiva refleja es la construcción pasiva DOMINANTE en español escrito (RAE, Nueva Gramática §41.6). No detectarla equivale a ignorar la mayoría de las pasivas reales. |
| **Consenso** | Lingüista y Corrector: ACEPTO. Narratóloga: MATIZO (muchas pasivas reflejas son idiomáticas y naturales, necesitan excepciones). |
| **Esfuerzo** | ~40 líneas + lista de excepciones |

### 2.2 — Falsos positivos con `estar + participio`

| Campo | Valor |
|-------|-------|
| **ID** | L9 |
| **Archivo** | `sentence_energy.py` (PASSIVE_AUXILIARIES) |
| **Decisión** | ✅ HACER |
| **Qué** | Eliminar TODAS las formas de `estar` de `PASSIVE_AUXILIARIES`. Solo `ser` constituye pasiva de acción en español. |
| **Por qué** | "Estaba cansada", "estaba sentada" son construcciones estativas, NO pasivas. La RAE las clasifica como atributivas. Marcarlas como pasivas es gramaticalmente incorrecto. |
| **Consenso** | Unánime. Corrector: "Si le digo a un autor que 'María estaba agotada' es voz pasiva, pierdo toda credibilidad profesional." |
| **Esfuerzo** | ~5 líneas (eliminar entradas del set) |

### 2.3 — Tiempos compuestos penalizados por auxiliar `haber`

| Campo | Valor |
|-------|-------|
| **ID** | CA9 |
| **Archivo** | `sentence_energy.py` (WEAK_VERBS + lógica de scoring) |
| **Decisión** | ✅ HACER |
| **Qué** | Detectar patrón "haber + participio". Evaluar la energía del participio (verbo principal), no del auxiliar. |
| **Por qué** | "Habían luchado ferozmente" tiene como núcleo semántico "luchado" (máxima energía). Penalizar "habían" es como penalizar una conjugación. Hace la herramienta inutilizable para novela histórica y memorias. |
| **Consenso** | Unánime. Narratóloga: "La métrica debería evaluar el participio, no el auxiliar gramatical" |
| **Esfuerzo** | ~25 líneas (detección de patrón) |

### 2.4 — "ir" siempre clasificado como débil

| Campo | Valor |
|-------|-------|
| **ID** | L10 |
| **Archivo** | `sentence_energy.py` (WEAK_VERBS) |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Heurística contextual: si "ir/fue/va" va seguido de preposición "a" + sustantivo/lugar, es verbo de movimiento (no débil). Idealmente, usar POS-tag de spaCy. |
| **Por qué** | "María fue a la tienda" es enérgico. Pero "va a hacer" (perífrasis de futuro) sí es débil. Necesita distinción contextual. |
| **Matiz** | No eliminar "ir" del dict, sino añadir lógica de excepción contextual. |
| **Esfuerzo** | ~15 líneas |

### 2.5 — Excepciones de nominalización inconsistentes

| Campo | Valor |
|-------|-------|
| **ID** | L12 |
| **Archivo** | `sentence_energy.py` (NOMINALIZATION_EXCEPTIONS) |
| **Decisión** | ✅ HACER |
| **Qué** | Ampliar la lista con sustantivos lexicalizados: "habitación", "posición", "dirección", "educación", "situación", "información", "comunicación", "organización", "condición", "alimentación", etc. |
| **Por qué** | Si la herramienta marca "habitación" como nominalización, ningún corrector la tomará en serio. |
| **Consenso** | Unánime. Revisar con frecuencia de corpus para determinar qué palabras están completamente lexicalizadas. |
| **Esfuerzo** | ~20 entradas adicionales |

### 2.6 — "hacer" siempre clasificado como débil

| Campo | Valor |
|-------|-------|
| **ID** | L11 |
| **Archivo** | `sentence_energy.py` (WEAK_VERBS) |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Mantener "hacer" como débil por defecto (ES un comodín frecuente), pero añadir lista de colocaciones fuertes ("hacer trizas", "hacer pedazos", "hacer frente", "hacer añicos") donde no se penalice. |
| **Por qué** | El corrector confirma que "hacer" se usa en exceso como comodín. Pero en colocaciones fuertes es enérgico. |
| **Matiz** | Prioridad menor que L10 porque la clasificación por defecto es razonablemente útil. |
| **Esfuerzo** | ~10 líneas + lista de colocaciones |

---

## BLOQUE 3: FRONTEND — CALIDAD Y ROBUSTEZ (Sprint prioritario)

Los 3 paneles coinciden: los 4 componentes nuevos carecen de patrones defensivos que los componentes anteriores sí tienen.

### 3.1 — URLs hardcoded `localhost:8008`

| Campo | Valor |
|-------|-------|
| **ID** | C4 |
| **Archivo** | 6 archivos (4 nuevos + StickySentencesTab + StyleTab) |
| **Decisión** | ✅ HACER |
| **Qué** | Reemplazar por `apiUrl()` de `@/config/api` en los 6 archivos afectados |
| **Por qué** | Rompe el desarrollo con Vite proxy. Bloqueante para despliegue si el puerto cambia. El patrón correcto ya existe en `useFeatureProfile.ts`. |
| **Consenso** | Unánime en los 3 paneles. PO: "Deployment blocker." |
| **Esfuerzo** | ~1 línea por archivo × 6 |

### 3.2 — Sin verificación `response.ok`

| Campo | Valor |
|-------|-------|
| **ID** | C5 |
| **Archivo** | 4 componentes nuevos |
| **Decisión** | ✅ HACER |
| **Qué** | Añadir `if (!response.ok) throw new Error(...)` antes de `.json()`. Manejar `data.success === false` explícitamente. |
| **Por qué** | Si el server devuelve 500 con HTML, `.json()` crashea silenciosamente. El usuario ve estado vacío sin feedback. |
| **Consenso** | Unánime. PO: "Silent failure es la peor experiencia para una herramienta profesional" |
| **Esfuerzo** | ~5 líneas por componente |

### 3.3 — Sin UI de error

| Campo | Valor |
|-------|-------|
| **ID** | H2 |
| **Archivo** | 4 componentes nuevos |
| **Decisión** | ✅ HACER |
| **Qué** | Crear componente compartido `AnalysisErrorState.vue` (icono, mensaje, botón Reintentar). Integrar en los 4 componentes con `v-else-if="errorMsg"`. |
| **Por qué** | Después de un error, el componente muestra "Haz clic en Analizar" — indistinguible de "análisis no ejecutado". El corrector no sabe qué pasó. |
| **Consenso** | UX: "Shared component para consistencia visual." FE: "Extraer en componente reutilizable para los 17+ tabs." |
| **Esfuerzo** | ~50 líneas (componente) + ~5 por integración |

### 3.4 — Sin `watch` de `projectId`

| Campo | Valor |
|-------|-------|
| **ID** | H1 |
| **Archivo** | 4 componentes nuevos |
| **Decisión** | ✅ HACER |
| **Qué** | Añadir `watch(() => props.projectId, () => { report.value = null; analyze() })` |
| **Por qué** | Si el usuario cambia de proyecto sin cambiar de tab, ve datos del manuscrito anterior. PO: "Esto podría dañar la reputación profesional del corrector." |
| **Consenso** | Unánime. El patrón ya existe en `EchoReportTab.vue` (line 232). |
| **Esfuerzo** | 3 líneas por componente |

---

## BLOQUE 4: CONCEPTUAL NARRATOLÓGICO (Sprint de calibración)

### 4.1 — Misatribución "12 de Jung"

| Campo | Valor |
|-------|-------|
| **ID** | CA7 + D7 |
| **Archivo** | `character_archetypes.py:12, 17-20` |
| **Decisión** | ✅ HACER |
| **Qué** | Corregir docstring: "12 de Mark & Pearson (2001) + funciones narrativas de Campbell/Vogler". Añadir referencia bibliográfica. |
| **Por qué** | Jung NO propuso 12 arquetipos. Los 12 son de Mark & Pearson ("The Hero and the Outlaw", 2001). Para un TFM académico, esta misatribución sería señalada por cualquier tribunal. |
| **Consenso** | Unánime. Narratóloga: "Distinguir claramente: Jung (Shadow, Self), Campbell/Vogler (funciones narrativas), Mark & Pearson (arquetipos de personalidad)" |
| **Esfuerzo** | ~10 líneas de docstring |

### 4.2 — Kishotenketsu `ten_twist` ruteado al detector de clímax

| Campo | Valor |
|-------|-------|
| **ID** | C1 |
| **Archivo** | `narrative_templates.py:464-466` |
| **Decisión** | ✅ HACER |
| **Qué** | Crear detector separado `_detect_twist()` que busque: cambio de tono inesperado, nueva información, cambio de perspectiva, sin requerir conflicto. Zona: 0.53-0.77. |
| **Por qué** | El "Ten" NO es un clímax. Kishotenketsu funciona sin conflicto. Usar `_detect_climax()` (basado en conflicto) invalida toda la detección del template. Error conceptual y posicional simultáneo. |
| **Consenso** | Unánime. Narratóloga: "Conceptualmente son opuestos: el clímax resuelve tensión; el Ten introduce perplejidad" |
| **Esfuerzo** | ~30 líneas (nuevo detector) |

### 4.3 — "resolution" incluida en `climax_events`

| Campo | Valor |
|-------|-------|
| **ID** | L2 |
| **Archivo** | `narrative_templates.py:736` |
| **Decisión** | ✅ HACER |
| **Qué** | Eliminar "resolution" de `climax_events` |
| **Por qué** | Resolución es lo opuesto a clímax. Un capítulo de cierre se detectaría como clímax, produciendo falsos positivos. |
| **Consenso** | Unánime. |
| **Esfuerzo** | 1 línea |

### 4.4 — Arcos estáticos penalizados

| Campo | Valor |
|-------|-------|
| **ID** | CA5 |
| **Archivo** | `narrative_health.py` |
| **Decisión** | ✅ HACER |
| **Qué** | Reconocer "flat arc" (K.M. Weiland) como tipo válido. Reescribir mensaje: "Arco estático detectado. Esto es válido en 'flat arcs' donde el protagonista no cambia pero transforma su entorno." |
| **Por qué** | Atticus Finch, Sherlock Holmes, James Bond son estáticos pero extraordinariamente efectivos. Decir que "resta impacto emocional" es prescriptivo y factualmente incorrecto. |
| **Consenso** | Unánime. Narratóloga cita a Weiland ("Creating Character Arcs") como referencia académica. |
| **Esfuerzo** | ~10 líneas |

### 4.5 — Tono prescriptivo en notas de elenco y recomendaciones

| Campo | Valor |
|-------|-------|
| **ID** | D4 |
| **Archivo** | `character_archetypes.py:663-677`, textos de backend en general |
| **Decisión** | ✅ HACER |
| **Qué** | Reescribir todos los textos prescriptivos en tono diagnóstico. Convención: "Se detectó / No se detectó", evitar imperativos ("deberías", "necesitas"), evitar universales ("todo relato necesita..."). |
| **Por qué** | La herramienta dice ser diagnóstica pero múltiples mensajes son prescriptivos. Los correctores profesionales lo perciben como patronizing. |
| **Consenso** | Unánime en los 3 paneles. PO: "La herramienta es un instrumento diagnóstico — una radiografía, no un doctor." |
| **Esfuerzo** | ~30 minutos revisando textos |

### 4.6 — Sin adaptación por tipo de documento en Narrative Health

| Campo | Valor |
|-------|-------|
| **ID** | D3 |
| **Archivo** | `narrative_health.py` + `models.py` (FeatureProfile) |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Approach híbrido: (a) Desactivar vía FeatureProfile para tipos claramente no narrativos (cocina, manual, referencia). (b) Mostrar banner contextual para tipos borderline (memorias, ensayo): "Este análisis está calibrado para ficción narrativa." |
| **Por qué** | Un libro de cocina con 0/100 en "protagonista" desacredita la herramienta entera. El docstring promete adaptación por tipo, pero no se implementa. |
| **Matiz** | No rehacer las 12 dimensiones por tipo (demasiado trabajo). Simplemente gatear con FeatureProfile (ya existe la infraestructura). |
| **Esfuerzo** | ~20 líneas backend + ~10 frontend |

### 4.7 — Protagonista auto-sesgado hacia Hero

| Campo | Valor |
|-------|-------|
| **ID** | L6 |
| **Archivo** | `character_archetypes.py:432-443` |
| **Decisión** | ✅ HACER |
| **Qué** | Reducir bonus Hero por importancia de +25 a +10. Distribuir: Explorer +5, Rebel +5, Lover +5, Ruler +5. |
| **Por qué** | Con +25 automáticos, el protagonista acumula hasta +86 para Hero, haciendo imposible clasificar protagonistas-Rebel (novela social), protagonistas-Lover (romance), o protagonistas-Explorer. |
| **Consenso** | Unánime. Narratóloga: "Hero = protagonista es exactamente la simplificación que la narratología moderna rechaza" |
| **Esfuerzo** | ~10 líneas |

### 4.8 — Normalización borra magnitud de evidencia

| Campo | Valor |
|-------|-------|
| **ID** | CA8 |
| **Archivo** | `character_archetypes.py:383-393` |
| **Decisión** | ✅ HACER |
| **Qué** | Preservar `raw_score` pre-normalización. Calcular confianza basada en score bruto, no normalizado. |
| **Por qué** | Un personaje con 5 puntos de evidencia para Herald se muestra igual (100, confianza 0.9) que uno con 86 puntos para Hero. El usuario no puede distinguir "evidencia sólida" de "adivinación". |
| **Esfuerzo** | ~10 líneas |

---

## BLOQUE 5: API Y ARQUITECTURA (Sprint de calidad)

### 5.1 — `low_threshold` aceptado pero no usado

| Campo | Valor |
|-------|-------|
| **ID** | H3 |
| **Archivo** | `api-server/main.py` (endpoint sentence-energy) |
| **Decisión** | ✅ HACER |
| **Qué** | Hacer que el detector acepte threshold configurable, o eliminar el query parameter |
| **Por qué** | Parámetro fantasma: el OpenAPI lo muestra, el frontend lo envía, pero nada sucede. Corrector que ajusta `low_threshold=80` obtiene exactamente los mismos resultados que con `low_threshold=10`. |
| **Esfuerzo** | ~15 líneas |

### 5.2 — Caché de `analyze_chapter_progress()`

| Campo | Valor |
|-------|-------|
| **ID** | F4 |
| **Archivo** | `api-server/main.py` |
| **Decisión** | ✅ HACER |
| **Qué** | Implementar caché con TTL (cachetools.TTLCache) key=(project_id, mode, llm_model). Invalidar cuando el proyecto cambie. |
| **Por qué** | 3 endpoints llaman a la misma función costosa independientemente. Ver las 3 tabs = 3× el tiempo de espera. |
| **Consenso** | Arquitecto: "El fix de mayor impacto en performance para Sprint C/D" |
| **Esfuerzo** | ~30 líneas |

### 5.3 — Endpoints async bloqueando event loop

| Campo | Valor |
|-------|-------|
| **ID** | H6 |
| **Archivo** | `api-server/main.py` (3 endpoints Sprint C/D) |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Cambiar `async def` → `def` para los 3 endpoints. FastAPI los ejecuta automáticamente en threadpool. |
| **Por qué** | `async def` sin `await` bloquea el event loop. En desktop single-user el impacto es menor, pero si se abren 3 tabs seguidas, la UI se congela. |
| **Matiz** | Seguridad e QA coinciden en impacto limitado para desktop. Aún así, es un anti-patrón clásico de FastAPI fácil de corregir. |
| **Esfuerzo** | 3 líneas (cambiar `async def` → `def`) |

### 5.4 — Validación de proyecto inconsistente

| Campo | Valor |
|-------|-------|
| **ID** | M10 |
| **Archivo** | `api-server/main.py` (3 endpoints Sprint C/D) |
| **Decisión** | ✅ HACER |
| **Qué** | Añadir validación de proyecto (project_manager.get + HTTPException 404) a los 3 endpoints que no la tienen |
| **Por qué** | sentence-energy valida → devuelve 404. Los otros 3 no validan → devuelven 200 con error opaco. Inconsistencia de API. |
| **Esfuerzo** | ~5 líneas por endpoint |

### 5.5 — `str(e)` filtra información interna

| Campo | Valor |
|-------|-------|
| **ID** | M11 |
| **Archivo** | `api-server/main.py` (4 endpoints) |
| **Decisión** | ✅ HACER |
| **Qué** | Si `e` es `NarrativeError`, usar `e.user_message`. Si no, devolver "Error interno del análisis". Log siempre el error completo. |
| **Por qué** | CWE-209 (Information Exposure). `str(e)` puede contener paths del sistema, nombres de módulos, strings de conexión Ollama. |
| **Matiz** | En desktop el riesgo es menor, pero si el usuario comparte screenshots para soporte, expone información del sistema. |
| **Esfuerzo** | ~10 líneas |

### 5.6 — Módulos Sprint C/D no exportados en `__init__.py`

| Campo | Valor |
|-------|-------|
| **ID** | F3 |
| **Archivo** | `src/narrative_assistant/analysis/__init__.py` |
| **Decisión** | 📋 BACKLOG |
| **Qué** | Añadir exports con `try/except ImportError` para consistencia |
| **Por qué** | Funciona sin los exports (los endpoints importan directamente). Es higiene de código. |
| **Esfuerzo** | ~6 líneas |

### 5.7 — Interacciones vacías para arquetipos

| Campo | Valor |
|-------|-------|
| **ID** | F2 |
| **Archivo** | `api-server/main.py:10030` |
| **Decisión** | 📋 BACKLOG |
| **Qué** | Conectar datos de interacciones cuando el endpoint esté disponible |
| **Por qué** | Reconocido como gap incompleto, documentado en el código con un TODO. El módulo degrada graciosamente. |
| **Esfuerzo** | ~15 líneas cuando se implemente el endpoint de interacciones |

### 5.8 — `pacing_data` no pasado a templates

| Campo | Valor |
|-------|-------|
| **ID** | F1 |
| **Archivo** | `api-server/main.py:9875-9878` |
| **Decisión** | 📋 BACKLOG |
| **Qué** | Conectar datos de pacing al template analyzer para mejorar detección de beats |
| **Por qué** | Feature incompleta, no un bug. Los detectores manejan `None` graciosamente. |
| **Esfuerzo** | ~15 líneas |

---

## BLOQUE 6: CALIBRACIÓN DE MÉTRICAS (Sprint futuro)

Estos hallazgos son válidos pero representan mejoras de precisión, no bugs. Se implementan después de los bloques 1-5.

### 6.1 — Setup/Development trivialmente satisfechos

| Campo | Valor |
|-------|-------|
| **ID** | L1 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Subir umbrales: Setup ≥ 2 personajes + evento de contexto. Development ≥ 3 eventos variados. |
| **Prioridad** | ALTA dentro de calibración |

### 6.2 — Templates con pocos beats puntúan más

| Campo | Valor |
|-------|-------|
| **ID** | L3 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Ponderar beats por importancia narrativa dentro de cada template. Excluir beats triviales del cálculo. |
| **Prioridad** | MEDIA |

### 6.3 — Tolerancia Kishotenketsu cubre todo

| Campo | Valor |
|-------|-------|
| **ID** | CA1 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Reducir tolerancia a 0.08 y/o añadir criterios cualitativos por beat |
| **Prioridad** | MEDIA (se enlaza con C1 / detector de twist) |

### 6.4 — Mentor/Refusal limitados a POSSIBLE

| Campo | Valor |
|-------|-------|
| **ID** | CA2 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Mejorar detección (usar relaciones del módulo de relaciones para Mentor). Si no es posible, reducir peso de estos beats. |
| **Prioridad** | MEDIA |

### 6.5 — Stakes medido solo por tono

| Campo | Valor |
|-------|-------|
| **ID** | L4 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Complementar con eventos de alto riesgo (muerte, traición, sacrificio) y escalada de conflicto. Mantener tono como factor parcial. |
| **Prioridad** | MEDIA |

### 6.6 — Pacing = consistencia de longitud

| Campo | Valor |
|-------|-------|
| **ID** | CA3 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Subir max_ratio a 3.5-4.0. Detectar patrones de alternancia intencional. |
| **Prioridad** | MEDIA |

### 6.7 — Coherencia penaliza cambios tonales

| Campo | Valor |
|-------|-------|
| **ID** | CA4 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Subir umbrales: OK ≤ 0.35, WARNING ≤ 0.55, CRITICAL > 0.55. Añadir nota sobre intencionalidad. |
| **Prioridad** | MEDIA |

### 6.8 — Ghost threshold demasiado agresivo

| Campo | Valor |
|-------|-------|
| **ID** | CA6 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Umbral adaptativo: ≤10 personajes → 2%, 11-25 → 1%, >25 → 0.5%. O umbral absoluto mínimo de 2 menciones. |
| **Prioridad** | MEDIA |

### 6.9 — Peso igual para todas las dimensiones

| Campo | Valor |
|-------|-------|
| **ID** | D2 |
| **Decisión** | ⚠️ HACER CON MATICES |
| **Qué** | Dimensiones core (Protagonista, Conflicto, Clímax, Resolución) con peso 1.5x. Complementarias (Cast Balance, Chekhov) con peso 1.0x. |
| **Prioridad** | MEDIA |

### 6.10 — Anti-héroes y elencos corales

| Campo | Valor |
|-------|-------|
| **ID** | L7 |
| **Decisión** | 📋 BACKLOG |
| **Qué** | Detectar patrones híbridos: Hero+Shadow con arco "fall" = "Anti-héroe". Elencos sin protagonista claro = "Coral". |
| **Prioridad** | BAJA (mejora de v2) |

### 6.11 — Métrica energía penaliza estilos literarios

| Campo | Valor |
|-------|-------|
| **ID** | D5 |
| **Decisión** | ⚠️ HACER CON MATICES (2 fases) |
| **Qué** | Fase 1: Banner de calibración en el tab. Fase 2: Slider de umbral configurable (como StickySentencesTab). |
| **Prioridad** | MEDIA |

### 6.12 — Hallazgos de baja prioridad

| ID | Hallazgo | Decisión |
|----|----------|----------|
| CA10 | Interrogativa auto-high structure score | 📋 BACKLOG — Documentar que structure mide forma/variedad. Reducir ligeramente a 75/80. |
| D1 | Fit score ignora orden de beats | 📋 BACKLOG — Bonus por secuencia correcta. Mitigado por tolerancias posicionales. |
| L5 | Goal detection por proxy | 📋 BACKLOG — Documentar limitación. Integrar LLM a futuro. |
| M7 | featureToTabMap desactualizado | 📋 BACKLOG — Completar o eliminar. 10 min. |
| M8 | Iconos duplicados | 📋 BACKLOG — Asignar iconos únicos. 10 min. |
| H4 | total_sentences vs analyzed_sentences | 📋 BACKLOG — Documentar semántica. |
| H10 | Memoria: acumulación de oraciones | 📋 BACKLOG — 40K floats = 320KB, impacto negligible. |
| M12 | TS interface incompleta | ✅ HACER (5 min) |

---

## HALLAZGOS RECHAZADOS

**Ninguno.** Los 38 hallazgos fueron aceptados o aceptados con matices por los 3 paneles. 0 rechazos.

---

## HOJA DE RUTA DE IMPLEMENTACIÓN

### Sprint E: Hotfix Crítico (inmediato, <1 día)

> **Objetivo**: Corregir crashes y vulnerabilidades de seguridad

| # | ID(s) | Tarea | Esfuerzo |
|---|-------|-------|----------|
| E1 | C1 | `ErrorSeverity.MEDIUM` → `RECOVERABLE` | 1 línea |
| E2 | C2 | `ArchetypeId.GUARDIAN` → `THRESHOLD_GUARDIAN`, limpiar dict muerto | 3 líneas |
| E3 | C3 | `dim.suggestion` → `d.suggestion` | 1 línea |
| E4 | C6 | HTML-escape en `highlightWord()` + escape regex | 10 líneas |
| E5 | M12 | Completar TS interface FeatureProfile | 3 líneas |

### Sprint F: Calidad Frontend (1-2 días)

> **Objetivo**: Los 4 componentes al nivel de calidad de los existentes

| # | ID(s) | Tarea | Esfuerzo |
|---|-------|-------|----------|
| F1 | C4 | Migrar 6 archivos a `apiUrl()` | 6 archivos × 1 línea |
| F2 | C5+H2 | `response.ok` check + crear `AnalysisErrorState.vue` + integrar en 4+ tabs | 50 líneas componente + 5/tab |
| F3 | H1 | `watch` de `projectId` en 4 componentes | 3 líneas × 4 |
| F4 | H6 | `async def` → `def` en 3 endpoints | 3 líneas |
| F5 | M10 | Validación de proyecto en 3 endpoints | 5 líneas × 3 |
| F6 | M11 | Sanitizar error responses | 10 líneas |

### Sprint G: Lingüística Española (2-3 días)

> **Objetivo**: Detector de energía preciso para español

| # | ID(s) | Tarea | Esfuerzo |
|---|-------|-------|----------|
| G1 | L9 | Eliminar `estar` de PASSIVE_AUXILIARIES | 5 líneas |
| G2 | L8 | Detectar pasiva refleja ("se + verbo 3ª persona") | 40 líneas |
| G3 | CA9 | Detectar "haber + participio", evaluar participio | 25 líneas |
| G4 | L10 | Heurística contextual para "ir" como movimiento | 15 líneas |
| G5 | L12 | Ampliar NOMINALIZATION_EXCEPTIONS | 20 entradas |
| G6 | L11 | Lista de colocaciones fuertes para "hacer" | 10 líneas |
| G7 | H3 | Hacer threshold configurable en detector + API | 15 líneas |
| G8 | D5.1 | Banner de calibración en SentenceEnergyTab | 5 líneas |

### Sprint H: Calibración Narrativa (2-3 días)

> **Objetivo**: Análisis narrativo preciso y diagnóstico (no prescriptivo)

| # | ID(s) | Tarea | Esfuerzo |
|---|-------|-------|----------|
| H1 | CA7+D7 | Corregir docstring arquetipos + añadir referencia Mark & Pearson | 10 líneas |
| H2 | D4+CA5 | Reescribir textos prescriptivos → diagnósticos. Reconocer flat arcs. | 30 min review |
| H3 | C1(templ) | Crear `_detect_twist()` para Kishotenketsu Ten | 30 líneas |
| H4 | L2 | Eliminar "resolution" de climax_events | 1 línea |
| H5 | L6 | Reducir Hero bonus de +25 a +10, distribuir a otros | 10 líneas |
| H6 | CA8 | Preservar raw_score, recalcular confianza | 10 líneas |
| H7 | D3 | Gatear Narrative Health en FeatureProfile por tipo doc | 20 líneas |
| H8 | L1 | Subir umbrales de setup/development | 10 líneas |
| H9 | D2 | Pesos diferenciados para dimensiones core vs complementarias | 10 líneas |
| H10 | F4 | Caché para `analyze_chapter_progress()` | 30 líneas |

### Sprint I: Calibración Fina + Tests (3-4 días)

> **Objetivo**: Umbrales afinados y cobertura de tests

| # | ID(s) | Tarea | Esfuerzo |
|---|-------|-------|----------|
| I1 | L3+CA1 | Normalizar fit_score por granularidad de template | 20 líneas |
| I2 | CA2 | Mejorar detectores mentor/refusal | 20 líneas |
| I3 | L4 | Complementar stakes con eventos de alto riesgo | 15 líneas |
| I4 | CA3 | Flexibilizar umbrales de pacing | 10 líneas |
| I5 | CA4 | Subir umbrales de coherencia tonal | 5 líneas |
| I6 | CA6 | Umbral adaptativo de ghost characters | 10 líneas |
| I7 | -- | Tests unitarios: sentence_energy (happy + error path) | **ESENCIAL** |
| I8 | -- | Tests unitarios: narrative_health (0 critical dims, warnings independientes) | **ESENCIAL** |
| I9 | -- | Tests unitarios: character_archetypes (import smoke test + scoring) | **ESENCIAL** |
| I10 | -- | Tests unitarios: narrative_templates (beat detection por template) | RECOMENDADO |
| I11 | -- | Tests API: proyecto inexistente → 404 en los 4 endpoints | **ESENCIAL** |
| I12 | -- | Tests API: parámetros query que afectan resultados | **ESENCIAL** |
| I13 | -- | Tests frontend: error states render correctamente | **ESENCIAL** |
| I14 | -- | Tests E2E: XSS con manuscrito .txt con `<script>` | **ESENCIAL** |
| I15 | -- | Tests adversariales: manuscrito vacío, 1 capítulo, HTML embebido | RECOMENDADO |

---

## PRIORIZACIÓN DE TESTS

### ESENCIALES (deben existir antes de release)

| Test | Qué previene | Framework |
|------|-------------|-----------|
| Import smoke test de character_archetypes | C2 — módulo no importable | pytest |
| Error path de sentence_energy.analyze() | C1 — crash en error handler | pytest |
| narrative_health con 0 dimensiones critical | C3 — NameError crash | pytest |
| highlightWord con `<script>` y HTML | C6 — XSS/RCE en Tauri | Vitest |
| Proyecto 999999 → 404 en 4 endpoints | M10 — respuesta inconsistente | pytest |
| low_threshold afecta resultados | H3 — parámetro fantasma | pytest |
| Error state UI visible tras API failure | C5+H2 — silent failure | Playwright |

### RECOMENDADOS

| Test | Qué previene | Framework |
|------|-------------|-----------|
| 12 dimensiones con datos variados | Scores incorrectos en health | pytest |
| Beat detection para cada template (5) | Detección incorrecta de estructura | pytest |
| Archetype scoring con arcos growth/fall/static | Clasificación incorrecta | pytest |
| Cambio de proyecto actualiza datos | H1 — datos stale | Playwright |
| Manuscrito con 0 capítulos | Edge case en todos los analyzers | pytest |
| regex metacaracteres en highlightWord | ReDoS potencial | Vitest |

---

## RESUMEN EJECUTIVO FINAL

| Categoría | Items | Sprints |
|-----------|-------|---------|
| Crashes + Seguridad (Bloque 1) | 5 | E (<1 día) |
| Frontend: calidad (Bloque 3) | 6 | F (1-2 días) |
| Lingüística española (Bloque 2) | 8 | G (2-3 días) |
| Calibración narrativa (Bloque 4+5) | 10 | H (2-3 días) |
| Calibración fina + Tests (Bloque 6) | 15 | I (3-4 días) |
| **TOTAL** | **44 items** | **~10 días** |

### Principios transversales adoptados

1. **Diagnóstico, no prescriptivo**: Todo output debe usar "Se detectó / No se detectó", nunca "Deberías / Necesitas".
2. **Calibrado para español**: Las heurísticas lingüísticas deben seguir la gramática de la RAE, no traducciones de reglas del inglés.
3. **Confianza del corrector**: Si una detección produce un falso positivo obvio ("habitación" = nominalización), la herramienta pierde credibilidad entera.
4. **Rigor académico**: Para el TFM, todas las atribuciones teóricas deben ser correctas y verificables.

---

*Documento generado: 29 Enero 2026*
*Basado en: 4 auditorías + 3 paneles de expertos (9 perfiles)*
