# Diseño de Interfaz de Usuario - Narrative Assistant

> **Estado:** Stack tecnológico aprobado (2026-01-10)
> **Versión:** 1.0

---

## 📋 Resumen Ejecutivo

Este directorio contiene la documentación completa del diseño de interfaz de usuario para Narrative Assistant, una herramienta offline de análisis narrativo para correctores literarios profesionales.

### Stack Tecnológico Aprobado ✅

```
Frontend:  Tauri 2.0 + Vue 3 + TypeScript + PrimeVue
Backend:   FastAPI (localhost:8008) + PyInstaller Sidecar
Build:     Vite 5.x
```

**Características clave:**
- 🪶 Ligero: Bundle de 3-10 MB (vs 85-120 MB de Electron)
- 🔒 Seguro: 100% offline, arquitectura Rust + IPC explícito
- ⚡ Rápido: Startup <0.5s, memoria 30-40 MB en idle
- 🎨 Profesional: PrimeVue con 160+ componentes enterprise

---

## 📁 Documentos en Este Directorio

### 1. [UI_DESIGN_PROPOSAL.md](./UI_DESIGN_PROPOSAL.md) - 95KB
**Propuesta completa de diseño de interfaz**

**Contenido:**
- Stack tecnológico detallado (Tauri vs Electron, Vue vs React)
- Análisis del estado del arte (Scrivener, ProWritingAid, Grammarly)
- Arquitectura de tres paneles (Sidebar + Editor + Inspector)
- Flujos de usuario completos (6 flujos principales)
- Componentes Vue con código de ejemplo
- Roadmap de implementación (9-14 semanas)

**Para quién:**
- Desarrolladores frontend
- Arquitectos de software
- Product managers

---

### 2. [UI_UX_CORRECTIONS.md](./UI_UX_CORRECTIONS.md) - 35KB
**Correcciones críticas de UX (basadas en feedback del usuario)**

**Cambios obligatorios:**

#### ✅ Navegación Interactiva
- **Requisito:** Clic en entidad en texto → abre ficha en Inspector Panel
- **Implementación:** Entidades clicables con entity_id vinculado
- **Estado backend:** ✅ 100% implementado

#### ✅ Contextos Múltiples en Alertas
- **Requisito:** Cada contexto con enlace directo (Cap. X, pág. Y, línea Z)
- **Implementación:** Enlaces independientes por cada fuente
- **Estado backend:** ⚠️ 60% implementado (falta page/line)

#### ✅ Trazabilidad de Atributos
- **Requisito:** Cada atributo muestra todas sus evidencias con ubicaciones
- **Implementación:** Tabla `attribute_evidences` con método de extracción
- **Estado backend:** ❌ 20% implementado (CRÍTICO)

#### ✅ Historial Permanente
- **Requisito:** Sin caducidad automática, undo completo
- **Implementación:** Deprecar `clear_old_entries()`, implementar `undo()`
- **Estado backend:** ⚠️ 70% implementado

**Para quién:**
- Desarrolladores backend (gaps a completar)
- Desarrolladores frontend (requisitos de UI)
- Diseñadores UX

---

### 3. [BACKEND_GAPS_ANALYSIS.md](./BACKEND_GAPS_ANALYSIS.md) - 45KB
**Análisis técnico de gaps del backend**

**Contenido:**
- Verificación requisito por requisito del backend actual
- Código SQL y Python de lo que falta implementar
- Estimaciones de tiempo detalladas
- Archivos específicos a modificar
- Priorización de tareas

**Resumen de gaps:**

| Requisito | Estado | Tiempo para completar |
|-----------|--------|---------------------|
| Navegación interactiva | ✅ 100% | Ya funciona |
| Contextos múltiples | ⚠️ 60% | 4-6 horas |
| Trazabilidad de atributos | ❌ 20% | **16-22 horas** |
| Historial permanente | ⚠️ 70% | 8-10 horas |

**Total estimado:** 35-45 horas de desarrollo backend

**Para quién:**
- Desarrolladores backend (tareas prioritarias)
- Tech leads (estimaciones y planificación)

---

## 🎯 Ruta Crítica de Implementación

### Fase 0: Completar Backend (35-45h) - ANTES DE UI

#### 🔴 CRÍTICO (16-22h)
1. **Tabla `attribute_evidences`**
   - Nueva tabla en `database.py`
   - Relación 1:N con `entity_attributes`

2. **Consolidación de atributos**
   - Nuevo archivo: `nlp/attribute_consolidation.py`
   - Agrupar evidencias del mismo atributo

3. **API de evidencias**
   - `EntityRepository.get_attribute_evidences(attribute_id)`
   - Incluir método de extracción y keywords

4. **Integración en pipeline**
   - Modificar `pipelines/analysis_pipeline.py`
   - Guardar evidencias al extraer atributos

#### 🟡 IMPORTANTE (12-16h)
5. **Función `calculate_page_and_line()`**
   - Nuevo en `parsers/base.py`
   - Mapear `start_char` → (page, line)

6. **Estructura `sources[]` en alertas**
   - Modificar `AlertEngine.create_from_attribute_inconsistency()`
   - Array consistente en `extra_data`

7. **Deprecar `clear_old_entries()`**
   - Añadir warning/error en `history.py`

8. **Implementar `undo()` completo**
   - `HistoryManager.undo(entry_id)`
   - Verificación de dependencias

**Referencias:**
- [BACKEND_GAPS_ANALYSIS.md](./BACKEND_GAPS_ANALYSIS.md) - Código detallado
- [UI_UX_CORRECTIONS.md](./UI_UX_CORRECTIONS.md) - Requisitos

---

### Fase 1-5: Implementación UI (9-14 semanas) - DESPUÉS DE BACKEND

#### Fase 0: Setup Base (1-2 semanas)
- Configurar Tauri 2.0 con Vue 3 + Vite
- Setup PrimeVue y estructura de componentes
- Implementar FastAPI server básico
- Configurar PyInstaller para bundling
- Implementar sidecar lifecycle

#### Fase 1: Core Features (3-4 semanas)
- Dashboard con lista de proyectos
- Importación de documentos (drag & drop)
- Análisis con progreso en tiempo real (WebSocket)
- Vista overview con estadísticas

#### Fase 2: Visualización de Entidades (2-3 semanas)
- Lista de entidades con filtrado/sorting
- Fusión de entidades duplicadas
- Ficha completa de personaje con atributos
- Navegación a menciones en documento

#### Fase 3: Alertas (2-3 semanas)
- Lista de alertas con filtros avanzados
- Detalle de alerta con navegación al texto
- Resolución/dismissal de alertas
- Vista comparada de contextos múltiples

#### Fase 4: Exportación (1-2 semanas)
- Informe completo (Markdown/JSON)
- Fichas de personajes
- Hoja de estilo
- Solo alertas (CSV/Excel)

#### Fase 5: Polish (1-2 semanas)
- Performance y optimización
- Dark mode completo
- Testing E2E
- Packaging para Windows/macOS

**Referencia:**
- [UI_DESIGN_PROPOSAL.md](./UI_DESIGN_PROPOSAL.md) - Roadmap detallado

---

## 🏗️ Arquitectura de la UI

### Layout Principal: Three-Pane

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
│ [Tabs]       │  Texto del manuscrito            │ [Alertas]    │
│ • Capítulos  │  con entidades clicables         │ • Filtros    │
│ • Personajes │  y highlights                    │ • Lista      │
│ • Lugares    │                                  │ • Detalle    │
│              │                                  │               │
├──────────────┴──────────────────────────────────┴───────────────┤
│ STATUS BAR: [████░░░░] 65% Analizando... | 45 pers. | 12 alert.│
└─────────────────────────────────────────────────────────────────┘
```

### Flujos de Usuario Principales

1. **Onboarding** → Verificación + tutorial opcional
2. **Crear proyecto** → Importar DOCX + configuración
3. **Análisis** → Progreso en tiempo real + resultados parciales
4. **Revisar alertas** → Navegación bidireccional documento ↔ alertas
5. **Gestión de entidades** → Fusión + validación + evidencias
6. **Exportación** → Informes + fichas + hoja de estilo

---

## 📊 Métricas y Estimaciones

### Backend (Estado Actual)
- **Completado:** 90% del MVP
- **Gaps para UI:** 62% completo
- **Tiempo para completar gaps:** 35-45 horas

### Frontend (Estimado)
- **Setup inicial:** 1-2 semanas
- **MVP UI:** 6-10 semanas
- **Total con polish:** 9-14 semanas

### Distribución Final
- **Bundle app:** 3-10 MB
- **Backend bundled:** 50-80 MB
- **Modelos NLP:** 1 GB
- **Total distribución:** ~1.1 GB

---

## 🔧 Herramientas y Recursos

### Desarrollo
- **Tauri CLI:** `npm install -g @tauri-apps/cli`
- **Vue DevTools:** Extensión para Chrome/Firefox
- **PyInstaller:** `pip install pyinstaller`

### Testing
- **Frontend:** Vitest + @vue/test-utils
- **E2E:** Playwright
- **Backend:** pytest (ya configurado)

### Referencias Externas
- [Tauri Documentation](https://v2.tauri.app/)
- [Vue 3 Docs](https://vuejs.org/)
- [PrimeVue Components](https://primevue.org/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

---

## 📞 Contacto y Próximos Pasos

### Estado Actual (2026-01-10)
✅ Stack tecnológico aprobado
✅ Documentación completa de UI generada
⏳ Pendiente: Completar gaps del backend (35-45h)
⏳ Pendiente: Iniciar implementación UI

### Próxima Acción Recomendada
1. **Implementar trazabilidad de atributos** (16-22h) - CRÍTICO
2. **Implementar calculate_page_and_line()** (4-6h)
3. **Setup inicial de Tauri + Vue** (1-2 semanas)

### Documentos Clave
- **Este README:** Vista general y roadmap
- **UI_DESIGN_PROPOSAL.md:** Diseño completo de UI
- **UI_UX_CORRECTIONS.md:** Requisitos obligatorios de UX
- **BACKEND_GAPS_ANALYSIS.md:** Tareas pendientes del backend

---

**Proyecto TFM de Pau Ubach**
**Herramienta NLP para editores literarios**
