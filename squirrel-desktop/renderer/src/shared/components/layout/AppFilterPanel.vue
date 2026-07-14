<!-- DESIGN.md § filter-popover — compact filter menu (Organize 32px). -->
<template>
  <div class="app-filter-panel">
    <header class="app-filter-panel__header">
      <div class="app-filter-panel__title-row">
        <strong class="app-filter-panel__title">{{ title }}</strong>
        <span
          v-if="activeCount > 0"
          class="app-filter-panel__count app-mono"
          :aria-label="`已启用 ${activeCount} 项`"
        >
          {{ activeCount }}
        </span>
      </div>
      <button
        v-if="activeCount > 0"
        type="button"
        class="app-filter-panel__reset"
        @click="$emit('reset')"
      >
        重置
      </button>
    </header>

    <div class="app-filter-panel__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  activeCount?: number
}>(), {
  title: '筛选',
  activeCount: 0,
})

defineEmits<{
  reset: []
}>()
</script>

<style scoped>
.app-filter-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-filter-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 2rem;
  padding: 0.55rem 0.85rem 0.15rem;
}

.app-filter-panel__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
}

.app-filter-panel__title {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  line-height: 1.2;
  text-transform: uppercase;
}

.app-filter-panel__count {
  display: inline-grid;
  min-width: 1rem;
  height: 1rem;
  place-items: center;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: var(--app-selection-count-bg);
  color: var(--app-selection-count-fg);
  font-size: 0.5625rem;
  font-weight: 700;
  line-height: 1;
}

.app-filter-panel__reset {
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  padding: 0.2rem 0.375rem;
  color: hsl(var(--muted-foreground) / 0.88);
  font-size: 0.75rem;
  font-weight: 550;
  line-height: 1.2;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.app-filter-panel__reset:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--muted) / 0.65);
}

.app-filter-panel__reset:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.4);
}

.app-filter-panel__body {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  padding: 0.1rem 0.7rem 0.7rem;
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-panel__reset {
    transition: none;
  }
}
</style>
