<!-- DESIGN.md § filter-popover — compact segmented track (exclusive choice).
     Dual-theme: track/raised tokens. role=group (honest; not full APG radiogroup). -->
<template>
  <div
    class="app-filter-chips"
    role="group"
    :aria-label="label"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="app-filter-chip"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
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
  min-height: 1.75rem;
  padding: 2px;
  border-radius: var(--radius-md);
  background: var(--app-filter-track-bg);
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
  padding: 0 0.25rem;
  color: hsl(var(--muted-foreground));
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

/* Raised segment — same dual-theme family as AppSegmentedControl. */
.app-filter-chip.is-active {
  background: var(--app-filter-raised-bg);
  color: var(--app-filter-raised-fg);
  font-weight: 650;
  box-shadow: var(--app-filter-raised-shadow);
}

.app-filter-chip:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.4);
}

.app-filter-chip.is-active:focus-visible {
  box-shadow:
    var(--app-filter-raised-shadow),
    0 0 0 2px hsl(var(--ring) / 0.4);
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-chip {
    transition: none;
  }
}
</style>
