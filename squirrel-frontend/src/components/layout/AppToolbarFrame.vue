<template>
  <section
    class="app-toolbar-frame"
    :class="[
      `app-toolbar-frame--${variant}`,
      {
        'app-toolbar-frame--bordered': bordered,
        'app-toolbar-frame--compact': compact,
      },
    ]"
  >
    <div class="app-toolbar-frame__inner">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'compact'].includes(value),
  },
  bordered: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.app-toolbar-frame {
  width: 100%;
  margin: 0 auto;
  padding-inline: var(--app-page-gutter);
}

.app-toolbar-frame--bordered {
  border-bottom: 1px solid hsl(var(--border) / var(--app-hairline-alpha));
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
