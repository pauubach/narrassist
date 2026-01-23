# Estado del Arte: UI/UX en Herramientas de Corrección Literaria y Productividad (2025-2026)

> **Fecha de investigación**: 2026-01-13
> **Investigador**: Claude (Sonnet 4.5)
> **Propósito**: Identificar patrones de diseño modernos aplicables a Narrative Assistant

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Herramientas de Corrección Literaria Profesional](#herramientas-de-corrección-literaria-profesional)
3. [Herramientas de Productividad con Excelente UX](#herramientas-de-productividad-con-excelente-ux)
4. [Tendencias de Diseño UI 2025-2026](#tendencias-de-diseño-ui-2025-2026)
5. [Análisis Comparativo](#análisis-comparativo)
6. [Recomendaciones para Narrative Assistant](#recomendaciones-para-narrative-assistant)
7. [Referencias y Recursos](#referencias-y-recursos)

---

## Resumen Ejecutivo

### Hallazgos Clave

**Patrones UI/UX dominantes en 2025-2026:**

1. **Interfaces adaptativas con IA integrada** - Asistentes contextuales que no interrumpen el flujo
2. **Sistemas de diseño semánticos** - Variables CSS dinámicas, tokens de color avanzados
3. **Command palettes universales** - Acceso rápido por teclado (Cmd+K / Ctrl+K)
4. **Paneles contextuales inteligentes** - Sidebars que muestran información relevante sin ocupar espacio
5. **Micro-feedback inmediato** - Validación en tiempo real sin alertas intrusivas
6. **Dark mode refinado** - No solo inversión de colores, sino paletas optimizadas para legibilidad
7. **Accesibilidad por defecto** - WCAG AAA, navegación por teclado completa

**Tecnologías emergentes:**
- Design tokens (JSON/YAML → CSS variables)
- Radix UI / Headless UI para componentes accesibles
- Framer Motion / Motion One para micro-interacciones
- View Transitions API para transiciones fluidas
- Container Queries para layouts responsivos contextuales

---

## Herramientas de Corrección Literaria Profesional

### 1. Grammarly (2025-2026)

**Versión actual**: Grammarly Pro con GrammarlyGO (AI assistant)

#### Qué hacen bien

**UI/UX:**
- **Sidebar contextual no intrusivo**: Panel lateral colapsable que solo aparece cuando hay sugerencias
- **Inline suggestions con preview**: Hover sobre texto subrayado muestra corrección sin interrumpir escritura
- **Tone detector visual**: Medidor de tono emocional con colores (profesional→casual)
- **Goals panel**: Permite configurar audiencia, formalidad, dominio antes de analizar
- **Card-based suggestions**: Cada sugerencia en una card clara con explicación y ejemplo

**Patrones de color:**
- **Crítico**: `#FF4D4F` (rojo brillante pero no agresivo)
- **Advertencia**: `#FAAD14` (amarillo/naranja)
- **Mejora**: `#1890FF` (azul neutro)
- **Correcto**: `#52C41A` (verde)
- **Fondo oscuro**: `#141414` (gris muy oscuro, no negro puro)

**Interacciones destacadas:**
- Click en sugerencia aplica cambio + permite undo inline
- Swipe left/right en móvil para aceptar/rechazar
- Keyboard shortcuts: `Tab` siguiente, `Shift+Tab` anterior, `Enter` aceptar

**Sistema de confianza:**
- Mostrar nivel de confianza visualmente (1-3 estrellas, no porcentajes)
- Ocultar sugerencias de baja confianza por defecto
- Permitir ajustar sensibilidad con slider

#### Fortalezas aplicables a Narrative Assistant

1. **Explicaciones contextuales**: Cada alerta tiene "Why is this important?" expandible
2. **Batch actions**: "Accept all [type]" con preview de cambios
3. **Learning from user**: Marca correcciones ignoradas y ajusta futuras sugerencias
4. **Performance dashboard**: Métricas de mejora (antes/después) con gráficos simples

---

### 2. ProWritingAid (2025)

**Versión actual**: ProWritingAid v3.0 (escritorio + web)

#### Qué hacen bien

**UI/UX:**
- **Múltiples vistas de análisis**: Summary, Writing Style, Grammar, Overused Words, Sticky Sentences, etc.
- **Heat maps visuales**: Párrafos coloreados por densidad de problemas (verde→amarillo→rojo)
- **Word Explorer integrado**: Click derecho en palabra muestra sinónimos, definiciones, uso contextual
- **Comparison mode**: Antes/después lado a lado
- **Document structure tree**: Árbol de capítulos colapsable con indicadores de alertas por sección

**Patrones de diseño:**
- **Split panel ajustable**: Documento (60%) + panel análisis (40%), con resize handle
- **Filtros visuales**: Iconos + contadores de alertas por categoría
- **Progress indicators**: Barra de progreso con pasos nombrados (Parsing → Analysis → Suggestions)
- **Contextual tooltips**: Hover sobre términos técnicos muestra definición inline

**Sistema de categorización de alertas:**
- Grammar (crítico)
- Style (sugerencia)
- Pacing (informativo)
- Readability (métrica)
- Cada categoría con icono distintivo + color consistente

#### Fortalezas aplicables a Narrative Assistant

1. **Reports exportables**: PDF/HTML con gráficos de calidad (word cloud, timeline)
2. **Custom style guides**: Usuario define reglas específicas (ej: evitar "muy", preferir voz activa)
3. **Integración con Scrivener**: Análisis de documentos compilados, respeta estructura de carpetas
4. **Escritura por sesión**: Guarda estadísticas de cada sesión (palabras escritas, tiempo, progreso)

---

### 3. Scrivener 3 (2025)

**Versión actual**: Scrivener 3.3.6 (macOS/Windows)

#### Qué hacen bien

**UI/UX:**
- **Three-pane layout**: Binder (navegación) + Editor + Inspector (metadatos)
- **Corkboard view**: Vista de tarjetas para reorganizar escenas
- **Scrivenings mode**: Múltiples documentos en un scroll continuo
- **Composition mode**: Full-screen sin distracciones
- **Customizable toolbar**: Usuario arrastra iconos que necesita

**Gestión de proyectos:**
- **Label & Status colors**: Etiquetas visuales por escena (Draft, Revised, Final)
- **Custom metadata**: Usuario define campos arbitrarios (POV, Date, Location)
- **Search collections**: Búsquedas guardadas como carpetas virtuales
- **Snapshots**: Versión de documento antes de editar, con diff visual

**Sistema de navegación:**
- Binder con iconos por tipo (carpeta, documento, imagen)
- Drag & drop para reorganizar estructura
- Reveal in Binder desde editor (breadcrumb navigation)

#### Fortalezas aplicables a Narrative Assistant

1. **Project templates**: Plantillas pre-configuradas (Novel, Screenplay, Research Paper)
2. **Inspector con tabs**: Metadatos, Notas, Keywords, Referencias en panel lateral tabbed
3. **Quick Reference windows**: Abrir documentos en ventanas flotantes para comparar
4. **Color-coded progress bars**: Barra de progreso por documento con target word count

---

### 4. Hemingway Editor (2025)

**Versión actual**: Hemingway Editor 3.0 Desktop + Online

#### Qué hacen bien

**UI/UX:**
- **Simplicidad extrema**: Solo dos botones principales (Write / Edit)
- **Color-coding inline**: Texto coloreado según problema (amarillo=adverbios, rojo=difícil de leer)
- **Readability grade**: Número grande y claro (Grade 8) con meta (Grade 6)
- **Side-by-side editor**: Markdown source + preview formateado

**Sistema de alertas visual:**
- Amarillo: Advertencia (adverbs, complex phrases)
- Rojo: Crítico (very hard to read)
- Púrpura: Sugerencia (simpler alternatives)
- Azul: Informativo (weak words)
- Verde: Voz pasiva (passive voice)

**Minimalismo funcional:**
- Sin sidebar, toda la información en overlay tooltip
- Hover sobre frase destacada muestra sugerencia + explicación breve
- Estadísticas en esquina (palabras, oraciones, tiempo de lectura)

#### Fortalezas aplicables a Narrative Assistant

1. **Focus on readability**: Métricas simples y accionables (no abrumar con datos)
2. **Write mode sin distracciones**: Oculta highlights mientras escribes
3. **Instant feedback**: Análisis en tiempo real mientras escribes (sin latencia)
4. **Export directo**: Exportar a Word/PDF con un click

---

### 5. AutoCrit (2025)

**Versión actual**: AutoCrit Online Editor

#### Qué hacen bien

**UI/UX:**
- **Manuscript compare**: Compara tu manuscrito con best-sellers del género
- **Pacing graph**: Gráfico de línea mostrando ritmo narrativo por capítulo
- **Dialogue visualization**: Porcentaje de diálogo vs narración por escena
- **Repetition timeline**: Timeline horizontal con marcadores de palabras repetidas

**Análisis específico de ficción:**
- **Show vs Tell ratio**: Detecta telling excesivo
- **Strong writing indicators**: Resalta escritura fuerte para reforzar patrones
- **Generic descriptions**: Detecta clichés ("ojos azules como el océano")
- **Adverb abuse**: Contador de -mente/-ly con ejemplos contextuales

**Comparación con benchmarks:**
- Seleccionar género (Thriller, Romance, Fantasy)
- Ver estadísticas comparativas (tu manuscrito vs promedio del género)
- Gráficos de radar para múltiples métricas

#### Fortalezas aplicables a Narrative Assistant

1. **Genre-specific analysis**: Ajustar expectativas según género literario
2. **Visualizaciones de datos**: Gráficos comprensibles para no-técnicos
3. **Progress tracking**: Comparar análisis antes/después de ediciones
4. **Actionable insights**: No solo detectar problemas, sugerir qué cambiar

---

## Herramientas de Productividad con Excelente UX

### 1. Notion (2025-2026)

**Versión actual**: Notion 3.0 con AI integrada

#### Patrones UI destacados

**Layout y estructura:**
- **Block-based editing**: Todo es un bloque draggable (texto, imagen, base de datos)
- **Nested pages infinitas**: Jerarquía visual con indent + iconos personalizables
- **Inline databases**: Tablas/Kanban/Calendar embebidos en páginas
- **Synced blocks**: Bloques sincronizados en múltiples páginas

**Sistema de diseño:**
- **Variables CSS semánticas**: `--notion-blue`, `--notion-gray-1` a `--notion-gray-9`
- **Modo oscuro refinado**: No invierte colores, usa paleta específica dark-optimized
- **Hover states sutiles**: `background-color: var(--bg-hover)` con transición 150ms
- **Focus states accesibles**: Outline azul con `outline-offset: 2px`

**Command palette (Cmd+K):**
- Búsqueda fuzzy ultra-rápida
- Categorías: Pages, Create, Actions, Settings
- Iconos + texto + keyboard shortcuts visibles
- Preview del resultado en panel derecho

**Componentes destacados:**
- **Toggle lists**: Acordeones con chevron animado
- **Callout blocks**: Cajas con icono, fondo coloreado, borde izquierdo grueso
- **Property pills**: Tags con border-radius alto, colores pasteles
- **Progress bars**: SVG circular para porcentajes, lineal para cantidades

#### Sistema de temas de Notion

```css
/* Light mode */
--notion-bg: #ffffff;
--notion-text: #37352f;
--notion-gray: #787774;
--notion-blue: #0b6dd6;
--notion-red: #eb5757;
--notion-yellow: #f7b844;
--notion-green: #4dab5e;
--notion-purple: #9b51e0;

/* Dark mode (no es simple inversión) */
--notion-bg-dark: #191919;
--notion-text-dark: #efefef;
--notion-gray-dark: #9b9a97;
--notion-blue-dark: #529cca;
--notion-red-dark: #ff6e6e;
/* Colores más saturados en dark mode para legibilidad */
```

**Transiciones:**
- Page load: fade-in + slide-up (300ms ease-out)
- Hover: scale(1.02) en cards (200ms)
- Modal open: backdrop fade + content scale-in (250ms)

#### Micro-interacciones

- **Drag handles**: Aparecen al hover, con haptic feedback visual
- **Loading states**: Skeleton screens, no spinners genéricos
- **Empty states**: Ilustración + texto motivacional + CTA claro
- **Undo toast**: Notification temporal con botón Undo (5s timeout)

---

### 2. Linear (2025)

**Versión actual**: Linear (web app)

#### Patrones UI destacados

**Velocidad y eficiencia:**
- **Instant search**: Resultados mientras escribes (< 50ms)
- **Keyboard-first**: Toda acción tiene shortcut (documentado en ?)
- **Optimistic UI**: Cambios aparecen inmediatamente, sync en background
- **Prefetching inteligente**: Precarga páginas probables (hover > 200ms)

**Sistema de color:**
- **Status colors**: Todo/In Progress/Done con colores consistentes
- **Priority indicators**: P0 (rojo), P1 (naranja), P2 (azul), P3 (gris)
- **Team colors**: Cada equipo tiene color único para issues
- **Gradientes sutiles**: Headers con gradiente lineal 5% opacity

**Navegación:**
- **Three-column layout**: Sidebar + Lista + Detalle
- **Breadcrumb navigation**: Siempre visible, con shortcuts (Alt+Up)
- **View switcher**: Dropdown para cambiar vistas (List, Board, Roadmap)
- **Filters panel**: Slide-in panel con filtros apilables

#### Sistema de animaciones

```css
/* Linear usa spring animations (no ease) */
--linear-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 350ms;

/* Ejemplos */
.modal-enter {
  animation: scale-in var(--duration-normal) var(--linear-spring);
}

@keyframes scale-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

**Feedback visual:**
- **Progress indicators**: Circular con porcentaje + color gradiente
- **Loading placeholders**: Gray blocks con shimmer effect
- **Success states**: Green checkmark con bounce animation
- **Error states**: Red shake + descriptive message

---

### 3. Figma (2025)

**Versión actual**: Figma (web + desktop)

#### Patrones UI destacados

**Canvas infinito:**
- **Zoom infinito**: Smooth zoom con pinch/scroll
- **Minimap**: Preview de toda la página en esquina
- **Pan handles**: Spacebar + drag para navegar
- **Frame selection**: Select múltiple con Shift+Click

**Paneles contextuales:**
- **Properties panel**: Cambia según selección (texto, forma, frame)
- **Layers panel**: Árbol colapsable con iconos + visibility toggles
- **Assets panel**: Componentes reutilizables con preview thumbnails
- **Plugins panel**: Marketplace integrado con ratings

**Sistema de componentes:**
- **Variants**: Componente con múltiples estados (hover, active, disabled)
- **Auto layout**: Flexbox visual con padding/gap configurable
- **Constraints**: Pins para responsive behavior
- **Styles**: Color, Text, Effect styles reutilizables

#### Colaboración en tiempo real

- **Cursors de otros usuarios**: Avatar + nombre + cursor con color único
- **Live comments**: Mensajes anclados a ubicación específica
- **Version history**: Timeline con thumbnails de cambios
- **Observation mode**: Seguir cursor de otro usuario

---

### 4. VS Code (2025)

**Versión actual**: Visual Studio Code 1.86

#### Patrones UI destacados

**Editor:**
- **Split editor**: Múltiples editores lado a lado o en grid
- **Breadcrumb navigation**: Path del archivo con dropdowns para navegar
- **Minimap**: Preview del código en scroll bar
- **Syntax highlighting**: Colores semánticos según lenguaje

**Paneles:**
- **Activity bar**: Iconos para Explorer, Search, Git, Debug, Extensions
- **Sidebar**: Contenido contextual según actividad seleccionada
- **Panel**: Terminal, Problems, Output, Debug Console en panel inferior
- **Status bar**: Info de línea/columna, lenguaje, encoding, Git branch

**Sistema de temas:**
- **Tokens semánticos**: `editor.background`, `editor.foreground`, `editor.lineHighlight`
- **Workbench colors**: `sideBar.background`, `statusBar.background`, etc.
- **Syntax tokens**: `keyword`, `string`, `comment`, `function.name`, etc.

```json
{
  "workbench.colorCustomizations": {
    "editor.background": "#1e1e1e",
    "editor.foreground": "#d4d4d4",
    "editor.lineHighlightBackground": "#2a2a2a",
    "sideBar.background": "#252526",
    "activityBar.background": "#333333"
  },
  "editor.tokenColorCustomizations": {
    "keywords": "#569cd6",
    "strings": "#ce9178",
    "functions": "#dcdcaa"
  }
}
```

**Command Palette (Cmd+Shift+P):**
- Búsqueda fuzzy de comandos
- Recently used commands al inicio
- Categorías: File, Edit, View, Terminal, Debug, etc.
- Keyboard shortcuts visibles al lado derecho

---

### 5. Obsidian (2025)

**Versión actual**: Obsidian 1.5

#### Patrones UI destacados

**Markdown-first:**
- **Live preview**: WYSIWYG editor que guarda Markdown
- **Graph view**: Visualización de enlaces entre notas
- **Backlinks panel**: Lista de notas que enlazan a la actual
- **Outline view**: TOC generado automáticamente

**Customización extrema:**
- **CSS snippets**: Usuario puede añadir CSS custom
- **Themes**: Marketplace con 200+ temas
- **Plugins community**: 1000+ plugins de comunidad
- **Hotkeys**: Rebind completo de shortcuts

**Layout flexible:**
- **Panes draggables**: Arrastrar tabs para reorganizar layout
- **Linked panes**: Scroll sincronizado entre panes
- **Popout windows**: Abrir nota en ventana separada
- **Workspace saves**: Guardar layout como workspace

---

### 6. Arc Browser (2024-2025)

**Versión actual**: Arc 1.23 (macOS)

#### Patrones UI destacados

**Sidebar vertical:**
- **Spaces**: Pestañas agrupadas por contexto (Work, Personal, etc.)
- **Pinned tabs**: Tabs permanentes en sidebar (como bookmarks)
- **Today tabs**: Tabs temporales que desaparecen al día siguiente
- **Tree structure**: Tabs organizadas en árbol colapsable

**Command bar (Cmd+T):**
- Búsqueda de tabs, historial, bookmarks, acciones
- Crear nueva tab con búsqueda directa
- Quick actions: "New note", "Open Gmail", etc.
- Categorías visuales con iconos

**Split view:**
- Dividir pantalla en 2-4 paneles
- Cada panel con URL independiente
- Layouts guardados como presets
- Sync entre paneles (scroll link)

---

## Tendencias de Diseño UI 2025-2026

### 1. Design Systems Modernos

#### Design Tokens

**Definición**: Variables de diseño centralizadas en JSON/YAML, exportadas a múltiples formatos.

```json
// tokens.json
{
  "color": {
    "brand": {
      "primary": { "value": "#3B82F6" },
      "secondary": { "value": "#6366F1" }
    },
    "semantic": {
      "success": { "value": "#10B981" },
      "error": { "value": "#EF4444" },
      "warning": { "value": "#F59E0B" }
    }
  },
  "spacing": {
    "xs": { "value": "4px" },
    "sm": { "value": "8px" },
    "md": { "value": "16px" },
    "lg": { "value": "24px" },
    "xl": { "value": "32px" }
  }
}
```

**Exportación a CSS:**

```css
:root {
  --color-brand-primary: #3B82F6;
  --color-brand-secondary: #6366F1;
  --color-semantic-success: #10B981;
  --spacing-xs: 4px;
  --spacing-md: 16px;
}
```

**Herramientas:**
- Style Dictionary (Amazon)
- Theo (Salesforce)
- Figma Tokens plugin

---

### 2. Sistemas de Temas (Light/Dark/Custom)

#### Estrategias modernas

**Opción 1: CSS Variables con data-theme**

```css
[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --border: #e0e0e0;
}

[data-theme="dark"] {
  --bg-primary: #1a1a1a;
  --bg-secondary: #2a2a2a;
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0a0;
  --border: #3a3a3a;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}
```

**Opción 2: Tailwind CSS con dark: variant**

```html
<div class="bg-white dark:bg-gray-900 text-black dark:text-white">
  <h1 class="text-blue-600 dark:text-blue-400">Title</h1>
</div>
```

**Opción 3: PrimeVue con Aura/Lara presets** (actual en Narrative Assistant)

```typescript
import { updatePreset, palette } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

// Cambiar preset
usePreset(Aura)

// Cambiar color primario
const colorPalette = palette('#3B82F6')
updatePreset(Aura, {
  semantic: {
    primary: colorPalette
  }
})
```

#### Best practices para dark mode

1. **No invertir colores directamente**: Diseñar paleta específica para dark
2. **Ajustar contraste**: WCAG AAA requiere ratio 7:1 para texto
3. **Reducir saturación**: Colores brillantes cansan en dark mode
4. **Evitar blanco/negro puros**: Usar grises muy claros/oscuros
5. **Considerar OLED**: Usar negro puro (`#000000`) para ahorrar batería

**Paletas recomendadas:**

```css
/* Light mode */
--bg-primary: #ffffff;
--bg-secondary: #f9fafb;
--text-primary: #111827;
--text-secondary: #6b7280;

/* Dark mode (no simple inversión) */
--bg-primary: #0f172a;  /* Slate 900 */
--bg-secondary: #1e293b; /* Slate 800 */
--text-primary: #f1f5f9; /* Slate 100 */
--text-secondary: #94a3b8; /* Slate 400 */
```

---

### 3. Accesibilidad (WCAG 2.2 AA/AAA)

#### Requisitos clave

**Contraste de color:**
- WCAG AA: Ratio mínimo 4.5:1 para texto normal
- WCAG AAA: Ratio mínimo 7:1 para texto normal
- Herramienta: Contrast Checker de WebAIM

**Navegación por teclado:**
- Todos los elementos interactivos accesibles con Tab
- Focus visible con outline (no `outline: none` sin alternativa)
- Skip links para saltar navegación
- Keyboard shortcuts documentados

**ARIA labels:**
- `aria-label` para iconos sin texto
- `aria-describedby` para descripciones adicionales
- `role="alert"` para mensajes importantes
- `aria-live="polite"` para actualizaciones dinámicas

**Ejemplo completo:**

```html
<button
  class="icon-button"
  aria-label="Cerrar diálogo"
  aria-describedby="close-hint"
>
  <i class="pi pi-times" aria-hidden="true"></i>
</button>
<span id="close-hint" class="sr-only">
  Atajo de teclado: Escape
</span>
```

**CSS para focus states:**

```css
.button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

/* Screen reader only (sr-only) */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

---

### 4. Micro-interacciones

#### Principios de animación

**Duración:**
- Rápida (< 150ms): Hover, active states
- Normal (200-300ms): Transiciones de componentes
- Lenta (400-500ms): Transiciones de páginas/modales

**Easing:**
- `ease-out`: Para elementos que aparecen (rápido inicio, lento final)
- `ease-in`: Para elementos que desaparecen (lento inicio, rápido final)
- `ease-in-out`: Para movimientos (lento inicio y final)
- `cubic-bezier`: Para efectos avanzados (bounce, elastic)

**Ejemplos de micro-interacciones:**

```css
/* 1. Button hover */
.button {
  transition: all 200ms ease-out;
}
.button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 2. Checkbox check */
.checkbox-icon {
  transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1);
}
.checkbox:checked + .checkbox-icon {
  transform: scale(1.1);
}

/* 3. Toast notification */
@keyframes slide-in-right {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
.toast {
  animation: slide-in-right 300ms ease-out;
}

/* 4. Loading spinner */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.spinner {
  animation: spin 1s linear infinite;
}

/* 5. Skeleton shimmer */
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}
.skeleton {
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 1000px 100%;
  animation: shimmer 2s infinite linear;
}
```

#### Reduced motion

**Respetar preferencias del usuario:**

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**JavaScript:**

```typescript
const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches

if (!prefersReducedMotion) {
  // Aplicar animaciones complejas
}
```

---

### 5. Command Palettes

#### Patrón estándar

**Activación:**
- Keyboard shortcut: `Cmd+K` (macOS) / `Ctrl+K` (Windows/Linux)
- Overlay modal con backdrop semi-transparente
- Foco automático en input de búsqueda

**Funcionalidades:**
- Búsqueda fuzzy de comandos
- Navegación por teclado (Arrow Up/Down, Enter)
- Categorías visibles (acciones, navegación, configuración)
- Comandos recientes al inicio
- Shortcuts visibles al lado derecho
- Preview del resultado (opcional)

**Ejemplo de implementación:**

```vue
<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :draggable="false"
    class="command-palette"
  >
    <input
      ref="searchInput"
      v-model="query"
      type="text"
      placeholder="Buscar comandos..."
      @keydown.down.prevent="selectNext"
      @keydown.up.prevent="selectPrevious"
      @keydown.enter.prevent="executeCommand"
      @keydown.esc="close"
    />

    <div class="results">
      <div
        v-for="(item, index) in filteredItems"
        :key="item.id"
        :class="['result-item', { active: index === selectedIndex }]"
        @click="executeCommand(item)"
        @mouseenter="selectedIndex = index"
      >
        <i :class="item.icon"></i>
        <span class="label">{{ item.label }}</span>
        <kbd v-if="item.shortcut">{{ item.shortcut }}</kbd>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

interface CommandItem {
  id: string
  label: string
  icon: string
  shortcut?: string
  action: () => void
  category: string
}

const visible = ref(false)
const query = ref('')
const selectedIndex = ref(0)
const searchInput = ref<HTMLInputElement>()

const commands: CommandItem[] = [
  {
    id: 'new-project',
    label: 'Nuevo proyecto',
    icon: 'pi pi-plus',
    shortcut: 'Ctrl+N',
    action: () => createProject(),
    category: 'Acciones'
  },
  // ... más comandos
]

const filteredItems = computed(() => {
  if (!query.value) return commands
  return commands.filter(cmd =>
    cmd.label.toLowerCase().includes(query.value.toLowerCase())
  )
})

function open() {
  visible.value = true
  setTimeout(() => searchInput.value?.focus(), 100)
}

function close() {
  visible.value = false
  query.value = ''
  selectedIndex.value = 0
}

function executeCommand(item?: CommandItem) {
  const cmd = item || filteredItems.value[selectedIndex.value]
  if (cmd) {
    cmd.action()
    close()
  }
}

// Keyboard shortcut global
onMounted(() => {
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      open()
    }
  })
})
</script>

<style scoped>
.command-palette {
  width: 600px;
  max-width: 90vw;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms;
}

.result-item.active {
  background-color: var(--p-primary-color);
  color: white;
}

.result-item kbd {
  margin-left: auto;
  padding: 2px 6px;
  background-color: var(--p-surface-100);
  border-radius: 4px;
  font-size: 0.85em;
}
</style>
```

---

### 6. Sidebars Colapsables

#### Patrones de diseño

**Opción 1: Toggle button con icono**

```html
<aside class="sidebar" :class="{ collapsed }">
  <button class="toggle" @click="collapsed = !collapsed">
    <i :class="collapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-left'"></i>
  </button>
  <nav><!-- contenido --></nav>
</aside>
```

```css
.sidebar {
  width: 280px;
  transition: width 300ms ease-out;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar.collapsed .label {
  opacity: 0;
  pointer-events: none;
}
```

**Opción 2: Hover para expandir**

```css
.sidebar {
  width: 60px;
  transition: width 200ms ease-out;
}

.sidebar:hover {
  width: 280px;
}
```

**Opción 3: Resize handle**

```html
<aside class="sidebar" ref="sidebar">
  <div class="resize-handle" @mousedown="startResize"></div>
  <nav><!-- contenido --></nav>
</aside>
```

```typescript
function startResize(e: MouseEvent) {
  const startX = e.clientX
  const startWidth = sidebar.value.offsetWidth

  function onMouseMove(e: MouseEvent) {
    const newWidth = startWidth + (e.clientX - startX)
    sidebar.value.style.width = `${Math.max(200, Math.min(newWidth, 500))}px`
  }

  function onMouseUp() {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
```

---

### 7. Panel Layouts

#### Patrones modernos

**Split panel (50/50 o 60/40):**

```css
.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  height: 100vh;
}

/* Responsive */
@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
}
```

**Three-column layout:**

```css
.layout {
  display: grid;
  grid-template-columns: 250px 1fr 300px;
  gap: 0;
  height: 100vh;
}

.sidebar-left { /* navegación */ }
.main-content { /* contenido principal */ }
.sidebar-right { /* detalles */ }
```

**Dashboard con widgets:**

```css
.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 20px;
}

.widget {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
```

---

## Análisis Comparativo

### Tabla de Características

| Herramienta | Sidebar colapsable | Command palette | Dark mode | Keyboard shortcuts | Inline suggestions | Export options | Analytics |
|-------------|-------------------|-----------------|-----------|-------------------|-------------------|----------------|-----------|
| **Grammarly** | ✅ (contextual) | ❌ | ✅ (refinado) | ⚠️ (básico) | ✅ (excelente) | ⚠️ (limitado) | ✅ (dashboard) |
| **ProWritingAid** | ✅ (multi-panel) | ❌ | ✅ | ✅ (extensivo) | ✅ (heat maps) | ✅ (PDF/HTML) | ✅ (gráficos) |
| **Scrivener** | ✅ (Inspector) | ❌ | ⚠️ (parcial) | ✅ (customizable) | ❌ | ✅ (compile) | ⚠️ (básico) |
| **Hemingway** | ❌ | ❌ | ❌ | ⚠️ (mínimo) | ✅ (color-coded) | ⚠️ (export) | ✅ (simple) |
| **AutoCrit** | ⚠️ (fixed) | ❌ | ⚠️ | ❌ | ⚠️ | ✅ (compare) | ✅ (benchmarks) |
| **Notion** | ✅ | ✅ (excelente) | ✅ (refinado) | ✅ (extensivo) | ❌ | ✅ (múltiples) | ❌ |
| **Linear** | ✅ | ✅ (ultra-rápido) | ✅ | ✅ (keyboard-first) | ❌ | ⚠️ | ✅ (insights) |
| **Figma** | ✅ (contextual) | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **VS Code** | ✅ | ✅ (completo) | ✅ (tokens) | ✅ (rebindable) | ✅ (IntelliSense) | ❌ | ❌ |
| **Obsidian** | ✅ (flexible) | ✅ (plugins) | ✅ (themes) | ✅ (customizable) | ⚠️ (plugins) | ✅ (Markdown) | ⚠️ (plugins) |

**Leyenda:**
- ✅ = Implementado y excelente
- ⚠️ = Implementado pero limitado
- ❌ = No implementado o inexistente

---

### Patrones UI más utilizados

**Top 10 patrones identificados:**

1. **Sidebar colapsable** (9/10 herramientas) - Navegación persistente pero no intrusiva
2. **Dark mode refinado** (8/10) - No solo inversión, sino paleta específica
3. **Keyboard shortcuts** (8/10) - Eficiencia para usuarios avanzados
4. **Inline suggestions** (6/10 literarias) - Feedback contextual sin interrumpir
5. **Command palette** (6/10 productividad) - Acceso rápido sin UI visible
6. **Split panel layout** (7/10) - Ver contenido + análisis simultáneamente
7. **Filtros avanzados** (8/10) - Categorizar y priorizar información
8. **Export múltiples formatos** (7/10) - PDF, Markdown, JSON, CSV
9. **Analytics/Dashboard** (6/10 literarias) - Métricas visuales de calidad
10. **Customización visual** (7/10) - Temas, colores, densidad

---

### Qué evitar (anti-patterns)

**Identificados en herramientas con mala UX:**

1. **Modales bloqueantes**: Interrumpen flujo, usar toasts o sidebars
2. **Animaciones excesivas**: Cansan y ralentizan, usar solo para feedback importante
3. **Colores puros**: Negro/Blanco/Rojo puros son agresivos, usar grises teñidos
4. **Tooltips lentos**: Delay > 500ms frustra, mantener < 300ms
5. **Shortcuts ocultos**: Documentar en UI (icono ? o Cmd+Shift+?)
6. **Loading genérico**: Spinners sin contexto, usar skeleton screens
7. **Errores técnicos**: Mensajes para usuarios, no stack traces
8. **Confirmaciones innecesarias**: Solo para acciones destructivas irreversibles
9. **Formularios largos**: Dividir en steps o usar inline editing
10. **Iconos sin labels**: Ambiguos, añadir tooltips o texto

---

## Recomendaciones para Narrative Assistant

### Implementación Prioritaria (P0)

#### 1. Mejorar Sistema de Temas Actual

**Estado actual:**
- ✅ Ya tiene theme store con PrimeVue presets (Aura, Lara, Material, Nora)
- ✅ Dark mode automático funcional
- ✅ Variables CSS para personalización

**Mejoras recomendadas:**

```typescript
// stores/theme.ts - añadir paletas específicas para alertas

export const ALERT_COLORS = {
  light: {
    critical: '#DC2626',    // Red 600
    high: '#EA580C',        // Orange 600
    medium: '#F59E0B',      // Amber 500
    low: '#3B82F6',         // Blue 500
    info: '#6366F1',        // Indigo 500
    success: '#10B981'      // Green 500
  },
  dark: {
    critical: '#FCA5A5',    // Red 300 (más suave en dark)
    high: '#FDBA74',        // Orange 300
    medium: '#FCD34D',      // Amber 300
    low: '#60A5FA',         // Blue 400
    info: '#818CF8',        // Indigo 400
    success: '#34D399'      // Green 400
  }
}

// Aplicar dinámicamente según modo
function applyAlertColors() {
  const colors = isDark.value ? ALERT_COLORS.dark : ALERT_COLORS.light
  Object.entries(colors).forEach(([key, value]) => {
    document.documentElement.style.setProperty(`--alert-${key}`, value)
  })
}
```

**CSS mejorado para alertas:**

```css
/* frontend/src/assets/themes.css */

/* Alert severity colors - dinámicos */
.alert-critical {
  background-color: var(--alert-critical-bg);
  border-left: 4px solid var(--alert-critical);
  color: var(--alert-critical-text);
}

[data-theme="light"] {
  --alert-critical: #DC2626;
  --alert-critical-bg: #FEE2E2;
  --alert-critical-text: #991B1B;
}

[data-theme="dark"] {
  --alert-critical: #FCA5A5;
  --alert-critical-bg: #7F1D1D;
  --alert-critical-text: #FEE2E2;
}
```

---

#### 2. Implementar Command Palette

**Integración con UI existente:**

```typescript
// composables/useCommandPalette.ts
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'

export interface Command {
  id: string
  label: string
  description?: string
  icon: string
  shortcut?: string
  action: () => void
  category: 'navigation' | 'actions' | 'settings'
  keywords: string[]
}

export function useCommandPalette() {
  const router = useRouter()
  const projectsStore = useProjectsStore()

  const commands = computed<Command[]>(() => [
    // Navegación
    {
      id: 'nav-home',
      label: 'Ir a Inicio',
      icon: 'pi pi-home',
      category: 'navigation',
      keywords: ['home', 'inicio', 'dashboard'],
      action: () => router.push('/')
    },
    {
      id: 'nav-projects',
      label: 'Ver Proyectos',
      icon: 'pi pi-folder',
      category: 'navigation',
      keywords: ['proyectos', 'projects', 'lista'],
      action: () => router.push('/projects')
    },

    // Acciones
    {
      id: 'new-project',
      label: 'Nuevo Proyecto',
      icon: 'pi pi-plus',
      shortcut: 'Ctrl+N',
      category: 'actions',
      keywords: ['nuevo', 'crear', 'proyecto'],
      action: () => projectsStore.showCreateDialog = true
    },
    {
      id: 'analyze-current',
      label: 'Analizar Proyecto Actual',
      icon: 'pi pi-play',
      shortcut: 'Ctrl+R',
      category: 'actions',
      keywords: ['analizar', 'ejecutar', 'run'],
      action: () => projectsStore.analyzeCurrentProject()
    },

    // Configuración
    {
      id: 'settings',
      label: 'Configuración',
      icon: 'pi pi-cog',
      shortcut: 'Ctrl+,',
      category: 'settings',
      keywords: ['configuración', 'settings', 'preferencias'],
      action: () => router.push('/settings')
    },
    {
      id: 'toggle-theme',
      label: 'Cambiar Tema',
      icon: 'pi pi-moon',
      shortcut: 'Ctrl+Shift+T',
      category: 'settings',
      keywords: ['tema', 'theme', 'dark', 'oscuro'],
      action: () => useThemeStore().toggleMode()
    }
  ])

  return {
    commands
  }
}
```

**Componente CommandPalette.vue:**

```vue
<template>
  <Dialog
    v-model:visible="visible"
    :modal="true"
    :closable="false"
    :draggable="false"
    class="command-palette-dialog"
    @show="onShow"
    @hide="onHide"
  >
    <template #header>
      <div class="palette-header">
        <i class="pi pi-search"></i>
        <InputText
          ref="searchInput"
          v-model="query"
          placeholder="Buscar comando o acción..."
          class="palette-input"
          @keydown="handleKeydown"
        />
        <kbd class="escape-hint">ESC para cerrar</kbd>
      </div>
    </template>

    <div class="results-container">
      <div
        v-for="(category, categoryName) in groupedResults"
        :key="categoryName"
        class="results-category"
      >
        <div class="category-label">{{ categoryLabels[categoryName] }}</div>
        <div
          v-for="(cmd, index) in category"
          :key="cmd.id"
          :class="['result-item', { active: isSelected(cmd) }]"
          @click="executeCommand(cmd)"
          @mouseenter="selectedCommand = cmd"
        >
          <i :class="cmd.icon"></i>
          <div class="result-content">
            <span class="result-label">{{ cmd.label }}</span>
            <span v-if="cmd.description" class="result-description">
              {{ cmd.description }}
            </span>
          </div>
          <kbd v-if="cmd.shortcut" class="result-shortcut">
            {{ cmd.shortcut }}
          </kbd>
        </div>
      </div>

      <div v-if="filteredCommands.length === 0" class="no-results">
        <i class="pi pi-search"></i>
        <p>No se encontraron comandos</p>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
// ... implementación completa en archivo separado
</script>

<style scoped>
.command-palette-dialog {
  width: 640px;
  max-width: 90vw;
}

.palette-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.palette-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1.1rem;
}

.escape-hint {
  background: var(--p-surface-200);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 150ms;
}

.result-item:hover,
.result-item.active {
  background-color: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.result-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-label {
  font-weight: 500;
}

.result-description {
  font-size: 0.85rem;
  opacity: 0.7;
}

.result-shortcut {
  background: var(--p-surface-100);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}
</style>
```

**Integración en App.vue:**

```vue
<template>
  <div id="app">
    <MenuBar />
    <RouterView />
    <CommandPalette />
    <!-- ... otros diálogos -->
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import CommandPalette from '@/components/CommandPalette.vue'

onMounted(() => {
  // Global shortcut para abrir command palette
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('command-palette:open'))
    }
  })
})
</script>
```

---

#### 3. Mejorar DocumentViewer con Inline Suggestions

**Estado actual:**
- DocumentViewer muestra highlights de alertas
- Click en alerta muestra detalles en panel lateral

**Mejoras estilo Grammarly:**

```vue
<!-- components/DocumentViewer.vue -->
<template>
  <div class="document-viewer">
    <div class="document-content" ref="contentRef">
      <p v-for="(paragraph, index) in paragraphs" :key="index">
        <span
          v-for="(segment, segIndex) in getSegmentsWithHighlights(paragraph)"
          :key="segIndex"
          :class="segment.alertClass"
          :data-alert-id="segment.alertId"
          @mouseenter="showInlineSuggestion($event, segment)"
          @mouseleave="hideInlineSuggestion"
          @click="selectAlert(segment.alertId)"
        >
          {{ segment.text }}
        </span>
      </p>
    </div>

    <!-- Inline suggestion tooltip (estilo Grammarly) -->
    <Popover
      ref="suggestionPopover"
      :target="popoverTarget"
      position="bottom"
      class="inline-suggestion"
    >
      <div v-if="currentAlert" class="suggestion-content">
        <div class="suggestion-header">
          <Badge :severity="getSeverityBadge(currentAlert.severity)">
            {{ currentAlert.category }}
          </Badge>
          <Button
            icon="pi pi-times"
            text
            size="small"
            @click="hideInlineSuggestion"
          />
        </div>

        <p class="suggestion-message">{{ currentAlert.message }}</p>

        <div v-if="currentAlert.suggestion" class="suggestion-fix">
          <strong>Sugerencia:</strong>
          <code>{{ currentAlert.suggestion }}</code>
        </div>

        <div class="suggestion-actions">
          <Button
            label="Aplicar"
            icon="pi pi-check"
            size="small"
            @click="applyFix(currentAlert)"
          />
          <Button
            label="Ignorar"
            icon="pi pi-times"
            text
            size="small"
            @click="dismissAlert(currentAlert)"
          />
        </div>
      </div>
    </Popover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const contentRef = ref<HTMLElement>()
const suggestionPopover = ref()
const popoverTarget = ref<HTMLElement>()
const currentAlert = ref<Alert>()

function showInlineSuggestion(event: MouseEvent, segment: Segment) {
  if (!segment.alertId) return

  currentAlert.value = alertsStore.getAlertById(segment.alertId)
  popoverTarget.value = event.target as HTMLElement

  setTimeout(() => {
    suggestionPopover.value?.show()
  }, 200) // Delay para evitar flickering
}

function hideInlineSuggestion() {
  suggestionPopover.value?.hide()
  currentAlert.value = undefined
}

function applyFix(alert: Alert) {
  // Implementar aplicación de fix
  alertsStore.applyFix(alert.id)
  hideInlineSuggestion()
}

function dismissAlert(alert: Alert) {
  alertsStore.dismissAlert(alert.id)
  hideInlineSuggestion()
}
</script>

<style scoped>
/* Highlight colors por severidad */
.highlight-critical {
  background-color: var(--alert-critical-bg);
  border-bottom: 2px solid var(--alert-critical);
  cursor: pointer;
  transition: background-color 150ms;
}

.highlight-critical:hover {
  background-color: var(--alert-critical-hover);
}

/* Similar para high, medium, low */

.inline-suggestion {
  max-width: 400px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.suggestion-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.suggestion-message {
  font-size: 0.95rem;
  line-height: 1.5;
}

.suggestion-fix {
  background: var(--p-surface-100);
  padding: 10px;
  border-radius: 6px;
  border-left: 3px solid var(--p-primary-color);
}

.suggestion-fix code {
  display: block;
  margin-top: 6px;
  font-family: 'Courier New', monospace;
  color: var(--p-text-color);
}

.suggestion-actions {
  display: flex;
  gap: 8px;
}
</style>
```

---

#### 4. Añadir Analytics Dashboard

**Inspirado en Grammarly + ProWritingAid:**

```vue
<!-- views/AnalyticsDashboardView.vue -->
<template>
  <div class="analytics-view">
    <div class="analytics-header">
      <h1>Análisis de Calidad</h1>
      <Dropdown
        v-model="selectedTimeRange"
        :options="timeRanges"
        optionLabel="label"
        optionValue="value"
      />
    </div>

    <div class="analytics-grid">
      <!-- 1. Score general -->
      <Card class="score-card">
        <template #title>Puntuación General</template>
        <template #content>
          <div class="score-display">
            <CircularProgress
              :value="overallScore"
              :max="100"
              :size="180"
              :strokeWidth="12"
            />
            <div class="score-label">
              <span class="score-value">{{ overallScore }}</span>
              <span class="score-max">/100</span>
            </div>
          </div>
          <div class="score-breakdown">
            <div class="metric">
              <i class="pi pi-check-circle" style="color: var(--alert-success)"></i>
              <span>{{ resolvedAlerts }} alertas resueltas</span>
            </div>
            <div class="metric">
              <i class="pi pi-exclamation-triangle" style="color: var(--alert-medium)"></i>
              <span>{{ pendingAlerts }} pendientes</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- 2. Alertas por categoría -->
      <Card class="chart-card">
        <template #title>Alertas por Categoría</template>
        <template #content>
          <Chart
            type="doughnut"
            :data="alertsByCategoryData"
            :options="chartOptions"
          />
        </template>
      </Card>

      <!-- 3. Tendencia temporal -->
      <Card class="chart-card full-width">
        <template #title>Progreso en el Tiempo</template>
        <template #content>
          <Chart
            type="line"
            :data="progressOverTimeData"
            :options="lineChartOptions"
          />
        </template>
      </Card>

      <!-- 4. Top problemas -->
      <Card class="top-issues-card">
        <template #title>Problemas Más Frecuentes</template>
        <template #content>
          <DataTable :value="topIssues" :rows="5">
            <Column field="issue" header="Tipo"></Column>
            <Column field="count" header="Cantidad">
              <template #body="slotProps">
                <Badge :value="slotProps.data.count" severity="warning" />
              </template>
            </Column>
            <Column field="avgSeverity" header="Gravedad Promedio">
              <template #body="slotProps">
                <ProgressBar
                  :value="slotProps.data.avgSeverity * 25"
                  :showValue="false"
                />
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>

      <!-- 5. Estadísticas de entidades -->
      <Card class="entities-stats-card">
        <template #title>Análisis de Personajes</template>
        <template #content>
          <div class="stats-grid">
            <div class="stat">
              <i class="pi pi-users"></i>
              <div>
                <div class="stat-value">{{ totalCharacters }}</div>
                <div class="stat-label">Personajes</div>
              </div>
            </div>
            <div class="stat">
              <i class="pi pi-map-marker"></i>
              <div>
                <div class="stat-value">{{ totalLocations }}</div>
                <div class="stat-label">Ubicaciones</div>
              </div>
            </div>
            <div class="stat">
              <i class="pi pi-link"></i>
              <div>
                <div class="stat-value">{{ totalRelationships }}</div>
                <div class="stat-label">Relaciones</div>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- 6. Mejoras recientes -->
      <Card class="improvements-card full-width">
        <template #title>Mejoras Aplicadas</template>
        <template #content>
          <Timeline :value="recentImprovements">
            <template #content="slotProps">
              <div class="timeline-item">
                <strong>{{ slotProps.item.title }}</strong>
                <p>{{ slotProps.item.description }}</p>
                <small>{{ formatDate(slotProps.item.date) }}</small>
              </div>
            </template>
          </Timeline>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useAlertsStore } from '@/stores/alerts'
import Chart from 'primevue/chart'
import CircularProgress from '@/components/CircularProgress.vue'

const projectsStore = useProjectsStore()
const alertsStore = useAlertsStore()

const selectedTimeRange = ref('all')
const timeRanges = [
  { label: 'Todo el tiempo', value: 'all' },
  { label: 'Última semana', value: '7d' },
  { label: 'Último mes', value: '30d' }
]

// Computed properties
const overallScore = computed(() => {
  // Calcular score basado en alertas resueltas vs totales
  const total = alertsStore.alerts.length
  const resolved = alertsStore.alerts.filter(a => a.status === 'resolved').length
  return total > 0 ? Math.round((resolved / total) * 100) : 100
})

const resolvedAlerts = computed(() =>
  alertsStore.alerts.filter(a => a.status === 'resolved').length
)

const pendingAlerts = computed(() =>
  alertsStore.alerts.filter(a => a.status === 'open').length
)

const alertsByCategoryData = computed(() => {
  const categories = alertsStore.getAlertsByCategory()
  return {
    labels: Object.keys(categories),
    datasets: [{
      data: Object.values(categories).map(alerts => alerts.length),
      backgroundColor: [
        'var(--alert-critical)',
        'var(--alert-high)',
        'var(--alert-medium)',
        'var(--alert-low)',
        'var(--alert-info)'
      ]
    }]
  }
})

// ... más computed properties
</script>

<style scoped>
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  padding: 20px;
}

.full-width {
  grid-column: 1 / -1;
}

.score-display {
  position: relative;
  display: flex;
  justify-content: center;
  margin: 20px 0;
}

.score-label {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.score-value {
  font-size: 3rem;
  font-weight: 700;
  color: var(--p-primary-color);
}

.score-max {
  font-size: 1.5rem;
  color: var(--p-text-muted-color);
}

.score-breakdown {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 20px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
```

---

### Implementación Media Prioridad (P1)

#### 5. Atajos de Teclado Globales

**Documentación inline:**

```vue
<!-- components/KeyboardShortcutsDialog.vue -->
<template>
  <Dialog v-model:visible="visible" modal header="Atajos de Teclado">
    <div class="shortcuts-grid">
      <div v-for="category in categories" :key="category.name" class="category">
        <h3>{{ category.name }}</h3>
        <div class="shortcuts-list">
          <div v-for="shortcut in category.shortcuts" :key="shortcut.key" class="shortcut-item">
            <div class="shortcut-keys">
              <kbd v-for="key in shortcut.keys" :key="key">{{ key }}</kbd>
            </div>
            <span class="shortcut-description">{{ shortcut.description }}</span>
          </div>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
const categories = [
  {
    name: 'General',
    shortcuts: [
      { keys: ['Ctrl', 'K'], description: 'Abrir paleta de comandos' },
      { keys: ['Ctrl', 'N'], description: 'Nuevo proyecto' },
      { keys: ['Ctrl', 'S'], description: 'Guardar cambios' },
      { keys: ['Ctrl', ','], description: 'Abrir configuración' },
      { keys: ['?'], description: 'Mostrar esta ayuda' }
    ]
  },
  {
    name: 'Navegación',
    shortcuts: [
      { keys: ['Ctrl', '1-9'], description: 'Ir a proyecto #N' },
      { keys: ['Alt', '←'], description: 'Volver' },
      { keys: ['Alt', '→'], description: 'Adelante' },
      { keys: ['Ctrl', 'B'], description: 'Toggle sidebar' }
    ]
  },
  {
    name: 'Análisis',
    shortcuts: [
      { keys: ['Ctrl', 'R'], description: 'Ejecutar análisis' },
      { keys: ['Ctrl', 'Shift', 'R'], description: 'Re-analizar' },
      { keys: ['Tab'], description: 'Siguiente alerta' },
      { keys: ['Shift', 'Tab'], description: 'Alerta anterior' },
      { keys: ['Enter'], description: 'Ver detalles' },
      { keys: ['D'], description: 'Descartar alerta' },
      { keys: ['R'], description: 'Resolver alerta' }
    ]
  },
  {
    name: 'Vista',
    shortcuts: [
      { keys: ['Ctrl', 'Shift', 'T'], description: 'Cambiar tema' },
      { keys: ['Ctrl', '+'], description: 'Aumentar zoom' },
      { keys: ['Ctrl', '-'], description: 'Disminuir zoom' },
      { keys: ['Ctrl', '0'], description: 'Resetear zoom' }
    ]
  }
]
</script>

<style scoped>
.shortcuts-grid {
  display: grid;
  gap: 30px;
}

.category h3 {
  margin-bottom: 15px;
  color: var(--p-primary-color);
}

.shortcuts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: 15px;
}

.shortcut-keys {
  display: flex;
  gap: 4px;
  min-width: 150px;
}

.shortcut-keys kbd {
  background: var(--p-surface-100);
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  padding: 4px 8px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 2px 0 var(--p-surface-200);
}

.shortcut-description {
  color: var(--p-text-color);
}
</style>
```

**Sistema global de shortcuts:**

```typescript
// composables/useKeyboardShortcuts.ts
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useThemeStore } from '@/stores/theme'

interface ShortcutHandler {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  handler: (e: KeyboardEvent) => void
  description: string
  category: string
}

export function useKeyboardShortcuts() {
  const router = useRouter()
  const projectsStore = useProjectsStore()
  const themeStore = useThemeStore()

  const shortcuts: ShortcutHandler[] = [
    // General
    {
      key: 'k',
      ctrl: true,
      handler: (e) => {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('command-palette:open'))
      },
      description: 'Abrir paleta de comandos',
      category: 'General'
    },
    {
      key: 'n',
      ctrl: true,
      handler: (e) => {
        e.preventDefault()
        projectsStore.showCreateDialog = true
      },
      description: 'Nuevo proyecto',
      category: 'General'
    },
    {
      key: '?',
      handler: () => {
        window.dispatchEvent(new CustomEvent('keyboard:show-help'))
      },
      description: 'Mostrar ayuda de atajos',
      category: 'General'
    },

    // Navegación
    {
      key: 'ArrowLeft',
      alt: true,
      handler: () => router.back(),
      description: 'Volver',
      category: 'Navegación'
    },
    {
      key: 'ArrowRight',
      alt: true,
      handler: () => router.forward(),
      description: 'Adelante',
      category: 'Navegación'
    },

    // Tema
    {
      key: 't',
      ctrl: true,
      shift: true,
      handler: (e) => {
        e.preventDefault()
        themeStore.toggleMode()
      },
      description: 'Cambiar tema',
      category: 'Vista'
    },

    // Análisis
    {
      key: 'r',
      ctrl: true,
      handler: (e) => {
        e.preventDefault()
        projectsStore.analyzeCurrentProject()
      },
      description: 'Ejecutar análisis',
      category: 'Análisis'
    }
  ]

  function handleKeydown(e: KeyboardEvent) {
    // Ignorar si está en input/textarea
    const target = e.target as HTMLElement
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      return
    }

    for (const shortcut of shortcuts) {
      const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : !e.ctrlKey && !e.metaKey
      const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey
      const altMatch = shortcut.alt ? e.altKey : !e.altKey

      if (
        e.key === shortcut.key &&
        ctrlMatch &&
        shiftMatch &&
        altMatch
      ) {
        shortcut.handler(e)
        break
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })

  return {
    shortcuts
  }
}
```

---

#### 6. Export Mejorado con Preview

**Inspirado en ProWritingAid:**

```vue
<!-- components/ExportDialog.vue - mejora -->
<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Exportar Informe"
    style="width: 800px"
  >
    <div class="export-layout">
      <!-- Panel izquierdo: Opciones -->
      <div class="export-options">
        <div class="option-section">
          <h3>Formato</h3>
          <SelectButton
            v-model="selectedFormat"
            :options="formats"
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div class="option-section">
          <h3>Incluir</h3>
          <div class="checkboxes">
            <Checkbox
              v-model="includeEntities"
              inputId="include-entities"
              binary
            />
            <label for="include-entities">Entidades y atributos</label>
          </div>
          <div class="checkboxes">
            <Checkbox
              v-model="includeRelationships"
              inputId="include-relationships"
              binary
            />
            <label for="include-relationships">Grafo de relaciones</label>
          </div>
          <div class="checkboxes">
            <Checkbox
              v-model="includeAlerts"
              inputId="include-alerts"
              binary
            />
            <label for="include-alerts">Alertas</label>
          </div>
          <div class="checkboxes">
            <Checkbox
              v-model="includeAnalytics"
              inputId="include-analytics"
              binary
            />
            <label for="include-analytics">Análisis estadístico</label>
          </div>
        </div>

        <div class="option-section">
          <h3>Filtros de Alertas</h3>
          <MultiSelect
            v-model="selectedSeverities"
            :options="severities"
            optionLabel="label"
            optionValue="value"
            placeholder="Todas las severidades"
          />
          <MultiSelect
            v-model="selectedCategories"
            :options="categories"
            optionLabel="label"
            optionValue="value"
            placeholder="Todas las categorías"
          />
        </div>
      </div>

      <!-- Panel derecho: Preview -->
      <div class="export-preview">
        <div class="preview-header">
          <h3>Vista Previa</h3>
          <Button
            icon="pi pi-refresh"
            text
            @click="regeneratePreview"
          />
        </div>
        <div class="preview-content" v-html="previewContent"></div>
      </div>
    </div>

    <template #footer>
      <div class="export-footer">
        <div class="export-size">
          Tamaño estimado: {{ estimatedSize }}
        </div>
        <div class="export-actions">
          <Button label="Cancelar" text @click="visible = false" />
          <Button
            label="Exportar"
            icon="pi pi-download"
            @click="handleExport"
            :loading="exporting"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'

const visible = defineModel<boolean>('visible')

const selectedFormat = ref('markdown')
const includeEntities = ref(true)
const includeRelationships = ref(true)
const includeAlerts = ref(true)
const includeAnalytics = ref(false)
const selectedSeverities = ref(['critical', 'high', 'medium'])
const selectedCategories = ref([])
const exporting = ref(false)

const formats = [
  { label: 'Markdown', value: 'markdown' },
  { label: 'PDF', value: 'pdf' },
  { label: 'HTML', value: 'html' },
  { label: 'JSON', value: 'json' }
]

// Preview content generado dinámicamente
const previewContent = computed(() => {
  const content = generateMarkdownReport({
    includeEntities: includeEntities.value,
    includeRelationships: includeRelationships.value,
    includeAlerts: includeAlerts.value,
    includeAnalytics: includeAnalytics.value,
    severities: selectedSeverities.value,
    categories: selectedCategories.value
  })

  return selectedFormat.value === 'markdown'
    ? marked(content)
    : content
})

const estimatedSize = computed(() => {
  const bytes = new Blob([previewContent.value]).size
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`
})

function generateMarkdownReport(options: ExportOptions): string {
  // Generar Markdown basado en opciones
  let report = `# Informe de Análisis - ${project.name}\n\n`
  report += `Generado: ${new Date().toLocaleString()}\n\n---\n\n`

  if (options.includeAnalytics) {
    report += `## Resumen Estadístico\n\n`
    report += `- **Palabras totales**: ${project.wordCount}\n`
    report += `- **Capítulos**: ${project.chapters.length}\n`
    report += `- **Personajes**: ${project.entitiesCount}\n\n`
  }

  if (options.includeEntities) {
    report += `## Entidades\n\n`
    // ... generar tabla de entidades
  }

  // ... más secciones

  return report
}

async function handleExport() {
  exporting.value = true

  try {
    const response = await fetch(
      `/api/projects/${project.id}/export/report?format=${selectedFormat.value}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          includeEntities: includeEntities.value,
          includeRelationships: includeRelationships.value,
          includeAlerts: includeAlerts.value,
          severities: selectedSeverities.value,
          categories: selectedCategories.value
        })
      }
    )

    if (!response.ok) throw new Error('Export failed')

    // Descargar archivo
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `informe-${project.name}.${selectedFormat.value}`
    a.click()
    window.URL.revokeObjectURL(url)

    toast.add({
      severity: 'success',
      summary: 'Exportación completa',
      detail: 'El informe se ha descargado correctamente',
      life: 3000
    })

    visible.value = false
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error al exportar',
      detail: error.message,
      life: 5000
    })
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.export-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  height: 600px;
}

.export-options {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  padding-right: 10px;
}

.option-section h3 {
  margin-bottom: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--p-text-secondary-color);
}

.checkboxes {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.export-preview {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--p-surface-border);
  border-radius: 8px;
  overflow: hidden;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--p-surface-100);
  border-bottom: 1px solid var(--p-surface-border);
}

.preview-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: var(--p-surface-0);
  font-size: 0.9rem;
  line-height: 1.6;
}

.export-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.export-size {
  font-size: 0.85rem;
  color: var(--p-text-secondary-color);
}

.export-actions {
  display: flex;
  gap: 10px;
}
</style>
```

---

### Implementación Baja Prioridad (P2)

#### 7. Micro-interacciones Refinadas

**Añadir transiciones suaves:**

```css
/* frontend/src/assets/main.css */

/* ============================
   Micro-interacciones globales
   ============================ */

/* Transiciones por defecto */
* {
  transition-property: background-color, border-color, color, fill, stroke, opacity, box-shadow, transform;
  transition-duration: 200ms;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
}

/* Hover elevación en cards */
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
}

/* Ripple effect en botones */
.button {
  position: relative;
  overflow: hidden;
}

.button::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.button:active::before {
  width: 300px;
  height: 300px;
}

/* Skeleton shimmer effect */
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.skeleton {
  background: linear-gradient(
    90deg,
    var(--p-surface-200) 25%,
    var(--p-surface-100) 50%,
    var(--p-surface-200) 75%
  );
  background-size: 1000px 100%;
  animation: shimmer 2s infinite linear;
  border-radius: 4px;
}

/* Toast slide-in animations */
@keyframes slide-in-right {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slide-out-right {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

.p-toast-message {
  animation: slide-in-right 300ms ease-out;
}

.p-toast-message-leave-active {
  animation: slide-out-right 300ms ease-in;
}

/* Focus states mejorados */
:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(var(--p-primary-color-rgb), 0.2);
}

/* Loading spinner con bounce */
@keyframes bounce {
  0%, 100% {
    transform: scale(0);
  }
  50% {
    transform: scale(1);
  }
}

.loading-dot {
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }

/* Checkbox check animation */
@keyframes check {
  0% {
    transform: scale(0) rotate(45deg);
  }
  50% {
    transform: scale(1.2) rotate(45deg);
  }
  100% {
    transform: scale(1) rotate(45deg);
  }
}

.checkbox-checked .checkbox-icon {
  animation: check 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* Progress bar fill animation */
@keyframes progress-fill {
  from {
    transform: scaleX(0);
    transform-origin: left;
  }
  to {
    transform: scaleX(1);
    transform-origin: left;
  }
}

.progress-bar-value {
  animation: progress-fill 600ms ease-out;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

#### 8. Empty States Ilustrados

**Inspirado en Notion:**

```vue
<!-- components/EmptyState.vue -->
<template>
  <div class="empty-state">
    <div class="empty-illustration">
      <component :is="illustration" />
    </div>
    <h2 class="empty-title">{{ title }}</h2>
    <p class="empty-description">{{ description }}</p>
    <div v-if="$slots.actions" class="empty-actions">
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Ilustraciones SVG inline
import EmptyProjectsIcon from '@/assets/illustrations/empty-projects.svg?component'
import EmptyAlertsIcon from '@/assets/illustrations/empty-alerts.svg?component'
import EmptyEntitiesIcon from '@/assets/illustrations/empty-entities.svg?component'

interface Props {
  type: 'projects' | 'alerts' | 'entities' | 'custom'
  title: string
  description: string
}

const props = defineProps<Props>()

const illustration = computed(() => {
  switch (props.type) {
    case 'projects': return EmptyProjectsIcon
    case 'alerts': return EmptyAlertsIcon
    case 'entities': return EmptyEntitiesIcon
    default: return EmptyProjectsIcon
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-illustration {
  width: 200px;
  height: 200px;
  margin-bottom: 24px;
  opacity: 0.8;
}

.empty-illustration svg {
  width: 100%;
  height: 100%;
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--p-text-color);
}

.empty-description {
  font-size: 1rem;
  color: var(--p-text-secondary-color);
  max-width: 400px;
  line-height: 1.6;
  margin-bottom: 24px;
}

.empty-actions {
  display: flex;
  gap: 12px;
}
</style>
```

**Uso:**

```vue
<!-- ProjectsView.vue -->
<EmptyState
  v-if="projects.length === 0"
  type="projects"
  title="No hay proyectos"
  description="Crea tu primer proyecto para empezar a analizar manuscritos"
>
  <template #actions>
    <Button
      label="Nuevo Proyecto"
      icon="pi pi-plus"
      @click="showCreateDialog = true"
    />
    <Button
      label="Ver Tutorial"
      icon="pi pi-question-circle"
      text
      @click="showTutorial"
    />
  </template>
</EmptyState>
```

---

## Referencias y Recursos

### Herramientas Analizadas

**Corrección Literaria:**
1. **Grammarly** - https://www.grammarly.com/
2. **ProWritingAid** - https://prowritingaid.com/
3. **Scrivener** - https://www.literatureandlatte.com/scrivener/
4. **Hemingway Editor** - https://hemingwayapp.com/
5. **AutoCrit** - https://www.autocrit.com/

**Productividad:**
6. **Notion** - https://www.notion.so/
7. **Linear** - https://linear.app/
8. **Figma** - https://www.figma.com/
9. **VS Code** - https://code.visualstudio.com/
10. **Obsidian** - https://obsidian.md/
11. **Arc Browser** - https://arc.net/

### Design Systems & Recursos

**Design Systems públicos:**
- [Material Design 3](https://m3.material.io/) - Google
- [Fluent 2](https://fluent2.microsoft.design/) - Microsoft
- [Carbon Design System](https://carbondesignsystem.com/) - IBM
- [Atlassian Design System](https://atlassian.design/) - Atlassian
- [Polaris](https://polaris.shopify.com/) - Shopify

**Herramientas:**
- [Style Dictionary](https://amzn.github.io/style-dictionary/) - Design tokens
- [Radix UI](https://www.radix-ui.com/) - Componentes accesibles headless
- [Headless UI](https://headlessui.com/) - Tailwind Labs
- [Framer Motion](https://www.framer.com/motion/) - Animaciones React
- [Motion One](https://motion.dev/) - Animaciones vanilla JS

**Recursos de color:**
- [Tailwind Colors](https://tailwindcss.com/docs/customizing-colors) - Paletas
- [Coolors](https://coolors.co/) - Generador de paletas
- [Contrast Checker](https://webaim.org/resources/contrastchecker/) - WCAG
- [Color Hunt](https://colorhunt.co/) - Inspiración

**Tipografía:**
- [Inter](https://rsms.me/inter/) - Sans-serif UI moderna
- [IBM Plex](https://www.ibm.com/plex/) - Sistema completo
- [Source Code Pro](https://adobe-fonts.github.io/source-code-pro/) - Monospace

### Accesibilidad

**Guidelines:**
- [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/) - W3C
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/) - Patrones

**Testing:**
- [axe DevTools](https://www.deque.com/axe/devtools/) - Browser extension
- [WAVE](https://wave.webaim.org/) - Web accessibility evaluation
- [Pa11y](https://pa11y.org/) - Automated testing

### Documentación Técnica

**Vue 3:**
- [Vue 3 Docs](https://vuejs.org/)
- [Vue Router](https://router.vuejs.org/)
- [Pinia](https://pinia.vuejs.org/)

**PrimeVue:**
- [PrimeVue 4 Docs](https://primevue.org/)
- [Aura Theme](https://primevue.org/theming/styled/#aura)
- [Theme Designer](https://designer.primevue.org/)

**CSS:**
- [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [CSS Grid](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [CSS Animations](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations/Using_CSS_animations)

---

## Apéndice: Comparación Visual

### Sistemas de Color

**Grammarly:**
```css
--critical: #FF4D4F;
--warning: #FAAD14;
--info: #1890FF;
--success: #52C41A;
--bg-dark: #141414;
```

**ProWritingAid:**
```css
--error: #D32F2F;
--caution: #F57C00;
--suggestion: #1976D2;
--good: #388E3C;
--bg-dark: #1E1E1E;
```

**Notion:**
```css
--red: #EB5757;
--orange: #F2994A;
--yellow: #F2C94C;
--green: #27AE60;
--blue: #2F80ED;
--purple: #BB6BD9;
--bg-dark: #191919;
```

**Linear:**
```css
--critical: #F04438;
--high: #F79009;
--medium: #FDB022;
--low: #2E90FA;
--bg-dark: #0D0D0D;
```

**Recomendación para Narrative Assistant:**
Combinar Grammarly (claros, legibles) + Linear (modernos) con ajustes para español.

```css
/* Sistema propuesto */
:root {
  /* Alertas - Light */
  --alert-critical: #DC2626;      /* Red 600 */
  --alert-high: #EA580C;          /* Orange 600 */
  --alert-medium: #F59E0B;        /* Amber 500 */
  --alert-low: #3B82F6;           /* Blue 500 */
  --alert-info: #6366F1;          /* Indigo 500 */
  --alert-success: #10B981;       /* Green 500 */

  /* Backgrounds - Light */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F9FAFB;
  --bg-tertiary: #F3F4F6;

  /* Text - Light */
  --text-primary: #111827;
  --text-secondary: #6B7280;
  --text-tertiary: #9CA3AF;

  /* Borders */
  --border-light: #E5E7EB;
  --border-medium: #D1D5DB;
}

[data-theme="dark"] {
  /* Alertas - Dark (más suaves) */
  --alert-critical: #FCA5A5;      /* Red 300 */
  --alert-high: #FDBA74;          /* Orange 300 */
  --alert-medium: #FCD34D;        /* Amber 300 */
  --alert-low: #60A5FA;           /* Blue 400 */
  --alert-info: #818CF8;          /* Indigo 400 */
  --alert-success: #34D399;       /* Green 400 */

  /* Backgrounds - Dark */
  --bg-primary: #0F172A;          /* Slate 900 */
  --bg-secondary: #1E293B;        /* Slate 800 */
  --bg-tertiary: #334155;         /* Slate 700 */

  /* Text - Dark */
  --text-primary: #F1F5F9;        /* Slate 100 */
  --text-secondary: #CBD5E1;      /* Slate 300 */
  --text-tertiary: #94A3B8;       /* Slate 400 */

  /* Borders */
  --border-light: #475569;        /* Slate 600 */
  --border-medium: #64748B;       /* Slate 500 */
}
```

---

## Conclusiones

### Top 5 Mejoras Prioritarias

1. **Command Palette (Cmd+K)** - Acceso rápido a toda funcionalidad
2. **Inline Suggestions mejoradas** - Estilo Grammarly con hover tooltips
3. **Analytics Dashboard** - Métricas visuales de calidad del manuscrito
4. **Sistema de color refinado** - Paletas específicas light/dark para alertas
5. **Keyboard shortcuts completos** - Documentación inline + handling global

### Patrones UI Clave Identificados

**Para Narrative Assistant:**
- ✅ **Sidebar colapsable** - Ya existe en DocumentViewer, expandir a otras vistas
- ✅ **Dark mode** - Ya implementado, refinar paletas de alertas
- 🔴 **Command palette** - No existe, implementar con prioridad P0
- 🔴 **Inline suggestions** - Parcial, mejorar con tooltips estilo Grammarly
- 🔴 **Analytics** - No existe, crear dashboard de métricas
- ✅ **Export** - Básico, mejorar con preview live
- ⚠️ **Keyboard shortcuts** - Básicos, expandir y documentar
- ✅ **Filtros avanzados** - Ya existe en AlertList/EntityList
- 🔴 **Micro-interacciones** - Mínimas, añadir animaciones sutiles
- ⚠️ **Empty states** - Básicos, mejorar con ilustraciones

**Leyenda:**
- ✅ = Ya implementado
- ⚠️ = Implementado parcialmente
- 🔴 = No implementado, prioritario

---

## Próximos Pasos

### Semana 1 (P0)
1. Implementar Command Palette básico (4h)
2. Refinar sistema de colores de alertas (2h)
3. Mejorar inline suggestions con tooltips (4h)

### Semana 2 (P1)
4. Crear Analytics Dashboard (8h)
5. Expandir keyboard shortcuts (4h)
6. Mejorar export con preview (4h)

### Semana 3 (P2)
7. Añadir micro-interacciones (4h)
8. Crear empty states ilustrados (4h)
9. Documentación UI completa (2h)

**Total estimado**: ~36 horas de desarrollo

---

**Fin del informe**

---

**Meta-nota**: Este informe se ha generado basándome en mi conocimiento hasta enero de 2025. Para información más actualizada de 2026, se recomienda realizar búsquedas web específicas con WebSearch cuando esté disponible.
