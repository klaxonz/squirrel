<template>
  <AppPageShell class="videos-view-page" variant="compact" :fill="false">
    <AppToolbarFrame v-if="searchMode !== 'remote'" bordered compact sticky>
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
    </AppToolbarFrame>
    <AppToolbarFrame v-else bordered compact sticky>
      <div class="videos-view-remote-toolbar">
        <Select :model-value="remoteSite || 'all'" @update:model-value="updateRemoteSite">
          <SelectTrigger class="app-toolbar-select-trigger app-toolbar-control w-auto min-w-[7.5rem]">
            <SelectValue placeholder="全部站点" />
          </SelectTrigger>
          <SelectContent class="min-w-44">
            <SelectItem value="all" class="text-xs">全部站点</SelectItem>
            <SelectItem
              v-for="opt in visibleRemoteSiteOptions"
              :key="opt.value"
              :value="opt.value"
              class="text-xs"
            >
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>

        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          @click="refreshCurrentList"
          title="刷新内容"
          aria-label="刷新内容"
        >
          <AppSpinner v-if="isRefreshing" size="sm" />
          <AppIcon v-else name="refresh" class="w-4 h-4 shrink-0" />
        </Button>
      </div>
    </AppToolbarFrame>

    <div class="app-page-content">

      <!-- Error -->
      <div v-if="loadError" class="videos-view-error">
        <AppEmptyState variant="error" title="加载失败" :copy="loadError">
          <template #actions>
            <Button variant="outline" size="sm" @click="refreshCurrentList">重试</Button>
          </template>
        </AppEmptyState>
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
            @goToProfile="openProfile"
            @goToSubscription="openSubscription"
            @openModal="openVideo"
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
import { useUIStore } from '@/shared/stores/ui'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/features/video/components/feed/FeedToolbar.vue'
import RemoteSearchResults from '@/features/video/components/feed/RemoteSearchResults.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import { VIDEO_TABS } from '@/features/video/constants/videos'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useSites } from '@/features/video/composables/useSites'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'

// Videos tabbed feed: full toolbar + tabbed router-view. Recommendation rows
// live in the separate HomeView (/home).
defineOptions({ name: 'VideosView' })

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const VIDEO_SEARCH_SCOPE = 'VideosView'
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const { activeTab, nsfw, sortBy, site, searchQuery, special, timeRange, duration, contentType, filters } = useFeedFilters()
const { options: siteOptions } = useSites()
const { settings } = useUserSettings()

const tabs = ref(VIDEO_TABS)
const visibleRemoteSiteOptions = computed(() =>
  (siteOptions.value || []).filter((option) => settings.value.showNsfw || option.isNsfw !== true),
)
const isRefreshing = ref(false)
const loadError = ref<string | null>(null)
// ponytail: child components (VideoTab / RemoteSearchResults) share a refresh() surface;
// typing as the minimal interface avoids coupling to specific component instances.
const videoChildRef = ref<{ refresh?: () => void } | null>(null)
const remoteSearchRef = ref<{ refresh?: () => void } | null>(null)

// Remote search uses an independent site filter so it never clobbers the local `site` ref.
const remoteSite = ref('')
const isActiveVideosRoute = computed(() => route.matched.some((record) => record.name === 'VideosView'))
const searchMode = ref<'local' | 'remote'>('local')

const childFilters = computed(() => filters.value)

const updateRemoteSite = (value: unknown) => {
  const siteValue = String(value || 'all') === 'all' ? '' : String(value)
  const query = { ...route.query }
  if (siteValue) query.site = siteValue
  else delete query.site
  router.replace({ query })
}

const refreshCurrentList = () => {
  loadError.value = null
  if (searchMode.value === 'remote') {
    remoteSearchRef.value?.refresh?.()
    return
  }
  videoChildRef.value?.refresh?.()
}

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, undefined)

watch(() => uiStore.getSearchTrigger(VIDEO_SEARCH_SCOPE), () => {
  if (!isActiveVideosRoute.value) return
  searchQuery.value = uiStore.getSearchQuery(VIDEO_SEARCH_SCOPE)
})

watch(() => route.query.q, (value) => {
  if (!isActiveVideosRoute.value) return
  const query = typeof value === 'string' ? value : ''
  searchQuery.value = query
  if (uiStore.getSearchQuery(VIDEO_SEARCH_SCOPE) !== query) {
    uiStore.setSearchQuery(VIDEO_SEARCH_SCOPE, query)
  }
}, { immediate: true })

watch(() => route.query.mode, (value) => {
  if (!isActiveVideosRoute.value) return
  const mode = value === 'remote' ? 'remote' : 'local'
  searchMode.value = mode
  uiStore.setHomeSearchMode(mode)
}, { immediate: true })

watch(() => route.query.site, (value) => {
  if (!isActiveVideosRoute.value) return
  remoteSite.value = typeof value === 'string' ? value : ''
}, { immediate: true })

watch(
  () => ({
    remoteSite: remoteSite.value,
    showNsfw: settings.value.showNsfw,
    options: siteOptions.value || [],
  }),
  ({ remoteSite: current, showNsfw, options }) => {
    if (!current || showNsfw) return
    const selected = options.find((option) => option.value === current)
    if (selected?.isNsfw === true) updateRemoteSite('all')
  },
  { immediate: true },
)

watch(() => route.query.special, (value) => {
  if (!isActiveVideosRoute.value) return
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })
</script>

<style scoped>
.videos-view-page {
  --app-page-max-width: 2400px;
}

.videos-view-remote-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.videos-view-error {
  padding: 0 0 var(--space-5);
}

</style>
