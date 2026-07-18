<template>
  <div
    role="button"
    tabindex="0"
    :class="cn(
      'app-selectable-list-item',
      variant === 'flush' && 'app-selectable-list-item--flush',
      selected && 'is-selected',
      props.class,
    )"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

const props = withDefaults(defineProps<{
  selected?: boolean
  /** default: padded card rows; flush: continuous list (Fluent Reader style). */
  variant?: 'default' | 'flush'
  class?: HTMLAttributes['class']
}>(), {
  selected: false,
  variant: 'default',
})
</script>

<style scoped>
.app-selectable-list-item {
  position: relative;
  display: flex;
  min-height: 2.75rem;
  width: 100%;
  align-items: center;
  gap: 0.625rem;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
}

.app-selectable-list-item + .app-selectable-list-item {
  margin-top: 0.25rem;
}

.app-selectable-list-item:hover,
.app-selectable-list-item:focus-visible {
  background: hsl(var(--accent) / 0.6);
  color: hsl(var(--foreground));
  outline: none;
}

.app-selectable-list-item.is-selected {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
}

/* Continuous workbench list: hairline separators, no card chrome. */
.app-selectable-list-item--flush {
  min-height: 0;
  align-items: stretch;
  gap: 0;
  border: 0;
  border-radius: 0;
  border-bottom: 1px solid hsl(var(--border) / 0.2);
  padding: 0;
  color: inherit;
}

.app-selectable-list-item--flush + .app-selectable-list-item--flush {
  margin-top: 0;
}

.app-selectable-list-item--flush:hover,
.app-selectable-list-item--flush:focus-visible {
  background: hsl(var(--accent) / 0.32);
  color: inherit;
}

.app-selectable-list-item--flush.is-selected {
  border-color: transparent;
  border-bottom-color: hsl(var(--border) / 0.2);
  background: hsl(var(--accent) / 0.58);
  color: inherit;
  box-shadow: inset 3px 0 0 hsl(var(--foreground) / 0.72);
}

.app-selectable-list-item--flush:focus-visible {
  box-shadow:
    inset 3px 0 0 hsl(var(--foreground) / 0.72),
    inset 0 0 0 1px hsl(var(--ring) / 0.42);
}

:deep(.app-selectable-list-item__actions) {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-default);
}

.app-selectable-list-item:hover :deep(.app-selectable-list-item__actions),
.app-selectable-list-item:focus-within :deep(.app-selectable-list-item__actions) {
  opacity: 1;
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  :deep(.app-selectable-list-item__actions) {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-selectable-list-item,
  :deep(.app-selectable-list-item__actions) {
    transition: none;
  }
}
</style>
