<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <router-link to="/" class="sidebar-brand">SQRL</router-link>
    </div>

    <nav class="sidebar-nav flex-1 overflow-y-auto scrollbar-hide">
      <div
        v-for="group in NAV_GROUPS"
        :key="group.key"
        class="sidebar-group"
      >
        <div class="sidebar-group-label">{{ group.label }}</div>
        <SidebarMenuItem
          v-for="item in group.items"
          :key="item.path"
          :item="item"
          :is-active="isNavigationItemActive(item, $route)"
        />
      </div>
    </nav>

    <div class="sidebar-footer">
      <button @click="handleLogout" class="sidebar-logout">
        <LogOut class="sidebar-logout-icon" />
        <span class="sidebar-logout-label">退出</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { LogOut } from 'lucide-vue-next'
import { useUser } from '@/composables/useUser'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_GROUPS, isNavigationItemActive } from '@/constants/sidebar'

const router = useRouter()
const { logout } = useUser()

const handleLogout = async () => {
  await logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: hsl(var(--sidebar));
  border-right: 1px solid hsl(var(--sidebar-border) / 0.5);
}

.sidebar-header {
  padding: 1.5rem 1.25rem 1.25rem;
}

.sidebar-brand {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: hsl(var(--primary));
  text-decoration: none;
}

.sidebar-nav {
  padding: 0 0.5rem 1.5rem;
}

.sidebar-group {
  margin-bottom: 1.5rem;
}

.sidebar-group:last-child {
  margin-bottom: 0;
}

.sidebar-group-label {
  padding: 0 0.75rem;
  margin-bottom: 0.375rem;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: hsl(var(--sidebar-foreground) / 0.35);
}

.sidebar-footer {
  padding: 0.5rem;
  border-top: 1px solid hsl(var(--sidebar-border) / 0.5);
}

.sidebar-logout {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: hsl(var(--sidebar-foreground) / 0.5);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-default);
}

.sidebar-logout:hover {
  background: hsl(var(--sidebar-accent));
  color: hsl(var(--sidebar-foreground));
}

.sidebar-logout-icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
}

.sidebar-logout-label {
  line-height: 1;
}
</style>
