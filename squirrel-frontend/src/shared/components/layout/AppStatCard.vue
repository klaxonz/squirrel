<template>
  <div class="app-stat-card" :class="props.class">
    <div class="app-stat-card__label">{{ label }}</div>
    <div class="app-stat-card__value">{{ value }}</div>
    <p v-if="description" class="app-stat-card__description">{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  label: string
  value: string | number
  description?: string
  class?: HTMLAttributes['class']
}>()
</script>

<style scoped>
.app-stat-card__description {
  margin-top: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.25;
}
</style>
