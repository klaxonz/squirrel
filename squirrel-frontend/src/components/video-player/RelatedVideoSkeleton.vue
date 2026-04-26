<template>
  <div class="related-video-skeleton" :style="{ animationDelay: `${delay}ms` }">
    <div class="skeleton-thumb">
      <div class="shimmer"></div>
    </div>
    <div class="skeleton-body">
      <div class="skeleton-title w-full"></div>
      <div class="skeleton-title w-2/3 mt-2"></div>
      <div class="skeleton-meta mt-3">
        <div class="skeleton-text w-16"></div>
        <div class="skeleton-separator">/</div>
        <div class="skeleton-text w-12"></div>
      </div>
    </div>
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
.related-video-skeleton {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 0.75rem;
  padding: 0.5rem 0;
  position: relative;
  overflow: hidden;
  animation: skeleton-appear var(--duration-slower) var(--ease-default) forwards;
  opacity: 0;
}

@keyframes skeleton-appear {
  from { opacity: 0; transform: translateX(10px); }
  to { opacity: 1; transform: translateX(0); }
}

.skeleton-thumb {
  aspect-ratio: 16 / 9;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 2px;
  position: relative;
  overflow: hidden;
}

.skeleton-body {
  display: flex;
  flex-direction: column;
}

.skeleton-title {
  height: 0.75rem;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 2px;
}

.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.skeleton-text {
  height: 0.6rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 2px;
}

.skeleton-separator {
  color: rgba(255, 255, 255, 0.1);
  font-size: 0.6rem;
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

@media (min-width: 1280px) {
  .related-video-skeleton {
    grid-template-columns: 100px 1fr;
  }
}
</style>
