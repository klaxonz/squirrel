<template>
  <article class="history-item">
    <div
      class="history-item__open"
      role="button"
      tabindex="0"
      @click="emit('open', video)"
      @keydown.enter.prevent="emit('open', video)"
      @keydown.space.prevent="emit('open', video)"
    >
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

      <div class="history-item__body">
        <h3 class="history-item__title">{{ video.title }}</h3>

        <div class="history-item__source">
          <SubscriptionAvatar
            v-if="displaySource"
            :src="displaySource.avatar"
            :name="displaySource.name"
            size="xs"
          />
          <span class="history-item__channel">{{ displayChannel }}</span>
          <span v-if="video.site" class="history-item__site">{{ video.site }}</span>
        </div>

        <div class="history-item__meta">
          <span>{{ playedTime }}</span>
          <span aria-hidden="true">·</span>
          <span :class="{ 'history-item__status--active': isUnfinished }">
            {{ progressLabel }}
          </span>
        </div>
      </div>
    </div>

    <Button
      variant="ghost"
      size="mini-icon"
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
import type { VideoHistoryEntry } from '@/features/video/types/video'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { formatDuration } from '@/shared/lib/dateFormat'
import { Button } from '@/shared/ui/button'

const props = defineProps<{
  video: VideoHistoryEntry
}>()

const emit = defineEmits<{
  open: [video: VideoHistoryEntry]
  delete: [historyId: number]
}>()

const timeFormatter = new Intl.DateTimeFormat('zh-CN', {
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const progress = computed(() => {
  const duration = Number(props.video.duration)
  return duration > 0
    ? Math.max(0, Math.min(1, Number(props.video.last_position) / duration))
    : 0
})

const progressPercent = computed(() => Math.round(progress.value * 100))
const isUnfinished = computed(() => progress.value > 0.01 && progress.value < 0.95)

const progressLabel = computed(() => {
  if (progress.value >= 0.95) return '已看完'
  if (progress.value > 0.01) return `继续观看 · ${progressPercent.value}%`
  return '已播放'
})

const playedTime = computed(() => {
  if (!props.video.played_at) return '时间未知'
  const date = new Date(props.video.played_at)
  return Number.isNaN(date.getTime()) ? '时间未知' : timeFormatter.format(date)
})

const videoSources = computed(() => {
  return props.video.subscriptions.length > 0 ? props.video.subscriptions : props.video.actors
})

const displaySource = computed(() => videoSources.value[0] ?? null)

const displayChannel = computed(
  () => videoSources.value.map((source) => source.name).filter(Boolean).join(' / ') || '未知作者',
)
</script>

<style scoped>
.history-item {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) 2rem;
  align-items: center;
  column-gap: var(--space-2);
  border-bottom: 1px solid var(--app-hairline);
  background: transparent;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.history-item:hover,
.history-item:focus-within {
  background: hsl(var(--foreground) / 0.025);
}

.history-item__open {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: 11.5rem minmax(0, 1fr);
  gap: var(--space-3);
  padding: 0.75rem 0;
  cursor: pointer;
  outline: none;
}

.history-item__open:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.62);
}

.history-item__thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  min-width: 0;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.history-item__duration {
  position: absolute;
  right: 0.375rem;
  bottom: 0.5rem;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: var(--radius-sm);
  background: var(--app-media-badge-bg);
  color: hsl(var(--app-media-on-image));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
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

.history-item__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0.5rem;
}

.history-item__title {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.9375rem;
  font-weight: 600;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.history-item__source,
.history-item__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.3;
}

.history-item__channel {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item__site {
  flex: 0 0 auto;
  padding: 0.0625rem 0.3125rem;
  border-radius: var(--radius-sm);
  background: hsl(var(--secondary));
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 600;
}

.history-item__meta {
  font-variant-numeric: tabular-nums;
}

.history-item__status--active {
  color: hsl(var(--muted-foreground));
  font-weight: 600;
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

.history-item__delete:hover {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

@media (prefers-reduced-motion: reduce) {
  .history-item,
  .history-item__delete {
    transition: none;
  }
}
</style>
