# Análisis de Correcciones en Documentos DOCX

## Resumen Ejecutivo

Se han analizado 5 documentos DOCX en la carpeta `test_books/`. De estos, 3 contienen correcciones editoriales significativas realizadas con el sistema de "Control de cambios" (Track Changes) de Microsoft Word.

---

## 1. Tipos de Correcciones Encontradas

### 1.1 Track Changes (Control de Cambios)

| Tipo | Elemento XML | Descripción | Archivos con este tipo |
|------|--------------|-------------|------------------------|
| **Texto eliminado** | `w:del` | Texto marcado para eliminar | FASHION SEWING (5188), Un mundo apasionado (1437), Aplicamos TIC (107) |
| **Texto insertado** | `w:ins` | Texto nuevo añadido | FASHION SEWING (3999), Un mundo apasionado (1154), Aplicamos TIC (109) |
| **Texto movido (origen)** | `w:moveFrom` | Texto movido de esta ubicación | Un mundo apasionado (10), FASHION SEWING (3) |
| **Texto movido (destino)** | `w:moveTo` | Texto movido a esta ubicación | Un mundo apasionado (10), FASHION SEWING (3) |

### 1.2 Cambios de Formato

| Tipo | Elemento XML | Descripción | Archivos con este tipo |
|------|--------------|-------------|------------------------|
| **Formato de carácter** | `w:rPrChange` | Cambios de negrita, cursiva, fuente, tamaño, etc. | Un mundo apasionado (3170), FASHION SEWING (1801), Aplicamos TIC (13) |
| **Formato de párrafo** | `w:pPrChange` | Cambios de alineación, espaciado, sangrías, estilos | FASHION SEWING (1066), Un mundo apasionado (156), Aplicamos TIC (4) |

### 1.3 Comentarios

| Archivo | Nº Comentarios | Revisores |
|---------|----------------|-----------|
| FASHION SEWING | 51 | Anna Ubach Royo, Carme Hernández Bordas |
| Un mundo apasionado | 11 | Nicolau, Carme |
| Aplicamos TIC | 4 | Anna Ubach, Gemma Modrego |
| Diario Polidori | 1 | Carlos |

**Tipos de comentarios observados:**
- Instrucciones de maquetación: "Paginar en primeras", "Pasamos los Agradec al final"
- Sugerencias de estilo: "No se acaba de entendre, no es podria dir: trucos profesionales?"
- Verificaciones pendientes: "Falta y comprobar el ISBN"
- Decisiones estructurales: "Invento una jerarquía nueva aquí"

---

## 2. Estado Actual del Parser

### 2.1 Lo que YA soportamos

| Funcionalidad | Estado | Ubicación en código |
|---------------|--------|---------------------|
| Detección de Track Changes | ✅ Sí | `_has_track_changes()` |
| Aceptar cambios automáticamente | ✅ Sí | `_get_text_with_track_changes()` |
| Excluir texto eliminado (`w:del`) | ✅ Sí | `_extract_text_from_element()` |
| Incluir texto insertado (`w:ins`) | ✅ Sí | `_extract_text_from_element()` |
| Excluir texto tachado | ✅ Sí | Verificación de `w:strike`, `w:dstrike` |
| Detección de comentarios | ✅ Parcial | `_has_comments()` - solo detecta si existen |
| Metadata por párrafo | ✅ Sí | `has_track_changes`, `original_text` |

### 2.2 Lo que NO soportamos

| Funcionalidad | Estado | Impacto |
|---------------|--------|---------|
| Extraer contenido de comentarios | ❌ No | No podemos mostrar las anotaciones del revisor |
| Identificar qué texto tiene cada comentario | ❌ No | No sabemos a qué se refiere cada comentario |
| Mostrar texto eliminado vs insertado | ❌ No | No podemos mostrar la comparación antes/después |
| Identificar autor de cada cambio | ❌ No | No sabemos quién hizo cada corrección |
| Texto movido (`w:moveFrom`/`w:moveTo`) | ❌ No | Se pierde información de reorganización |
| Cambios de formato (`w:rPrChange`) | ❌ No | No detectamos cambios de negrita, cursiva, etc. |
| Cambios de párrafo (`w:pPrChange`) | ❌ No | No detectamos cambios de alineación, estilo |
| Fecha/hora de cada cambio | ❌ No | No tenemos cronología de revisiones |

---

## 3. Relevancia para Narrative Assistant

### 3.1 Correcciones RELEVANTES para nuestra herramienta

| Tipo | Por qué es relevante | Prioridad |
|------|---------------------|-----------|
| **Comentarios** | Contienen observaciones sobre inconsistencias, errores, dudas del revisor | **ALTA** |
| **Texto eliminado/insertado** | Permiten ver qué cambió y por qué (contexto para el análisis) | **MEDIA** |
| **Texto movido** | Indica reorganización estructural del texto | **MEDIA** |

### 3.2 Correcciones MENOS relevantes

| Tipo | Por qué es menos relevante |
|------|---------------------------|
| **Cambios de formato carácter** | Son decisiones de diseño/maquetación, no afectan al contenido narrativo |
| **Cambios de formato párrafo** | Son decisiones de estilo visual, no de contenido |

---

## 4. Plan de Trabajo

### Fase 1: Extracción de Comentarios (Prioridad ALTA)

**Objetivo:** Extraer y mostrar los comentarios del documento con su texto de referencia.

**Tareas:**
1. Parsear `word/comments.xml` para extraer:
   - ID del comentario
   - Autor
   - Fecha
   - Texto del comentario

2. Parsear `word/commentsExtended.xml` para:
   - Relaciones padre-hijo (respuestas)
   - Estado (resuelto/abierto)

3. Identificar rangos de texto comentados:
   - Buscar `w:commentRangeStart` y `w:commentRangeEnd` en `document.xml`
   - Asociar cada comentario con su texto referenciado

4. Exponer en la API:
   ```python
   class Comment:
       id: str
       author: str
       date: datetime
       text: str
       referenced_text: str  # Texto al que se refiere
       start_char: int
       end_char: int
       replies: List[Comment]
       is_resolved: bool
   ```

5. Mostrar en UI:
   - Panel lateral de comentarios
   - Resaltado del texto comentado
   - Filtro por autor/estado

**Estimación:** 2-3 días de desarrollo

---

### Fase 2: Modo "Ver Cambios" (Prioridad MEDIA)

**Objetivo:** Opción para ver el documento con los cambios visibles (no aceptados automáticamente).

**Tareas:**
1. Añadir flag `accept_changes: bool = True` al parser
2. Cuando `accept_changes=False`:
   - Preservar texto de `w:del` marcado como eliminado
   - Preservar texto de `w:ins` marcado como insertado
   - Incluir metadata de autor y fecha por cambio

3. Nuevo modelo de datos:
   ```python
   class TextChange:
       change_type: Literal["insertion", "deletion", "move"]
       text: str
       author: str
       date: datetime
       start_char: int
       end_char: int
       move_id: Optional[str]  # Para vincular moveFrom/moveTo
   ```

4. Mostrar en UI:
   - Texto tachado (rojo) para eliminaciones
   - Texto subrayado (verde) para inserciones
   - Tooltip con autor/fecha
   - Toggle para mostrar/ocultar cambios

**Estimación:** 3-4 días de desarrollo

---

### Fase 3: Detección de Movimientos (Prioridad MEDIA-BAJA)

**Objetivo:** Detectar y visualizar texto que fue movido de lugar.

**Tareas:**
1. Parsear `w:moveFrom` y `w:moveTo` con sus IDs de vinculación
2. Crear visualización de origen → destino
3. Útil para detectar reorganización de capítulos/secciones

**Estimación:** 1-2 días de desarrollo

---

### Fase 4: Historial de Revisores (Prioridad BAJA)

**Objetivo:** Mostrar quién ha revisado el documento y qué cambios hizo cada uno.

**Tareas:**
1. Parsear `word/people.xml` para lista de revisores
2. Agrupar cambios por autor
3. Estadísticas: nº de cambios por revisor, tipos de cambios
4. Timeline de revisiones

**Estimación:** 1-2 días de desarrollo

---

## 5. Recomendaciones

### Implementación Inmediata (MVP+)
- **Fase 1** es la más valiosa: los comentarios contienen información directa del revisor sobre problemas detectados. Esto complementa perfectamente el análisis automático de Narrative Assistant.

### Implementación Futura
- **Fase 2** sería útil para flujos de trabajo donde el corrector quiere ver qué cambios ya se propusieron.
- **Fases 3-4** son "nice to have" pero no críticas para el caso de uso principal.

### No Implementar
- Detección de cambios de formato (`w:rPrChange`, `w:pPrChange`): son decisiones de maquetación que no afectan al análisis narrativo.

---

## 6. Archivos de Referencia

| Archivo | Características | Uso recomendado |
|---------|-----------------|-----------------|
| `FASHION SEWING fionaREVPERMI.docx` | Muchos cambios y comentarios | Testing de parsing masivo |
| `Un mundo apasionado_para Anna Ubach.docx` | Tiene moveFrom/moveTo | Testing de detección de movimientos |
| `Aplicamos las TIC Cast2U1_G.docx` | Cambios moderados, comentarios en catalán/castellano | Testing general |
| `la_regenta_sample.docx` | Sin correcciones | Documento "limpio" de referencia |
| `diario POLIDORI.docx` | 1 comentario mínimo | Caso edge |

---

## Apéndice: Estructura XML de Correcciones en DOCX

### Comentario
```xml
<!-- En word/comments.xml -->
<w:comment w:id="0" w:author="Anna Ubach" w:date="2024-01-15T10:30:00Z">
  <w:p>
    <w:r>
      <w:t>Este párrafo necesita revisión</w:t>
    </w:r>
  </w:p>
</w:comment>

<!-- En word/document.xml - marca el texto referenciado -->
<w:commentRangeStart w:id="0"/>
<w:r><w:t>Texto comentado</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r><w:commentReference w:id="0"/></w:r>
```

### Track Change - Inserción
```xml
<w:ins w:author="Carme" w:date="2024-01-16T14:20:00Z">
  <w:r>
    <w:t>Texto nuevo insertado</w:t>
  </w:r>
</w:ins>
```

### Track Change - Eliminación
```xml
<w:del w:author="Carme" w:date="2024-01-16T14:21:00Z">
  <w:r>
    <w:delText>Texto eliminado</w:delText>
  </w:r>
</w:del>
```

### Track Change - Movimiento
```xml
<!-- Origen -->
<w:moveFrom w:author="Carme" w:id="move1">
  <w:r><w:t>Texto movido</w:t></w:r>
</w:moveFrom>

<!-- Destino -->
<w:moveTo w:author="Carme" w:id="move1">
  <w:r><w:t>Texto movido</w:t></w:r>
</w:moveTo>
```
