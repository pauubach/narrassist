# Frontend Unit Testing Setup - Pendiente de Configuración npm

**Fecha**: 2026-02-22
**Estado**: ⏸️ BLOQUEADO (npm no disponible en bash)
**Prioridad**: Alta

---

## Problema

El proyecto frontend (Vue 3 + TypeScript) no tiene tests unitarios:
- **121 componentes Vue** sin archivos `.spec.ts` correspondientes
- **0 tests** de componentes críticos (DocumentViewer, ProjectSummary, DialogueAttributionPanel)
- **Sin framework de testing** configurado

---

## Requisitos Previos

### 1. Instalación de Node.js/npm

**Windows**:
```bash
# Descargar e instalar desde https://nodejs.org/
# O usar nvm-windows:
nvm install 20
nvm use 20
```

**Verificar instalación**:
```bash
node --version  # v20.x.x
npm --version   # 10.x.x
```

### 2. Framework de Testing Recomendado

**Vitest** (recomendado para Vue 3 + Vite):
- Más rápido que Jest
- Integración nativa con Vite
- Soporte completo para TypeScript + Vue 3

**Alternativa**: Jest + Vue Test Utils

---

## Setup Inicial (Cuando npm esté disponible)

### Paso 1: Instalar Dependencias

```bash
cd frontend

# Vitest + Vue Test Utils
npm install -D vitest @vue/test-utils @vitest/ui happy-dom

# TypeScript support
npm install -D @types/node

# Coverage
npm install -D @vitest/coverage-v8
```

### Paso 2: Configurar Vitest

Crear `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/**/*.spec.ts',
        'src/test/**',
        'src/main.ts',
        'src/App.vue',
      ],
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
```

### Paso 3: Crear Setup de Tests

Crear `frontend/src/test/setup.ts`:

```typescript
import { config } from '@vue/test-utils'
import PrimeVue from 'primevue/config'

// Mock de PrimeVue
config.global.plugins = [PrimeVue]

// Mock de router
config.global.mocks = {
  $route: {
    params: {},
    query: {},
  },
  $router: {
    push: vi.fn(),
    replace: vi.fn(),
  },
}

// Mock de API calls (si es necesario)
global.fetch = vi.fn()
```

### Paso 4: Añadir Scripts a package.json

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "test:run": "vitest run"
  }
}
```

---

## Tests Prioritarios (60+ tests estimados)

### Componentes Críticos (Alta Prioridad)

#### 1. DocumentViewer.vue (~15 tests)
- **Rendering**: Carga de capítulos, lazy loading
- **Highlights**: Aplicación de spans, navegación por alertas
- **Cache**: LRU cache clearing, performance
- **Edge cases**: Capítulos vacíos, texto largo, caracteres especiales

```typescript
// frontend/src/components/DocumentViewer.spec.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DocumentViewer from './DocumentViewer.vue'

describe('DocumentViewer', () => {
  it('renders chapter content correctly', async () => {
    const wrapper = mount(DocumentViewer, {
      props: {
        chapters: [{ id: 1, number: 1, content: 'Test content' }],
      },
    })
    expect(wrapper.text()).toContain('Test content')
  })

  it('applies alert highlights to text', async () => {
    const wrapper = mount(DocumentViewer, {
      props: {
        chapters: [{ id: 1, number: 1, content: 'Error here' }],
        alerts: [
          { spanStart: 0, spanEnd: 5, severity: 'high' }
        ],
      },
    })
    const highlight = wrapper.find('.alert-highlight')
    expect(highlight.exists()).toBe(true)
    expect(highlight.classes()).toContain('severity-high')
  })

  // ... 13 tests más
})
```

#### 2. ProjectSummary.vue (~12 tests)
- **Stats cards**: Renderizado de métricas
- **Chapter summaries**: Resúmenes de capítulos
- **Empty state**: Proyecto sin datos
- **Loading states**: Carga de datos

#### 3. DialogueAttributionPanel.vue (~10 tests)
- **Attribution editing**: Corrección de atribuciones
- **Visual states**: Editing state, hover
- **API calls**: Guardar correcciones
- **Error handling**: Fallos de red

#### 4. EntityInspector.vue (~8 tests)
- **Entity details**: Renderizado de detalles
- **Mention navigation**: Loading states, navegación
- **Attributes**: Mostrar atributos del personaje
- **Empty state**: Entidad sin menciones

#### 5. ChapterInspector.vue (~7 tests)
- **Timeline events**: Renderizado de eventos
- **Character navigation**: Navegación por personajes
- **Empty state**: Capítulo sin eventos

### Utilidades y Transformers (Media Prioridad)

#### 6. API Transformers (~10 tests)
```typescript
// frontend/src/api/transformers/alert.spec.ts
import { describe, it, expect } from 'vitest'
import { transformAlert } from './alert'

describe('Alert Transformer', () => {
  it('transforms snake_case to camelCase', () => {
    const apiAlert = {
      id: 1,
      alert_type: 'consistency',
      span_start: 100,
      span_end: 150,
    }
    const domainAlert = transformAlert(apiAlert)
    expect(domainAlert.alertType).toBe('consistency')
    expect(domainAlert.spanStart).toBe(100)
    expect(domainAlert.spanEnd).toBe(150)
  })

  // ... 9 tests más
})
```

### Composables (Media Prioridad)

#### 7. useAlerts.ts (~8 tests)
- **Fetching**: Llamadas a API
- **Caching**: Cache de alertas
- **Filtering**: Filtrado por tipo/severidad
- **Error handling**: Manejo de errores

---

## Comandos de Testing

### Desarrollo
```bash
# Watch mode (re-ejecuta al cambiar archivos)
npm run test

# UI interactiva
npm run test:ui
```

### CI/CD
```bash
# Single run con coverage
npm run test:coverage

# Solo tests específicos
npm run test -- DocumentViewer.spec.ts
```

### Coverage Esperado

| Componente | Tests | Coverage Target |
|------------|-------|-----------------|
| DocumentViewer | 15 | > 80% |
| ProjectSummary | 12 | > 75% |
| DialogueAttributionPanel | 10 | > 70% |
| EntityInspector | 8 | > 70% |
| ChapterInspector | 7 | > 70% |
| Transformers | 10 | > 90% |
| **TOTAL** | **62** | **> 75%** |

---

## Plantilla de Test

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import ComponentName from './ComponentName.vue'

describe('ComponentName', () => {
  let wrapper: VueWrapper

  beforeEach(() => {
    wrapper = mount(ComponentName, {
      props: {
        // Props del componente
      },
      global: {
        stubs: {
          // Componentes a mockear
          'PrimeVueDialog': true,
        },
        mocks: {
          // Mocks globales
        },
      },
    })
  })

  afterEach(() => {
    wrapper.unmount()
  })

  it('renders correctly', () => {
    expect(wrapper.exists()).toBe(true)
  })

  it('handles user interaction', async () => {
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update')).toBeTruthy()
  })

  // ... más tests
})
```

---

## Próximos Pasos

1. **Configurar npm en el entorno** (bloqueante)
2. **Instalar Vitest + dependencias** (Paso 1)
3. **Configurar vitest.config.ts** (Paso 2)
4. **Crear tests de DocumentViewer** (15 tests, alta prioridad)
5. **Crear tests de ProjectSummary** (12 tests)
6. **Crear tests de DialogueAttributionPanel** (10 tests)
7. **Crear tests de transformers** (10 tests)
8. **Añadir coverage a CI/CD** (GitHub Actions)

---

## Referencias

- **Auditoría Fase 3**: `docs/AUDIT_2026_02_22_FASE3.md` (líneas 96-166)
- **Issue Frontend Testing**: QA encontró gaps de testing
- **Vitest Docs**: https://vitest.dev/
- **Vue Test Utils**: https://test-utils.vuejs.org/

---

**Estado**: ⏸️ Bloqueado hasta configurar npm en bash
**Estimación**: 3-4 días una vez desbloqueado
**Prioridad**: Alta (0 tests actualmente)

---

**Generado**: 2026-02-22
**Autor**: Claude Sonnet 4.5
**Revisión**: Frontend Testing Setup Guide
