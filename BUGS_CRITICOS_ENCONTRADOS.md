# Bugs Críticos Encontrados - Narrative Assistant

**Fecha**: 2026-01-11
**Contexto**: Peer review exhaustivo del sistema completo

## 🔴 CRÍTICO: Fusión de Entidades No Implementada en Pipeline

**Archivo**: `src/narrative_assistant/pipelines/analysis_pipeline.py`

### Problema
El módulo `src/narrative_assistant/entities/fusion.py` existe y está completamente implementado, pero **NO se usa en el pipeline de análisis**.

### Impacto
- Entidades como "María" y "María Sánchez" se tratan como entidades DIFERENTES
- El consistency checker compara:
  - "maría" con "maría" ✓ (iguales - no inconsistencia)
  - "maría sánchez" con "maría sánchez" ✓ (iguales - no inconsistencia)
- **NUNCA compara** "maría" con "maría sánchez" ✗
- Resultado: **0 inconsistencias detectadas** aunque existan inconsistencias obvias

### Evidencia
```sql
-- Base de datos después del análisis:
María         | eye_color | verdes
María Sánchez | eye_color | azules

-- Deberían ser la misma entidad!
```

### Solución
1. Integrar `FusionService.suggest_merges()` en el pipeline después del paso de NER
2. Aplicar fusión automática con threshold alto (>= 0.85) para casos obvios
3. Guardar sugerencias de fusión con threshold medio (0.7-0.85) para revisión manual

### Código a añadir
En `analysis_pipeline.py`, después del paso 5 (NER):

```python
# STEP 5.5: Fusión automática de entidades similares
if entities:
    from ..entities.fusion import get_fusion_service
    fusion_service = get_fusion_service()

    # Sugerir fusiones
    suggestions_result = fusion_service.suggest_merges(project_id, threshold=0.7)
    if suggestions_result.is_success:
        suggestions = suggestions_result.value

        # Fusión automática para casos muy obvios (threshold >= 0.85)
        for suggestion in suggestions:
            if suggestion.similarity >= 0.85:
                logger.info(f"Auto-merging {suggestion.entity_id1} with {suggestion.entity_id2} (similarity: {suggestion.similarity:.2f})")
                fusion_service.merge_entities(
                    project_id=project_id,
                    source_entity_id=suggestion.entity_id2,
                    target_entity_id=suggestion.entity_id1,
                    reason="Automatic merge (high similarity)",
                    session_id=session_id
                )

        # Recargar entidades después de las fusiones
        entities_result = entity_repo.get_all_by_project(project_id)
        if entities_result.is_success:
            entities = entities_result.value
```

---

## 🟡 IMPORTANTE: NER Detecta Basura como Entidades

**Archivo**: `src/narrative_assistant/pipelines/analysis_pipeline.py` líneas 352-468

### Problema
El NER detecta diálogos y descripciones como entidades:
- "Buenos días"
- "Hola Juan"
- "Imposible"
- "Cabello negro"
- "Algo extraño estaba pasando"

### Filtros Actuales (insuficientes)
```python
# 1. Ignorar texto vacío
# 2. Ignorar títulos de capítulos (regex)
# 3. Ignorar frases largas (> 4 palabras)
# 4. Ignorar líneas que parecen descripciones (ten[ií]a|era|estaba|llevaba|parec[ií]a)
```

### Solución
Añadir filtros adicionales:

```python
# 5. Ignorar expresiones que empiezan con palabras de diálogo comunes
dialogue_starters = r'^(buenos|hola|adiós|gracias|por favor|imposible|claro|vale)'
if re.match(dialogue_starters, canonical, re.IGNORECASE):
    continue

# 6. Ignorar descripciones físicas sin nombre
physical_desc = r'^(cabello|pelo|ojos|cara|manos|piernas)'
if re.match(physical_desc, canonical, re.IGNORECASE):
    continue

# 7. Ignorar frases de narración
narrative_phrases = r'^(algo|todo|nada|alguien|nadie).*(?:estaba|era|pasaba|ocurría)'
if re.match(narrative_phrases, canonical, re.IGNORECASE):
    continue
```

---

## 🟡 Extracción de Atributos Limitada

**Archivo**: `src/narrative_assistant/nlp/attributes.py`

### Problema
Solo extrae 6 atributos de un documento rico con ~15-20 atributos esperados.

### Posibles Causas
1. Patterns regex insuficientes
2. Menciones de entidades incorrectas impiden asociaciones
3. El deduplicador elimina demasiado

### Investigación Necesaria
- Revisar todos los patterns en `_ATTRIBUTE_PATTERNS`
- Añadir patterns para variaciones comunes:
  - "de unos X años"
  - "aproximadamente X años"
  - "con el pelo/cabello X"
  - "lucía X" (lucía cansado, lucía feliz)

### Test de Regresión
Crear test con documento `test_document_rich.txt` que verifique:
- Extrae >= 15 atributos
- Detecta >= 2 inconsistencias
- Crea >= 2 alertas

---

## 🟡 Logging Insuficiente

**Archivos**: Todos los módulos NLP y pipeline

### Problema
- No hay logging detallado del análisis
- Imposible debuggear sin añadir prints manuales
- Los logs actuales no muestran el flujo de datos

### Solución
Añadir logging en puntos clave:

```python
# En cada paso del pipeline
logger.info(f"STEP X: Starting {step_name}")
logger.debug(f"Input: {len(input_data)} items")
# ... procesamiento ...
logger.info(f"STEP X: Completed - Output: {len(output_data)} items")
if errors:
    logger.warning(f"STEP X: {len(errors)} errors occurred")

# En AttributeExtractor
logger.debug(f"Extracted attribute: {entity_name} -> {key}={value} (confidence: {confidence:.2f})")

# En ConsistencyChecker
logger.debug(f"Comparing {attr1.entity_name}.{attr1.key}: '{attr1.value}' vs '{attr2.value}'")
logger.info(f"Inconsistency detected: {inc.entity_name} {inc.attribute_key} ({inc.confidence:.2f})")
```

---

## Estado Actual del Sistema

### ✅ Funciona Correctamente
- Extracción básica de atributos con patterns regex
- Detección de pronombres posesivos y objetos ("Juan la saludó, sorprendido por su cabello" → "su" se refiere a ella)
- Resolución de sujetos elípticos
- Consistency checker con antónimos y embeddings
- Persistencia de atributos en DB
- API REST con FastAPI

### ❌ NO Funciona / Falta
- ❌ **Fusión automática de entidades** (existe pero no se usa)
- ❌ **Filtrado robusto de NER** (detecta basura)
- ❌ **Extracción exhaustiva de atributos** (solo 6 en vez de 15-20)
- ❌ **Logging adecuado para debugging**
- ❌ **Tests automatizados** (no existen)
- ⚠️  **Creación de alertas desde inconsistencias** (código existe pero no se ejecuta porque inconsistencies = 0)

### 🔧 Existe Pero No Se Usa
- `entities/fusion.py` - Sistema completo de fusión NO integrado
- `nlp/coref.py` - Sistema de correferencias ¿se usa?
- Tests en `tests/` - ¿existen? ¿están actualizados?

---

## Plan de Acción Inmediato

### Prioridad 1 - Bloquea Funcionalidad Core
1. ✅ Integrar FusionService en pipeline
2. ✅ Mejorar filtros NER
3. ✅ Añadir logging detallado
4. ✅ Test de integración end-to-end

### Prioridad 2 - Mejoras de Calidad
5. Revisar y ampliar patterns de atributos
6. Crear suite de tests automatizados
7. Documentar flujo completo con diagramas

### Prioridad 3 - Refactoring
8. Eliminar código huérfano
9. Revisar imports y dependencias
10. Optimizar performance (si es necesario)

---

## Próximos Pasos

Esperando reportes completos de agentes especializados:
- 🏗️ **Arquitecto** (Opus) - Revisión estructura completa vs documentación
- 🧠 **Experto NLP** (Sonnet) - Pipeline NLP y flujo de datos
- ⚙️ **Experto Backend** (Sonnet) - FastAPI y persistencia
- 🐍 **Experto Python** (Sonnet) - Calidad de código y patterns

Una vez recibidos los reportes, consolidar y ejecutar todas las correcciones.
