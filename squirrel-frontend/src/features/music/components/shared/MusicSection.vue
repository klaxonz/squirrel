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
  margin-bottom: var(--space-6);
}

.music-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--app-hairline);
}

.music-section-title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  letter-spacing: var(--app-h3-tracking);
  line-height: var(--app-h3-leading);
}

.music-section-content {
  min-height: 0;
}
</style>
