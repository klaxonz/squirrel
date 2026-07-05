<template>
  <RouterLink
    v-if="!hidden"
    :to="targetPath"
    :replace="resolvePathFn ? false : true"
    class="sidebar-item group"
    :class="[{ 'is-active': isActive }, collapsed ? 'is-collapsed' : '']"
    :title="collapsed ? item.name : undefined"
  >
    <AppIcon :name="item.icon" class="sidebar-item__icon" :class="{ 'is-active': isActive }" />
    <span v-if="!collapsed" class="sidebar-item__label">{{ item.name }}</span>
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

const resolvePathFn = computed(() => props.item.resolvePath)

// UI-012: caller-supplied resolvePath can return the actual target path
// (e.g. keep current settings tab) or null to suppress the click entirely.
const targetPath = computed(() => {
  const fn = resolvePathFn.value
  if (fn) {
    const resolved = fn(route.path)
    return resolved ?? props.item.path
  }
  return props.item.path
})

const hidden = computed(() => {
  const fn = resolvePathFn.value
  if (fn) return fn(route.path) === null
  return false
})
</script>

<style scoped>
.sidebar-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 2.25rem;
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
  outline: none;
}
.sidebar-item:not(.is-collapsed) {
  width: 100%;
}
.sidebar-item.is-collapsed {
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  margin: 0 auto;
  padding: 0;
}
.sidebar-item:hover {
  background: hsl(var(--card) / 0.58);
  color: hsl(var(--foreground));
}
.sidebar-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--sidebar)), 0 0 0 4px hsl(var(--ring) / 0.4);
}
.sidebar-item.is-active {
  background: hsl(var(--primary) / 0.11);
  color: hsl(var(--foreground));
  font-weight: 650;
}

.sidebar-item__icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  color: hsl(var(--muted-foreground));
  transition: color var(--duration-fast) var(--ease-default);
}
.sidebar-item:hover .sidebar-item__icon {
  color: hsl(var(--foreground));
}
.sidebar-item__icon.is-active {
  color: hsl(var(--primary));
}

.sidebar-item__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: 0;
}
</style>
