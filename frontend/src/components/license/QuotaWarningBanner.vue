<template>
  <div
    v-if="showBanner"
    class="quota-warning-banner"
    :class="bannerClass"
    role="alert"
  >
    <i :class="bannerIcon"></i>
    <div class="quota-warning-banner__text">
      <span class="quota-warning-banner__title">{{ bannerTitle }}</span>
      <span class="quota-warning-banner__hint">{{ bannerHint }}</span>
    </div>
    <button
      class="quota-warning-banner__action"
      @click="$emit('upgrade')"
    >
      {{ actionLabel }}
    </button>
    <button
      class="quota-warning-banner__close"
      aria-label="Cerrar aviso"
      @click="dismiss"
    >
      <i class="pi pi-times"></i>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useLicenseStore } from '@/stores/license'

defineEmits<{
  (e: 'upgrade'): void
}>()

const licenseStore = useLicenseStore()

const SESSION_KEY = 'na_quota_banner_dismissed_level'

const dismissedLevel = ref<string | null>(
  sessionStorage.getItem(SESSION_KEY)
)

function dismiss() {
  dismissedLevel.value = licenseStore.quotaWarningLevel
  sessionStorage.setItem(SESSION_KEY, licenseStore.quotaWarningLevel)
}

// Reappear if warning level escalates beyond the dismissed level
const levelOrder = { none: 0, warning: 1, danger: 2, critical: 3 } as const

watch(
  () => licenseStore.quotaWarningLevel,
  (newLevel) => {
    if (
      dismissedLevel.value &&
      levelOrder[newLevel] > levelOrder[dismissedLevel.value as keyof typeof levelOrder]
    ) {
      dismissedLevel.value = null
      sessionStorage.removeItem(SESSION_KEY)
    }
  }
)

const showBanner = computed(() => {
  const level = licenseStore.quotaWarningLevel
  if (level === 'none') return false
  if (!licenseStore.isLicensed) return false
  if (licenseStore.licenseInfo?.unlimited) return false
  if (dismissedLevel.value && levelOrder[level] <= levelOrder[dismissedLevel.value as keyof typeof levelOrder]) return false
  return true
})

const bannerClass = computed(() => {
  return `quota-warning-banner--${licenseStore.quotaWarningLevel}`
})

const bannerIcon = computed(() => {
  const level = licenseStore.quotaWarningLevel
  if (level === 'critical') return 'pi pi-ban'
  if (level === 'danger') return 'pi pi-exclamation-circle'
  return 'pi pi-info-circle'
})

const pagesUsed = computed(() => licenseStore.licenseInfo?.pages_used ?? 0)
const pagesMax = computed(() => licenseStore.licenseInfo?.pages_max ?? 0)
const pagesRemaining = computed(() => licenseStore.licenseInfo?.pages_remaining ?? 0)

const bannerTitle = computed(() => {
  const level = licenseStore.quotaWarningLevel
  if (level === 'critical') return 'Limite de paginas alcanzado'
  if (level === 'danger') return `Quedan pocas paginas (${pagesRemaining.value} restantes)`
  return `Has usado ${pagesUsed.value} de ${pagesMax.value} paginas este mes`
})

const daysRemaining = computed(() => licenseStore.daysRemainingInPeriod)

const bannerHint = computed(() => {
  const level = licenseStore.quotaWarningLevel
  const days = daysRemaining.value
  const daysText = days !== null ? ` Se renueva en ${days} dias.` : ''
  if (level === 'critical') return `No puedes analizar mas documentos hasta el proximo periodo.${daysText}`
  if (level === 'danger') return `Considera ampliar tu plan para evitar interrupciones.${daysText}`
  return `Tu cuota mensual esta llegando al limite.${daysText}`
})

const actionLabel = computed(() => {
  const level = licenseStore.quotaWarningLevel
  if (level === 'warning') return 'Ver planes'
  return 'Ampliar plan'
})
</script>

<style scoped>
.quota-warning-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.quota-warning-banner > i {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.quota-warning-banner__text {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0.1rem;
}

.quota-warning-banner__title {
  font-weight: 600;
}

.quota-warning-banner__hint {
  font-size: 0.8rem;
  opacity: 0.85;
}

.quota-warning-banner__action {
  background: none;
  border: 1px solid currentColor;
  border-radius: var(--p-border-radius);
  padding: 0.25rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s;
}

.quota-warning-banner__action:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.quota-warning-banner__close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0.25rem;
  opacity: 0.7;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.quota-warning-banner__close:hover {
  opacity: 1;
}

/* Warning (80-89%) — yellow */
.quota-warning-banner--warning {
  background-color: var(--p-yellow-50);
  color: var(--p-yellow-700);
  border-bottom: 2px solid var(--p-yellow-200);
}

/* Danger (90-99%) — orange */
.quota-warning-banner--danger {
  background-color: var(--p-orange-50);
  color: var(--p-orange-700);
  border-bottom: 2px solid var(--p-orange-200);
}

/* Critical (100%) — red */
.quota-warning-banner--critical {
  background-color: var(--p-red-50);
  color: var(--p-red-700);
  border-bottom: 2px solid var(--p-red-200);
}

/* Dark mode */
:global(.dark) .quota-warning-banner--warning {
  background-color: var(--p-yellow-900);
  color: var(--p-yellow-100);
  border-color: var(--p-yellow-700);
}

:global(.dark) .quota-warning-banner--danger {
  background-color: var(--p-orange-900);
  color: var(--p-orange-100);
  border-color: var(--p-orange-700);
}

:global(.dark) .quota-warning-banner--critical {
  background-color: var(--p-red-900);
  color: var(--p-red-100);
  border-color: var(--p-red-700);
}
</style>
