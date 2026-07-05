<template>
  <div class="music-section">
    <header v-if="title" class="music-section-header">
      <h2 class="music-section-title">{{ title }}</h2>
      <Button v-if="moreAction" variant="ghost" size="sm" class="-mr-3" @click="$emit('more')">
        更多 <AppIcon name="chevronRight" class="h-4 w-4" />
      </Button>
    </header>
    <div class="music-section-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

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

.music-section-content {
  min-height: 0;
}
</style>
