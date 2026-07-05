<template>
  <div
    v-if="src"
    class="rss-image-lightbox"
    @click="$emit('close')"
  >
    <button
      class="rss-image-lightbox__close"
      @click.stop="$emit('close')"
    >
      <AppIcon name="close" class="h-5 w-5" />
    </button>

    <div class="rss-image-lightbox__frame">
      <img
        :src="src"
        class="rss-image-lightbox__image"
        :style="{ transform: `scale(${scale})` }"
        @click.stop="$emit('close')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Full-screen image lightbox for the RSS reader. Extracted from RssSources.vue
 * (was an inline ~25-line block). Pure presentational: shows when `src` is
 * truthy, emits `close` on backdrop/button/image click. The zoom scale is
 * passed in (owned by useRssReader).
 */
import AppIcon from '@/shared/icons/AppIcon.vue'

defineProps<{
  src: string | null
  scale: number
}>()

defineEmits<{
  close: []
}>()
</script>

<style scoped>
.rss-image-lightbox {
  position: fixed;
  inset: 0;
  z-index: var(--z-sidebar, 60);
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--background) / 0.96);
}

.rss-image-lightbox__close {
  position: absolute;
  top: 1.25rem;
  right: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: 1px solid hsl(var(--border) / 0.16);
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.24);
  color: hsl(var(--foreground));
  cursor: pointer;
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.rss-image-lightbox__close:hover {
  border-color: hsl(var(--border) / 0.32);
  background: hsl(var(--accent) / 0.42);
}

.rss-image-lightbox__frame {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  user-select: none;
}

.rss-image-lightbox__image {
  max-width: 100%;
  max-height: 90vh;
  border-radius: 0.625rem;
  object-fit: contain;
  cursor: zoom-out;
  transition: transform 0.2s ease;
}

@media (prefers-reduced-motion: reduce) {
  .rss-image-lightbox__close,
  .rss-image-lightbox__image {
    transition: none;
  }
}
</style>
