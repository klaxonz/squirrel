<template>
  <nav class="app-section-nav" :aria-label="ariaLabel">
    <Button
      v-for="option in options"
      :key="option.value"
      unstyled
      type="button"
      class="app-section-nav__item"
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
    </Button>
  </nav>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'

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
  gap: var(--space-5);
}

.app-section-nav--optical {
  margin-inline-start: calc(var(--space-2) * -1);
}

.app-section-nav__item {
  position: relative;
  display: inline-flex;
  height: 2.5rem;
  align-items: center;
  gap: 0.325rem;
  border-radius: 0;
  padding: 0;
  color: hsl(var(--muted-foreground) / 0.86);
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
}

.app-section-nav__item:hover {
  color: hsl(var(--foreground));
}

.app-section-nav__item:focus-visible {
  color: hsl(var(--foreground));
  outline: 2px solid hsl(var(--ring));
  outline-offset: 0.2rem;
}

.app-section-nav__item.is-active {
  color: hsl(var(--foreground));
  font-weight: 620;
}

.app-section-nav__item.is-active::after {
  position: absolute;
  right: 0;
  bottom: -0.4375rem;
  left: 0;
  height: 2px;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.72);
  content: '';
}

.app-section-nav__badge {
  min-width: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.76);
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
    margin-inline-start: calc(var(--space-4) * -1);
  }
}
</style>
