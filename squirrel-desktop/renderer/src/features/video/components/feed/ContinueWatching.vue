<template>
  <section v-if="historyItems.length > 0 || loading || loadError" class="continue-rail">
    <header class="continue-rail__header">
      <h2>继续观看</h2>
      <Button text severity="secondary" size="sm" @click="$emit('viewMore')">
        全部
        <AppIcon name="chevronRight" class="size-3.5" />
      </Button>
    </header>

    <div v-if="loadError && !loading && historyItems.length === 0" class="continue-rail__state">
      <AppEmptyState variant="error" title="继续观看加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="loading && historyItems.length === 0" class="continue-rail__track" aria-label="正在加载继续观看">
      <div v-for="index in 4" :key="index" class="continue-rail__skeleton">
        <div class="continue-rail__skeleton-thumb" />
        <div class="continue-rail__skeleton-copy">
          <span />
          <span />
        </div>
      </div>
    </div>

    <ol v-else class="continue-rail__track" aria-label="未完成内容">
      <li v-for="item in historyItems" :key="item.history_id">
        <button
          type="button"
          class="continue-rail__card"
          :aria-label="`继续播放：${item.title}`"
          @pointerenter="prefetchPlayback(item)"
          @pointerdown.left="prefetchPlayback(item)"
          @click="$emit('openModal', item)"
        >
          <span class="continue-rail__visual">
            <VideoThumbnail :src="item.thumbnail" :alt="item.title" fit="cover" interactive />
            <span
              class="continue-rail__progress"
              role="progressbar"
              :aria-label="`已观看 ${progressPercent(item)}%`"
              :aria-valuenow="progressPercent(item)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <span :style="{ width: `${progressPercent(item)}%` }" />
            </span>
          </span>

          <span class="continue-rail__copy">
            <span class="continue-rail__title">{{ item.title }}</span>
            <span class="continue-rail__meta">
              {{ progressPercent(item) }}% · 剩余 {{ remainingDuration(item) }}
            </span>
          </span>
        </button>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { Button } from '@/shared/ui/button'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'
import { errorMessage } from '@/shared/lib/errorMessage'
import { formatDuration } from '@/shared/lib/dateFormat'
import { Logger } from '@/shared/lib/logger'
import type { VideoHistoryEntry, VideoProfile } from '@/features/video/types/video'

defineEmits<{
  openModal: [video: VideoHistoryEntry]
  viewMore: []
  goToProfile: [profile: VideoProfile]
  goToSubscription: [id: number | string | null | undefined]
}>()

const { getWatchHistory } = useVideoHistory()
const historyItems = ref<VideoHistoryEntry[]>([])
const loading = ref(false)
const loadError = ref('')
const MIN_CONTINUE_PROGRESS = 0.01
const MAX_CONTINUE_PROGRESS = 0.95

const getProgress = (video: VideoHistoryEntry) => {
  const duration = Number(video.duration || 0)
  return duration > 0
    ? Math.max(0, Math.min(1, Number(video.last_position || 0) / duration))
    : 0
}

const progressPercent = (video: VideoHistoryEntry) => Math.round(getProgress(video) * 100)
const remainingDuration = (video: VideoHistoryEntry) => formatDuration(
  Math.max(0, Number(video.duration || 0) - Number(video.last_position || 0)),
)

const prefetchPlayback = (video: VideoHistoryEntry) => {
  void prefetchDesktopPlaybackSource(video)
}

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const { items } = await getWatchHistory(1, { pageSize: 30 })
    historyItems.value = items
      .filter((item) => {
        const progress = getProgress(item)
        return progress >= MIN_CONTINUE_PROGRESS && progress < MAX_CONTINUE_PROGRESS
      })
      .slice(0, 4)
  } catch (error) {
    Logger.error('Failed to load continue watching history:', error)
    historyItems.value = []
    loadError.value = errorMessage(error, '无法加载继续观看，请稍后重试。')
  } finally {
    loading.value = false
  }
}

onMounted(load)
defineExpose({ refresh: load })
</script>

<style scoped>
/* Thin horizontal rail above the feed — not a boxed SaaS module. */
.continue-rail {
  min-width: 0;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
}

.continue-rail__header {
  display: flex;
  min-height: 2.5rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.5rem 0.875rem;
  border-bottom: 1px solid hsl(var(--border));
}

.continue-rail__header h2 {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.continue-rail__track {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(10.5rem, 1fr);
  gap: 0.625rem;
  margin: 0;
  padding: 0.75rem 0.875rem;
  overflow-x: auto;
  list-style: none;
  scrollbar-width: thin;
}

.continue-rail__track > li {
  min-width: 0;
}

.continue-rail__card {
  display: grid;
  width: 100%;
  min-width: 0;
  gap: 0.375rem;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.continue-rail__card:hover .continue-rail__visual,
.continue-rail__card:focus-visible .continue-rail__visual {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.16);
}

.continue-rail__card:focus-visible {
  outline: none;
}

.continue-rail__card:focus-visible .continue-rail__visual {
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.45);
}

.continue-rail__visual {
  position: relative;
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.continue-rail__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 2;
  height: 3px;
  overflow: hidden;
  background: var(--app-media-progress-track);
}

.continue-rail__progress > span {
  display: block;
  height: 100%;
  background: hsl(var(--primary));
}

.continue-rail__copy {
  display: grid;
  min-width: 0;
  gap: 0.125rem;
}

.continue-rail__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.continue-rail__meta {
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.continue-rail__state {
  min-height: 8rem;
  padding: 0.75rem;
}

.continue-rail__skeleton {
  display: grid;
  gap: 0.375rem;
}

.continue-rail__skeleton-thumb {
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.55);
}

.continue-rail__skeleton-copy {
  display: grid;
  gap: 0.25rem;
}

.continue-rail__skeleton-copy > span {
  display: block;
  height: 0.625rem;
  border-radius: 999px;
  background: hsl(var(--muted) / 0.55);
}

.continue-rail__skeleton-copy > span:last-child {
  width: 55%;
}

@media (prefers-reduced-motion: reduce) {
  .continue-rail__card,
  .continue-rail__visual {
    transition: none;
  }
}
</style>
