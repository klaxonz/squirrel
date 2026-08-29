<template>
  <div class="subscription-row-skeleton">
    <div class="subscription-row-skeleton__identity">
      <AppSkeleton width="1.75rem" height="1.75rem" rounded="999px" shimmer />
      <div class="subscription-row-skeleton__copy">
        <AppSkeleton width="10rem" height="0.75rem" rounded="var(--radius-sm)" shimmer />
        <AppSkeleton width="4rem" height="0.625rem" rounded="var(--radius-sm)" shimmer />
      </div>
    </div>
    <AppSkeleton width="3rem" height="0.6875rem" rounded="var(--radius-sm)" shimmer />
    <AppSkeleton width="2.5rem" height="0.6875rem" rounded="var(--radius-sm)" shimmer />
    <AppSkeleton width="5rem" height="0.6875rem" rounded="var(--radius-sm)" shimmer />
    <AppSkeleton width="4rem" height="0.6875rem" rounded="var(--radius-sm)" shimmer />
    <AppSkeleton width="1.625rem" height="1.625rem" rounded="var(--radius-md)" shimmer />
  </div>
</template>

<script setup lang="ts">
import { Skeleton as AppSkeleton } from '@/shared/ui/skeleton'
</script>

<style scoped>
.subscription-row-skeleton {
  display: grid;
  min-height: 4rem;
  grid-template-columns: var(
    --subscription-table-columns,
    minmax(15rem, 1fr) 5.5rem 5.5rem 8rem minmax(6.5rem, 8rem) 1.75rem
  );
  align-items: center;
  gap: 1rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.625rem 0.75rem;
}

.subscription-row-skeleton__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.75rem;
}

.subscription-row-skeleton__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.35rem;
}
</style>
