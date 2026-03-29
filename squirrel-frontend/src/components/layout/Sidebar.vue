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
        <span class="logout-text-minimal">Terminate Access</span>
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

const handleLogout = () => {
  logout()
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
  padding: 1.5rem 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.logout-btn-minimal {
  width: 100%;
  padding: 0.75rem 0;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  font-size: 0.55rem;
  letter-spacing: 0.15em;
  text-align: center;
  transition: color 0.3s;
  cursor: pointer;
}

.logout-btn-minimal:hover {
  color: #ff4d00;
}
</style>
