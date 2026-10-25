<template>
  <AppPageShell class="videos-workbench" variant="compact" surface="consume" width="browse">
    <header class="app-page-heading">
      <AppOperatePageHeader title="视频库" :summary="videosSummary" size="md" />
    </header>

    <AppToolbarFrame compact sticky boundary="browse">
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
        >
          <!-- Active filters live inside the toolbar row (no separate band →
               zero layout shift when they appear/disappear). -->
          <template v-if="activeFilterTokens.length" #after-tabs>
            <div class="videos-workbench__filters no-scrollbar" aria-label="已启用筛选">
              <button
                v-for="token in activeFilterTokens"
                :key="token.key"
                type="button"
                class="videos-workbench__chip"
                :aria-label="`移除筛选：${token.dim ? `${token.dim} ` : ''}${token.label}`"
                @click="clearFilter(token.key)"
              >
                <span v-if="token.dim" class="videos-workbench__chip-dim">{{ token.dim }}</span>
                {{ token.label }}
                <AppIcon name="close" class="size-3" />
              </button>
              <button type="button" class="videos-workbench__clear" @click="clearAllPageFilters">清除全部</button>
            </div>
          </template>
        </FeedToolbar>

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
          <Button variant="secondary" size="sm" icon-only title="刷新远端结果" aria-label="刷新远端结果" @click="refreshCurrentList">
            <AppSpinner v-if="isRefreshing" size="sm" />
            <AppIcon v-else name="refresh" class="size-4" />
          </Button>
        </div>
    </AppToolbarFrame>

    <div class="videos-workbench__body">
      <main class="videos-workbench__canvas" aria-label="视频内容">
        <NewContentBar
          v-if="searchMode !== 'remote'"
          class="videos-workbench__new-content"
          :visible="newContentVisible"
          :count="newContentCount"
          @apply="applyNewContent"
        />

        <div v-if="loadError" class="videos-workbench__error">
          <AppEmptyState variant="error" title="加载失败" :copy="loadError">
            <template #actions>
              <Button variant="outline" size="sm" @click="refreshCurrentList">重试</Button>
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
import NewContentBar from '@/shared/components/layout/NewContentBar.vue'
import { useNewContentDetector, prependPreservingScroll } from '@/shared/composables/useNewContentDetector'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppOperatePageHeader from '@/shared/components/layout/AppOperatePageHeader.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import type { VideoListItem } from '@/features/video/types/video'
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
const loadedVideoCount = ref<number | null>(null)
const videosSummary = computed(() => (
  loadedVideoCount.value == null ? '本地视频与稍后看' : `${loadedVideoCount.value} 项可视`
))
const videoChildRef = ref<{
  refresh?: () => void
  fetchTop?: (pageSize?: number) => Promise<VideoListItem[]>
  prependVideos?: (items: VideoListItem[]) => void
  getFirstId?: () => number | null
} | null>(null)
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
  const tokens: Array<{ key: FilterTokenKey; label: string; dim?: string }> = []
  if (site.value) {
    tokens.push({
      key: 'site',
      dim: '来源',
      label: siteOptions.value?.find((option) => option.value === site.value)?.label || site.value,
    })
  }
  if (timeRange.value !== 'all') tokens.push({ key: 'timeRange', dim: '时间', label: optionLabel(TIME_RANGE_OPTIONS, timeRange.value) })
  if (duration.value !== 'all') tokens.push({ key: 'duration', dim: '时长', label: optionLabel(DURATION_OPTIONS, duration.value) })
  if (contentType.value !== 'all') tokens.push({ key: 'contentType', dim: '类型', label: optionLabel(CONTENT_TYPE_OPTIONS, contentType.value) })
  if (nsfw.value !== 'all') tokens.push({ key: 'nsfw', dim: '分级', label: optionLabel(NSFW_OPTIONS, nsfw.value) })
  if (special.value === 'yes') tokens.push({ key: 'special', label: '特别关注' })
  return tokens
})

const handleLoaded = (items?: VideoListItem[]) => {
  loadError.value = null
  if (Array.isArray(items)) loadedVideoCount.value = items.length
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

// Reddit-style new-content detection for the local feed: a quiet probe
// compares the newest page against the displayed list and only surfaces the
// bar. Remote search is an explicit search operation — it keeps its button.
const {
  visible: newContentVisible,
  count: newContentCount,
  check: checkNewContent,
  apply: applyNewContent,
  reset: resetNewContent,
} = useNewContentDetector<VideoListItem>({
  getKnownId: () => videoChildRef.value?.getFirstId?.() ?? null,
  fetchNewest: () => videoChildRef.value?.fetchTop?.() ?? Promise.resolve([]),
  idOf: (item) => item.id,
  onApply: async (newItems) => {
    await prependPreservingScroll(getMainScrollRoot, () => {
      videoChildRef.value?.prependVideos?.(newItems)
    })
  },
  isEnabled: () => searchMode.value === 'local' && !!videoChildRef.value,
})

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

// R key / window-focus auto-refresh now probe silently and surface the bar
// (local mode); remote mode keeps the explicit re-search behaviour.
useRefreshTriggers({
  onRefresh: () => {
    if (searchMode.value === 'remote') refreshCurrentList()
    else checkNewContent()
  },
})
useRouteTabSync(router, route, activeTab, undefined)

// Pending detection is scoped to one list: any tab/filter/mode change makes
// it stale, so drop it (the new list establishes its own baseline).
watch(
  [activeTab, nsfw, sortBy, site, timeRange, duration, contentType, special, searchQuery, searchMode],
  resetNewContent,
)

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
  background: hsl(var(--background));
}

/* Toolbar chrome (sticky band, divider, reading boundary) is shared with the
   subscribed/history pages via AppToolbarFrame — no page-local chrome here. */
.videos-workbench__remote-tools > span {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
}

.videos-workbench__remote-tools {
  display: flex;
  margin-left: auto;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* Active-filter chips live inside the toolbar row (after-tabs slot):
   no extra row, so the page never shifts when filters change. */
.videos-workbench__filters {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  gap: 0.4rem;
  overflow-x: auto;
}

.videos-workbench__filters button {
  display: inline-flex;
  min-height: 1.7rem;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.3rem;
  border: 1px solid hsl(var(--border));
  border-radius: var(--app-control-item-radius);
  padding: 0 0.6rem;
  background: hsl(var(--card));
  color: hsl(var(--foreground));
  box-shadow: var(--shadow-xs);
  font-size: var(--app-text-xs);
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.videos-workbench__filters button:hover {
  border-color: hsl(var(--foreground) / 0.24);
  background: var(--app-control-hover-bg);
}

/* Dimension prefix disambiguates bare values ("本周" → 时间 · 本周). */
.videos-workbench__filters .videos-workbench__chip-dim {
  color: hsl(var(--muted-foreground) / 0.9);
  font-weight: 550;
}

/* Clear-all is a quiet secondary action, not the loudest element in the row. */
.videos-workbench__filters .videos-workbench__clear {
  margin-left: auto;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
  color: hsl(var(--muted-foreground));
}

.videos-workbench__filters .videos-workbench__clear:hover {
  border-color: transparent;
  background: hsl(var(--muted) / 0.6);
  color: hsl(var(--foreground));
}

.videos-workbench__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}

/* The library canvas shares the browse width with the home feed; toolbar
   pills, filter chips and cards keep one horizontal edge. */
.videos-workbench__canvas {
  min-width: 0;
  width: 100%;
  max-width: var(--app-content-browse-max);
  margin-inline: auto;
  padding-inline: var(--app-page-gutter);
  padding-block: 1.05rem 3rem;
}

.videos-workbench__new-content {
  margin-bottom: 0.75rem;
}

.videos-workbench__error {
  margin-bottom: 1rem;
}

.videos-workbench__empty {
  min-height: 28rem;
}
</style>
