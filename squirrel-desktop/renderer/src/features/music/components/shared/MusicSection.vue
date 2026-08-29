<template>
  <section class="music-section">
    <header v-if="title" class="music-section-header">
      <div class="music-section-heading">
        <h2 class="music-section-title">{{ title }}</h2>
        <p v-if="description" class="music-section-description">{{ description }}</p>
      </div>
      <Button v-if="moreAction" text variant="secondary" size="sm" @click="$emit('more')">
        查看全部
        <AppIcon name="chevronRight" class="h-3.5 w-3.5" />
      </Button>
    </header>
    <div class="music-section-content">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

defineProps<{
  title?: string
  description?: string
  moreAction?: boolean
}>()

defineEmits<{
  more: []
}>()
</script>

<style scoped>
.music-section {
  margin-bottom: var(--space-7);
}

.music-section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.music-section-heading {
  min-width: 0;
}

.music-section-title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  letter-spacing: 0;
  line-height: var(--app-h3-leading);
}

.music-section-description {
  margin: 0.2rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.35;
}

.music-section-content {
  min-height: 0;
}
</style>
