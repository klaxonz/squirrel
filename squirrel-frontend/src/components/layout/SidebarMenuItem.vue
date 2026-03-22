<template>
  <Tooltip>
    <TooltipTrigger as-child>
      <router-link
        :to="item.path"
        class="menu-item"
        :class="[
          isActive ? 'menu-item-active' : 'menu-item-inactive',
          { 'menu-item-collapsed': isCollapsed }
        ]"
      >
        <span class="menu-icon-wrap">
          <component :is="item.icon" class="menu-icon w-5 h-5" />
        </span>
        <span class="menu-text">
          <span class="menu-text__label">{{ item.name }}</span>
        </span>
      </router-link>
    </TooltipTrigger>
    <TooltipContent v-if="isCollapsed" side="right" :side-offset="10">
      {{ item.name }}
    </TooltipContent>
  </Tooltip>
</template>

<script setup>
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

defineProps({
  item: {
    type: Object,
    required: true,
  },
  isCollapsed: {
    type: Boolean,
    default: false,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  min-height: 3rem;
  padding: 0 0.75rem;
  margin-bottom: 0.35rem;
  color: hsl(var(--sidebar-foreground));
  border-radius: 1rem;
  border: 1px solid transparent;
  transition: background-color 0.2s ease, transform 0.2s ease, color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.menu-icon-wrap {
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 0.85rem;
  background: hsl(var(--card) / 0.65);
  border: 1px solid hsl(var(--border) / 0.55);
  box-shadow: 0 10px 22px hsl(var(--surface-shadow) / 0.08);
}

.menu-item-inactive:hover {
  background-color: hsl(var(--sidebar-accent) / 0.68);
  border-color: hsl(var(--border) / 0.68);
  transform: translateX(2px);
}

.menu-item-active {
  background:
    linear-gradient(135deg, hsl(var(--primary) / 0.16), hsl(var(--sidebar-accent)));
  color: hsl(var(--foreground));
  border-color: hsl(var(--primary) / 0.18);
  box-shadow:
    inset 0 0 0 1px hsl(var(--primary) / 0.18),
    0 16px 32px hsl(var(--surface-shadow) / 0.12);
}

.menu-icon {
  flex-shrink: 0;
}

.menu-text {
  opacity: 1;
  transform: translateX(0);
  transition: opacity 0.15s ease, transform 0.2s ease;
  white-space: nowrap;
  will-change: opacity, transform;
  min-width: 0;
  margin-left: 0.8rem;
}

.menu-text__label {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
}

.menu-item-collapsed .menu-text {
  opacity: 0;
  transform: translateX(-0.5rem);
  pointer-events: none;
  width: 0;
  overflow: hidden;
}

.menu-item-collapsed {
  padding-left: var(--sidebar-collapsed-item-padding, 0.875rem);
  padding-right: var(--sidebar-collapsed-item-padding, 0.875rem);
}

.menu-item-collapsed .menu-icon-wrap {
  margin: 0;
}
</style>
