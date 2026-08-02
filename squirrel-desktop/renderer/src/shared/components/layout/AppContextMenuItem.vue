<template>
  <button
    type="button"
    tabindex="-1"
    :role="role"
    :aria-checked="ariaChecked"
    :class="cn('app-context-menu-item', compact && 'app-context-menu-item--compact', danger && 'app-context-menu-item--danger', props.class)"
  >
    <AppIcon v-if="icon" :name="icon" class="app-context-menu-item__icon" />
    <span class="app-context-menu-item__label">
      <slot />
    </span>
    <AppIcon v-if="checked" name="check" class="app-context-menu-item__check" />
  </button>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { cn } from '@/shared/lib/utils'

const props = withDefaults(defineProps<{
  icon?: AppIconName
  checked?: boolean
  compact?: boolean
  danger?: boolean
  role?: 'menuitem' | 'menuitemradio'
  class?: HTMLAttributes['class']
}>(), {
  checked: false,
  compact: false,
  danger: false,
  role: 'menuitem',
})

const ariaChecked = computed(() =>
  props.role === 'menuitemradio' ? props.checked : undefined,
)
</script>

<style scoped>
.app-context-menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2rem;
  padding: 0 0.625rem;
  border-radius: var(--radius-md);
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.app-context-menu-item:hover,
.app-context-menu-item:focus-visible {
  background: var(--app-row-hover-bg);
  outline: none;
}

.app-context-menu-item--compact {
  min-height: 1.75rem;
}

.app-context-menu-item--danger {
  color: hsl(var(--destructive));
}

.app-context-menu-item__icon {
  width: 0.875rem;
  height: 0.875rem;
  flex: 0 0 auto;
  opacity: 0.7;
}

.app-context-menu-item__label {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-context-menu-item__check {
  width: 0.75rem;
  height: 0.75rem;
  flex: 0 0 auto;
  color: var(--app-selection-fg);
}

@media (prefers-reduced-motion: reduce) {
  .app-context-menu-item {
    transition: none;
  }
}
</style>
