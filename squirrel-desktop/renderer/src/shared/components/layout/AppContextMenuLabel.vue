<template>
  <div class="app-context-menu-label" role="group" :aria-label="ariaLabel || undefined">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  ariaLabel?: string
}>()
</script>

<style scoped>
.app-context-menu-label {
  padding: 0.25rem 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 650;
}
</style>
