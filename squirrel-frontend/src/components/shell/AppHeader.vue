<template>
  <header class="h-14 sticky top-0 z-[60] flex items-center px-6 gap-4 bg-background">
    <button
      v-if="nav.isVideoPage && nav.videoBackTarget"
      @click="handleVideoBack"
      class="flex items-center gap-1.5 px-2 py-1.5 -ml-2 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-all shrink-0"
      :title="`返回${nav.videoBackLabel || ''}`"
    >
      <AppIcon name="back" class="w-4 h-4" />
      <span class="text-[13px] font-medium whitespace-nowrap">{{ nav.videoBackLabel }}</span>
    </button>

    <div class="flex items-center gap-4 flex-1 min-w-0">
      <div v-if="!showSearch" class="flex items-center overflow-hidden">
        <RouteContextBar 
          :page-title="routeContext.pageTitle" 
          :breadcrumbs="routeContext.breadcrumbs"
          :section-label="routeContext.sectionLabel"
        />
      </div>
      
      <div v-else class="flex min-w-0 flex-1 justify-center">
        <div class="flex w-full max-w-[720px] items-center justify-center gap-2">
          <GlobalSearchBar
            class="min-w-0 flex-1"
            :placeholder="String(route.meta.searchPlaceholder || '搜索或输入命令...')"
            :search-modes="showHomeSearchMode ? searchModeOptions : []"
            :active-search-mode="homeSearchMode"
            @search-mode-change="uiStore.setHomeSearchMode"
          />
        </div>
      </div>
    </div>
    
    <div class="flex items-center gap-1">
      <button class="w-8 h-8 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-all active:scale-95 relative group">
        <AppIcon name="notification" class="w-4 h-4" />
        <span class="absolute top-2 right-2 w-1.5 h-1.5 bg-destructive rounded-full border border-background shadow-sm" />
      </button>

      <div class="flex items-center gap-2.5 pl-2.5 ml-1 border-l border-border">
        <div
          class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-accent cursor-pointer transition-all active:scale-95"
          @click="goToProfile"
        >
          <div class="w-7 h-7 rounded-full bg-primary/10 dark:bg-primary/20 flex items-center justify-center text-xs font-bold text-primary dark:text-primary-foreground shrink-0">
            <template v-if="userInitial">{{ userInitial }}</template>
            <AppIcon v-else name="user" class="w-3.5 h-3.5" />
          </div>
          <span class="text-[13px] font-medium text-foreground hidden sm:inline">{{ userDisplayName }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import RouteContextBar from '@/components/layout/RouteContextBar.vue'
import GlobalSearchBar from '@/components/layout/GlobalSearchBar.vue'
import { resolveRouteContext } from '@/constants/sidebar'
import { useUIStore } from '@/stores/ui'
import { useUserStore } from '@/stores/user'
import { useNavigationHistory } from '@/composables/useNavigationHistory'

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()
const userStore = useUserStore()
const nav = useNavigationHistory()

const userDisplayName = computed(() => {
  if (!userStore.currentUser) return '未登录'
  return userStore.currentUser.nickname || userStore.currentUser.email?.split('@')[0] || '用户'
})

const userInitial = computed(() => {
  const name = userDisplayName.value
  return name && name !== '未登录' ? name.charAt(0) : ''
})

const goToProfile = () => {
  router.push('/profile')
}

function handleVideoBack() {
  if (nav.videoBackTarget.value) {
    router.replace(nav.videoBackTarget.value)
  }
}

const showSearch = computed(() => !!route.meta?.showSearch)
const homeSearchMode = computed(() => uiStore.homeSearchMode)
const showHomeSearchMode = computed(() => {
  return window.desktopApp?.isDesktop === true
    && route.matched.some((record) => record.name === 'LatestVideos')
    && !route.params.id
})
const routeContext = computed(() => resolveRouteContext(route))
const searchModeOptions = [
  { value: 'local', label: '本地' },
  { value: 'remote', label: '远端' },
] as const
</script>
