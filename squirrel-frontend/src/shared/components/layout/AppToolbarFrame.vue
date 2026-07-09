<template>
  <section
    class="app-toolbar-frame"
    :class="[
      `app-toolbar-frame--${variant}`,
      {
        'app-toolbar-frame--bordered': bordered,
        'app-toolbar-frame--compact': compact,
        'app-toolbar-frame--sticky': sticky,
      },
    ]"
  >
    <div class="app-toolbar-frame__inner">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'default' | 'compact'
  bordered?: boolean
  compact?: boolean
  sticky?: boolean
}>(), {
  variant: 'default',
  bordered: false,
  compact: false,
  sticky: false,
})
</script>

<style scoped>
.app-toolbar-frame {
  width: 100%;
  margin: 0 auto;
  padding-inline: var(--app-page-gutter);
  /* Opaque on the shared canvas so sticky toolbars cover scroll content
     without a frosted or card-tinted band. */
  background: hsl(var(--background));
}

.app-toolbar-frame--sticky {
  position: sticky;
  top: 0;
  /* UI-068: rely on background opacity instead of backdrop blur — keeps the
     toolbar readable on top of any scroll content without the frosted-glass
     effect DESIGN.md prohibits. */
  z-index: var(--z-sticky);
}

.app-toolbar-frame--bordered {
  border-bottom: 1px solid var(--app-hairline);
}

.app-toolbar-frame__inner {
  width: 100%;
  max-width: var(--app-page-max-width);
  margin: 0 auto;
  padding-block: var(--app-toolbar-padding-block);
}

.app-toolbar-frame--compact .app-toolbar-frame__inner {
  padding-block: 0.5rem;
}

@media (min-width: 640px) {
  .app-toolbar-frame {
    padding-inline: var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .app-toolbar-frame {
    padding-inline: var(--app-page-gutter-lg);
  }
}
</style>
