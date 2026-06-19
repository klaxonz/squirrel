<template>
  <div
    class="app-skeleton"
    :class="[shimmer && 'app-skeleton--shimmer']"
    :style="skeletonStyle"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * Single placeholder block. Every skeleton in the app composes from this — it
 * ends the muted / accent / secondary base-color split. Pass `width`/`height`
 * (any CSS length) and optional `rounded`. Add `shimmer` for the sweeping
 * highlight (list/grids); leave it off for plain pulse (dense rows).
 */
const props = withDefaults(defineProps<{
  width?: string
  height?: string
  rounded?: string
  /** Sweep highlight animation (uses --app-skeleton-shimmer). */
  shimmer?: boolean
}>(), {
  width: '100%',
  height: '1rem',
  rounded: 'var(--app-skeleton-radius)',
  shimmer: false,
})

const skeletonStyle = computed(() => ({
  width: props.width,
  height: props.height,
  borderRadius: props.rounded,
}))
</script>

<style scoped>
.app-skeleton {
  background: var(--app-skeleton-base);
  position: relative;
  overflow: hidden;
}

.app-skeleton--shimmer::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent,
    var(--app-skeleton-shimmer),
    transparent
  );
  animation: app-skeleton-shimmer 1.5s ease-in-out infinite;
}

@keyframes app-skeleton-shimmer {
  100% {
    transform: translateX(100%);
  }
}
</style>
