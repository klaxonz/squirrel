<template>
  <div class="app-root" :class="{ 'app-root--desktop': isDesktopShell }">
    <header
      v-if="isDesktopShell"
      :class="['desktop-titlebar', `desktop-titlebar--${desktopPlatform}`]"
    >
      <div class="desktop-titlebar__drag">
        <div class="desktop-titlebar__identity"></div>
        <div class="desktop-titlebar__trailing">
          <div
            v-if="showDesktopWindowControls"
            class="desktop-window-controls"
            role="group"
            aria-label="窗口控制"
          >
            <button
              type="button"
              class="desktop-window-controls__button"
              aria-label="最小化窗口"
              title="最小化"
              @click="minimizeDesktopWindow"
            >
              <svg viewBox="0 0 12 12" class="desktop-window-controls__icon" aria-hidden="true">
                <path d="M2 8.25h8" />
              </svg>
            </button>
            <button
              type="button"
              class="desktop-window-controls__button"
              :aria-label="isDesktopWindowMaximized ? '还原窗口' : '最大化窗口'"
              :title="isDesktopWindowMaximized ? '还原' : '最大化'"
              @click="toggleDesktopWindowMaximize"
            >
              <svg
                v-if="isDesktopWindowMaximized"
                viewBox="0 0 12 12"
                class="desktop-window-controls__icon"
                aria-hidden="true"
              >
                <path d="M4.25 2.25h5.5v5.5" />
                <path d="M2.25 4.25h5.5v5.5h-5.5z" />
              </svg>
              <svg
                v-else
                viewBox="0 0 12 12"
                class="desktop-window-controls__icon"
                aria-hidden="true"
              >
                <path d="M2.25 2.25h7.5v7.5h-7.5z" />
              </svg>
            </button>
            <button
              type="button"
              class="desktop-window-controls__button desktop-window-controls__button--close"
              aria-label="关闭窗口"
              title="关闭"
              @click="closeDesktopWindow"
            >
              <svg viewBox="0 0 12 12" class="desktop-window-controls__icon" aria-hidden="true">
                <path d="M3 3l6 6" />
                <path d="M9 3l-6 6" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>

    <div v-if="isAuthPage" :class="isDesktopShell ? 'app-auth-shell' : 'h-screen overflow-hidden'">
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
              <div
                v-if="showGlobalSearch"
                :class="['minimal-header', { 'minimal-header--compact': isVideoPlayRoute }]"
              >
                <div :class="['header-left-spacer', { 'is-compact': isVideoPlayRoute }]"></div>
                <GlobalSearchBar
                  ref="globalSearchBar"
                  v-model="searchQuery"
                  :class="['minimal-search', { 'minimal-search--compact': isVideoPlayRoute }]"
                  :placeholder="searchPlaceholder"
                  @search="handleGlobalSearch"
                  @clear="handleGlobalSearchClear"
                />
                <div :class="['header-right-spacer', { 'is-compact': isVideoPlayRoute }]"></div>
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
  </div>
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
import { useAppTheme } from './composables/useAppTheme'
import { Logger } from '@/utils/logger'

const route = useRoute()
const emitter = mitt()
provide('emitter', emitter)

// Initialize theme
useAppTheme()

const APP_TITLE = 'Squirrel'
const desktopBridge = typeof window === 'undefined' ? null : window.desktopApp
const isDesktopShell = desktopBridge?.isDesktop === true
const desktopPlatform = String(desktopBridge?.platform || 'desktop').toLowerCase()
const DESKTOP_WINDOW_CONTROL_PLATFORMS = new Set(['win32', 'linux'])
const ROUTE_TITLES = {
  AllVideos: '全部视频',
  UnreadVideos: '未读视频',
  ReadVideos: '已读视频',
  PreviewVideos: '预览视频',
  LikedVideos: '喜欢的视频',
  LaterVideos: '稍后再看',
  Subscribed: '订阅',
  Settings: '系统设置',
  Plugins: '插件管理',
  Logs: '日志查看器',
  SyncCenter: '同步中心',
  ScheduledTasks: '计划任务',
  SubscriptionAllVideos: '订阅视频',
  SubscriptionUnreadVideos: '订阅未读',
  SubscriptionReadVideos: '订阅已读',
  SubscriptionPreviewVideos: '订阅预览',
  SubscriptionLikedVideos: '订阅喜欢',
  SubscriptionLaterVideos: '订阅稍后看',
  History: '历史记录',
  VideoPlay: '视频播放',
  Login: '登录',
  Register: '注册',
}

const contentContainerRef = ref(null)
const topbarRef = ref(null)
const globalSearchBar = ref(null)
const desktopPageTitle = ref('桌面应用')
const isDesktopWindowMaximized = ref(false)
let contentResizeObserver = null
let titleObserver = null
let stopDesktopWindowStateSync = null

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
const isVideoPlayRoute = computed(() => route.name === 'VideoPlay')
const showShellHeader = computed(() => showGlobalSearch.value || isVideoWidescreen.value)
const isCenteredSearchPage = computed(() => ['home', 'subscribed', 'history'].includes(String(route.meta?.search || '')))
const isScrollablePage = computed(() => !!route.meta?.scrollable)
const desktopPlatformLabel = computed(() => {
  const platformMap = {
    win32: 'Windows',
    darwin: 'macOS',
    linux: 'Linux',
  }

  return platformMap[desktopPlatform] || 'Desktop'
})
const desktopChromeContext = computed(() => {
  if (isAuthPage.value) {
    return '身份认证'
  }
  if (isVideoPlayRoute.value) {
    return '沉浸播放'
  }
  if (route.name === 'Settings') {
    return '系统配置'
  }
  return '工作台'
})
const showDesktopWindowControls = computed(() => {
  return isDesktopShell && DESKTOP_WINDOW_CONTROL_PLATFORMS.has(desktopPlatform)
})

const contentScrollClass = computed(() => {
  if (!isScrollablePage.value) {
    return 'overflow-hidden'
  }
  return route.meta?.hideScrollbar ? 'scrollbar-hide overflow-y-auto' : 'scrollbar overflow-y-auto'
})

const resolveRouteTitle = () => {
  const routeName = String(route.name || '')
  return ROUTE_TITLES[routeName] || '桌面应用'
}

const updateDesktopPageTitle = (rawTitle) => {
  const normalizedTitle = String(rawTitle || '').replace(new RegExp(`\\s+-\\s+${APP_TITLE}$`), '').trim()
  desktopPageTitle.value = normalizedTitle || resolveRouteTitle()
}

const syncDocumentTitle = () => {
  const nextTitle = `${resolveRouteTitle()} - ${APP_TITLE}`
  document.title = nextTitle
  updateDesktopPageTitle(nextTitle)
}

const applyDesktopWindowState = (state) => {
  isDesktopWindowMaximized.value = state?.isMaximized === true
}

const syncDesktopWindowState = async () => {
  if (!showDesktopWindowControls.value || typeof desktopBridge?.getWindowState !== 'function') {
    return
  }

  try {
    applyDesktopWindowState(await desktopBridge.getWindowState())
  } catch (error) {
    Logger.warn('Failed to sync desktop window state', error)
  }
}

const minimizeDesktopWindow = async () => {
  if (typeof desktopBridge?.minimizeWindow !== 'function') {
    return
  }

  try {
    await desktopBridge.minimizeWindow()
  } catch (error) {
    Logger.warn('Failed to minimize desktop window', error)
  }
}

const toggleDesktopWindowMaximize = async () => {
  if (typeof desktopBridge?.toggleMaximizeWindow !== 'function') {
    return
  }

  try {
    applyDesktopWindowState(await desktopBridge.toggleMaximizeWindow())
  } catch (error) {
    Logger.warn('Failed to toggle desktop maximize state', error)
  }
}

const closeDesktopWindow = async () => {
  if (typeof desktopBridge?.closeWindow !== 'function') {
    return
  }

  try {
    await desktopBridge.closeWindow()
  } catch (error) {
    Logger.warn('Failed to close desktop window', error)
  }
}

const startDesktopTitleObserver = () => {
  if (!isDesktopShell) {
    return
  }

  const titleElement = document.head.querySelector('title')
  if (!titleElement) {
    updateDesktopPageTitle(document.title)
    return
  }

  titleObserver = new MutationObserver(() => {
    updateDesktopPageTitle(titleElement.textContent || document.title)
  })
  titleObserver.observe(titleElement, { childList: true, characterData: true, subtree: true })
  updateDesktopPageTitle(titleElement.textContent || document.title)
}

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

const handleWindowResize = () => {
  void syncAppTopbarHeight()
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
watch(() => route.fullPath, syncDocumentTitle, { immediate: true })

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

  startDesktopTitleObserver()
  if (showDesktopWindowControls.value) {
    if (typeof desktopBridge?.onWindowStateChange === 'function') {
      stopDesktopWindowStateSync = desktopBridge.onWindowStateChange((state) => {
        applyDesktopWindowState(state)
      })
    }
    await syncDesktopWindowState()
  }
  syncAppTopbarHeight()
  window.addEventListener('resize', handleWindowResize)

  if (contentContainerRef.value && !contentResizeObserver) {
    contentResizeObserver = new ResizeObserver(() => {
      syncAppTopbarHeight()
    })
    contentResizeObserver.observe(contentContainerRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  if (contentResizeObserver) {
    contentResizeObserver.disconnect()
    contentResizeObserver = null
  }
  if (titleObserver) {
    titleObserver.disconnect()
    titleObserver = null
  }
  if (typeof stopDesktopWindowStateSync === 'function') {
    stopDesktopWindowStateSync()
    stopDesktopWindowStateSync = null
  }
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

.app-root {
  height: 100vh;
  overflow: hidden;
}

.app-root--desktop {
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top, var(--app-bg-gradient-top), transparent 32%),
    linear-gradient(180deg, var(--app-bg-gradient-bottom-start) 0%, var(--app-bg-gradient-bottom-end) 56%);
}

.app-auth-shell {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.desktop-titlebar {
  position: relative;
  z-index: 80;
  flex: 0 0 auto;
  height: 32px;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--background) / 0.95);
  backdrop-filter: blur(12px);
}

.desktop-titlebar__drag {
  display: flex;
  height: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 0.5rem 0 1rem;
  -webkit-app-region: drag;
  user-select: none;
}

.desktop-titlebar--darwin .desktop-titlebar__drag {
  padding-left: 5.5rem;
}

.desktop-titlebar__identity {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
}

.desktop-titlebar__logo {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 800;
  color: hsl(var(--primary));
  opacity: 0.9;
  margin-right: 0.85rem;
  padding: 0.1rem 0.35rem;
  border: 1px solid hsl(var(--primary) / 0.25);
  border-radius: 3px;
  background: hsl(var(--primary) / 0.03);
  letter-spacing: 0.02em;
}

.desktop-titlebar__headline {
  display: flex;
  min-width: 0;
  align-items: center;
}

.desktop-titlebar__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--muted-foreground));
  font-size: 0.725rem;
  font-weight: 500;
  letter-spacing: 0.01em;
}

.desktop-titlebar__trailing {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
}

.desktop-window-controls {
  display: inline-flex;
  align-items: center;
  gap: 1px;
  -webkit-app-region: no-drag;
}

.desktop-window-controls__button {
  display: inline-flex;
  width: 2.5rem;
  height: 32px;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 0;
  color: hsl(var(--muted-foreground));
  transition: all 0.2s ease;
}

.desktop-window-controls__button:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.desktop-window-controls__button:active {
  background: hsl(var(--accent) / 0.8);
}

.desktop-window-controls__button--close:hover {
  background: #e81123;
  color: #fff;
}

.desktop-window-controls__icon {
  width: 10px;
  height: 10px;
}

.desktop-window-controls__icon path {
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.15;
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
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: hsl(var(--background));
}

.app-root--desktop .app-shell {
  flex: 1 1 auto;
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
  padding: 1.5rem 2rem 1rem 2rem;
  background: linear-gradient(to bottom, hsl(var(--background)) 0%, hsl(var(--background) / 0.8) 60%, transparent 100%);
  pointer-events: none;
}

.minimal-header--compact {
  padding: 0.5rem 1rem;
  background: linear-gradient(to bottom, hsl(var(--background)) 0%, hsl(var(--background) / 0.92) 72%, hsl(var(--background) / 0.55) 100%);
}

.header-left-spacer {
  width: 120px;
  flex-shrink: 0;
}

.header-right-spacer {
  width: 120px;
  flex-shrink: 0;
}

.header-left-spacer.is-compact,
.header-right-spacer.is-compact {
  width: 3rem;
}

.minimal-search {
  width: clamp(20rem, calc(100vw - 18rem), 480px);
  pointer-events: auto;
}

.minimal-search--compact {
  width: min(46rem, calc(100vw - 6rem));
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
