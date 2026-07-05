<template>
  <div class="app-floating-list" :class="props.class">
    <div class="app-floating-list__body custom-scrollbar" :style="{ maxHeight }">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

const props = withDefaults(defineProps<{
  maxHeight?: string
  class?: HTMLAttributes['class']
}>(), {
  maxHeight: '17.5rem',
})
</script>

<style scoped>
.app-floating-list {
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  z-index: var(--z-dropdown);
  margin-top: 0.375rem;
  padding: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-lg);
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
  box-shadow: var(--app-floating-shadow);
}

.app-floating-list__body {
  overflow-y: auto;
  padding-right: 0.25rem;
}
</style>
