<template>
  <header class="app-header">
    <!-- ── Left cluster: history controls + page title ── -->
    <div class="app-header__lead">
      <div class="app-header__history" role="group" aria-label="页面导航">
        <div
          class="app-header__nav-wrap"
          @mouseenter="openBackMenu"
          @mouseleave="scheduleCloseMenu('back')"
        >
          <button
            type="button"
            class="app-header__nav-btn"
            :disabled="!canGoBack"
            :title="canGoBack ? `返回 ${backTooltipLabel}` : '已是第一页'"
            aria-label="返回上一页"
            @click="handleBack"
          >
            <AppIcon name="chevronLeft" class="size-[15px]" />
          </button>
          <Transition name="header-menu">
            <ul
              v-if="backMenuOpen && backCandidates.length > 0"
              class="app-header__menu app-header__menu--back"
              role="menu"
              @mouseenter="cancelCloseMenu"
              @mouseleave="scheduleCloseMenu('back')"
            >
              <li v-for="entry in backCandidates" :key="entry.id">
                <button
                  type="button"
                  class="app-header__menu-item"
                  role="menuitem"
                  @click="jumpTo(entry.id)"
                >
                  <AppIcon name="chevronLeft" class="size-3 opacity-60" />
                  <span class="truncate">{{ entry.title || entry.sectionLabel || entry.fullPath }}</span>
                </button>
              </li>
            </ul>
          </Transition>
        </div>

        <div
          class="app-header__nav-wrap"
          @mouseenter="openForwardMenu"
          @mouseleave="scheduleCloseMenu('forward')"
        >
          <button
            type="button"
            class="app-header__nav-btn"
            :disabled="!canGoForward"
            :title="canGoForward ? '前进' : '已是最新页面'"
            aria-label="前进到下一页"
            @click="handleForward"
          >
            <AppIcon name="chevronRight" class="size-[15px]" />
          </button>
          <Transition name="header-menu">
            <ul
              v-if="forwardMenuOpen && forwardCandidates.length > 0"
              class="app-header__menu app-header__menu--forward"
              role="menu"
              @mouseenter="cancelCloseMenu"
              @mouseleave="scheduleCloseMenu('forward')"
            >
              <li v-for="entry in forwardCandidates" :key="entry.id">
                <button
                  type="button"
                  class="app-header__menu-item"
                  role="menuitem"
                  @click="jumpTo(entry.id)"
                >
                  <AppIcon name="chevronRight" class="size-3 opacity-60" />
                  <span class="truncate">{{ entry.title || entry.sectionLabel || entry.fullPath }}</span>
                </button>
              </li>
            </ul>
          </Transition>
        </div>
      </div>

      <div class="app-header__title" :title="pageTitle">
        <h1 class="app-header__page-title">{{ pageTitle }}</h1>
      </div>
    </div>

    <!-- ── Center: search bar (when applicable) ── -->
    <div class="app-header__center">
      <Transition name="fade" mode="out-in">
        <div v-if="showSearch" key="search" class="app-header__search-wrap">
          <GlobalSearchBar
            class="app-header__search"
            :placeholder="String(route.meta.searchPlaceholder || '搜索或输入命令...')"
            :suggestion-scope="String(route.meta.search || 'home')"
            :search-modes="showVideoSearchMode ? searchModeOptions : []"
            :active-search-mode="videoSearchMode"
            :search-redirect-name="searchRedirectName"
            @search-mode-change="setVideoSearchMode"
          />
        </div>
        <div v-else key="spacer" class="app-header__spacer" />
      </Transition>
    </div>

    <!-- ── Right: user menu ── -->
    <div class="app-header__actions">
      <div
        class="app-header__user"
        role="button"
        tabindex="0"
        :title="`${userDisplayName} — 个人资料`"
        @click="goToProfile"
        @keydown.enter.prevent="goToProfile"
        @keydown.space.prevent="goToProfile"
      >
        <div class="app-header__avatar">
          <template v-if="userInitial">{{ userInitial }}</template>
          <AppIcon v-else name="user" class="size-3.5" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { resolveRouteContext } from '@/shared/constants/sidebar'
import AppIcon from '@/shared/icons/AppIcon.vue'
import GlobalSearchBar from '@/shared/components/layout/GlobalSearchBar.vue'
import { useUIStore } from '@/shared/stores/ui'
import { useUserStore } from '@/shared/stores/user'

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()
const userStore = useUserStore()
const nav = useNavigationHistory()

const userDisplayName = computed(() => {
  if (!userStore.currentUser) return '未登录'
  return userStore.currentUser.nickname || '用户'
})
const userInitial = computed(() => {
  const name = userDisplayName.value
  return name && name !== '未登录' ? name.charAt(0) : ''
})

const goToProfile = () => {
  router.push('/profile')
}

// ── Search ──
const showSearch = computed(() => !!route.meta?.showSearch)
const { isDesktop: isDesktopEnv } = useDesktopBridge()
const isVideosRoute = computed(() => route.matched.some((record) => record.name === 'VideosView'))
const showVideoSearchMode = computed(() => {
  return isDesktopEnv()
    && (
      route.matched.some((record) => record.name === 'HomeView')
      || isVideosRoute.value
      || route.name === 'VideoPlay'
    )
})
const videoSearchMode = computed(() => {
  if (isVideosRoute.value) return route.query.mode === 'remote' ? 'remote' : 'local'
  return uiStore.homeSearchMode
})
const searchRedirectName = computed(() => (
  showVideoSearchMode.value && !isVideosRoute.value
    ? 'AllVideos'
    : isVideosRoute.value
      ? String(route.name || 'AllVideos')
      : String(route.meta.searchRedirectName || '')
))
const searchModeOptions = [
  { value: 'local', label: '本地' },
  { value: 'remote', label: '远端' },
] as const

function setVideoSearchMode(mode: 'local' | 'remote') {
  uiStore.setHomeSearchMode(mode)
  if (!isVideosRoute.value) return
  const query = { ...route.query }
  if (mode === 'remote') query.mode = 'remote'
  else {
    delete query.mode
    delete query.site
  }
  router.replace({ query })
}

// ── Title ──
// Header 永远只显示当前页标题；祖先面包屑（section）已经在左侧 Sidebar 里高亮，
// 在 header 里再显示一次会变成视觉噪音（"视频 / 全部视频"这种重复）。
const routeContext = computed(() => resolveRouteContext(route))
const pageTitle = computed(() => routeContext.value.pageTitle)

// ── History controls ──
const canGoBack = computed(() => nav.canGoBack.value)
const canGoForward = computed(() => nav.canGoForward.value)
const backCandidates = computed(() => nav.backCandidates.value)
const forwardCandidates = computed(() => nav.forwardCandidates.value)
const backTooltipLabel = computed(() => {
  const list = backCandidates.value
  // 栈里 currentIndex - 1 才是"上一页"，对应列表的最后一个元素（listBackCandidates
  // 是从近到远反序）。
  const last = list[list.length - 1]
  return last?.title || last?.sectionLabel || '上一页'
})

function handleBack() {
  void nav.goBack()
}
function handleForward() {
  void nav.goForward()
}
function jumpTo(entryId: string) {
  closeAllMenus()
  nav.jumpTo(entryId)
}

// ── Hover menus ──
const backMenuOpen = ref(false)
const forwardMenuOpen = ref(false)
let closeTimer: ReturnType<typeof setTimeout> | null = null

function openBackMenu() {
  if (!backCandidates.value.length) return
  cancelCloseMenu()
  backMenuOpen.value = true
  forwardMenuOpen.value = false
}
function openForwardMenu() {
  if (!forwardCandidates.value.length) return
  cancelCloseMenu()
  forwardMenuOpen.value = true
  backMenuOpen.value = false
}
function scheduleCloseMenu(_which: 'back' | 'forward') {
  if (closeTimer) clearTimeout(closeTimer)
  closeTimer = setTimeout(closeAllMenus, 220)
}
function cancelCloseMenu() {
  if (closeTimer) {
    clearTimeout(closeTimer)
    closeTimer = null
  }
}
function closeAllMenus() {
  backMenuOpen.value = false
  forwardMenuOpen.value = false
  if (closeTimer) {
    clearTimeout(closeTimer)
    closeTimer = null
  }
}
</script>

<style scoped>
.app-header {
  height: 3.25rem; /* 52px */
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.875rem; /* 14px */
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--background) / 0.85);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  user-select: none;
}

/* ── Left cluster ── */
.app-header__lead {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 0 1 auto;
  min-width: 0;
  max-width: 40%;
}

.app-header__history {
  display: inline-flex;
  align-items: center;
  gap: 1px;
  flex-shrink: 0;
}

.app-header__nav-wrap {
  position: relative;
  display: inline-flex;
}

.app-header__nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;  /* 28px */
  height: 1.75rem; /* 28px */
  border-radius: 999px;
  border: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition:
    background-color 140ms cubic-bezier(0.4, 0, 0.2, 1),
    color 140ms cubic-bezier(0.4, 0, 0.2, 1),
    transform 140ms cubic-bezier(0.4, 0, 0.2, 1);
}
.app-header__nav-btn:not(:disabled):hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}
.app-header__nav-btn:not(:disabled):active {
  transform: scale(0.92);
}
.app-header__nav-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.app-header__nav-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.55);
}

.app-header__menu {
  position: absolute;
  top: calc(100% + 6px);
  min-width: 16rem;
  max-width: 24rem;
  max-height: 20rem;
  overflow-y: auto;
  padding: 0.3rem;
  list-style: none;
  margin: 0;
  background: hsl(var(--popover));
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: 10px;
  box-shadow:
    0 1px 2px hsl(var(--foreground) / 0.06),
    0 8px 24px hsl(var(--foreground) / 0.14),
    0 24px 56px hsl(var(--foreground) / 0.10);
  z-index: var(--z-popover, 1100);
}
.app-header__menu--back { left: 0; }
.app-header__menu--forward { left: 0; }

.app-header__menu-item {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
  padding: 0.45rem 0.6rem;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: hsl(var(--foreground) / 0.88);
  font-size: 0.8125rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background-color 100ms cubic-bezier(0.4, 0, 0.2, 1);
}
.app-header__menu-item:hover,
.app-header__menu-item:focus-visible {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
  outline: none;
}

/* Title: 只显示当前页标题，section 已在 sidebar 高亮，header 不再重复 */
.app-header__title {
  min-width: 0;
  display: flex;
  align-items: center;
  padding-left: 0.25rem;
}

.app-header__page-title {
  margin: 0;
  font-size: 0.9375rem; /* 15px */
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.005em;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Center: search ── */
.app-header__center {
  flex: 1 1 auto;
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 0 0.5rem;
}
.app-header__search-wrap {
  width: 100%;
  max-width: 480px;
  display: flex;
  justify-content: center;
}
.app-header__search {
  width: 100%;
}
.app-header__spacer {
  flex: 1 1 auto;
}

/* ── Right: user ── */
.app-header__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 0 0 auto;
}

.app-header__user {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  transition: opacity 120ms cubic-bezier(0.4, 0, 0.2, 1);
}
.app-header__user:hover { opacity: 0.85; }
.app-header__user:focus-visible {
  outline: none;
}
.app-header__user:focus-visible .app-header__avatar {
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.55);
}

.app-header__avatar {
  width: 1.85rem; /* 30px */
  height: 1.85rem;
  border-radius: 999px;
  background: linear-gradient(135deg, hsl(var(--primary) / 0.85), hsl(var(--primary) / 0.65));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--primary-foreground));
  border: 1px solid hsl(var(--border) / 0.4);
  flex-shrink: 0;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

/* ── Transitions ── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 140ms cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.header-menu-enter-active {
  transition:
    opacity 120ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 140ms cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: top left;
}
.header-menu-leave-active {
  transition:
    opacity 80ms cubic-bezier(0.4, 0, 1, 1),
    transform 100ms cubic-bezier(0.4, 0, 1, 1);
  transform-origin: top left;
}
.header-menu-enter-from,
.header-menu-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
}
</style>
