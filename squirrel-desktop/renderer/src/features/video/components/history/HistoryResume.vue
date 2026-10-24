<template>
  <article class="history-resume">
    <button
      type="button"
      class="history-resume__media"
      :aria-label="`继续播放 ${video.title}`"
      @click="emit('open', video)"
    >
      <MediaFrame
        class="history-resume__frame"
        :duration="video.duration ? formatDuration(video.duration) : ''"
        :progress="progress"
        :progress-label="`已观看 ${progressPercent}%`"
      >
        <VideoThumbnail
          :src="video.thumbnail"
          :alt="video.title"
          fit="cover"
          interactive
        />
      </MediaFrame>
    </button>

    <div class="history-resume__copy">
      <span class="history-resume__eyebrow">继续观看</span>

      <button
        type="button"
        class="history-resume__title"
        @click="emit('open', video)"
      >
        {{ video.title }}
      </button>

      <div class="history-resume__meta">
        <button
          v-if="source"
          type="button"
          class="history-resume__channel"
          @click="emit('openProfile', source)"
        >
          <SubscriptionAvatar :src="source.avatar" :name="source.name" size="xs" />
          <span>{{ channelName }}</span>
        </button>
        <span v-else class="history-resume__channel">{{ channelName }}</span>
        <span v-if="playedLabel" class="history-resume__played">{{ playedLabel }}</span>
      </div>

      <div class="history-resume__progress-line">
        <div class="history-resume__track" aria-hidden="true">
          <span :style="{ width: `${progressPercent}%` }" />
        </div>
        <span class="history-resume__percent">已看 {{ progressPercent }}%</span>
      </div>

      <div class="history-resume__actions">
        <Button type="button" size="sm" @click="emit('open', video)">
          <AppIcon name="play" class="h-3.5 w-3.5" />
          继续观看
        </Button>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import MediaFrame from '@/shared/components/layout/MediaFrame.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import { Button } from '@/shared/ui/button'
import { formatDuration } from '@/shared/lib/dateFormat'
import type { VideoHistoryEntry, VideoProfile } from '@/features/video/types/video'

defineProps<{
  video: VideoHistoryEntry
  progress: number
  progressPercent: number
  playedLabel: string
  source: VideoProfile | null
  channelName: string
}>()

const emit = defineEmits<{
  open: [video: VideoHistoryEntry]
  openProfile: [profile: VideoProfile]
}>()
</script>

<style scoped>
.history-resume {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(15rem, 21rem) minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--app-surface-border);
  border-radius: var(--radius-xl);
  background: hsl(var(--card));
}

.history-resume__media {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 0;
  padding: 0;
  background: var(--app-media-thumb-placeholder);
  cursor: pointer;
}

.history-resume__media:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.7);
}

.history-resume__frame {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

.history-resume__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0.5rem;
  padding: var(--space-5);
}

.history-resume__eyebrow {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
  font-weight: 600;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

.history-resume__title {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-display);
  font-size: clamp(1.25rem, 1.7vw, 1.75rem);
  font-weight: 600;
  letter-spacing: -0.015em;
  line-height: 1.28;
  text-align: left;
  text-wrap: pretty;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.history-resume__title:hover {
  color: hsl(var(--primary));
}

.history-resume__title:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.5);
  border-radius: var(--radius-sm);
}

.history-resume__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.45rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.3;
}

.history-resume__channel {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.history-resume__channel span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-resume__channel:hover {
  color: hsl(var(--foreground));
}

.history-resume__channel:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.5);
  border-radius: var(--radius-sm);
}

.history-resume__played::before {
  content: '·';
  margin-right: 0.45rem;
  color: hsl(var(--muted-foreground) / 0.5);
}

.history-resume__progress-line {
  display: flex;
  max-width: 28rem;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.15rem;
}

.history-resume__track {
  height: 3px;
  flex: 1 1 auto;
  overflow: hidden;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.09);
}

.history-resume__track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: hsl(var(--foreground));
}

.history-resume__percent {
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.history-resume__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: 0.2rem;
}

@media (max-width: 760px) {
  .history-resume {
    grid-template-columns: minmax(0, 1fr);
  }

  .history-resume__media {
    aspect-ratio: 16 / 9;
  }

  .history-resume__copy {
    padding: var(--space-4);
  }
}
</style>
