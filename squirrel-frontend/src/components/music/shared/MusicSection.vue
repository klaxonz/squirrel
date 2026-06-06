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
import AppIcon from '@/components/common/AppIcon.vue'

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
  margin-bottom: 1.75rem;
}

.music-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.875rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.25);
}

.music-section-title {
  font-size: 1rem;
  font-weight: 800;
  color: hsl(var(--foreground));
  letter-spacing: -0.02em;
  position: relative;
  padding-left: 0.75rem;
}

.music-section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 70%;
  background: hsl(var(--primary));
  border-radius: 2px;
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
  transition: all 0.2s ease;
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
</style>
