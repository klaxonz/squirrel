<template>
  <header class="app-operate-page-header">
    <div class="app-operate-page-header__copy">
      <div class="app-operate-page-header__title">
        <h1>{{ title }}</h1>
        <span v-if="summary">{{ summary }}</span>
      </div>
      <p v-if="description">{{ description }}</p>
    </div>

    <div v-if="$slots.actions" class="app-operate-page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  summary?: string
  description?: string
}>()
</script>

<style scoped>
.app-operate-page-header {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-7);
}

.app-operate-page-header__copy {
  display: grid;
  min-width: 0;
  gap: var(--space-2);
}

.app-operate-page-header__title {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: var(--space-2);
}

.app-operate-page-header__title h1 {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-sans);
  font-size: 1.125rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.app-operate-page-header__title span {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 550;
}

.app-operate-page-header__copy p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  line-height: 1.5;
}

.app-operate-page-header__actions {
  display: flex;
  min-width: 0;
  flex: none;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

@media (max-width: 900px) {
  .app-operate-page-header {
    flex-direction: column;
  }

  .app-operate-page-header__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
