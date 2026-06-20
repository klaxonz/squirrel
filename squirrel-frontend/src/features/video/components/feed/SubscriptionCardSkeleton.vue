<template>
  <div class="space-y-3 rounded-lg border border-border/50 bg-background p-3">
    <div class="flex items-start gap-3">
      <AppSkeleton width="2.75rem" height="2.75rem" rounded="var(--radius-md)" shimmer />
      <div class="flex-1 space-y-2 py-0.5">
        <AppSkeleton width="66%" height="1rem" rounded="var(--radius-md)" shimmer />
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
    <div class="border-t border-border/50 pt-2">
      <AppSkeleton width="5rem" height="0.75rem" rounded="var(--radius)" shimmer />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
</script>
