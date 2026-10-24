<template>
  <nav v-hover-fill class="app-section-nav" :aria-label="ariaLabel">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="app-section-nav__item"
      data-hover-fill-item
      :class="{ 'is-active': modelValue === option.value }"
      :aria-current="modelValue === option.value ? 'page' : undefined"
      @click="selectOption(option.value)"
    >
      <span>{{ option.label }}</span>
      <span
        v-if="option.badge !== null && option.badge !== undefined && option.badge !== ''"
        class="app-section-nav__badge app-mono"
      >
        {{ option.badge }}
      </span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { hoverFill as vHoverFill } from '@/shared/directives/hoverFill'

export interface AppSectionNavOption {
  value: string | number
  label: string
  badge?: string | number | null
}

const props = withDefaults(defineProps<{
  modelValue: string | number
  options: readonly AppSectionNavOption[]
  ariaLabel?: string
}>(), {
  ariaLabel: '',
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
}>()

const selectOption = (value: string | number) => {
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.app-section-nav {
  display: flex;
  min-width: 0;
  flex: none;
  align-items: center;
  gap: 0.125rem;
}

.app-section-nav--optical {
  margin-inline-start: 0;
}

.app-section-nav__item {
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: 0.375rem;
  border-radius: var(--app-control-radius);
  padding: 0 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.app-section-nav__item:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--foreground) / 0.06);
}

.app-section-nav__item:focus-visible {
  color: hsl(var(--foreground));
  outline: 2px solid hsl(var(--ring));
  outline-offset: 0.15rem;
}

.app-section-nav__item.is-active {
  color: hsl(var(--foreground));
  background: var(--app-selection-bg);
}

.app-section-nav__badge {
  min-width: 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
  line-height: 1;
  text-align: center;
}

@media (prefers-reduced-motion: reduce) {
  .app-section-nav__item {
    transition: none;
  }
}

@media (min-width: 1280px) {
  .app-section-nav--optical {
    margin-inline-start: 0;
  }
}
</style>
