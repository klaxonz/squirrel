<template>
  <div class="app-list-empty" :class="props.class">
    <slot />
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<style scoped>
.app-list-empty {
  padding: 1rem 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  text-align: center;
}
</style>
