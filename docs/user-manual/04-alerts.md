# 4. Alertas de Inconsistencia

Las **alertas** son el corazón de Narrative Assistant: señalan posibles inconsistencias, errores y oportunidades de mejora en tu manuscrito. Cada alerta es una invitación a revisar, no una orden de corregir.

---

## ¿Qué es una Alerta?

Una alerta es un aviso generado automáticamente cuando el sistema detecta algo que **podría** ser un error o inconsistencia. Incluye:

- **Título**: Descripción breve del problema ("Color de ojos inconsistente")
- **Descripción**: Detalle con los valores conflictivos ("María: 'verdes' vs 'azules'")
- **Ubicación**: Capítulo y posición exacta en el texto
- **Confianza**: Porcentaje de certeza del sistema (0-100%)
- **Sugerencia**: Recomendación de corrección (cuando aplica)

> **Recuerda**: Tú decides si cada alerta es un error real o una decisión narrativa intencional.

---

## Categorías de Alertas

Las alertas se organizan en **tres grandes grupos** (meta-categorías) y **14 categorías** específicas:

### Errores (rojo)

| Categoría | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Gramática** | Errores ortográficos y gramaticales | "havía" → "había" |
| **Tipografía** | Comillas incorrectas, espaciado | Comillas rectas en vez de tipográficas |
| **Puntuación** | Raya de diálogo, puntos suspensivos | "- Hola" → "—Hola" |
| **Concordancia** | Discordancia de género o número | "la problema" → "el problema" |

### Inconsistencias (amarillo)

| Categoría | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Atributo** | Contradicciones de personajes | Ojos azules en cap. 3, verdes en cap. 12 |
| **Temporal** | Problemas en la línea temporal | Personaje envejece 5 años en 2 meses de historia |
| **Relación** | Vínculos contradictorios | "Su hermano Juan" → "Su primo Juan" |
| **Ubicación** | Presencia imposible en lugares | Personaje en Madrid y Barcelona el mismo día |
| **Comportamiento** | Acciones fuera de carácter | Personaje tímido hace un discurso público sin justificación |
| **Conocimiento** | Información que no debería tener | Personaje sabe un secreto que nadie le contó |

### Sugerencias (verde)

| Categoría | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Estilo** | Voz narrativa, registro | Cambio involuntario de registro formal a coloquial |
| **Repetición** | Palabras repetidas cercanas | "importante" tres veces en el mismo párrafo |
| **Estructura** | Problemas estructurales | Capítulo demasiado corto sin justificación narrativa |
| **Otra** | Alertas no categorizadas | Entidades ambiguas, variantes de nombres |

---

## Niveles de Severidad

Cada alerta tiene un nivel de severidad que indica su urgencia:

```
🔴 CRÍTICO   Debe corregirse (error evidente, contradicción clara)
🟠 ALTO      Debería revisarse (posible error importante)
🟡 MEDIO     Merece atención (inconsistencia probable)
🔵 BAJO      Sugerencia menor (mejora opcional)
ℹ️  INFO      Informativa (para tu conocimiento)
```

**Orden de priorización**: Las alertas se ordenan automáticamente por severidad (críticas primero), luego por confianza y posición en el texto.

---

## El Panel de Alertas (AlertsDashboard)

```
┌───────────────────────────────────────────────────────────────┐
│ 🔍 [Buscar...]   [Severidad▼]  [Categoría▼]  [Estado▼]      │
│ ┌─────────┐ ┌──────────────────┐ ┌─────────────┐             │
│ │ Errores │ │ Inconsistencias  │ │ Sugerencias  │  [Limpiar]  │
│ │   23    │ │       18         │ │     26       │             │
│ └─────────┘ └──────────────────┘ └─────────────┘             │
├───────────────────────────────────────────────────────────────┤
│ 🔴 Color de ojos inconsistente              Cap. 3  │ 95%    │
│ 🟠 Edad imposible                           Cap. 12 │ 90%    │
│ 🟡 Repetición léxica                        Cap. 5  │ 75%    │
└───────────────────────────────────────────────────────────────┘
```

Los tres botones superiores (**Errores**, **Inconsistencias**, **Sugerencias**) son filtros rápidos de meta-categoría. Haz clic en uno para ver solo ese grupo; clic de nuevo para desactivar.

---

## Búsqueda y Filtrado

### Filtros Disponibles

| Filtro | Descripción | Uso típico |
|--------|-------------|------------|
| **Búsqueda de texto** | Busca en título, descripción | Buscar "María" para ver alertas de ese personaje |
| **Severidad** | Crítico, Alto, Medio, Bajo, Info | Ver solo alertas críticas y altas |
| **Categoría** | Las 14 categorías listadas | Filtrar solo errores gramaticales |
| **Estado** | Activa, Resuelta, Descartada | Ver solo alertas pendientes |
| **Rango de capítulos** | Del capítulo X al Y | Revisar solo los capítulos recién escritos |
| **Confianza mínima** | Porcentaje de certeza | Ocultar alertas con baja confianza |
| **Tipo de alerta** | Tipo específico del detector | Solo errores de tildes, solo repeticiones |
| **Entidad** | Filtrar por personaje/lugar | Alertas que involucran a "María" |

### Presets de Filtro Rápido

Para agilizar flujos de trabajo comunes, el sistema incluye presets predefinidos:

| Preset | Qué filtra |
|--------|------------|
| **Errores gramaticales** | Gramática, concordancia, tipografía, puntuación |
| **Severidad alta+** | Solo alertas críticas y altas |
| **Inconsistencias** | Atributos, timeline, relaciones, ubicación, comportamiento, conocimiento |
| **Estilo y repetición** | Problemas de estilo y repeticiones léxicas |

Para usar un preset, haz clic en el **menú de filtros rápidos** y selecciona uno. El preset aplica los filtros automáticamente; puedes modificarlos después.

---

## Gestión de Estados

Cada alerta pasa por un ciclo de vida sencillo:

```
  ┌──────────┐     Corregiste el texto     ┌───────────┐
  │  ACTIVA  │ ───────────────────────────→ │ RESUELTA  │
  │  (nueva) │                              └───────────┘
  └────┬─────┘
       │   No es un error real              ┌────────────┐
       └──────────────────────────────────→ │ DESCARTADA │
                                            └────────────┘
```

### Acciones sobre una Alerta

1. **Resolver** ✅ — Usaste la alerta para corregir tu manuscrito
2. **Descartar** ❌ — La alerta es un falso positivo o es intencional
3. **Reabrir** 🔄 — Cambiar una alerta resuelta/descartada de vuelta a activa

**Tip**: Al re-analizar el documento después de correcciones, las alertas resueltas automáticamente por cambios en el texto se marcan como "auto-resueltas".

---

## Modo Foco: Navegar al Texto

Una de las funciones más útiles: al hacer clic en una alerta, el sistema **navega directamente** a la posición del texto donde ocurre el problema.

### Cómo funciona

1. **Selecciona** una alerta de la lista
2. El visor de texto **se desplaza** automáticamente al fragmento relevante
3. El texto problemático queda **resaltado** en el visor
4. Si la alerta tiene **dos ubicaciones** (inconsistencia de atributo), puedes navegar a cada una por separado haciendo clic en las fuentes

### Ejemplo: Inconsistencia de Atributo

```
Alerta: "Color de ojos inconsistente"
├── Fuente 1: Cap. 3  → "María abrió sus ojos azules..."
└── Fuente 2: Cap. 12 → "Los ojos verdes de María brillaban..."

→ Haz clic en "Fuente 1" para ir al capítulo 3
→ Haz clic en "Fuente 2" para ir al capítulo 12
```

---

## Reglas de Supresión

Si recibes alertas recurrentes que no son relevantes para tu manuscrito, puedes crear **reglas de supresión** para silenciarlas automáticamente.

### Crear una Regla

1. Haz clic en el icono de **configuración de supresión** en la barra de herramientas
2. En el diálogo, haz clic en **"Nueva Regla"**
3. Configura:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Tipo de regla** | Qué criterio usar para suprimir | Tipo de alerta, Categoría, Entidad, Módulo |
| **Patrón** | Texto o comodín para coincidir | `spelling_*` (todos los errores ortográficos) |
| **Entidad** | Nombre de entidad (solo si tipo = Entidad) | "Madrid" |
| **Motivo** | Razón para la supresión (opcional) | "Nombre artístico intencional" |

**Ejemplos**: Nombre artístico intencional ("Kris" sin "h") → suprimir por entidad. Neologismos de ciencia ficción → suprimir patrón `spelling_*`. Las reglas son por proyecto y no afectan a otros manuscritos.

---

## Exportar Alertas

Haz clic en **"Exportar"** en la barra de herramientas para descargar las alertas filtradas:

| Formato | Uso |
|---------|-----|
| **CSV** | Abrir en Excel, Google Sheets o LibreOffice Calc |
| **JSON** | Integración con otras herramientas, programático |

```csv
ID,Severidad,Categoría,Estado,Capítulo,Título,Descripción,Confianza
1,critical,attribute,active,3,"Color de ojos inconsistente","María: verdes vs azules",95%
2,high,timeline,active,12,"Edad imposible","Juan envejece 10 años en 1 semana",90%
```

---

## Casos de Uso Prácticos

### Corrección editorial de una novela

1. **Primer pase**: Filtrar por **"Errores gramaticales"** (preset) → corregir erratas
2. **Segundo pase**: Filtrar por **"Severidad alta+"** → resolver inconsistencias graves
3. **Tercer pase**: Revisar **"Sugerencias"** → mejorar estilo si lo deseas
4. Re-importar el documento corregido y re-analizar

### Revisar un capítulo específico

1. Usar filtro de **Rango de capítulos** (ej: 5 a 5)
2. Revisar todas las alertas de ese capítulo
3. Resolver o descartar una por una
4. Pasar al siguiente capítulo

### Limpiar falsos positivos

1. Filtrar por **Estado: Activa** y **Confianza < 60%**
2. Revisar y descartar las que sean falsos positivos
3. Crear reglas de supresión para patrones repetitivos

---

## Consejos

- ✅ **Prioriza** alertas críticas y altas antes de pasar a las medias
- ✅ **Fusiona entidades** antes de revisar alertas (mejora la precisión; ver [Capítulo 3](03-entities.md))
- ✅ **Usa presets** como punto de partida y ajusta filtros según tu flujo
- ✅ **Exporta a CSV** para llevar un registro de correcciones entre sesiones
- ⚠️ No descartes alertas sin leerlas: una alerta de confianza 60% puede ser un error real
- ⚠️ Re-analiza después de cada ronda de correcciones para verificar que las alertas desaparecen

---

## Próximos Pasos

- **Timeline y Eventos**: [Capítulo 5](05-timeline-events.md)
- **Colecciones y Sagas**: [Capítulo 6](06-collections-sagas.md)
- **Configuración Avanzada**: [Capítulo 7](07-settings.md)

---

**Tip**: Dedica la primera sesión a resolver alertas críticas y descartar falsos positivos evidentes. Esto "entrena" tu ojo para las siguientes rondas y mantiene la lista de alertas manejable.
