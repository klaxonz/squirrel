<template>
  <nav class="mobile-nav-shell">
    <ul class="mobile-nav-list">
      <li v-for="route in routes" :key="route.path">
        <router-link
          :to="route.path"
          class="mobile-nav-link"
          :class="{ 'mobile-nav-link--active': isNavigationItemActive(route, $route) }"
        >
          <span class="mobile-nav-link__icon">
            <component :is="route.icon" class="w-5 h-5" />
          </span>
          <span class="mobile-nav-link__label">{{ route.mobileLabel || route.name }}</span>
        </router-link>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { isNavigationItemActive } from '@/constants/sidebar'

defineProps({
  routes: {
    type: Array,
    required: true
  }
});
</script>

<style scoped>
.mobile-nav-shell {
  position: fixed;
  left: 0.6rem;
  right: 0.6rem;
  bottom: 0.35rem;
  z-index: 45;
}

.mobile-nav-list {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  min-height: calc(var(--mobile-nav-height) - 1.4rem);
  margin: 0;
  padding: 0.35rem;
  list-style: none;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1rem;
  background: hsl(var(--card) / 0.98);
  box-shadow: var(--shadow-lg);
  overflow-x: auto;
}

.mobile-nav-list li {
  flex: 0 0 auto;
}

.mobile-nav-link {
  display: flex;
  min-width: 4.25rem;
  min-height: 2.75rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  padding: 0 0.5rem;
  border-radius: 0.75rem;
  color: hsl(var(--muted-foreground));
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  border: 1px solid transparent;
}

.mobile-nav-link--active {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.92);
  border-color: hsl(var(--border));
}

.mobile-nav-link__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.mobile-nav-link__label {
  font-size: 0.6875rem;
  font-weight: 500;
  white-space: nowrap;
}

@media (max-width: 420px) {
  .mobile-nav-shell {
    left: 0.5rem;
    right: 0.5rem;
    bottom: 0.25rem;
  }

  .mobile-nav-list {
    border-radius: 0.875rem;
  }
}
</style>
