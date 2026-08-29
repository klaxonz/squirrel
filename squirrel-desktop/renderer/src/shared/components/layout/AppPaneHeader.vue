<template>
  <div class="app-pane-header" :class="props.class">
    <div class="app-pane-header__copy">
      <div class="app-pane-header__title-row">
        <component :is="headingLevel" class="app-pane-header__title" :class="titleClass">
          {{ title }}
        </component>
        <slot name="meta" />
      </div>
      <p v-if="subtitle || description" class="app-pane-header__subtitle">
        {{ subtitle || description }}
      </p>
    </div>
    <div v-if="$slots.actions" class="app-pane-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { HTMLAttributes } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  /** Compact workbench subtitle (preferred). */
  subtitle?: string
  /** Alias for subtitle. */
  description?: string
  /** Heading element / scale. Default h2 uses .app-h2. */
  level?: 1 | 2 | 3
  class?: HTMLAttributes['class']
}>(), {
  subtitle: '',
  description: '',
  level: 2,
})

const headingLevel = computed(() => `h${props.level}` as 'h1' | 'h2' | 'h3')
const titleClass = computed(() => {
  if (props.level === 1) return 'app-h1'
  if (props.level === 3) return 'app-h3'
  return 'app-h2'
})
</script>

<style scoped>
/*
  Shared main-pane header for workbench pages (title + optional subtitle +
  actions). Replaces the hand-rolled min-w-0 / flex shrink-0 patterns that
  every two-column view re-implemented.
*/
.app-pane-header {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.app-pane-header__copy {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.app-pane-header__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.app-pane-header__title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-wrap: balance;
}

.app-pane-header__subtitle {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.35;
  text-wrap: pretty;
}

.app-pane-header__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
