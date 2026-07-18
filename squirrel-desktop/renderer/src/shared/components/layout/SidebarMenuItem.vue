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
    <span class="sidebar-item__label">{{ item.name }}</span>
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
const targetPath = computed(() => props.item.resolvePath?.(route.path) ?? props.item.path)
</script>

<style scoped>
.sidebar-item {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 2.25rem;
  align-items: center;
  gap: 0.7rem;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0 0.625rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 520;
  line-height: 1.2;
  text-decoration: none;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.sidebar-item:hover {
  background: hsl(var(--accent) / 0.56);
  color: hsl(var(--foreground));
}

.sidebar-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.46);
}

.sidebar-item.is-active {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--foreground));
  font-weight: 620;
}

.sidebar-item.is-collapsed {
  justify-content: center;
  gap: 0;
  padding-inline: 0;
}

.sidebar-item.is-collapsed .sidebar-item__label {
  display: none;
}

.sidebar-item__icon {
  width: var(--sidebar-icon-size);
  height: var(--sidebar-icon-size);
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground));
}

.sidebar-item.is-active .sidebar-item__icon {
  color: hsl(var(--primary));
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
