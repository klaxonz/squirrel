<template>
  <RouterLink
    :to="targetPath"
    :replace="!item.resolvePath"
    class="sidebar-item"
    :class="{ 'is-active': isActive }"
    :aria-current="isActive ? 'page' : undefined"
  >
    <AppIcon
      :name="item.icon"
      class="sidebar-item__icon"
      :stroke-width="isActive ? 2 : 1.75"
    />
    <span class="sidebar-item__label">
      {{ item.name }}
    </span>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { NavigationItem } from '@/shared/constants/sidebar'

const props = defineProps<{
  item: NavigationItem
  isActive: boolean
}>()

const route = useRoute()

const targetPath = computed(() => {
  const resolved = props.item.resolvePath?.(route.path)
  return resolved ?? props.item.path
})
</script>

<style scoped>
/* Nav item: neutral ink selection (DESIGN color + navigation). Never primary. */
.sidebar-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  height: var(--sidebar-item-height);
  padding: 0 0.625rem;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.2;
  text-decoration: none;
  overflow: hidden;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.sidebar-item:hover {
  background: hsl(var(--foreground) / 0.055);
  color: var(--app-selection-fg);
}

.sidebar-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.55);
}

.sidebar-item.is-active {
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
  font-weight: 600;
}

.sidebar-item.is-active:hover {
  background: var(--app-selection-bg-hover);
}

.sidebar-item__icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
  color: currentColor;
}

.sidebar-item__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-item {
    transition: none;
  }
}
</style>
