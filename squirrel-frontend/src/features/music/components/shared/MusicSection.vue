<template>
  <div class="music-section">
    <header v-if="title" class="music-section-header">
      <h2 class="music-section-title">{{ title }}</h2>
      <button v-if="moreAction" class="music-section-more" @click="$emit('more')">
        更多 <AppIcon name="chevronRight" class="h-4 w-4" />
      </button>
    </header>
    <div class="music-section-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

defineProps<{
  title?: string
  moreAction?: boolean
}>()

defineEmits<{
  more: []
}>()
</script>

<style scoped>
.music-section {
  margin-bottom: 1.875rem;
}

.music-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.875rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid hsl(var(--border) / 0.35);
}

.music-section-title {
  font-family: var(--app-heading-font);
  font-size: 1.0625rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  letter-spacing: -0.01em;
}

.music-section-more {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  padding: 0.375rem 0.75rem;
  margin: -0.375rem -0.75rem;
  border-radius: 0.5rem;
}

.music-section-more:hover {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.06);
}

.music-section-content {
  min-height: 0;
}

@media (prefers-reduced-motion: reduce) {
  .music-section-more {
    transition: none;
  }
}
</style>
