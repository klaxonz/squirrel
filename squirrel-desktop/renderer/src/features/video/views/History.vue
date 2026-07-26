<template>
  <AppPageShell class="history-page" variant="compact" surface="organize" width="media">
    <AppToolbarFrame bordered sticky boundary="media" divider="content">
      <div class="history-toolbar">
        <AppSectionNav
          class="app-section-nav--optical"
          :model-value="historyMode"
          :options="modeOptions"
          aria-label="历史记录范围"
          @change="handleModeChange"
        />
        <div class="history-toolbar__actions">
          <Button
            text severity="secondary"
            size="sm" icon-only
            title="刷新历史"
            aria-label="刷新历史"
            :disabled="loading"
            @click="loadData"
          >
            <AppSpinner v-if="loading" size="sm" />
            <AppIcon v-else name="refresh" class="size-4" />
          </Button>
          <Button
            v-if="videos.length && !isContinueMode"
            text severity="secondary"
            size="sm" icon-only
            class="history-toolbar__clear"
            title="清空历史"
            aria-label="清空历史"
            @click="showClearConfirm = true"
          >
            <AppIcon name="trash" class="size-4" />
          </Button>
        </div>
      </div>
    </AppToolbarFrame>

    <main class="app-media-content-frame history-content">
      <div v-if="loading && videos.length === 0" class="history-groups" aria-label="正在加载历史记录">
        <section class="history-day">
          <div class="history-day__header">
            <div class="history-day__heading">
              <AppSkeleton width="3rem" height="1.25rem" rounded="var(--radius-sm)" shimmer />
              <AppSkeleton width="7rem" height="0.875rem" rounded="var(--radius-sm)" shimmer />
            </div>
          </div>
          <div class="history-day__items">
            <HistoryItemSkeleton v-for="itemIndex in 6" :key="itemIndex" />
          </div>
        </section>
      </div>

      <div v-else-if="loadError" class="app-page-empty app-page-empty--compact">
        <AppEmptyState variant="error" title="加载失败" :copy="loadError">
          <template #actions>
            <Button severity="secondary" outlined size="sm" @click="loadData">重试</Button>
          </template>
        </AppEmptyState>
      </div>

      <div v-else-if="groupedVideos.length === 0" class="app-page-empty app-page-empty--compact">
        <AppEmptyState variant="plain" icon="history" :title="emptyTitle" :copy="emptyDescription" />
      </div>

      <!-- Stable list contract for filters, visual checks and CDP probes. -->
      <div
        v-else
        class="history-groups"
        data-history-list
        :data-history-mode="historyMode"
        :data-history-count="String(displayVideos.length)"
      >
        <section v-for="group in groupedVideos" :key="group.key" class="history-day" data-history-day>
          <header class="history-day__header">
            <div class="history-day__heading">
              <h2 class="history-day__title">{{ group.label }}</h2>
              <span v-if="group.detail" class="history-day__detail">{{ group.detail }}</span>
            </div>
          </header>

          <div class="history-day__items">
            <HistoryItem
              v-for="video in group.items"
              :key="video.history_id"
              :video="video"
              @open="handleOpenVideo"
              @open-profile="handleOpenProfile"
              @delete="handleDeleteItem"
            />
          </div>
        </section>
      </div>

      <div v-if="loading && videos.length > 0" class="app-page-actions app-page-actions--loose">
        <AppSpinner />
      </div>

      <div v-else-if="hasMore" class="app-page-actions app-page-actions--loose">
        <Button severity="secondary" outlined @click="loadMore">加载更多</Button>
      </div>
    </main>

    <ConfirmDialog
      v-model:open="showClearConfirm"
      icon="trash"
      icon-bg-class="bg-destructive/10 text-destructive"
      title="清空所有历史记录？"
      cancel-label="取消"
      confirm-label="确认清空"
      confirm-variant="destructive"
      @confirm="handleClearHistory"
    >
      <template #description>
        此操作将永久移除你账户下的所有观看记录，包括各端同步的进度信息。该操作不可撤销。
      </template>
    </ConfirmDialog>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import HistoryItem from '@/features/video/components/history/HistoryItem.vue'
import HistoryItemSkeleton from '@/features/video/components/history/HistoryItemSkeleton.vue'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'
import { useProfileNavigation } from '@/features/video/composables/useProfileNavigation'
import type { VideoHistoryEntry, VideoProfile } from '@/features/video/types/video'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useUIStore } from '@/shared/stores/ui'
import { Button } from '@/shared/ui/button'
import { useVideoHistory } from '../composables/useVideoHistory'

defineOptions({ name: 'History' })

const PAGE_SIZE = 100
const DAY_MS = 86_400_000

type HistoryMode = 'all' | 'continue'

type HistoryDayGroup = {
  key: string
  label: string
  detail: string
  items: VideoHistoryEntry[]
}

const modeOptions = [
  { value: 'all', label: '全部记录' },
  { value: 'continue', label: '未看完' },
] as const

const weekdayFormatter = new Intl.DateTimeFormat('zh-CN', { weekday: 'long' })
const monthDayFormatter = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' })
const fullDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const { openProfile } = useProfileNavigation(router)
const searchQuery = computed(() => uiStore.getSearchQuery('history'))
const searchTrigger = computed(() => uiStore.getSearchTrigger('history'))
const { getWatchHistory, clearHistory, deleteHistoryEntry } = useVideoHistory()

const handleOpenProfile = (profile: VideoProfile) => {
  void openProfile(profile)
}

const videos = ref<VideoHistoryEntry[]>([])
const loading = ref(false)
const loadError = ref('')
const page = ref(1)
const total = ref(0)
const query = ref('')
const showClearConfirm = ref(false)
let latestRequestId = 0

const historyMode = computed<HistoryMode>(() => route.query.mode === 'continue' ? 'continue' : 'all')
const isContinueMode = computed(() => historyMode.value === 'continue')

const getProgress = (video: VideoHistoryEntry) => {
  const duration = Number(video.duration)
  return duration > 0 ? Math.max(0, Math.min(1, Number(video.last_position) / duration)) : 0
}

const displayVideos = computed(() => {
  if (!isContinueMode.value) return videos.value
  return videos.value.filter((video) => {
    const progress = getProgress(video)
    return progress > 0.01 && progress < 0.95
  })
})

const emptyTitle = computed(() => {
  if (query.value) return '没有匹配的历史记录'
  return isContinueMode.value ? '没有未看完的视频' : '暂无历史记录'
})

const emptyDescription = computed(() => {
  if (query.value) return '尝试调整搜索词，或切换到全部记录。'
  return isContinueMode.value ? '最近未看完的视频会集中显示在这里。' : '观看视频后，记录会按日期自动归档。'
})

const hasMore = computed(() => videos.value.length < total.value)

const getDayDescriptor = (playedAt: string | null) => {
  if (!playedAt) {
    return { key: 'unknown', label: '时间未知', detail: '' }
  }

  const date = new Date(playedAt)
  if (Number.isNaN(date.getTime())) {
    return { key: 'unknown', label: '时间未知', detail: '' }
  }

  const year = date.getFullYear()
  const month = date.getMonth()
  const day = date.getDate()
  const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  const today = new Date()
  const daySerial = Date.UTC(year, month, day)
  const todaySerial = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  const dayOffset = Math.round((todaySerial - daySerial) / DAY_MS)
  const calendarDate = new Date(year, month, day)

  if (dayOffset === 0) {
    return { key, label: '今天', detail: `${monthDayFormatter.format(calendarDate)} · ${weekdayFormatter.format(calendarDate)}` }
  }
  if (dayOffset === 1) {
    return { key, label: '昨天', detail: `${monthDayFormatter.format(calendarDate)} · ${weekdayFormatter.format(calendarDate)}` }
  }
  if (year === today.getFullYear()) {
    return { key, label: monthDayFormatter.format(calendarDate), detail: weekdayFormatter.format(calendarDate) }
  }
  return { key, label: fullDateFormatter.format(calendarDate), detail: weekdayFormatter.format(calendarDate) }
}

const getPlayedAtTimestamp = (playedAt: string | null) => {
  if (!playedAt) return 0
  const timestamp = Date.parse(playedAt)
  return Number.isNaN(timestamp) ? 0 : timestamp
}

const groupedVideos = computed<HistoryDayGroup[]>(() => {
  const groups = new Map<string, HistoryDayGroup>()
  const sortedVideos = [...displayVideos.value].sort(
    (left, right) => getPlayedAtTimestamp(right.played_at) - getPlayedAtTimestamp(left.played_at),
  )

  sortedVideos.forEach((video) => {
    const descriptor = getDayDescriptor(video.played_at)
    const group = groups.get(descriptor.key)
    if (group) {
      group.items.push(video)
      return
    }
    groups.set(descriptor.key, { ...descriptor, items: [video] })
  })

  return [...groups.values()]
})

const loadData = async ({ append = false } = {}) => {
  const requestId = ++latestRequestId
  loading.value = true
  loadError.value = ''
  try {
    const nextPage = append ? page.value + 1 : 1
    const data = await getWatchHistory(nextPage, { pageSize: PAGE_SIZE, query: query.value })
    if (requestId !== latestRequestId) return
    videos.value = append ? [...videos.value, ...data.items] : data.items
    page.value = data.page
    total.value = data.total
  } catch (err) {
    if (requestId !== latestRequestId) return
    loadError.value = errorMessage(err, '加载历史记录失败')
  } finally {
    if (requestId === latestRequestId) {
      loading.value = false
    }
  }
}

const loadMore = () => loadData({ append: true })

const handleModeChange = (value: string | number) => {
  const mode = value as HistoryMode
  const nextQuery = { ...route.query }
  if (mode === 'continue') {
    nextQuery.mode = 'continue'
  } else {
    delete nextQuery.mode
  }
  router.replace({ name: 'History', query: nextQuery })
}

const handleClearHistory = async () => {
  await clearHistory()
  videos.value = []
  total.value = 0
  showClearConfirm.value = false
}

const handleDeleteItem = async (historyId: number) => {
  await deleteHistoryEntry(historyId)
  videos.value = videos.value.filter((video) => video.history_id !== historyId)
  total.value = Math.max(0, total.value - 1)
}

const handleOpenVideo = (video: VideoHistoryEntry) => {
  rememberVideoPlaybackSeed(video)
  void prefetchDesktopPlaybackSource(video)
  router.push(`/video/${video.id}`)
}

watch(searchTrigger, () => {
  query.value = searchQuery.value.trim()
  loadData()
})

onMounted(() => {
  query.value = searchQuery.value.trim()
  loadData()
})
</script>

<style scoped>
.history-content {
  max-width: var(--app-content-feed-max);
  margin-inline: auto;
  padding-block: var(--space-4) var(--app-content-padding-bottom);
}

.history-toolbar {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.history-toolbar__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
}

.history-toolbar__clear {
  color: hsl(var(--muted-foreground));
}

.history-toolbar__clear:hover,
.history-toolbar__clear:focus-visible {
  border-color: hsl(var(--destructive) / 0.28);
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.history-groups {
  display: grid;
  gap: var(--space-4);
}

.history-day {
  display: grid;
  gap: 0;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  padding: 0;
}

.history-day__header {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: var(--space-4);
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid hsl(var(--border));
}

.history-day__heading {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: var(--space-2);
}

.history-day__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.history-day__detail {
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.85);
  font-size: 0.75rem;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-day__items {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  row-gap: 0;
}

.history-day__items > * + * {
  border-top: 1px solid hsl(var(--border));
}
</style>
