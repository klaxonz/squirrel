<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import type { BadgeVariant } from '.'

const props = withDefaults(defineProps<{
  variant?: BadgeVariant
  class?: HTMLAttributes['class']
}>(), {
  variant: 'default',
})
</script>

<template>
  <span
    :class="[
      'app-badge',
      `app-badge--${variant}`,
      props.class,
    ]"
  >
    <slot />
  </span>
</template>

<style scoped>
.app-badge {
  display: inline-flex;
  min-height: 1.375rem;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  padding-inline: 0.5rem;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: 0.6875rem;
  font-weight: 650;
  line-height: 1;
  white-space: nowrap;
}

.app-badge--default {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.app-badge--secondary,
.app-badge--muted {
  border-color: hsl(var(--border) / 0.42);
  background: hsl(var(--muted) / 0.52);
  color: hsl(var(--muted-foreground) / 0.94);
}

.app-badge--outline {
  border-color: hsl(var(--border) / 0.72);
  background: transparent;
  color: hsl(var(--foreground) / 0.86);
}

.app-badge--active {
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
}

.app-badge--success {
  border-color: hsl(var(--success) / 0.25);
  background: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.app-badge--warning {
  border-color: hsl(var(--warning) / 0.25);
  background: hsl(var(--warning) / 0.1);
  color: hsl(var(--warning));
}

.app-badge--destructive,
.app-badge--error {
  border-color: hsl(var(--destructive) / 0.28);
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}
</style>
