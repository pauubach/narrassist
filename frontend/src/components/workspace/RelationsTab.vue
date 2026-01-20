<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
import ProgressSpinner from 'primevue/progressspinner'
import type { Entity } from '@/types'

// Lazy loading de RelationshipGraph (vis-network es pesado ~300KB)
// Solo se carga cuando el usuario accede a la pestaña de relaciones
const RelationshipGraph = defineAsyncComponent({
  loader: () => import('@/components/RelationshipGraph.vue'),
  loadingComponent: {
    template: `
      <div class="graph-loading">
        <ProgressSpinner style="width: 50px; height: 50px" />
        <p>Cargando visualización de relaciones...</p>
      </div>
    `,
    components: { ProgressSpinner }
  },
  delay: 200, // Mostrar loading después de 200ms
  timeout: 30000 // Timeout de 30 segundos
})

/**
 * RelationsTab - Pestaña de visualización de relaciones
 *
 * Contenedor simple que delega todo al componente RelationshipGraph,
 * que incluye su propio toolbar con controles de layout, filtros y zoom.
 */

interface Props {
  /** ID del proyecto */
  projectId: number
  /** Entidades del proyecto (para filtros) */
  entities: Entity[]
  /** Datos de relaciones pre-cargados */
  relationships?: any
  /** Si está cargando */
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  relationships: null
})

const emit = defineEmits<{
  'entity-select': [entity: Entity]
  'refresh': []
}>()

// Handler para selección de entidad
function handleEntitySelect(entityId: number) {
  const entity = props.entities.find(e => e.id === entityId)
  if (entity) {
    emit('entity-select', entity)
  }
}
</script>

<template>
  <div class="relations-tab">
    <!-- RelationshipGraph incluye su propio toolbar con controles de layout, filtros y zoom -->
    <RelationshipGraph
      :project-id="projectId"
      :data="relationships"
      @entitySelect="handleEntitySelect"
    />
  </div>
</template>

<style scoped>
.relations-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Lazy loading state */
.graph-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.graph-loading p {
  margin: 0;
  font-size: 0.9rem;
}
</style>
