<template>
  <div v-if="loading" class="music-loading-state">
    <AppIcon name="loadingSpinner" class="h-5 w-5 animate-spin" />
    <span>{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

withDefaults(defineProps<{
  loading: boolean
  text?: string
}>(), {
  text: '加载中...',
})
</script>

<style scoped>
.music-loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  padding: 3rem 1rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  font-weight: 500;
}
</style>