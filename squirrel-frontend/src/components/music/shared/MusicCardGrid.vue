<template>
  <div class="music-card-grid" :class="layoutClass">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { musicCardGridVariants, type MusicCardSize } from './music-card.variants'

const props = withDefaults(defineProps<{
  layout?: 'grid-2' | 'grid-3' | 'grid-4' | 'grid-auto' | 'scroll-x'
  size?: MusicCardSize
}>(), {
  layout: 'grid-auto',
  size: 'md',
})

const layoutClass = computed(() => musicCardGridVariants({ layout: props.layout }))
</script>

<style scoped>
.music-card-grid {
  display: grid;
  gap: 1rem;
}

.music-card-grid--cols-2 {
  grid-template-columns: repeat(2, 1fr);
}

.music-card-grid--cols-3 {
  grid-template-columns: repeat(3, 1fr);
}

.music-card-grid--cols-4 {
  grid-template-columns: repeat(4, 1fr);
}

.music-card-grid--auto {
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
}

.music-card-grid--scroll-x {
  display: flex;
  overflow-x: auto;
  gap: 1rem;
  padding-bottom: 0.5rem;
  scrollbar-width: none;
}

.music-card-grid--scroll-x::-webkit-scrollbar {
  display: none;
}

.music-card-grid--scroll-x > * {
  flex-shrink: 0;
  width: 160px;
}

@media (max-width: 768px) {
  .music-card-grid--cols-3,
  .music-card-grid--cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }

  .music-card-grid--auto {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.875rem;
  }
}
</style>
