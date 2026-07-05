<template>
  <div class="app-sidebar-header" :class="props.class">
    <div class="app-sidebar-header__copy">
      <h1 class="app-h3 truncate">{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="app-sidebar-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  title: string
  subtitle?: string
  class?: HTMLAttributes['class']
}>()
</script>

<style scoped>
.app-sidebar-header {
  display: flex;
  min-height: var(--app-workbench-header-height, 3.5rem);
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--background) / 0.52);
  padding-inline: var(--space-4);
}

.app-sidebar-header__copy {
  min-width: 0;
}

.app-sidebar-header__copy p {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.25;
}

.app-sidebar-header__actions {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
}
</style>
