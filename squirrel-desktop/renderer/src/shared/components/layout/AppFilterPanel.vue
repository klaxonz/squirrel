<!-- Compact filter popover panel. -->
<template>
  <div class="app-filter-panel">
    <header class="app-filter-panel__header">
      <div class="app-filter-panel__title-row">
        <strong class="app-filter-panel__title">{{ title }}</strong>
        <span
          v-if="activeCount > 0"
          class="app-filter-panel__status"
          :aria-label="`已启用 ${activeCount} 项`"
        >
          已启用 {{ activeCount }} 项
        </span>
      </div>
      <button
        v-if="activeCount > 0"
        type="button"
        class="app-filter-panel__reset"
        @click="$emit('reset')"
      >
        清除
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
  max-height: inherit;
  flex-direction: column;
  min-width: 0;
}

.app-filter-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 2.875rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.625rem 0.875rem;
}

.app-filter-panel__title-row {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 0.5rem;
}

.app-filter-panel__title {
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 650;
  letter-spacing: -0.01em;
  line-height: 1.25;
}

.app-filter-panel__status {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: var(--app-text-badge-size);
  font-weight: 550;
  line-height: 1.25;
}

.app-filter-panel__reset {
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  padding: 0.25rem 0.375rem;
  color: hsl(var(--muted-foreground) / 0.82);
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
  min-height: 0;
  gap: 0.25rem;
  overflow-y: auto;
  padding: 0.625rem 0.75rem 0.75rem;
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-panel__reset {
    transition: none;
  }
}
</style>
