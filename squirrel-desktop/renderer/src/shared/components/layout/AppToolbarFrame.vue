<template>
  <section
    class="app-toolbar-frame"
    :class="[
      `app-toolbar-frame--${variant}`,
      `app-toolbar-frame--boundary-${boundary}`,
      `app-toolbar-frame--divider-${divider}`,
      {
        'app-toolbar-frame--bordered': bordered,
        'app-toolbar-frame--compact': compact,
        'app-toolbar-frame--sticky': sticky,
      },
    ]"
  >
    <div
      class="app-toolbar-frame__inner"
      :class="{ 'app-content-aligned-divider': bordered && divider === 'content' }"
    >
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'default' | 'compact'
  /** Horizontal reading boundary shared with the page content below. */
  boundary?: 'page' | 'media'
  /** A full-width shell rule or a rule aligned to the inner content edge. */
  divider?: 'full' | 'content'
  bordered?: boolean
  compact?: boolean
  sticky?: boolean
}>(), {
  variant: 'default',
  boundary: 'page',
  divider: 'full',
  bordered: false,
  compact: false,
  sticky: false,
})
</script>

<style scoped>
.app-toolbar-frame {
  --app-toolbar-content-max: var(--app-page-max-width);
  --app-toolbar-inline-gutter: var(--app-page-gutter);
  --app-divider-inline-gutter: var(--app-toolbar-inline-gutter);
  width: 100%;
  margin: 0 auto;
  /* Opaque on the shared canvas so sticky toolbars cover scroll content
     without a frosted or card-tinted band. */
  background: hsl(var(--background));
}

.app-toolbar-frame--sticky {
  position: sticky;
  top: 0;
  /* Prefer solid background over backdrop blur for sticky toolbars. */
  z-index: var(--z-sticky);
}

.app-toolbar-frame--bordered.app-toolbar-frame--divider-full {
  border-bottom: 1px solid hsl(var(--border) / 0.32);
}

.app-toolbar-frame__inner {
  width: 100%;
  max-width: var(--app-toolbar-content-max);
  margin: 0 auto;
  padding-block: var(--app-toolbar-padding-block);
  padding-inline: var(--app-toolbar-inline-gutter);
}

.app-toolbar-frame--boundary-media {
  --app-toolbar-content-max: var(--app-content-media-max);
  --app-toolbar-inline-gutter: var(--app-content-media-gutter);
}

.app-toolbar-frame--compact .app-toolbar-frame__inner {
  padding-block: 0.4375rem;
}

@media (min-width: 640px) {
  .app-toolbar-frame--boundary-page {
    --app-toolbar-inline-gutter: var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .app-toolbar-frame--boundary-page {
    --app-toolbar-inline-gutter: var(--app-page-gutter-lg);
  }
}
</style>
