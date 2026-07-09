<template>
  <div class="subscription-card-skeleton">
    <div class="subscription-card-skeleton__media">
      <div v-for="i in 3" :key="i" class="subscription-card-skeleton__thumb">
        <span class="app-shimmer" />
      </div>
    </div>
    <div class="subscription-card-skeleton__body">
      <div class="subscription-card-skeleton__identity">
        <AppSkeleton width="1.75rem" height="1.75rem" rounded="999px" shimmer />
        <div class="subscription-card-skeleton__copy">
          <AppSkeleton width="72%" height="0.875rem" rounded="var(--radius-md)" shimmer />
          <AppSkeleton width="48%" height="0.7rem" rounded="var(--radius-sm)" shimmer />
        </div>
      </div>
      <AppSkeleton width="5rem" height="0.65rem" rounded="var(--radius-sm)" shimmer />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
</script>

<style scoped>
.subscription-card-skeleton {
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-card-radius);
  background: hsl(var(--card));
}

.subscription-card-skeleton__media {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  background: hsl(0 0% 0% / 0.45);
}

.subscription-card-skeleton__thumb {
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  background: var(--app-skeleton-base);
}

.subscription-card-skeleton__body {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.75rem 0.875rem;
}

.subscription-card-skeleton__identity {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
}

.subscription-card-skeleton__copy {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.4rem;
  padding-top: 0.15rem;
}
</style>
