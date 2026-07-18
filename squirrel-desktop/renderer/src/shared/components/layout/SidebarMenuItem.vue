<template>
  <RouterLink
    :to="targetPath"
    :replace="!item.resolvePath"
    class="sidebar-item"
    :class="{ 'is-active': isActive, 'is-collapsed': collapsed }"
    :aria-current="isActive ? 'page' : undefined"
    :title="collapsed ? item.name : undefined"
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
  collapsed?: boolean
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
  gap: 0.55rem;
  width: 100%;
  height: var(--sidebar-item-height);
  padding: 0 0.75rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.88);
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
  background: hsl(var(--foreground) / 0.035);
  color: hsl(var(--foreground) / 0.92);
}

.sidebar-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.55);
}

.sidebar-item.is-active {
  background: transparent;
  color: hsl(var(--primary));
  font-weight: 600;
}

.sidebar-item.is-active::before {
  content: '';
  position: absolute;
  top: 0.5rem;
  bottom: 0.5rem;
  left: 0.2rem;
  width: 2px;
  border-radius: 2px;
  background: hsl(var(--primary));
}

.sidebar-item.is-active:hover {
  background: hsl(var(--foreground) / 0.045);
}

.sidebar-item.is-collapsed {
  justify-content: center;
  gap: 0;
  padding-inline: 0;
}

.sidebar-item.is-collapsed.is-active::before {
  top: 0.55rem;
  bottom: 0.55rem;
  left: 0;
}

.sidebar-item.is-collapsed .sidebar-item__label {
  width: 0;
  opacity: 0;
}

.sidebar-item__icon {
  width: var(--sidebar-icon-size);
  height: var(--sidebar-icon-size);
  flex-shrink: 0;
  color: currentColor;
  opacity: 0.88;
}

.sidebar-item.is-active .sidebar-item__icon {
  opacity: 1;
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
