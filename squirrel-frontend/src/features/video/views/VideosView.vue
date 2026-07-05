<template>
  <AppPageShell class="videos-view-page" variant="compact" :fill="false">
    <div v-if="searchMode !== 'remote'" class="videos-view-toolbar">
      <div class="videos-view-toolbar__inner">
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
    </div>
    <div v-else class="videos-view-toolbar">
      <div class="videos-view-toolbar__inner videos-view-toolbar__inner--remote">
        <div class="flex min-w-0 items-center gap-2">
          <AppIcon name="siteFallback" class="h-4 w-4 shrink-0 text-primary opacity-80" />
          <span class="shrink-0 text-sm font-semibold text-foreground">远端搜索</span>
          <span v-if="searchQuery" class="min-w-0 truncate text-sm text-muted-foreground">“{{ searchQuery }}”</span>
        </div>

        <div class="flex shrink-0 items-center gap-1">
          <Select :model-value="remoteSite || 'all'" @update:model-value="updateRemoteSite">
            <SelectTrigger class="h-8 w-auto min-w-[120px] border border-border/60 bg-transparent px-2.5 py-0 text-xs font-medium text-muted-foreground shadow-none transition-colors hover:bg-accent/40 hover:text-foreground focus:ring-0">
              <SelectValue placeholder="全部站点" />
            </SelectTrigger>
            <SelectContent class="min-w-44 border-border/60 bg-popover shadow-lg rounded-md">
              <SelectItem value="all" class="text-xs">全部站点</SelectItem>
              <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">{{ opt.label }}</SelectItem>
            </SelectContent>
          </Select>

          <button
            type="button"
            class="flex size-8 shrink-0 items-center justify-center rounded-md border border-transparent text-muted-foreground transition-colors outline-none hover:bg-accent/40 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            @click="refreshCurrentList"
            title="刷新内容"
            aria-label="刷新内容"
          >
            <AppSpinner v-if="isRefreshing" size="sm" />
            <AppIcon v-else name="refresh" class="w-4 h-4 shrink-0" />
          </button>
        </div>
      </div>
    </div>

    <div class="app-page-content videos-view-content">

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
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import { VIDEO_TABS } from '@/features/video/constants/videos'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useSites } from '@/features/video/composables/useSites'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'

// Videos tabbed feed: full toolbar + tabbed router-view. Recommendation rows
// live in the separate HomeView (/home).
defineOptions({ name: 'VideosView' })

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const { openVideo, openSubscription } = useVideoCardNavigation(router)

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

watch(() => uiStore.searchTrigger, () => {
  if (!isActiveVideosRoute.value) return
  if (route.meta.search === 'home' || !route.meta.search) {
    searchQuery.value = uiStore.searchQuery
  }
})

watch(() => route.query.q, (value) => {
  if (!isActiveVideosRoute.value) return
  const query = typeof value === 'string' ? value : ''
  searchQuery.value = query
  if (uiStore.searchQuery !== query) uiStore.searchQuery = query
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

watch(() => route.query.special, (value) => {
  if (!isActiveVideosRoute.value) return
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })
</script>

<style scoped>
.videos-view-page {
  --app-page-max-width: 2400px;
}

.videos-view-toolbar {
  position: sticky;
  top: 0;
  z-index: var(--z-content);
  padding: var(--space-3) var(--app-page-gutter) var(--space-2);
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  background: hsl(var(--background) / 0.92);
}

.videos-view-toolbar__inner {
  width: 100%;
  max-width: var(--app-page-max-width);
  margin: 0 auto;
}

.videos-view-toolbar__inner--remote {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.videos-view-content {
  padding-top: var(--space-5);
}

.videos-view-error {
  padding: 0 0 var(--space-5);
}

@media (min-width: 640px) {
  .videos-view-toolbar {
    padding-left: var(--app-page-gutter-sm);
    padding-right: var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .videos-view-toolbar {
    padding-left: var(--app-page-gutter-lg);
    padding-right: var(--app-page-gutter-lg);
  }
}
</style>
