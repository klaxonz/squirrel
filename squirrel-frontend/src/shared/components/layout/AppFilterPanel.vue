<!-- DESIGN.md §9.1 — compact filter menu. -->
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
  description?: string
  activeCount?: number
}>(), {
  title: '筛选',
  description: '',
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
  min-height: 2.125rem;
  padding: 0.4rem 0.75rem 0.25rem;
}

.app-filter-panel__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
}

.app-filter-panel__title {
  color: hsl(var(--foreground) / 0.5);
  font-size: 0.6875rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.app-filter-panel__count {
  display: inline-grid;
  min-width: 1rem;
  height: 1rem;
  place-items: center;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground) / 0.7);
  font-size: 0.5625rem;
  font-weight: 700;
  line-height: 1;
}

.app-filter-panel__reset {
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  padding: 0.15rem 0.3rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 550;
  cursor: pointer;
}

.app-filter-panel__reset:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--muted) / 0.65);
}

.app-filter-panel__body {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.125rem 0.625rem 0.625rem;
}
</style>
