<template>
  <article
    v-for="i in count"
    :key="i"
    class="app-video-rail-card"
    :style="{ animationDelay: `${i * 60}ms` }"
  >
    <div
      class="relative aspect-video overflow-hidden"
      :style="{ borderRadius: 'var(--app-card-radius)' }"
    >
      <AppSkeleton width="100%" height="100%" rounded="var(--app-card-radius)" shimmer />
    </div>
    <div class="mt-2 space-y-2">
      <AppSkeleton height="1rem" width="100%" />
      <AppSkeleton height="1rem" width="66%" />
    </div>
    <div class="mt-2 flex items-center gap-1.5">
      <AppSkeleton width="1rem" height="1rem" rounded="var(--radius-md)" />
      <AppSkeleton height="0.75rem" width="5rem" />
    </div>
  </article>
</template>

<script setup lang="ts">
import { Skeleton as AppSkeleton } from '@/shared/ui/skeleton'

withDefaults(defineProps<{
  count?: number
}>(), {
  count: 4,
})
</script>
