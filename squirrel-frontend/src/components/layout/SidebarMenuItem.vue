<template>
  <router-link
    :to="item.path"
    class="sidebar-item"
    :class="{ 'sidebar-item--active': isActive }"
  >
    <component
      :is="item.icon"
      class="sidebar-item-icon"
      aria-hidden="true"
    />
    <span class="sidebar-item-label">{{ item.name }}</span>
  </router-link>
</template>

<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.sidebar-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: var(--sidebar-item-height);
  padding: 0 0.75rem;
  border-radius: var(--radius-md);
  color: hsl(var(--sidebar-foreground) / 0.6);
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: all var(--duration-fast) var(--ease-default);
}

.sidebar-item:hover {
  background: hsl(var(--sidebar-accent));
  color: hsl(var(--sidebar-foreground));
}

.sidebar-item--active {
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
  font-weight: 600;
}

.sidebar-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  border-radius: 0 2px 2px 0;
  background: hsl(var(--primary));
}

.sidebar-item-icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
}

.sidebar-item-label {
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
