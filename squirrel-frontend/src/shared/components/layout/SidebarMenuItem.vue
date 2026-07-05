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
  height: 2.25rem;
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
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
  background: hsl(var(--card) / 0.58);
  color: hsl(var(--foreground));
}
.sidebar-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--sidebar)), 0 0 0 4px hsl(var(--ring) / 0.4);
}
.sidebar-item.is-active {
  background:
    radial-gradient(ellipse 85% 160% at 0% 50%, hsl(var(--primary) / 0.18), transparent 72%),
    hsl(var(--primary) / 0.11);
  color: hsl(var(--foreground));
  font-weight: 650;
  box-shadow: 0 0 0 1px hsl(var(--primary) / 0.16) inset;
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
