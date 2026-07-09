<template>
  <RouterLink
    :to="targetPath"
    :replace="!item.resolvePath"
    class="sidebar-item"
    :class="{ 'is-active': isActive, 'is-collapsed': collapsed }"
    :title="collapsed ? item.name : undefined"
  >
    <AppIcon
      :name="item.icon"
      class="sidebar-item__icon"
      :class="{ 'is-active': isActive }"
      :stroke-width="1.75"
    />
    <span
      v-if="!collapsed"
      class="sidebar-item__label"
    >
      {{ item.name }}
    </span>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

const props = defineProps<{
  item: {
    path: string
    name: string
    icon: AppIconName
    resolvePath?: (currentPath: string) => string | null
  }
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
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  height: 2.25rem;
  padding: 0 0.625rem;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.sidebar-item.is-collapsed {
  width: 2.25rem;
  margin-inline: auto;
  padding: 0;
  justify-content: center;
  gap: 0;
}

.sidebar-item:hover {
  background: hsl(var(--card) / 0.55);
  color: hsl(var(--foreground));
}

.sidebar-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--sidebar)), 0 0 0 4px hsl(var(--ring) / 0.4);
}

.sidebar-item.is-active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--foreground));
  font-weight: 600;
}

.sidebar-item__icon {
  width: 1.0625rem;
  height: 1.0625rem;
  flex-shrink: 0;
  color: hsl(var(--muted-foreground));
}

.sidebar-item:hover .sidebar-item__icon {
  color: hsl(var(--foreground));
}

.sidebar-item__icon.is-active {
  color: hsl(var(--primary));
}

.sidebar-item__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
