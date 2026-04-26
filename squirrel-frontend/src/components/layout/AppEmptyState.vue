<template>
  <section class="app-empty-state">
    <h2 class="app-empty-state__title">{{ title }}</h2>
    <p v-if="copy" class="app-empty-state__copy">{{ copy }}</p>
    <div v-if="$slots.actions" class="app-empty-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  copy: {
    type: String,
    default: '',
  },
})
</script>

<style scoped>
.app-empty-state {
  min-height: var(--app-empty-min-height);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: var(--app-empty-gap);
  padding: var(--app-empty-padding);
  border: 1px dashed hsl(var(--border) / var(--app-empty-border-alpha));
  border-radius: var(--app-surface-radius);
}

.app-empty-state__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 1.125rem;
  font-weight: 600;
}

.app-empty-state__copy {
  margin: 0;
  max-width: var(--app-empty-copy-width);
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  line-height: 1.6;
}

.app-empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
}
</style>
