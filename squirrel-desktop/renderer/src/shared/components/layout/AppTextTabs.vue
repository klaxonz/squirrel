<template>
  <nav class="app-text-tabs" :aria-label="ariaLabel">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="app-text-tabs__item"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      @click="selectOption(option.value)"
    >
      <span>{{ option.label }}</span>
      <span
        v-if="option.badge !== null && option.badge !== undefined && option.badge !== ''"
        class="app-text-tabs__badge app-mono"
      >{{ option.badge }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
export interface AppTextTabsOption {
  value: string | number
  label: string
  badge?: string | number | null
}

const props = withDefaults(defineProps<{
  modelValue: string | number
  options: readonly AppTextTabsOption[]
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
.app-text-tabs {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.875rem;
}

.app-text-tabs__item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 0;
  padding: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font: inherit;
  font-size: var(--app-text-sm);
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
}

.app-text-tabs__item:hover,
.app-text-tabs__item.is-active {
  color: hsl(var(--foreground) / 0.82);
}

.app-text-tabs__item.is-active {
  font-weight: 600;
}

.app-text-tabs__badge {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-2xs);
  line-height: 1;
}
</style>
