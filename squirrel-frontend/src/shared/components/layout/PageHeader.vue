<template>
  <section class="page-header">
    <div class="page-header__copy">
      <div class="page-header__title-row">
        <h1 class="page-header__title app-h2">{{ title }}</h1>
        <slot name="meta" />
      </div>
      <p v-if="description" class="page-header__description">{{ description }}</p>
    </div>

    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-5);
  width: 100%;
  padding: var(--space-2) 0 var(--space-4);
}

.page-header__copy {
  min-width: 0;
  display: grid;
  gap: var(--space-2);
}

.page-header__title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.page-header__title {
  color: hsl(var(--foreground));
  text-wrap: balance;
}

.page-header__description {
  margin: 0;
  max-width: 56rem;
  color: hsl(var(--muted-foreground) / 0.92);
  font-size: 0.875rem;
  line-height: 1.6;
  text-wrap: pretty;
}

.page-header__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  flex-wrap: wrap;
  flex-shrink: 0;
}

/* No mobile breakpoint: desktop-only product. The old <768px stack variant
   was dead code. */
</style>
