<template>
  <header
    class="music-detail-header"
    :class="{ 'music-detail-header--circle': coverShape === 'circle' }"
  >
    <div class="music-detail-cover">
      <img v-if="cover" :src="cover" :alt="title" loading="lazy" />
      <div v-else class="music-detail-cover__fallback">
        <AppIcon :name="fallbackIcon" class="h-10 w-10" />
      </div>
    </div>

    <div class="music-detail-info">
      <span class="music-detail-kicker">{{ kicker }}</span>
      <h1 class="music-detail-title">{{ title }}</h1>

      <div v-if="$slots.meta" class="music-detail-meta">
        <slot name="meta" />
      </div>

      <p v-if="description" class="music-detail-desc">{{ description }}</p>

      <div v-if="$slots.actions" class="music-detail-actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

withDefaults(defineProps<{
  kicker: string
  title: string
  cover?: string | null
  description?: string
  coverShape?: 'square' | 'circle'
  fallbackIcon?: AppIconName
}>(), {
  cover: null,
  description: '',
  coverShape: 'square',
  fallbackIcon: 'playlistMusic',
})
</script>

<style scoped>
.music-detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--app-hairline);
}

.music-detail-cover {
  width: 7.5rem;
  height: 7.5rem;
  flex: none;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--muted) / 0.45);
}

.music-detail-header--circle .music-detail-cover {
  border-radius: 9999px;
}

.music-detail-cover img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-detail-cover__fallback {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.music-detail-info {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.375rem;
}

.music-detail-kicker {
  color: var(--app-heading-color-muted);
  font-size: var(--app-text-sm);
  font-weight: 650;
  line-height: 1.25;
  letter-spacing: 0;
}

.music-detail-title {
  margin: 0;
  color: var(--app-heading-color);
  font-family: var(--app-heading-font);
  font-size: var(--app-h2-size);
  font-weight: var(--app-h2-weight);
  letter-spacing: var(--app-h2-tracking);
  line-height: var(--app-h2-leading);
  text-wrap: balance;
}

.music-detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.625rem 0.875rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  font-weight: 500;
}

.music-detail-desc {
  margin: 0.25rem 0 0;
  max-width: 42rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-wrap: pretty;
}

.music-detail-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.625rem;
  margin-top: 0.5rem;
}

@media (max-width: 720px) {
  .music-detail-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .music-detail-cover {
    width: 7.5rem;
    height: 7.5rem;
  }
}
</style>
