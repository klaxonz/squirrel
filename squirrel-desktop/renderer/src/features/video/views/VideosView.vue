<template>
  <AppPageShell class="videos-workbench" variant="compact" surface="consume" width="fluid">
    <header class="videos-workbench__toolbar">
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
    </header>

    <div v-if="activeFilterTokens.length" class="videos-workbench__filters" aria-label="已启用筛选">
      <span>已筛选</span>
      <button v-for="token in activeFilterTokens" :key="token.key" type="button" @click="clearFilter(token.key)">
        {{ token.label }}
        <AppIcon name="close" class="size-3" />
      </button>
      <button type="button" class="videos-workbench__clear" @click="clearAllPageFilters">清除全部</button>
    </div>

    <div class="videos-workbench__body" :class="{ 'has-inspector': selectedVideo && searchMode === 'local' }">
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
              :selected-video-id="selectedVideo?.id"
              ref="videoChildRef"
              @goToProfile="openProfile"
              @goToSubscription="openSubscription"
              @openModal="openVideo"
              @selectVideo="selectedVideo = $event"
              @loaded="handleLoaded"
              @error="loadError = String($event || '')"
              @loading-change="isRefreshing = !!$event"
            />
          </keep-alive>
        </router-view>
      </main>

      <Transition name="inspector">
        <aside v-if="selectedVideo && searchMode === 'local'" class="videos-inspector" aria-label="视频详情">
          <header class="videos-inspector__header">
            <span>详情</span>
            <Button text severity="secondary" size="sm" icon-only title="关闭详情" aria-label="关闭详情" @click="selectedVideo = null">
              <AppIcon name="close" class="size-3.5" />
            </Button>
          </header>

          <div class="videos-inspector__thumb">
            <VideoThumbnail :src="selectedVideo.thumbnail" :alt="selectedVideo.title" fit="cover" />
            <span v-if="selectedVideo.duration" class="videos-inspector__duration app-mono">
              {{ formatDuration(selectedVideo.duration) }}
            </span>
          </div>

          <div class="videos-inspector__content">
            <div class="videos-inspector__states">
              <span :class="{ 'is-active': selectedVideo.is_read }">{{ selectedVideo.is_read ? '已看' : '未看' }}</span>
              <span v-if="selectedVideo.interaction_type === 1" class="is-active">喜欢</span>
              <span v-if="selectedVideo.interaction_type === 3" class="is-active">稍后看</span>
            </div>
            <h2>{{ selectedVideo.title }}</h2>
            <button v-if="selectedProfile" type="button" class="videos-inspector__source" @click="openProfile(selectedProfile)">
              {{ selectedSourceName }}
            </button>
            <p v-else class="videos-inspector__source">{{ selectedSourceName }}</p>

            <div v-if="selectedProgress > 0" class="videos-inspector__watch-progress">
              <div><span>观看进度</span><strong>{{ selectedProgress }}%</strong></div>
              <span class="videos-inspector__progress-track"><span :style="{ width: `${selectedProgress}%` }" /></span>
            </div>

            <dl>
              <div>
                <dt>上传时间</dt>
                <dd>{{ selectedDate }}</dd>
              </div>
              <div v-if="selectedVideo.site">
                <dt>站点</dt>
                <dd>{{ selectedVideo.site }}</dd>
              </div>
              <div>
                <dt>编号</dt>
                <dd class="app-mono">{{ selectedVideo.id }}</dd>
              </div>
            </dl>

            <Button class="videos-inspector__play" @click="openVideo(selectedVideo)">
              <AppIcon name="play" class="size-4 fill-current" />
              播放视频
            </Button>
            <p class="videos-inspector__hint">双击缩略图或按 Enter 也可直接播放</p>
          </div>
        </aside>
      </Transition>
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
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
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
import { pickPrimaryProfile, profileDisplayNames } from '@/features/video/composables/useProfileNavigation'
import type { VideoListItem } from '@/features/video/types/video'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
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
const selectedVideo = ref<VideoListItem | null>(null)
const videoChildRef = ref<{ refresh?: () => void } | null>(null)
const remoteSearchRef = ref<{ refresh?: () => void } | null>(null)
const remoteSite = ref('')
const searchMode = ref<'local' | 'remote'>('local')
const childFilters = computed(() => filters.value)
const viewPreferenceKey = computed(() => `local:${activeTab.value}`)
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

const selectedProfile = computed(() => selectedVideo.value ? pickPrimaryProfile(selectedVideo.value) : null)
const selectedSourceName = computed(() => selectedVideo.value ? profileDisplayNames(selectedVideo.value, '未知来源') : '')
const selectedDate = computed(() => {
  const value = selectedVideo.value?.uploaded_at || selectedVideo.value?.created_at
  return value ? formatDate(value) : '未知'
})
const selectedProgress = computed(() => {
  const video = selectedVideo.value
  if (!video?.duration) return 0
  return Math.min(100, Math.round((Number(video.last_position || 0) / Number(video.duration)) * 100))
})

const handleLoaded = (items: unknown[]) => {
  loadError.value = null
  if (selectedVideo.value && !items.some((item) => (item as VideoListItem)?.id === selectedVideo.value?.id)) {
    selectedVideo.value = null
  }
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

watch(childFilters, () => { selectedVideo.value = null }, { deep: true })
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
  selectedVideo.value = null
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

.videos-workbench__toolbar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  min-height: 4.25rem;
  align-items: center;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 clamp(1.25rem, 2.5vw, 2.5rem);
  background: hsl(var(--background));
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

.videos-workbench__filters {
  display: flex;
  min-height: 2.75rem;
  align-items: center;
  gap: 0.375rem;
  padding: 0 clamp(1.25rem, 2.5vw, 2.5rem);
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--muted) / 0.14);
}

.videos-workbench__filters > span {
  margin-right: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.videos-workbench__filters button {
  display: inline-flex;
  min-height: 1.625rem;
  align-items: center;
  gap: 0.3rem;
  border: 1px solid hsl(var(--border) / 0.58);
  border-radius: var(--radius-sm);
  padding: 0 0.45rem;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.6875rem;
  cursor: pointer;
}

.videos-workbench__filters button:hover {
  border-color: hsl(var(--primary) / 0.42);
}

.videos-workbench__filters .videos-workbench__clear {
  margin-left: auto;
  border-color: transparent;
  background: transparent;
  color: hsl(var(--muted-foreground));
}

.videos-workbench__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}

.videos-workbench__body.has-inspector {
  grid-template-columns: minmax(0, 1fr) 20rem;
}

.videos-workbench__canvas {
  min-width: 0;
  padding: 1.25rem clamp(1.25rem, 2.5vw, 2.5rem) 3rem;
}

.videos-workbench__error {
  margin-bottom: 1rem;
}

.videos-workbench__empty {
  min-height: 28rem;
}

.videos-inspector {
  position: sticky;
  top: 4.25rem;
  min-width: 0;
  min-height: calc(100vh - var(--app-titlebar-height) - 4.25rem);
  border-left: 1px solid var(--app-hairline);
  background: hsl(var(--background));
}

.videos-inspector__header {
  display: flex;
  min-height: 3rem;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 0.75rem 0 1rem;
  font-size: 0.75rem;
  font-weight: 650;
}

.videos-inspector__thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  margin: 1rem;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: hsl(var(--muted));
}

.videos-inspector__duration {
  position: absolute;
  right: 0.5rem;
  bottom: 0.5rem;
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.35rem;
  background: hsl(0 0% 0% / 0.78);
  color: white;
  font-size: 0.625rem;
}

.videos-inspector__content {
  padding: 0 1rem 1.5rem;
}

.videos-inspector__states {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.videos-inspector__states span {
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.4rem;
  background: hsl(var(--muted) / 0.48);
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  font-weight: 600;
}

.videos-inspector__states span.is-active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
}

.videos-inspector h2 {
  margin: 0.75rem 0 0;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.4;
}

.videos-inspector__source {
  margin: 0.45rem 0 0;
  border: 0;
  padding: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  text-align: left;
}

button.videos-inspector__source {
  cursor: pointer;
}

button.videos-inspector__source:hover {
  color: hsl(var(--primary));
}

.videos-inspector__watch-progress {
  margin-top: 1rem;
}

.videos-inspector__watch-progress > div {
  display: flex;
  justify-content: space-between;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.videos-inspector__watch-progress strong {
  color: hsl(var(--foreground));
}

.videos-inspector__progress-track {
  display: block;
  height: 3px;
  margin-top: 0.4rem;
  overflow: hidden;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.1);
}

.videos-inspector__progress-track span {
  display: block;
  height: 100%;
  background: hsl(var(--primary));
}

.videos-inspector dl {
  margin: 1.25rem 0 0;
  border-top: 1px solid var(--app-hairline);
}

.videos-inspector dl div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: 0.75rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--app-hairline);
  font-size: 0.6875rem;
}

.videos-inspector dt {
  color: hsl(var(--muted-foreground));
}

.videos-inspector dd {
  margin: 0;
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.videos-inspector__play {
  width: 100%;
  margin-top: 1.25rem;
}

.videos-inspector__hint {
  margin: 0.6rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  text-align: center;
}

.inspector-enter-active,
.inspector-leave-active {
  transition: opacity var(--duration-base) var(--ease-default);
}

.inspector-enter-from,
.inspector-leave-to {
  opacity: 0;
}

@media (max-width: 1180px) {
  .videos-workbench__toolbar {
    padding-block: 0.5rem;
  }

  .videos-workbench__body.has-inspector {
    grid-template-columns: minmax(0, 1fr) 18rem;
  }
}

@media (max-width: 880px) {
  .videos-workbench__body.has-inspector {
    grid-template-columns: 1fr;
  }

  .videos-inspector {
    position: fixed;
    top: var(--app-titlebar-height);
    right: 0;
    bottom: 0;
    z-index: var(--z-sheet);
    width: min(22rem, 92vw);
    overflow-y: auto;
    box-shadow: -1rem 0 2.5rem hsl(var(--foreground) / 0.12);
  }
}
</style>
