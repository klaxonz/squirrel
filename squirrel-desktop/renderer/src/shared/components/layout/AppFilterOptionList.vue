<!-- Exclusive source picker for filter panels. A compact grid keeps source
     identity scannable without making the popover look like a navigation menu. -->
<template>
  <div
    class="app-filter-option-list"
    role="radiogroup"
    :aria-label="label"
  >
    <button
      v-for="(option, index) in options"
      :key="option.value"
      type="button"
      class="app-filter-option"
      :class="{ 'is-active': modelValue === option.value }"
      role="radio"
      :aria-checked="modelValue === option.value"
      :tabindex="optionTabIndex(option, index)"
      :title="option.label"
      @click="emit('update:modelValue', option.value)"
      @keydown="handleKeydown($event, index)"
    >
      <span class="app-filter-option__icon" aria-hidden="true">
        <slot name="leading" :option="option" />
      </span>
      <span class="app-filter-option__label">{{ option.label }}</span>
      <span
        v-if="modelValue === option.value"
        class="app-filter-option__check"
        aria-hidden="true"
      >
        <AppIcon name="check" :stroke-width="2.5" />
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

export type AppFilterListOption = {
  value: string
  label: string
  iconUrl?: string | null
}

const props = defineProps<{
  modelValue: string
  options: AppFilterListOption[]
  label: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const optionTabIndex = (option: AppFilterListOption, index: number) => {
  const hasSelectedOption = props.options.some((item) => item.value === props.modelValue)
  return option.value === props.modelValue || (!hasSelectedOption && index === 0) ? 0 : -1
}

const handleKeydown = (event: KeyboardEvent, index: number) => {
  if (props.options.length === 0) return

  let nextIndex: number | null = null
  if (event.key === 'Home') nextIndex = 0
  if (event.key === 'End') nextIndex = props.options.length - 1
  if (event.key === 'ArrowRight') {
    nextIndex = (index + 1) % props.options.length
  }
  if (event.key === 'ArrowLeft') {
    nextIndex = (index - 1 + props.options.length) % props.options.length
  }
  if (event.key === 'ArrowDown') nextIndex = (index + 2) % props.options.length
  if (event.key === 'ArrowUp') {
    nextIndex = (index - 2 + props.options.length) % props.options.length
  }
  if (nextIndex == null) return

  event.preventDefault()
  const nextOption = props.options[nextIndex]
  if (!nextOption) return

  emit('update:modelValue', nextOption.value)
  const group = (event.currentTarget as HTMLButtonElement).closest('.app-filter-option-list')
  group?.querySelectorAll<HTMLButtonElement>('.app-filter-option')[nextIndex]?.focus()
}
</script>

<style scoped>
.app-filter-option-list {
  display: grid;
  max-height: 13.5rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.375rem;
  overflow-y: auto;
  padding: 0.0625rem;
}

.app-filter-option {
  display: grid;
  min-width: 0;
  min-height: 2.375rem;
  grid-template-columns: 1.375rem minmax(0, 1fr) 0.875rem;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.24);
  padding: 0.25rem 0.5rem;
  color: hsl(var(--foreground) / 0.78);
  text-align: left;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.app-filter-option:hover {
  border-color: hsl(var(--border) / 0.72);
  background: hsl(var(--muted) / 0.48);
  color: hsl(var(--foreground));
}

.app-filter-option.is-active {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
}

.app-filter-option.is-active:hover {
  border-color: var(--app-selection-border-hover);
  background: var(--app-selection-bg-hover);
}

.app-filter-option:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.42);
}

.app-filter-option__icon {
  display: inline-flex;
  width: 1.375rem;
  height: 1.375rem;
  align-items: center;
  justify-content: center;
}

.app-filter-option__icon :deep(.site-icon),
.app-filter-option__icon :deep(.app-filter-all-icon) {
  width: 1.375rem;
  height: 1.375rem;
}

.app-filter-option__icon :deep(.app-filter-all-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border) / 0.48);
  border-radius: var(--radius-sm);
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--muted-foreground) / 0.82);
}

.app-filter-option__icon :deep(.app-filter-all-icon svg) {
  width: 0.75rem;
  height: 0.75rem;
}

.app-filter-option.is-active .app-filter-option__icon :deep(.app-filter-all-icon) {
  color: hsl(var(--foreground));
}

.app-filter-option__label {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-filter-option__check {
  display: inline-flex;
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  color: hsl(var(--foreground));
}

.app-filter-option__check :deep(svg) {
  width: 0.75rem;
  height: 0.75rem;
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-option {
    transition: none;
  }
}
</style>
