<template>
  <aside class="sidebar bg-sidebar text-sidebar-foreground h-full flex flex-col border-r border-sidebar-border/80" :class="{ collapsed: effectiveCollapsed }">
    <div class="sidebar-header">
      <router-link
        to="/"
        class="sidebar-brand"
        :class="{ 'sidebar-brand--collapsed': effectiveCollapsed }"
      >
        <span class="sidebar-brand__mark">
          <img src="/squirrel-icon.png" alt="Squirrel" class="sidebar-brand__logo">
        </span>
        <span class="sidebar-brand__copy">
          <span class="sidebar-brand__eyebrow">Content Workbench</span>
          <span class="sidebar-brand__title">Squirrel</span>
        </span>
      </router-link>

      <button
        @click="toggleCollapse"
        class="toggle-btn"
        :title="props.flyout ? '关闭侧边栏' : (effectiveCollapsed ? '展开侧边栏' : '收起侧边栏')"
      >
        <Bars3Icon
          class="h-6 w-6 text-foreground transition-transform duration-300"
          :class="{ 'rotate-180': !props.flyout && effectiveCollapsed }"
        />
      </button>
    </div>

    <nav class="sidebar-nav flex-1 overflow-y-auto py-2 scrollbar-hide">
      <div
        v-for="group in NAV_GROUPS"
        :key="group.key"
        class="sidebar-section px-2"
      >
        <p v-if="!effectiveCollapsed" class="sidebar-section__label">{{ group.label }}</p>
        <SidebarMenuItem
          v-for="item in group.items"
          :key="item.path"
          :item="item"
          :is-collapsed="effectiveCollapsed"
          :is-active="isNavigationItemActive(item, $route.path)"
        />
        <div
          v-if="group.key !== NAV_GROUPS[NAV_GROUPS.length - 1].key"
          class="sidebar-divider my-2 mx-1"
        ></div>
      </div>
    </nav>

    <div class="sidebar-footer">
      <button
        @click="handleLogout"
        class="logout-btn"
        :title="effectiveCollapsed ? '退出' : ''"
      >
        <ArrowRightOnRectangleIcon class="logout-icon w-5 h-5" />
        <span class="logout-text text-xs">退出</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch, inject, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bars3Icon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/vue/24/outline'
import { useUser } from '@/composables/useUser'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { NAV_GROUPS, isNavigationItemActive } from '@/constants/sidebar'

const route = useRoute()
const router = useRouter()
const isCollapsed = ref(false)
const emit = defineEmits(['collapse', 'requestClose'])
const props = defineProps({
  flyout: {
    type: Boolean,
    default: false,
  },
})
const emitter = inject('emitter')
const { logout } = useUser()

const effectiveCollapsed = computed(() => {
  return props.flyout ? false : isCollapsed.value
})

const toggleCollapse = () => {
  if (props.flyout) {
    emit('requestClose')
    return
  }

  if (window.innerWidth <= 768) {
    emit('requestClose')
    return
  }

  isCollapsed.value = !isCollapsed.value
  emit('collapse', isCollapsed.value)
  emitter.emit('sidebarStateChanged')
}

const handleLogout = () => {
  logout()
  router.push('/login')
}

onMounted(() => {
  isCollapsed.value = false
  emit('collapse', false)
  localStorage.setItem('sidebar-collapsed', 'false')
})


watch(route, () => {
  if (window.innerWidth <= 768) {
    isCollapsed.value = true
    emit('collapse', true)
  }
})
</script>

<style scoped>
.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.sidebar {
  width: var(--sidebar-width, 12rem);
  flex-shrink: 0;
  transition: width 0.18s ease-out;
  will-change: width;
  background: hsl(var(--sidebar));
  box-shadow: inset -1px 0 0 hsl(var(--sidebar-border) / 0.75);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width, 4rem);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-height: 3.75rem;
  padding: 0.75rem 0.625rem;
}

.sidebar-brand {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.7rem;
  color: hsl(var(--sidebar-foreground));
}

.sidebar-brand__mark {
  display: inline-flex;
  height: 2.25rem;
  width: 2.25rem;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.7);
  background: hsl(var(--background));
}

.sidebar-brand__logo {
  height: 1.5rem;
  width: 1.5rem;
  object-fit: contain;
}

.sidebar-brand__copy {
  display: grid;
  min-width: 0;
  gap: 0.1rem;
}

.sidebar-brand__eyebrow {
  font-size: 0.6rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.sidebar-brand__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.sidebar-brand--collapsed .sidebar-brand__copy {
  display: none;
}

.toggle-btn {
  display: inline-flex;
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 0.625rem;
  border: 1px solid hsl(var(--border) / 0.7);
  background: hsl(var(--background));
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.toggle-btn:hover {
  background: hsl(var(--sidebar-accent));
  border-color: hsl(var(--border));
}

.rotate-180 {
  transform: rotate(180deg);
}

.sidebar-section__label {
  margin: 0 0 0.5rem;
  padding: 0 0.625rem;
  font-size: 0.625rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.sidebar-divider {
  height: 1px;
  background: hsl(var(--sidebar-border) / 0.7);
}

.sidebar.collapsed .sidebar-divider {
  opacity: 0.5;
  margin-left: 0.5rem;
  margin-right: 0.5rem;
}

.sidebar-footer {
  padding: 0.625rem;
  border-top: 1px solid hsl(var(--border) / 0.55);
}

.logout-btn {
  display: flex;
  width: 100%;
  align-items: center;
  min-height: 2.5rem;
  padding: 0 0.75rem;
  color: hsl(var(--sidebar-foreground));
  border-radius: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.7);
  background: hsl(var(--background));
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.logout-btn:hover {
  background-color: hsl(var(--sidebar-accent) / 0.85);
  border-color: hsl(var(--border));
}

.logout-icon {
  margin-right: 0.75rem;
}

.sidebar.collapsed .logout-icon {
  margin-right: 0;
}

.logout-text {
  opacity: 1;
  transform: translateX(0);
  transition: opacity 0.15s ease, transform 0.2s ease;
  white-space: nowrap;
  will-change: opacity, transform;
}

.sidebar.collapsed .logout-text {
  opacity: 0;
  transform: translateX(-0.5rem);
  pointer-events: none;
  width: 0;
  overflow: hidden;
}

.sidebar.collapsed .logout-btn {
  padding-left: calc(var(--sidebar-collapsed-item-padding, 0.875rem) - 0.125rem);
  padding-right: calc(var(--sidebar-collapsed-item-padding, 0.875rem) - 0.125rem);
}

.sidebar.collapsed .sidebar-header,
.sidebar.collapsed .sidebar-footer {
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}
</style>
