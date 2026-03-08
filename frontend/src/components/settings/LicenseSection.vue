<template>
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Estado de licencia</label>
      <p class="setting-description">
        {{ licenseStore.isLicensed
          ? `Plan ${licenseStore.tierDisplayName} activo`
          : 'Sin licencia activa' }}
      </p>
    </div>
    <div class="setting-control">
      <Button
        :label="licenseStore.isLicensed ? 'Gestionar licencia' : 'Activar licencia'"
        :icon="licenseStore.isLicensed ? 'pi pi-cog' : 'pi pi-key'"
        :severity="licenseStore.isLicensed ? 'secondary' : undefined"
        outlined
        @click="$emit('showLicenseDialog')"
      />
    </div>
  </div>

  <div v-if="licenseStore.isLicensed && licenseStore.quotaStatus" class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Uso del periodo</label>
      <p class="setting-description">
        {{ licenseStore.quotaStatus.unlimited
          ? 'Páginas ilimitadas'
          : `${licenseStore.quotaStatus.pages_used} / ${licenseStore.quotaStatus.pages_max} páginas` }}
      </p>
    </div>
    <div class="setting-control">
      <Tag
        :value="licenseStore.quotaWarningLevel === 'none' ? 'OK' : licenseStore.quotaWarningLevel"
        :severity="licenseStore.quotaWarningLevel === 'none' ? 'success'
          : licenseStore.quotaWarningLevel === 'warning' ? 'warn'
            : 'danger'"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useLicenseStore } from '@/stores/license'

defineEmits<{
  showLicenseDialog: []
}>()

const licenseStore = useLicenseStore()
</script>
