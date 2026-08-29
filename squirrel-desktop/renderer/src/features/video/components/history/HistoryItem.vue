<template>
  <!--
    Stable DOM contract (automation + visual):
    - root: article.history-item[data-history-item]
    - stable selectors: .history-item, [data-history-item], .history-groups .history-item
    - unfinished flag: data-unfinished="true|false"
  -->
  <article
    class="history-item"
    data-history-item
    :data-history-id="String(video.history_id)"
    :data-unfinished="isUnfinished ? 'true' : 'false'"
  >
    <div
      class="history-item__open"
      @pointerenter="prefetchPlayback"
      @pointerdown.left="prefetchPlayback"
    >
      <button
        type="button"
        class="history-item__open-button"
        :aria-label="`播放 ${video.title}`"
        @click="emit('open', video)"
      />

      <div class="history-item__thumb">
        <VideoThumbnail :src="video.thumbnail" :alt="video.title" fit="cover" interactive />

        <span v-if="video.duration" class="history-item__duration">
          {{ formatDuration(video.duration) }}
        </span>

        <div
          v-if="progress > 0"
          class="history-item__progress"
          role="progressbar"
          :aria-valuenow="progressPercent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`已观看 ${progressPercent}%`"
        >
          <div class="history-item__progress-fill" :style="{ width: `${progressPercent}%` }" />
        </div>
      </div>

      <div class="history-item__main">
        <h3 class="history-item__title">{{ video.title }}</h3>

        <button
          v-if="displaySource"
          type="button"
          class="history-item__source history-item__source--link"
          @click="emit('openProfile', displaySource)"
        >
          <SubscriptionAvatar
            :src="displaySource.avatar"
            :name="displaySource.name"
            size="xs"
          />
          <span class="history-item__channel">{{ displayChannel }}</span>
          <span v-if="video.site" class="history-item__site">{{ video.site }}</span>
        </button>
        <div v-else class="history-item__source">
          <span class="history-item__channel">{{ displayChannel }}</span>
          <span v-if="video.site" class="history-item__site">{{ video.site }}</span>
        </div>
      </div>

      <div class="history-item__meta" aria-label="播放信息">
        <span class="history-item__time">{{ playedTime }}</span>
        <span
          class="history-item__status"
          :class="{ 'history-item__status--active': isUnfinished }"
        >
          {{ progressLabel }}
        </span>
      </div>
    </div>

    <Button
     
      variant="secondary"
      size="sm"
      icon-only
      class="history-item__delete"
      title="删除此条历史"
      aria-label="删除此条历史"
      @click="emit('delete', video.history_id)"
    >
      <AppIcon name="trash" class="size-4" />
    </Button>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import type { VideoHistoryEntry, VideoProfile } from '@/features/video/types/video'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { formatDuration } from '@/shared/lib/dateFormat'
import { Button } from '@/shared/ui/button'

const props = defineProps<{
  video: VideoHistoryEntry
}>()

const emit = defineEmits<{
  open: [video: VideoHistoryEntry]
  delete: [historyId: number]
  openProfile: [profile: VideoProfile]
}>()

const progress = computed(() => {
  const duration = Number(props.video.duration || 0)
  if (duration <= 0) return 0
  return Math.max(0, Math.min(1, Number(props.video.last_position || 0) / duration))
})
const progressPercent = computed(() => {
  if (progress.value <= 0) return 0
  // Unfinished rows never round down to 0% — that reads as "not started".
  return Math.max(1, Math.min(99, Math.round(progress.value * 100)))
})
const isUnfinished = computed(() => progress.value > 0.01 && progress.value < 0.95)
const progressLabel = computed(() => {
  if (progress.value <= 0) return '已播放'
  if (progress.value >= 0.95) return '已播放'
  return `继续观看 · ${progressPercent.value}%`
})

const timeFormatter = new Intl.DateTimeFormat('zh-CN', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})
const playedTime = computed(() => {
  if (!props.video.played_at) return '时间未知'
  const date = new Date(props.video.played_at)
  return Number.isNaN(date.getTime()) ? '时间未知' : timeFormatter.format(date)
})

const videoSources = computed(() => {
  return props.video.subscriptions.length > 0 ? props.video.subscriptions : props.video.actors
})

const displaySource = computed(() => {
  const raw = videoSources.value[0] ?? null
  if (!raw) return null
  if (raw.profile_source) return raw
  const fromSubs = props.video.subscriptions.length > 0
  return { ...raw, profile_source: fromSubs ? 'subscription' as const : 'creator' as const }
})

const displayChannel = computed(
  () => videoSources.value.map((source) => source.name).filter(Boolean).join(' / ') || '未知作者',
)

const prefetchPlayback = () => {
  void prefetchDesktopPlaybackSource(props.video)
}
</script>

<style scoped>
.history-item {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) 2rem;
  align-items: center;
  column-gap: 0.35rem;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.88);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  padding-inline: 0.7rem;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.history-item:hover,
.history-item:focus-within {
  border-color: hsl(var(--foreground) / 0.16);
  background: hsl(var(--card));
}

/* Always three columns on desktop workbench widths. */
.history-item__open {
  position: relative;
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: 11rem minmax(0, 1fr) 10.5rem;
  align-items: center;
  column-gap: 1rem;
  padding: 0.7rem 0;
}

.history-item__open-button {
  position: absolute;
  z-index: 0;
  inset: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
}

.history-item__open-button:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.62);
}

.history-item__open > :not(.history-item__open-button) {
  position: relative;
  z-index: 1;
  pointer-events: none;
}

.history-item__thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  min-width: 0;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.04);
}

.history-item__duration {
  position: absolute;
  right: 0.375rem;
  bottom: 0.55rem;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: var(--radius-sm);
  background: var(--app-media-badge-bg);
  color: hsl(var(--app-media-on-image));
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.history-item__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 20;
  height: 3px;
  overflow: hidden;
  background: var(--app-media-progress-track);
}

.history-item__progress-fill {
  height: 100%;
  background: hsl(var(--primary));
}

.history-item__main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0.4rem;
}

.history-item__title {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--foreground));
  font-size: var(--app-text-lg);
  font-weight: 650;
  letter-spacing: -0.01em;
  line-height: 1.35;
  text-wrap: pretty;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.history-item__source {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.4rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.3;
}

.history-item__source--link {
  z-index: 2;
  border: 0;
  padding: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font: inherit;
  text-align: left;
  pointer-events: auto !important;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: color var(--duration-fast) var(--ease-default);
}

.history-item__source--link:hover .history-item__channel {
  color: hsl(var(--foreground));
}

.history-item__source--link:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.55);
}

.history-item__channel {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item__site {
  flex: 0 0 auto;
  max-width: 5.5rem;
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: var(--app-text-xs);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item__site::before {
  content: '·';
  margin-right: 0.3rem;
  color: hsl(var(--muted-foreground) / 0.45);
}

.history-item__meta {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 0.3rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-variant-numeric: tabular-nums;
  line-height: 1.35;
  text-align: right;
}

.history-item__time {
  color: hsl(var(--muted-foreground));
}

.history-item__status {
  display: inline-flex;
  align-items: center;
  min-height: 1.35rem;
  border-radius: 999px;
  padding: 0 0.5rem;
  color: hsl(var(--muted-foreground) / 0.92);
  background: hsl(var(--foreground) / 0.04);
}

.history-item__status--active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.08);
  font-weight: 700;
}

.history-item__delete {
  justify-self: end;
  color: hsl(var(--muted-foreground));
  opacity: 0;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.history-item:hover .history-item__delete,
.history-item:focus-within .history-item__delete {
  opacity: 1;
}

.history-item__delete:hover,
.history-item__delete:focus-visible {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

@media (max-width: 720px) {
  .history-item__open {
    grid-template-columns: 7.75rem minmax(0, 1fr);
    row-gap: 0.4rem;
  }

  .history-item__meta {
    grid-column: 2;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 0.5rem;
    text-align: left;
  }
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .history-item__delete {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .history-item,
  .history-item__delete {
    transition: none;
  }
}
</style>
