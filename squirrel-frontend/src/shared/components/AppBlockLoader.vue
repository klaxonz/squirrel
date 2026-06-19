<template>
  <div class="app-block-loader" :class="[`app-block-loader--${size}`]" role="status" :aria-live="text ? 'polite' : undefined">
    <AppSpinner :size="size" :muted="muted" />
    <span v-if="text" class="app-block-loader__text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import AppSpinner from './AppSpinner.vue'

/**
 * Centered spinner + optional caption for a loading region. Replaces the six
 * music-scoped loader classes (`.music-loading`, `.music-detail-loading`, …)
 * and MusicLoadingState. Use inside any container that needs a loading state;
 * pass `text` for a caption, leave it off for a silent spinner.
 */
withDefaults(defineProps<{
  text?: string
  size?: 'sm' | 'md' | 'lg'
  muted?: boolean
}>(), {
  text: '',
  size: 'md',
  muted: true,
})
</script>

<style scoped>
.app-block-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--app-loader-gap);
  min-height: var(--app-loader-min-height);
  padding: var(--app-loader-padding);
  color: hsl(var(--muted-foreground));
}

.app-block-loader__text {
  font-size: var(--app-loader-font-size);
  font-weight: 500;
}

.app-block-loader--sm {
  min-height: 4rem;
  padding: 1.5rem 1rem;
  gap: 0.5rem;
}

.app-block-loader--sm .app-block-loader__text {
  font-size: 0.8125rem;
}
</style>
