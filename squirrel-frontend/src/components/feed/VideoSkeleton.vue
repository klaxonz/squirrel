<template>
  <div class="video-skeleton-item" :style="{ animationDelay: `${delay}ms` }">
    <div class="video-viewer-frame-skeleton">
      <div class="shimmer" :style="{ animationDelay: `${delay}ms` }"></div>
      <div class="skeleton-overlay">
        <div class="flex justify-between items-start w-full">
          <div class="skeleton-tag"></div>
        </div>
        <div class="flex justify-between items-end w-full">
          <div class="skeleton-tag w-12"></div>
          <div class="skeleton-time w-10"></div>
        </div>
      </div>
    </div>

    <div class="video-terminal-info-skeleton">
      <div class="skeleton-title w-full"></div>
      <div class="skeleton-title w-2/3 mt-2"></div>
      <div class="video-terminal-meta-skeleton mt-4">
        <div class="meta-left">
          <div class="skeleton-avatar"></div>
          <div class="skeleton-text w-20"></div>
        </div>
        <div class="meta-right">
          <div class="skeleton-text w-12"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  delay: {
    type: Number,
    default: 0,
  },
})
</script>

<style scoped>
.video-skeleton-item {
  position: relative;
  padding: 1rem;
  animation: skeleton-appear 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes skeleton-appear {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.video-viewer-frame-skeleton {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: hsl(var(--foreground) / 0.03);
  border-radius: 4px;
  border: 1px solid hsl(var(--foreground) / 0.05);
}

.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.05),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.skeleton-overlay {
  position: absolute;
  inset: 0;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(to bottom, hsl(var(--background) / 0.2) 0%, transparent 30%, transparent 70%, hsl(var(--background) / 0.4) 100%);
}

.skeleton-tag {
  height: 8px;
  background: hsl(var(--foreground) / 0.05);
  border-radius: 2px;
  width: 40px;
}

.skeleton-time {
  height: 12px;
  background: hsl(var(--foreground) / 0.1);
  border-radius: 2px;
}

.video-terminal-info-skeleton {
  margin-top: 0.75rem;
}

.skeleton-title {
  height: 14px;
  background: hsl(var(--foreground) / 0.07);
  border-radius: 2px;
}

.video-terminal-meta-skeleton {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex: 1;
}

.skeleton-avatar {
  width: 14px;
  height: 14px;
  background: hsl(var(--foreground) / 0.07);
  border-radius: 2px;
}

.skeleton-text {
  height: 10px;
  background: hsl(var(--foreground) / 0.05);
  border-radius: 2px;
}
</style>
