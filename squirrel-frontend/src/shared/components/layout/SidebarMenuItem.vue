<template>
  <RouterLink
    :to="targetPath"
    :replace="!item.resolvePath"
    class="sidebar-item"
    :class="{
      'is-active': isActive,
      'is-nested': nested,
    }"
    :aria-current="isActive ? 'page' : undefined"
  >
    <AppIcon
      :name="item.icon"
      class="sidebar-item__icon"
      :class="{ 'is-active': isActive }"
      :stroke-width="1.75"
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
  nested?: boolean
}>()

const route = useRoute()

const targetPath = computed(() => {
  const resolved = props.item.resolvePath?.(route.path)
  return resolved ?? props.item.path
})
</script>

<style scoped>
.sidebar-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  height: var(--sidebar-item-height);
  padding: 0 0.625rem;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.sidebar-item.is-nested {
  padding-left: 1.5rem;
}

.sidebar-item:hover {
  background: hsl(var(--foreground) / 0.055);
  color: hsl(var(--foreground));
}

.sidebar-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.65);
}

.sidebar-item.is-active {
  border-color: transparent;
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground));
  font-weight: 500;
}

.sidebar-item.is-active:hover {
  background: hsl(var(--foreground) / 0.1);
}

.sidebar-item__icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
  color: hsl(var(--muted-foreground));
  transition: color var(--duration-fast) var(--ease-default);
}

.sidebar-item:hover .sidebar-item__icon {
  color: hsl(var(--foreground));
}

.sidebar-item__icon.is-active {
  color: hsl(var(--foreground));
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
