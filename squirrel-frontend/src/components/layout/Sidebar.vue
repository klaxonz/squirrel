<template>
  <aside class="sidebar-minimal h-full flex flex-col">
    <div class="sidebar-header-minimal">
      <router-link to="/" class="sidebar-brand-minimal">SQRL</router-link>
    </div>

    <nav class="sidebar-nav-neon flex-1 overflow-y-auto py-4 scrollbar-hide">
      <div
        v-for="(group, groupIdx) in NAV_GROUPS"
        :key="group.key"
        class="sidebar-section-neon mb-6"
      >
        <div class="section-header-neon">
          <span class="section-title">{{ group.label }}</span>
          <div class="section-line"></div>
        </div>
        <SidebarMenuItem
          v-for="(item, itemIdx) in group.items"
          :key="item.path"
          :item="item"
          :index="(groupIdx * 3) + itemIdx + 1"
          :is-active="isNavigationItemActive(item, $route.path)"
        />
      </div>
    </nav>

    <div class="sidebar-footer-minimal">
      <button @click="handleLogout" class="logout-btn-minimal">
        <div class="logout-content">
          <div class="icon-wrapper">
            <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </div>
          <div class="label-wrapper">
            <span class="menu-index">99</span>
            <span class="menu-label">退出</span>
          </div>
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { inject } from 'vue'
import { useRouter } from 'vue-router'
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
.sidebar-minimal {
  width: var(--sidebar-width, 11rem);
  background: #050505;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
}

.sidebar-header-minimal {
  padding: 2rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.sidebar-brand-minimal {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.05em;
  color: #fff;
  text-decoration: none;
  opacity: 0.9;
}

.section-header-neon {
  padding: 0 1rem 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.section-title {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.15);
  text-transform: uppercase;
  white-space: nowrap;
}

.section-line {
  height: 1px;
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
}

.sidebar-nav-neon {
  padding-bottom: 2rem;
}

.sidebar-footer-minimal {
  padding: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}

.logout-btn-minimal {
  --neon-primary: #ff4d00;
  --neon-primary-glow: rgba(255, 77, 0, 0.8);
  --neon-primary-bg: rgba(255, 77, 0, 0.05);

  position: relative;
  width: 100%;
  display: flex;
  padding: 1.25rem 1rem;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  text-decoration: none;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  cursor: pointer;
  overflow: hidden;
}

.logout-btn-minimal:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.02);
}

.logout-btn-minimal:hover .menu-icon {
  transform: translateX(2px);
  color: #fff;
}

.logout-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 2;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
}

.menu-icon {
  width: 1.25rem;
  height: 1.25rem;
  transition: all 0.3s ease;
}

.label-wrapper {
  display: flex;
  flex-direction: column;
}

.menu-index {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  letter-spacing: 0.1em;
  opacity: 0.4;
  margin-bottom: -0.1rem;
}

.menu-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
</style>
