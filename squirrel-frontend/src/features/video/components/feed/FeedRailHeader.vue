<template>
  <div class="feed-rail-header">
    <!-- Left: title + geometric › (CSS, not font/SVG — true midline with CJK) -->
    <div class="feed-rail-header__lead">
      <h2 class="feed-rail-header__title">
        <span class="feed-rail-header__title-text">{{ title }}</span>
        <button
          v-if="viewMore"
          type="button"
          class="feed-rail-header__more"
          :aria-label="viewMoreLabel"
          @click="$emit('viewMore')"
        >
          <span class="feed-rail-header__more-chevron" aria-hidden="true" />
        </button>
      </h2>
    </div>

    <!-- Right: page left / right -->
    <div
      v-if="showScrollControls"
      class="feed-rail-header__scroll"
      role="group"
      aria-label="横向滚动"
    >
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        class="feed-rail-header__icon-btn"
        :disabled="!canScrollLeft"
        aria-label="向左滚动"
        @click="$emit('scroll', 'left')"
      >
        <AppIcon name="chevronLeft" class="size-3.5" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        class="feed-rail-header__icon-btn"
        :disabled="!canScrollRight"
        aria-label="向右滚动"
        @click="$emit('scroll', 'right')"
      >
        <AppIcon name="chevronRight" class="size-3.5" />
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

const props = withDefaults(defineProps<{
  title: string
  viewMore?: boolean
  viewMoreLabel?: string
  canScrollLeft?: boolean
  canScrollRight?: boolean
}>(), {
  viewMore: false,
  viewMoreLabel: '查看全部',
  canScrollLeft: false,
  canScrollRight: false,
})

defineEmits<{
  viewMore: []
  scroll: [direction: 'left' | 'right']
}>()

const showScrollControls = computed(
  () => props.canScrollLeft || props.canScrollRight,
)
</script>

<style scoped>
.feed-rail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.125rem;
  min-height: 2.125rem;
}

.feed-rail-header__lead {
  min-width: 0;
}

/* One flex line: CJK label + chevron share the same vertical center */
.feed-rail-header__title {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  margin: 0;
  line-height: 1;
}

.feed-rail-header__title-text {
  display: block;
  font-family: var(--font-display);
  font-size: 1.125rem;
  font-weight: 650;
  letter-spacing: -0.022em;
  line-height: 1.15;
  color: hsl(var(--foreground));
}

.feed-rail-header__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  /* Same height as the 1em text line box → flex center is true optical center */
  width: 0.75em;
  height: 1em;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 0.2rem;
  transition: color 150ms ease;
}

.feed-rail-header__more:hover,
.feed-rail-header__more:focus-visible {
  color: hsl(var(--foreground));
}

.feed-rail-header__more:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.5);
}

/*
 * Geometric chevron (rotated square corner).
 * No font metrics, no SVG viewBox bias — pure box center.
 */
.feed-rail-header__more-chevron {
  display: block;
  width: 0.34em;
  height: 0.34em;
  border-top: 1.5px solid currentColor;
  border-right: 1.5px solid currentColor;
  transform: rotate(45deg);
  /* Pull slightly left so the visual tip sits tighter to the title */
  margin-left: -0.05em;
}

.feed-rail-header__scroll {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  flex-shrink: 0;
}

.feed-rail-header__icon-btn {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 0;
}

.feed-rail-header__icon-btn :deep(svg) {
  display: block;
  flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
  .feed-rail-header__more {
    transition: none;
  }
}
</style>
