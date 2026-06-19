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
/**
 * Two-column app shell: fixed sidebar + scrollable main with a sticky header.
 * Collapses the duplicated `<aside w-72 border-r> + <header h-14 border-b>`
 * markup that ScheduledTasks / Settings / SiteRuntimeManager each hand-rolled.
 * Sidebar is hidden below `lg`; the mobile nav (if any) is left to the caller
 * since each page wires it differently.
 */
withDefaults(defineProps<{
  sidebarWidth?: string
}>(), {
  sidebarWidth: '18rem',
})
</script>

<style scoped>
.app-two-column {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
}

.app-two-column__sidebar {
  display: none;
  flex-direction: column;
  flex: none;
  width: v-bind(sidebarWidth);
  border-right: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--background));
}

.app-two-column__main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  background: hsl(var(--background));
}

.app-two-column__header {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  height: 3.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
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
