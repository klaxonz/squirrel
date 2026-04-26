<template>
  <nav class="mobile-nav">
    <router-link
      v-for="route in routes"
      :key="route.path"
      :to="route.path"
      class="mobile-nav-item"
      :class="{ 'mobile-nav-item--active': isNavigationItemActive(route, $route) }"
    >
      <component :is="route.icon" class="mobile-nav-item-icon" />
      <span class="mobile-nav-item-label">{{ route.mobileLabel || route.name }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { isNavigationItemActive } from '@/constants/sidebar'

defineProps({
  routes: {
    type: Array,
    required: true,
  },
})
</script>

<style scoped>
.mobile-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-fixed);
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: var(--mobile-nav-height);
  padding-bottom: env(safe-area-inset-bottom, 0);
  background: var(--glass-strong-bg);
  backdrop-filter: var(--glass-strong-blur);
  -webkit-backdrop-filter: var(--glass-strong-blur);
  border-top: 1px solid hsl(var(--border) / 0.5);
}

.mobile-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  flex: 1;
  min-width: 0;
  padding: 0.375rem 0;
  color: hsl(var(--muted-foreground));
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-default);
}

.mobile-nav-item--active {
  color: hsl(var(--primary));
}

.mobile-nav-item--active .mobile-nav-item-label {
  font-weight: 600;
}

.mobile-nav-item-icon {
  width: 1.25rem;
  height: 1.25rem;
}

.mobile-nav-item-label {
  font-size: 0.625rem;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}
</style>
