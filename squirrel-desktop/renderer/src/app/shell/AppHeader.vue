<template>
  <header
    class="app-header"
    :class="{ 'app-header--desktop': variant === 'desktop' }"
  >
    <div
      v-if="showLeading"
      class="app-header__leading"
    >
      <Button
        type="button"
        text
        severity="secondary"
        size="sm"
        icon-only
        class="app-header__sidebar-toggle"
        :title="isSidebarOpen ? '收起侧边栏 (Ctrl+B)' : '展开侧边栏 (Ctrl+B)'"
        :aria-label="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
        :aria-expanded="isSidebarOpen"
        @click="toggleSidebar"
      >
        <AppIcon name="panelLeft" class="size-4" />
      </Button>
    </div>

    <div class="app-header__search-slot">
      <Transition name="fade" mode="out-in">
        <div v-if="showSearch" key="search" class="app-header__search-wrap">
          <GlobalSearchBar
            :key="searchScope"
            class="app-header__search"
            :search-scope="searchScope"
            :placeholder="String(route.meta.searchPlaceholder || '搜索归仓')"
            :suggestion-scope="String(route.meta.search || 'home')"
            :suggestions-enabled="searchSuggestionsEnabled"
            :search-modes="showVideoSearchMode ? searchModeOptions : []"
            :active-search-mode="videoSearchMode"
            :search-redirect-name="searchRedirectName"
            @search-mode-change="setVideoSearchMode"
          />
        </div>
        <div v-else key="spacer" class="app-header__spacer" />
      </Transition>
    </div>

    <div class="app-header__actions">
      <Button
        type="button"
        text
        severity="secondary"
        size="sm"
        class="app-header__user"
        :title="`${userDisplayName} - 个人资料`"
        @click="goToProfile"
      >
        <span class="app-header__avatar">
          <template v-if="userInitial">{{ userInitial }}</template>
          <AppIcon v-else name="user" class="size-3.5" />
        </span>
        <span class="app-header__user-name">{{ userDisplayName }}</span>
      </Button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import AppIcon from '@/shared/icons/AppIcon.vue'
import GlobalSearchBar from '@/shared/components/layout/GlobalSearchBar.vue'
import { Button } from '@/shared/ui/button'
import { useUIStore } from '@/shared/stores/ui'
import { useUserStore } from '@/shared/stores/user'

const props = withDefaults(defineProps<{
  persistSidebarToggle?: boolean
  /** desktop = fragment inside Electron titlebar (no own chrome) */
  variant?: 'default' | 'desktop'
}>(), {
  persistSidebarToggle: true,
  variant: 'default',
})

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()
const userStore = useUserStore()
const { isDesktop: isDesktopEnv } = useDesktopBridge()
const isDesktopClient = isDesktopEnv()

const isSidebarOpen = computed(() => uiStore.isSidebarOpen)
const showLeading = computed(() => props.variant !== 'desktop' && !isDesktopClient)

const toggleSidebar = () => {
  uiStore.toggleSidebar({ persist: props.persistSidebarToggle })
}

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

const showSearch = computed(() => !!route.meta?.showSearch)
const searchScope = computed(() => String(route.meta.searchPersistKey || route.meta.search))
const searchSuggestionsEnabled = computed(() => route.meta.searchSuggestions !== false)
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

</script>

<style scoped>
/*
  default: standalone header bar
  desktop: transparent fragment — search centered in remaining middle,
           user pinned right next to window controls
*/
.app-header {
  height: var(--app-header-height);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.75rem;
  border-bottom: 1px solid hsl(var(--border));
  background: hsl(var(--card));
  position: relative;
  z-index: var(--z-header);
  user-select: none;
}

.app-header--desktop {
  height: 100%;
  border-bottom: 0;
  padding: 0 0.25rem 0 0.5rem;
  background: transparent;
  z-index: auto;
}

.app-header__leading {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  min-width: 0;
}

.app-header__sidebar-toggle {
  border-radius: 999px;
  color: hsl(var(--muted-foreground));
}

.app-header__sidebar-toggle:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--foreground) / 0.06);
}

/*
  Search slot takes all free middle width and centers the pill optically.
  max-width keeps the control readable; flex:1 keeps it from looking left-stuck.
*/
.app-header__search-slot {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  justify-content: center;
}

.app-header__search-wrap {
  width: 100%;
  max-width: 40rem;
  display: flex;
  justify-content: center;
}

.app-header__search {
  width: 100%;
}

.app-header__spacer {
  flex: 1 1 auto;
}

.app-header__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
  gap: 0.5rem;
}

.app-header__user {
  min-width: 0;
  max-width: 11rem;
  gap: 0.5rem;
  height: 2rem;
  border-radius: 999px;
  padding: 0 0.625rem 0 0.25rem;
  color: hsl(var(--foreground));
}

.app-header--desktop .app-header__user {
  max-width: 9rem;
}

.app-header__user:hover {
  background: hsl(var(--foreground) / 0.06);
}

.app-header__avatar {
  width: 1.5rem;
  height: 1.5rem;
  border: 0;
  border-radius: 999px;
  background: hsl(var(--primary));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6875rem;
  font-weight: 700;
  color: hsl(var(--primary-foreground));
  flex: 0 0 auto;
  letter-spacing: 0;
}

/* Soft gray pill — Reddit search */
.app-header__search-slot :deep(.global-search) {
  max-width: 40rem;
}

.app-header__search-slot :deep(.global-search__box) {
  height: 2.3rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background: hsl(var(--muted) / 0.78);
  box-shadow: none;
}

.app-header__search-slot :deep(.global-search__box:focus-within) {
  border-color: hsl(var(--foreground) / 0.12);
  background: hsl(var(--card));
  box-shadow: 0 0 0 1px hsl(var(--foreground) / 0.04), var(--shadow-xs);
}

.app-header__search-slot :deep(.global-search__box.is-open:not(:focus-within)) {
  border-color: hsl(var(--border) / 0.45);
  background: hsl(var(--muted) / 0.62);
}

.app-header__search-slot :deep(.global-search__suggestions) {
  border-color: hsl(var(--border));
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-popover);
}

.app-header__user-name {
  overflow: hidden;
  font-size: 0.8125rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast) var(--ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 980px) {
  .app-header__user-name {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-header__user,
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
