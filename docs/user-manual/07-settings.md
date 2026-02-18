# 7. Configuración

Narrative Assistant se adapta a tu flujo de trabajo. Desde **Configuración** puedes ajustar presets por género, sensibilidad del análisis, modelos de IA, preferencias de gramática y gestión de datos.

---

## Acceder a Configuración

Haz clic en el **icono de engranaje** (esquina superior derecha) o ve a **Menú → Configuración**.

---

## Presets de Documento

Los presets configuran automáticamente múltiples ajustes según el **tipo de manuscrito**. Seleccionar un preset es el punto de partida; siempre puedes ajustar valores individuales después.

| Preset | Enfoque Principal | Sensibilidad Diálogos | Sensibilidad Timeline | Gramática |
|--------|-------------------|----------------------|----------------------|-----------|
| **Novela** | Personajes, diálogos, relaciones | Alta | Media | Estándar |
| **Técnico** | Terminología, acrónimos, referencias | Baja | Baja | Formal |
| **Jurídico** | Precisión, referencias cruzadas | Baja | Baja | Estricta |
| **Memoria** | Timeline, cronología, fechas | Media | Muy alta | Estándar |
| **Infantil** | Vocabulario, legibilidad, registro | Alta | Baja | Simple |
| **Ensayo** | Coherencia argumental, registro | Baja | Media | Formal |

Para cambiar: **Configuración → Presets** → selecciona el preset → los ajustes se aplican inmediatamente.

> **Tip**: Si tu manuscrito mezcla géneros (ej: novela histórica con rigor cronológico), empieza con **"Novela"** y sube manualmente la sensibilidad de Timeline.

---

## Análisis

### Sensibilidad General

```
Menos alertas ◄──────────●──────────► Más alertas
(solo evidentes)     [Equilibrada]     (incluye dudosas)
```

| Nivel | Comportamiento | Recomendado para |
|-------|----------------|------------------|
| **Baja** | Solo inconsistencias claras (confianza > 85%) | Manuscritos finales |
| **Media** | Balance precisión/cobertura (> 65%) | Uso general |
| **Alta** | Incluye alertas dudosas (> 40%) | Primeros borradores |

### Calidad de Análisis

| Nivel | Métodos Usados | Tiempo | Precisión |
|-------|---------------|--------|-----------|
| **Rápida** | NLP básico (spaCy) | 1-3 min | Buena |
| **Equilibrada** | NLP + embeddings + heurísticas | 3-7 min | Alta |
| **Profunda** | NLP + embeddings + LLM (Ollama) | 5-15 min | Muy alta |

> **Tip**: Usa **"Rápida"** mientras escribes borradores y **"Profunda"** para la revisión final.

---

## Modelos LLM (Ollama)

Narrative Assistant usa **Ollama** para ejecutar modelos de lenguaje 100% locales. Tus manuscritos nunca salen de tu ordenador.

| Modelo | Tamaño | Velocidad | Calidad | Mejor para |
|--------|--------|-----------|---------|------------|
| **llama3.2** | 3B (~2 GB) | Rápido | Buena | Uso general, equipos modestos |
| **qwen2.5** | 7B (~4 GB) | Media | Alta | Textos en español (recomendado) |
| **mistral** | 7B (~4 GB) | Media | Alta | Razonamiento, alertas complejas |
| **gemma2** | 9B (~6 GB) | Lento | Muy alta | Máxima calidad, requiere GPU |

### Configurar

1. Ve a **Configuración → Modelos LLM**
2. Verás el estado de Ollama (✅ Conectado / ❌ Desconectado)
3. Selecciona el modelo preferido y haz clic en **"Probar Conexión"**

### Sistema Multi-Modelo (Votación)

Para máxima precisión, habilita varios métodos simultáneos:

```
Métodos habilitados:
☑ llama3.2      (LLM)
☑ qwen2.5       (LLM)
☐ mistral        (LLM)
☑ rule_based     (Reglas)       ← Siempre disponible
☑ embeddings     (Semántico)

Confianza mínima: [70%]
Consenso mínimo:  [60%]  ← % de métodos que deben coincidir
```

> **Tip**: Con poca RAM (< 16 GB), usa solo **llama3.2** + **rule_based**. Con equipos potentes, activa 2-3 modelos LLM y sube el consenso al 70%.

---

## Gramática y Estilo

### Reglas de Gramática Española

| Regla | Descripción | Ejemplo |
|-------|-------------|---------|
| **Concordancia** | Género y número | "Los niños *contenta*" → "contentos" |
| **Artículo ante 'a' tónica** | Femeninos con "el" | "el agua *clara*" (correcto) |
| **Leísmo/Laísmo** | Pronombres | "Le dijo" vs "La dijo" |
| **Dequeísmo** | Uso incorrecto de "de que" | "*De que* vengas" → "Que vengas" |
| **Registro** | Consistencia formal/informal | Mezclar "usted" y "tú" sin motivo |

### Sensibilidad de Concordancia

- **Estricta**: Detecta toda discordancia, incluyendo las contextuales
- **Contextual** *(recomendada)*: Ignora falsos positivos comunes
- **Permisiva**: Solo errores claros e inequívocos

### Preferencias de Estilo

- **Muletillas**: Detectar repeticiones excesivas de palabras/frases
- **Párrafos largos**: Alertar si un párrafo supera X líneas
- **Riqueza léxica**: Señalar vocabulario repetitivo
- **Voz pasiva**: Alertar uso excesivo (configurable)

---

## Preferencias de Alertas

### Categorías Habilitadas

```
☑ Inconsistencias de personajes     [Alta prioridad]
☑ Contradicciones de timeline       [Alta prioridad]
☑ Relaciones incoherentes           [Media prioridad]
☑ Eventos contradictorios           [Media prioridad]
☐ Calidad de diálogos               [Desactivado]
☑ Gramática y estilo                [Baja prioridad]
```

### Severidad Mínima

| Nivel | Muestra |
|-------|---------|
| **Todas** | Críticas + Altas + Medias + Bajas + Info |
| **Media+** | Críticas + Altas + Medias |
| **Alta+** | Solo Críticas y Altas |
| **Solo críticas** | Solo inconsistencias graves |

> **Tip**: Para la primera revisión, configura **"Media+"**. Así te concentras en lo importante sin abrumarte.

---

## Gestión de Datos

### Exportar Datos

1. Ve a **Configuración → Gestión de Datos → Exportar Proyecto**
2. Selecciona formato: **JSON completo**, **CSV de alertas** o **Markdown resumen**

### Eliminar Proyecto

1. Ve a **Gestión de Datos → Proyectos** → selecciona → **"Eliminar"**

⚠️ **Irreversible**. Se eliminan entidades, alertas e historial.

### Limpiar Todos los Datos

1. Ve a **Gestión de Datos → Avanzado → "Eliminar Todos los Datos"**
2. Confirma escribiendo "ELIMINAR"

> **Nota**: Los modelos NLP y LLM no se eliminan (están en directorios separados).

---

## Apariencia y Sistema

### Tema Claro / Oscuro

En **Configuración → Apariencia**, selecciona **Claro**, **Oscuro** o **Sistema** (sigue tu SO). El cambio se aplica inmediatamente.

### Diagnósticos

**Configuración → Sistema** muestra estado del entorno:

```
Sistema:     Windows 11 Pro | 16 GB RAM | NVIDIA RTX 3060
spaCy:       es_core_news_lg ✅
Embeddings:  paraphrase-multilingual ✅
Ollama:      Conectado ✅ (llama3.2, qwen2.5)
Base datos:  45 MB | 3 proyectos | 1 colección
```

Haz clic en **"Verificar"** para comprobar que modelos, Ollama y base de datos funcionan correctamente.

---

## Próximos Pasos

- **Ver casos de uso prácticos**: [Capítulo 8](08-use-cases.md)
- **Gestión de colecciones**: [Capítulo 6](06-collections-sagas.md)
- **Volver a alertas**: [Capítulo 4](04-alerts.md)

---

**Tip**: No intentes configurar todo a la perfección desde el principio. Empieza con un preset, analiza tu manuscrito, y ajusta según los resultados que obtengas.
