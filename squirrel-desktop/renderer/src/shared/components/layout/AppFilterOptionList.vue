<!-- DESIGN.md § filter-popover — source tiles.
     Selected = raised card + selection border (not ink-wash mud).
     role=group (honest; not full APG listbox). Idle brand marks stay full color. -->
<template>
  <div
    class="app-filter-sites"
    role="group"
    :aria-label="label"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="app-filter-site"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      :title="option.label"
      @click="emit('update:modelValue', option.value)"
    >
      <span class="app-filter-site__icon">
        <slot name="leading" :option="option" />
      </span>
      <span class="app-filter-site__label">{{ shortLabel(option) }}</span>
      <span
        v-if="modelValue === option.value"
        class="app-filter-site__check"
        aria-hidden="true"
      >
        <AppIcon name="check" :stroke-width="3" />
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

export type AppFilterListOption = {
  value: string
  label: string
  /** Optional shorter label for tile grid. */
  shortLabel?: string
  iconUrl?: string | null
}

defineProps<{
  modelValue: string
  options: AppFilterListOption[]
  label: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const shortLabel = (option: AppFilterListOption) => {
  if (option.shortLabel) return option.shortLabel
  const label = option.label
  if (option.value === 'all') return '全部'
  if (label.length <= 8) return label
  return label.slice(0, 7)
}
</script>

<style scoped>
.app-filter-sites {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.375rem;
}

/*
  Dual-theme tile language (tokens in layout.css + .light):
  - idle: quiet field, full-color brand marks
  - active: raised card + selection edge (border only)
*/
.app-filter-site {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 3.375rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  border: 1px solid var(--app-filter-tile-idle-border);
  border-radius: var(--radius-md);
  background: var(--app-filter-tile-idle-bg);
  padding: 0.4rem 0.2rem 0.35rem;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.app-filter-site:hover {
  border-color: var(--app-selection-border);
  background: var(--app-filter-tile-hover-bg);
  color: hsl(var(--foreground));
}

.app-filter-site.is-active {
  border-color: var(--app-selection-border);
  background: var(--app-filter-raised-bg);
  color: var(--app-filter-raised-fg);
  box-shadow: var(--app-filter-tile-raised-shadow);
}

.app-filter-site.is-active:hover {
  border-color: var(--app-selection-border-hover);
  background: var(--app-filter-raised-bg);
  box-shadow: var(--app-filter-tile-raised-shadow);
}

.app-filter-site:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.4);
}

.app-filter-site.is-active:focus-visible {
  box-shadow:
    var(--app-filter-tile-raised-shadow),
    0 0 0 2px hsl(var(--ring) / 0.4);
}

.app-filter-site__icon {
  display: inline-flex;
  width: 1.5rem;
  height: 1.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
}

.app-filter-site__icon :deep(.site-icon),
.app-filter-site__icon :deep(.feed-filter-all-icon),
.app-filter-site__icon :deep(.subscription-filter-all-icon) {
  width: 1.5rem;
  height: 1.5rem;
}

.app-filter-site__label {
  max-width: 100%;
  overflow: hidden;
  padding: 0 0.1rem;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.15;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-filter-site.is-active .app-filter-site__label {
  color: var(--app-filter-raised-fg);
  font-weight: 650;
}

.app-filter-site__check {
  position: absolute;
  top: 0.2rem;
  right: 0.2rem;
  display: grid;
  width: 0.875rem;
  height: 0.875rem;
  place-items: center;
  border-radius: 999px;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
}

.app-filter-site__check :deep(svg) {
  width: 0.55rem;
  height: 0.55rem;
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-site {
    transition: none;
  }
}
</style>
