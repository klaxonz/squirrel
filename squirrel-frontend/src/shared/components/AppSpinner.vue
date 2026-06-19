<template>
  <AppIcon
    name="loadingSpinner"
    class="app-spinner animate-spin"
    :class="[`app-spinner--${size}`, muted && 'app-spinner--muted']"
  />
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

/**
 * Single loading spinner atom. Use inside buttons (size="sm"), inline, or as a
 * block loader via AppBlockLoader. Ends the loadingSpinner / border-ring /
 * refresh-icon spinner split — every loading indicator funnels through here.
 */
withDefaults(defineProps<{
  size?: 'sm' | 'md' | 'lg'
  /** Use muted-foreground instead of primary. For low-emphasis loaders. */
  muted?: boolean
}>(), {
  size: 'md',
  muted: false,
})
</script>

<style scoped>
.app-spinner {
  width: var(--app-spinner-size-md);
  height: var(--app-spinner-size-md);
  color: var(--app-spinner-color);
  flex: none;
}

.app-spinner--sm {
  width: var(--app-spinner-size-sm);
  height: var(--app-spinner-size-sm);
}

.app-spinner--lg {
  width: var(--app-spinner-size-lg);
  height: var(--app-spinner-size-lg);
}

.app-spinner--muted {
  color: var(--app-spinner-muted-color);
}
</style>
