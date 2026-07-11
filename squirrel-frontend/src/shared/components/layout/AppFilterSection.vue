<template>
  <section
    class="app-filter-section"
    :class="{
      'app-filter-section--divided': divided,
      'app-filter-section--row': layout === 'row',
    }"
  >
    <header v-if="label" class="app-filter-section__label">{{ label }}</header>
    <div class="app-filter-section__body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  label?: string
  divided?: boolean
  /** row = label left, control right (for compact range rows). */
  layout?: 'stack' | 'row'
}>(), {
  divided: false,
  layout: 'stack',
})
</script>

<style scoped>
.app-filter-section {
  display: grid;
  gap: 0.35rem;
  min-width: 0;
  padding: 0.25rem 0.125rem;
}

.app-filter-section--divided {
  margin-top: 0.25rem;
  border-top: 1px solid hsl(var(--border) / 0.48);
  padding-top: 0.625rem;
}

.app-filter-section--row {
  grid-template-columns: 2rem 1fr;
  align-items: center;
  gap: 0.5rem;
  padding-block: 0.2rem;
}

.app-filter-section--row .app-filter-section__label {
  padding-inline: 0;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 600;
}

.app-filter-section__label {
  padding-inline: 0.15rem;
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.2;
}

.app-filter-section__body {
  min-width: 0;
}
</style>
