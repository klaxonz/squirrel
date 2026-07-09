<template>
  <component
    :is="as"
    v-bind="as === 'button' ? { type: 'button' } : { tabindex: 0 }"
    :role="role"
    :aria-selected="selected"
    :class="cn(
      'app-list-option',
      compact && 'app-list-option--compact',
      selected && 'is-selected',
      danger && 'app-list-option--danger',
      props.class,
    )"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/shared/lib/utils'

const props = withDefaults(defineProps<{
  as?: 'button' | 'div'
  selected?: boolean
  danger?: boolean
  role?: 'option' | 'menuitem'
  compact?: boolean
  class?: HTMLAttributes['class']
}>(), {
  as: 'button',
  selected: false,
  danger: false,
  compact: false,
  role: 'option',
})
</script>

<style scoped>
.app-list-option {
  display: flex;
  min-height: 2.25rem;
  width: 100%;
  align-items: center;
  gap: 0.625rem;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0.375rem 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
}

/* Dense nav rows (settings tabs, filter lists). */
.app-list-option--compact {
  min-height: 2rem;
  gap: 0.5rem;
  padding: 0.25rem 0.625rem;
  font-size: 0.8125rem;
}

.app-list-option:hover,
.app-list-option:focus-visible {
  background: hsl(var(--accent) / 0.48);
  color: hsl(var(--foreground));
  outline: none;
}

.app-list-option.is-selected {
  border-color: hsl(var(--primary) / 0.18);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--foreground));
  font-weight: 650;
}

.app-list-option--danger:hover,
.app-list-option--danger:focus-visible {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

@media (prefers-reduced-motion: reduce) {
  .app-list-option {
    transition: none;
  }
}
</style>
