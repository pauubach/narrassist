<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'

/**
 * AlertDiffView - Vista comparativa Original vs Propuesta
 *
 * Muestra el texto original (excerpt) y la sugerencia de corrección
 * lado a lado o apilado según el espacio disponible.
 *
 * Usa CSS container queries para adaptar el layout:
 * - ≥700px: side-by-side (2 columnas)
 * - <700px: stacked (vertical)
 * - <500px: solo propuesta + botón "Ver original"
 */

withDefaults(defineProps<{
  /** Texto original del manuscrito */
  excerpt: string
  /** Sugerencia de corrección */
  suggestion: string
  /** Forzar un layout específico (auto usa container queries) */
  layout?: 'auto' | 'side-by-side' | 'stacked' | 'compact'
}>(), {
  layout: 'auto'
})

const showOriginal = ref(false)
</script>

<template>
  <div
    class="alert-diff-view"
    :class="[`layout-${layout}`]"
  >
    <!-- Original (excerpt) -->
    <div class="diff-panel diff-original">
      <div class="diff-label">
        <i class="pi pi-file-edit"></i>
        Original
      </div>
      <div class="diff-content diff-content--remove">
        <p class="diff-text">"{{ excerpt }}"</p>
      </div>
    </div>

    <!-- Propuesta (suggestion) -->
    <div class="diff-panel diff-proposed">
      <div class="diff-label">
        <i class="pi pi-lightbulb"></i>
        Propuesta
      </div>
      <div class="diff-content diff-content--add">
        <p class="diff-text">{{ suggestion }}</p>
      </div>
    </div>

    <!-- Compact mode: toggle for original -->
    <div class="diff-compact-toggle">
      <Button
        :label="showOriginal ? 'Ocultar original' : 'Ver original'"
        :icon="showOriginal ? 'pi pi-eye-slash' : 'pi pi-eye'"
        text
        size="small"
        @click="showOriginal = !showOriginal"
      />
      <div v-if="showOriginal" class="diff-compact-original">
        <div class="diff-content diff-content--remove">
          <p class="diff-text">"{{ excerpt }}"</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alert-diff-view {
  container-type: inline-size;
  display: flex;
  gap: var(--ds-space-3, 0.75rem);
  border-radius: var(--ds-radius-md, 6px);
  overflow: hidden;
}

/* ── Panels ── */
.diff-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.diff-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: var(--ds-space-2, 0.5rem) var(--ds-space-3, 0.75rem);
}

.diff-label i {
  font-size: 0.75rem;
}

.diff-content {
  flex: 1;
  padding: var(--ds-space-3, 0.75rem);
  border-left: 3px solid;
}

.diff-text {
  margin: 0;
  font-size: var(--ds-font-size-sm, 0.875rem);
  line-height: 1.6;
  font-style: italic;
}

/* ── Original (red) ── */
.diff-original .diff-label {
  color: var(--red-700);
  background: var(--red-50);
}

.diff-content--remove {
  background: var(--red-50);
  border-color: var(--red-400);
  color: var(--red-900);
}

/* ── Proposed (green) ── */
.diff-proposed .diff-label {
  color: var(--green-700);
  background: var(--green-50);
}

.diff-content--add {
  background: var(--green-50);
  border-color: var(--green-400);
  color: var(--green-900);
}

/* ── Compact toggle (hidden by default, visible <500px) ── */
.diff-compact-toggle {
  display: none;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
  margin-top: var(--ds-space-2, 0.5rem);
}

.diff-compact-original {
  border-radius: var(--ds-radius-md, 6px);
  overflow: hidden;
}

/* ═══════════════════════════════════════════════════
   Layout: auto (container queries)
   ═══════════════════════════════════════════════════ */
.layout-auto {
  flex-direction: row;
}

/* ≥700px: side-by-side */
@container (min-width: 700px) {
  .layout-auto {
    flex-direction: row;
  }
  .layout-auto .diff-panel { display: flex; }
  .layout-auto .diff-compact-toggle { display: none; }
}

/* <700px: stacked */
@container (max-width: 699px) {
  .layout-auto {
    flex-direction: column;
  }
  .layout-auto .diff-panel { display: flex; }
  .layout-auto .diff-compact-toggle { display: none; }
}

/* <500px: compact (only proposed + toggle for original) */
@container (max-width: 499px) {
  .layout-auto {
    flex-direction: column;
  }
  .layout-auto .diff-original { display: none; }
  .layout-auto .diff-proposed { display: flex; }
  .layout-auto .diff-compact-toggle { display: flex; }
}

/* ═══════════════════════════════════════════════════
   Layout: forced side-by-side
   ═══════════════════════════════════════════════════ */
.layout-side-by-side {
  flex-direction: row;
}
.layout-side-by-side .diff-compact-toggle { display: none; }

/* ═══════════════════════════════════════════════════
   Layout: forced stacked
   ═══════════════════════════════════════════════════ */
.layout-stacked {
  flex-direction: column;
}
.layout-stacked .diff-compact-toggle { display: none; }

/* ═══════════════════════════════════════════════════
   Layout: forced compact
   ═══════════════════════════════════════════════════ */
.layout-compact {
  flex-direction: column;
}
.layout-compact .diff-original { display: none; }
.layout-compact .diff-compact-toggle { display: flex; }

/* ═══════════════════════════════════════════════════
   Dark mode
   ═══════════════════════════════════════════════════ */
:global(.dark) .diff-original .diff-label {
  color: var(--red-300);
  background: var(--red-900);
}

:global(.dark) .diff-content--remove {
  background: color-mix(in srgb, var(--red-900) 40%, transparent);
  border-color: var(--red-700);
  color: var(--red-200);
}

:global(.dark) .diff-proposed .diff-label {
  color: var(--green-300);
  background: var(--green-900);
}

:global(.dark) .diff-content--add {
  background: color-mix(in srgb, var(--green-900) 40%, transparent);
  border-color: var(--green-700);
  color: var(--green-200);
}
</style>
