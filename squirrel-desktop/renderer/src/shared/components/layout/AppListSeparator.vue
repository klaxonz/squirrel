<template>
  <div class="app-list-separator" :class="props.class" />
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<style scoped>
.app-list-separator {
  height: 1px;
  margin: 0.25rem 0;
  background: hsl(var(--border) / 0.45);
}
</style>
