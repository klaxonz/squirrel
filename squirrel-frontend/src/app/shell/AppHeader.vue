<template>
  <header class="h-14 sticky top-0 z-header flex items-center px-5 gap-4 border-b border-border/40 bg-background/95 backdrop-blur">
    <div class="flex min-w-0 flex-1 items-center gap-4">
      <div class="flex min-w-0 shrink-0 items-center gap-2">
        <button
          v-if="showContextBack"
          type="button"
          class="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
          :title="backTitle"
          :aria-label="backTitle"
          @click="goBack"
        >
          <AppIcon name="chevronLeft" class="size-4" />
        </button>

        <div class="min-w-0">
          <RouteContextBar
            v-if="showBreadcrumbs"
            class="mb-0.5 max-w-[360px]"
            :page-title="routeContext.pageTitle"
            :breadcrumbs="breadcrumbTrail"
            :section-label="routeContext.sectionLabel"
          />
          <h1 class="truncate text-[1.05rem] font-semibold leading-6 text-foreground">
            {{ routeContext.pageTitle }}
          </h1>
        </div>
      </div>

      <Transition name="fade" mode="out-in">
        <div v-if="showSearch" key="search" class="flex min-w-0 flex-1 justify-center">
          <div class="flex min-w-0 flex-1 justify-center">
            <GlobalSearchBar
              class="min-w-0 w-full max-w-[720px]"
              :placeholder="String(route.meta.searchPlaceholder || '搜索或输入命令...')"
              :suggestion-scope="String(route.meta.search || 'home')"
              :search-modes="showVideoSearchMode ? searchModeOptions : []"
              :active-search-mode="videoSearchMode"
              :search-redirect-name="searchRedirectName"
              @search-mode-change="setVideoSearchMode"
            />
          </div>
        </div>

        <div v-else key="spacer" class="min-w-0 flex-1" />
      </Transition>
    </div>
    
    <div class="flex items-center gap-1">
      <div class="flex items-center gap-2.5 pl-2.5 ml-1 border-l border-border/60">
        <div
          class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-accent/40 cursor-pointer transition-colors active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
          role="button"
          tabindex="0"
          @click="goToProfile"
          @keydown.enter.prevent="goToProfile"
          @keydown.space.prevent="goToProfile"
        >
          <div class="w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold text-foreground/80 shrink-0 border border-border/50">
            <template v-if="userInitial">{{ userInitial }}</template>
            <AppIcon v-else name="user" class="w-3.5 h-3.5" />
          </div>
          <span class="text-sm font-medium text-foreground/90">{{ userDisplayName }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import AppIcon from '@/shared/icons/AppIcon.vue'
import RouteContextBar from '@/shared/components/layout/RouteContextBar.vue'
import GlobalSearchBar from '@/shared/components/layout/GlobalSearchBar.vue'
import { resolveRouteContext } from '@/shared/constants/sidebar'
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
const routeContext = computed(() => resolveRouteContext(route))
const canGoBack = computed(() => nav.canGoBack.value)
const breadcrumbTrail = computed(() => routeContext.value.breadcrumbs.slice(0, -1))
const showBreadcrumbs = computed(() => breadcrumbTrail.value.length > 0 && !routeContext.value.isTopLevel)
const showContextBack = computed(() => (
  canGoBack.value
  && (
    Boolean(routeContext.value.backTarget)
    || nav.hasInternalBack.value
    || (nav.isVideoPage.value && Boolean(nav.videoBackTarget.value))
  )
))
const backTitle = computed(() => {
  if (nav.isVideoPage.value && nav.videoBackLabel.value) return `返回 ${nav.videoBackLabel.value}`
  if (nav.hasInternalBack.value) return '返回上一层'
  const parent = [...breadcrumbTrail.value].reverse().find((item) => item.to)
  return parent?.label ? `返回 ${parent.label}` : '返回上一页'
})
const searchModeOptions = [
  { value: 'local', label: '本地' },
  { value: 'remote', label: '远端' },
] as const

function goBack() {
  nav.goBack()
}

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
