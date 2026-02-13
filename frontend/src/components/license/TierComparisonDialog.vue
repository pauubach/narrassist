<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :draggable="false"
    :block-scroll="true"
    header="Comparar planes"
    :style="{ width: '700px', maxWidth: '95vw' }"
    class="tier-comparison-dialog"
  >
    <div class="tier-comparison">
      <!-- Founding member badge -->
      <div v-if="isFoundingMember" class="founding-badge">
        <i class="pi pi-star-fill"></i>
        <span>Miembro fundador — precios especiales de por vida</span>
      </div>

      <table class="tier-table">
        <thead>
          <tr>
            <th class="feature-col"></th>
            <th
              v-for="plan in plans"
              :key="plan.key"
              :class="['plan-col', { 'plan-current': plan.key === currentTier }]"
            >
              <div class="plan-header">
                <span class="plan-name">{{ plan.name }}</span>
                <span class="plan-price">{{ plan.price }}</span>
                <span v-if="plan.priceNote" class="plan-price-note">{{ plan.priceNote }}</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in featureRows" :key="row.label">
            <td class="feature-label">{{ row.label }}</td>
            <td
              v-for="plan in plans"
              :key="plan.key"
              :class="['feature-cell', { 'plan-current': plan.key === currentTier }]"
            >
              <template v-if="typeof row[plan.key] === 'boolean'">
                <i v-if="row[plan.key]" class="pi pi-check feature-yes"></i>
                <i v-else class="pi pi-minus feature-no"></i>
              </template>
              <span v-else class="feature-text">{{ row[plan.key] }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="tier-cta">
        <a
          href="mailto:hola@narrativeassistant.com?subject=Upgrade%20de%20plan"
          class="cta-link"
        >
          <i class="pi pi-envelope"></i>
          Contactar para upgrade
        </a>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import { useLicenseStore } from '@/stores/license'

interface Props {
  visible: boolean
}
interface Emits {
  (e: 'update:visible', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const licenseStore = useLicenseStore()

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

const currentTier = computed(() => licenseStore.tier)

const isFoundingMember = computed(() => {
  return licenseStore.licenseInfo?.is_founding_member === true
})

const plans = computed(() => {
  if (isFoundingMember.value) {
    return [
      { key: 'corrector' as const, name: 'Corrector', price: '19 \u20AC/mes', priceNote: '(fundador)' },
      { key: 'profesional' as const, name: 'Profesional', price: '34 \u20AC/mes', priceNote: '(fundador)' },
      { key: 'editorial' as const, name: 'Editorial', price: '119 \u20AC/mes', priceNote: '(fundador)' },
    ]
  }
  return [
    { key: 'corrector' as const, name: 'Corrector', price: '24 \u20AC/mes', priceNote: '' },
    { key: 'profesional' as const, name: 'Profesional', price: '49 \u20AC/mes', priceNote: '' },
    { key: 'editorial' as const, name: 'Editorial', price: '159 \u20AC/mes', priceNote: '' },
  ]
})

interface FeatureRow {
  label: string
  corrector: boolean | string
  profesional: boolean | string
  editorial: boolean | string
}

const featureRows: FeatureRow[] = [
  {
    label: 'Consistencia de atributos',
    corrector: true, profesional: true, editorial: true,
  },
  {
    label: 'Gramatica y ortografia',
    corrector: true, profesional: true, editorial: true,
  },
  {
    label: 'Entidades y correferencias',
    corrector: true, profesional: true, editorial: true,
  },
  {
    label: 'Variantes de nombres',
    corrector: true, profesional: true, editorial: true,
  },
  {
    label: 'Perfiles de personajes',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Analisis de relaciones',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Deteccion de anacronismos',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Deteccion fuera de caracter',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Espanol clasico',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Multi-modelo (votacion)',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Informes completos',
    corrector: false, profesional: true, editorial: true,
  },
  {
    label: 'Export/Import editorial',
    corrector: false, profesional: false, editorial: true,
  },
  {
    label: 'Paginas/mes',
    corrector: '1.500', profesional: '3.000', editorial: 'Ilimitadas',
  },
  {
    label: 'Dispositivos',
    corrector: '1', profesional: '1', editorial: '3+',
  },
  {
    label: 'Manuscrito max',
    corrector: '60k palabras', profesional: 'Ilimitado', editorial: 'Ilimitado',
  },
]
</script>

<style scoped>
.tier-comparison {
  padding: 0.5rem 0;
}

.founding-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: color-mix(in srgb, var(--p-yellow-500) 15%, transparent);
  border-radius: var(--p-border-radius);
  margin-bottom: 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--p-yellow-700);
}

:global(.dark) .founding-badge {
  color: var(--p-yellow-200);
}

.founding-badge i {
  color: var(--p-yellow-500);
}

.tier-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.tier-table th,
.tier-table td {
  padding: 0.5rem 0.75rem;
  text-align: center;
  border-bottom: 1px solid var(--p-surface-200);
}

:global(.dark) .tier-table th,
:global(.dark) .tier-table td {
  border-color: var(--p-surface-700);
}

.feature-col {
  width: 35%;
  text-align: left;
}

.feature-label {
  text-align: left;
  color: var(--p-text-color);
  font-size: 0.85rem;
}

.plan-col {
  width: calc(65% / 3);
}

.plan-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.plan-name {
  font-weight: 700;
  font-size: 0.95rem;
}

.plan-price {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.plan-price-note {
  font-size: 0.7rem;
  color: var(--p-yellow-600);
  font-weight: 500;
}

/* Current tier highlight */
.plan-current {
  background-color: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
  border-left: 2px solid var(--p-primary-color);
  border-right: 2px solid var(--p-primary-color);
}

th.plan-current {
  border-top: 2px solid var(--p-primary-color);
}

tbody tr:last-child td.plan-current {
  border-bottom: 2px solid var(--p-primary-color);
}

.feature-yes {
  color: var(--p-green-500);
  font-size: 1rem;
}

.feature-no {
  color: var(--p-surface-400);
  font-size: 0.85rem;
}

.feature-text {
  font-weight: 500;
  font-size: 0.8rem;
}

.tier-cta {
  display: flex;
  justify-content: center;
  margin-top: 1.5rem;
}

.cta-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.5rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-radius: var(--p-border-radius);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
  transition: opacity 0.15s;
}

.cta-link:hover {
  opacity: 0.9;
}
</style>
