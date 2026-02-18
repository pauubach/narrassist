<script setup lang="ts">
import { computed, ref, toRef } from 'vue'
import Button from 'primevue/button'
import { useWordDiff } from '@/composables/useWordDiff'

/**
 * AlertDiffView - Vista comparativa con diff a nivel de palabra (estilo GitHub)
 *
 * Modo default (inline): texto unificado donde las palabras eliminadas
 * aparecen en rojo+tachado (<del>) y las añadidas en verde (<ins>).
 *
 * Modo side-by-side: dos paneles con word-level highlighting.
 *
 * Usa CSS container queries para adaptar el layout automáticamente.
 */

const props = withDefaults(defineProps<{
  /** Texto original del manuscrito */
  excerpt: string
  /** Sugerencia de corrección */
  suggestion: string
  /** Layout: auto/inline (unificado), side-by-side, stacked, compact */
  layout?: 'auto' | 'inline' | 'side-by-side' | 'stacked' | 'compact'
}>(), {
  layout: 'auto'
})

const { segments, isDiffMeaningful } = useWordDiff(
  toRef(props, 'excerpt'),
  toRef(props, 'suggestion')
)

/** Para side-by-side: segmentos solo del original (unchanged + removed) */
const originalSegments = computed(() =>
  segments.value.filter(s => s.type !== 'added')
)

/** Para side-by-side: segmentos solo de la propuesta (unchanged + added) */
const proposedSegments = computed(() =>
  segments.value.filter(s => s.type !== 'removed')
)

/** Layout efectivo */
const effectiveLayout = computed(() =>
  props.layout === 'auto' ? 'inline' : props.layout
)

const showOriginal = ref(false)
</script>

<template>
  <div
    class="alert-diff-view"
    :class="[`layout-${effectiveLayout}`]"
  >
    <!-- ══════════ Non-diff fallback (suggestion is an instruction, not a rewrite) ══════════ -->
    <template v-if="!isDiffMeaningful">
      <div class="diff-panel diff-original">
        <div class="diff-label">
          <i class="pi pi-file-edit"></i>
          Original
        </div>
        <div class="diff-content diff-content--remove">
          <p class="diff-text">{{ excerpt }}</p>
        </div>
      </div>
      <div class="diff-panel diff-proposed">
        <div class="diff-label">
          <i class="pi pi-lightbulb"></i>
          Sugerencia
        </div>
        <div class="diff-content diff-content--add">
          <p class="diff-text">{{ suggestion }}</p>
        </div>
      </div>
    </template>

    <!-- ══════════ Inline (unified) ══════════ -->
    <div v-else-if="effectiveLayout === 'inline'" class="diff-inline-panel">
      <div class="diff-label diff-label--inline">
        <i class="pi pi-arrows-h"></i>
        Cambios
      </div>
      <div class="diff-content diff-content--inline">
        <p class="diff-text-inline">
          <template v-for="(seg, i) in segments" :key="i">
            <del v-if="seg.type === 'removed'" class="diff-del">{{ seg.value }}</del>
            <ins v-else-if="seg.type === 'added'" class="diff-ins">{{ seg.value }}</ins>
            <span v-else>{{ seg.value }}</span>
          </template>
        </p>
      </div>
    </div>

    <!-- ══════════ Side-by-side / Stacked ══════════ -->
    <template v-else-if="effectiveLayout === 'side-by-side' || effectiveLayout === 'stacked'">
      <!-- Original -->
      <div class="diff-panel diff-original">
        <div class="diff-label">
          <i class="pi pi-file-edit"></i>
          Original
        </div>
        <div class="diff-content diff-content--remove">
          <p class="diff-text">
            <template v-for="(seg, i) in originalSegments" :key="i">
              <del v-if="seg.type === 'removed'" class="diff-del">{{ seg.value }}</del>
              <span v-else>{{ seg.value }}</span>
            </template>
          </p>
        </div>
      </div>

      <!-- Propuesta -->
      <div class="diff-panel diff-proposed">
        <div class="diff-label">
          <i class="pi pi-lightbulb"></i>
          Propuesta
        </div>
        <div class="diff-content diff-content--add">
          <p class="diff-text">
            <template v-for="(seg, i) in proposedSegments" :key="i">
              <ins v-if="seg.type === 'added'" class="diff-ins">{{ seg.value }}</ins>
              <span v-else>{{ seg.value }}</span>
            </template>
          </p>
        </div>
      </div>
    </template>

    <!-- ══════════ Compact ══════════ -->
    <template v-else>
      <!-- Solo propuesta con diff inline -->
      <div class="diff-panel diff-proposed">
        <div class="diff-label">
          <i class="pi pi-lightbulb"></i>
          Propuesta
        </div>
        <div class="diff-content diff-content--add">
          <p class="diff-text">{{ suggestion }}</p>
        </div>
      </div>
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
    </template>
  </div>
</template>

<style scoped>
.alert-diff-view {
  container-type: inline-size;
  border-radius: var(--ds-radius-md, 6px);
  overflow: hidden;
}

/* ── Layout modes ── */
.layout-inline {
  display: flex;
  flex-direction: column;
}

.layout-side-by-side {
  display: flex;
  flex-direction: row;
  gap: var(--ds-space-3, 0.75rem);
}

.layout-stacked {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3, 0.75rem);
}

.layout-compact {
  display: flex;
  flex-direction: column;
}

/* ── Panels ── */
.diff-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.diff-inline-panel {
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

.diff-text,
.diff-text-inline {
  margin: 0;
  font-size: var(--ds-font-size-sm, 0.875rem);
  line-height: 1.6;
}

/* ── Inline panel styling ── */
.diff-label--inline {
  color: var(--surface-600);
  background: var(--surface-100);
}

.diff-content--inline {
  background: var(--surface-50);
  border-color: var(--surface-300);
  color: var(--surface-900);
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

/* ═══════════════════════════════════════════
   Word-level diff highlights (GitHub-style)
   ═══════════════════════════════════════════ */
.diff-del {
  background: var(--red-200);
  color: var(--red-900);
  text-decoration: line-through;
  text-decoration-color: var(--ds-color-danger, #ef4444);
  border-radius: 3px;
  padding: 1px 3px;
}

.diff-ins {
  background: var(--green-200);
  color: var(--green-900);
  text-decoration: none;
  border-radius: 3px;
  padding: 1px 3px;
  font-weight: 600;
}

/* ── Compact toggle ── */
.diff-compact-toggle {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
  margin-top: var(--ds-space-2, 0.5rem);
}

.diff-compact-original {
  border-radius: var(--ds-radius-md, 6px);
  overflow: hidden;
}

/* ═══════════════════════════════════════════
   Dark mode
   ═══════════════════════════════════════════ */
:global(.dark) .diff-label--inline {
  color: var(--surface-300);
  background: var(--surface-800);
}

:global(.dark) .diff-content--inline {
  background: var(--surface-900);
  border-color: var(--surface-600);
  color: var(--surface-100);
}

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

:global(.dark) .diff-del {
  background: color-mix(in srgb, var(--red-800) 60%, transparent);
  color: var(--red-200);
  text-decoration-color: var(--red-400);
}

:global(.dark) .diff-ins {
  background: color-mix(in srgb, var(--green-800) 60%, transparent);
  color: var(--green-200);
}
</style>
