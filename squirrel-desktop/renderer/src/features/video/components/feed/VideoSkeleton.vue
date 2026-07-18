<template>
  <div
    :class="[
      layout === 'list' ? 'flex flex-row gap-4' : 'flex flex-col gap-3',
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
      :style="{ borderRadius: 'var(--radius-xl)' }"
    >
      <AppSkeleton
        width="100%"
        height="100%"
        rounded="var(--radius-xl)"
        shimmer
      />
    </div>
    <div
      :class="[
        layout === 'list'
          ? 'flex flex-1 flex-col justify-center py-1'
          : 'flex gap-3 px-1',
      ]"
    >
      <AppSkeleton
        v-if="layout === 'grid'"
        width="2.25rem"
        height="2.25rem"
        rounded="var(--radius-md)"
      />
      <div class="flex-1 space-y-2">
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
