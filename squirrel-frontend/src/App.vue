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
        <div v-if="showGlobalSearch" class="topbar-shell" ref="topbarRef">
          <div class="topbar">
            <div class="topbar__lead">
              <button
                v-if="isVideoWidescreen"
                class="topbar-menu-btn"
                :aria-label="isVideoSidebarOpen ? '关闭侧边栏' : '打开侧边栏'"
                :title="isVideoSidebarOpen ? '关闭侧边栏' : '打开侧边栏'"
                @click="toggleSidebarFlyout"
              >
                <Bars3Icon class="h-5 w-5" />
              </button>
              <div v-if="!isMobile" class="topbar__copy">
                <span class="topbar__eyebrow">{{ searchEyebrow }}</span>
                <span class="topbar__title">{{ searchSectionTitle }}</span>
              </div>
            </div>

            <GlobalSearchBar
              ref="globalSearchBar"
              v-model="searchQuery"
              class="topbar__search"
              :placeholder="searchPlaceholder"
              @search="handleGlobalSearch"
              @clear="handleGlobalSearchClear"
            />
          </div>
        </div>

        <div class="page-container">
          <div
            ref="contentContainerRef"
            class="content-container absolute inset-0"
            :class="contentScrollClass"
          >
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
import { useUser } from './composables/useUser'
import { Logger } from '@/utils/logger'

const SEARCH_SECTION_TITLES = {
  home: '内容片库',
  subscribed: '订阅频道',
  history: '观看历史',
}

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

const { getCurrentUser } = useUser()
const { loadSystemConfig } = useSystemConfig()

const mobileRoutes = MOBILE_NAV_ITEMS

const showGlobalSearch = computed(() => !isAuthPage.value && !!route.meta?.showSearch)
const isScrollablePage = computed(() => !!route.meta?.scrollable)

const contentScrollClass = computed(() => {
  if (!isScrollablePage.value) {
    return 'overflow-hidden'
  }
  return route.meta?.hideScrollbar ? 'scrollbar-hide overflow-y-auto' : 'scrollbar overflow-y-auto'
})

const searchSectionTitle = computed(() => {
  const searchKey = route.meta?.search
  if (searchKey && SEARCH_SECTION_TITLES[searchKey]) {
    return SEARCH_SECTION_TITLES[searchKey]
  }
  return '搜索工作台'
})

const searchEyebrow = computed(() => {
  if (route.meta?.search === 'history') {
    return 'PLAYBACK DESK'
  }
  if (route.meta?.search === 'subscribed') {
    return 'SUBSCRIPTION DESK'
  }
  return 'EDITORIAL SEARCH'
})

const syncAppTopbarHeight = async () => {
  await nextTick()
  const root = document.documentElement

  const contentContainer = contentContainerRef.value
  if (contentContainer) {
    const height = Math.ceil(contentContainer.getBoundingClientRect().height)
    root.style.setProperty('--app-content-height', `${height}px`)
  }

  if (!showGlobalSearch.value) {
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

watch(showGlobalSearch, syncAppTopbarHeight)
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
  if (localStorage.getItem('token')) {
    const result = await getCurrentUser()
    if (result.error) {
      Logger.error('Failed to get user info', result.error)
    }
  }

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
  background:
    radial-gradient(circle at 0% 0%, hsl(var(--primary) / 0.08), transparent 24%),
    linear-gradient(180deg, hsl(var(--background) / 0.98), hsl(var(--background)));
}

.app-main {
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
}

.topbar-shell {
  position: relative;
  padding: 0.8rem 1rem 0.6rem;
  background:
    linear-gradient(180deg, hsl(var(--background) / 0.9), hsl(var(--background) / 0.7));
  border-bottom: 1px solid hsl(var(--border) / 0.68);
  backdrop-filter: blur(18px);
}

.topbar-shell::after {
  content: '';
  position: absolute;
  inset: auto 1rem 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, hsl(var(--primary) / 0.18), transparent);
}

.topbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  max-width: min(var(--container-max-width, 2560px), calc(100vw - 2rem));
  margin: 0 auto;
}

.topbar__lead {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-shrink: 0;
}

.topbar__copy {
  display: grid;
  gap: 0.12rem;
}

.topbar__eyebrow {
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.topbar__title {
  font-size: 0.95rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.topbar__search {
  flex: 1 1 auto;
  min-width: 0;
}

.topbar-menu-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border) / 0.78);
  background: hsl(var(--card) / 0.88);
  color: hsl(var(--foreground));
  box-shadow: 0 14px 32px hsl(var(--surface-shadow));
  transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.topbar-menu-btn:hover {
  background: hsl(var(--accent));
  box-shadow: 0 18px 40px hsl(var(--surface-shadow));
  transform: translateY(-1px);
}

.page-container {
  @apply flex-1 relative min-h-0;
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
  top: 0.9rem;
  left: 0.9rem;
  z-index: 40;
}

.sidebar-flyout-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--card) / 0.9);
  color: hsl(var(--foreground));
  box-shadow: 0 18px 40px hsl(var(--surface-shadow));
  transition: transform 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.sidebar-flyout-toggle:hover {
  background: hsl(var(--accent));
  box-shadow: 0 22px 48px hsl(var(--surface-shadow));
  transform: translateY(-1px);
}

.sidebar-flyout-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: stretch;
  background: hsl(var(--overlay));
  backdrop-filter: blur(12px);
}

.sidebar-flyout-panel {
  height: 100%;
  max-width: 19rem;
  box-shadow: 0 30px 70px hsl(var(--surface-shadow));
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
    padding: 0.7rem 0.8rem 0.55rem;
  }

  .topbar {
    gap: 0.75rem;
    max-width: calc(100vw - 1.6rem);
  }
}
</style>
