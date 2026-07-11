<!-- DESIGN.md §9.1 — compact segmented track. -->
<template>
  <div
    class="app-filter-chips"
    role="radiogroup"
    :aria-label="label"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      class="app-filter-chip"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-checked="modelValue === option.value"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
export type AppFilterChipOption = {
  value: string
  label: string
}

defineProps<{
  modelValue: string
  options: AppFilterChipOption[]
  label: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<style scoped>
.app-filter-chips {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 0;
  padding: 2px;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.7);
}

.app-filter-chip {
  display: inline-flex;
  min-height: 1.5rem;
  min-width: 0;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: calc(var(--radius-md) - 2px);
  background: transparent;
  padding: 0 0.2rem;
  color: hsl(var(--muted-foreground) / 0.9);
  font-size: 0.6875rem;
  font-weight: 550;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.app-filter-chip:hover {
  color: hsl(var(--foreground));
}

.app-filter-chip.is-active {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-weight: 650;
  box-shadow: 0 1px 1px hsl(var(--foreground) / 0.06);
}

.app-filter-chip:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.35);
}
</style>
