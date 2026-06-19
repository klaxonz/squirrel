<template>
  <section class="app-empty-state" :class="[`app-empty-state--${variant}`, iconCircle && 'app-empty-state--icon-circle']">
    <div v-if="icon" class="app-empty-state__icon-wrap">
      <AppIcon :name="icon" class="app-empty-state__icon" />
    </div>
    <h2 class="app-empty-state__title">{{ title }}</h2>
    <p v-if="copy" class="app-empty-state__copy">{{ copy }}</p>
    <div v-if="$slots.actions" class="app-empty-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

/**
 * Empty state for lists/regions. `bordered` (dashed outline, original LogViewer
 * style) or `plain` (no border). Optional `icon` renders centered above the
 * title; `iconCircle` wraps it in a rounded badge (the video/rss pattern).
 * Supersedes the 10+ hand-rolled empty blocks and MusicEmptyState.
 */
withDefaults(defineProps<{
  title: string
  copy?: string
  icon?: AppIconName
  iconCircle?: boolean
  variant?: 'bordered' | 'plain'
}>(), {
  copy: '',
  icon: undefined,
  iconCircle: false,
  // `bordered` preserves the original LogViewer look (the only existing call
  // site). New call sites pass `plain` for borderless list empties.
  variant: 'bordered',
})
</script>

<style scoped>
.app-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: var(--app-empty-gap);
  padding: var(--app-empty-padding);
  min-height: var(--app-empty-min-height);
}

.app-empty-state--bordered {
  border: 1px dashed hsl(var(--border) / var(--app-empty-border-alpha));
  border-radius: var(--app-surface-radius);
}

.app-empty-state__icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 9999px;
  background: hsl(var(--accent) / 0.5);
  margin-bottom: 0.25rem;
}

.app-empty-state--icon-circle .app-empty-state__icon-wrap {
  width: 3.5rem;
  height: 3.5rem;
  background: hsl(var(--accent) / 0.4);
  box-shadow: inset 0 0 0 4px hsl(var(--background));
}

.app-empty-state__icon {
  width: 1.5rem;
  height: 1.5rem;
  color: hsl(var(--muted-foreground) / 0.5);
}

.app-empty-state--icon-circle .app-empty-state__icon {
  width: 1.25rem;
  height: 1.25rem;
  color: hsl(var(--muted-foreground) / 0.5);
}

.app-empty-state__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 1.125rem;
  font-weight: 600;
}

.app-empty-state__copy {
  margin: 0;
  max-width: var(--app-empty-copy-width);
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  line-height: 1.6;
}

.app-empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
}
</style>
