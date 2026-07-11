<template>
  <div
    role="button"
    tabindex="0"
    :class="cn(
      'app-selectable-list-item',
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
  class?: HTMLAttributes['class']
}>(), {
  selected: false,
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

@media (prefers-reduced-motion: reduce) {
  .app-selectable-list-item,
  :deep(.app-selectable-list-item__actions) {
    transition: none;
  }
}
</style>
