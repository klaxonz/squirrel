<template>
  <div
    class="app-segmented-control"
    :class="[`app-segmented-control--${size}`]"
    role="group"
    :aria-label="ariaLabel"
  >
    <Button
      v-for="option in options"
      :key="option.value"
      text severity="secondary"
      :size="buttonSize"
      :icon-only="size === 'icon'"
      type="button"
      class="app-segmented-control__item"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      :title="option.label"
      :aria-label="option.label"
      @click="selectOption(option.value)"
    >
      <slot name="option" :option="option">
        {{ option.label }}
      </slot>
    </Button>
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'

export interface AppSegmentedControlOption {
  value: string | number
  label: string
  icon?: AppIconName
}

const props = withDefaults(defineProps<{
  modelValue: string | number
  options: readonly AppSegmentedControlOption[]
  ariaLabel?: string
  size?: 'default' | 'sm' | 'icon'
}>(), {
  ariaLabel: '',
  size: 'default',
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
}>()

defineSlots<{
  option?: (props: { option: AppSegmentedControlOption }) => unknown
}>()

const buttonSize = 'sm'

const selectOption = (value: string | number) => {
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.app-segmented-control {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex: 0 0 auto;
  background: var(--app-filter-track-bg);
  border-radius: var(--radius-md);
  padding: 2px;
}

.app-segmented-control__item {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.app-segmented-control__item:hover {
  color: hsl(var(--foreground));
}

.app-segmented-control__item.is-active {
  color: var(--app-filter-raised-fg);
  background: var(--app-filter-raised-bg);
  box-shadow: var(--app-filter-raised-shadow);
}

@media (prefers-reduced-motion: reduce) {
  .app-segmented-control__item {
    transition: none;
  }
}

.app-segmented-control--sm .app-segmented-control__item {
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  height: auto;
}

.app-segmented-control--icon {
  border: 1px solid hsl(var(--border) / 0.58);
  background: hsl(var(--background) / 0.36);
}

.app-segmented-control--icon .app-segmented-control__item {
  width: 1.625rem;
  height: 1.625rem;
  padding: 0;
}
</style>
