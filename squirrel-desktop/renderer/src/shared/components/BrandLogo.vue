<template>
  <div
    class="brand-logo flex items-center justify-center"
    :class="[sizeClass, roundedClass, props.class]"
    :style="containerStyle"
  >
    <BrandMark
      class="brand-logo__mark"
      :class="iconClass"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * The product mark — a spiral glyph on a restrained amber tile.
 *
 * Single source of truth for the brand visual. Replaces the previous
 * lightening-bolt mark (Zap icon), which signaled "speed/energy" — the wrong
 * metaphor for a content-aggregation product. The new mark signals
 * "gathering / return / storage" which matches the Chinese product name
 * 归仓 (return-to-warehouse) and the English brand "Squirrel" (a storer).
 *
 * Sizes:
 *   xs (20px) — compact navigation surfaces
 *   sm (32px) — auth pages (Login/Register/ServerConfig) brand panel
 *   md (48px) — reserved for hero/feature surfaces (currently unused)
 *
 * The container styling (gradient, inner highlight, glow) lives entirely in
 * the scoped stylesheet so consumers can drop the component in anywhere and
 * get a consistent badge.
 */
import { computed } from 'vue'
import type { HTMLAttributes } from 'vue'
import BrandMark from '@/shared/components/BrandMark.vue'

const props = withDefaults(defineProps<{
  size?: 'xs' | 'sm' | 'md'
  class?: HTMLAttributes['class']
}>(), {
  size: 'md',
})

const sizeClass = computed(() =>
  props.size === 'xs' ? 'w-5 h-5' : props.size === 'sm' ? 'w-8 h-8' : 'w-12 h-12',
)
const roundedClass = computed(() =>
  props.size === 'xs' ? 'rounded-md' : 'rounded-lg',
)
const iconClass = computed(() =>
  props.size === 'xs' ? 'w-3 h-3' : props.size === 'sm' ? 'w-4 h-4' : 'w-6 h-6',
)
const containerStyle = computed(() => ({
  backgroundColor: 'hsl(var(--primary) / 0.14)',
  boxShadow: 'inset 0 0 0 1px hsl(var(--primary) / 0.28)',
}))
</script>

<style scoped>
.brand-logo {
  position: relative;
  color: hsl(var(--primary));
  isolation: isolate;
  transition: transform var(--duration-fast) var(--ease-default);
}

.brand-logo::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  box-shadow: none;
  z-index: 1;
}

.brand-logo__mark {
  position: relative;
  z-index: 2;
  display: block;
  /* SVG strokes inherit `color` from the container, which is primary-foreground
     (dark text in dark mode, light in light mode) — so the mark always reads
     with maximum contrast against the amber gradient regardless of theme. */
}

/* The spiral stroke and the acorn dot share the same color but the dot is
   drawn with a tiny CSS scale animation only when the component is hovered —
   a quiet "the mark is alive" hint. Disabled under reduced motion. */
@media (prefers-reduced-motion: reduce) {
  .brand-logo {
    transition: none;
  }
}
</style>
