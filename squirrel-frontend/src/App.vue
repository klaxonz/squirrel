<template>
  <div v-if="isAuthPage" class="h-screen overflow-hidden">
    <router-view />
  </div>
  <div v-else class="flex h-screen min-h-0 overflow-x-hidden">
    <!-- Sidebar for desktop -->
    <Sidebar v-if="!isMobile" :routes="sidebarRoutes" />

    <!-- Main content area -->
    <main class="flex-1 relative flex flex-col min-h-0">
      <!-- 全局搜索框 -->
      <GlobalSearchBar
        v-if="showGlobalSearch"
        ref="globalSearchBar"
        v-model="searchQuery"
        :placeholder="searchPlaceholder"
        @search="handleGlobalSearch"
        @clear="handleGlobalSearchClear"
      />

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
import { provide, ref, onMounted, onUnmounted, computed, watch } from 'vue';
import mitt from 'mitt';
import MobileNav from './components/MobileNav.vue';
import Sidebar from './components/Sidebar.vue';
import GlobalSearchBar from './components/GlobalSearchBar.vue';
import RefreshCenter from './components/RefreshCenter.vue';
import { HomeIcon, BookmarkIcon, CogIcon, ClockIcon, DocumentTextIcon, ChartBarIcon } from '@heroicons/vue/24/outline';
import { isMobile } from "./composables/useMobile.js";
import { useRoute } from 'vue-router';
import { useUser } from './composables/useUser';
import { useGlobalSearch } from './composables/useGlobalSearch';
import { useSystemConfig } from './composables/useSystemConfig';

const route = useRoute();
const emitter = mitt();
provide('emitter', emitter);

const contentContainerRef = ref(null);

const isAuthPage = computed(() => {
  return ['/login', '/register'].includes(route.path);
});

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

// 是否允许当前页面滚动（如视频播放页）
const isScrollablePage = computed(() => {
  return !!route.meta?.scrollable;
});

const contentScrollClass = computed(() => {
  if (!isScrollablePage.value) return 'overflow-hidden'
  return route.meta?.hideScrollbar ? 'scrollbar-hide overflow-y-auto' : 'scrollbar overflow-y-auto'
})

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

onMounted(async () => {
  if (localStorage.getItem('token')) {
    try {
      await getCurrentUser();
    } catch (error) {
      console.error('Failed to get user info:', error);
    }
  }
  
  // 加载系统配置
  try {
    await loadSystemConfig();
  } catch (error) {
    console.error('Failed to load system config:', error);
  }
});

</script>

<style>
html, body {
  @apply h-full overflow-hidden;
  overscroll-behavior: none;
}

body {
  font-family: var(--font-sans);
  @apply bg-bg-primary text-text-primary;
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-sans);
}

</style>
