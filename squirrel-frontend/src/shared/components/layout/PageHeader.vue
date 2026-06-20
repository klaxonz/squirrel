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
  gap: 1rem;
  width: 100%;
  padding: 0.25rem 0;
}

.page-header__copy {
  min-width: 0;
  display: grid;
  gap: 0.2rem;
}

.page-header__title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.page-header__title {
  /* Size/weight/leading/tracking/family now come from the .app-h2 utility
     applied in the template; this block only owns color fallback for callers
     that pass a custom title class. */
  color: hsl(var(--foreground));
}

.page-header__description {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.45;
}

.page-header__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.375rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }

  .page-header__actions {
    justify-content: flex-start;
  }
}
</style>
