<template>
  <article class="history-item-skeleton" aria-hidden="true">
    <div class="history-item-skeleton__inner">
      <div class="history-item-skeleton__thumb">
        <AppSkeleton width="100%" height="100%" rounded="var(--radius-md)" shimmer />
      </div>

      <div class="history-item-skeleton__body">
        <AppSkeleton width="78%" height="1.125rem" rounded="var(--radius-sm)" shimmer />

        <div class="history-item-skeleton__source">
          <AppSkeleton width="1rem" height="1rem" rounded="50%" shimmer />
          <AppSkeleton width="6.5rem" height="0.75rem" rounded="var(--radius-sm)" shimmer />
          <AppSkeleton width="2.5rem" height="1rem" rounded="var(--radius-sm)" shimmer />
        </div>

        <div class="history-item-skeleton__meta">
          <AppSkeleton width="2.75rem" height="0.75rem" rounded="var(--radius-sm)" shimmer />
          <AppSkeleton width="5rem" height="0.75rem" rounded="var(--radius-sm)" shimmer />
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
</script>

<style scoped>
.history-item-skeleton {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) 2rem;
  column-gap: var(--space-2);
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  padding-inline: 0.75rem;
}

.history-item-skeleton__inner {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: 11.5rem minmax(0, 1fr);
  gap: var(--space-3);
  padding: 0.75rem 0;
}

.history-item-skeleton__thumb {
  min-width: 0;
  aspect-ratio: 16 / 9;
}

.history-item-skeleton__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0.5rem;
}

.history-item-skeleton__source,
.history-item-skeleton__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
}
</style>
