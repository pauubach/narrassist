---
description: "Reglas para el frontend Vue 3 + TypeScript + PrimeVue. Aplicar al editar archivos en frontend/src/**."
globs: ["frontend/src/**/*.vue", "frontend/src/**/*.ts", "frontend/src/**/*.css"]
---

# Frontend Vue 3 — Reglas del proyecto

## Stack

- **Vue 3** con Composition API (`<script setup>`).
- **TypeScript** estricto — no `any` salvo último recurso documentado.
- **PrimeVue** como UI library (overrides en `assets/primevue-overrides.css`).
- **Vite** bundler.
- **Vitest** para tests.
- **Pinia / composables** para estado (no Vuex).

## Seguridad — XSS

- **PROHIBIDO** `v-html` con contenido derivado de manuscrito o de la API sin sanitizar.
- Texto del manuscrito → siempre `{{ }}` (texto interpolado, auto-escapado).
- Si hace falta resaltar (spans de alertas), construir DOM con `v-for` + `<span>`, no con `v-html`.

## Naming y casing

- **Archivos**: `PascalCase.vue` para componentes (`AlertList.vue`), `camelCase.ts` para composables/utils.
- **Componentes**: PascalCase en `<template>` (`<AlertList />`).
- **Props y emits**: camelCase en TS, kebab-case al pasar en template (`:alert-item="…"`).
- **CSS classes**: kebab-case.

## API ↔ Frontend

- Backend responde snake_case → **transformer** (`frontend/src/transformers/` o similar) convierte a camelCase.
- **NUNCA** consumir snake_case directamente en componentes — siempre pasar por el transformer.
- Tipos: `ApiXxx` (raw) → `Xxx` (domain), ver `/types`.
- Posiciones de alertas: `start_char/end_char` (API) → `spanStart/spanEnd` (domain).

## Estado

- Estado compartido → **Pinia store** en `stores/`.
- Estado local de componente → `ref`/`reactive` directo.
- Evitar prop drilling >2 niveles → considerar provide/inject o store.

## PrimeVue — patrones del proyecto

- Diálogos: `<Dialog>` con `v-model:visible`, `modal`, `:closable="true"` por defecto.
- Tablas: `<DataTable>` con `dataKey`, paginación server-side cuando los datos vienen paginados de la API.
- Iconos: clases `pi pi-*` (PrimeIcons), no otra librería.
- Dark mode: `assets/main.css` + `primevue-overrides.css` — no CSS inline de color.

## Accesibilidad

- `role="dialog"`, `aria-modal="true"` en modales custom.
- `aria-label` en botones con solo icono.
- Escape cierra modales; backdrop click cierra salvo que se indique lo contrario.
- Contraste suficiente en ambos temas (light y dark).

## Componentes — tamaño

- Target < 300 líneas por componente. Si crece más → extraer sub-componentes o composables.
- Lógica reutilizable → `composables/useXxx.ts`.

## Estilos

- Preferir clases utility definidas en `main.css`/`primevue-overrides.css` antes que estilos inline o `<style scoped>` grande.
- **Evitar** `!important` — si lo necesitas, entender por qué PrimeVue override no gana especificidad.
- Animaciones: CSS transitions, no librerías externas (Framer Motion, GSAP).

## Tests (Vitest)

- `*.test.ts` junto al archivo o en `__tests__/` adyacente.
- Mount components con `@vue/test-utils`.
- Mock de `fetch` / API clients con `vi.mock`.
- **Nunca** tests que hagan requests reales a Ollama, backend local o internet.

## Internacionalización

- Si el proyecto usa i18n (revisar `vue-i18n` en `package.json` antes de asumir) → todas las cadenas en locale files, no hardcodeadas.
- Si no usa i18n todavía → cadenas en español en templates, preparadas para extracción futura (evitar template literals con lógica en medio).

## Supresiones prohibidas

- **NO** `// @ts-ignore`, **NO** `// eslint-disable-next-line`, **NO** `// @ts-expect-error` para silenciar. Arreglar el tipo/regla o justificar en PR con link al issue si es bug de herramienta.
