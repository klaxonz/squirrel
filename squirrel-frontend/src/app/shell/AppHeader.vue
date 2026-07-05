<template>
  <header class="app-header">
    <div class="app-header__lead">
      <button
        v-if="canGoBack"
        type="button"
        class="app-header__back"
        :title="`返回 ${backTooltipLabel}`"
        aria-label="返回上一页"
        @click="handleBack"
      >
        <AppIcon name="chevronLeft" class="size-[15px]" />
      </button>

      <div class="app-header__context" :title="contextTitle">
        <div class="app-header__section">{{ sectionLabel }}</div>
        <h1 class="app-header__page-title">{{ pageTitle }}</h1>
      </div>
    </div>

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

    <div class="app-header__actions">
      <button
        type="button"
        class="app-header__user"
        :title="`${userDisplayName} - 个人资料`"
        @click="goToProfile"
      >
        <span class="app-header__avatar">
          <template v-if="userInitial">{{ userInitial }}</template>
          <AppIcon v-else name="user" class="size-3.5" />
        </span>
        <span class="app-header__user-name">{{ userDisplayName }}</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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

const routeContext = computed(() => resolveRouteContext(route))
const pageTitle = computed(() => routeContext.value.pageTitle)
const sectionLabel = computed(() => routeContext.value.sectionLabel)
const contextTitle = computed(() => `${sectionLabel.value} / ${pageTitle.value}`)

const canGoBack = computed(() => nav.canGoBack.value)
const backTooltipLabel = computed(() => {
  const list = nav.backCandidates.value
  const last = list[list.length - 1]
  return last?.title || last?.sectionLabel || '上一页'
})

function handleBack() {
  void nav.goBack()
}
</script>

<style scoped>
.app-header {
  height: 3.5rem;
  display: grid;
  grid-template-columns: minmax(15rem, 0.8fr) minmax(22rem, 1.2fr) minmax(10rem, 0.55fr);
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--card) / 0.88);
  position: relative;
  z-index: var(--z-header);
  user-select: none;
}

.app-header__lead {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.app-header__back {
  width: 1.875rem;
  height: 1.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: 1px solid hsl(var(--border) / 0.64);
  border-radius: var(--radius-md);
  background: hsl(var(--secondary) / 0.58);
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.app-header__back:hover {
  border-color: hsl(var(--primary) / 0.38);
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.app-header__back:active {
  transform: translateY(1px);
}

.app-header__context {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.app-header__section {
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-header__page-title {
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 0.9375rem;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-header__center {
  min-width: 0;
  display: flex;
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
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
}

.app-header__user {
  min-width: 0;
  max-width: 11rem;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  height: 2rem;
  padding: 0 0.5rem 0 0.375rem;
  border-radius: var(--radius-md);
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.app-header__user:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.app-header__avatar {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: var(--radius-md);
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
  .app-header {
    grid-template-columns: minmax(10rem, 0.7fr) minmax(16rem, 1fr) auto;
  }

  .app-header__user-name {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-header__back,
  .app-header__user,
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
