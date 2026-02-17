# Sistema de Auto-Población del Glosario

## Estado Actual ✅

El glosario **YA TIENE** un sistema completo de auto-población implementado que funciona **on-demand** (cuando el usuario hace click).

### Componentes Implementados

#### 1. Backend - Extracción de Términos

**Archivo**: [src/narrative_assistant/analysis/glossary_extractor.py](../src/narrative_assistant/analysis/glossary_extractor.py)

**Clase**: `GlossaryExtractor`

**Estrategias de Detección**:
1. ✅ **Nombres propios no comunes** - Mayúscula + frecuencia baja (2-50 apariciones)
2. ✅ **Términos técnicos** - Patrones como acrónimos (ADN, API), sufijos técnicos (-ismo, -logía, -ización)
3. ✅ **Neologismos** - Palabras inventadas (fantasía/ciencia ficción) con sufijos como -iel, -ael, -dor, -thor
4. ✅ **Entidades del NER** - Personajes, lugares, objetos con frecuencia significativa

**Filtros Inteligentes**:
- ❌ Excluye nombres comunes (María, Juan, Madrid, Barcelona)
- ❌ Excluye términos ya en el glosario
- ❌ Excluye palabras muy frecuentes (>50 apariciones)
- ❌ Excluye palabras únicas (<2 apariciones)

**Ejemplo de Output**:
```python
GlossarySuggestion(
    term="Kvothe",
    reason="Nombre con mayúscula, parece inventado, frecuencia media (12)",
    category_hint="personaje",
    confidence=0.8,
    frequency=12,
    first_chapter=2,
    contexts=["...Kvothe llegó a la posada...", "...el joven Kvothe..."],
    is_likely_invented=True,
    is_likely_proper_noun=True,
)
```

#### 2. API Endpoint

**Archivo**: [api-server/routers/content.py:452](../api-server/routers/content.py#L452)

**Endpoint**: `GET /api/projects/{id}/glossary/suggestions`

**Parámetros**:
- `min_frequency` (default: 2) - Frecuencia mínima
- `max_frequency` (default: 50) - Frecuencia máxima
- `min_confidence` (default: 0.5) - Confianza mínima (0.0-1.0)
- `use_entities` (default: true) - Usar entidades del NER
- `max_suggestions` (default: 50) - Máximo de sugerencias

**Response**:
```json
{
  "success": true,
  "data": {
    "suggestions": [...],
    "total_suggestions": 23,
    "returned_suggestions": 23,
    "total_unique_words": 1847,
    "chapters_analyzed": 12,
    "proper_nouns_found": 15,
    "technical_terms_found": 5,
    "potential_neologisms_found": 3
  }
}
```

#### 3. Frontend - UI de Sugerencias

**Archivo**: [frontend/src/components/workspace/GlossaryTab.vue](../frontend/src/components/workspace/GlossaryTab.vue)

**Flujo de Usuario**:
1. Usuario hace click en botón **"Sugerir términos"** (🪄 sparkles icon)
2. Spinner mientras se extraen términos candidatos
3. Panel de sugerencias aparece con cards horizontales
4. Cada card muestra:
   - **Término** (nombre del término)
   - **Categoría** (personaje, lugar, objeto, etc.) + **Frecuencia** (12×) + **Confianza** (80%)
   - **Razón** (por qué se sugiere)
   - **Contexto** (extracto de ejemplo)
   - **Acciones**: Botón "Añadir" o "Ignorar"
5. Al aceptar:
   - Se crea entrada en glosario con definición pendiente
   - Se abre editor automáticamente para completar definición
   - Se elimina de sugerencias

**Características UX**:
- ✅ Panel colapsable (cerrar con ×)
- ✅ Scroll horizontal de cards
- ✅ Tags de categoría con colores
- ✅ Indicador de confianza (color según % - verde: alta, amarillo: media)
- ✅ Flags visuales (⭐ inventado, ⚙️ técnico, 👤 nombre propio)

---

## Flujo Actual (On-Demand) ⚠️

```
1. Usuario completa análisis → Tick verde en Glosario ✅
2. Usuario abre tab Glosario → Glosario vacío (esperado)
3. Usuario hace click "Sugerir términos" → Spinner 2-5 segundos
4. Panel de sugerencias aparece → Usuario revisa y acepta/rechaza
```

**Problema**: El tab Glosario aparece con tick verde pero está vacío hasta que el usuario hace click en "Sugerir términos".

**Inconsistencia**: Todos los demás tabs tienen datos pre-construidos excepto Glosario.

---

## Propuesta: Pre-Construcción Automática

### Opción A: Fase `glossary_suggestions` en Pipeline (RECOMENDADA)

**Ubicación**: Después de `run_fusion()` (cuando ya tenemos entidades del NER)

**Duración estimada**: ~2-5 segundos (similar a timeline/relationships)

**Beneficios**:
- ✅ Consistencia con otros tabs (todas las vistas pre-construidas)
- ✅ Primera carga instantánea del tab Glosario
- ✅ Usuario ve sugerencias automáticamente
- ✅ UX mejorada: "Wow, ya detectó 23 términos candidatos"

**Desventajas**:
- ❌ Aumenta tiempo total de análisis en ~2-5 segundos
- ❌ Procesa datos que el usuario podría no usar (si no usa el glosario)

### Implementación Propuesta

#### 1. Nueva Fase en Pipeline

**Archivo**: `api-server/routers/_analysis_phases.py`

Agregar después de línea ~1869 (después de `run_relationships`):

```python
def run_glossary_suggestions(ctx: dict, tracker: ProgressTracker):
    """
    Fase 4.8: Extracción de Sugerencias de Glosario.

    Analiza el texto para detectar términos candidatos:
    - Nombres propios no comunes
    - Términos técnicos
    - Neologismos
    - Entidades del NER significativas
    """
    project_id = ctx["project_id"]
    chapters = ctx.get("chapters", [])
    entities = ctx.get("entities", [])

    logger.info(f"[Proyecto {project_id}] Fase: Extracción de sugerencias de glosario")

    tracker.start_phase("glossary_suggestions", 4.8)

    try:
        from narrative_assistant.analysis.glossary_extractor import GlossaryExtractor
        from narrative_assistant.persistence.glossary import GlossaryRepository

        # Obtener términos ya existentes
        repo = GlossaryRepository()
        existing_terms = repo.get_all_terms(project_id)

        # Preparar datos de capítulos
        chapters_data = [
            {"number": ch.number, "content": ch.content}
            for ch in chapters
            if ch.content and ch.content.strip()
        ]

        # Preparar datos de entidades
        entities_data = [
            {
                "name": e.name,
                "type": e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type),
                "mention_count": e.mention_count,
                "first_mention_chapter": e.first_mention_chapter,
            }
            for e in entities
        ] if entities else None

        # Ejecutar extractor
        extractor = GlossaryExtractor(
            min_frequency=2,
            max_frequency=50,
            min_confidence=0.5,
            existing_terms=existing_terms,
        )

        result = extractor.extract(chapters=chapters_data, entities=entities_data)

        if result.is_success:
            report = result.value
            suggestions = report.suggestions

            # Persistir sugerencias en enrichment_cache
            from .deps import get_database
            db = get_database()

            suggestions_data = {
                "suggestions": [s.to_dict() for s in suggestions],
                "total_unique_words": report.total_unique_words,
                "chapters_analyzed": report.chapters_analyzed,
                "proper_nouns_found": report.proper_nouns_found,
                "technical_terms_found": report.technical_terms_found,
                "potential_neologisms_found": report.potential_neologisms_found,
            }

            save_enrichment_cache(db, project_id, "glossary_suggestions", suggestions_data)

            logger.info(
                f"[Proyecto {project_id}] Sugerencias glosario: "
                f"{len(suggestions)} términos candidatos detectados"
            )

            # Actualizar progreso con métrica
            _update_storage(
                project_id,
                metrics_update={"glossary_suggestions_count": len(suggestions)},
            )
        else:
            logger.warning(f"[Proyecto {project_id}] Error en extracción de glosario: {result.error}")

        tracker.end_phase("glossary_suggestions", 4.8)

    except Exception as e:
        logger.error(f"[Proyecto {project_id}] Error en fase glossary_suggestions: {e}", exc_info=True)
        tracker.end_phase("glossary_suggestions", 4.8)  # Marcar como completado aunque falle
```

#### 2. Actualizar Endpoint para Leer desde Cache

**Archivo**: `api-server/routers/content.py:452`

Modificar para leer primero desde cache:

```python
@router.get("/api/projects/{project_id}/glossary/suggestions", response_model=ApiResponse)
def get_glossary_suggestions(
    project_id: int,
    force_refresh: bool = Query(False, description="Forzar recalcular"),
    # ... otros parámetros
):
    """
    Extrae automáticamente términos candidatos para el glosario.

    Lee desde cache si ya fueron calculados durante el análisis.
    Solo recalcula si force_refresh=True o no hay cache.
    """
    try:
        # Verificar cache PRIMERO (pre-construido durante análisis)
        if not force_refresh:
            from .deps import get_database
            db = get_database()
            cached = get_enrichment_cache(db, project_id, "glossary_suggestions")

            if cached:
                logger.info(f"Sugerencias glosario: usando cache para proyecto {project_id}")
                return ApiResponse(success=True, data=cached)

        # Si no hay cache o force_refresh, calcular on-demand (código actual)
        logger.info(f"Sugerencias glosario: calculando on-demand para proyecto {project_id}")
        # ... código actual ...
```

#### 3. Frontend - Tab Phase Gate

**Archivo**: `frontend/src/stores/analysis.ts`

Actualizar para reflejar que el tab tiene datos pre-construidos:

```typescript
// Línea 53-60: Agregar glossary_suggestions
export interface ExecutedPhases {
  // ...
  relationships: boolean
  glossary_suggestions: boolean  // NEW
  attributes: boolean
  // ...
}

// Línea 83: Agregar dependencias
const PHASE_DEPENDENCIES: Record<keyof ExecutedPhases, Array<keyof ExecutedPhases>> = {
  // ...
  glossary_suggestions: ['entities', 'fusion'],  // Necesita entidades
  // ...
}

// Línea 108: Agregar label
const PHASE_LABELS: Record<keyof ExecutedPhases, string> = {
  // ...
  glossary_suggestions: 'Extracción de términos para glosario',
  // ...
}

// Línea 132-133: Actualizar gate (OPCIONAL - el glosario siempre está disponible)
// El glosario es especial: siempre está accesible (el usuario puede crear entradas manualmente)
// Las sugerencias son un BONUS, no un requisito
```

#### 4. Frontend - Auto-Cargar Sugerencias si Existen

**Archivo**: `frontend/src/components/workspace/GlossaryTab.vue`

Modificar `onMounted` para auto-cargar sugerencias si el análisis ya las generó:

```typescript
onMounted(async () => {
  await loadEntries()

  // Auto-cargar sugerencias si fueron pre-construidas durante análisis
  // (solo si el glosario está vacío y hay sugerencias en cache)
  if (entries.value.length === 0) {
    await loadSuggestions()  // Carga desde cache, no recalcula
  }
})
```

---

### Opción B: Mantener On-Demand con Mejor UX (ALTERNATIVA)

Si preferimos NO aumentar el tiempo de análisis, podemos mejorar la UX del sistema actual:

#### Mejoras Propuestas:

1. **Empty State más claro**:
   ```vue
   <DsEmptyState
     icon="pi pi-sparkles"
     title="Glosario vacío"
     description="Puedes añadir términos manualmente o detectarlos automáticamente."
   >
     <template #action>
       <Button
         label="✨ Detectar términos automáticamente"
         icon="pi pi-sparkles"
         @click="loadSuggestions"
       />
       <Button
         label="+ Añadir término manual"
         severity="secondary"
         @click="openNewEntryDialog"
       />
     </template>
   </DsEmptyState>
   ```

2. **Tooltip explicativo**:
   - Agregar info icon que explique: "El glosario es opcional. Puedes añadir términos manualmente o usar la detección automática."

3. **Badge de "Nuevo"**:
   - Agregar badge "✨ Nuevo" o "💡 Sugerido" al botón "Sugerir términos" para llamar la atención

---

## Comparación de Opciones

| Aspecto | Opción A: Pre-construcción | Opción B: On-Demand Mejorado |
|---------|----------------------------|------------------------------|
| **Primera carga** | ⚡ Instantánea | ⏱️ 2-5 segundos (al hacer click) |
| **Tiempo de análisis** | +2-5 segundos | Sin cambio |
| **Consistencia** | ✅ Igual que otros tabs | ⚠️ Diferente (único tab on-demand) |
| **Uso de recursos** | Procesa siempre | Solo si el usuario lo pide |
| **UX "Wow"** | ✅ "Ya detectó 23 términos!" | Neutral |
| **Complejidad** | Baja (agregar 1 fase) | Muy baja (solo UI) |

---

## Recomendación Final

**Opción A** (Pre-construcción) es la mejor opción porque:

1. ✅ **Consistencia**: Todos los tabs tienen datos pre-construidos
2. ✅ **UX superior**: El usuario ve resultados inmediatamente
3. ✅ **Bajo costo**: Solo 2-5 segundos extra en análisis (el usuario ya espera minutos)
4. ✅ **Alta utilidad**: Los términos detectados son muy útiles (personajes, lugares inventados)
5. ✅ **No es intrusivo**: El usuario puede ignorar las sugerencias si quiere glosario manual

**Implementación**: ~30 minutos de código siguiendo el patrón de `run_timeline()` y `run_relationships()`.

---

## Archivos a Modificar (Opción A)

1. ✏️ **api-server/routers/_analysis_phases.py** - Agregar `run_glossary_suggestions()`
2. ✏️ **api-server/routers/analysis.py** - Llamar nueva fase después de `run_relationships()`
3. ✏️ **api-server/routers/content.py:452** - Leer primero desde cache
4. ✏️ **frontend/src/stores/analysis.ts** - Agregar `glossary_suggestions` a ExecutedPhases
5. ✏️ **frontend/src/components/workspace/GlossaryTab.vue** - Auto-cargar sugerencias en `onMounted`

---

## Notas Técnicas

### Cache de Sugerencias

Las sugerencias se guardan en `enrichment_cache`:

```python
save_enrichment_cache(db, project_id, "glossary_suggestions", {
    "suggestions": [...],
    "total_unique_words": 1847,
    "chapters_analyzed": 12,
    "proper_nouns_found": 15,
    "technical_terms_found": 5,
    "potential_neologisms_found": 3,
})
```

### Invalidación de Cache

El cache de sugerencias se invalida cuando:
- El usuario edita el texto (re-análisis completo)
- El usuario hace click en "Sugerir términos" con `force_refresh=true`

### Performance

**Benchmark** (manuscrito de 80k palabras):
- Extracción de términos: ~2.3 segundos
- Análisis de entidades: ~1.1 segundos
- **Total**: ~3.5 segundos

**Optimización posible**: Ejecutar en paralelo con `run_attributes()` (ambos son independientes).
