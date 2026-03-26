<template>
  <router-link
    :to="item.path"
    class="menu-item"
    :class="[
      isActive ? 'menu-item-active' : 'menu-item-inactive',
      { 'menu-item-collapsed': isCollapsed }
    ]"
  >
    <component :is="item.icon" class="menu-icon w-4 h-4" />
    <span class="menu-text">
      <span class="menu-text__label">{{ item.name }}</span>
    </span>
  </router-link>
</template>

<script setup>
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
  gap: 0.45rem;
  min-height: 1.95rem;
  padding: 0 0.5rem;
  margin-bottom: 0.15rem;
  color: hsl(var(--sidebar-foreground));
  border-radius: 0.55rem;
  border: 1px solid transparent;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.menu-item-inactive:hover {
  background-color: hsl(var(--sidebar-accent) / 0.72);
  border-color: hsl(var(--border) / 0.68);
}

.menu-item-active {
  background: hsl(var(--accent) / 0.9);
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
}

.menu-icon {
  flex-shrink: 0;
  color: currentColor;
}

.menu-text {
  opacity: 1;
  transform: translateX(0);
  transition: opacity 0.15s ease, transform 0.2s ease;
  white-space: nowrap;
  will-change: opacity, transform;
  min-width: 0;
}

.menu-text__label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 500;
}

.menu-item-collapsed .menu-text {
  display: none;
}

.menu-item-collapsed {
  width: 2.35rem;
  min-height: 2.35rem;
  margin-left: auto;
  margin-right: auto;
  padding: 0;
  gap: 0;
  justify-content: center;
}
</style>
