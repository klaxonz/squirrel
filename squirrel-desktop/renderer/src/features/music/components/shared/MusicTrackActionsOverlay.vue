<template>
  <div class="music-track-actions-overlay">
    <slot />
  </div>
</template>

<style scoped>
.music-track-actions-overlay {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.music-track-row:hover .music-track-actions-overlay,
.music-track-actions-overlay:hover {
  opacity: 1;
}
</style>