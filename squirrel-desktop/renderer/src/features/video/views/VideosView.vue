<template>
  <AppPageShell class="videos-workbench" variant="compact" surface="consume" width="fluid">
    <header class="videos-workbench__toolbar">
      <div class="videos-workbench__toolbar-inner">
        <FeedToolbar
          v-if="searchMode !== 'remote'"
          variant="workbench"
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
          :preference-key="viewPreferenceKey"
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

        <div v-else class="videos-workbench__remote-tools">
          <span>远端结果</span>
          <Select
            :model-value="remoteSite || 'all'"
            :options="remoteSiteSelectOptions"
            option-label="label"
            option-value="value"
            placeholder="全部站点"
            size="small"
            class="app-toolbar-control app-toolbar-select-trigger min-w-32"
            aria-label="远端搜索站点"
            @update:model-value="updateRemoteSite"
          />
          <Button text severity="secondary" size="sm" icon-only title="刷新远端结果" aria-label="刷新远端结果" @click="refreshCurrentList">
            <AppSpinner v-if="isRefreshing" size="sm" />
            <AppIcon v-else name="refresh" class="size-4" />
          </Button>
        </div>
      </div>
    </header>

    <div v-if="activeFilterTokens.length" class="videos-workbench__filters-band">
      <div
        class="videos-workbench__filters"
        aria-label="已启用筛选"
      >
        <span>已筛选</span>
        <button v-for="token in activeFilterTokens" :key="token.key" type="button" @click="clearFilter(token.key)">
          {{ token.label }}
          <AppIcon name="close" class="size-3" />
        </button>
        <button type="button" class="videos-workbench__clear" @click="clearAllPageFilters">清除全部</button>
      </div>
    </div>

    <div class="videos-workbench__body">
      <main class="videos-workbench__canvas" aria-label="视频内容">
        <div v-if="loadError" class="videos-workbench__error">
          <AppEmptyState variant="error" title="加载失败" :copy="loadError">
            <template #actions>
              <Button severity="secondary" outlined size="sm" @click="refreshCurrentList">重试</Button>
            </template>
          </AppEmptyState>
        </div>

        <keep-alive v-if="searchMode === 'remote' && searchQuery">
          <RemoteSearchResults
            ref="remoteSearchRef"
            :query="searchQuery"
            :site="remoteSite"
            presentation="workbench"
            @error="loadError = String($event || '')"
            @loaded="handleLoaded"
            @loading-change="isRefreshing = !!$event"
          />
        </keep-alive>

        <div v-else-if="searchMode === 'remote'" class="videos-workbench__empty">
          <AppEmptyState title="搜索远端内容" copy="在顶部搜索框输入关键词；结果来自源站，不会写入本地视频库。" />
        </div>

        <router-view v-else v-slot="{ Component, route: childRoute }">
          <keep-alive :max="10">
            <component
              :is="Component"
              :key="childRoute.name"
              :filters="childFilters"
              presentation="workbench"
              ref="videoChildRef"
              @goToProfile="openProfile"
              @goToSubscription="openSubscription"
              @openModal="openVideo"
              @loaded="handleLoaded"
              @error="loadError = String($event || '')"
              @loading-change="isRefreshing = !!$event"
            />
          </keep-alive>
        </router-view>
      </main>
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
import { VIDEO_LIBRARY_TABS, VIDEO_TABS } from '@/features/video/constants/videos'
import {
  CONTENT_TYPE_OPTIONS,
  DURATION_OPTIONS,
  NSFW_OPTIONS,
  TIME_RANGE_OPTIONS,
} from '@/features/video/constants/feedFilters'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useSites } from '@/features/video/composables/useSites'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import { Select } from '@/shared/ui/select'

defineOptions({ name: 'VideosView' })

type FilterTokenKey = 'site' | 'timeRange' | 'duration' | 'contentType' | 'nsfw' | 'special'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const VIDEO_SEARCH_SCOPE = 'VideosView'
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)
const { activeTab, nsfw, sortBy, site, searchQuery, special, timeRange, duration, contentType, filters } = useFeedFilters()
const { options: siteOptions } = useSites()
const { settings } = useUserSettings()

const tabs = [...VIDEO_TABS, ...VIDEO_LIBRARY_TABS]
const isRefreshing = ref(false)
const loadError = ref<string | null>(null)
const videoChildRef = ref<{ refresh?: () => void } | null>(null)
const remoteSearchRef = ref<{ refresh?: () => void } | null>(null)
const remoteSite = ref('')
const searchMode = ref<'local' | 'remote'>('local')
const childFilters = computed(() => filters.value)
const viewPreferenceKey = computed(() => `local-v2:${activeTab.value}`)
const isActiveVideosRoute = computed(() => route.matched.some((record) => record.name === 'VideosView'))

const visibleRemoteSiteOptions = computed(() =>
  (siteOptions.value || []).filter((option) => settings.value.showNsfw || option.isNsfw !== true),
)
const remoteSiteSelectOptions = computed(() => [
  { value: 'all', label: '全部站点' },
  ...visibleRemoteSiteOptions.value,
])

const optionLabel = (options: readonly { value: string; label: string }[], value: string) => (
  options.find((option) => option.value === value)?.label || value
)

const activeFilterTokens = computed(() => {
  const tokens: Array<{ key: FilterTokenKey; label: string }> = []
  if (site.value) {
    tokens.push({
      key: 'site',
      label: siteOptions.value?.find((option) => option.value === site.value)?.label || site.value,
    })
  }
  if (timeRange.value !== 'all') tokens.push({ key: 'timeRange', label: optionLabel(TIME_RANGE_OPTIONS, timeRange.value) })
  if (duration.value !== 'all') tokens.push({ key: 'duration', label: optionLabel(DURATION_OPTIONS, duration.value) })
  if (contentType.value !== 'all') tokens.push({ key: 'contentType', label: optionLabel(CONTENT_TYPE_OPTIONS, contentType.value) })
  if (nsfw.value !== 'all') tokens.push({ key: 'nsfw', label: optionLabel(NSFW_OPTIONS, nsfw.value) })
  if (special.value === 'yes') tokens.push({ key: 'special', label: '特别关注' })
  return tokens
})

const handleLoaded = () => {
  loadError.value = null
}

const clearFilter = (key: FilterTokenKey) => {
  if (key === 'site') site.value = undefined
  if (key === 'timeRange') timeRange.value = 'all'
  if (key === 'duration') duration.value = 'all'
  if (key === 'contentType') contentType.value = 'all'
  if (key === 'nsfw') nsfw.value = 'all'
  if (key === 'special') setSpecialFilter('all')
}

const clearAllPageFilters = () => {
  site.value = undefined
  timeRange.value = 'all'
  duration.value = 'all'
  contentType.value = 'all'
  nsfw.value = 'all'
  setSpecialFilter('all')
}

const updateRemoteSite = (value: unknown) => {
  const siteValue = String(value || 'all') === 'all' ? '' : String(value)
  const query = { ...route.query }
  if (siteValue) query.site = siteValue
  else delete query.site
  router.replace({ query })
}

const refreshCurrentList = () => {
  loadError.value = null
  if (searchMode.value === 'remote') remoteSearchRef.value?.refresh?.()
  else videoChildRef.value?.refresh?.()
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

watch(viewPreferenceKey, (key) => uiStore.applyVideoViewPreference(key), { immediate: true })

watch(() => uiStore.getSearchTrigger(VIDEO_SEARCH_SCOPE), () => {
  if (!isActiveVideosRoute.value) return
  searchQuery.value = uiStore.getSearchQuery(VIDEO_SEARCH_SCOPE)
})

watch(() => route.query.q, (value) => {
  if (!isActiveVideosRoute.value) return
  const query = typeof value === 'string' ? value : ''
  searchQuery.value = query
  if (uiStore.getSearchQuery(VIDEO_SEARCH_SCOPE) !== query) uiStore.setSearchQuery(VIDEO_SEARCH_SCOPE, query)
}, { immediate: true })

watch(() => route.query.mode, (value) => {
  if (!isActiveVideosRoute.value) return
  searchMode.value = value === 'remote' ? 'remote' : 'local'
  uiStore.setHomeSearchMode(searchMode.value)
}, { immediate: true })

watch(() => route.query.site, (value) => {
  if (!isActiveVideosRoute.value) return
  remoteSite.value = typeof value === 'string' ? value : ''
}, { immediate: true })

watch(
  () => ({ remoteSite: remoteSite.value, showNsfw: settings.value.showNsfw, options: siteOptions.value || [] }),
  ({ remoteSite: current, showNsfw, options }) => {
    if (!current || showNsfw) return
    if (options.find((option) => option.value === current)?.isNsfw === true) updateRemoteSite('all')
  },
  { immediate: true },
)

watch(() => route.query.special, (value) => {
  if (!isActiveVideosRoute.value) return
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })
</script>

<style scoped>
.videos-workbench {
  min-height: 100%;
  background: hsl(var(--card));
}

/* Full-bleed sticky toolbar — opaque Reddit sort bar, not a frosted slab. */
.videos-workbench__toolbar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background: hsl(var(--card));
  border-bottom: 1px solid hsl(var(--border) / 0.72);
}

.videos-workbench__toolbar-inner {
  display: flex;
  width: 100%;
  max-width: none;
  min-height: 3rem;
  margin-inline: 0;
  padding-inline: var(--app-content-media-gutter);
  align-items: center;
}

.videos-workbench__remote-tools > span {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.videos-workbench__remote-tools {
  display: flex;
  margin-left: auto;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

.videos-workbench__filters-band {
  /* Sticky filter row is part of the content surface (the toolbar above it
     is already card) — tint from the card, not the canvas. */
  background: hsl(var(--card) / 0.88);
  border-bottom: 1px solid hsl(var(--border) / 0.55);
}

.videos-workbench__filters {
  display: flex;
  width: 100%;
  max-width: none;
  min-height: 2.55rem;
  margin-inline: 0;
  padding-inline: var(--app-content-media-gutter);
  align-items: center;
  gap: 0.4rem;
}

.videos-workbench__filters > span {
  margin-right: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.videos-workbench__filters button {
  display: inline-flex;
  min-height: 1.7rem;
  align-items: center;
  gap: 0.3rem;
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  padding: 0 0.6rem;
  background: hsl(var(--card));
  color: hsl(var(--foreground));
  box-shadow: var(--shadow-xs);
  font-size: 0.6875rem;
  font-weight: 600;
  cursor: pointer;
}

.videos-workbench__filters button:hover {
  border-color: hsl(var(--foreground) / 0.24);
  background: hsl(var(--accent));
}

.videos-workbench__filters .videos-workbench__clear {
  margin-left: auto;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
  color: hsl(var(--info));
}

.videos-workbench__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}

/* Full workspace width; list cards hug the left, grid fills. */
.videos-workbench__canvas {
  min-width: 0;
  width: 100%;
  max-width: none;
  margin-inline: 0;
  padding-inline: var(--app-content-media-gutter);
  padding-block: 1.05rem 3rem;
}

.videos-workbench__error {
  margin-bottom: 1rem;
}

.videos-workbench__empty {
  min-height: 28rem;
}

@media (max-width: 1180px) {
  .videos-workbench__toolbar-inner {
    padding-block: 0.5rem;
  }
}
</style>
