<template>
  <section class="app-empty-state" :class="[variantClass, iconCircle && 'app-empty-state--icon-circle']">
    <div v-if="resolvedIcon" class="app-empty-state__icon-wrap">
      <AppIcon :name="resolvedIcon" class="app-empty-state__icon" />
    </div>
    <h2 class="app-empty-state__title">{{ title }}</h2>
    <p v-if="copy" class="app-empty-state__copy">{{ copy }}</p>
    <div v-if="$slots.actions" class="app-empty-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

/**
 * Empty state for lists/regions. `bordered` (dashed outline, original LogViewer
 * style) or `plain` (no border). Optional `icon` renders centered above the
 * title; `iconCircle` wraps it in a rounded badge (the video/rss pattern).
 *
 * `variant="error"` is the canonical load-failure state: it tints the icon +
 * title destructive-red and defaults `icon` to `warning`, so every failed
 * fetch looks the same without each view re-rolling a red banner. Pair with the
 * `#actions` slot for a 重试 button (see `History.vue`).
 *
 * Supersedes the 10+ hand-rolled empty blocks and MusicEmptyState.
 */
const props = withDefaults(defineProps<{
  title: string
  copy?: string
  /** Defaults to `warning` for the `error` variant, otherwise none. */
  icon?: AppIconName
  iconCircle?: boolean
  variant?: 'bordered' | 'plain' | 'error'
}>(), {
  copy: '',
  icon: undefined,
  iconCircle: false,
  // `bordered` preserves the original LogViewer look (the only existing call
  // site). New call sites pass `plain` for borderless list empties.
  variant: 'bordered',
})

// Error variant defaults its icon to `warning` unless the caller overrides it.
const resolvedIcon = computed<AppIconName | undefined>(
  () => props.icon ?? (props.variant === 'error' ? 'warning' : undefined),
)
// `error` shares `plain`'s borderless layout and layers the destructive tint on top.
const variantClass = computed(() =>
  props.variant === 'error'
    ? 'app-empty-state--plain app-empty-state--error'
    : `app-empty-state--${props.variant}`,
)
</script>

<style scoped>
.app-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: var(--space-3);
  padding: var(--space-7) var(--space-5);
  min-height: max(var(--app-empty-min-height), 16rem);
}

.app-empty-state--bordered {
  border: 1px solid hsl(var(--border) / 0.58);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--card) / 0.42);
}

.app-empty-state__icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: var(--radius-xl);
  background: hsl(var(--muted) / 0.52);
  border: 1px solid hsl(var(--border) / 0.62);
  margin-bottom: var(--space-1);
}

.app-empty-state--icon-circle .app-empty-state__icon-wrap {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: var(--radius-xl);
  background: hsl(var(--muted) / 0.52);
  box-shadow: inset 0 0 0 4px hsl(var(--background) / 0.58);
}

.app-empty-state__icon {
  width: 1.5rem;
  height: 1.5rem;
  color: hsl(var(--muted-foreground) / 0.84);
}

.app-empty-state--icon-circle .app-empty-state__icon {
  width: 1.25rem;
  height: 1.25rem;
  color: hsl(var(--muted-foreground) / 0.84);
}

.app-empty-state__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-display);
  font-size: var(--app-h2-size);
  font-weight: 600;
  line-height: var(--app-h2-leading);
  letter-spacing: var(--app-h2-tracking);
}

.app-empty-state__copy {
  margin: 0;
  max-width: var(--app-empty-copy-width);
  color: hsl(var(--muted-foreground) / 0.92);
  font-size: 0.875rem;
  line-height: 1.6;
  text-wrap: pretty;
}

.app-empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

/* Error variant: destructive tint on the icon badge + title so a failed load is
   visually distinct from a genuinely-empty list. Layout reuses `--plain`. */
.app-empty-state--error .app-empty-state__icon-wrap {
  background: hsl(var(--destructive) / 0.12);
  border-color: hsl(var(--destructive) / 0.22);
}

.app-empty-state--error .app-empty-state__icon {
  color: hsl(var(--destructive));
}

.app-empty-state--error .app-empty-state__title {
  color: hsl(var(--destructive));
}
</style>
