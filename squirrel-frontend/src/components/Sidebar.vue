<template>
  <div class="sidebar bg-bg-primary h-full flex flex-col" :class="{ collapsed: effectiveCollapsed }">
    <!-- 顶部菜单按钮 -->
    <div class="sidebar-header flex items-center h-14 px-3">
<button
        @click="toggleCollapse"
        class="toggle-btn p-2 hover:bg-bg-hover rounded-full transition-all duration-200"
        :title="props.flyout ? '关闭侧边栏' : (effectiveCollapsed ? '展开侧边栏' : '收起侧边栏')"
      >
        <Bars3Icon
          class="h-6 w-6 text-text-accent transition-transform duration-300"
          :class="{ 'rotate-180': !props.flyout && effectiveCollapsed }"
        />
      </button>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav flex-1 overflow-y-auto py-1 scrollbar-hide">
      <!-- 主要菜单项 -->
      <div class="px-2">
        <SidebarMenuItem
          v-for="item in MENU_ITEMS.main"
          :key="item.path"
          :item="item"
          :is-collapsed="effectiveCollapsed"
          :is-active="$route.path === item.path"
        />
      </div>

      <!-- 分割线 -->
      <div class="sidebar-divider my-2 mx-2"></div>

      <!-- 底部菜单项 -->
      <div class="px-2">
        <SidebarMenuItem
          v-for="item in MENU_ITEMS.bottom"
          :key="item.path"
          :item="item"
          :is-collapsed="effectiveCollapsed"
          :is-active="$route.path === item.path"
        />
      </div>
    </nav>

    <!-- 底部退出按钮 -->
    <div class="sidebar-footer px-2 py-1 border-t border-border-secondary">
      <button
        @click="handleLogout"
        class="logout-btn flex items-center h-10 px-3 text-text-accent rounded-lg w-full"
        :title="isCollapsed ? '退出' : ''"
      >
        <ArrowRightOnRectangleIcon class="logout-icon w-5 h-5" />
        <span class="logout-text text-xs">退出</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, inject, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bars3Icon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/vue/24/outline'
import { useUser } from '../composables/useUser'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { MENU_ITEMS } from '../constants/sidebar'

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
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width, 4rem);
}

.sidebar-header,
.sidebar-footer {
  transition: none;
}

.sidebar.collapsed .sidebar-header,
.sidebar.collapsed .sidebar-footer {
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}

.toggle-btn {
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.toggle-btn:hover {
  transform: scale(1.05);
}

.toggle-btn:active {
  transform: scale(0.95);
}

.rotate-180 {
  transform: rotate(180deg);
}

.sidebar-divider {
  opacity: 1;
  transition: opacity 0.2s ease;
}

.sidebar.collapsed .sidebar-divider {
  opacity: 0.5;
  margin-left: 0.5rem;
  margin-right: 0.5rem;
}

.logout-btn {
  transition: background-color 0.2s ease;
}

.logout-btn:hover {
  background-color: var(--bg-hover);
}

.logout-icon {
  margin-right: 1rem;
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
  padding-left: var(--sidebar-collapsed-item-padding, 0.875rem);
  padding-right: var(--sidebar-collapsed-item-padding, 0.875rem);
}
</style>
