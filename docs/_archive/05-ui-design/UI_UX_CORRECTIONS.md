# Correcciones y Mejoras de UX - Narrative Assistant

> **Fecha:** 2026-01-10
> **Basado en:** Feedback del usuario sobre UI_DESIGN_PROPOSAL.md
> **Estado:** Requisitos obligatorios

---

## Índice

1. [Navegación Interactiva en Documento](#navegación-interactiva)
2. [Visualización de Contextos Múltiples](#contextos-múltiples)
3. [Trazabilidad de Atributos](#trazabilidad-atributos)
4. [Historial Sin Caducidad](#historial-permanente)
5. [Cambios en Componentes](#cambios-componentes)

---

## 1. Navegación Interactiva en Documento {#navegación-interactiva}

### Problema Original

El diseño inicial no especificaba qué sucede al hacer clic en una entidad (personaje, lugar, etc.) dentro del texto del manuscrito.

### Solución: Entidades Clicables

**Comportamiento al hacer clic en una entidad en el texto:**

```
Usuario está leyendo el manuscrito:
"María González llegó tarde a la comisaría..."
       ^^^^^^^^^^^^^^
       (enlace clicable)

1. Usuario hace clic en "María González"

2. Sistema ejecuta:
   ├─> Identifica la entidad (entity_id: 42)
   ├─> Abre el Inspector Panel (si estaba cerrado)
   └─> Carga la ficha completa de la entidad

3. Inspector Panel muestra:
   ┌────────────────────────────────────────────┐
   │ 👤 MARÍA GONZÁLEZ         [⬅️ Volver]     │
   ├────────────────────────────────────────────┤
   │ Protagonista | 127 menciones              │
   │                                            │
   │ ATRIBUTOS                                  │
   │ • Ojos: verdes ⚠️                         │
   │ • Edad: 30 años                            │
   │ • Profesión: detective                     │
   │                                            │
   │ MENCIONES (127)                            │
   │ • Cap. 1, pág. 3 (primera aparición)      │
   │ • Cap. 2, pág. 14 ← TÚ ESTÁS AQUÍ        │
   │ • Cap. 3, pág. 28                         │
   │ ...                                        │
   └────────────────────────────────────────────┘

4. Sidebar izquierdo (opcional):
   - Resalta la entidad en la lista de personajes
   - Scroll automático hasta "María González"
```

### Implementación Técnica

**HTML con anotaciones:**

```vue
<template>
  <div class="manuscript-viewer">
    <p>
      <span
        v-for="token in tokens"
        :key="token.id"
        :class="getTokenClass(token)"
        @click="handleTokenClick(token)"
      >
        {{ token.text }}
      </span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { useEntitiesStore } from '@/stores/entities';
import { useRouter } from 'vue-router';

const entitiesStore = useEntitiesStore();
const router = useRouter();

interface Token {
  id: number;
  text: string;
  entity_id?: number;
  mention_id?: number;
  entity_type?: string;
}

const getTokenClass = (token: Token) => {
  if (!token.entity_id) return '';

  return [
    'entity-mention',
    `entity-type-${token.entity_type}`,
    'clickable'
  ];
};

const handleTokenClick = async (token: Token) => {
  if (!token.entity_id) return;

  // Cargar detalles de la entidad
  await entitiesStore.loadEntityDetail(token.entity_id);

  // Abrir Inspector Panel con la entidad
  inspectorStore.openEntity(token.entity_id, {
    fromMention: token.mention_id,
    highlightInList: true
  });

  // Opcional: También resaltar en Sidebar
  sidebarStore.highlightEntity(token.entity_id);
};
</script>

<style scoped>
.entity-mention {
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.entity-mention:hover {
  background-color: rgba(59, 130, 246, 0.1);
}

.entity-type-CHARACTER {
  border-bottom-color: #3b82f6;
}

.entity-type-LOCATION {
  border-bottom-color: #10b981;
}

.entity-type-OBJECT {
  border-bottom-color: #f59e0b;
}

.clickable {
  text-decoration: none;
}

.clickable:hover {
  text-decoration: underline;
}
</style>
```

### Feedback Visual

**Estados del enlace de entidad:**

- **Normal:** Subrayado con color según tipo de entidad
- **Hover:** Background suave + underline
- **Activo (seleccionado):** Background más marcado
- **En otra mención de la misma entidad:** Background persistente mientras Inspector está abierto

### Variantes de Comportamiento

**Opción A: Inspector Panel (Recomendada)**
- Clic en entidad → Inspector Panel muestra ficha completa
- No cierra el documento, layout split
- Usuario puede seguir leyendo mientras ve información

**Opción B: Modal**
- Clic en entidad → Modal sobre el documento
- Ventaja: Mayor foco
- Desventaja: Bloquea lectura del manuscrito

**Opción C: Sidebar**
- Clic en entidad → Sidebar cambia a tab "Entidades" y selecciona
- Desventaja: Puede estar lejos visualmente del texto

**Decisión:** **Opción A (Inspector Panel)** - Mejor para flujo de lectura continuo.

---

## 2. Visualización de Contextos Múltiples {#contextos-múltiples}

### Problema Original

El diseño mostraba un botón genérico "Ver contexto" pero en alertas con múltiples fuentes (ej: inconsistencia con 2 ubicaciones), solo se puede navegar a una ubicación a la vez.

### Solución: Enlaces Directos por Ubicación

**Diseño INCORRECTO (original):**

```
🔴 CRÍTICA - Color de ojos inconsistente
   María: "ojos verdes" vs "ojos azules"
   Cap. 2, pág. 14 | Cap. 5, pág. 67
   [Ver contexto] [Resolver] [Falso positivo]
   ^^^^^^^^^^^^^^
   ¿A cuál contexto va? Ambiguo.
```

**Diseño CORRECTO (nuevo):**

```
🔴 CRÍTICA - Color de ojos inconsistente
   Entidad: María González

   CONTEXTO 1:
   "María levantó la vista, sus ojos verdes reflejaban..."
   → [Cap. 2, pág. 14, línea 5]  ← ENLACE CLICABLE

   CONTEXTO 2:
   "Los ojos azules de María lo miraron con intensidad."
   → [Cap. 5, pág. 67, línea 12]  ← ENLACE CLICABLE

   ─────────────────────────────────────
   [Marcar como resuelta] [Falso positivo]
```

### Comportamiento al Hacer Clic en Ubicación

```
Usuario hace clic en "[Cap. 2, pág. 14, línea 5]":

1. Sistema navega al documento:
   ├─> Scroll suave hasta el capítulo 2
   ├─> Calcula posición de página 14
   ├─> Centra línea 5 en viewport
   └─> Aplica highlight temporal (amarillo brillante)

2. Highlight temporal:
   ├─> Duración: 3 segundos
   ├─> Efecto: Fade-in → Persistente → Fade-out
   └─> Color: rgba(250, 204, 21, 0.4) (amarillo)

3. Panel de alerta permanece visible:
   ├─> Layout split: documento (70%) + alerta (30%)
   ├─> Usuario puede leer contexto amplio
   └─> Puede hacer clic en "Cap. 5, pág. 67" sin cerrar
```

### Modo Vista Comparada (Opcional, Post-MVP)

Para inconsistencias con 2 ubicaciones, permitir vista split del documento:

```
┌───────────────────────────────────────────────────────────┐
│ ALERTA: Color de ojos inconsistente                      │
├───────────────────────────────────────────────────────────┤
│                                                           │
│ ┌─────────────────────┬─────────────────────┐           │
│ │ Cap. 2, pág. 14     │ Cap. 5, pág. 67     │           │
│ ├─────────────────────┼─────────────────────┤           │
│ │ María levantó la    │ Los ojos azules de  │           │
│ │ vista, sus ojos     │ María lo miraron    │           │
│ │ verdes reflejaban   │ con intensidad.     │           │
│ │ la luz de la        │                     │           │
│ │ ventana.            │                     │           │
│ │        ^^^^^^       │      ^^^^^^         │           │
│ └─────────────────────┴─────────────────────┘           │
│                                                           │
│ [Marcar como resuelta] [Volver a vista normal]          │
└───────────────────────────────────────────────────────────┘
```

**Implementación:**
- Botón "Comparar contextos" en alertas con 2+ ubicaciones
- Vista split temporal del documento
- Ambos contextos sincronizados y resaltados

### Actualización del Componente AlertDetail.vue

```vue
<template>
  <Card class="alert-detail">
    <template #title>
      <Tag :severity="getSeverityColor(alert.severity)">
        {{ getSeverityIcon(alert.severity) }}
      </Tag>
      {{ alert.title }}
    </template>

    <template #content>
      <div class="alert-description">
        {{ alert.description }}
      </div>

      <Divider />

      <!-- CONTEXTOS con enlaces individuales -->
      <div class="contexts">
        <div
          v-for="(source, index) in alert.sources"
          :key="index"
          class="context-item"
        >
          <h4>CONTEXTO {{ index + 1 }}</h4>

          <div class="excerpt">
            "{{ source.excerpt }}"
          </div>

          <!-- ENLACE CLICABLE A UBICACIÓN ESPECÍFICA -->
          <Button
            :label="formatLocation(source)"
            icon="pi pi-map-marker"
            link
            @click="navigateToSource(source)"
            class="source-link"
          />
        </div>
      </div>

      <!-- Botón de vista comparada (si 2 contextos) -->
      <Button
        v-if="alert.sources.length === 2"
        label="Comparar contextos lado a lado"
        icon="pi pi-clone"
        outlined
        @click="openCompareView"
      />

      <Divider />

      <div class="alert-actions">
        <Button
          label="Marcar como resuelta"
          icon="pi pi-check"
          @click="resolveAlert"
        />
        <Button
          label="Falso positivo"
          icon="pi pi-times"
          severity="secondary"
          @click="dismissAlert"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useDocumentStore } from '@/stores/document';

const props = defineProps<{ alert: Alert }>();
const router = useRouter();
const documentStore = useDocumentStore();

interface Source {
  chapter: number;
  page: number;
  line: number;
  start_char: number;
  end_char: number;
  excerpt: string;
}

const formatLocation = (source: Source) => {
  return `Cap. ${source.chapter}, pág. ${source.page}, línea ${source.line}`;
};

const navigateToSource = async (source: Source) => {
  // Navegar al documento
  await documentStore.scrollToPosition(source.start_char);

  // Aplicar highlight temporal
  documentStore.highlightRange(
    source.start_char,
    source.end_char,
    { duration: 3000, color: 'warning' }
  );
};

const openCompareView = () => {
  // Abrir vista comparada
  documentStore.openCompareView(props.alert.sources);
};
</script>

<style scoped>
.context-item {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--surface-card);
  border-radius: 6px;
}

.context-item h4 {
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.excerpt {
  font-style: italic;
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background: var(--surface-ground);
  border-left: 3px solid var(--primary-color);
}

.source-link {
  font-weight: 500;
}
</style>
```

---

## 3. Trazabilidad de Atributos {#trazabilidad-atributos}

### Problema Original

El diseño mostraba atributos como "Personalidad: decidida" pero no explicaba POR QUÉ el sistema llegó a esa conclusión. Faltaba trazabilidad completa.

### Solución: Cada Atributo es Clicable con Evidencias

**Diseño CORRECTO:**

```
┌─────────────────────────────────────────────────────────────┐
│ 👤 MARÍA GONZÁLEZ                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ATRIBUTOS FÍSICOS                                          │
│                                                             │
│ • Color de ojos: [verdes] ⚠️  📋 2 menciones              │
│                  ^^^^^^^                                    │
│                  (enlace clicable)                         │
│                                                             │
│ • Edad: [30 años]  📋 1 mención                            │
│         ^^^^^^^^                                            │
│         (enlace clicable)                                  │
│                                                             │
│ ATRIBUTOS PSICOLÓGICOS                                     │
│                                                             │
│ • Personalidad: [decidida, impulsiva]  📋 5 evidencias     │
│                 ^^^^^^^^^^^^^^^^^^^^^                       │
│                 (enlace clicable)                          │
└─────────────────────────────────────────────────────────────┘
```

### Comportamiento al Hacer Clic en Atributo

```
Usuario hace clic en "decidida":

1. Sistema abre panel de evidencias:

┌─────────────────────────────────────────────────────────────┐
│ 📋 EVIDENCIAS: María González - Personalidad: decidida      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Se encontraron 5 evidencias en el texto:                   │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ EVIDENCIA 1 (Confianza: 85%)                               │
│ Cap. 1, pág. 8, línea 15  [Ir al texto →]                 │
│                                                             │
│ "María tomó una decisión rápida sin consultar a nadie.    │
│  Como siempre, actuaba con determinación."                 │
│                                                             │
│ Método: Análisis de acciones                               │
│ Keywords: "decisión rápida", "determinación"               │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ EVIDENCIA 2 (Confianza: 78%)                               │
│ Cap. 3, pág. 42, línea 3  [Ir al texto →]                 │
│                                                             │
│ "—No voy a esperar más —dijo María con firmeza."          │
│                                                             │
│ Método: Análisis de diálogo                                │
│ Keywords: "firmeza", tono imperativo                       │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ EVIDENCIA 3 (Confianza: 92%)                               │
│ Cap. 5, pág. 67, línea 8  [Ir al texto →]                 │
│                                                             │
│ "María era una mujer decidida que no se dejaba             │
│  intimidar por nadie."                                      │
│                                                             │
│ Método: Descripción directa                                │
│ Keywords: "decidida" (explícito)                           │
│                                                             │
│ [... 2 evidencias más ...]                                 │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ ACCIONES:                                                   │
│ [✓ Validar todas] [✗ Rechazar atributo] [Cerrar]         │
└─────────────────────────────────────────────────────────────┘
```

### Tipos de Evidencias

El backend ya extrae atributos con fuentes (`source_excerpt`, `source_chapter`). La UI debe mostrar:

1. **Descripciones directas** (confianza alta):
   - "María era decidida" → Explícito en texto

2. **Acciones narrativas** (confianza media):
   - "tomó una decisión rápida" → Inferido de acción

3. **Diálogos** (confianza media):
   - Tono y contenido de lo que dice el personaje

4. **Reacciones de otros personajes** (confianza baja):
   - "Juan admiraba la determinación de María"

### Usuario NO Puede Añadir Atributos Manualmente

**Cambio importante respecto al diseño original:**

❌ **ELIMINAR:** Botón "+ Añadir atributo manualmente"

✅ **MANTENER:** Solo validación/rechazo de atributos detectados

**Razón:** Los atributos se infieren del texto mediante NLP. Permitir añadir manualmente rompería la trazabilidad y confiabilidad del sistema.

**Alternativa si el usuario detecta algo que el sistema no vio:**

```
Opción 1: Feedback al sistema (post-MVP)
- Usuario marca región de texto
- "Reportar atributo no detectado"
- Sistema re-analiza esa región específica

Opción 2: Notas del usuario
- Campo de "Notas del corrector" en ficha de personaje
- No se mezcla con atributos automáticos
- Se exporta por separado en informe
```

### Actualización del Componente AttributesList.vue

```vue
<template>
  <div class="attributes-section">
    <h3>ATRIBUTOS FÍSICOS</h3>

    <div
      v-for="attr in physicalAttributes"
      :key="attr.id"
      class="attribute-item"
    >
      <span class="attribute-label">{{ attr.attribute_key }}:</span>

      <!-- Valor clicable -->
      <Button
        :label="attr.value"
        link
        class="attribute-value"
        @click="showEvidences(attr)"
      />

      <!-- Indicador de evidencias -->
      <Tag
        :value="`📋 ${attr.evidence_count} evidencia${attr.evidence_count > 1 ? 's' : ''}`"
        severity="info"
      />

      <!-- Estado de validación -->
      <Tag
        v-if="attr.validated_by_user"
        value="✓ Validado"
        severity="success"
      />
      <Tag
        v-else-if="attr.confidence < 0.7"
        value="⚠️ Revisar"
        severity="warning"
      />
    </div>

    <Divider />

    <h3>ATRIBUTOS PSICOLÓGICOS</h3>

    <div
      v-for="attr in psychologicalAttributes"
      :key="attr.id"
      class="attribute-item"
    >
      <span class="attribute-label">{{ attr.attribute_key }}:</span>

      <!-- Valor clicable -->
      <Button
        :label="attr.value"
        link
        class="attribute-value"
        @click="showEvidences(attr)"
      />

      <Tag :value="`📋 ${attr.evidence_count} evidencias`" />
    </div>
  </div>

  <!-- Dialog de evidencias -->
  <Dialog
    v-model:visible="evidencesDialogVisible"
    modal
    :header="`Evidencias: ${selectedAttribute?.attribute_key} - ${selectedAttribute?.value}`"
    :style="{ width: '60vw' }"
  >
    <div class="evidences-list">
      <p>Se encontraron {{ evidences.length }} evidencias en el texto:</p>

      <div
        v-for="(evidence, index) in evidences"
        :key="evidence.id"
        class="evidence-item"
      >
        <Divider />

        <h4>EVIDENCIA {{ index + 1 }} (Confianza: {{ (evidence.confidence * 100).toFixed(0) }}%)</h4>

        <Button
          :label="`Cap. ${evidence.chapter}, pág. ${evidence.page}, línea ${evidence.line}`"
          icon="pi pi-map-marker"
          link
          @click="navigateToEvidence(evidence)"
        />

        <div class="excerpt">
          "{{ evidence.excerpt }}"
        </div>

        <div class="metadata">
          <span><strong>Método:</strong> {{ evidence.extraction_method }}</span>
          <span v-if="evidence.keywords">
            <strong>Keywords:</strong> {{ evidence.keywords.join(', ') }}
          </span>
        </div>
      </div>
    </div>

    <template #footer>
      <Button
        label="✓ Validar todas las evidencias"
        @click="validateAttribute"
      />
      <Button
        label="✗ Rechazar atributo"
        severity="secondary"
        @click="rejectAttribute"
      />
      <Button
        label="Cerrar"
        outlined
        @click="evidencesDialogVisible = false"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAttributesStore } from '@/stores/attributes';
import { useDocumentStore } from '@/stores/document';

const props = defineProps<{ entityId: number }>();

const attributesStore = useAttributesStore();
const documentStore = useDocumentStore();

const evidencesDialogVisible = ref(false);
const selectedAttribute = ref(null);
const evidences = ref([]);

const physicalAttributes = computed(() =>
  attributesStore.attributes.filter(a =>
    a.entity_id === props.entityId &&
    a.attribute_type === 'physical'
  )
);

const psychologicalAttributes = computed(() =>
  attributesStore.attributes.filter(a =>
    a.entity_id === props.entityId &&
    a.attribute_type === 'psychological'
  )
);

const showEvidences = async (attribute: Attribute) => {
  selectedAttribute.value = attribute;

  // Cargar evidencias desde el backend
  evidences.value = await attributesStore.getAttributeEvidences(attribute.id);

  evidencesDialogVisible.value = true;
};

const navigateToEvidence = (evidence: Evidence) => {
  documentStore.scrollToPosition(evidence.start_char);
  documentStore.highlightRange(evidence.start_char, evidence.end_char, {
    duration: 3000,
    color: 'info'
  });
};

const validateAttribute = async () => {
  await attributesStore.validateAttribute(selectedAttribute.value.id);
  evidencesDialogVisible.value = false;
};

const rejectAttribute = async () => {
  if (confirm('¿Seguro que deseas rechazar este atributo? Se marcará como falso positivo.')) {
    await attributesStore.rejectAttribute(selectedAttribute.value.id);
    evidencesDialogVisible.value = false;
  }
};
</script>

<style scoped>
.attribute-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
}

.attribute-label {
  font-weight: 500;
  min-width: 120px;
}

.attribute-value {
  font-weight: 600;
}

.evidence-item {
  margin: 1rem 0;
}

.excerpt {
  font-style: italic;
  margin: 0.5rem 0;
  padding: 0.75rem;
  background: var(--surface-ground);
  border-left: 3px solid var(--primary-color);
  border-radius: 4px;
}

.metadata {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}
</style>
```

### Cambios en el Backend (Requeridos)

Para soportar esta funcionalidad, el backend debe:

1. **Guardar evidencias de atributos:**
   - Cada `Attribute` debe tener múltiples `AttributeEvidence`
   - Tabla nueva: `attribute_evidences` con campos:
     - `attribute_id` (FK)
     - `start_char`, `end_char`
     - `chapter`, `page`, `line`
     - `excerpt`
     - `extraction_method` ("direct_description", "action_inference", "dialogue", etc.)
     - `keywords` (JSON array)
     - `confidence`

2. **API para obtener evidencias:**
   ```python
   @app.get("/api/attributes/{attribute_id}/evidences")
   def get_attribute_evidences(attribute_id: int) -> list[AttributeEvidence]:
       ...
   ```

---

## 4. Historial Sin Caducidad {#historial-permanente}

### Problema Original

El diseño mencionaba "historial de 30 días" para fusiones de entidades y otras acciones.

### Solución: Historial Permanente

**Cambio obligatorio:**

❌ **ELIMINAR:** Cualquier caducidad de historial (30 días, 90 días, etc.)

✅ **IMPLEMENTAR:** Historial completo sin límite temporal

**Razón:** El corrector puede necesitar revertir decisiones semanas o meses después, especialmente si el manuscrito pasa por múltiples revisiones.

### Tabla de Historial (Backend)

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'entity_merge', 'alert_resolve', 'attribute_validate'
    action_data JSON NOT NULL,  -- Detalles específicos de la acción
    user_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reverted_at TIMESTAMP NULL,

    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- NO hay campo de expiración
-- NO hay proceso de limpieza automática
```

### Panel de Historial

```
┌─────────────────────────────────────────────────────────────┐
│ 📜 HISTORIAL DEL PROYECTO                    [Buscar: ___] │
├─────────────────────────────────────────────────────────────┤
│ Filtrar: [Todos ▼] [Últimos 7 días ▼] [Solo reversiones]  │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ 2026-01-10 14:32                                           │
│ ✓ Alerta resuelta: "Color de ojos inconsistente"          │
│   María González                                            │
│   Nota: "Corregido en manuscrito v2.1"                     │
│   [Deshacer] [Ver detalles]                                │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ 2026-01-09 11:15                                           │
│ 🔀 Entidades fusionadas: "Ana" + "Anna" → "Ana María"     │
│   20 menciones unificadas                                  │
│   [Deshacer fusión] [Ver detalles]                         │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ 2026-01-08 16:48                                           │
│ ✓ Atributo validado: María González - Edad: 30 años       │
│   [Deshacer] [Ver detalles]                                │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│ 2025-12-20 09:22  ← Hace 3 semanas                        │
│ ⟲ REVERSIÓN: Fusión deshecha "Juan" + "Dr. Pérez"        │
│   Razón: Eran personajes diferentes                        │
│   [Ver detalles]                                            │
│                                                             │
│ [... historial completo desde creación del proyecto ...]  │
│                                                             │
│ Mostrando 4 de 127 acciones                                │
│ [Cargar más (123 restantes)]                              │
└─────────────────────────────────────────────────────────────┘
```

### Características del Historial

1. **Búsqueda:** Por entidad, tipo de acción, fecha
2. **Filtrado:** Por rango de fechas, tipo de acción
3. **Paginación:** Carga incremental para proyectos con miles de acciones
4. **Exportación:** Posibilidad de exportar historial completo

### Deshacer Acciones

**Reglas:**
- Cualquier acción es reversible mientras el proyecto exista
- Sistema verifica conflictos antes de deshacer:
  - Si fusionaste A+B y luego fusionaste (A+B)+C, al deshacer la primera fusión se debe deshacer también la segunda
- Confirmación obligatoria con advertencia de conflictos

```vue
<script setup lang="ts">
const undoAction = async (historyItem: HistoryItem) => {
  // Verificar conflictos
  const conflicts = await historyStore.checkUndoConflicts(historyItem.id);

  if (conflicts.length > 0) {
    const message = `
      Esta acción tiene ${conflicts.length} dependencia(s):
      ${conflicts.map(c => `- ${c.description}`).join('\n')}

      Al deshacer, también se revertirán estas acciones.
      ¿Deseas continuar?
    `;

    if (!confirm(message)) return;
  }

  await historyStore.undoAction(historyItem.id);
};
</script>
```

---

## 5. Cambios en Componentes {#cambios-componentes}

### Resumen de Cambios Obligatorios

#### Componente: ManuscriptViewer.vue

**Añadir:**
- Tokens clicables para entidades
- Eventos `@click` en menciones
- Integración con Inspector Panel
- Estados hover y activo

#### Componente: AlertDetail.vue

**Cambiar:**
- ❌ Botón genérico "Ver contexto"
- ✅ Enlace clicable en cada ubicación (`Cap. X, pág. Y`)
- ✅ Múltiples contextos con excerpts
- ✅ Botón "Comparar contextos" (si 2+ fuentes)

#### Componente: AttributesList.vue

**Cambiar:**
- ❌ Botón "+ Añadir atributo manualmente"
- ✅ Valores de atributos clicables
- ✅ Dialog de evidencias con lista completa
- ✅ Enlaces a cada evidencia en el texto
- ✅ Mostrar método de extracción y keywords

#### Componente: EntityDetail.vue

**Añadir:**
- Indicador "TÚ ESTÁS AQUÍ" si se abrió desde una mención
- Scroll automático a la mención actual en lista de menciones

#### Store: historyStore.ts

**Cambiar:**
- ❌ Lógica de expiración/limpieza
- ✅ Carga completa sin límite temporal
- ✅ Paginación eficiente
- ✅ Verificación de conflictos en undo

---

## Conclusiones

Estos cambios mejoran significativamente la **trazabilidad**, **navegabilidad** y **transparencia** del sistema:

1. **Navegación fluida:** Cualquier entidad en el texto es un punto de acceso a información
2. **Contextos claros:** Cada alerta muestra todos sus contextos con enlaces directos
3. **Transparencia total:** Cada atributo muestra las evidencias que lo soportan
4. **Historial confiable:** Sin caducidad, el corrector puede auditar decisiones antiguas

**Próximo paso:** Actualizar wireframes y prototipos con estos cambios antes de implementación.
