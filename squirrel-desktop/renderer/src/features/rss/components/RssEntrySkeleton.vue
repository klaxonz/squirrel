<template>
  <div class="rss-entry-skeleton" aria-hidden="true">
    <div class="rss-entry-skeleton__meta">
      <div class="rss-entry-skeleton__source">
        <AppSkeleton width="1rem" height="1rem" rounded="var(--radius-sm)" shimmer />
        <AppSkeleton width="6.5rem" height="0.625rem" rounded="var(--radius-sm)" shimmer />
      </div>
      <AppSkeleton width="2.75rem" height="0.625rem" rounded="var(--radius-sm)" shimmer />
    </div>

    <div class="rss-entry-skeleton__title">
      <AppSkeleton width="92%" height="0.875rem" rounded="var(--radius-sm)" shimmer />
      <AppSkeleton width="68%" height="0.875rem" rounded="var(--radius-sm)" shimmer />
    </div>

    <div class="rss-entry-skeleton__summary">
      <AppSkeleton width="100%" height="0.6875rem" rounded="var(--radius-sm)" shimmer />
      <AppSkeleton width="82%" height="0.6875rem" rounded="var(--radius-sm)" shimmer />
    </div>

    <AppSkeleton width="7.5rem" height="0.625rem" rounded="var(--radius-sm)" shimmer />
  </div>
</template>

<script setup lang="ts">
import { Skeleton as AppSkeleton } from '@/shared/ui/skeleton'
</script>

<style scoped>
.rss-entry-skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.2);
}

.rss-entry-skeleton__meta,
.rss-entry-skeleton__source {
  display: flex;
  align-items: center;
}

.rss-entry-skeleton__meta {
  justify-content: space-between;
  gap: 0.75rem;
}

.rss-entry-skeleton__source {
  gap: 0.375rem;
}

.rss-entry-skeleton__title,
.rss-entry-skeleton__summary {
  display: flex;
  flex-direction: column;
}

.rss-entry-skeleton__title {
  gap: 0.375rem;
}

.rss-entry-skeleton__summary {
  gap: 0.3125rem;
}
</style>
