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
    validator: (value) => ['default', 'dense', 'tactical', 'playback'].includes(value),
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

.app-page-shell--tactical {
  overflow: hidden;
}
</style>
