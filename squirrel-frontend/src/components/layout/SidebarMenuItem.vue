<template>
  <Tooltip>
    <TooltipTrigger as-child>
      <router-link
        :to="item.path"
        class="menu-item flex items-center h-10 px-3 text-sidebar-foreground rounded-xl mb-1"
        :class="[
          isActive ? 'menu-item-active' : 'menu-item-inactive',
          { 'menu-item-collapsed': isCollapsed }
        ]"
      >
        <component :is="item.icon" class="menu-icon w-5 h-5" />
        <span class="menu-text text-xs">{{ item.name }}</span>
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
  transition: background-color 0.2s ease, transform 0.2s ease, color 0.2s ease;
}

.menu-item-inactive:hover {
  background-color: hsl(var(--sidebar-accent));
  transform: translateX(2px);
}

.menu-item-active {
  background:
    linear-gradient(135deg, hsl(var(--primary) / 0.16), hsl(var(--sidebar-accent)));
  color: hsl(var(--foreground));
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.22);
}

.menu-icon {
  flex-shrink: 0;
  margin-right: 1rem;
}

.menu-text {
  opacity: 1;
  transform: translateX(0);
  transition: opacity 0.15s ease, transform 0.2s ease;
  white-space: nowrap;
  will-change: opacity, transform;
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

.menu-item-collapsed .menu-icon {
  margin-right: 0;
}
</style>
