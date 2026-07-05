<template>
  <AppPageShell variant="compact">
    <AppToolbarFrame bordered compact>
      <div class="app-page-toolbar">
        <div class="app-page-toolbar__title">
          <h1 class="app-h3 truncate">{{ pageTitle }}</h1>
          <p class="mt-0.5 text-xs text-muted-foreground">{{ pageSubtitle }}</p>
        </div>

        <div class="app-page-toolbar__actions">
          <Button variant="ghost" size="icon-sm" title="刷新历史" aria-label="刷新历史" @click="loadData">
            <AppSpinner v-if="loading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </Button>
          <Button v-if="isContinueMode" variant="ghost" @click="router.push({ name: 'History' })">
            全部历史
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
            <AppIcon name="trash" class="h-4 w-4" />
          </Button>
        </div>
      </div>
    </AppToolbarFrame>

    <div class="flex-1">
      <main class="app-page-content history-content">
        <div v-if="loading && videos.length === 0" class="app-content-stack app-content-stack--feed">
          <div v-for="i in 2" :key="i" class="app-content-stack app-content-stack--dense">
            <AppSkeleton width="5rem" height="1.75rem" rounded="var(--radius)" shimmer />
            <div class="app-content-stack app-content-stack--dense history-skeleton-list">
              <AppSkeleton v-for="j in 3" :key="j" height="7rem" rounded="var(--radius-lg)" shimmer />
            </div>
          </div>
        </div>

        <div v-else-if="loadError" class="app-page-empty app-page-empty--compact">
          <AppEmptyState variant="error" title="加载失败" :copy="loadError">
            <template #actions>
              <Button variant="outline" size="sm" @click="loadData">重试</Button>
            </template>
          </AppEmptyState>
        </div>

        <div v-else-if="groupedVideos.length === 0" class="app-page-empty app-page-empty--compact">
          <AppEmptyState variant="plain" icon="time" :title="emptyTitle" :copy="emptyDescription" />
        </div>

        <div v-else class="app-content-stack app-content-stack--feed">
          <section v-if="featuredVideo" class="overflow-hidden rounded-lg border border-border/70 bg-card">
            <Button
              variant="ghost"
              class="app-featured-media group relative block w-full overflow-hidden text-left"
              @click="handleOpenVideo(featuredVideo)"
            >
              <VideoThumbnail
                :src="featuredVideo.thumbnail"
                :alt="featuredVideo.title"
                fit="responsive"
                class="absolute inset-0 h-full w-full"
              />
              <div class="history-featured__scrim" />
              <div class="absolute inset-x-0 bottom-0 h-1 bg-white/15">
                <div class="h-full bg-primary" :style="{ width: `${getProgress(featuredVideo) * 100}%` }" />
              </div>
              <div class="relative z-10 flex h-full max-w-3xl flex-col justify-end gap-3 p-5 text-white lg:p-6">
                <div class="flex items-center gap-2 text-xs font-medium text-white/80">
                  <span class="inline-flex items-center gap-1 rounded-md border border-white/20 bg-black/35 px-2 py-1">
                    <AppIcon name="playback" class="h-3.5 w-3.5" />
                    {{ featuredLabel }}
                  </span>
                  <span v-if="featuredVideo.duration" class="rounded-md border border-white/15 bg-black/35 px-2 py-1 tabular-nums">
                    {{ formatDuration(featuredVideo.duration) }}
                  </span>
                </div>
                <h2 class="line-clamp-2 text-2xl font-semibold leading-tight tracking-normal lg:text-3xl">
                  {{ featuredVideo.title }}
                </h2>
                <div class="flex flex-wrap items-center gap-2 text-sm text-white/75">
                  <span class="truncate">{{ getVideoSourceText(featuredVideo) }}</span>
                  <span v-if="featuredVideo.played_at">上次 {{ formatDate(featuredVideo.played_at) }}</span>
                  <span v-if="getProgress(featuredVideo) > 0">已看 {{ Math.round(getProgress(featuredVideo) * 100) }}%</span>
                </div>
              </div>
            </Button>
          </section>

          <section v-for="group in groupedVideos" :key="group.date" class="app-content-stack app-content-stack--dense">
            <div class="app-sticky-section-bar">
              <h3 class="text-xs font-semibold text-muted-foreground">{{ group.date }}</h3>
              <span class="text-xs text-muted-foreground">{{ group.items.length }} 条</span>
            </div>

            <div class="app-content-stack app-content-stack--dense history-item-list">
              <HistoryItem 
                v-for="video in group.items" 
                :key="video.history_id || video.id"
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
    </div>

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
import { onMounted, ref, computed, watch } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import HistoryItem from '@/features/video/components/history/HistoryItem.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { Button } from '@/shared/ui/button'
import { useVideoHistory } from '../composables/useVideoHistory'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import { useUIStore } from '@/shared/stores/ui'
import type { VideoHistoryEntry } from '@/features/video/types/video'

const PAGE_SIZE = 100

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
const isContinueMode = computed(() => route.query.mode === 'continue')
const pageTitle = computed(() => isContinueMode.value ? '继续观看' : '播放历史')
const pageSubtitle = computed(() => {
  const loaded = displayVideos.value.length
  const countText = isContinueMode.value ? `已加载 ${loaded} 条可继续观看` : `已加载 ${loaded} / ${total.value} 条`
  return query.value ? `${countText} · 搜索“${query.value}”` : countText
})
const emptyTitle = computed(() => isContinueMode.value ? '暂无继续观看' : '暂无历史记录')
const emptyDescription = computed(() => query.value ? '没有匹配的历史视频。' : (isContinueMode.value ? '未看完的视频会显示在这里。' : '观看过的视频会显示在这里。'))

const getProgress = (video: VideoHistoryEntry) => {
  const duration = Number(video.duration || 0)
  return duration > 0 ? Math.min(1, Number(video.last_position || 0) / duration) : 0
}

const displayVideos = computed(() => {
  if (!isContinueMode.value) return videos.value
  return videos.value.filter((video) => {
    const progress = getProgress(video)
    return progress > 0.01 && progress < 0.95
  })
})
const continueVideos = computed(() => videos.value.filter((video) => {
  const progress = getProgress(video)
  return progress > 0.01 && progress < 0.95
}))
const featuredVideo = computed(() => continueVideos.value[0] || displayVideos.value[0] || null)
const featuredLabel = computed(() => continueVideos.value.length > 0 ? '接着看' : '最近观看')
const hasMore = computed(() => videos.value.length < total.value)

const getVideoSourceText = (video: VideoHistoryEntry) => {
  const sources = video.subscriptions?.length ? video.subscriptions : video.actors
  return sources?.map((item) => item.name).filter(Boolean).join(' / ') || video.site || '未知作者'
}

const loadData = async ({ append = false } = {}) => {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    const nextPage = append ? page.value + 1 : 1
    const data = await getWatchHistory(nextPage, { pageSize: PAGE_SIZE, query: query.value })
    videos.value = append ? [...videos.value, ...(data.items || [])] : (data.items || [])
    page.value = data.page
    total.value = data.total
  } catch (err) {
    loadError.value = errorMessage(err, '加载历史记录失败')
  } finally {
    loading.value = false
  }
}

const loadMore = () => loadData({ append: true })

const handleClearHistory = async () => {
  await clearHistory()
  videos.value = []
  total.value = 0
  showClearConfirm.value = false
}

const handleDeleteItem = async (id: number | string) => {
  await deleteHistoryEntry(id)
  videos.value = videos.value.filter(v => (v.history_id || v.id) !== id)
  total.value = Math.max(0, total.value - 1)
}

const handleOpenVideo = (video: VideoHistoryEntry) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const groupedVideos = computed(() => {
  const groups: Record<string, VideoHistoryEntry[]> = {}
  displayVideos.value.forEach(v => {
    const date = v.played_at ? formatDate(v.played_at) : '未知时间'
    if (!groups[date]) groups[date] = []
    groups[date].push(v)
  })
  return Object.entries(groups).map(([date, items]) => ({ date, items }))
})

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
  --app-page-max-width: 1200px;
  padding-top: var(--space-5);
}

.history-skeleton-list,
.history-item-list {
  --app-content-stack-gap: var(--space-2);
}

.history-featured__scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, hsl(0 0% 0% / 0.74), hsl(0 0% 0% / 0.42) 52%, hsl(0 0% 0% / 0.12));
}
</style>
