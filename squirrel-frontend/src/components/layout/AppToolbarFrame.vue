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
    validator: (value) => ['default', 'dense', 'tactical', 'playback'].includes(value),
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
  padding-block: var(--app-toolbar-padding-block);
}

.app-toolbar-frame--compact .app-toolbar-frame__inner,
.app-toolbar-frame--dense .app-toolbar-frame__inner {
  padding-block: 0.75rem;
}

.app-toolbar-frame--tactical {
  padding-inline: var(--app-tactical-page-gutter);
}

.app-toolbar-frame--tactical .app-toolbar-frame__inner {
  padding-block: 1rem 0.5rem;
}

@media (min-width: 640px) {
  .app-toolbar-frame {
    padding-inline: var(--app-page-gutter-sm);
  }

  .app-toolbar-frame--tactical {
    padding-inline: var(--app-tactical-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .app-toolbar-frame {
    padding-inline: var(--app-page-gutter-lg);
  }

  .app-toolbar-frame--tactical {
    padding-inline: var(--app-tactical-page-gutter-lg);
  }
}
</style>
