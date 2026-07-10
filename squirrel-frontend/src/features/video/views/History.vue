<template>
  <AppPageShell class="history-page" variant="compact" :fill="false">
    <AppToolbarFrame bordered compact sticky>
      <div class="history-toolbar">
        <div class="history-toolbar__lead">
          <p class="history-toolbar__summary" aria-live="polite">{{ pageSubtitle }}</p>
        </div>
        <div class="history-toolbar__actions">
          <AppSegmentedControl
            :model-value="historyMode"
            :options="modeOptions"
            aria-label="历史记录范围"
            size="sm"
            @change="handleModeChange"
          />
          <Button
            variant="ghost"
            size="icon-sm"
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
            variant="ghost"
            size="icon-sm"
            class="text-destructive hover:bg-destructive/10 hover:text-destructive"
            title="清空历史"
            aria-label="清空历史"
            @click="showClearConfirm = true"
          >
            <AppIcon name="trash" class="size-4" />
          </Button>
        </div>
      </div>
    </AppToolbarFrame>

    <main class="app-page-content history-content">
      <div v-if="loading && videos.length === 0" class="history-groups" aria-label="正在加载历史记录">
        <section v-for="groupIndex in 2" :key="groupIndex" class="history-day">
          <div class="history-day__header">
            <AppSkeleton width="7rem" height="1.25rem" rounded="var(--radius-sm)" shimmer />
            <AppSkeleton width="2.5rem" height="1rem" rounded="var(--radius-sm)" shimmer />
          </div>
          <div class="history-day__items">
            <AppSkeleton
              v-for="itemIndex in 4"
              :key="itemIndex"
              height="8.125rem"
              rounded="var(--radius-lg)"
              shimmer
            />
          </div>
        </section>
      </div>

      <div v-else-if="loadError" class="app-page-empty app-page-empty--compact">
        <AppEmptyState variant="error" title="加载失败" :copy="loadError">
          <template #actions>
            <Button variant="outline" size="sm" @click="loadData">重试</Button>
          </template>
        </AppEmptyState>
      </div>

      <div v-else-if="groupedVideos.length === 0" class="app-page-empty app-page-empty--compact">
        <AppEmptyState variant="plain" icon="history" :title="emptyTitle" :copy="emptyDescription" />
      </div>

      <div v-else class="history-groups">
        <section v-for="group in groupedVideos" :key="group.key" class="history-day">
          <header class="history-day__header">
            <div class="history-day__heading">
              <h2 class="history-day__title">{{ group.label }}</h2>
              <span v-if="group.detail" class="history-day__detail">{{ group.detail }}</span>
            </div>
            <span class="history-day__count">{{ group.items.length }} 条</span>
          </header>

          <div class="history-day__items">
            <HistoryItem
              v-for="video in group.items"
              :key="video.history_id"
              :video="video"
              @open="handleOpenVideo"
              @delete="handleDeleteItem"
            />
          </div>
        </section>
      </div>

      <div v-if="loading && videos.length > 0" class="app-page-actions app-page-actions--loose">
        <AppSpinner />
      </div>

      <div v-else-if="hasMore" class="app-page-actions app-page-actions--loose">
        <Button variant="outline" @click="loadMore">加载更多</Button>
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
import { storeToRefs } from 'pinia'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import HistoryItem from '@/features/video/components/history/HistoryItem.vue'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import type { VideoHistoryEntry } from '@/features/video/types/video'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useUIStore } from '@/shared/stores/ui'
import { Button } from '@/shared/ui/button'
import { useVideoHistory } from '../composables/useVideoHistory'

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
const { searchQuery, searchTrigger } = storeToRefs(uiStore)
const { getWatchHistory, clearHistory, deleteHistoryEntry } = useVideoHistory()

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

const pageSubtitle = computed(() => {
  if (loading.value && videos.value.length === 0) return '正在加载观看记录'
  const loadedText = isContinueMode.value
    ? `已加载 ${displayVideos.value.length} 条未看完记录`
    : `共 ${total.value} 条记录，已加载 ${videos.value.length} 条`
  return query.value ? `${loadedText} · 搜索“${query.value}”` : loadedText
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
.history-page {
  --app-page-max-width: 94rem;
}

.history-content {
  padding-top: var(--space-5);
}

.history-toolbar {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.history-toolbar__lead {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  gap: var(--space-3);
}

.history-toolbar__summary {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-toolbar__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
}

.history-groups {
  display: grid;
  gap: var(--space-8);
}

.history-day {
  display: grid;
  gap: var(--space-3);
}

.history-day__header {
  display: flex;
  min-width: 0;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--app-hairline);
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
  font-family: var(--app-heading-font);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.3;
}

.history-day__detail,
.history-day__count {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.3;
}

.history-day__detail {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-day__count {
  flex: 0 0 auto;
  font-variant-numeric: tabular-nums;
}

.history-day__items {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  column-gap: var(--space-6);
  row-gap: 0;
}

@media (min-width: 1500px) {
  .history-day__items {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
