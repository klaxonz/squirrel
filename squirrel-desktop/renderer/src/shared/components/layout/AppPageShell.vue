<template>
  <section
    class="app-page-shell"
    :class="[
      `app-page-shell--${variant}`,
      `app-page-shell--surface-${surface}`,
      `app-page-shell--width-${width}`,
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
withDefaults(defineProps<{
  variant?: 'default' | 'compact'
  surface?: 'consume' | 'organize' | 'operate' | 'immersive'
  width?: 'media' | 'table' | 'form' | 'reading' | 'fluid'
  fill?: boolean
  scrollable?: boolean
}>(), {
  variant: 'default',
  surface: 'operate',
  width: 'table',
  fill: false,
  scrollable: false,
})
</script>

<style scoped>
.app-page-shell {
  display: flex;
  width: 100%;
  min-height: 100%;
  flex-direction: column;
  color: hsl(var(--foreground));
  /* Flat resting surface — media and content carry visual richness. */
  background: transparent;
}

/*
  Fill = contained workbench page. Height is bound to the layout stage so
  the outer app scrollport does not become the document scroller; the first
  child (usually AppTwoColumnLayout) owns the internal scroll roots.
*/
.app-page-shell--fill {
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* Stretch the primary workbench child only — dialogs / portals may also be
   direct children and must not receive flex:1. */
.app-page-shell--fill > :deep(*:first-child) {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
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

@media (min-width: 1440px) {
  .app-page-shell--default {
    padding-left: var(--app-page-gutter-lg);
    padding-right: var(--app-page-gutter-lg);
  }
}

.app-page-shell--compact {
  padding: 0;
}

.app-page-shell--width-media {
  --app-page-max-width: var(--app-content-media-max);
}

.app-page-shell--width-table {
  --app-page-max-width: var(--app-content-table-max);
}

.app-page-shell--width-form {
  --app-page-max-width: var(--app-content-form-max);
}

.app-page-shell--width-reading {
  --app-page-max-width: var(--app-content-reading-max);
}

.app-page-shell--width-fluid {
  --app-page-max-width: none;
}
</style>
