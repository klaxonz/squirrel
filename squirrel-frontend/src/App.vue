<template>
  <div v-if="isAuthPage" class="h-screen overflow-hidden">
    <router-view />
  </div>
  <TooltipProvider v-else :delay-duration="200">
    <div class="app-shell" :class="{ 'video-widescreen': isVideoWidescreen }">
      <Sidebar
        v-if="!isMobile && !isSidebarFlyout && !(isVideoWidescreen && !isVideoSidebarOpen)"
        :flyout="isVideoWidescreen"
        @requestClose="closeVideoSidebar"
      />

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
              :flyout="true"
              @requestClose="closeSidebarFlyout"
            />
          </div>
        </transition>
      </div>

      <main class="app-main">
        <div class="page-container">
          <div
            ref="contentContainerRef"
            class="content-container absolute inset-0"
            :class="contentScrollClass"
          >
            <!-- 顶部装饰栏：极简搜索（居中） + 状态 -->
            <div v-if="showGlobalSearch" class="minimal-header">
              <div class="header-left-spacer"></div>
              <GlobalSearchBar
                ref="globalSearchBar"
                v-model="searchQuery"
                class="minimal-search"
                :placeholder="searchPlaceholder"
                @search="handleGlobalSearch"
                @clear="handleGlobalSearchClear"
              />
              <div class="header-right-spacer"></div>
            </div>

            <router-view v-slot="{ Component }">
              <keep-alive :include="['LatestVideos', 'Subscribed']">
                <component :is="Component" :key="routeCacheKey" />
              </keep-alive>
            </router-view>
          </div>
          <RefreshCenter />
        </div>
      </main>

      <MobileNav v-if="isMobile" :routes="mobileRoutes" />
    </div>
  </TooltipProvider>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, provide, ref, watch } from 'vue'
import { Bars3Icon } from '@heroicons/vue/24/outline'
import mitt from 'mitt'
import { useRoute } from 'vue-router'
import GlobalSearchBar from '@/components/layout/GlobalSearchBar.vue'
import MobileNav from '@/components/layout/MobileNav.vue'
import RefreshCenter from '@/components/layout/RefreshCenter.vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import { MOBILE_NAV_ITEMS } from '@/constants/sidebar'
import { isMobile } from './composables/useMobile'
import { useGlobalSearch } from './composables/useGlobalSearch'
import { useSystemConfig } from './composables/useSystemConfig'
import { Logger } from '@/utils/logger'

const route = useRoute()
const emitter = mitt()
provide('emitter', emitter)

const contentContainerRef = ref(null)
const topbarRef = ref(null)
const globalSearchBar = ref(null)
let contentResizeObserver = null

const isAuthPage = computed(() => ['/login', '/register'].includes(route.path))

const sidebarMeta = computed(() => route.meta?.sidebar || { mode: 'fixed', defaultOpen: false })
const isSidebarFlyout = computed(() => sidebarMeta.value?.mode === 'flyout')

const isSidebarFlyoutOpen = ref(false)
const isVideoWidescreen = ref(false)
const isVideoSidebarOpen = ref(true)

const { searchQuery, searchPlaceholder, handleSearch: handleGlobalSearch, handleClear: handleGlobalSearchClear } =
  useGlobalSearch(emitter)

const { loadSystemConfig } = useSystemConfig()

const mobileRoutes = MOBILE_NAV_ITEMS

const showGlobalSearch = computed(() => !isAuthPage.value && !!route.meta?.showSearch)
const showShellHeader = computed(() => showGlobalSearch.value || isVideoWidescreen.value)
const isCenteredSearchPage = computed(() => ['home', 'subscribed', 'history'].includes(String(route.meta?.search || '')))
const isScrollablePage = computed(() => !!route.meta?.scrollable)

const contentScrollClass = computed(() => {
  if (!isScrollablePage.value) {
    return 'overflow-hidden'
  }
  return route.meta?.hideScrollbar ? 'scrollbar-hide overflow-y-auto' : 'scrollbar overflow-y-auto'
})

const syncAppTopbarHeight = async () => {
  await nextTick()
  const root = document.documentElement

  const contentContainer = contentContainerRef.value
  if (contentContainer) {
    const height = Math.ceil(contentContainer.getBoundingClientRect().height)
    root.style.setProperty('--app-content-height', `${height}px`)
  }

  if (!showShellHeader.value) {
    root.style.setProperty('--app-topbar-height', '0px')
    return
  }

  const bar = topbarRef.value || globalSearchBar.value?.$el || document.querySelector('.global-search-bar')
  if (!bar) {
    root.style.setProperty('--app-topbar-height', '0px')
    return
  }

  const height = Math.ceil(bar.getBoundingClientRect().height)
  root.style.setProperty('--app-topbar-height', `${height}px`)
}

const routeCacheKey = computed(() => {
  if (route.params.id) {
    return `subscription-${route.params.id}`
  }
  if (route.path.startsWith('/videos')) {
    return 'videos'
  }
  return route.name || route.path
})

const closeVideoSidebar = () => {
  isVideoSidebarOpen.value = false
}

const closeSidebarFlyout = () => {
  isSidebarFlyoutOpen.value = false
}

const toggleSidebarFlyout = () => {
  if (isVideoWidescreen.value) {
    isVideoSidebarOpen.value = !isVideoSidebarOpen.value
    return
  }
  isSidebarFlyoutOpen.value = !isSidebarFlyoutOpen.value
}

watch(isScrollablePage, (nextValue, previousValue) => {
  if (previousValue && !nextValue && contentContainerRef.value) {
    contentContainerRef.value.scrollTop = 0
  }
})

watch(
  () => route.meta?.sidebar,
  (sidebar) => {
    if (sidebar?.mode === 'flyout') {
      isSidebarFlyoutOpen.value = !!sidebar.defaultOpen
      return
    }
    isSidebarFlyoutOpen.value = false
  },
  { immediate: true },
)

watch(showShellHeader, syncAppTopbarHeight)
watch(() => route.path, syncAppTopbarHeight)

watch(() => route.name, () => {
  if (sidebarMeta.value?.mode !== 'flyout') {
    isSidebarFlyoutOpen.value = false
  }
})

emitter.on('videoWidescreenStateChanged', (enabled) => {
  isVideoWidescreen.value = !!enabled
  if (isVideoWidescreen.value) {
    isSidebarFlyoutOpen.value = false
    isVideoSidebarOpen.value = false
    return
  }
  isVideoSidebarOpen.value = true
})

onMounted(async () => {
  const configResult = await loadSystemConfig()
  if (configResult.error) {
    Logger.error('Failed to load system config', configResult.error)
  }

  syncAppTopbarHeight()

  const handleResize = () => syncAppTopbarHeight()
  window.addEventListener('resize', handleResize)

  if (contentContainerRef.value && !contentResizeObserver) {
    contentResizeObserver = new ResizeObserver(() => {
      syncAppTopbarHeight()
    })
    contentResizeObserver.observe(contentContainerRef.value)
  }

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    if (contentResizeObserver) {
      contentResizeObserver.disconnect()
      contentResizeObserver = null
    }
  })
})

onUnmounted(() => {
  emitter.all.clear()
})
</script>

<style>
html,
body {
  @apply h-full overflow-hidden;
  overscroll-behavior: none;
}

body {
  font-family: var(--font-sans);
  @apply bg-background text-foreground;
}

h1,
h2,
h3,
h4,
h5,
h6 {
  font-family: var(--font-sans);
}

.app-shell {
  display: flex;
  height: 100vh;
  min-height: 0;
  overflow: hidden;
  background: #050505;
}

.app-main {
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
}

/* 极简页头 */
.minimal-header {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2.5rem 2rem 1rem 2rem;
  background: linear-gradient(to bottom, #050505 0%, rgba(5, 5, 5, 0.8) 60%, transparent 100%);
  pointer-events: none;
}

.header-left-spacer {
  width: 120px;
  flex-shrink: 0;
}

.header-right-spacer {
  width: 120px;
  flex-shrink: 0;
}

.minimal-search {
  width: 320px;
  pointer-events: auto;
  transition: width 0.4s cubic-bezier(0.19, 1, 0.22, 1);
}

.minimal-search:focus-within {
  width: 480px;
}

.page-container {
  @apply flex-1 relative min-h-0;
  height: 100%;
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
  top: 0.5rem;
  left: 0.5rem;
  z-index: 40;
}

.sidebar-flyout-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 0.45rem;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.sidebar-flyout-toggle:hover {
  background: hsl(var(--accent));
  border-color: hsl(var(--border));
}

.sidebar-flyout-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: stretch;
  background: hsl(var(--overlay));
  backdrop-filter: blur(6px);
}

.sidebar-flyout-panel {
  height: 100%;
  max-width: 19rem;
  box-shadow: var(--shadow-popup);
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

@media (max-width: 767px) {
  .topbar-shell {
    padding: 0.45rem 0.65rem;
  }

  .topbar {
    gap: 0.5rem;
    max-width: calc(100vw - 1.3rem);
  }

  .topbar__lead {
    flex: 1 1 auto;
  }

  .topbar__search {
    min-width: 0;
  }

  .topbar__search--centered {
    flex: 1 1 auto;
    width: 100%;
    max-width: none;
  }
}
</style>
