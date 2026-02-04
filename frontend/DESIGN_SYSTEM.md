# Narrative Assistant - Design System

**Version**: 1.0.0
**Last Updated**: 2026-01-13

Este documento define el sistema de diseno completo para Narrative Assistant, incluyendo tokens de diseno, componentes base y guias de implementacion.

---

## Tabla de Contenidos

1. [Tokens de Diseno](#1-tokens-de-diseno)
   - 1.1 [Colores](#11-colores)
   - 1.2 [Tipografia](#12-tipografia)
   - 1.3 [Espaciado](#13-espaciado)
   - 1.4 [Bordes y Sombras](#14-bordes-y-sombras)
   - 1.5 [Animaciones](#15-animaciones)
2. [Componentes Base](#2-componentes-base)
3. [Integracion con PrimeVue](#3-integracion-con-primevue)
4. [Soporte de Temas](#4-soporte-de-temas)
5. [Guia de Implementacion](#5-guia-de-implementacion)

---

## 1. Tokens de Diseno

### 1.1 Colores

#### Paleta Primaria (Brand)

La paleta primaria es dinamica y se selecciona desde Settings. Valores disponibles:

| Nombre | Light | Dark | Variable CSS |
|--------|-------|------|--------------|
| Blue | `#3B82F6` | `#60A5FA` | `--ds-primary-500` |
| Indigo | `#6366F1` | `#818CF8` | `--ds-primary-500` |
| Purple | `#A855F7` | `#C084FC` | `--ds-primary-500` |
| Pink | `#EC4899` | `#F472B6` | `--ds-primary-500` |
| Red | `#EF4444` | `#F87171` | `--ds-primary-500` |
| Orange | `#F97316` | `#FB923C` | `--ds-primary-500` |
| Amber | `#F59E0B` | `#FBBF24` | `--ds-primary-500` |
| Yellow | `#EAB308` | `#FACC15` | `--ds-primary-500` |
| Lime | `#84CC16` | `#A3E635` | `--ds-primary-500` |
| Green | `#22C55E` | `#4ADE80` | `--ds-primary-500` |
| Teal | `#14B8A6` | `#2DD4BF` | `--ds-primary-500` |
| Cyan | `#06B6D4` | `#22D3EE` | `--ds-primary-500` |

**Escala de tonos primarios**:

```css
:root {
  --ds-primary-50:  /* Tono mas claro, fondo hover */
  --ds-primary-100: /* Fondo activo */
  --ds-primary-200: /* Bordes sutiles */
  --ds-primary-300: /* Iconos secundarios */
  --ds-primary-400: /* Texto secundario */
  --ds-primary-500: /* Color principal */
  --ds-primary-600: /* Hover en botones */
  --ds-primary-700: /* Active/pressed */
  --ds-primary-800: /* Texto sobre fondo claro */
  --ds-primary-900: /* Maxima intensidad */
}
```

#### Paleta de Grises/Neutros

| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| `--ds-surface-0` | `#FFFFFF` | `#121212` | Fondo de cards |
| `--ds-surface-50` | `#F8FAFC` | `#1E1E1E` | Fondo hover sutil |
| `--ds-surface-100` | `#F1F5F9` | `#262626` | Fondo secundario |
| `--ds-surface-200` | `#E2E8F0` | `#333333` | Bordes |
| `--ds-surface-300` | `#CBD5E1` | `#404040` | Bordes hover |
| `--ds-surface-400` | `#94A3B8` | `#525252` | Iconos deshabilitados |
| `--ds-surface-500` | `#64748B` | `#6B7280` | Texto placeholder |
| `--ds-surface-600` | `#475569` | `#9CA3AF` | Texto secundario |
| `--ds-surface-700` | `#334155` | `#D1D5DB` | Texto principal (dark) |
| `--ds-surface-800` | `#1E293B` | `#E5E7EB` | Headers |
| `--ds-surface-900` | `#0F172A` | `#F3F4F6` | Texto principal |
| `--ds-surface-ground` | `#F3F4F6` | `#0A0A0A` | Fondo de pagina |

#### Colores Semanticos

| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| **Success** |
| `--ds-success-50` | `#F0FDF4` | `#14532D` | Fondo mensaje exito |
| `--ds-success-500` | `#22C55E` | `#4ADE80` | Icono/texto exito |
| `--ds-success-700` | `#15803D` | `#86EFAC` | Texto sobre fondo |
| **Warning** |
| `--ds-warning-50` | `#FEFCE8` | `#422006` | Fondo advertencia |
| `--ds-warning-500` | `#EAB308` | `#FACC15` | Icono/texto warning |
| `--ds-warning-700` | `#A16207` | `#FDE047` | Texto sobre fondo |
| **Error/Danger** |
| `--ds-error-50` | `#FEF2F2` | `#450A0A` | Fondo error |
| `--ds-error-500` | `#EF4444` | `#F87171` | Icono/texto error |
| `--ds-error-700` | `#B91C1C` | `#FCA5A5` | Texto sobre fondo |
| **Info** |
| `--ds-info-50` | `#EFF6FF` | `#172554` | Fondo info |
| `--ds-info-500` | `#3B82F6` | `#60A5FA` | Icono/texto info |
| `--ds-info-700` | `#1D4ED8` | `#93C5FD` | Texto sobre fondo |

#### Colores para Tipos de Entidad (19 tipos)

```css
:root {
  /* CHARACTER - Morado */
  --ds-entity-character: #7B1FA2;
  --ds-entity-character-bg: rgba(123, 31, 162, 0.12);

  /* LOCATION - Verde azulado */
  --ds-entity-location: #00897B;
  --ds-entity-location-bg: rgba(0, 137, 123, 0.12);

  /* ORGANIZATION - Azul */
  --ds-entity-organization: #1565C0;
  --ds-entity-organization-bg: rgba(21, 101, 192, 0.12);

  /* OBJECT - Naranja */
  --ds-entity-object: #F57C00;
  --ds-entity-object-bg: rgba(245, 124, 0, 0.12);

  /* EVENT - Purpura */
  --ds-entity-event: #8E24AA;
  --ds-entity-event-bg: rgba(142, 36, 170, 0.12);

  /* ANIMAL - Verde bosque */
  --ds-entity-animal: #2E7D32;
  --ds-entity-animal-bg: rgba(46, 125, 50, 0.12);

  /* CREATURE - Violeta oscuro */
  --ds-entity-creature: #5E35B1;
  --ds-entity-creature-bg: rgba(94, 53, 177, 0.12);

  /* BUILDING - Marron */
  --ds-entity-building: #6D4C41;
  --ds-entity-building-bg: rgba(109, 76, 65, 0.12);

  /* REGION - Verde oliva */
  --ds-entity-region: #558B2F;
  --ds-entity-region-bg: rgba(85, 139, 47, 0.12);

  /* VEHICLE - Gris azulado */
  --ds-entity-vehicle: #546E7A;
  --ds-entity-vehicle-bg: rgba(84, 110, 122, 0.12);

  /* FACTION - Rojo oscuro */
  --ds-entity-faction: #C62828;
  --ds-entity-faction-bg: rgba(198, 40, 40, 0.12);

  /* FAMILY - Rosa */
  --ds-entity-family: #AD1457;
  --ds-entity-family-bg: rgba(173, 20, 87, 0.12);

  /* TIME_PERIOD - Indigo */
  --ds-entity-time-period: #303F9F;
  --ds-entity-time-period-bg: rgba(48, 63, 159, 0.12);

  /* CONCEPT - Cyan */
  --ds-entity-concept: #0097A7;
  --ds-entity-concept-bg: rgba(0, 151, 167, 0.12);

  /* RELIGION - Dorado */
  --ds-entity-religion: #FF8F00;
  --ds-entity-religion-bg: rgba(255, 143, 0, 0.12);

  /* MAGIC_SYSTEM - Magenta */
  --ds-entity-magic-system: #C2185B;
  --ds-entity-magic-system-bg: rgba(194, 24, 91, 0.12);

  /* WORK - Azul grisaceo */
  --ds-entity-work: #455A64;
  --ds-entity-work-bg: rgba(69, 90, 100, 0.12);

  /* TITLE - Ambar oscuro */
  --ds-entity-title: #E65100;
  --ds-entity-title-bg: rgba(230, 81, 0, 0.12);

  /* LANGUAGE - Teal oscuro */
  --ds-entity-language: #00695C;
  --ds-entity-language-bg: rgba(0, 105, 92, 0.12);

  /* OTHER - Gris */
  --ds-entity-other: #616161;
  --ds-entity-other-bg: rgba(97, 97, 97, 0.12);
}

.dark {
  /* Versiones mas brillantes para dark mode */
  --ds-entity-character: #BA68C8;
  --ds-entity-character-bg: rgba(186, 104, 200, 0.2);

  --ds-entity-location: #4DB6AC;
  --ds-entity-location-bg: rgba(77, 182, 172, 0.2);

  --ds-entity-organization: #42A5F5;
  --ds-entity-organization-bg: rgba(66, 165, 245, 0.2);

  --ds-entity-object: #FFA726;
  --ds-entity-object-bg: rgba(255, 167, 38, 0.2);

  --ds-entity-event: #CE93D8;
  --ds-entity-event-bg: rgba(206, 147, 216, 0.2);

  --ds-entity-animal: #66BB6A;
  --ds-entity-animal-bg: rgba(102, 187, 106, 0.2);

  --ds-entity-creature: #9575CD;
  --ds-entity-creature-bg: rgba(149, 117, 205, 0.2);

  --ds-entity-building: #A1887F;
  --ds-entity-building-bg: rgba(161, 136, 127, 0.2);

  --ds-entity-region: #9CCC65;
  --ds-entity-region-bg: rgba(156, 204, 101, 0.2);

  --ds-entity-vehicle: #78909C;
  --ds-entity-vehicle-bg: rgba(120, 144, 156, 0.2);

  --ds-entity-faction: #EF5350;
  --ds-entity-faction-bg: rgba(239, 83, 80, 0.2);

  --ds-entity-family: #EC407A;
  --ds-entity-family-bg: rgba(236, 64, 122, 0.2);

  --ds-entity-time-period: #7986CB;
  --ds-entity-time-period-bg: rgba(121, 134, 203, 0.2);

  --ds-entity-concept: #26C6DA;
  --ds-entity-concept-bg: rgba(38, 198, 218, 0.2);

  --ds-entity-religion: #FFB74D;
  --ds-entity-religion-bg: rgba(255, 183, 77, 0.2);

  --ds-entity-magic-system: #F06292;
  --ds-entity-magic-system-bg: rgba(240, 98, 146, 0.2);

  --ds-entity-work: #90A4AE;
  --ds-entity-work-bg: rgba(144, 164, 174, 0.2);

  --ds-entity-title: #FF8A65;
  --ds-entity-title-bg: rgba(255, 138, 101, 0.2);

  --ds-entity-language: #26A69A;
  --ds-entity-language-bg: rgba(38, 166, 154, 0.2);

  --ds-entity-other: #9E9E9E;
  --ds-entity-other-bg: rgba(158, 158, 158, 0.2);
}
```

#### Colores para Severidades de Alertas (4 niveles)

```css
:root {
  /* CRITICAL */
  --ds-alert-critical: #D32F2F;
  --ds-alert-critical-bg: #FFEBEE;
  --ds-alert-critical-border: #F44336;

  /* WARNING */
  --ds-alert-warning: #F57C00;
  --ds-alert-warning-bg: #FFF3E0;
  --ds-alert-warning-border: #FF9800;

  /* INFO */
  --ds-alert-info: #0288D1;
  --ds-alert-info-bg: #E1F5FE;
  --ds-alert-info-border: #03A9F4;

  /* HINT */
  --ds-alert-hint: #616161;
  --ds-alert-hint-bg: #F5F5F5;
  --ds-alert-hint-border: #9E9E9E;
}

.dark {
  --ds-alert-critical: #EF5350;
  --ds-alert-critical-bg: #3E1F1F;
  --ds-alert-critical-border: #E53935;

  --ds-alert-warning: #FFA726;
  --ds-alert-warning-bg: #3E2E1F;
  --ds-alert-warning-border: #FB8C00;

  --ds-alert-info: #42A5F5;
  --ds-alert-info-bg: #1F2D3E;
  --ds-alert-info-border: #2196F3;

  --ds-alert-hint: #9E9E9E;
  --ds-alert-hint-bg: #2D2D30;
  --ds-alert-hint-border: #757575;
}
```

---

### 1.2 Tipografia

#### Escala de Tamanos

| Token | Tamano Base | Uso |
|-------|-------------|-----|
| `--ds-font-xs` | `0.75rem` (12px) | Etiquetas pequenas, metadata |
| `--ds-font-sm` | `0.875rem` (14px) | Texto secundario, descripciones |
| `--ds-font-base` | `1rem` (16px) | Texto principal |
| `--ds-font-lg` | `1.125rem` (18px) | Subtitulos, destacados |
| `--ds-font-xl` | `1.25rem` (20px) | Titulos de seccion |
| `--ds-font-2xl` | `1.5rem` (24px) | Titulos de pagina |
| `--ds-font-3xl` | `1.875rem` (30px) | Headers principales |

**Configuracion dinamica desde Settings**:

| Preset | Base Size | Uso |
|--------|-----------|-----|
| `small` | `14px` | Usuarios que prefieren densidad |
| `medium` | `16px` | Por defecto |
| `large` | `18px` | Mayor legibilidad |
| `xlarge` | `20px` | Accesibilidad |

#### Pesos de Fuente

```css
:root {
  --ds-font-normal: 400;
  --ds-font-medium: 500;
  --ds-font-semibold: 600;
  --ds-font-bold: 700;
}
```

| Token | Peso | Uso |
|-------|------|-----|
| `--ds-font-normal` | 400 | Texto de parrafo |
| `--ds-font-medium` | 500 | Labels, botones |
| `--ds-font-semibold` | 600 | Titulos de card, nombres |
| `--ds-font-bold` | 700 | Headers, destacados |

#### Line Heights

| Token | Valor | Uso |
|-------|-------|-----|
| `--ds-leading-none` | `1` | Titulos cortos |
| `--ds-leading-tight` | `1.25` | Headers |
| `--ds-leading-snug` | `1.375` | Botones, labels |
| `--ds-leading-normal` | `1.5` | Texto general |
| `--ds-leading-relaxed` | `1.625` | Parrafos largos |
| `--ds-leading-loose` | `2` | Maxima legibilidad |

**Configuracion dinamica desde Settings**:

| Preset | Line Height | Uso |
|--------|-------------|-----|
| `compact` | `1.4` | Interfaces densas |
| `normal` | `1.6` | Por defecto |
| `relaxed` | `1.8` | Lectura de documentos |
| `loose` | `2.0` | Maxima legibilidad |

#### Letter Spacing

```css
:root {
  --ds-tracking-tighter: -0.05em;
  --ds-tracking-tight: -0.025em;
  --ds-tracking-normal: 0;
  --ds-tracking-wide: 0.025em;
  --ds-tracking-wider: 0.05em;
}
```

#### Familia Tipografica

```css
:root {
  --ds-font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                    Roboto, Oxygen, Ubuntu, sans-serif;
  --ds-font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
}
```

---

### 1.3 Espaciado

#### Escala Base (4px)

| Token | Valor | Pixeles | Uso |
|-------|-------|---------|-----|
| `--ds-space-0` | `0` | 0px | Sin espacio |
| `--ds-space-px` | `1px` | 1px | Bordes finos |
| `--ds-space-0.5` | `0.125rem` | 2px | Micro espaciado |
| `--ds-space-1` | `0.25rem` | 4px | Espaciado minimo |
| `--ds-space-1.5` | `0.375rem` | 6px | Entre iconos y texto |
| `--ds-space-2` | `0.5rem` | 8px | Padding interno pequeno |
| `--ds-space-2.5` | `0.625rem` | 10px | - |
| `--ds-space-3` | `0.75rem` | 12px | Padding botones |
| `--ds-space-3.5` | `0.875rem` | 14px | - |
| `--ds-space-4` | `1rem` | 16px | Padding cards |
| `--ds-space-5` | `1.25rem` | 20px | Gap entre items |
| `--ds-space-6` | `1.5rem` | 24px | Padding secciones |
| `--ds-space-7` | `1.75rem` | 28px | - |
| `--ds-space-8` | `2rem` | 32px | Margen entre cards |
| `--ds-space-9` | `2.25rem` | 36px | - |
| `--ds-space-10` | `2.5rem` | 40px | - |
| `--ds-space-12` | `3rem` | 48px | Padding pagina |
| `--ds-space-16` | `4rem` | 64px | Espaciado grande |
| `--ds-space-20` | `5rem` | 80px | - |
| `--ds-space-24` | `6rem` | 96px | - |

#### Variables de Compactness (UI Density)

```css
:root {
  /* Scale factor aplicado via --app-spacing-scale */
  --ds-compact-scale: 0.875;  /* compact */
  --ds-normal-scale: 1;        /* normal */
  --ds-comfortable-scale: 1.125; /* comfortable */
}
```

---

### 1.4 Bordes y Sombras

#### Border Radius Scale

| Token | Valor | Uso |
|-------|-------|-----|
| `--ds-radius-none` | `0px` | Sin redondeo |
| `--ds-radius-sm` | `2px` | Inputs pequenos |
| `--ds-radius-default` | `4px` | Botones, inputs |
| `--ds-radius-md` | `6px` | Cards, dropdowns |
| `--ds-radius-lg` | `8px` | Modales, paneles |
| `--ds-radius-xl` | `12px` | Dialogs grandes |
| `--ds-radius-2xl` | `16px` | Elementos destacados |
| `--ds-radius-full` | `9999px` | Pills, avatares |

**Configuracion dinamica desde Settings**:

| Preset | Radius Base |
|--------|-------------|
| `none` | `0px` |
| `small` | `4px` |
| `medium` | `8px` |
| `large` | `12px` |

#### Border Widths

```css
:root {
  --ds-border-0: 0px;
  --ds-border-1: 1px;
  --ds-border-2: 2px;
  --ds-border-4: 4px;
  --ds-border-8: 8px;
}
```

#### Shadow Elevation System

| Token | Light Mode | Dark Mode | Uso |
|-------|------------|-----------|-----|
| `--ds-shadow-none` | `none` | `none` | Sin sombra |
| `--ds-shadow-xs` | `0 1px 2px rgba(0,0,0,0.05)` | `0 1px 2px rgba(0,0,0,0.5)` | Elementos sutiles |
| `--ds-shadow-sm` | `0 1px 3px rgba(0,0,0,0.08)` | `0 1px 3px rgba(0,0,0,0.5)` | Cards base |
| `--ds-shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | `0 4px 6px rgba(0,0,0,0.6)` | Cards elevadas |
| `--ds-shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | `0 10px 15px rgba(0,0,0,0.7)` | Modales |
| `--ds-shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | `0 20px 25px rgba(0,0,0,0.75)` | Dialogs |
| `--ds-shadow-2xl` | `0 25px 50px rgba(0,0,0,0.25)` | `0 25px 50px rgba(0,0,0,0.8)` | Maximo |

#### Focus Ring

```css
:root {
  --ds-focus-ring: 0 0 0 3px rgba(var(--ds-primary-500-rgb), 0.25);
  --ds-focus-ring-error: 0 0 0 3px rgba(239, 68, 68, 0.25);
}
```

---

### 1.5 Animaciones

#### Duraciones Estandar

| Token | Valor | Uso |
|-------|-------|-----|
| `--ds-duration-instant` | `0ms` | Sin animacion |
| `--ds-duration-fastest` | `50ms` | Micro-interacciones |
| `--ds-duration-faster` | `100ms` | Hover estados |
| `--ds-duration-fast` | `150ms` | Tooltips, ripples |
| `--ds-duration-normal` | `200ms` | Transiciones estandar |
| `--ds-duration-slow` | `300ms` | Modales, slides |
| `--ds-duration-slower` | `400ms` | Transiciones complejas |
| `--ds-duration-slowest` | `500ms` | Animaciones destacadas |

#### Curvas de Easing

```css
:root {
  --ds-ease-linear: linear;
  --ds-ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ds-ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ds-ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ds-ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
```

#### Transiciones Predefinidas

```css
:root {
  /* Propiedades comunes */
  --ds-transition-colors: color, background-color, border-color;
  --ds-transition-transform: transform;
  --ds-transition-opacity: opacity;
  --ds-transition-shadow: box-shadow;
  --ds-transition-all: all;
}
```

#### Clases de Utilidad para Animaciones

```css
/* Fade */
.ds-fade-enter-active,
.ds-fade-leave-active {
  transition: opacity var(--ds-duration-normal) var(--ds-ease-out);
}
.ds-fade-enter-from,
.ds-fade-leave-to {
  opacity: 0;
}

/* Slide */
.ds-slide-enter-active,
.ds-slide-leave-active {
  transition: transform var(--ds-duration-normal) var(--ds-ease-out),
              opacity var(--ds-duration-normal) var(--ds-ease-out);
}
.ds-slide-enter-from {
  transform: translateY(-10px);
  opacity: 0;
}
.ds-slide-leave-to {
  transform: translateY(10px);
  opacity: 0;
}

/* Scale */
.ds-scale-enter-active,
.ds-scale-leave-active {
  transition: transform var(--ds-duration-normal) var(--ds-ease-out),
              opacity var(--ds-duration-normal) var(--ds-ease-out);
}
.ds-scale-enter-from,
.ds-scale-leave-to {
  transform: scale(0.95);
  opacity: 0;
}

/* Hover utilities */
.ds-hover-lift {
  transition: transform var(--ds-duration-fast) var(--ds-ease-out),
              box-shadow var(--ds-duration-fast) var(--ds-ease-out);
}
.ds-hover-lift:hover {
  transform: translateY(-2px);
  box-shadow: var(--ds-shadow-md);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

html.reduced-motion *,
html.reduced-motion *::before,
html.reduced-motion *::after {
  animation-duration: 0.01ms !important;
  transition-duration: 0.01ms !important;
}
```

---

## 2. Componentes Base

### 2.1 Badge

Badges para severidades, tipos de entidad, importancia y estados.

#### Variantes

| Variante | Uso |
|----------|-----|
| `severity` | Alertas (critical, warning, info, hint) |
| `entity-type` | Tipos de entidad (CHARACTER, LOCATION, etc.) |
| `importance` | Importancia (principal, high, medium, low, minimal) |
| `status` | Estados (open, resolved, dismissed) |

#### Props

```typescript
interface BadgeProps {
  variant: 'severity' | 'entity-type' | 'importance' | 'status' | 'default';
  value: string;
  size?: 'sm' | 'md' | 'lg';
  outlined?: boolean;
  rounded?: boolean; // pill style
  icon?: string;
}
```

#### Estados

| Estado | Descripcion |
|--------|-------------|
| Default | Fondo solido, texto contrastante |
| Outlined | Solo borde, fondo transparente |
| Disabled | Opacity reducida |

#### CSS

```css
.ds-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-1);
  padding: 0.25em 0.5em;
  font-size: var(--ds-font-xs);
  font-weight: var(--ds-font-semibold);
  line-height: 1;
  border-radius: var(--ds-radius-default);
  white-space: nowrap;
}

.ds-badge--sm {
  padding: 0.2em 0.4em;
  font-size: 0.7rem;
}

.ds-badge--lg {
  padding: 0.35em 0.65em;
  font-size: var(--ds-font-sm);
}

.ds-badge--rounded {
  border-radius: var(--ds-radius-full);
  padding: 0.25em 0.75em;
}

/* Severity variants */
.ds-badge--critical {
  background: var(--ds-alert-critical);
  color: white;
}

.ds-badge--warning {
  background: var(--ds-alert-warning);
  color: white;
}

.ds-badge--info {
  background: var(--ds-alert-info);
  color: white;
}

.ds-badge--hint {
  background: var(--ds-alert-hint);
  color: white;
}

/* Entity type variants */
.ds-badge--entity-character {
  background: var(--ds-entity-character);
  color: white;
}

/* ... otros tipos de entidad ... */

/* Importance variants */
.ds-badge--importance-principal {
  background: var(--ds-success-500);
  color: white;
}

.ds-badge--importance-high {
  background: var(--ds-warning-500);
  color: var(--ds-surface-900);
}

.ds-badge--importance-medium {
  background: var(--ds-info-500);
  color: white;
}

.ds-badge--importance-low {
  background: var(--ds-surface-400);
  color: white;
}

/* Status variants */
.ds-badge--status-open {
  background: var(--ds-warning-500);
  color: var(--ds-surface-900);
}

.ds-badge--status-resolved {
  background: var(--ds-success-500);
  color: white;
}

.ds-badge--status-dismissed {
  background: var(--ds-surface-400);
  color: white;
}
```

---

### 2.2 Button

#### Variantes

| Variante | Uso |
|----------|-----|
| `primary` | Accion principal |
| `secondary` | Accion secundaria |
| `text` | Accion terciaria, links |
| `outlined` | Variante alternativa |
| `icon-only` | Solo icono (acciones) |

#### Props

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'text' | 'outlined';
  severity?: 'success' | 'warning' | 'danger' | 'info' | 'help';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  iconPos?: 'left' | 'right';
  loading?: boolean;
  disabled?: boolean;
  rounded?: boolean;
  raised?: boolean;
}
```

#### Estados

| Estado | Cambios visuales |
|--------|------------------|
| Default | Colores base |
| Hover | Fondo ligeramente mas oscuro |
| Active | Escala 0.98, sombra interna |
| Focus | Focus ring visible |
| Disabled | Opacity 0.5, cursor not-allowed |
| Loading | Spinner visible, texto oculto |

#### CSS

```css
.ds-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-4);
  font-size: var(--ds-font-sm);
  font-weight: var(--ds-font-medium);
  line-height: var(--ds-leading-snug);
  border-radius: var(--ds-radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color var(--ds-duration-fast) var(--ds-ease-out),
    border-color var(--ds-duration-fast) var(--ds-ease-out),
    transform var(--ds-duration-fastest) var(--ds-ease-out);
}

.ds-btn:focus-visible {
  outline: none;
  box-shadow: var(--ds-focus-ring);
}

.ds-btn:active {
  transform: scale(0.98);
}

.ds-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* Sizes */
.ds-btn--sm {
  padding: var(--ds-space-1) var(--ds-space-3);
  font-size: var(--ds-font-xs);
}

.ds-btn--lg {
  padding: var(--ds-space-3) var(--ds-space-6);
  font-size: var(--ds-font-base);
}

/* Primary */
.ds-btn--primary {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-color: var(--p-primary-color);
}

.ds-btn--primary:hover {
  background: var(--p-primary-600);
  border-color: var(--p-primary-600);
}

/* Secondary */
.ds-btn--secondary {
  background: var(--ds-surface-100);
  color: var(--ds-surface-700);
  border-color: var(--ds-surface-200);
}

.ds-btn--secondary:hover {
  background: var(--ds-surface-200);
}

/* Text */
.ds-btn--text {
  background: transparent;
  color: var(--p-primary-color);
  border-color: transparent;
  padding: var(--ds-space-2);
}

.ds-btn--text:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

/* Outlined */
.ds-btn--outlined {
  background: transparent;
  color: var(--p-primary-color);
  border-color: var(--p-primary-color);
}

.ds-btn--outlined:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

/* Icon only */
.ds-btn--icon-only {
  padding: var(--ds-space-2);
  aspect-ratio: 1;
}

.ds-btn--icon-only.ds-btn--rounded {
  border-radius: var(--ds-radius-full);
}
```

---

### 2.3 Card

#### Variantes

| Variante | Uso |
|----------|-----|
| `default` | Card basica |
| `elevated` | Con sombra elevada |
| `outlined` | Solo borde |
| `header` | Con header destacado |
| `interactive` | Clickeable con hover |

#### Props

```typescript
interface CardProps {
  variant?: 'default' | 'elevated' | 'outlined';
  header?: boolean;
  headerTitle?: string;
  headerIcon?: string;
  footer?: boolean;
  interactive?: boolean;
  selected?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}
```

#### CSS

```css
.ds-card {
  background: var(--ds-surface-0);
  border-radius: var(--ds-radius-lg);
  border: 1px solid var(--ds-surface-200);
  overflow: hidden;
}

.ds-card--elevated {
  border-color: transparent;
  box-shadow: var(--ds-shadow-md);
}

.ds-card--outlined {
  background: transparent;
  border-color: var(--ds-surface-300);
}

.ds-card--interactive {
  cursor: pointer;
  transition:
    border-color var(--ds-duration-fast) var(--ds-ease-out),
    box-shadow var(--ds-duration-fast) var(--ds-ease-out),
    transform var(--ds-duration-fast) var(--ds-ease-out);
}

.ds-card--interactive:hover {
  border-color: var(--p-primary-color);
  box-shadow: var(--ds-shadow-md);
  transform: translateY(-2px);
}

.ds-card--selected {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--ds-surface-0));
}

.ds-card__header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  background: var(--ds-surface-50);
  border-bottom: 1px solid var(--ds-surface-200);
}

.ds-card__header-icon {
  font-size: var(--ds-font-lg);
  color: var(--p-primary-color);
}

.ds-card__header-title {
  margin: 0;
  font-size: var(--ds-font-base);
  font-weight: var(--ds-font-semibold);
}

.ds-card__body {
  padding: var(--ds-space-4);
}

.ds-card__body--no-padding {
  padding: 0;
}

.ds-card__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--ds-surface-50);
  border-top: 1px solid var(--ds-surface-200);
}
```

---

### 2.4 Input

#### Variantes

| Variante | Uso |
|----------|-----|
| `text` | Entrada de texto |
| `search` | Busqueda con icono |
| `select` | Dropdown de seleccion |
| `textarea` | Texto multilinea |

#### Props

```typescript
interface InputProps {
  type?: 'text' | 'search' | 'email' | 'password' | 'number';
  size?: 'sm' | 'md' | 'lg';
  placeholder?: string;
  icon?: string;
  iconPos?: 'left' | 'right';
  clearable?: boolean;
  disabled?: boolean;
  invalid?: boolean;
  helpText?: string;
  errorText?: string;
}
```

#### Estados

| Estado | Visual |
|--------|--------|
| Default | Borde surface-200 |
| Focus | Borde primary, focus ring |
| Hover | Borde surface-300 |
| Disabled | Fondo gris, texto muted |
| Invalid | Borde error, mensaje error |
| Valid | Borde success (opcional) |

#### CSS

```css
.ds-input-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.ds-input {
  width: 100%;
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-sm);
  line-height: var(--ds-leading-normal);
  color: var(--ds-surface-900);
  background: var(--ds-surface-0);
  border: 1px solid var(--ds-surface-200);
  border-radius: var(--ds-radius-md);
  transition:
    border-color var(--ds-duration-fast) var(--ds-ease-out),
    box-shadow var(--ds-duration-fast) var(--ds-ease-out);
}

.ds-input::placeholder {
  color: var(--ds-surface-500);
}

.ds-input:hover:not(:disabled):not(:focus) {
  border-color: var(--ds-surface-300);
}

.ds-input:focus {
  outline: none;
  border-color: var(--p-primary-color);
  box-shadow: var(--ds-focus-ring);
}

.ds-input:disabled {
  background: var(--ds-surface-100);
  color: var(--ds-surface-500);
  cursor: not-allowed;
}

.ds-input--invalid {
  border-color: var(--ds-error-500);
}

.ds-input--invalid:focus {
  box-shadow: var(--ds-focus-ring-error);
}

/* Sizes */
.ds-input--sm {
  padding: var(--ds-space-1) var(--ds-space-2);
  font-size: var(--ds-font-xs);
}

.ds-input--lg {
  padding: var(--ds-space-3) var(--ds-space-4);
  font-size: var(--ds-font-base);
}

/* With icon */
.ds-input--with-icon-left {
  padding-left: var(--ds-space-8);
}

.ds-input--with-icon-right {
  padding-right: var(--ds-space-8);
}

.ds-input-icon {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ds-surface-500);
  pointer-events: none;
}

.ds-input-icon--left {
  left: var(--ds-space-3);
}

.ds-input-icon--right {
  right: var(--ds-space-3);
}

/* Helper text */
.ds-input-help {
  font-size: var(--ds-font-xs);
  color: var(--ds-surface-600);
}

.ds-input-error {
  font-size: var(--ds-font-xs);
  color: var(--ds-error-500);
}
```

---

### 2.5 List Item

#### Variantes

| Variante | Uso |
|----------|-----|
| `default` | Item basico |
| `compact` | Densidad alta |
| `expanded` | Con detalles adicionales |
| `selectable` | Clickeable |

#### Props

```typescript
interface ListItemProps {
  variant?: 'default' | 'compact' | 'expanded';
  selected?: boolean;
  disabled?: boolean;
  icon?: string;
  title: string;
  subtitle?: string;
  metadata?: string;
  badge?: BadgeProps;
  actions?: boolean;
}
```

#### CSS

```css
.ds-list-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--ds-surface-0);
  border: 1px solid var(--ds-surface-200);
  border-radius: var(--ds-radius-md);
  transition:
    background-color var(--ds-duration-fast) var(--ds-ease-out),
    border-color var(--ds-duration-fast) var(--ds-ease-out),
    transform var(--ds-duration-fast) var(--ds-ease-out);
}

.ds-list-item--selectable {
  cursor: pointer;
}

.ds-list-item--selectable:hover {
  background: var(--ds-surface-50);
  border-color: var(--p-primary-color);
  transform: translateX(4px);
}

.ds-list-item--selected {
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--ds-surface-0));
  border-color: var(--p-primary-color);
}

.ds-list-item--compact {
  padding: var(--ds-space-2) var(--ds-space-3);
  gap: var(--ds-space-2);
}

.ds-list-item__icon-wrapper {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  border-radius: var(--ds-radius-full);
  flex-shrink: 0;
}

.ds-list-item__icon {
  font-size: var(--ds-font-lg);
  color: var(--p-primary-color);
}

.ds-list-item__content {
  flex: 1;
  min-width: 0;
}

.ds-list-item__title {
  font-weight: var(--ds-font-semibold);
  font-size: var(--ds-font-sm);
  color: var(--ds-surface-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ds-list-item__subtitle {
  font-size: var(--ds-font-xs);
  color: var(--ds-surface-600);
  margin-top: var(--ds-space-0.5);
}

.ds-list-item__metadata {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.ds-list-item__actions {
  display: flex;
  gap: var(--ds-space-1);
  flex-shrink: 0;
}
```

---

### 2.6 Tab

#### Variantes

| Variante | Orientacion |
|----------|-------------|
| `horizontal` | Tabs horizontales |
| `vertical` | Tabs verticales (sidebar) |

#### Props

```typescript
interface TabItem {
  id: string;
  label: string;
  icon?: string;
  badge?: string | number;
  disabled?: boolean;
}

interface TabsProps {
  items: TabItem[];
  activeId: string;
  orientation?: 'horizontal' | 'vertical';
  size?: 'sm' | 'md' | 'lg';
}
```

#### CSS

```css
.ds-tabs {
  display: flex;
}

.ds-tabs--horizontal {
  flex-direction: row;
  border-bottom: 1px solid var(--ds-surface-200);
  gap: var(--ds-space-1);
}

.ds-tabs--vertical {
  flex-direction: column;
  border-right: 1px solid var(--ds-surface-200);
  gap: var(--ds-space-0.5);
}

.ds-tab {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  font-size: var(--ds-font-sm);
  font-weight: var(--ds-font-medium);
  color: var(--ds-surface-600);
  background: transparent;
  border: none;
  cursor: pointer;
  transition:
    color var(--ds-duration-fast) var(--ds-ease-out),
    background-color var(--ds-duration-fast) var(--ds-ease-out);
}

.ds-tabs--horizontal .ds-tab {
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.ds-tabs--vertical .ds-tab {
  border-left: 3px solid transparent;
  margin-right: -1px;
}

.ds-tab:hover:not(:disabled) {
  color: var(--ds-surface-900);
  background: var(--ds-surface-50);
}

.ds-tab--active {
  color: var(--p-primary-color);
  font-weight: var(--ds-font-semibold);
}

.ds-tabs--horizontal .ds-tab--active {
  border-bottom-color: var(--p-primary-color);
}

.ds-tabs--vertical .ds-tab--active {
  border-left-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

.ds-tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ds-tab__badge {
  margin-left: auto;
}
```

---

### 2.7 Panel

#### Props

```typescript
interface PanelProps {
  title?: string;
  icon?: string;
  collapsible?: boolean;
  collapsed?: boolean;
  resizable?: boolean;
  minWidth?: string;
  maxWidth?: string;
}
```

#### CSS

```css
.ds-panel {
  display: flex;
  flex-direction: column;
  background: var(--ds-surface-0);
  border: 1px solid var(--ds-surface-200);
  border-radius: var(--ds-radius-lg);
  overflow: hidden;
}

.ds-panel__header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--ds-surface-50);
  border-bottom: 1px solid var(--ds-surface-200);
}

.ds-panel__header-icon {
  font-size: var(--ds-font-lg);
  color: var(--p-primary-color);
}

.ds-panel__header-title {
  flex: 1;
  margin: 0;
  font-size: var(--ds-font-base);
  font-weight: var(--ds-font-semibold);
}

.ds-panel__header-actions {
  display: flex;
  gap: var(--ds-space-1);
}

.ds-panel__collapse-btn {
  transition: transform var(--ds-duration-fast) var(--ds-ease-out);
}

.ds-panel--collapsed .ds-panel__collapse-btn {
  transform: rotate(-90deg);
}

.ds-panel__body {
  flex: 1;
  overflow: auto;
  padding: var(--ds-space-4);
}

.ds-panel--collapsed .ds-panel__body {
  display: none;
}

/* Resizable */
.ds-panel--resizable {
  resize: horizontal;
  overflow: auto;
}

.ds-panel__resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  background: transparent;
  transition: background-color var(--ds-duration-fast) var(--ds-ease-out);
}

.ds-panel__resize-handle:hover {
  background: var(--p-primary-color);
}
```

---

### 2.8 Tooltip

#### Props

```typescript
interface TooltipProps {
  content: string;
  position?: 'top' | 'right' | 'bottom' | 'left';
  delay?: number;
  maxWidth?: string;
}
```

#### CSS

```css
.ds-tooltip {
  position: absolute;
  z-index: 1000;
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-xs);
  color: white;
  background: var(--ds-surface-800);
  border-radius: var(--ds-radius-md);
  box-shadow: var(--ds-shadow-lg);
  max-width: 300px;
  pointer-events: none;
  white-space: normal;
  word-wrap: break-word;
}

.ds-tooltip--top {
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-8px);
}

.ds-tooltip--bottom {
  top: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(8px);
}

.ds-tooltip--left {
  right: 100%;
  top: 50%;
  transform: translateY(-50%) translateX(-8px);
}

.ds-tooltip--right {
  left: 100%;
  top: 50%;
  transform: translateY(-50%) translateX(8px);
}

/* Arrow */
.ds-tooltip::after {
  content: '';
  position: absolute;
  border: 6px solid transparent;
}

.ds-tooltip--top::after {
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-top-color: var(--ds-surface-800);
}

.ds-tooltip--bottom::after {
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-bottom-color: var(--ds-surface-800);
}
```

---

### 2.9 Empty State

#### Props

```typescript
interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  actionLabel?: string;
  actionIcon?: string;
}
```

#### CSS

```css
.ds-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-12) var(--ds-space-4);
  text-align: center;
}

.ds-empty-state__icon {
  font-size: 3rem;
  color: var(--ds-surface-400);
  margin-bottom: var(--ds-space-4);
  opacity: 0.5;
}

.ds-empty-state__title {
  margin: 0 0 var(--ds-space-2) 0;
  font-size: var(--ds-font-lg);
  font-weight: var(--ds-font-semibold);
  color: var(--ds-surface-700);
}

.ds-empty-state__description {
  margin: 0 0 var(--ds-space-6) 0;
  font-size: var(--ds-font-sm);
  color: var(--ds-surface-500);
  max-width: 400px;
}

.ds-empty-state__action {
  margin-top: var(--ds-space-4);
}
```

---

### 2.10 Loading State

#### Variantes

| Variante | Uso |
|----------|-----|
| `spinner` | Spinner circular |
| `skeleton` | Placeholder de contenido |
| `progress` | Barra de progreso |

#### CSS

```css
/* Spinner */
.ds-loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-6);
}

.ds-loading-spinner__icon {
  animation: ds-spin 1s linear infinite;
}

.ds-loading-spinner__text {
  font-size: var(--ds-font-sm);
  color: var(--ds-surface-600);
}

@keyframes ds-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Skeleton */
.ds-skeleton {
  background: linear-gradient(
    90deg,
    var(--ds-surface-100) 0%,
    var(--ds-surface-200) 50%,
    var(--ds-surface-100) 100%
  );
  background-size: 200% 100%;
  animation: ds-shimmer 1.5s ease-in-out infinite;
  border-radius: var(--ds-radius-md);
}

.ds-skeleton--text {
  height: 1em;
  width: 100%;
}

.ds-skeleton--circle {
  border-radius: var(--ds-radius-full);
}

.ds-skeleton--card {
  height: 200px;
}

@keyframes ds-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Progress */
.ds-progress {
  width: 100%;
  height: 4px;
  background: var(--ds-surface-200);
  border-radius: var(--ds-radius-full);
  overflow: hidden;
}

.ds-progress__bar {
  height: 100%;
  background: var(--p-primary-color);
  border-radius: var(--ds-radius-full);
  transition: width var(--ds-duration-normal) var(--ds-ease-out);
}

.ds-progress--indeterminate .ds-progress__bar {
  width: 30%;
  animation: ds-progress-indeterminate 1.5s ease-in-out infinite;
}

@keyframes ds-progress-indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
```

---

### 2.11 Alert/Message

#### Variantes

| Severity | Color | Icono |
|----------|-------|-------|
| `info` | Blue | `pi-info-circle` |
| `success` | Green | `pi-check-circle` |
| `warning` | Yellow/Orange | `pi-exclamation-triangle` |
| `error` | Red | `pi-times-circle` |

#### Props

```typescript
interface AlertProps {
  severity: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  message: string;
  closable?: boolean;
  icon?: string;
}
```

#### CSS

```css
.ds-alert {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  border-radius: var(--ds-radius-lg);
  border: 1px solid;
}

.ds-alert__icon {
  font-size: var(--ds-font-lg);
  flex-shrink: 0;
}

.ds-alert__content {
  flex: 1;
}

.ds-alert__title {
  margin: 0 0 var(--ds-space-1) 0;
  font-weight: var(--ds-font-semibold);
  font-size: var(--ds-font-sm);
}

.ds-alert__message {
  margin: 0;
  font-size: var(--ds-font-sm);
  line-height: var(--ds-leading-relaxed);
}

.ds-alert__close {
  flex-shrink: 0;
  margin-left: var(--ds-space-2);
}

/* Info */
.ds-alert--info {
  background: var(--ds-info-50);
  border-color: var(--ds-info-500);
  color: var(--ds-info-700);
}

.ds-alert--info .ds-alert__icon {
  color: var(--ds-info-500);
}

/* Success */
.ds-alert--success {
  background: var(--ds-success-50);
  border-color: var(--ds-success-500);
  color: var(--ds-success-700);
}

.ds-alert--success .ds-alert__icon {
  color: var(--ds-success-500);
}

/* Warning */
.ds-alert--warning {
  background: var(--ds-warning-50);
  border-color: var(--ds-warning-500);
  color: var(--ds-warning-700);
}

.ds-alert--warning .ds-alert__icon {
  color: var(--ds-warning-500);
}

/* Error */
.ds-alert--error {
  background: var(--ds-error-50);
  border-color: var(--ds-error-500);
  color: var(--ds-error-700);
}

.ds-alert--error .ds-alert__icon {
  color: var(--ds-error-500);
}
```

---

## 3. Integracion con PrimeVue

### 3.1 Configuracion del Tema

El proyecto usa PrimeVue 4 con el sistema de temas nuevo. La configuracion esta en `main.ts`:

```typescript
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark',
      cssLayer: false
    }
  },
  ripple: true
})
```

### 3.2 Personalizacion de Componentes PrimeVue

Los overrides se definen en `src/assets/primevue-overrides.css` y se cargan DESPUES del tema base.

**Componentes personalizados**:

- **Dropdown/Select**: Padding mejorado, items mas espaciados
- **Menu**: Items con mejor padding y alineacion
- **Tag/Badge**: Tamanos consistentes, centrado vertical correcto
- **MultiSelect**: Tokens/chips que no se cortan
- **Toast/Message**: Estructura flex mejorada
- **Todos**: box-sizing: border-box

### 3.3 Variables CSS de PrimeVue Relevantes

```css
/* Colores primarios (generados dinamicamente por palette()) */
--p-primary-50
--p-primary-100
/* ... hasta 900 */
--p-primary-color
--p-primary-contrast-color

/* Superficies */
--p-surface-0
--p-surface-50
/* ... hasta 950 */
--p-surface-ground
--p-surface-card
--p-surface-border

/* Texto */
--p-text-color
--p-text-color-secondary
--p-text-muted-color

/* Bordes */
--p-content-border-radius
--p-form-field-border-radius
```

### 3.4 Cambio Dinamico de Preset y Color

El store `theme.ts` usa las funciones de `@primeuix/themes`:

```typescript
import { usePreset, updatePreset, palette } from '@primeuix/themes'

// Cambiar preset completo
usePreset(Aura)

// Actualizar color primario
const colorPalette = palette('#3B82F6')
updatePreset(Aura, {
  semantic: {
    primary: colorPalette
  }
})
```

---

## 4. Soporte de Temas

### 4.1 Presets de Tema Disponibles

Los presets definen la apariencia visual global. Inspirados en interfaces actuales:

| Preset | Inspiración | Características |
|--------|-------------|-----------------|
| **aura** | VS Code, GitHub | Moderno, bordes redondeados suaves, sombras sutiles. Default. |
| **lara** | Notion, Linear | Minimalista, espacioso, tipografía prominente |
| **material** | Google Docs | Material Design 3, ripple effects, elevaciones |
| **nora** | macOS nativo | Aspecto nativo Apple, vibrancy, blur |
| **nord** | Nord Theme | Paleta fría ártica, azules y grises armoniosos |
| **dracula** | Dracula Theme | Alto contraste, púrpuras y verdes neón |
| **grammarly** | Grammarly | Limpio, enfocado en lectura, verde característico |
| **scrivener** | Scrivener | Clásico editorial, tonos cálidos, serif opcional |

**Detalles de cada preset:**

#### Aura (Default)
- Bordes: `border-radius: 6px`
- Sombras: Sutiles, multi-capa
- Ideal para: Uso prolongado, entornos profesionales

#### Lara
- Bordes: `border-radius: 8px`
- Espaciado: Más generoso (+20%)
- Tipografía: Inter/System, mayor peso visual
- Ideal para: Claridad, presentaciones

#### Material
- Bordes: `border-radius: 4px` (más angular)
- Animaciones: Ripple en botones
- Elevaciones: 5 niveles de sombra
- Ideal para: Usuarios de Google Workspace

#### Nora
- Bordes: `border-radius: 10px` (más redondeado)
- Efectos: Backdrop blur en paneles
- Colores: Vibrancy de macOS
- Ideal para: Usuarios de Mac

#### Nord (NUEVO)
- Paleta: Azules árticos (#2E3440, #88C0D0, #A3BE8C)
- Contraste: Suave, reduce fatiga visual
- Ideal para: Sesiones largas de lectura

#### Dracula (NUEVO)
- Paleta: Fondo oscuro (#282A36), acentos (#BD93F9, #50FA7B)
- Contraste: Alto, excelente legibilidad
- Ideal para: Trabajo nocturno, preferencia dark

#### Grammarly (NUEVO)
- Paleta: Verde distintivo (#15C39A), fondo neutro
- Highlights: Subrayados prominentes
- Focus: Máxima legibilidad del texto
- Ideal para: Corrección intensiva

#### Scrivener (NUEVO)
- Paleta: Tonos cálidos (marfil, sepia)
- Opción: Tipografía serif para documento
- Estética: Editorial clásico
- Ideal para: Escritores, sensación "libro"

### 4.2 Store de Tema

El archivo `src/stores/theme.ts` gestiona todas las configuraciones de apariencia:

**Configuraciones disponibles**:

| Setting | Opciones | Default |
|---------|----------|---------|
| `preset` | aura, lara, material, nora, nord, dracula, grammarly, scrivener | aura |
| `primaryColor` | 12 colores | #3B82F6 |
| `mode` | light, dark, auto | auto |
| `fontSize` | small, medium, large, xlarge | medium |
| `lineHeight` | compact, normal, relaxed, loose | normal |
| `radius` | none, small, medium, large | medium |
| `compactness` | compact, normal, comfortable | normal |
| `reducedMotion` | boolean | false |

### 4.3 Implementacion del Dark Mode

1. **Deteccion automatica**: `window.matchMedia('(prefers-color-scheme: dark)')`
2. **Clase en HTML**: Se agrega/remueve `.dark` del `documentElement`
3. **PrimeVue**: Configurado con `darkModeSelector: '.dark'`
4. **CSS Custom Properties**: Variables diferentes para `.dark`

### 4.4 Mejoras Propuestas

#### 4.4.1 Transiciones de Tema

```css
/* Ya implementado en themes.css */
html.theme-transition,
html.theme-transition *,
html.theme-transition *:before,
html.theme-transition *:after {
  transition: background-color 0.3s ease,
              color 0.3s ease,
              border-color 0.3s ease !important;
}
```

**Uso**:
```typescript
function toggleDarkMode() {
  document.documentElement.classList.add('theme-transition')
  // Cambiar tema
  setTimeout(() => {
    document.documentElement.classList.remove('theme-transition')
  }, 300)
}
```

#### 4.4.2 Sistema de Temas Personalizados

Propuesta para permitir temas personalizados por usuario:

```typescript
interface CustomTheme {
  id: string
  name: string
  basePreset: ThemePreset
  colors: {
    primary: string
    success?: string
    warning?: string
    error?: string
    info?: string
  }
  overrides?: Record<string, string>
}
```

#### 4.4.3 Persistencia Mejorada

Actualmente se usa `localStorage`. Considerar:

- Sincronizacion con backend para preferencias de usuario
- Exportar/importar configuracion de tema
- Perfiles de tema (Trabajo, Lectura, Presentacion)

---

## 5. Guia de Implementacion

### 5.1 Estructura de Archivos

```
frontend/src/
├── assets/
│   ├── design-system/
│   │   ├── tokens.css           # Variables CSS (tokens)
│   │   ├── components.css       # Estilos base de componentes
│   │   ├── utilities.css        # Clases de utilidad
│   │   └── animations.css       # Animaciones y transiciones
│   ├── main.css                 # Reset y estilos globales
│   ├── themes.css               # Variables de tema
│   └── primevue-overrides.css   # Personalizaciones PrimeVue
├── components/
│   └── ds/                      # Componentes del Design System
│       ├── DsBadge.vue
│       ├── DsCard.vue
│       ├── DsInput.vue
│       └── ...
└── stores/
    └── theme.ts                 # Gestion de tema
```

### 5.2 Orden de Carga de CSS

1. `main.css` - Reset y base
2. PrimeVue theme (via config)
3. `themes.css` - Variables de tema app
4. `design-system/tokens.css` - Tokens
5. `design-system/components.css` - Componentes base
6. `design-system/utilities.css` - Utilidades
7. `animations.css` - Animaciones
8. `primevue-overrides.css` - Overrides (ULTIMO)

### 5.3 Convencion de Nombres

**CSS Classes**:
- Prefijo: `ds-` para Design System
- BEM: `ds-component__element--modifier`

**CSS Variables**:
- Tokens: `--ds-{category}-{name}` (ej: `--ds-space-4`)
- Componentes: `--ds-{component}-{property}` (ej: `--ds-btn-padding`)

**Componentes Vue**:
- Prefijo: `Ds` (ej: `DsBadge.vue`, `DsCard.vue`)

### 5.4 Uso en Componentes

```vue
<template>
  <div class="ds-card ds-card--interactive">
    <div class="ds-card__header">
      <i class="pi pi-user ds-card__header-icon"></i>
      <h3 class="ds-card__header-title">{{ title }}</h3>
    </div>
    <div class="ds-card__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
/* Usar tokens del Design System */
.custom-element {
  padding: var(--ds-space-4);
  background: var(--ds-surface-50);
  border-radius: var(--ds-radius-md);
}
</style>
```

### 5.5 Accesibilidad

1. **Focus visible**: Todos los elementos interactivos deben tener focus ring
2. **Contraste**: Minimo 4.5:1 para texto normal, 3:1 para grande
3. **Reduced motion**: Respetar preferencia del usuario
4. **Keyboard navigation**: Tab order logico, atajos documentados

```css
/* Ya implementado */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Apendice A: Mapeo de Colores de Entidad a Iconos

| Tipo | Color | Icono PrimeIcons |
|------|-------|------------------|
| CHARACTER | Morado | `pi-user` |
| LOCATION | Verde azulado | `pi-map-marker` |
| ORGANIZATION | Azul | `pi-building` |
| OBJECT | Naranja | `pi-box` |
| EVENT | Purpura | `pi-calendar` |
| ANIMAL | Verde bosque | `pi-heart` |
| CREATURE | Violeta | `pi-moon` |
| BUILDING | Marron | `pi-home` |
| REGION | Verde oliva | `pi-globe` |
| VEHICLE | Gris azulado | `pi-car` |
| FACTION | Rojo | `pi-flag` |
| FAMILY | Rosa | `pi-users` |
| TIME_PERIOD | Indigo | `pi-clock` |
| CONCEPT | Cyan | `pi-lightbulb` |
| RELIGION | Dorado | `pi-star` |
| MAGIC_SYSTEM | Magenta | `pi-sparkles` |
| WORK | Gris | `pi-book` |
| TITLE | Ambar | `pi-id-card` |
| LANGUAGE | Teal | `pi-comments` |
| OTHER | Gris neutro | `pi-tag` |

---

## Apendice B: Severidades de PrimeVue

Mapeo de severidades de la aplicacion a valores de PrimeVue:

| App Severity | PrimeVue Severity | Uso |
|--------------|-------------------|-----|
| critical | danger | Alertas criticas |
| warning | warning | Advertencias |
| info | info | Informacion |
| hint | secondary | Sugerencias |
| success | success | Exito |
| open | warning | Estado abierto |
| resolved | success | Estado resuelto |
| dismissed | secondary | Estado descartado |

---

## Changelog

### v1.0.0 (2026-01-13)
- Documentacion inicial del Design System
- Definicion de todos los tokens de diseno
- Especificacion de 11 componentes base
- Guia de integracion con PrimeVue 4
- Documentacion de soporte de temas
