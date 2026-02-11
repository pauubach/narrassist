<template>
  <div class="ds-skeleton" :class="[`ds-skeleton--${variant}`]">
    <template v-if="variant === 'list'">
      <div v-for="i in rows" :key="i" class="ds-skeleton__row">
        <div v-if="showAvatar" class="ds-skeleton__avatar shimmer" />
        <div class="ds-skeleton__content">
          <div class="ds-skeleton__line ds-skeleton__line--primary shimmer" />
          <div class="ds-skeleton__line ds-skeleton__line--secondary shimmer" />
        </div>
      </div>
    </template>

    <template v-else-if="variant === 'card'">
      <div v-for="i in rows" :key="i" class="ds-skeleton__card">
        <div class="ds-skeleton__card-header shimmer" />
        <div class="ds-skeleton__card-body">
          <div class="ds-skeleton__line shimmer" style="width: 80%" />
          <div class="ds-skeleton__line shimmer" style="width: 60%" />
        </div>
      </div>
    </template>

    <template v-else>
      <!-- variant === 'text' -->
      <div
        v-for="i in rows" :key="i" class="ds-skeleton__line shimmer"
        :style="{ width: lineWidth(i) }"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
interface Props {
  variant?: 'text' | 'list' | 'card'
  rows?: number
  showAvatar?: boolean
}

withDefaults(defineProps<Props>(), {
  variant: 'list',
  rows: 4,
  showAvatar: false,
})

function lineWidth(index: number): string {
  const widths = ['100%', '85%', '92%', '70%', '78%', '95%']
  return widths[(index - 1) % widths.length]
}
</script>

<style scoped>
.ds-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3, 0.75rem);
  padding: var(--ds-space-2, 0.5rem) 0;
}

/* Shimmer animation */
.shimmer {
  background: linear-gradient(
    90deg,
    var(--surface-100, #f1f5f9) 0px,
    var(--surface-200, #e2e8f0) 40px,
    var(--surface-100, #f1f5f9) 80px
  );
  background-size: 600px;
  animation: ds-shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes ds-shimmer {
  0% { background-position: -468px 0; }
  100% { background-position: 468px 0; }
}

/* Text variant */
.ds-skeleton__line {
  height: 12px;
  border-radius: 4px;
}

.ds-skeleton__line--primary {
  height: 14px;
  width: 60%;
}

.ds-skeleton__line--secondary {
  height: 10px;
  width: 40%;
  opacity: 0.6;
}

/* List variant */
.ds-skeleton__row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3, 0.75rem);
  padding: var(--ds-space-2, 0.5rem) 0;
}

.ds-skeleton__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ds-skeleton__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1, 0.25rem);
}

/* Card variant */
.ds-skeleton__card {
  border: 1px solid var(--surface-border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
}

.ds-skeleton__card-header {
  height: 20px;
  margin: var(--ds-space-3, 0.75rem);
  width: 50%;
}

.ds-skeleton__card-body {
  padding: 0 var(--ds-space-3, 0.75rem) var(--ds-space-3, 0.75rem);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .shimmer {
    animation: none;
  }
}
</style>
