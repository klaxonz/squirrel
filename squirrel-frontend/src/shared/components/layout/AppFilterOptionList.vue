<!-- DESIGN.md §9.1 — source tiles (icon grid). Selected = ring, no row wash. -->
<template>
  <div
    class="app-filter-sites"
    role="listbox"
    :aria-label="label"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="option"
      class="app-filter-site"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-selected="modelValue === option.value"
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

const props = defineProps<{
  modelValue: string
  options: AppFilterListOption[]
  label: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const shortLabel = (option: AppFilterListOption) => {
  if (option.shortLabel) return option.shortLabel
  // Keep tiles readable: strip common prefixes / long brand tails.
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

.app-filter-site {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 3.625rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.3125rem;
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.28);
  padding: 0.4375rem 0.25rem 0.375rem;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.app-filter-site:hover {
  border-color: hsl(var(--border) / 0.85);
  background: hsl(var(--muted) / 0.45);
  color: hsl(var(--foreground));
}

.app-filter-site.is-active {
  border-color: hsl(var(--foreground) / 0.22);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  box-shadow:
    0 1px 2px hsl(var(--foreground) / 0.06),
    0 0 0 1px hsl(var(--foreground) / 0.06);
}

.app-filter-site:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.4);
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
  padding: 0 0.125rem;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.15;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-filter-site.is-active .app-filter-site__label {
  color: hsl(var(--foreground));
}

.app-filter-site__check {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  display: grid;
  width: 0.875rem;
  height: 0.875rem;
  place-items: center;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.88);
  color: hsl(var(--background));
}

.app-filter-site__check :deep(svg) {
  width: 0.5625rem;
  height: 0.5625rem;
}
</style>
