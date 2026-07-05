<template>
  <div class="app-two-column">
    <aside v-if="$slots.sidebar" class="app-two-column__sidebar">
      <slot name="sidebar" />
    </aside>
    <main class="app-two-column__main">
      <header v-if="$slots.header" class="app-two-column__header">
        <slot name="header" />
      </header>
      <div class="app-two-column__content">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  sidebarWidth?: string
}>(), {
  sidebarWidth: '17.5rem',
})
</script>

<style scoped>
.app-two-column {
  display: flex;
  height: 100%;
  overflow: hidden;
  background:
    linear-gradient(180deg, hsl(var(--muted) / 0.12), transparent 12rem),
    hsl(var(--background));
  color: hsl(var(--foreground));
}

.app-two-column__sidebar {
  display: none;
  flex-direction: column;
  flex: none;
  width: v-bind(sidebarWidth);
  border-right: 1px solid hsl(var(--border) / 0.58);
  background: hsl(var(--card) / 0.42);
}

.app-two-column__main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  background: transparent;
}

.app-two-column__header {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 4.25rem;
  border-bottom: 1px solid hsl(var(--border) / 0.48);
  background: hsl(var(--background) / 0.72);
  padding-inline: 1rem;
}

.app-two-column__content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

@media (min-width: 1024px) {
  .app-two-column__sidebar {
    display: flex;
  }

  .app-two-column__header {
    padding-inline: 1.5rem;
  }
}
</style>
