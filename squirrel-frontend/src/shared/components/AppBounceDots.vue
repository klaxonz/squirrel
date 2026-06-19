<template>
  <span class="app-bounce-dots" :class="[`app-bounce-dots--${size}`]" role="status" aria-label="loading">
    <span class="app-bounce-dots__dot" />
    <span class="app-bounce-dots__dot" />
    <span class="app-bounce-dots__dot" />
  </span>
</template>

<script setup lang="ts">
/**
 * Three-dot bounce indicator for compact inline loading (e.g. next to a title
 * while syncing). Replaces the three hand-rolled bounce-dot blocks in History /
 * RssSources / LoadingIndicator.
 */
withDefaults(defineProps<{
  size?: 'sm' | 'md'
}>(), {
  size: 'sm',
})
</script>

<style scoped>
.app-bounce-dots {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.app-bounce-dots__dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 9999px;
  background: hsl(var(--primary));
  animation: app-bounce-dot 1.2s ease-in-out infinite;
}

.app-bounce-dots__dot:nth-child(2) {
  animation-delay: 0.16s;
}

.app-bounce-dots__dot:nth-child(3) {
  animation-delay: 0.32s;
}

.app-bounce-dots--md .app-bounce-dots__dot {
  width: 0.5rem;
  height: 0.5rem;
}

@keyframes app-bounce-dot {
  0%, 80%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-0.25rem);
    opacity: 1;
  }
}
</style>
