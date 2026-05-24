<template>
  <header class="h-14 sticky top-0 z-40 flex items-center px-6 gap-4 bg-background">
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
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import RouteContextBar from '@/components/layout/RouteContextBar.vue'
import GlobalSearchBar from '@/components/layout/GlobalSearchBar.vue'
import { resolveRouteContext } from '@/constants/sidebar'
import { useUIStore } from '@/stores/ui'

const route = useRoute()
const uiStore = useUIStore()
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
