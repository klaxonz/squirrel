<template>
  <div class="app-surface app-surface--subtle space-y-2.5 p-3">
    <div class="flex items-start gap-2.5">
      <AppSkeleton width="2.25rem" height="2.25rem" rounded="var(--radius-md)" shimmer />
      <div class="flex-1 space-y-2 py-0.5">
        <AppSkeleton width="66%" height="0.875rem" rounded="var(--radius-md)" shimmer />
        <div class="flex gap-2">
          <AppSkeleton width="3.5rem" height="0.75rem" rounded="var(--radius)" shimmer />
          <AppSkeleton width="4rem" height="0.75rem" rounded="var(--radius)" shimmer />
        </div>
      </div>
    </div>
    <div class="grid grid-cols-3 gap-1.5">
      <div
        v-for="i in 3"
        :key="i"
        class="relative aspect-video overflow-hidden rounded-md bg-[var(--app-skeleton-base)]"
      >
        <span class="app-shimmer" />
      </div>
    </div>
    <div class="app-divider-top pt-2">
      <AppSkeleton width="5rem" height="0.75rem" rounded="var(--radius)" shimmer />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
</script>
