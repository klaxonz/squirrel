<template>
  <div class="feed-rail-header">
    <div class="feed-rail-header__lead">
      <h2 class="feed-rail-header__title">
        <span class="feed-rail-header__title-text">{{ title }}</span>
        <Button
          v-if="viewMore"
          type="button"
          text severity="secondary"
          size="sm"
          class="feed-rail-header__more"
          :aria-label="viewMoreLabel"
          @click="$emit('viewMore')"
        >
          <span>{{ viewMoreLabel }}</span>
          <AppIcon name="chevronRight" class="size-3.5" aria-hidden="true" />
        </Button>
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
        text severity="secondary"
        size="sm" icon-only
        class="feed-rail-header__icon-btn"
        :disabled="!canScrollLeft"
        aria-label="向左滚动"
        @click="$emit('scroll', 'left')"
      >
        <AppIcon name="chevronLeft" class="size-3.5" />
      </Button>
      <Button
        type="button"
        text severity="secondary"
        size="sm" icon-only
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
  letter-spacing: 0;
  line-height: 1.15;
  color: hsl(var(--foreground));
}

.feed-rail-header__more {
  display: inline-flex;
  min-height: 1.5rem;
  align-items: center;
  gap: 0.125rem;
  flex-shrink: 0;
  margin-left: 0.125rem;
  padding-inline: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.feed-rail-header__more:hover {
  color: hsl(var(--foreground));
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

</style>
