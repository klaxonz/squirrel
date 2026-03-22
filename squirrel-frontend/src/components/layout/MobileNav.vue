<template>
  <nav class="mobile-nav-shell">
    <ul class="mobile-nav-list">
      <li v-for="route in routes" :key="route.path">
        <router-link
          :to="route.path"
          class="mobile-nav-link"
          :class="{ 'mobile-nav-link--active': isNavigationItemActive(route, $route.path) }"
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
  left: 0.8rem;
  right: 0.8rem;
  bottom: 0.45rem;
  z-index: 45;
}

.mobile-nav-list {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem;
  min-height: calc(var(--mobile-nav-height) - 1.1rem);
  margin: 0;
  padding: 0.45rem;
  list-style: none;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1.6rem;
  background:
    linear-gradient(180deg, hsl(var(--card) / 0.94), hsl(var(--background) / 0.9));
  box-shadow: 0 24px 48px hsl(var(--surface-shadow));
  backdrop-filter: blur(18px);
}

.mobile-nav-list li {
  flex: 1 1 0;
}

.mobile-nav-link {
  display: flex;
  min-height: 3rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  border-radius: 1.2rem;
  color: hsl(var(--muted-foreground));
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.mobile-nav-link--active {
  color: hsl(var(--foreground));
  background: linear-gradient(180deg, hsl(var(--primary) / 0.16), hsl(var(--card) / 0.92));
  box-shadow: 0 14px 30px hsl(var(--surface-shadow));
}

.mobile-nav-link__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.mobile-nav-link__label {
  font-size: var(--font-size-2xs);
  font-weight: 600;
}

@media (max-width: 420px) {
  .mobile-nav-shell {
    left: 0.5rem;
    right: 0.5rem;
    bottom: 0.35rem;
  }

  .mobile-nav-list {
    border-radius: 1.3rem;
  }
}
</style>
