# 2. Primer Análisis

Esta guía te llevará desde cero hasta tu primer análisis completo de un manuscrito.

---

## Paso 1: Crear un Proyecto

1. **Abre Narrative Assistant**
2. En la pantalla principal, haz clic en **"Nuevo Proyecto"**
3. Completa el formulario:
   - **Título**: El nombre de tu manuscrito (ej: "El Reino Olvidado - Tomo 1")
   - **Autor**: Tu nombre o seudónimo
   - **Género** *(opcional)*: Novela, Técnico, Jurídico, Memoria, etc.
   - **Descripción** *(opcional)*: Sinopsis breve

4. Haz clic en **"Crear"**

**Resultado**: Se crea un proyecto vacío listo para importar tu documento.

---

## Paso 2: Importar el Documento

### Formatos Soportados

| Formato | Extensión | Recomendación |
|---------|-----------|---------------|
| Word | `.docx` | ⭐ Mejor opción (preserva capítulos, formato) |
| Texto plano | `.txt` | ⭐ Simple y rápido |
| Markdown | `.md` | ⭐ Ideal si escribes en Markdown |
| PDF | `.pdf` | ⚠️ Solo texto (no OCR de imágenes) |
| EPUB | `.epub` | ⚠️ E-books (puede perder formato) |

### Importar desde la Vista de Proyecto

1. **Abre el proyecto** recién creado
2. Haz clic en **"Importar Documento"** (botón de subida)
3. Selecciona el archivo de tu manuscrito
4. **Espera** mientras se procesa (puede tardar 10-30 segundos según tamaño)

**Progreso**:
```
📄 Leyendo archivo...
🔍 Detectando estructura...
📝 Extrayendo capítulos...
✅ Documento cargado (45 capítulos, 120.000 palabras)
```

---

## Paso 3: Ejecutar Análisis Inicial

Una vez importado el documento, puedes iniciar el análisis:

### 3.1 Seleccionar Preset (Opcional)

Antes de analizar, puedes configurar el preset según el tipo de manuscrito:

1. Ve a **Configuración** → **Presets**
2. Selecciona el preset más adecuado:

| Preset | Descripción | Ajustes Clave |
|--------|-------------|---------------|
| **Novela** | Ficción narrativa | Máx. diálogo, personajes, timeline |
| **Técnico** | Libros técnicos | Terminología consistente, acrónimos |
| **Jurídico** | Textos legales | Formal, sin muletillas, precisión |
| **Memoria** | Biografías, memorias | Timeline estricto, coherencia temporal |
| **Infantil** | Literatura infantil | Vocabulario simple, legibilidad |
| **Ensayo** | Ensayos, artículos | Coherencia argumental, registro formal |

> **Tip**: Si no estás seguro, usa **"Novela"** como punto de partida. Siempre puedes ajustar después.

### 3.2 Iniciar Análisis

1. En la vista del proyecto, haz clic en **"Analizar"** (botón principal)
2. Selecciona el **modo de análisis** en el diálogo de confirmación:
   - **Auto** (recomendado): Se ajusta según el tamaño del documento
   - **Express**: Solo gramática y ortografía (rápido, cualquier PC)
   - **Ligero**: Personajes + gramática (sin análisis profundo)
   - **Estándar**: Análisis completo (ideal para <50k palabras)
   - **Profundo**: Todo incluido (requiere más recursos)
3. Haz clic en **"Analizar"**
4. **Espera** mientras se ejecuta el análisis (puede tardar 2-10 minutos)

> **Nota**: En modo **Auto**, si tu manuscrito tiene más de 50.000 palabras, la aplicación
> usará automáticamente el modo Ligero para evitar problemas de rendimiento.
> Puedes forzar un modo superior si tu equipo lo soporta.

**Fases del análisis**:

```
🔄 Fase 1: Análisis NLP (spaCy)
   ├─ Tokenización y POS tagging
   ├─ Extracción de entidades (NER)
   └─ Análisis sintáctico

🔄 Fase 2: Extracción Profunda
   ├─ Atributos de personajes
   ├─ Relaciones entre entidades
   ├─ Eventos narrativos
   └─ Diálogos y hablantes

🔄 Fase 3: Resolución de Correferencias
   ├─ Votación multi-método
   ├─ Fusión de menciones
   └─ Cadenas de correferencia

🔄 Fase 4: Detección de Inconsistencias
   ├─ Atributos contradictorios
   ├─ Timeline (edad, fechas)
   ├─ Relaciones incoherentes
   └─ Eventos contradictorios

🔄 Fase 5: Generación de Alertas
   ├─ Priorización por severidad
   ├─ Cálculo de confianza
   └─ Agrupación por categoría

✅ Análisis completado (3m 45s)
   📊 245 entidades detectadas
   ⚠️ 67 alertas generadas
```

---

## Paso 4: Interpretar Resultados

Una vez completado el análisis, verás el **Dashboard Principal** con 4 áreas:

### 4.1 Vista General (HomeView)

Muestra estadísticas del proyecto:

- **Entidades**: 245 detectadas (180 personajes, 35 lugares, 30 otros)
- **Alertas**: 67 activas (12 críticas, 35 altas, 20 medias)
- **Capítulos**: 45 analizados
- **Palabras**: 120.000

### 4.2 Entidades (EntitiesTab)

Lista todas las entidades detectadas:

- **Personajes**: María González, Juan Pérez, Dr. López
- **Lugares**: Madrid, Hospital Central, Cafetería
- **Organizaciones**: Ministerio de Salud, ONG Esperanza
- **Otros**: objeto, evento, concepto

**Acciones disponibles**:
- Editar nombre, tipo, menciones
- Fusionar duplicados (María = Mari = Sra. González)
- Añadir atributos manualmente
- Ocultar entidades irrelevantes

### 4.3 Alertas (AlertsDashboard)

Listado de inconsistencias detectadas:

#### Ejemplo de Alerta Crítica

```
🔴 ALTA | Inconsistencia de Edad

Capítulo 3, línea 145:
"María tiene 25 años y trabaja como médica desde hace 5 años."

Capítulo 12, línea 892:
"Cuando María cumplió 30, ya llevaba 8 años ejerciendo medicina."

⚠️ Problema: Entre cap. 3 y 12 pasan solo 2 meses de historia,
pero María envejece 5 años.

Confianza: 95%
```

**Acciones**:
- Navegar al texto fuente (click en línea)
- Marcar como resuelta (si ya lo corregiste)
- Rechazar (si es falso positivo)
- Crear regla de supresión (si es patrón recurrente)

### 4.4 Timeline (TimelineView)

Visualización temporal de eventos clave:

```
Día 1  | María conoce a Juan en el hospital
Día 3  | Primera cita
Día 7  | Juan le propone matrimonio
Día 10 | Boda ⚠️ (muy rápido - alerta)
```

---

## Paso 5: Flujo de Trabajo Recomendado

### Iterativo, No Lineal

1. **Analizar** → Ver alertas
2. **Corregir** en tu editor (Word, Scrivener, etc.)
3. **Re-importar** documento actualizado
4. **Re-analizar** → Verificar que alertas desaparecen
5. **Repetir** hasta estar satisfecho

### Priorización

**Orden recomendado**:
1. **Alertas críticas** primero (edad, muerte, contradicciones claras)
2. **Fusionar entidades duplicadas** (mejora precisión de siguientes alertas)
3. **Alertas de calidad** al final (repeticiones, muletillas)

---

## Consejos de Primer Uso

### ✅ DO

- **Revisa manualmente** cada alerta antes de cambiar el manuscrito
- **Fusiona duplicados** cuanto antes (mejora detección)
- **Usa presets** como punto de partida, ajusta después
- **Guarda backups** antes de hacer cambios masivos

### ❌ DON'T

- **No confíes ciegamente** en el 100% de alertas (falsos positivos existen)
- **No uses "Aplicar Todo"** sin revisar (algunas alertas son contextuales)
- **No analices** textos muy cortos (< 5.000 palabras, poco efectivo)
- **No esperes** que detecte todo (es asistencia, no magia)

---

## Problemas Comunes

### "El análisis tarda mucho (> 10 min)"

- **Causa**: Manuscrito muy largo (> 200.000 palabras) o LLM lento
- **Solución**: Desactiva análisis LLM en Settings o mejora hardware

### "Muchas alertas falsas de diálogos"

- **Causa**: Preset demasiado estricto o diálogos sin formato estándar
- **Solución**: Ajusta sensibilidad en Settings → Diálogos

### "No detecta personaje obvio"

- **Causa**: Nombre ambiguo o menciones muy dispersas
- **Solución**: Añade la entidad manualmente en EntitiesTab

---

## Próximos Pasos

- **Gestionar Entidades**: [Capítulo 3](03-entities.md)
- **Trabajar con Alertas**: [Capítulo 4](04-alerts.md)
- **Configuración Avanzada**: [Capítulo 7](07-settings.md)

---

**¿Atascado?** Consulta la [FAQ](../FAQ.md) o abre un [issue en GitHub](https://github.com/pauubach/narrassist/issues).
