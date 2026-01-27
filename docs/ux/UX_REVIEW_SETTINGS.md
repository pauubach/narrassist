# Revisión UX: Configuración, Correcciones y Filtros

**Fecha**: 2026-01-28
**Estado**: Para deliberación con equipo

**Participantes necesarios**: PO, UX, UI, Arquitecto, Experto Editorial, Lingüista, Usuarios tipo

---

## 0. Problema Principal: Sistema de Correcciones Editoriales

### Situación actual

El sistema de "presets de corrección" tiene problemas fundamentales de diseño:

1. **No detecta el tipo de documento automáticamente**
   - El usuario debe configurar manualmente el preset
   - No aprovecha el análisis NLP que ya detecta el tipo de documento

2. **No respeta la consistencia interna del documento**
   - Si un manuscrito usa guión simple (`-`) consistentemente en TODO el documento
   - ¿Tiene sentido sugerir cambiar TODOS los guiones a raya (`—`)?
   - El sistema debería ofrecer una opción "definido por el documento"

3. **Configuración confusa**
   - No queda claro si es para "nuevos proyectos" o "documento actual"
   - El usuario ve un "resumen" pero no sabe cómo editarlo

### Propuesta de diseño

```
┌─────────────────────────────────────────────────────────────────┐
│  Estilo tipográfico                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Para cada tipo de documento, define qué estilo aplicar:        │
│                                                                  │
│  ┌─────────────┬──────────────────────────────────────────────┐ │
│  │ Narrativa   │ [Detectar del documento ▼]                   │ │
│  │             │  ○ Detectar del documento (respetar estilo)  │ │
│  │             │  ○ Raya (—) para diálogos                    │ │
│  │             │  ○ Guión (-) para diálogos                   │ │
│  │             │  ○ Comillas angulares «»                     │ │
│  │             │  ○ Comillas inglesas ""                      │ │
│  ├─────────────┼──────────────────────────────────────────────┤ │
│  │ Autoayuda   │ [Detectar del documento ▼]                   │ │
│  ├─────────────┼──────────────────────────────────────────────┤ │
│  │ Técnico     │ [Detectar del documento ▼]                   │ │
│  └─────────────┴──────────────────────────────────────────────┘ │
│                                                                  │
│  ℹ️ "Detectar del documento" respetará el estilo que ya usa     │
│     el manuscrito, sugiriendo solo corregir inconsistencias.    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Comportamiento propuesto

| Configuración | Comportamiento |
|---------------|----------------|
| **Detectar del documento** (default) | Analiza qué usa el documento. Si usa `-` consistentemente, NO sugiere cambiar a `—`. Solo alerta si hay MEZCLA de estilos. |
| **Raya (—)** | Siempre sugiere usar raya, aunque el documento use guión consistentemente. |
| **Guión (-)** | Siempre sugiere usar guión, aunque el documento use raya. |

### Preguntas para deliberación

| Rol | Pregunta |
|-----|----------|
| **PO** | ¿Los usuarios quieren que el sistema "imponga" un estilo o que "respete" el estilo del documento? |
| **Experto Editorial** | ¿Cuál es la práctica estándar en corrección profesional? ¿Se respeta el estilo del autor o se normaliza? |
| **Lingüista** | ¿Qué reglas de tipografía aplican según el tipo de documento (narrativa vs técnico vs autoayuda)? |
| **UX** | ¿Cómo comunicamos esta flexibilidad sin abrumar al usuario? |
| **Arquitecto** | ¿Cómo implementamos la detección automática del estilo del documento? |

---

## 1. Filtros de Entidades - ¿Útil o sobrecarga?

### ¿Qué hace actualmente?

La sección "Filtros de Entidades" permite:
1. **Patrones del sistema** (57 patrones): Activar/desactivar filtros para palabras comunes
   - Artículos determinados: El, La, Las, Los
   - Artículos indeterminados: Un, Una
   - Marcadores temporales, expresiones comunes, etc.

2. **Rechazos globales**: Lista de entidades que el usuario ha rechazado manualmente

### Preguntas para el equipo

| Pregunta | Para quién |
|----------|------------|
| ¿Qué problema del usuario resuelve mostrar 57 checkboxes de filtrado? | PO |
| ¿Alguien ha pedido poder desactivar el filtro del artículo "El"? | PO |
| ¿Un corrector/editor entiende qué es un "patrón de filtrado de entidades"? | UX, Usuarios |
| ¿Con qué frecuencia un usuario cambiaría estos filtros? | Usuarios |

### Opciones de diseño

| Opción | Descripción | Beneficio |
|--------|-------------|-----------|
| **A: Eliminar de UI** | Los filtros funcionan automáticamente | Menos sobrecarga cognitiva |
| **B: Configuración avanzada** | Ocultar bajo acordeón colapsable | Disponible sin molestar |
| **C: Simplificar** | 3-4 toggles por categoría en vez de 57 checkboxes | Mismo control, menos ruido |

**Recomendación**: Opción A. El sistema debería "simplemente funcionar".

---

## 2. Problema de Espacio Desaprovechado

### Estado: ✅ CSS corregido

Se añadió CSS para `.setting-item.column` que hace que el contenido use todo el ancho:

```css
.setting-item.column {
  flex-direction: column;
  gap: 1rem;
}
```

### Pendiente: Revisión general

La vista de Configuración se está haciendo muy larga. ¿Debería consolidarse o reorganizarse?

**Pregunta para UX/UI**: ¿Merece la pena tener la configuración separada en tantas secciones?

---

## 3. Tutorial Desactualizado

### Problema detectado

El tutorial muestra **7 pestañas**:
- Texto, Entidades, Relaciones, Alertas, Timeline, Estilo, Resumen

Pero el workspace tiene **8 pestañas** (falta **Glosario**).

### Archivo a corregir

`frontend/src/components/TutorialDialog.vue` líneas 117-127

```vue
<!-- Actual (incorrecto) -->
<span class="tab">Texto</span>
<span class="tab">Entidades</span>
<span class="tab">Relaciones</span>
<span class="tab">Alertas</span>
<span class="tab">Timeline</span>
<span class="tab">Estilo</span>
<span class="tab">Resumen</span>
<!-- Falta: Glosario -->
```

**Nota**: Las tabs son dinámicas según tipo de documento, así que el texto "7 pestañas" también debe actualizarse.

---

## 4. Otros problemas detectados

### 4.1 Resumen de configuración sin acción

**Problema**: Se muestra "Resumen de configuración" pero no hay forma de editarlo.

**Solución propuesta**: Añadir botón "Personalizar" que abra un diálogo de edición.

### 4.2 Texto ambiguo "preset seleccionado"

**Problema**: Usuario pregunta "¿A qué documento se refiere?"

**Solución propuesta**: Clarificar que es para **nuevos proyectos**:
```
"Configuración base para nuevos proyectos"
"Esta configuración se aplicará cuando crees un nuevo proyecto.
 Cada proyecto puede tener su propia configuración."
```

---

## 5. Plan de acción

| Prioridad | Tarea | Responsable | Estado |
|-----------|-------|-------------|--------|
| **Alta** | Deliberar sobre sistema de correcciones editoriales | Equipo completo | Pendiente |
| **Alta** | Corregir tutorial (8 tabs, no 7) | FE | Pendiente |
| Media | Decidir qué hacer con filtros de entidades | PO + UX | Pendiente |
| Media | Añadir botón "Personalizar" al resumen | FE | Pendiente |
| ~~Media~~ | ~~Añadir CSS para `.setting-item.column`~~ | ~~FE~~ | ✅ Hecho |
| Baja | Revisar longitud de vista de configuración | UX + FE | Pendiente |

---

## 6. Próximos pasos

1. **Programar sesión de deliberación** con:
   - PO
   - UX
   - UI
   - Arquitecto
   - Experto Editorial (si disponible)
   - Lingüista (si disponible)
   - Usuarios tipo (si posible)

2. **Decisiones a tomar**:
   - ¿El sistema debe detectar el estilo del documento automáticamente?
   - ¿Debe haber opción "definido por el documento"?
   - ¿Los filtros de entidades deben ser visibles o automáticos?
   - ¿La vista de configuración necesita reorganizarse?
