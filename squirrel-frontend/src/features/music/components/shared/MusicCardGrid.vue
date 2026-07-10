<template>
  <div class="music-card-grid" :class="layoutClass">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { musicCardGridVariants } from './music-card.variants'

const props = withDefaults(defineProps<{
  layout?: 'grid-2' | 'grid-3' | 'grid-4' | 'grid-5' | 'grid-auto' | 'scroll-x'
}>(), {
  layout: 'grid-auto',
})

const layoutClass = computed(() => musicCardGridVariants({ layout: props.layout }))
</script>

<style scoped>
.music-card-grid {
  display: grid;
  gap: var(--space-4) var(--space-3);
}

.music-card-grid--cols-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.music-card-grid--cols-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.music-card-grid--cols-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.music-card-grid--cols-5 {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.music-card-grid--auto {
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
}

.music-card-grid--scroll-x {
  display: flex;
  gap: var(--space-4);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  scrollbar-width: none;
}

.music-card-grid--scroll-x::-webkit-scrollbar {
  display: none;
}

.music-card-grid--scroll-x > * {
  width: 10rem;
  flex: none;
}

@media (max-width: 1180px) {
  .music-card-grid--cols-5 {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
