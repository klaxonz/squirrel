<template>
  <div
    class="brand-logo flex items-center justify-center"
    :class="[sizeClass, roundedClass, props.class]"
    :style="containerStyle"
  >
    <svg
      class="brand-logo__mark"
      :class="iconClass"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <!-- Spiral mark: one continuous bezier curve that gathers inward from
           outside to a small filled dot at the heart. The metaphor stacks
           four layers of meaning on one shape:
             · 归  — the stroke returns to the center
             · 仓  — the outer ring is the warehouse wall
             · aggregation — a spiral reads as "things coming together"
             · Squirrel tail — the curve echoes a curled tail
           Each cubic segment pulls the curve tighter, so the spiral
           transitions smoothly between turns instead of looking like stacked
           arcs. At 20px the spiral reads as a glyph; at 48px the metaphor
           reveals. -->
      <path
        class="brand-logo__stroke"
        d="M 12 4
           C 17 4, 20 7, 20 12
           C 20 17, 17 20, 12 20
           C 7 20, 4 17, 4 12
           C 4 7.5, 7 5, 11 5
           C 14.5 5, 16.5 7.5, 16.5 11
           C 16.5 13.5, 14.5 15, 12 15
           C 10.5 15, 9.5 14, 9.5 12.5
           C 9.5 11.5, 10.5 11, 12 11"
        stroke="currentColor"
        stroke-width="2.25"
        stroke-linecap="round"
        stroke-linejoin="round"
        fill="none"
      />
      <!-- Acorn / content dot at the heart of the spiral -->
      <circle
        class="brand-logo__dot"
        cx="12"
        cy="11"
        r="1.55"
        fill="currentColor"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
/**
 * The product mark — a spiral glyph on a polished amber badge.
 *
 * Single source of truth for the brand visual. Replaces the previous
 * lightening-bolt mark (Zap icon), which signaled "speed/energy" — the wrong
 * metaphor for a content-aggregation product. The new mark signals
 * "gathering / return / storage" which matches the Chinese product name
 * 归仓 (return-to-warehouse) and the English brand "Squirrel" (a storer).
 *
 * Sizes:
 *   xs (20px) — DesktopTitleBar
 *   sm (32px) — auth pages (Login/Register/ServerConfig) brand panel
 *   md (48px) — reserved for hero/feature surfaces (currently unused)
 *
 * The container styling (gradient, inner highlight, glow) lives entirely in
 * the scoped stylesheet so consumers can drop the component in anywhere and
 * get a consistent badge.
 */
import { computed } from 'vue'
import type { HTMLAttributes } from 'vue'

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
  props.size === 'xs' ? 'rounded-md' : props.size === 'sm' ? 'rounded-lg' : 'rounded-xl',
)
const iconClass = computed(() =>
  props.size === 'xs' ? 'w-3 h-3' : props.size === 'sm' ? 'w-4 h-4' : 'w-6 h-6',
)
const containerStyle = computed(() => ({
  backgroundImage: 'var(--brand-gradient)',
  boxShadow: props.size === 'md' ? 'var(--brand-glow)' : 'var(--brand-glow-sm)',
}))
</script>

<style scoped>
.brand-logo {
  position: relative;
  color: hsl(var(--primary-foreground));
  /* The inner highlight + border give the badge a "polished enamel" depth
     without using a 1px solid border (which looks flat next to the gradient). */
  isolation: isolate;
  transition: transform var(--duration-fast) var(--ease-default);
}

.brand-logo::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  /* Top-edge inner highlight — simulates light hitting the top of the badge */
  box-shadow:
    inset 0 1px 0 hsl(0 0% 100% / 0.18),
    inset 0 -1px 0 hsl(0 0% 0% / 0.12);
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
.brand-logo__stroke {
  transform-origin: 12px 12px;
  transition: stroke-width var(--duration-fast) var(--ease-default);
}

.brand-logo__dot {
  transform-origin: 12px 13px;
  transition: transform var(--duration-fast) var(--ease-default);
}

.brand-logo:hover .brand-logo__dot {
  transform: scale(1.15);
}

@media (prefers-reduced-motion: reduce) {
  .brand-logo,
  .brand-logo__stroke,
  .brand-logo__dot {
    transition: none;
  }
  .brand-logo:hover .brand-logo__dot {
    transform: none;
  }
}
</style>