<template>
  <AppPageShell class="videos-view-page" variant="compact" :fill="false">
    <div class="app-page-content">

      <!-- Persistent Sticky Toolbar (always at top, never moves) -->
      <div class="sticky top-0 z-20 -mx-6 mb-4 px-6 py-2 bg-background/95 backdrop-blur border-b border-border/10">
        <FeedToolbar
          :active-tab="activeTab"
          :nsfw="nsfw"
          :sort-by="sortBy"
          :site="site"
          :special="special"
          :time-range="timeRange"
          :duration="duration"
          :content-type="contentType"
          :tabs="tabs"
          :is-refreshing="isRefreshing"
          :show-tabs="true"
          :show-sort="true"
          :show-filter="true"
          @update:activeTab="activeTab = $event"
          @update:nsfw="nsfw = $event"
          @update:sortBy="sortBy = $event"
          @update:site="site = $event"
          @update:timeRange="timeRange = $event"
          @update:duration="duration = $event"
          @update:contentType="contentType = $event"
          @update:special="setSpecialFilter"
          @refresh="refreshCurrentList"
        />
      </div>

      <!-- Error -->
      <div v-if="loadError" class="px-6 pt-2 pb-4">
        <div class="bg-destructive/10 rounded-sm p-4 flex items-center justify-between">
          <p class="text-sm text-destructive font-medium">{{ loadError }}</p>
          <button @click="refreshCurrentList" class="text-xs font-bold uppercase tracking-widest px-4 py-2 bg-destructive text-white rounded-full">重试</button>
        </div>
      </div>

      <!-- Remote search header (replaces nothing above; only an inline section header) -->
      <div v-if="searchMode === 'remote' && searchQuery" class="px-6 flex items-center justify-between mb-2 mt-4">
        <h2 class="text-[16px] font-bold tracking-tight text-foreground/90 flex items-center gap-2">
          <AppIcon name="siteFallback" class="w-5 h-5 text-primary opacity-80" />
          远端搜索结果
        </h2>

        <Select :model-value="remoteSite || 'all'" @update:model-value="updateRemoteSite">
          <SelectTrigger class="h-8 w-auto min-w-[120px] bg-accent/40 border-0 text-[12px] font-bold rounded-full transition-colors hover:bg-accent/60">
            <SelectValue placeholder="全部站点" />
          </SelectTrigger>
          <SelectContent class="border-border/10 bg-background/70 backdrop-blur-2xl shadow-2xl rounded-md min-w-[140px]">
            <SelectItem value="all" class="text-xs">全部站点</SelectItem>
            <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">{{ opt.label }}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <!-- Remote search results -->
      <keep-alive v-if="searchMode === 'remote' && searchQuery">
        <RemoteSearchResults
          ref="remoteSearchRef"
          :query="searchQuery"
          :site="remoteSite"
          @error="loadError = $event"
          @loading-change="isRefreshing = !!$event"
        />
      </keep-alive>

      <!-- Local feed -->
      <router-view v-else v-slot="{ Component, route: childRoute }">
        <keep-alive :max="10">
          <component
            :is="Component"
            :key="childRoute.name"
            :filters="childFilters"
            ref="videoChildRef"
            @goToSubscription="goToChannelDetail"
            @openModal="handleOpenModal"
            @error="loadError = String($event || '')"
            @loading-change="isRefreshing = !!$event"
          />
        </keep-alive>
      </router-view>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import RemoteSearchResults from '@/components/feed/RemoteSearchResults.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { VIDEO_TABS } from '@/constants/videos'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import AppIcon from '@/components/common/AppIcon.vue'
import { useSites } from '@/composables/useSites'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

// Videos tabbed feed: full toolbar + tabbed router-view. Recommendation rows
// live in the separate HomeView (/home).
defineOptions({ name: 'VideosView' })

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()

const { activeTab, nsfw, sortBy, site, searchQuery, special, timeRange, duration, contentType, filters } = useFeedFilters()
const { options: siteOptions } = useSites()

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<string | null>(null)
// ponytail: child components (VideoTab / RemoteSearchResults) share a refresh() surface;
// typing as the minimal interface avoids coupling to specific component instances.
const videoChildRef = ref<{ refresh?: () => void } | null>(null)
const remoteSearchRef = ref<{ refresh?: () => void } | null>(null)

// Remote search uses an independent site filter so it never clobbers the local `site` ref.
const remoteSite = ref('')

const searchMode = computed({
  get: () => uiStore.homeSearchMode,
  set: (value: 'local' | 'remote') => uiStore.setHomeSearchMode(value),
})

const childFilters = computed(() => filters.value)

const updateRemoteSite = (value: unknown) => {
  remoteSite.value = String(value || 'all') === 'all' ? '' : String(value)
}

const refreshCurrentList = () => {
  loadError.value = null
  if (searchMode.value === 'remote') {
    remoteSearchRef.value?.refresh?.()
    return
  }
  videoChildRef.value?.refresh?.()
}

const handleOpenModal = (video: { id: string | number }) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (id: string) => router.push(`/subscription/${id}/all`)

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, undefined)

watch(() => uiStore.searchTrigger, () => {
  if (route.meta.search === 'home' || !route.meta.search) {
    searchQuery.value = uiStore.searchQuery
  }
})

watch(() => route.query.special, (value) => {
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })
</script>

<style scoped>
.videos-view-page {
  --app-page-max-width: 2400px;
}
</style>
