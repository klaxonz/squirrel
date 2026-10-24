<template>
  <header
    class="app-operate-page-header"
    :class="`app-operate-page-header--${size}`"
  >
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
withDefaults(defineProps<{
  title: string
  summary?: string
  description?: string
  size?: 'md' | 'lg'
}>(), {
  size: 'md',
})
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
  gap: 0.375rem;
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
  font-family: var(--font-display);
  font-size: var(--app-text-2xl);
  font-weight: 650;
  line-height: var(--app-leading-title);
  letter-spacing: -0.02em;
}

.app-operate-page-header__title span {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 600;
}

.app-operate-page-header--lg .app-operate-page-header__title h1 {
  font-size: var(--app-text-3xl);
}

.app-operate-page-header__copy p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  line-height: 1.55;
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
