<script setup lang="ts">
/**
 * RevisionView — Vista de Revision Intelligence para un proyecto (S14-12).
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import RevisionDashboard from '@/components/revision/RevisionDashboard.vue'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => Number(route.params.id))

function goBack() {
  router.push({ name: 'project', params: { id: route.params.id }, query: { tab: 'alerts' } })
}
</script>

<template>
  <div class="revision-view">
    <div class="revision-nav">
      <Button
        icon="pi pi-arrow-left"
        label="Volver al proyecto"
        text
        @click="goBack"
      />
    </div>
    <RevisionDashboard
      :project-id="projectId"
      @close="goBack"
    />
  </div>
</template>

<style scoped>
.revision-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 16px;
}

.revision-nav {
  margin-bottom: 12px;
}
</style>
