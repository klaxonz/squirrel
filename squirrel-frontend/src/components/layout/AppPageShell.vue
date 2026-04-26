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

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'compact'].includes(value),
  },
  fill: {
    type: Boolean,
    default: true,
  },
  scrollable: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.app-page-shell {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  color: hsl(var(--foreground));
  background: hsl(var(--background));
}

.app-page-shell--fill {
  height: 100%;
  min-height: 0;
}

.app-page-shell--scrollable {
  overflow-y: auto;
}

.app-page-shell--default {
  padding: 0 var(--app-page-gutter);
}

@media (min-width: 640px) {
  .app-page-shell--default {
    padding: 0 var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .app-page-shell--default {
    padding: 0 var(--app-page-gutter-lg);
  }
}

.app-page-shell--compact {
  padding: 0;
}
</style>
