<template>
  <RouterLink
    :to="item.path"
    replace
    class="sidebar-item group"
    :class="[{ 'is-active': isActive }, collapsed ? 'is-collapsed' : '']"
    :title="collapsed ? item.name : undefined"
  >
    <AppIcon :name="item.icon" class="sidebar-item__icon" :class="{ 'is-active': isActive }" />
    <span v-if="!collapsed" class="sidebar-item__label">{{ item.name }}</span>
  </RouterLink>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

defineProps<{
  item: {
    path: string
    name: string
    icon: AppIconName
  }
  isActive: boolean
  collapsed?: boolean
}>()
</script>

<style scoped>
.sidebar-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 2.375rem;
  padding: 0 var(--space-3);
  border-radius: var(--radius-lg);
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  transition: background-color 0.12s ease, color 0.12s ease;
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
  background: hsl(var(--accent) / 0.74);
  color: hsl(var(--foreground));
}
.sidebar-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--sidebar)), 0 0 0 4px hsl(var(--ring) / 0.4);
}
.sidebar-item.is-active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--foreground));
  font-weight: 650;
}
.sidebar-item.is-active::before {
  content: '';
  position: absolute;
  left: 0.375rem;
  top: 50%;
  width: 3px;
  height: 1rem;
  border-radius: 999px;
  background: hsl(var(--primary));
  transform: translateY(-50%);
}
.sidebar-item.is-collapsed.is-active::before {
  left: 0.25rem;
  height: 1.125rem;
}

.sidebar-item__icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  color: hsl(var(--muted-foreground));
  transition: color 0.12s ease;
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
