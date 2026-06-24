<template>
  <!-- Expanded item -->
  <RouterLink
    v-if="!collapsed"
    :to="item.path"
    class="sidebar-item group"
    :class="{ 'is-active': isActive }"
  >
    <span class="sidebar-item__active-bar" />
    <AppIcon :name="item.icon" class="sidebar-item__icon" :class="{ 'is-active': isActive }" />
    <span class="sidebar-item__label">{{ item.name }}</span>
  </RouterLink>

  <!-- Collapsed item — wrapped in Tooltip for a hover label -->
  <Tooltip v-else>
    <TooltipTrigger as-child>
      <RouterLink
        :to="item.path"
        class="sidebar-item group is-collapsed"
        :class="{ 'is-active': isActive }"
      >
        <span class="sidebar-item__active-bar" />
        <AppIcon :name="item.icon" class="sidebar-item__icon" :class="{ 'is-active': isActive }" />
      </RouterLink>
    </TooltipTrigger>
    <TooltipContent side="right">
      {{ item.name }}
    </TooltipContent>
  </Tooltip>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import Tooltip from '@/shared/ui/tooltip/Tooltip.vue'
import TooltipTrigger from '@/shared/ui/tooltip/TooltipTrigger.vue'
import TooltipContent from '@/shared/ui/tooltip/TooltipContent.vue'
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
  gap: 0.75rem;
  height: 2.25rem;
  padding: 0 0.75rem;
  border-radius: 0.375rem;
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
  width: 2.25rem;
  height: 2.25rem;
  margin: 0 auto;
  padding: 0;
}
.sidebar-item:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}
.sidebar-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--sidebar)), 0 0 0 4px hsl(var(--ring) / 0.4);
}
.sidebar-item.is-active {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--foreground));
  font-weight: 500;
}

/* Left emphasis bar — replaces the old ring + drop-shadow active treatment. */
.sidebar-item__active-bar {
  position: absolute;
  left: -0.375rem;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 2px;
  height: 1.125rem;
  border-radius: 2px;
  background: hsl(var(--primary));
  transition: transform 0.14s ease;
}
.sidebar-item.is-active .sidebar-item__active-bar {
  transform: translateY(-50%) scaleY(1);
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
  letter-spacing: -0.005em;
}
</style>