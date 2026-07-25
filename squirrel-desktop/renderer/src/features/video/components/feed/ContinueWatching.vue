<template>
  <section v-if="historyItems.length > 0 || loading || loadError" class="continue-workbench">
    <header class="continue-workbench__header">
      <div>
        <h2>继续观看</h2>
      </div>
      <Button text severity="secondary" size="sm" @click="$emit('viewMore')">
        观看记录
        <AppIcon name="chevronRight" class="size-3.5" />
      </Button>
    </header>

    <div v-if="loadError && !loading && historyItems.length === 0" class="continue-workbench__state">
      <AppEmptyState variant="error" title="继续观看加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="loading && historyItems.length === 0" class="continue-workbench__loading" aria-label="正在加载继续观看">
      <div v-for="index in 4" :key="index" class="continue-workbench__loading-card">
        <div class="continue-workbench__loading-thumb" />
        <div class="continue-workbench__loading-copy">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>

    <ol v-else class="continue-workbench__grid" aria-label="未完成内容">
      <li v-for="item in historyItems" :key="item.history_id">
        <button
          type="button"
          class="continue-workbench__card"
          :aria-label="`继续播放：${item.title}`"
          @pointerenter="prefetchPlayback(item)"
          @pointerdown.left="prefetchPlayback(item)"
          @click="$emit('openModal', item)"
        >
          <span class="continue-workbench__visual">
            <VideoThumbnail :src="item.thumbnail" :alt="item.title" fit="cover" interactive />
            <span
              class="continue-workbench__progress"
              role="progressbar"
              :aria-label="`已观看 ${progressPercent(item)}%`"
              :aria-valuenow="progressPercent(item)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <span :style="{ width: `${progressPercent(item)}%` }" />
            </span>
          </span>

          <span class="continue-workbench__copy">
            <span class="continue-workbench__source">{{ itemSource(item) }}</span>
            <span class="continue-workbench__title">{{ item.title }}</span>
            <span class="continue-workbench__meta">
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
const itemSource = (video: VideoHistoryEntry) => (
  video.subscriptions?.[0]?.name || video.actors?.[0]?.name || video.site || '本地媒体'
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
.continue-workbench {
  min-width: 0;
}

.continue-workbench__header {
  display: flex;
  min-height: 3.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  border-bottom: 1px solid var(--app-hairline);
}

.continue-workbench__header h2,
.continue-workbench__source {
  margin: 0;
}

.continue-workbench__header h2 {
  font-family: var(--font-display);
  font-size: 1.125rem;
  font-weight: 680;
  letter-spacing: -0.02em;
}

.continue-workbench__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.875rem 1.25rem;
  margin: 0;
  margin-top: 0.875rem;
  padding: 0;
  list-style: none;
}

.continue-workbench__grid > li {
  min-width: 0;
}

.continue-workbench__card {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  align-items: center;
  gap: 0.75rem;
  border: 0;
  border-radius: var(--app-card-radius);
  padding: 0.375rem;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 160ms ease;
}

.continue-workbench__card:hover {
  background: hsl(var(--accent) / 0.42);
}

.continue-workbench__card:focus-visible {
  outline: 2px solid hsl(var(--ring) / 0.72);
  outline-offset: 2px;
}

.continue-workbench__visual {
  position: relative;
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--app-media-thumb-placeholder);
}

.continue-workbench__copy {
  display: grid;
  min-width: 0;
  align-content: center;
  gap: 0.2rem;
}

.continue-workbench__source {
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.continue-workbench__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 620;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.continue-workbench__meta {
  overflow: hidden;
  margin-top: 0.05rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.continue-workbench__progress {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  height: 3px;
  overflow: hidden;
  background: hsl(0 0% 0% / 0.28);
}

.continue-workbench__progress span {
  display: block;
  height: 100%;
  background: hsl(var(--primary));
}

.continue-workbench__state {
  min-height: 12rem;
}

.continue-workbench__loading {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.875rem 1.25rem;
  margin-top: 0.875rem;
}

.continue-workbench__loading-card {
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  align-items: center;
  gap: 0.75rem;
  padding: 0.375rem;
}

.continue-workbench__loading-thumb,
.continue-workbench__loading-copy span {
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.54);
  animation: continue-pulse 1.25s ease-in-out infinite alternate;
}

.continue-workbench__loading-thumb {
  aspect-ratio: 16 / 9;
}

.continue-workbench__loading-copy {
  display: grid;
  gap: 0.375rem;
}

.continue-workbench__loading-copy span {
  display: block;
  height: 0.625rem;
}

.continue-workbench__loading-copy span:nth-child(2) {
  width: 92%;
  height: 0.875rem;
}

.continue-workbench__loading-copy span:last-child {
  width: 62%;
}

@keyframes continue-pulse {
  to { opacity: 0.55; }
}

@media (max-width: 1280px) {
  .continue-workbench__grid,
  .continue-workbench__loading {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .continue-workbench__grid,
  .continue-workbench__loading {
    grid-template-columns: minmax(0, 1fr);
  }

  .continue-workbench__card,
  .continue-workbench__loading-card {
    grid-template-columns: 7rem minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .continue-workbench__loading-thumb,
  .continue-workbench__loading-copy span {
    animation: none;
  }

  .continue-workbench__card {
    transition: none;
  }
}
</style>
