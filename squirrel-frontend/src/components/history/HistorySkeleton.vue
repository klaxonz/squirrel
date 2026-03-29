<template>
  <div class="history-skeleton-item" :style="{ animationDelay: `${delay}ms` }">
    <div class="skeleton-thumb">
      <div class="shimmer"></div>
    </div>
    
    <div class="skeleton-info">
      <div class="skeleton-title w-3/4"></div>
      <div class="skeleton-title w-1/2 mt-2"></div>
      <div class="skeleton-meta mt-3">
        <div class="skeleton-tag w-12"></div>
        <div class="skeleton-avatar"></div>
        <div class="skeleton-text w-20"></div>
        <div class="skeleton-dot"></div>
        <div class="skeleton-text w-16"></div>
      </div>
    </div>

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
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

.skeleton-thumb {
  width: 11rem;
  aspect-ratio: 16 / 9;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.skeleton-title {
  height: 0.875rem;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 2px;
}

.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.skeleton-tag {
  height: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.skeleton-avatar {
  width: 1rem;
  height: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
}

.skeleton-text {
  height: 0.6rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 2px;
}

.skeleton-dot {
  width: 3px;
  height: 3px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 50%;
}

.skeleton-action {
  width: 2.25rem;
  height: 2.25rem;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 50%;
  flex-shrink: 0;
}

.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.03),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
</style>
