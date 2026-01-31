<template>
  <div v-if="isAuthPage" class="h-screen overflow-hidden">
    <router-view />
  </div>
  <div v-else class="flex h-screen min-h-0 overflow-x-hidden">
    <!-- Sidebar for desktop -->
    <Sidebar
      v-if="!isMobile && !isSidebarFlyout && !(isVideoWidescreen && !isVideoSidebarOpen)"
      :routes="sidebarRoutes"
      :flyout="isVideoWidescreen"
      @requestClose="closeVideoSidebar"
    />

    <!-- Floating sidebar for flyout routes -->
    <div v-if="!isMobile && isSidebarFlyout" class="sidebar-flyout">
      <button
        class="sidebar-flyout-toggle"
        @click="toggleSidebarFlyout"
        :aria-label="isSidebarFlyoutOpen ? '关闭侧边栏' : '打开侧边栏'"
        :title="isSidebarFlyoutOpen ? '关闭侧边栏' : '打开侧边栏'"
      >
        <Bars3Icon class="h-5 w-5" />
      </button>
      <transition name="sidebar-flyout">
        <div
          v-if="isSidebarFlyoutOpen"
          class="sidebar-flyout-overlay"
          @click.self="closeSidebarFlyout"
        >
          <Sidebar
            class="sidebar-flyout-panel"
            :routes="sidebarRoutes"
            :flyout="true"
            @requestClose="closeSidebarFlyout"
          />
        </div>
      </transition>
    </div>

    <!-- Main content area -->
    <main class="flex-1 relative flex flex-col min-h-0">
      <!-- 全局搜索框 -->
      <div v-if="showGlobalSearch" class="topbar" ref="topbarRef">
        <button
          v-if="isVideoWidescreen"
          class="topbar-menu-btn"
          :aria-label="isVideoSidebarOpen ? '关闭侧边栏' : '打开侧边栏'"
          :title="isVideoSidebarOpen ? '关闭侧边栏' : '打开侧边栏'"
          @click="toggleSidebarFlyout"
        >
          <Bars3Icon class="h-5 w-5" />
        </button>
        <GlobalSearchBar
          ref="globalSearchBar"
          v-model="searchQuery"
          :placeholder="searchPlaceholder"
          @search="handleGlobalSearch"
          @clear="handleGlobalSearchClear"
        />
      </div>

      <!-- 页面内容容器 -->
      <div class="page-container flex-1 relative min-h-0">
        <div class="content-container absolute inset-0" ref="contentContainerRef" :class="contentScrollClass">
          <router-view v-slot="{ Component }">
            <keep-alive :include="['LatestVideos', 'Subscribed']">
              <component :is="Component" :key="routeCacheKey" />
            </keep-alive>
          </router-view>
        </div>
        <!-- 全局同步中心 -->
        <RefreshCenter />
      </div>
    </main>

    <!-- Mobile navigation -->
    <MobileNav v-if="isMobile" :routes="mobileRoutes" />
  </div>
</template>

<script setup>
import { provide, ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import mitt from 'mitt';
import MobileNav from '@/components/layout/MobileNav.vue';
import Sidebar from '@/components/layout/Sidebar.vue';
import GlobalSearchBar from '@/components/layout/GlobalSearchBar.vue';
import RefreshCenter from '@/components/layout/RefreshCenter.vue';
import { HomeIcon, BookmarkIcon, CogIcon, ClockIcon, DocumentTextIcon, ChartBarIcon, Bars3Icon } from '@heroicons/vue/24/outline';
import { isMobile } from "./composables/useMobile.js";
import { useRoute } from 'vue-router';
import { useUser } from './composables/useUser';
import { useGlobalSearch } from './composables/useGlobalSearch';
import { useSystemConfig } from './composables/useSystemConfig';
import { Logger } from '@/utils/logger'

const route = useRoute();
const emitter = mitt();
provide('emitter', emitter);

const contentContainerRef = ref(null);
const topbarRef = ref(null);
let contentResizeObserver = null;


const isAuthPage = computed(() => {
  return ['/login', '/register'].includes(route.path);
});

const sidebarMeta = computed(() => {
  return route.meta?.sidebar || { mode: 'fixed', defaultOpen: false };
});

const isSidebarFlyout = computed(() => {
  return sidebarMeta.value?.mode === 'flyout';
});

const isSidebarFlyoutOpen = ref(false);
const closeVideoSidebar = () => {
  isVideoSidebarOpen.value = false;
};

const openSidebarFlyout = () => {
  isSidebarFlyoutOpen.value = true;
};

const closeSidebarFlyout = () => {
  isSidebarFlyoutOpen.value = false;
};

const toggleSidebarFlyout = () => {
  if (isVideoWidescreen.value) {
    isVideoSidebarOpen.value = !isVideoSidebarOpen.value;
    return;
  }
  isSidebarFlyoutOpen.value = !isSidebarFlyoutOpen.value;
};

// 控制全局搜索框显示：由路由 meta 控制
const showGlobalSearch = computed(() => {
  return !isAuthPage.value && !!route.meta?.showSearch;
});

const globalSearchBar = ref(null);
const { searchQuery, searchPlaceholder, handleSearch: handleGlobalSearch, handleClear: handleGlobalSearchClear } = useGlobalSearch(emitter);

const routes = ref([
  { path: '/', name: '首页', icon: HomeIcon },
  { path: '/subscribed', name: '订阅', icon: BookmarkIcon },
  { path: '/history', name: '历史', icon: ClockIcon },
  { path: '/monitoring', name: '监控', icon: ChartBarIcon },
  { path: '/logs', name: '日志', icon: DocumentTextIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);

onUnmounted(() => {
  emitter.all.clear();
});

const sidebarRoutes = computed(() => {
  return routes.value.filter(route => !route.path.includes('/settings'))
})

const mobileRoutes = computed(() => {
  return routes.value
})

const { getCurrentUser } = useUser();
const { loadSystemConfig } = useSystemConfig();

const isVideoWidescreen = ref(false);
const isVideoSidebarOpen = ref(true);


// 是否允许当前页面滚动（如视频播放页）
const isScrollablePage = computed(() => {
  return !!route.meta?.scrollable;
});

const contentScrollClass = computed(() => {
  if (!isScrollablePage.value) return 'overflow-hidden'
  return route.meta?.hideScrollbar ? 'scrollbar-hide overflow-y-auto' : 'scrollbar overflow-y-auto'
})

const syncAppTopbarHeight = async () => {
  await nextTick();
  const root = document.documentElement;

  const contentContainer = contentContainerRef.value;
  if (contentContainer) {
    const height = Math.ceil(contentContainer.getBoundingClientRect().height);
    root.style.setProperty('--app-content-height', `${height}px`);
  }

  if (!showGlobalSearch.value) {
    root.style.setProperty('--app-topbar-height', '0px');
    return;
  }

  const bar = topbarRef.value || globalSearchBar.value?.$el || document.querySelector('.global-search-bar');
  if (!bar) {
    root.style.setProperty('--app-topbar-height', '0px');
    return;
  }

  const height = Math.ceil(bar.getBoundingClientRect().height);
  root.style.setProperty('--app-topbar-height', `${height}px`);
};

const routeCacheKey = computed(() => {
  if (route.params.id) {
    return `subscription-${route.params.id}`;
  }
  if (route.path.startsWith('/videos')) {
    return 'videos';
  }
  return route.name || route.path;
});


watch(isScrollablePage, (newVal, oldVal) => {
  if (oldVal && !newVal && contentContainerRef.value) {
    contentContainerRef.value.scrollTop = 0;
  }
});

watch(
  () => route.meta?.sidebar,
  (sidebar) => {
    if (sidebar?.mode === 'flyout') {
      isSidebarFlyoutOpen.value = !!sidebar.defaultOpen;
    } else {
      isSidebarFlyoutOpen.value = false;
    }
  },
  { immediate: true }
);

emitter.on('videoWidescreenStateChanged', (enabled) => {
  isVideoWidescreen.value = !!enabled;
  if (isVideoWidescreen.value) {
    isSidebarFlyoutOpen.value = false;
    isVideoSidebarOpen.value = false;
  } else {
    isVideoSidebarOpen.value = true;
  }
});

watch(showGlobalSearch, () => {
  syncAppTopbarHeight();
});

watch(() => route.path, () => {
  syncAppTopbarHeight();
});

watch(() => route.name, (newRoute) => {
  if (sidebarMeta.value?.mode !== 'flyout') {
    isSidebarFlyoutOpen.value = false;
  }
});

onMounted(async () => {
  if (localStorage.getItem('token')) {
    const result = await getCurrentUser();
    if (result.error) {
      Logger.error('Failed to get user info', result.error);
    }
  }
  
  // 加载系统配置
  const configResult = await loadSystemConfig();
  if (configResult.error) {
    Logger.error('Failed to load system config', configResult.error);
  }

  syncAppTopbarHeight();

  const handleResize = () => syncAppTopbarHeight();
  window.addEventListener('resize', handleResize);

  if (contentContainerRef.value && !contentResizeObserver) {
    contentResizeObserver = new ResizeObserver(() => {
      syncAppTopbarHeight();
    });
    contentResizeObserver.observe(contentContainerRef.value);
  }

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    if (contentResizeObserver) {
      contentResizeObserver.disconnect();
      contentResizeObserver = null;
    }
  });
});


</script>

<style>
html, body {
  @apply h-full overflow-hidden;
  overscroll-behavior: none;
}

.topbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--bg-primary);
  padding: 0.75rem 1rem;
}

.topbar .global-search-bar {
  flex: 1;
  padding: 0;
  background: transparent;
}

.topbar-menu-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  color: var(--text-primary);
  transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.topbar-menu-btn:hover {
  background: var(--bg-hover);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.22);
  transform: translateY(-1px);
}

.topbar-menu-btn:active {
  transform: translateY(0);
}

body {
  font-family: var(--font-sans);
  @apply bg-bg-primary text-text-primary;
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-sans);
}

.video-widescreen .sidebar {
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  width: var(--sidebar-width, 12rem);
  flex: 0 0 0;
  z-index: 60;
}

.video-widescreen .sidebar.collapsed {
  width: var(--sidebar-width, 12rem);
}

.video-widescreen .sidebar .toggle-btn {
  transform: none;
}

.sidebar-flyout {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 40;
}

.sidebar-flyout-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  background: transparent;
  color: var(--text-primary);
  box-shadow: none;
  transition: transform 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.sidebar-flyout-toggle:hover {
  background: var(--bg-hover);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.22);
  transform: translateY(-1px);
}

.sidebar-flyout-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 10, 10, 0.45);
  /* No backdrop blur: keep overlay simple and fast */
  z-index: 50;
  display: flex;
  align-items: stretch;
}

.sidebar-flyout-panel {
  height: 100%;
  max-width: 18rem;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
}

.sidebar-flyout-enter-active,
.sidebar-flyout-leave-active {
  transition: opacity 0.2s ease;
}

.sidebar-flyout-enter-from,
.sidebar-flyout-leave-to {
  opacity: 0;
}

.sidebar-flyout-enter-to,
.sidebar-flyout-leave-from {
  opacity: 1;
}
</style>
