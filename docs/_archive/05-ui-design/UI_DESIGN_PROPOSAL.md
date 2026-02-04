# Propuesta de Diseño de Interfaz - Narrative Assistant

> **Documento generado:** 2026-01-09
> **Versión:** 1.0
> **Estado:** Propuesta para revisión

---

## Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Análisis del Backend Actual](#análisis-del-backend-actual)
3. [Estado del Arte en Herramientas de Edición](#estado-del-arte)
4. [Stack Tecnológico Recomendado](#stack-tecnológico)
5. [Arquitectura de la UI](#arquitectura-ui)
6. [Diseño de Flujos de Usuario](#flujos-de-usuario)
7. [Componentes y Patrones de UI](#componentes)
8. [Roadmap de Implementación](#roadmap)
9. [Referencias y Fuentes](#referencias)

---

## 1. Resumen Ejecutivo {#resumen-ejecutivo}

### Objetivo del Documento

Este documento define la interfaz de usuario (UI) de **Narrative Assistant**, una herramienta offline para correctores literarios profesionales que analiza manuscritos de ficción detectando inconsistencias narrativas.

### Recomendaciones Principales

**Stack Tecnológico:**
- **Desktop Framework:** Tauri 2.0 (Rust + WebView nativa)
- **Frontend:** Vue 3 + TypeScript + Vite
- **UI Library:** PrimeVue 3.x
- **Integración Backend:** FastAPI Local Server (localhost:8008) + PyInstaller Sidecar
- **Visualización:** Cytoscape.js (grafos), Recogito (anotaciones de texto)

**Arquitectura:**
- Layout de tres paneles (Sidebar + Editor Central + Inspector)
- Disponibilidad progresiva de resultados durante análisis
- Navegación bidireccional: Documento ↔ Alertas ↔ Entidades

**Prioridades de Diseño:**
1. **Transparencia:** Mostrar siempre confianza del sistema y fuentes
2. **Eficiencia:** Optimizar para flujo de revisión diario (100+ alertas/sesión)
3. **Seguridad:** 100% offline, datos nunca salen de la máquina
4. **Profesionalismo:** Diseño sobrio, funcional, sin distracciones

---

## 2. Análisis del Backend Actual {#análisis-del-backend-actual}

### 2.1. Estado de Implementación

**Backend completado al 90%:**
- ✅ **Core:** Configuración, errors, Result pattern (1,049 líneas)
- ✅ **Parsers:** DOCX, TXT, MD + estructura (1,388 líneas)
- ✅ **Persistencia:** SQLite, proyectos, sesiones, historial (1,744 líneas)
- ✅ **NLP:** NER, diálogos, atributos, correferencia (3,212 líneas)
- ✅ **Entidades:** Modelos, repositorio, fusión (1,447 líneas)
- ✅ **Análisis:** Consistencia de atributos (710 líneas)
- ✅ **Alertas:** Motor completo con filtrado (997 líneas)
- ✅ **Pipeline:** Integración end-to-end (780 líneas)

**Total:** ~12,089 líneas Python implementadas y funcionales.

**Bloqueantes:**
- ❌ Tests unitarios (0% coverage) - **CRÍTICO**
- 🟡 Exportación avanzada (fichas personajes, hoja estilo) - Importante

### 2.2. APIs Disponibles para la UI

#### Gestión de Proyectos

```python
ProjectManager:
  - create_from_document(text, name, format, path) -> Result[Project]
  - get_all() -> Result[list[Project]]
  - get_by_id(project_id) -> Result[Project]
  - update(project) -> Result[Project]
  - delete(project_id) -> Result[bool]
```

**Datos del proyecto:**
- Metadatos: nombre, descripción, formato, fingerprint
- Estadísticas: palabra count, capítulos, estado de análisis
- Progreso: `analysis_progress` (0.0 - 1.0)
- Timestamps: creación, última modificación, última apertura

#### Pipeline de Análisis

```python
run_full_analysis(
    document_path: Path,
    project_name: str = None,
    config: PipelineConfig = None
) -> Result[AnalysisReport]

# Fases del análisis:
1. Parsing (2s)          → Extracción de texto
2. Structure (3s)        → Capítulos y escenas
3. NER (10s)            → Entidades (personajes, lugares)
4. Attributes (30s)     → Extracción de atributos
5. Consistency (10s)    → Detección de contradicciones
6. Alerts (5s)          → Generación de alertas

# Tiempo total estimado: ~60s para 80k palabras
```

#### Entidades

```python
EntityRepository (singleton):
  - get_by_project(project_id) -> Result[list[Entity]]
  - get_by_id(entity_id) -> Result[Entity]
  - search_by_name(project_id, name) -> Result[list[Entity]]
  - merge_entities(entity_ids, canonical_name) -> Result[Entity]
  - update(entity) -> Result[Entity]

# 19 tipos de entidad soportados:
CHARACTER, ANIMAL, CREATURE, LOCATION, BUILDING, REGION,
OBJECT, VEHICLE, ORGANIZATION, FACTION, FAMILY, EVENT,
TIME_PERIOD, CONCEPT, RELIGION, MAGIC_SYSTEM, WORK,
TITLE, LANGUAGE, CUSTOM
```

#### Sistema de Alertas

```python
AlertEngine (singleton):
  - create_alert(...) -> Result[Alert]
  - get_alerts_by_project(project_id, filter) -> Result[list[Alert]]
  - update_status(alert_id, status, note) -> Result[Alert]
  - dismiss_alert(alert_id, reason) -> Result[Alert]
  - resolve_alert(alert_id, note) -> Result[Alert]
  - get_summary(project_id) -> Result[dict]

# Categorías de alertas:
CONSISTENCY, STYLE, FOCALIZATION, STRUCTURE, WORLD, ENTITY, OTHER

# Severidades:
CRITICAL, WARNING, INFO, HINT

# Estados:
NEW → OPEN → ACKNOWLEDGED → IN_PROGRESS → RESOLVED/DISMISSED
```

#### Exportación

```python
export_report_json(report, output_path) -> Result[Path]
export_report_markdown(report, output_path) -> Result[Path]
export_alerts_json(alerts, output_path) -> Result[Path]

# Pendiente de implementar:
- export_character_sheets() (STEP 7.2)
- export_style_guide() (STEP 7.3)
```

### 2.3. Modelos de Datos Clave

```typescript
// Para la UI (TypeScript)

interface Project {
  id: number;
  name: string;
  description?: string;
  document_path?: string;
  document_format: "docx" | "txt" | "md";
  word_count: number;
  chapter_count: number;
  analysis_status: "pending" | "analyzing" | "completed" | "error";
  analysis_progress: number; // 0.0 - 1.0
  created_at: string;
  updated_at: string;
  last_opened_at?: string;
}

interface Entity {
  id: number;
  project_id: number;
  entity_type: string;
  canonical_name: string;
  aliases: string[];
  importance: "protagonist" | "secondary" | "minor" | "mentioned";
  mention_count: number;
  first_appearance_char: number;
  validated_by_user: boolean;
}

interface Attribute {
  id: number;
  entity_id: number;
  attribute_type: "physical" | "psychological" | "social" | "background";
  attribute_key: string;
  value: string;
  source_chapter?: number;
  source_excerpt: string;
  confidence: number; // 0.0 - 1.0
  validated_by_user: boolean;
}

interface Alert {
  id: number;
  project_id: number;
  category: "consistency" | "style" | "focalization" | "structure" | "world" | "entity";
  severity: "critical" | "warning" | "info" | "hint";
  title: string;
  description: string;
  explanation: string;
  suggestion?: string;
  chapter?: number;
  excerpt: string;
  entity_ids: number[];
  confidence: number;
  status: "new" | "open" | "acknowledged" | "in_progress" | "resolved" | "dismissed";
  created_at: string;
}

interface AnalysisProgress {
  project_id: number;
  current_phase: "parsing" | "structure" | "ner" | "coreference" |
                 "attributes" | "consistency" | "complete" | "error";
  phase_progress: number; // 0.0 - 1.0
  overall_progress: number; // 0.0 - 1.0
  chapters_found: number;
  entities_found: number;
  alerts_generated: number;
  status_message: string;
  estimated_remaining?: number; // segundos
}
```

---

## 3. Estado del Arte en Herramientas de Edición {#estado-del-arte}

### 3.1. Herramientas Analizadas

#### Scrivener - Referente en Organización

**Fortalezas:**
- **Binder (panel izquierdo):** Organización jerárquica drag-and-drop
- **Corkboard view:** Visualización de alto nivel con tarjetas
- **Inspector (panel derecho):** Información contextual colapsable
- **Flexibilidad extrema:** Se adapta al proceso del escritor

**Lecciones para Narrative Assistant:**
- Panel izquierdo debe mostrar estructura de capítulos/escenas detectados
- Navegación rápida por jerarquía del manuscrito
- Herramientas auxiliares colapsables

#### ProWritingAid - Referente en Análisis en Tiempo Real

**Fortalezas:**
- **Highlights con código de color:** Subrayados para diferentes problemas
- **Sidebar flotante:** Panel no intrusivo con sugerencias
- **Cards individuales:** Accept/Dismiss con explicación detallada
- **Enfoque educativo:** Explica el porqué de cada sugerencia

**Lecciones:**
- Sistema de colores consistente (rojo=crítico, amarillo=warning, azul=info)
- Sidebar derecho con lista de alertas clicables
- Cards con contexto completo + botones claros
- Explicaciones pedagógicas, no solo marcar errores

#### Grammarly - Referente en Navegación de Sugerencias

**Fortalezas:**
- **Navegación secuencial:** Tour guiado desde inicio del documento
- **Click to jump:** Saltar directamente a texto subrayado
- **Acciones claras:** Accept/Dismiss/Learn more

**Lecciones:**
- Modo "tour guiado" para revisar alertas secuencialmente
- Modo "exploración libre" con lista clicable
- Paneles movibles para adaptarse a pantallas pequeñas

### 3.2. Patrones de UI Identificados

#### Sistema de Highlights Recomendado

```
🔴 Rojo/Rosa:     Inconsistencias críticas (atributos contradictorios)
🟡 Amarillo:      Advertencias (variantes de grafía, posibles errores)
🔵 Azul:          Información (entidades detectadas, atributos)
🟣 Morado:        Repeticiones léxicas/semánticas
🟢 Verde:         Confirmaciones (fusiones, alertas resueltas)
```

**Implementación:**
- Underline ondulado bajo el texto (no bloque completo)
- Tooltip al hover con resumen breve
- Clic abre tarjeta completa en sidebar

#### Navegación Documento ↔ Problemas

**Dos modos complementarios:**

1. **Modo Documento-Primero:**
   - Usuario lee y encuentra highlights inline
   - Clic en highlight → sidebar muestra detalle

2. **Modo Alertas-Primero:**
   - Usuario revisa lista de problemas
   - Clic en alerta → scroll automático al texto + highlight

**Sincronización bidireccional:**
- Scroll en documento actualiza lista de alertas
- Selección en alertas hace scroll suave al texto

#### Gestión de Falsos Positivos

**Nivel 1 - Quick Actions:**
- Right-click en highlight → menú contextual:
  - "Ignorar esta ocurrencia"
  - "Ignorar en todo el documento"
  - "Ignorar para esta entidad"

**Nivel 2 - Panel de Configuración:**
- Checkboxes para enable/disable familias de heurísticas
- Ajustar umbrales de confianza

**Nivel 3 - Historial:**
- Panel "Alertas Ignoradas" con lista filtrable
- Botón "Restaurar" para reactivar

---

## 4. Stack Tecnológico Recomendado {#stack-tecnológico}

### 4.1. Decisión Principal: Tauri 2.0

**Tauri vs Electron:**

| Aspecto | Tauri | Electron | Ganador |
|---------|-------|----------|---------|
| Bundle size | 3-10 MB | 85-120 MB | **Tauri** |
| Memoria (idle) | 30-40 MB | 200-300 MB | **Tauri** |
| Cold start | <0.5s | 1-2s | **Tauri** |
| Seguridad | Rust + IPC explícito | Node.js + Chromium | **Tauri** |
| Ecosistema | Menor | Mayor | Electron |
| Madurez | v2.0 (2024) | Muy maduro | Electron |

**Razones para Tauri:**
- **Tamaño crítico:** Distribución profesional requiere paquetes pequeños
- **Memoria:** Correctores mantienen app abierta todo el día
- **Seguridad:** Arquitectura Rust alineada con requisito de confidencialidad
- **WebView nativa:** Usa WebView2 (Windows) / WKWebView (macOS)

### 4.2. Frontend: Vue 3 + TypeScript

**Vue 3 vs React vs Svelte:**

| Criterio | Vue 3 | React | Svelte |
|----------|-------|-------|--------|
| Curva de aprendizaje | Baja | Media | Baja |
| Performance | Excelente | Buena | Excelente |
| Ecosistema UI | Rico | Muy rico | Menor |
| TypeScript | Excelente | Excelente | Bueno |
| Bundle size | 50KB | 130KB | 10KB |

**Razones para Vue 3:**
- Ya mencionado en CLAUDE.md ("Tauri + Vue 3 post-MVP")
- Composition API ergonómica para apps complejas
- Single File Components ideal para componentes con mucho estado
- Ecosistema maduro (Vuetify, PrimeVue)

### 4.3. UI Library: PrimeVue

**PrimeVue vs Vuetify vs Quasar:**

| Componente | Vuetify | Quasar | PrimeVue | Ganador |
|------------|---------|--------|----------|---------|
| DataTable | Básica | Media | **Avanzada** | PrimeVue |
| Tree | Sí | Sí | Sí | Empate |
| Customización | Material Design | Material Design | **Flexible** | PrimeVue |
| Componentes | 80+ | 90+ | 160+ | PrimeVue |

**Razones:**
- 160+ componentes enterprise-grade
- DataTable con virtualización (crítico para listas grandes)
- Temas flexibles (no bloqueado a Material Design)
- Performance optimizado para tablas de miles de filas

### 4.4. Integración Backend: FastAPI Sidecar

**Arquitectura:**

```
┌─────────────────────────────────────────┐
│ Tauri App (Vue 3 Frontend)             │
│   WebView → localhost:8008              │
└─────────────────────────────────────────┘
                ↕ HTTP/WebSocket
┌─────────────────────────────────────────┐
│ Python Backend (PyInstaller Sidecar)    │
│   FastAPI Server (port 8008)            │
│   narrative_assistant modules           │
└─────────────────────────────────────────┘
```

**Ventajas del patrón Sidecar:**
- Backend Python NO requiere reescritura
- FastAPI proporciona REST + WebSocket
- Debugging independiente de frontend
- Aislamiento: fallos en Python no crashean UI

**Gestión de lifecycle:**

```rust
// src-tauri/src/main.rs
#[tauri::command]
async fn start_backend() -> Result<(), String> {
    Command::new_sidecar("narrative-assistant-backend")
        .spawn()
        .expect("Failed to spawn backend");
    Ok(())
}
```

**Comunicación:**

```javascript
// Frontend (Vue 3)
import axios from 'axios';

const api = axios.create({ baseURL: 'http://localhost:8008/api' });

// REST para CRUD
const projects = await api.get('/projects');

// WebSocket para progreso
const ws = new WebSocket('ws://localhost:8008/ws/analysis/1');
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  progressBar.value = progress.overall_progress;
};
```

### 4.5. Librerías Especializadas

**Anotaciones de texto:**
```javascript
import { TextAnnotator } from '@recogito/text-annotator-js';
// Highlights inline con tooltips
```

**Grafos de relaciones:**
```javascript
import cytoscape from 'cytoscape';
// Visualización de relaciones entre entidades
```

**Charts:**
```javascript
import { Chart } from 'chart.js';
// Gráficos de estadísticas y progreso
```

### 4.6. Stack Completo

```json
{
  "framework": "Tauri 2.0",
  "frontend": "Vue 3.4+ + TypeScript 5.x",
  "build": "Vite 5.x",
  "ui": "PrimeVue 3.50+",
  "state": "Pinia 2.1",
  "router": "Vue Router 4.2",
  "backend": "FastAPI + PyInstaller Sidecar",
  "specializedLibs": [
    "@recogito/text-annotator-js",
    "cytoscape",
    "chart.js"
  ]
}
```

---

## 5. Arquitectura de la UI {#arquitectura-ui}

### 5.1. Layout Principal: Three-Pane

```
┌─────────────────────────────────────────────────────────────────┐
│ TITLE BAR: Narrative Assistant - Proyecto: mi_novela.docx      │
├─────────────────────────────────────────────────────────────────┤
│ MENU: Archivo  Edición  Ver  Análisis  Exportar  Ayuda         │
├──────────────┬──────────────────────────────────┬───────────────┤
│              │                                  │               │
│   SIDEBAR    │      EDITOR PRINCIPAL            │  INSPECTOR    │
│   (250px)    │      (flex)                      │  (350px)      │
│              │                                  │               │
│ ┌──────────┐ │  Capítulo 1                      │ 📋 ALERTAS   │
│ │ Tabs:    │ │                                  │               │
│ │          │ │  —Hola —dijo María.              │ 🔴 3 Críticas│
│ ├──────────┤ │  Ella tenía los ojos verdes.     │ 🟡 12 Avisos │
│ │📖 Caps   │ │           ^^^^^^ 🔴              │ 🔵 32 Info   │
│ │  Cap.1   │ │                                  │              │
│ │  Cap.2   │ │  ...más tarde...                 │ [Filtros...] │
│ │  Cap.3   │ │                                  │              │
│ ├──────────┤ │  —Qué ojos tan azules —dijo...  │ [Lista de    │
│ │👤 Pers.  │ │           ^^^^^^ 🔴              │  alertas]    │
│ │  María   │ │                                  │              │
│ │  Juan    │ │                                  │              │
│ │  Ana     │ │                                  │              │
│ ├──────────┤ │                                  │              │
│ │📍 Lugares│ │                                  │              │
│ │  Madrid  │ │                                  │              │
│ └──────────┘ │                                  │              │
│              │                                  │              │
├──────────────┴──────────────────────────────────┴───────────────┤
│ STATUS BAR: [████░░░░] 65% Analizando... | 45 pers. | 12 alert.│
└─────────────────────────────────────────────────────────────────┘
```

**Razones del diseño:**

1. **Sidebar izquierdo (250-300px, colapsable):**
   - Navegación primaria con tabs
   - Vista de árbol para capítulos/escenas
   - Lista de entidades con búsqueda

2. **Editor central (máximo espacio):**
   - Texto del manuscrito (read-only en MVP)
   - Highlights inline con tooltips
   - Scroll sincronizado con paneles laterales

3. **Inspector derecho (300-400px, colapsable):**
   - Panel de alertas principal
   - Filtros y búsqueda
   - Detalles de entidad seleccionada

4. **Status bar (bottom):**
   - Barra de progreso durante análisis
   - Métricas en tiempo real
   - Indicadores de estado

### 5.2. Estructura de Vistas

```
/
├── Dashboard (Vista inicial)
│   ├── ProjectList
│   ├── CreateProjectDialog
│   └── RecentProjects
│
├── ProjectView (Vista principal)
│   ├── Sidebar
│   │   ├── ChapterTree (navegación capítulos)
│   │   ├── EntityList (personajes, lugares)
│   │   └── TimelineView (opcional post-MVP)
│   │
│   ├── EditorPanel (centro)
│   │   ├── ManuscriptViewer (texto con highlights)
│   │   ├── ChapterNavigation
│   │   └── Search
│   │
│   ├── InspectorPanel (derecha)
│   │   ├── AlertsPanel
│   │   │   ├── AlertFilters
│   │   │   ├── AlertList
│   │   │   └── AlertDetail
│   │   └── EntityDetails
│   │       ├── AttributesTable
│   │       └── MentionsList
│   │
│   └── AnalysisProgress (overlay durante análisis)
│       ├── ProgressBar
│       ├── PhaseIndicator
│       └── PartialResults
│
└── ExportView
    ├── ExportOptions
    └── PreviewPanel
```

### 5.3. State Management (Pinia)

```typescript
// stores/project.ts
export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null as Project | null,
    projects: [] as Project[],
    isAnalyzing: false
  }),

  actions: {
    async loadProjects() {
      const response = await api.get('/projects');
      this.projects = response.data;
    },

    async createProject(file: File, name: string) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', name);
      const response = await api.post('/projects', formData);
      this.currentProject = response.data;
    }
  }
});

// stores/entities.ts
export const useEntitiesStore = defineStore('entities', {
  state: () => ({
    entities: [] as Entity[],
    currentEntity: null as Entity | null
  }),

  actions: {
    async loadEntities(projectId: number) {
      const response = await api.get(`/projects/${projectId}/entities`);
      this.entities = response.data;
    },

    async mergeEntities(ids: number[], canonicalName: string) {
      await api.post('/entities/merge', { ids, canonicalName });
      await this.loadEntities(this.currentProject.id);
    }
  }
});

// stores/alerts.ts
export const useAlertsStore = defineStore('alerts', {
  state: () => ({
    alerts: [] as Alert[],
    filter: {} as AlertFilter,
    summary: null as AlertSummary | null
  }),

  actions: {
    async loadAlerts(projectId: number) {
      const response = await api.get(`/projects/${projectId}/alerts`, {
        params: this.filter
      });
      this.alerts = response.data.alerts;
      this.summary = response.data.summary;
    },

    async resolveAlert(alertId: number, note: string) {
      await api.post(`/alerts/${alertId}/resolve`, { note });
      await this.loadAlerts(this.currentProject.id);
    }
  }
});

// stores/analysis.ts
export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    progress: null as AnalysisProgress | null,
    isRunning: false
  }),

  actions: {
    startListening(projectId: number) {
      const ws = new WebSocket(`ws://localhost:8008/ws/analysis/${projectId}`);

      ws.onmessage = (event) => {
        this.progress = JSON.parse(event.data);
        this.isRunning = this.progress.current_phase !== 'complete';
      };

      ws.onerror = () => {
        this.isRunning = false;
      };
    }
  }
});
```

---

## 6. Diseño de Flujos de Usuario {#flujos-de-usuario}

### 6.1. Flujo: Onboarding (Primera vez)

**Objetivo:** Usuario entiende la herramienta y verifica que funciona.

```
1. Lanzar aplicación
   └─> Pantalla de bienvenida automática

2. Verificación de licencia (única conexión a internet)
   ├─> Usuario introduce código
   ├─> Sistema verifica
   └─> Si falla: modo offline temporal o bloqueo

3. Verificación de entorno (automática)
   ├─> Modelos NLP presentes
   ├─> GPU/CPU detectado
   ├─> Espacio en disco
   └─> Resultado: ✅ Todo OK / ⚠️ Warnings

4. Tutorial interactivo (OPCIONAL)
   ├─> "Analizar ejemplo de 5 páginas"
   ├─> Análisis en ~15 segundos
   └─> Usuario ve: capítulos, personajes, alertas

5. Acciones disponibles:
   ├─> "Crear mi primer proyecto" (CTA principal)
   ├─> "Ver documentación"
   └─> "Omitir tutorial"
```

**Decisiones críticas:**
- Tutorial opcional pero muy visible
- Verificación de licencia clara y transparente
- Ejemplo corto (no abrumar)

**Puntos de fricción:**
- Licencia falla → Modo temporal + instrucciones
- Modelos no detectados → Script de reparación
- Usuario confundido → Video explicativo 30s

### 6.2. Flujo: Crear/Abrir Proyecto

**Objetivo:** Importar manuscrito e iniciar análisis.

```
1. Pantalla "Nuevo Proyecto"
   ├─> Nombre: [Auto-sugerido del archivo]
   ├─> Importar: [Botón "Seleccionar DOCX/TXT/MD"]
   └─> Vista previa al seleccionar:
       ├─> Tamaño: 82,453 palabras
       ├─> Formato: DOCX
       ├─> Tiempo estimado: ~2-4 minutos
       └─> ⚠️ Advertencia si muy grande (>150k)

2. Configuración avanzada (panel colapsado)
   ├─> ✅ Estructura (capítulos, escenas)
   ├─> ✅ Personajes y lugares (NER)
   ├─> ✅ Atributos y consistencia
   ├─> ✅ Diálogos
   ├─> ⬜ Repeticiones (lento)
   └─> ⬜ Análisis temporal (experimental)

3. Botón "Iniciar análisis"
   └─> Sistema crea proyecto + inicia pipeline
```

**Decisiones críticas:**
- Configuración simple por defecto
- Vista previa crítica para confianza
- Estimación de tiempo basada en hardware
- Defaults inteligentes (todo marcado)

**Puntos de fricción:**
- Archivo muy grande → Warning + sugerencia de dividir
- Formato no soportado → Mensaje + guía
- Usuario inseguro → Tooltips en opciones
- Estructura no estándar → Permitir config manual

### 6.3. Flujo: Análisis en Progreso

**Objetivo:** Mostrar progreso en tiempo real + disponibilidad progresiva.

```
┌─────────────────────────────────────────────────────────────┐
│ Proyecto: "Los herederos del alba" - Analizando...         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [████████████░░░░░░░░] 65% - Extrayendo atributos...     │
│                                                             │
│  Progreso por fase:                                        │
│  ✅ Estructura (12 capítulos, 45 escenas)                 │
│  ✅ Personajes (8 principales)                            │
│  ✅ Diálogos (523 intervenciones)                         │
│  ⟳ Atributos en proceso... (124 extraídos)               │
│  ⏸ Consistencia en espera                                 │
│                                                             │
│  Tiempo: 1m 23s | Restante: ~47s                          │
│                                                             │
│  [Ya puedes revisar capítulos y personajes detectados]    │
│  [Ver resultados parciales]                                │
│                                                             │
│  [Cancelar]  [Minimizar y seguir trabajando]             │
└─────────────────────────────────────────────────────────────┘
```

**Disponibilidad progresiva:**
- **~10-15s:** Estructura y capítulos disponibles
- **~30-40s:** Entidades disponibles
- **~60-90s:** Alertas y atributos completos

**Decisiones críticas:**
- NO bloquear UI durante análisis
- Usuario puede navegar resultados parciales
- Cancelar mantiene resultados útiles
- Estimación actualizada dinámicamente

**Puntos de fricción:**
- Análisis muy lento → Opción de minimizar
- Error en medio → Mantener resultados parciales + log
- Usuario no sabe si puede cerrar → Botón claro
- Progreso estancado → Mostrar actividad actual

### 6.4. Flujo: Revisión de Alertas (80% del trabajo diario)

**Objetivo:** Revisar y resolver inconsistencias detectadas.

```
┌─────────────────────────────────────────────────────────────┐
│ ALERTAS (47)                              [Filtros ▼]       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ⚠️ 3 Críticas | ⚡ 12 Advertencias | ℹ️ 32 Info           │
│                                                             │
│ [Mostrar: ● Pendientes  ○ Todas  ○ Resueltas]            │
│ Ordenar: [Severidad ▼]                                     │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│                                                             │
│ 🔴 CRÍTICA - Color de ojos inconsistente                   │
│    María: "ojos verdes" vs "ojos azules"                   │
│    Cap. 2, pág. 14 | Cap. 5, pág. 67                      │
│    Confianza: 95%                                          │
│    [Ver contexto] [Resolver] [Falso positivo]             │
│                                                             │
│ 🔴 CRÍTICA - Inconsistencia temporal                       │
│    Juan: 30 años (Cap. 1) vs 28 años (Cap. 8)            │
│    [Ver contexto] [Resolver] [Ignorar]                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Acciones en alerta:**
1. **Clic en alerta** → Panel expandido con:
   - Contextos completos (extractos)
   - Ubicaciones clicables
   - Explicación detallada
   - Sugerencia de corrección

2. **"Ver contexto"** → Scroll al texto + highlight

3. **"Resolver"** → Marca como resuelta + nota opcional

4. **"Falso positivo"** → Dismisses + razón

**Decisiones críticas:**
- Layout split: lista + detalle + documento
- Estados claros: pendiente/resuelta/ignorada
- Confianza siempre visible
- Navegación con teclado (← →)
- Notas opcionales pero recomendadas

**Puntos de fricción:**
- Demasiadas alertas → Filtro por severidad
- No entiende por qué → Campo "Explicación"
- No puede resolver desde app → Botón "Marcar resuelta"
- Pierde contexto → Vista split persistente
- Falsos positivos → Botón muy visible

### 6.5. Flujo: Gestión de Entidades

**Objetivo:** Validar personajes detectados y fusionar duplicados.

```
┌─────────────────────────────────────────────────────────────┐
│ PERSONAJES (23) | LUGARES (8) | OTROS (6)    [+ Añadir]    │
├─────────────────────────────────────────────────────────────┤
│ Buscar: [___] 🔍  Ordenar: [Importancia ▼]                 │
│                                                             │
│ 👤 María González                   [⚠️ 2 variantes]      │
│    Protagonista | 127 menciones | Cap. 1-12                │
│    ● ojos verdes ● 30 años ● detective                     │
│    [Ver ficha completa]                                    │
│                                                             │
│ 👤 Ana / Anna                      🔀 Posible duplicado    │
│    ¿Es la misma persona?                                   │
│    Ana: 12 menciones (Cap. 1-4)                           │
│    Anna: 8 menciones (Cap. 6-9)                           │
│    [Fusionar] [Son diferentes] [Revisar]                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Subproceso: Fusionar entidades**

```
1. Clic en "🔀 Posible duplicado"

2. Modal de fusión:
   ┌────────────────────────────────────────────┐
   │ Fusionar entidades                        │
   │                                            │
   │ ANA (12 menciones)  +  ANNA (8 menciones)│
   │                                            │
   │ Ejemplos de uso:                          │
   │ "Ana llegó tarde"    "Anna sonrió"       │
   │                                            │
   │ Nombre canónico: [Ana María Rodríguez]   │
   │ Alias: Ana, Anna, Ana María              │
   │                                            │
   │ [❌ Cancelar]  [✅ Fusionar]             │
   └────────────────────────────────────────────┘

3. Sistema fusiona:
   ├─> Unifica menciones
   ├─> Combina atributos
   ├─> Genera alertas si hay conflictos
   └─> Guarda historial (permite deshacer)
```

**Ficha completa de personaje:**

```
┌─────────────────────────────────────────────────────────────┐
│ 👤 MARÍA GONZÁLEZ                         [⬅️ Volver]      │
├─────────────────────────────────────────────────────────────┤
│ Tipo: Personaje | Protagonista                             │
│ 127 menciones | Primera: Cap. 1 | Última: Cap. 12         │
│                                                             │
│ ━━━ ATRIBUTOS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ FÍSICOS                                                    │
│ • Ojos: verdes ⚠️ [Inconsistencia]                        │
│   Cap. 2: "ojos verdes"                                    │
│   Cap. 5: "ojos azules" ← conflicto                       │
│                                                             │
│ • Edad: 30 años ✅                                         │
│   Cap. 1: "treinta años"                                   │
│                                                             │
│ PSICOLÓGICOS                                               │
│ • Personalidad: decidida, impulsiva                        │
│                                                             │
│ SOCIALES                                                   │
│ • Profesión: detective ✅                                  │
│   Cap. 1: "detective privada"                              │
│                                                             │
│ [+ Añadir atributo]                                        │
│                                                             │
│ ━━━ MENCIONES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ Primera aparición (Cap. 1, pág. 3):                       │
│ "María González, detective privada..."                     │
│ [Ver en documento]                                         │
│                                                             │
│ [Ver todas las 127 menciones]                             │
│                                                             │
│ ━━━ RELACIONES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ • Juan Martínez (compañero, 23 interacciones)             │
│                                                             │
│ ━━━ ACCIONES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ [📄 Exportar ficha] [✏️ Editar] [🗑️ Eliminar]            │
└─────────────────────────────────────────────────────────────┘
```

**Decisiones críticas:**
- Indicador visual de validación (✅/⚠️)
- Importancia auto-calculada pero editable
- Fusión reversible (historial 30 días)
- Atributos vinculados a fuente
- Búsqueda rápida por nombre

**Puntos de fricción:**
- Muchas entidades sin validar → Filtro "Solo principales"
- Duda en fusionar → Mostrar ejemplos de uso
- Fusión incorrecta → Botón "Deshacer"
- Añadir atributo lento → Autocompletado + templates
- Pierde track → Filtro "Sin validar" + contador

### 6.6. Flujo: Exportación

**Objetivo:** Generar informes y fichas para compartir.

```
┌─────────────────────────────────────────────────────────────┐
│ EXPORTAR                                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌──────────────────────────────────────┐                   │
│ │ 📄 INFORME DE ANÁLISIS               │                   │
│ │ Resumen completo del manuscrito      │                   │
│ │ Incluye: estadísticas, alertas,      │                   │
│ │ entidades                             │                   │
│ │ Formato: ● Markdown  ○ JSON  ○ PDF  │                   │
│ │ [Exportar informe]                    │                   │
│ └──────────────────────────────────────┘                   │
│                                                             │
│ ┌──────────────────────────────────────┐                   │
│ │ 📚 FICHAS DE PERSONAJES              │                   │
│ │ ☐ Solo principales                   │                   │
│ │ ☑ Incluir atributos                  │                   │
│ │ ☑ Incluir menciones destacadas       │                   │
│ │ Formato: ● Markdown  ○ JSON         │                   │
│ │ [Exportar fichas]                     │                   │
│ └──────────────────────────────────────┘                   │
│                                                             │
│ ┌──────────────────────────────────────┐                   │
│ │ 📋 HOJA DE ESTILO                    │                   │
│ │ Decisiones editoriales y grafías     │                   │
│ │ Formato: ● Markdown  ○ Word         │                   │
│ │ [Exportar hoja de estilo]            │                   │
│ └──────────────────────────────────────┘                   │
│                                                             │
│ ┌──────────────────────────────────────┐                   │
│ │ ⚠️ SOLO ALERTAS                      │                   │
│ │ Mostrar: ☑ Pendientes ☐ Resueltas   │                   │
│ │ Formato: ● JSON  ○ CSV  ○ Excel     │                   │
│ │ [Exportar alertas]                    │                   │
│ └──────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

**Formatos soportados:**
- **Markdown:** Correctores técnicos, fácil versionar
- **JSON:** Integración con otras herramientas
- **PDF:** Clientes no técnicos (opcional)
- **Excel/CSV:** Alertas filtrables

**Decisiones críticas:**
- NO incluir texto completo (privacidad)
- Solo extractos relevantes
- Checkboxes para personalizar
- Formatos flexibles según uso

**Puntos de fricción:**
- No sabe qué formato → Tooltips explicativos
- Archivo muy grande → Warning + sugerencias
- Quiere personalizar → Templates (post-MVP)
- No encuentra archivo → Notificación con ubicación

---

## 7. Componentes y Patrones de UI {#componentes}

### 7.1. Componentes Clave

#### AlertList.vue

```vue
<template>
  <DataTable
    :value="filteredAlerts"
    :paginator="true"
    :rows="50"
    sortField="severity"
    :sortOrder="-1"
    :virtualScrollerOptions="{ itemSize: 80 }"
  >
    <Column field="severity" header="Sev." style="width: 80px">
      <template #body="slotProps">
        <Tag :severity="getSeverityColor(slotProps.data.severity)">
          {{ getSeverityIcon(slotProps.data.severity) }}
        </Tag>
      </template>
    </Column>

    <Column field="title" header="Alerta" sortable></Column>

    <Column field="chapter" header="Cap." style="width: 80px" sortable></Column>

    <Column field="entity_ids" header="Entidades">
      <template #body="slotProps">
        <Chip v-for="id in slotProps.data.entity_ids"
              :key="id"
              :label="getEntityName(id)"
              @click="goToEntity(id)" />
      </template>
    </Column>

    <Column field="confidence" header="Conf." style="width: 100px">
      <template #body="slotProps">
        <ProgressBar :value="slotProps.data.confidence * 100" />
      </template>
    </Column>

    <Column field="status" header="Estado" style="width: 150px">
      <template #body="slotProps">
        <Dropdown v-model="slotProps.data.status"
                  :options="statusOptions"
                  @change="updateStatus(slotProps.data)" />
      </template>
    </Column>

    <template #expansion="slotProps">
      <AlertDetail :alert="slotProps.data" />
    </template>
  </DataTable>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAlertsStore } from '@/stores/alerts';
import { useEntitiesStore } from '@/stores/entities';

const alertsStore = useAlertsStore();
const entitiesStore = useEntitiesStore();

const filteredAlerts = computed(() => {
  return alertsStore.alerts.filter(a =>
    alertsStore.filter.statuses?.includes(a.status) ?? true
  );
});

const getSeverityColor = (severity: string) => {
  const colors = {
    critical: 'danger',
    warning: 'warning',
    info: 'info',
    hint: 'secondary'
  };
  return colors[severity];
};

const getEntityName = (entityId: number) => {
  const entity = entitiesStore.entities.find(e => e.id === entityId);
  return entity?.canonical_name ?? 'Desconocido';
};

const updateStatus = async (alert: Alert) => {
  await alertsStore.updateStatus(alert.id, alert.status);
};
</script>
```

#### EntityDetail.vue

```vue
<template>
  <Card>
    <template #title>
      {{ entity.canonical_name }}
      <Tag :value="entity.entity_type" />
      <Tag :value="entity.importance" :severity="getImportanceSeverity()" />
    </template>

    <template #content>
      <TabView>
        <TabPanel header="Atributos">
          <DataTable :value="attributes">
            <Column field="attribute_type" header="Tipo" />
            <Column field="attribute_key" header="Atributo" />
            <Column field="value" header="Valor" />
            <Column field="source_chapter" header="Fuente">
              <template #body="slotProps">
                <Button
                  :label="`Cap. ${slotProps.data.source_chapter}`"
                  link
                  @click="goToSource(slotProps.data)"
                />
              </template>
            </Column>
            <Column field="confidence" header="Conf.">
              <template #body="slotProps">
                {{ (slotProps.data.confidence * 100).toFixed(0) }}%
              </template>
            </Column>
            <Column field="validated_by_user" header="✓">
              <template #body="slotProps">
                <Checkbox
                  v-model="slotProps.data.validated_by_user"
                  binary
                  @change="validateAttribute(slotProps.data)"
                />
              </template>
            </Column>
          </DataTable>
        </TabPanel>

        <TabPanel header="Menciones">
          <VirtualScroller :items="mentions" :itemSize="80">
            <template #item="{ item }">
              <div class="mention-item">
                <div class="surface-form">{{ item.surface_form }}</div>
                <div class="context">
                  {{ item.context_before }}
                  <mark>{{ item.surface_form }}</mark>
                  {{ item.context_after }}
                </div>
                <Button
                  icon="pi pi-map-marker"
                  text
                  @click="goToMention(item)"
                />
              </div>
            </template>
          </VirtualScroller>
        </TabPanel>
      </TabView>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useEntitiesStore } from '@/stores/entities';
import { useRouter } from 'vue-router';

const props = defineProps<{ entityId: number }>();
const entitiesStore = useEntitiesStore();
const router = useRouter();

const entity = computed(() =>
  entitiesStore.entities.find(e => e.id === props.entityId)
);
const attributes = ref([]);
const mentions = ref([]);

const goToSource = (attribute: Attribute) => {
  router.push({
    name: 'document',
    query: {
      chapter: attribute.source_chapter,
      highlight: attribute.id
    }
  });
};

const validateAttribute = async (attribute: Attribute) => {
  await api.post(`/attributes/${attribute.id}/validate`, {
    validated: attribute.validated_by_user
  });
};
</script>
```

#### AnalysisProgressOverlay.vue

```vue
<template>
  <Dialog
    v-model:visible="isAnalyzing"
    modal
    :closable="false"
    :style="{ width: '50vw' }"
  >
    <template #header>
      <h3>Analizando manuscrito...</h3>
    </template>

    <div class="progress-content">
      <ProgressBar
        :value="overallProgress"
        :showValue="true"
      />

      <div class="phase-info">
        <strong>{{ currentPhaseMessage }}</strong>
        <p v-if="progress?.current_action">
          {{ progress.current_action }}
        </p>
      </div>

      <div class="metrics">
        <div class="metric" v-if="progress?.chapters_found">
          <i class="pi pi-book"></i>
          <span>{{ progress.chapters_found }} capítulos</span>
        </div>
        <div class="metric" v-if="progress?.entities_found">
          <i class="pi pi-users"></i>
          <span>{{ progress.entities_found }} entidades</span>
        </div>
        <div class="metric" v-if="progress?.alerts_generated">
          <i class="pi pi-exclamation-triangle"></i>
          <span>{{ progress.alerts_generated }} alertas</span>
        </div>
      </div>

      <div class="timing" v-if="progress?.estimated_remaining">
        Tiempo restante: ~{{ formatSeconds(progress.estimated_remaining) }}
      </div>

      <Message
        severity="info"
        :closable="false"
      >
        Ya puedes revisar resultados parciales mientras el análisis continúa.
        <Button
          label="Ver resultados"
          link
          @click="showPartialResults"
        />
      </Message>
    </div>

    <template #footer>
      <Button
        label="Cancelar análisis"
        severity="secondary"
        @click="cancelAnalysis"
      />
      <Button
        label="Minimizar"
        @click="minimizeDialog"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useAnalysisStore } from '@/stores/analysis';

const analysisStore = useAnalysisStore();
const { progress, isRunning: isAnalyzing } = storeToRefs(analysisStore);

const overallProgress = computed(() =>
  (progress.value?.overall_progress ?? 0) * 100
);

const currentPhaseMessage = computed(() => {
  const messages = {
    parsing: 'Leyendo documento...',
    structure: 'Detectando capítulos y escenas...',
    ner: 'Identificando personajes y lugares...',
    coreference: 'Resolviendo referencias...',
    attributes: 'Extrayendo atributos de personajes...',
    consistency: 'Verificando inconsistencias...',
    complete: 'Análisis completado',
    error: 'Error en el análisis'
  };
  return messages[progress.value?.current_phase ?? 'parsing'];
});

const formatSeconds = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
};

const cancelAnalysis = async () => {
  if (confirm('¿Seguro que deseas cancelar? Los resultados parciales se conservarán.')) {
    await api.post('/analysis/cancel');
    isAnalyzing.value = false;
  }
};

const minimizeDialog = () => {
  // Dialog se minimiza pero análisis continúa
  isAnalyzing.value = false;
};

const showPartialResults = () => {
  minimizeDialog();
  // Navegar a vista de resultados
};
</script>
```

### 7.2. Sistema de Temas (Dark Mode)

```scss
// themes/light.scss
$primary-color: #2563eb;
$surface-ground: #ffffff;
$surface-card: #f9fafb;
$text-color: #1f2937;
$text-color-secondary: #6b7280;

// Highlights
$highlight-critical: #dc2626;
$highlight-warning: #f59e0b;
$highlight-info: #3b82f6;
$highlight-success: #10b981;

// themes/dark.scss
$primary-color: #60a5fa;
$surface-ground: #1e1e1e;
$surface-card: #2d2d2d;
$text-color: #e5e7eb;
$text-color-secondary: #9ca3af;

// Highlights (ajustados para dark mode)
$highlight-critical: #f87171;
$highlight-warning: #fbbf24;
$highlight-info: #60a5fa;
$highlight-success: #34d399;
```

**Toggle de tema:**

```typescript
// composables/useTheme.ts
import { ref, watch } from 'vue';

export function useTheme() {
  const isDark = ref(
    localStorage.getItem('theme') === 'dark' ||
    window.matchMedia('(prefers-color-scheme: dark)').matches
  );

  const toggleTheme = () => {
    isDark.value = !isDark.value;
  };

  watch(isDark, (dark) => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, { immediate: true });

  return { isDark, toggleTheme };
}
```

### 7.3. Atajos de Teclado

```typescript
// composables/useKeyboardShortcuts.ts
import { onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAlertsStore } from '@/stores/alerts';

export function useKeyboardShortcuts() {
  const router = useRouter();
  const alertsStore = useAlertsStore();

  const handleKeydown = (event: KeyboardEvent) => {
    const { key, ctrlKey, metaKey, shiftKey } = event;
    const modifier = ctrlKey || metaKey;

    // Navegación de alertas
    if (key === 'F8' && !shiftKey) {
      event.preventDefault();
      alertsStore.nextAlert();
    } else if (key === 'F8' && shiftKey) {
      event.preventDefault();
      alertsStore.previousAlert();
    }

    // Paneles
    else if (modifier && key === 'b') {
      event.preventDefault();
      toggleSidebar();
    } else if (modifier && key === 'e') {
      event.preventDefault();
      router.push({ name: 'entities' });
    } else if (modifier && key === 'a') {
      event.preventDefault();
      router.push({ name: 'alerts' });
    }

    // Búsqueda
    else if (modifier && key === 'f') {
      event.preventDefault();
      focusSearch();
    }

    // Acciones rápidas
    else if (key === 'Enter' && alertsStore.selectedAlert) {
      event.preventDefault();
      alertsStore.resolveSelectedAlert();
    } else if (key === 'Delete' && alertsStore.selectedAlert) {
      event.preventDefault();
      alertsStore.dismissSelectedAlert();
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown);
  });
}
```

---

## 8. Roadmap de Implementación {#roadmap}

### Fase 0: Setup Base (1-2 semanas)

**Tareas:**
1. Configurar Tauri 2.0 con Vue 3 + Vite + TypeScript
2. Setup de PrimeVue + tema base
3. Implementar FastAPI server básico con endpoints stub
4. Configurar PyInstaller para backend bundling
5. Implementar sidecar lifecycle en Tauri
6. Setup de Pinia stores y Vue Router

**Entregables:**
- Aplicación Tauri vacía que lanza backend Python
- "Hello World" comunicándose via REST API

### Fase 1: Core Features (3-4 semanas)

**Sprint 1.1: Dashboard y Proyectos (1 semana)**
- Vista de lista de proyectos (CRUD)
- Diálogo de creación con file picker
- Integración con `ProjectManager` del backend

**Sprint 1.2: Análisis con Progreso (1 semana)**
- Overlay de análisis con barra de progreso
- WebSocket para streaming de progreso
- Vista de resultados parciales

**Sprint 1.3: Dashboard de Proyecto (1 semana)**
- Vista overview con estadísticas
- Navegación entre paneles
- Status bar funcional

**Sprint 1.4: Estructura y Navegación (1 semana)**
- Sidebar con árbol de capítulos
- Visor de documento básico (read-only)
- Scroll sincronizado

**Entregables:**
- Usuario puede crear proyecto y ver análisis completo

### Fase 2: Visualización de Entidades (2-3 semanas)

**Sprint 2.1: Lista de Entidades (1 semana)**
- Tabs por tipo (Personajes, Lugares, Otros)
- DataTable con filtrado y sorting
- Búsqueda por nombre

**Sprint 2.2: Fusión de Entidades (1 semana)**
- Detección de duplicados sugeridos
- Diálogo de fusión con preview
- Integración con `EntityRepository.merge_entities()`

**Sprint 2.3: Ficha de Personaje (1 semana)**
- Vista detallada con tabs (Atributos, Menciones)
- Validación de atributos
- Navegación a menciones en documento

**Entregables:**
- Panel de entidades completamente funcional
- Usuario puede fusionar duplicados y validar atributos

### Fase 3: Alertas y Timeline (2-3 semanas)

**Sprint 3.1: Lista de Alertas (1 semana)**
- DataTable con alertas
- Filtrado por categoría, severidad, estado
- Resumen por severidad

**Sprint 3.2: Detalle y Navegación (1 semana)**
- Card expandible con contexto completo
- Navegación a texto desde alerta
- Highlights contextuales en documento

**Sprint 3.3: Gestión de Alertas (1 semana)**
- Resolver/Dismiss con notas
- Historial de cambios
- Sincronización con backend

**Entregables:**
- Flujo completo de revisión de alertas
- Usuario puede trabajar eficientemente con 100+ alertas

### Fase 4: Exportación y Visualización Avanzada (1-2 semanas)

**Sprint 4.1: Exportación Básica (1 semana)**
- Exportar informe completo (Markdown/JSON)
- Exportar alertas (CSV/JSON)
- Integración con `export.py` del backend

**Sprint 4.2: Grafos y Timeline (opcional, 1 semana)**
- Grafo de relaciones con Cytoscape.js
- Timeline básico de eventos
- Visualización de interacciones

**Entregables:**
- Sistema completo de exportación
- Visualizaciones avanzadas (opcional)

### Fase 5: Polish y Distribución (1-2 semanas)

**Sprint 5.1: Performance y UX (1 semana)**
- Optimización de renders
- Virtualización de listas grandes
- Animaciones y transiciones
- Dark mode completo

**Sprint 5.2: Testing y Packaging (1 semana)**
- Testing E2E con Playwright
- Build para Windows y macOS
- Instaladores (.msi, .dmg)
- Documentación de usuario

**Entregables:**
- Aplicación lista para distribución
- Instaladores para ambas plataformas

### Estimación Total: 9-14 semanas (2-3.5 meses)

**Recursos requeridos:**
- 1 desarrollador full-time frontend (Vue 3)
- 0.5 desarrollador backend (endpoints FastAPI)
- 0.25 diseñador UX (opcional, para refinamiento)

---

## 9. Referencias y Fuentes {#referencias}

### Documentación del Proyecto

- [docs/PROJECT_STATUS.md](../PROJECT_STATUS.md) - Estado actual del backend
- [docs/API_REFERENCE.md](../API_REFERENCE.md) - APIs disponibles
- [docs/TESTING_STRATEGY.md](../TESTING_STRATEGY.md) - Estrategia de testing
- [docs/02-architecture/](../02-architecture/) - Arquitectura del sistema
- [CLAUDE.md](../../CLAUDE.md) - Instrucciones y convenciones

### Herramientas de Escritura Analizadas

- [Scrivener Review 2025](https://writergadgets.com/scrivener-review/)
- [ProWritingAid Desktop App](https://prowritingaid.com/art/1559/how-to-use-the-prowritingaid-desktop-app-for-windows.aspx)
- [Grammarly Editor User Guide](https://support.grammarly.com/hc/en-us/articles/360003474732-Grammarly-Editor-user-guide)

### Stack Tecnológico

**Tauri:**
- [Tauri vs Electron Comparison](https://www.gethopp.app/blog/tauri-vs-electron)
- [Tauri + Vue + Python Guide](https://hamza-senhajirhazi.medium.com/how-to-write-and-package-desktop-apps-with-tauri-vue-python-ecc08e1e9f2a)
- [Tauri IPC Documentation](https://v2.tauri.app/concept/inter-process-communication/)

**Vue 3:**
- [React vs Vue vs Svelte 2026](https://medium.com/@artur.friedrich/react-vs-vue-vs-svelte-in-2026-a-practical-comparison-for-your-next-side-hustle-e57b7f5f37eb)
- [Top Vue Component Libraries 2025](https://uibakery.io/blog/top-vue-component-libraries)

**Visualización:**
- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [Recogito Text Annotator](https://www.npmjs.com/package/text-annotator)

### Patrones de UI y UX

- [Suppress Code Analysis - Visual Studio](https://learn.microsoft.com/en-us/visualstudio/code-quality/in-source-suppression-overview)
- [Navigation Testing Best Practices](https://www.lyssna.com/guides/navigation-testing/)
- [Dark Mode Accessibility](https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/)
- [Keyboard Shortcuts UX](https://medium.com/design-bootcamp/the-art-of-keyboard-shortcuts-designing-for-speed-and-efficiency-9afd717fc7ed)

---

## Apéndice: Wireframes Sugeridos

Para implementación, se recomienda crear wireframes de alta fidelidad para:

1. **Dashboard:** Vista inicial con lista de proyectos
2. **Vista de Proyecto:** Layout de tres paneles completo
3. **Panel de Alertas:** Lista + detalle + navegación
4. **Ficha de Personaje:** Tabs con atributos y menciones
5. **Diálogo de Fusión:** Proceso completo de fusión de entidades
6. **Overlay de Análisis:** Progreso con disponibilidad progresiva

Herramientas recomendadas: Figma, Adobe XD, o Sketch.

---

**Documento preparado para revisión por el equipo de desarrollo.**
**Próximo paso:** Aprobación de stack tecnológico y priorización de fases.
