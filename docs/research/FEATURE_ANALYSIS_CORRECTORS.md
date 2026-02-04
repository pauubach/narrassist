# Análisis de Features: Correctores vs Escritores

> **Contexto**: El software es una herramienta para **correctores editoriales** que debe **señalar problemas sin corregir**. La corrección final la hace el profesional.
> **Fecha**: Enero 2026

---

## Panel de Expertos Consultados

| Rol | Perspectiva |
|-----|-------------|
| **Editor profesional** | Flujo de trabajo real, necesidades del día a día |
| **Lingüista/Corrector** | Precisión en detección de errores, falsos positivos |
| **Experto NLP/IA** | Viabilidad técnica, calidad de modelos |
| **Arquitecto software** | Complejidad, mantenibilidad, escalabilidad |
| **Frontend dev** | UX/UI, presentación de información |
| **Backend dev** | Performance, concurrencia, integración |

---

## 1. Features ESENCIALES para Correctores

Estas son **imprescindibles** para el público objetivo inicial (correctores profesionales).

### 1.1 Detección de Inconsistencias (Core)

| Feature | Fuente | Prioridad | Complejidad | Consenso |
|---------|--------|-----------|-------------|----------|
| **Character Consistency** | Novelium | ⭐⭐⭐ CRÍTICA | Alta | ✅ Unánime |
| **Timeline Conflicts** | Novelium | ⭐⭐⭐ CRÍTICA | Alta | ✅ Unánime |
| **Deceased Character Alert** | Novelium | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |
| **Character Location Tracking** | Novelium | ⭐⭐ Alta | Media | ✅ Unánime |
| **Knowledge Tracking** | Novelium | ⭐⭐ Alta | Alta | ✅ Unánime |

**Opiniones:**

> **Editor**: "Esto es exactamente lo que paso horas haciendo manualmente. Fichas de personajes, líneas temporales en Excel... Si el software lo detecta automáticamente, me ahorra días por manuscrito."

> **Lingüista**: "Los atributos físicos son críticos. He visto publicar novelas donde el protagonista tiene ojos azules en el cap. 1 y verdes en el cap. 20. Es vergonzoso."

> **Experto NLP**: "Ya tenemos entity tracking y attributes. El sistema de correferencias multi-método nos da la base. Timeline es más complejo pero viable con markers temporales + LLM."

> **Arquitecto**: "El knowledge tracking es el más complejo. Requiere un knowledge graph real. Sugiero dejarlo para fase 2-3."

---

### 1.2 Análisis Estilístico (Señalar, NO corregir)

| Feature | Fuente | Prioridad | Complejidad | Consenso |
|---------|--------|-----------|-------------|----------|
| **Sticky Sentences** | ProWritingAid | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |
| **Echo/Repetitions** | ProWritingAid | ⭐⭐⭐ CRÍTICA | Baja | ✅ Unánime |
| **Pacing Analysis** | ProWritingAid | ⭐⭐ Alta | Media | ✅ Unánime |
| **Sentence Variation Graph** | ProWritingAid | ⭐⭐ Alta | Baja | ✅ Unánime |
| **POV Consistency Checker** | yWriter | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |

**Opiniones:**

> **Editor**: "Las repeticiones léxicas son lo que más marco en rojo. 'Dijo' cinco veces en una página. 'Sin embargo' cada dos párrafos. Que el software las resalte sería fantástico."

> **Lingüista**: "Sticky sentences es brillante. Oraciones sobrecargadas de conectores vacíos ('que', 'de', 'el'). Muy común en traducciones y en escritores noveles."

> **Experto NLP**: "Sticky sentences es puro NLP: tokenización + POS tagging + lista de glue words. Tenemos spaCy listo. Podemos implementarlo esta semana."

> **Frontend**: "Necesito visualizar las oraciones problemáticas IN CONTEXT. Un sidebar con la oración, por qué es sticky (% de glue words), y poder saltar al texto."

---

### 1.3 Visualización y Navegación

| Feature | Fuente | Prioridad | Complejidad | Consenso |
|---------|--------|-----------|-------------|----------|
| **Scene Tagging** | Final Draft | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |
| **Breakdown Reports** | Final Draft | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |
| **Show Markup Mode** | WordPerfect | ⭐⭐ Alta | Baja | ✅ Unánime |
| **Smart Navigation** | Final Draft | ⭐⭐ Alta | Baja | ✅ Unánime |

**Opiniones:**

> **Editor**: "Necesito ver DÓNDE está cada personaje, CUÁNDO aparece, QUÉ sabe. Un informe de desglose por capítulo me ahorra horas de lectura lineal."

> **Frontend**: "Scene tagging ya lo podemos inferir parcialmente. Tenemos chapter_id, podemos añadir scene_id. La UI de etiquetado manual es sencilla."

> **Arquitecto**: "Show Markup Mode es transparencia: mostrar qué voter/método generó cada alerta. Ya tenemos esa info en extra_data. Solo falta exponerla en la UI."

---

### 1.4 Índices de Claridad (Español Nativo)

| Feature | Fuente | Prioridad | Complejidad | Consenso |
|---------|--------|-----------|-------------|----------|
| **Clarity Index Español** | StyleWriter | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |
| **Bog Score** | StyleWriter | ⭐⭐⭐ CRÍTICA | Media | ✅ Unánime |

**Opiniones:**

> **Lingüista**: "Flesch-Kincaid está calibrado para inglés. Necesitamos métricas propias: longitud media de oración en español, uso de subordinadas, pasivas perifrásticas..."

> **Experto NLP**: "Tenemos sentence segmentation con spaCy. Calcular métricas es trivial. El reto es calibrar umbrales para español literario (no académico)."

---

## 2. Features SECUNDARIAS para Correctores

Útiles pero no esenciales para v1. Pueden ir en roadmap fase 2-3.

| Feature | Fuente | Prioridad | Razón para postergar |
|---------|--------|-----------|---------------------|
| **Dialogue Tags Analysis** | ProWritingAid | ⭐⭐ Media | Menos crítico que repeticiones generales |
| **Sensory Report** | ProWritingAid | ⭐⭐ Media | Requiere clasificación semántica compleja |
| **Benchmarking por género** | AutoCrit | ⭐⭐ Media | Necesita corpus de referencia (IP issues) |
| **Story Completeness** | Dramatica | ⭐ Baja | Muy subjetivo, difícil de automatizar |
| **Character Archetype Detector** | Dramatica | ⭐ Baja | Análisis literario avanzado |

**Opiniones:**

> **Editor**: "El benchmarking sería genial para dar feedback al autor, pero como corrector, mi trabajo es detectar errores, no comparar con otros libros."

> **Experto NLP**: "Sensory report requiere clasificar descripciones por sentido (vista, oído, tacto...). Viable con LLM pero costoso en tokens."

---

## 3. Features para ESCRITORES (Fase Futura)

Estas features serían valiosas si expandimos el producto a **escritores como apoyo creativo**. NO implementar ahora, pero mantener en el backlog estratégico.

### 3.1 Generación/Sugerencia de Contenido

| Feature | Fuente | Prioridad Escritor | Por qué NO para correctores |
|---------|--------|--------------------|-----------------------------|
| **Continue Writing** | Sudowrite | ⭐⭐⭐ | Corrector no escribe, señala |
| **Add Sensory Detail** | Sudowrite | ⭐⭐⭐ | Corrector no expande texto |
| **Expand/Condense** | ProWritingAid | ⭐⭐⭐ | Corrector no reescribe |
| **Change POV** | ProWritingAid | ⭐⭐ | Transformación, no corrección |
| **Brainstorm Ideas** | Sudowrite | ⭐⭐⭐ | Creación, no revisión |

> **Editor**: "Esto NO es para mí. Como corrector, si el texto necesita reescribirse, lo marco y el autor lo hace. No soy ghostwriter."

> **Arquitecto**: "Si añadimos generación, cambia completamente el modelo de uso. Requiere prompts, configuración de estilo, feedback loop... Es otro producto."

### 3.2 Organización y Planificación

| Feature | Fuente | Prioridad Escritor | Por qué NO para correctores |
|---------|--------|--------------------|-----------------------------|
| **Story Bible** | Sudowrite | ⭐⭐⭐ | Escritor crea worldbuilding |
| **Plantillas de Estructura** | Plottr | ⭐⭐⭐ | Escritor planifica historia |
| **Development Stages** | StoryWeaver | ⭐⭐ | Proceso creativo, no revisión |
| **Scene Cards View** | yWriter | ⭐⭐ | Reorganización = autoría |

> **Editor**: "El Story Bible sería útil para LEER, no para crear. Si el autor me lo da, genial. Pero yo no lo creo."

### 3.3 Exportación Avanzada

| Feature | Fuente | Prioridad Escritor | Por qué NO para correctores |
|---------|--------|--------------------|-----------------------------|
| **Export EPUB** | Atticus | ⭐⭐⭐ | Publicación = autor |
| **Export PDF print-ready** | Atticus | ⭐⭐⭐ | Maquetación = diseñador |
| **Export Scrivener** | Atticus | ⭐⭐ | Interoperabilidad = autor |

> **Editor**: "Yo exporto un documento corregido (DOCX con control de cambios). El autor decide qué hacer después."

---

## 4. Matriz de Decisión Final

### Para Correctores (v1.0)

| Categoría | Features Incluir | Features Postergar |
|-----------|-----------------|-------------------|
| **Inconsistencias** | Character Consistency, Timeline, Deceased Alert, Location | Knowledge Tracking completo |
| **Estilo** | Sticky Sentences, Repetitions, Pacing, POV Check | Sensory Report, Dialogue Tags |
| **Visualización** | Scene Tags, Breakdown Reports, Markup Mode | - |
| **Métricas** | Clarity Index, Bog Score, Sentence Variation | Benchmarking por género |

### Para Escritores (v2.0+, backlog)

| Categoría | Features Backlog |
|-----------|-----------------|
| **Generación** | Continue, Expand, Sensory, POV Change |
| **Planificación** | Story Bible, Templates, Scene Cards |
| **Exportación** | EPUB, PDF, Scrivener |

---

## 5. Roadmap Revisado

### Fase 1: Quick Wins (Próximas semanas)
1. ✅ **Sticky Sentences** - Ya en desarrollo
2. **Echo Report** - Repeticiones léxicas en proximidad
3. **Sentence Variation Graph** - Visualización de longitudes
4. **Clarity Index Español** - Métricas nativas

### Fase 2: Diferenciadores (1-2 meses)
1. **Timeline automático** - Extraer y visualizar eventos
2. **Character Consistency Alerts** - Cambios de atributos físicos
3. **POV Consistency Checker** - Cambios de punto de vista
4. **Breakdown Reports** - Desglose por personaje/ubicación

### Fase 3: Avanzado (2-4 meses)
1. **Deceased Character Alert** - Personajes muertos que reaparecen
2. **Character Location Tracking** - Ubicación física inconsistente
3. **Scene Tagging** + Smart Navigation
4. **Bog Score** + Pacing Analysis mejorado

### Fase Futura: Escritores (TBD)
- Story Bible viewer (solo lectura)
- Generación con LLM (si hay demanda)
- Exportación multi-formato

---

## 6. Consideraciones Técnicas

### Ya implementado (base para nuevas features):
- Entity extraction + correferencias multi-método
- Attribute tracking con evidencias
- Chapter segmentation
- LLM local (Ollama)
- Sistema de alertas centralizado

### Requiere implementación:
- Glue words dictionary para español
- Calibración de umbrales para métricas españolas
- UI para visualización de métricas estilísticas
- Timeline extraction mejorado

---

*Documento preparado para roadmap Narrative Assistant v1.0*
