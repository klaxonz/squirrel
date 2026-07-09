<template>
  <section
    class="app-page-shell"
    :class="[
      `app-page-shell--${variant}`,
      {
        'app-page-shell--fill': fill,
        'app-page-shell--scrollable': scrollable,
      },
    ]"
  >
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{
  variant?: 'default' | 'compact'
  fill?: boolean
  scrollable?: boolean
}>()
</script>

<style scoped>
.app-page-shell {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  color: hsl(var(--foreground));
  /* Flat resting surface — media and content carry visual richness. */
  background: transparent;
}

.app-page-shell--fill {
  height: 100%;
  min-height: 0;
}

/* Stretch the primary workbench child only — dialogs / portals may also be
   direct children and must not receive flex:1. */
.app-page-shell--fill > :deep(*:first-child) {
  flex: 1 1 auto;
  min-height: 0;
}

.app-page-shell--scrollable {
  overflow-y: auto;
}

.app-page-shell--default {
  padding: var(--space-5) var(--app-page-gutter) var(--app-content-padding-bottom);
}

@media (min-width: 640px) {
  .app-page-shell--default {
    padding-left: var(--app-page-gutter-sm);
    padding-right: var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .app-page-shell--default {
    padding-left: var(--app-page-gutter-lg);
    padding-right: var(--app-page-gutter-lg);
  }
}

.app-page-shell--compact {
  padding: 0;
}
</style>
