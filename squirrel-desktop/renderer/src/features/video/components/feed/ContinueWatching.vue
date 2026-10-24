<template>
  <section v-if="historyItems.length > 0 || loading || loadError" class="continue-rail">
    <header class="continue-rail__header">
      <div class="continue-rail__heading">
        <h2>继续观看</h2>
        <span v-if="historyItems.length" class="continue-rail__count">{{ historyItems.length }}</span>
      </div>
      <Button variant="secondary" size="sm" class="continue-rail__more" @click="$emit('viewMore')">
        查看全部
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
            <span class="continue-rail__resume">
              <AppIcon name="play" class="size-3" />
              续播
            </span>
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
              <span class="continue-rail__percent">{{ progressPercent(item) }}%</span>
              <span>剩余 {{ remainingDuration(item) }}</span>
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
/* Resume shelf stays open to the page canvas while its media remains primary. */
.continue-rail {
  min-width: 0;
}

.continue-rail__header {
  display: flex;
  min-height: 1.75rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.continue-rail__heading {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.45rem;
}

.continue-rail__header h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--app-text-base);
  font-weight: 650;
  letter-spacing: -0.01em;
}

.continue-rail__count {
  display: inline-flex;
  min-width: 1.25rem;
  height: 1.25rem;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  padding-inline: 0.35rem;
}

.continue-rail__more {
  color: hsl(var(--muted-foreground));
}

.continue-rail__track {
  display: grid;
  grid-auto-flow: column;
  /* Four-up shelf: percentage columns keep all four visible instead of letting
     1fr collapse to max-content inside the horizontal scroll container. */
  grid-auto-columns: calc((100% - 2.1rem) / 4);
  gap: 0.7rem;
  margin: 0;
  padding: 0;
  overflow-x: auto;
  list-style: none;
  scrollbar-width: none;
}

.continue-rail__track > li {
  min-width: 0;
}

.continue-rail__card {
  display: grid;
  width: 100%;
  min-width: 0;
  gap: 0.45rem;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.continue-rail__card:hover .continue-rail__visual,
.continue-rail__card:focus-visible .continue-rail__visual {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.14);
}

.continue-rail__card:hover .continue-rail__resume {
  opacity: 1;
  transform: translateY(0);
}

.continue-rail__card:focus-visible {
  outline: none;
}

.continue-rail__card:focus-visible .continue-rail__visual {
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.8);
}

.continue-rail__visual {
  position: relative;
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.continue-rail__resume {
  position: absolute;
  left: 0.4rem;
  bottom: 0.55rem;
  z-index: 3;
  display: inline-flex;
  height: 1.35rem;
  align-items: center;
  gap: 0.2rem;
  border-radius: var(--radius-sm);
  padding: 0 0.45rem 0 0.35rem;
  background: hsl(var(--overlay) / 0.72);
  color: hsl(var(--app-media-on-image));
  font-size: var(--app-text-xs);
  font-weight: 600;
  opacity: 0;
  transform: translateY(0.15rem);
  transition:
    opacity var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
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
  background: var(--app-media-progress-fill);
}

.continue-rail__copy {
  display: grid;
  min-width: 0;
  gap: 0.15rem;
}

.continue-rail__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: var(--app-text-md);
  font-weight: 600;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.continue-rail__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.continue-rail__percent {
  color: hsl(var(--foreground));
  font-weight: 600;
}

.continue-rail__state {
  min-height: 8rem;
  padding: 0.75rem;
}

.continue-rail__skeleton {
  display: grid;
  gap: 0.4rem;
}

.continue-rail__skeleton-thumb {
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.55);
}

.continue-rail__skeleton-copy {
  display: grid;
  gap: 0.25rem;
}

.continue-rail__skeleton-copy > span {
  display: block;
  height: 0.625rem;
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.55);
}

.continue-rail__skeleton-copy > span:last-child {
  width: 55%;
}

@media (hover: none) {
  .continue-rail__resume {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .continue-rail__card,
  .continue-rail__visual,
  .continue-rail__resume {
    transition: none;
  }

  .continue-rail__resume {
    opacity: 1;
    transform: none;
  }
}
 </style>
