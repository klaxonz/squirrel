<template>
  <div
    class="history-item"
    role="button"
    tabindex="0"
    @click="$emit('open', video)"
    @keydown.enter.prevent="$emit('open', video)"
    @keydown.space.prevent="$emit('open', video)"
  >
    <div class="history-item__thumb">
      <VideoThumbnail
        :src="video.thumbnail"
        :alt="video.title"
        fit="responsive"
      />

      <div class="history-item__scrim" />

      <div v-if="progress > 0" class="history-item__progress">
        <div class="h-full bg-primary transition-[width] duration-500 ease-out" :style="{ width: `${progress * 100}%` }" />
      </div>

      <div v-if="video.duration" class="history-item__duration">
        {{ formatDuration(video.duration) }}
      </div>
    </div>

    <div class="flex flex-1 min-w-0 py-1">
      <div class="flex-1 min-w-0 flex flex-col gap-1 justify-center">
        <h3 class="font-semibold leading-[1.3] text-foreground/90 group-hover:text-primary transition-colors tracking-tight text-base line-clamp-2 md:line-clamp-3">
          {{ video.title }}
        </h3>

        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-2 text-xs text-muted-foreground/80 font-medium">
            <SubscriptionAvatar
              v-if="displayAvatar"
              :src="displayAvatar.avatar"
              :name="displayAvatar.name"
              size="sm"
              class="shrink-0"
            />
            <span class="truncate">
              {{ displayChannel || '未知作者' }}
            </span>
            <span v-if="video.site" class="history-item__site">
              {{ video.site }}
            </span>
          </div>

          <div class="flex items-center gap-2 text-xs text-muted-foreground/70 font-medium">
            <span>{{ formatDate(video.played_at) }}</span>
            <span v-if="progress > 0" class="history-item__watch-progress">
              <span class="h-2.5 w-0.5 rounded-sm bg-primary" />
              已观看 {{ (progress * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <button
      class="history-item__delete"
      @click.stop="handleDelete"
    >
      <AppIcon name="trash" class="h-4 w-4" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import type { VideoHistoryEntry } from '@/features/video/types/video'

const props = defineProps<{
  video: VideoHistoryEntry
}>()

const emit = defineEmits(['open', 'delete'])

const handleDelete = () => {
  emit('delete', props.video.history_id || props.video.id)
}

const progress = computed(() => {
  const d = Number(props.video.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video.last_position || 0) / d) : 0
})

const displayAvatar = computed(() => {
  const source = (props.video.subscriptions || props.video.actors || [])[0] || null
  return source ? { name: source.name, avatar: source.avatar ?? '' } : null
})

const displayChannel = computed(() => {
  const sources = props.video.subscriptions || props.video.actors || []
  return sources.map((s) => s.name).join(' / ')
})
</script>

<style scoped>
.history-item {
  position: relative;
  display: flex;
  gap: 1rem;
  cursor: pointer;
  border-radius: 0.625rem;
  outline: none;
}

.history-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.4);
}

.history-item__thumb {
  position: relative;
  width: 12rem;
  aspect-ratio: 16 / 9;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 0.625rem;
  background: hsl(var(--muted));
  transition: border-color 0.16s ease;
}

@media (min-width: 768px) {
  .history-item__thumb {
    width: 16rem;
  }
}

.history-item:hover .history-item__thumb,
.history-item:focus-visible .history-item__thumb {
  border-color: hsl(var(--primary) / 0.32);
}

.history-item__scrim {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  height: 2.5rem;
  pointer-events: none;
  background: linear-gradient(to top, hsl(0 0% 0% / 0.6), transparent);
}

.history-item__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 20;
  height: 1px;
  background: hsl(0 0% 100% / 0.16);
}

.history-item__duration {
  position: absolute;
  right: 0.375rem;
  bottom: 0.375rem;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: 0.375rem;
  background: hsl(0 0% 0% / 0.72);
  color: white;
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  transition: opacity 0.16s ease;
}

.history-item:hover .history-item__duration {
  opacity: 0;
}

.history-item__site {
  flex: 0 0 auto;
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.25rem;
  background: hsl(var(--accent) / 0.5);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 700;
}

.history-item__watch-progress {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.7);
  color: hsl(var(--muted-foreground));
}

.history-item__delete {
  position: absolute;
  top: 0.375rem;
  right: 0.375rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.375rem;
  background: hsl(var(--background) / 0.92);
  color: hsl(var(--muted-foreground));
  opacity: 0;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    opacity 0.16s ease;
}

.history-item:hover .history-item__delete,
.history-item:focus-within .history-item__delete {
  opacity: 1;
}

.history-item__delete:hover {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}

@media (prefers-reduced-motion: reduce) {
  .history-item__thumb,
  .history-item__duration,
  .history-item__delete {
    transition: none;
  }
}
</style>
