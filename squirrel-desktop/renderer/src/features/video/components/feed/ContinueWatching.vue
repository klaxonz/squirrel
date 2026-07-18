<template>
  <section v-if="historyItems.length > 0 || loading || loadError" class="continue-workspace">
    <div class="continue-workspace__heading">
      <div>
        <p class="continue-workspace__eyebrow">WATCHING</p>
        <h2>继续观看</h2>
      </div>
      <button type="button" class="continue-workspace__more" @click="$emit('viewMore')">
        查看全部
        <AppIcon name="chevronRight" class="size-3.5" />
      </button>
    </div>

    <div v-if="loadError && !loading && historyItems.length === 0" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="error" title="继续观看加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="loading && historyItems.length === 0" class="continue-workspace__loading" aria-label="正在加载继续观看">
      <div class="continue-workspace__skeleton continue-workspace__skeleton--feature" />
      <div class="continue-workspace__skeleton continue-workspace__skeleton--queue" />
    </div>

    <div v-else-if="featuredItem" class="continue-workspace__grid">
      <article
        class="continue-feature"
        role="button"
        tabindex="0"
        :aria-label="`继续播放：${featuredItem.title}`"
        @click="$emit('openModal', featuredItem)"
        @keydown.enter.prevent="$emit('openModal', featuredItem)"
        @keydown.space.prevent="$emit('openModal', featuredItem)"
      >
        <div class="continue-feature__content">
          <div class="continue-feature__copy">
            <p class="continue-feature__source">{{ itemSource(featuredItem) }}</p>
            <h3>{{ featuredItem.title }}</h3>
            <p class="continue-feature__meta">
              已观看 {{ progressPercent(featuredItem) }}%
              <span aria-hidden="true">·</span>
              剩余 {{ remainingDuration(featuredItem) }}
            </p>
          </div>

          <div class="continue-feature__actions">
            <Button class="continue-feature__play" @click.stop="$emit('openModal', featuredItem)">
              <AppIcon name="play" class="size-4 fill-current" />
              继续播放
            </Button>
            <Button variant="secondary" icon-only title="打开观看记录" aria-label="打开观看记录" @click.stop="$emit('viewMore')">
              <AppIcon name="history" class="size-4" />
            </Button>
          </div>
        </div>

        <div class="continue-feature__visual">
          <VideoThumbnail
            :src="featuredItem.thumbnail"
            :alt="featuredItem.title"
            fit="cover"
            interactive
            class="continue-feature__art"
          />
          <div class="continue-feature__shade" aria-hidden="true" />
        </div>

        <div
          class="continue-feature__progress"
          role="progressbar"
          :aria-valuenow="progressPercent(featuredItem)"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`已观看 ${progressPercent(featuredItem)}%`"
        >
          <span :style="{ width: `${progressPercent(featuredItem)}%` }" />
        </div>
      </article>

      <aside class="continue-queue" aria-label="待继续播放">
        <div class="continue-queue__header">
          <div>
            <p>待继续</p>
            <span>{{ queueItems.length }} 项待继续</span>
          </div>
          <AppIcon name="history" class="size-4" />
        </div>

        <div class="continue-queue__items">
          <button
            v-for="item in queueItems"
            :key="item.history_id"
            type="button"
            class="continue-queue__item"
            @click="$emit('openModal', item)"
          >
            <span class="continue-queue__thumb">
              <VideoThumbnail :src="item.thumbnail" :alt="item.title" fit="cover" />
              <span class="continue-queue__thumb-progress">
                <span :style="{ width: `${progressPercent(item)}%` }" />
              </span>
            </span>
            <span class="continue-queue__body">
              <strong>{{ item.title }}</strong>
              <small>{{ itemSource(item) }} · {{ progressPercent(item) }}%</small>
            </span>
            <AppIcon name="play" class="continue-queue__play size-3.5" />
          </button>
        </div>

        <button type="button" class="continue-queue__footer" @click="$emit('viewMore')">
          打开观看记录
          <AppIcon name="chevronRight" class="size-3.5" />
        </button>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { Button } from '@/shared/ui/button'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
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

const featuredItem = computed(() => historyItems.value[0] ?? null)
const queueItems = computed(() => historyItems.value.slice(1, 5))

const getProgress = (video: VideoHistoryEntry) => {
  const duration = Number(video.duration || 0)
  return duration > 0 ? Math.min(1, Number(video.last_position || 0) / duration) : 0
}

const progressPercent = (video: VideoHistoryEntry) => Math.round(getProgress(video) * 100)

const remainingDuration = (video: VideoHistoryEntry) => {
  return formatDuration(Math.max(0, Number(video.duration || 0) - Number(video.last_position || 0)))
}

const itemSource = (video: VideoHistoryEntry) => {
  return video.subscriptions?.[0]?.name || video.actors?.[0]?.name || video.site || '本地媒体'
}

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const { items } = await getWatchHistory(1, { pageSize: 30 })
    historyItems.value = items.filter((item) => getProgress(item) > 0 && getProgress(item) < 1).slice(0, 5)
  } catch (e) {
    Logger.error('Failed to load continue watching history:', e)
    historyItems.value = []
    loadError.value = errorMessage(e, '无法加载继续观看，请稍后重试。')
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>

<style scoped>
.continue-workspace {
  display: grid;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  gap: var(--space-4);
}

.continue-workspace__heading,
.continue-queue__header,
.continue-queue__footer,
.continue-feature__actions {
  display: flex;
  align-items: center;
}

.continue-workspace__heading {
  justify-content: space-between;
}

.continue-workspace__heading h2 {
  margin: 0.1rem 0 0;
  color: hsl(var(--foreground));
  font-family: var(--font-display);
  font-size: var(--app-h2-size);
  font-weight: 680;
  letter-spacing: -0.025em;
}

.continue-workspace__eyebrow {
  margin: 0;
  color: hsl(var(--primary));
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.continue-workspace__more,
.continue-queue__footer {
  gap: var(--space-1);
  border: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
}

.continue-workspace__more:hover,
.continue-queue__footer:hover {
  color: hsl(var(--foreground));
}

.continue-workspace__grid,
.continue-workspace__loading {
  display: grid;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) clamp(16rem, 24%, 21rem);
  gap: var(--space-4);
}

.continue-feature,
.continue-queue,
.continue-workspace__skeleton {
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-xl);
  background: hsl(var(--card));
}

.continue-feature {
  position: relative;
  display: grid;
  grid-template-columns: minmax(17rem, 0.72fr) minmax(0, 1.28fr);
  min-height: 19rem;
  cursor: pointer;
  isolation: isolate;
  outline: none;
}

.continue-feature:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.55);
}

.continue-feature__art {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.continue-feature__visual {
  position: relative;
  min-width: 0;
  min-height: 19rem;
  overflow: hidden;
  background: var(--app-media-thumb-placeholder);
}

.continue-feature__shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, hsl(var(--card) / 0.22), transparent 30%);
}

.continue-feature__content {
  position: relative;
  z-index: 2;
  display: grid;
  width: auto;
  align-content: center;
  gap: var(--space-4);
  padding: clamp(1.5rem, 2.5vw, 2.25rem);
  background: hsl(var(--card));
}

.continue-feature__copy {
  display: grid;
  gap: var(--space-2);
}

.continue-feature__copy h3 {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-display);
  font-size: clamp(1.25rem, 1.7vw, 1.625rem);
  font-weight: 650;
  line-height: 1.16;
  letter-spacing: -0.035em;
  text-wrap: balance;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.continue-feature__source,
.continue-feature__meta {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 550;
}

.continue-feature__source {
  color: hsl(var(--primary));
  font-weight: 650;
}

.continue-feature__meta {
  display: flex;
  gap: var(--space-2);
}

.continue-feature__actions {
  gap: var(--space-2);
}

.continue-feature__play {
  box-shadow: 0 0.375rem 1.25rem hsl(var(--primary) / 0.18);
}

.continue-feature__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 4;
  height: 3px;
  background: hsl(var(--foreground) / 0.12);
}

.continue-feature__progress span,
.continue-queue__thumb-progress span {
  display: block;
  height: 100%;
  background: hsl(var(--primary));
}

.continue-queue {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.continue-queue__header {
  justify-content: space-between;
  padding: 1rem 1rem 0.875rem;
  border-bottom: 1px solid var(--app-hairline);
  color: hsl(var(--muted-foreground));
}

.continue-queue__header p {
  margin: 0 0 0.1rem;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 680;
}

.continue-queue__header span {
  font-size: 0.6875rem;
}

.continue-queue__items {
  display: grid;
  flex: 1;
  align-content: start;
  padding: var(--space-2);
}

.continue-queue__item {
  display: grid;
  grid-template-columns: 5.75rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  min-width: 0;
  padding: var(--space-2);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.continue-queue__item:hover,
.continue-queue__item:focus-visible {
  background: hsl(var(--accent) / 0.7);
  outline: none;
}

.continue-queue__thumb {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-md);
  background: var(--app-media-thumb-placeholder);
}

.continue-queue__thumb-progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2px;
  background: hsl(0 0% 100% / 0.24);
}

.continue-queue__body {
  display: grid;
  min-width: 0;
  gap: 0.3rem;
}

.continue-queue__body strong {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 620;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.continue-queue__body small {
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.65rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.continue-queue__play {
  color: hsl(var(--muted-foreground));
  opacity: 0;
  transform: translateX(-0.25rem);
  transition: opacity var(--duration-fast), transform var(--duration-fast);
}

.continue-queue__item:hover .continue-queue__play,
.continue-queue__item:focus-visible .continue-queue__play {
  opacity: 1;
  transform: none;
}

.continue-queue__footer {
  justify-content: space-between;
  width: 100%;
  padding: 0.875rem 1rem;
  border-top: 1px solid var(--app-hairline);
  text-align: left;
}

.continue-workspace__skeleton {
  min-height: 19rem;
  background: linear-gradient(90deg, hsl(var(--muted) / 0.45), hsl(var(--muted) / 0.72), hsl(var(--muted) / 0.45));
  background-size: 200% 100%;
  animation: continue-shimmer 1.4s ease-in-out infinite;
}

@keyframes continue-shimmer {
  to { background-position: -200% 0; }
}

@media (max-width: 1120px) {
  .continue-workspace__grid,
  .continue-workspace__loading {
    grid-template-columns: minmax(0, 1fr) 16rem;
  }

  .continue-feature {
    grid-template-columns: minmax(15rem, 0.9fr) minmax(0, 1.1fr);
    min-height: 20rem;
  }

  .continue-feature__visual {
    min-height: 20rem;
  }

  .continue-queue__item:nth-child(n + 4) {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .continue-workspace__skeleton { animation: none; }
}
</style>
