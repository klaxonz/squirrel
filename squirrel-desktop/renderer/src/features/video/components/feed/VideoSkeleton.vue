<template>
  <div
    :class="[
      layout === 'list' ? 'flex flex-row gap-4' : 'flex flex-col gap-2',
      'video-skeleton',
      `video-skeleton--${appearance}`,
    ]"
    :style="{ animationDelay: `${delay}ms` }"
  >
    <div
      :class="[
        layout === 'list'
          ? 'relative aspect-video w-48 shrink-0 overflow-hidden md:w-64'
          : 'relative aspect-video overflow-hidden',
      ]"
      :style="{ borderRadius: appearance === 'workbench' ? 'var(--radius-md)' : 'var(--app-card-radius)' }"
    >
      <AppSkeleton
        width="100%"
        height="100%"
        :rounded="appearance === 'workbench' ? 'var(--radius-md)' : 'var(--app-card-radius)'"
        shimmer
      />
    </div>
    <div
      :class="[
        layout === 'list'
          ? 'flex flex-1 flex-col justify-center py-1'
          : 'video-skeleton__grid-body',
      ]"
    >
      <template v-if="layout === 'grid'">
        <div class="video-skeleton__title">
          <AppSkeleton height="0.875rem" width="100%" />
          <AppSkeleton height="0.875rem" width="72%" />
        </div>
        <div class="video-skeleton__meta">
          <AppSkeleton
            width="1.75rem"
            height="1.75rem"
            rounded="999px"
          />
          <AppSkeleton height="0.75rem" width="44%" />
          <AppSkeleton height="0.75rem" width="18%" />
        </div>
      </template>
      <div v-else class="flex-1 space-y-2">
        <AppSkeleton height="1rem" width="100%" />
        <AppSkeleton height="0.75rem" width="66%" />
        <div class="flex gap-2 pt-1">
          <AppSkeleton height="0.75rem" width="4rem" />
          <AppSkeleton height="0.75rem" width="3rem" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSkeleton from '@/shared/components/AppSkeleton.vue'

withDefaults(defineProps<{
  delay?: number
  layout?: 'grid' | 'list'
  appearance?: 'default' | 'workbench'
}>(), {
  appearance: 'default',
})
</script>

<style scoped>
.video-skeleton {
  animation: video-skeleton-pulse 1.6s var(--ease-default) infinite;
}

.video-skeleton__grid-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 0.125rem 0.25rem;
}

.video-skeleton__title {
  display: flex;
  min-height: calc(2 * 0.875rem * 1.35);
  flex-direction: column;
  justify-content: space-between;
}

.video-skeleton__meta {
  display: flex;
  min-height: 1.75rem;
  align-items: center;
  gap: 0.5rem;
}

@keyframes video-skeleton-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.62;
  }
}

@media (prefers-reduced-motion: reduce) {
  .video-skeleton {
    animation: none;
  }
}
</style>
