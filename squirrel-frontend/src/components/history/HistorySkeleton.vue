<template>
  <div class="history-skeleton-item" :style="{ animationDelay: `${delay}ms` }">
    <!-- Thumbnail Skeleton -->
    <div class="skeleton-thumb">
      <div class="shimmer"></div>
    </div>

    <!-- Info Skeleton -->
    <div class="skeleton-info">
      <div class="skeleton-line skeleton-title-full"></div>
      <div class="skeleton-line skeleton-title-partial"></div>
      <div class="skeleton-meta">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-line skeleton-text-sm"></div>
        <div class="skeleton-dot"></div>
        <div class="skeleton-line skeleton-text-xs"></div>
      </div>
    </div>

    <!-- Action Skeleton -->
    <div class="skeleton-action"></div>
  </div>
</template>

<script setup>
defineProps({
  delay: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.history-skeleton-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  position: relative;
  overflow: hidden;
  animation: skeleton-appear 0.4s ease-out forwards;
  opacity: 0;
}

@keyframes skeleton-appear {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Thumbnail */
.skeleton-thumb {
  width: 11rem;
  aspect-ratio: 16 / 9;
  background: hsl(var(--secondary) / 0.25);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.3);
}

@media (max-width: 640px) {
  .skeleton-thumb {
    width: 8rem;
  }
}

/* Info */
.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skeleton-line {
  height: 0.8rem;
  background: hsl(var(--secondary) / 0.2);
  border-radius: 2px;
}

.skeleton-title-full {
  width: 75%;
}

.skeleton-title-partial {
  width: 50%;
}

.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.skeleton-avatar {
  width: 1rem;
  height: 1rem;
  background: hsl(var(--secondary) / 0.2);
  border-radius: 2px;
}

.skeleton-text-sm {
  width: 4rem;
  height: 0.65rem;
}

.skeleton-text-xs {
  width: 3rem;
  height: 0.6rem;
}

.skeleton-dot {
  width: 3px;
  height: 3px;
  background: hsl(var(--border) / 0.5);
  border-radius: 50%;
}

/* Action */
.skeleton-action {
  width: 1.75rem;
  height: 1.75rem;
  background: hsl(var(--secondary) / 0.15);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  opacity: 0.5;
}

/* Shimmer */
.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--primary) / 0.03),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Responsive */
@media (max-width: 640px) {
  .history-skeleton-item {
    gap: 0.75rem;
    padding: 0.5rem;
  }

  .skeleton-action {
    display: none;
  }
}
</style>
