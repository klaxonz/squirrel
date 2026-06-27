<template>
  <div
    class="group relative flex cursor-pointer gap-4 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-shadow"
    role="button"
    tabindex="0"
    @click="$emit('open', video)"
    @keydown.enter.prevent="$emit('open', video)"
    @keydown.space.prevent="$emit('open', video)"
  >
    <div class="relative overflow-hidden rounded-lg bg-muted ring-1 ring-border/40 transition-all duration-300 group-hover:shadow-card-hover group-active:scale-[0.99] w-48 shrink-0 md:w-64 aspect-video">
      <VideoThumbnail
        :src="video.thumbnail"
        :alt="video.title"
        fit="responsive"
      />

      <!-- Bottom Shadow/Gradient for Overlay Visibility -->
      <div class="absolute bottom-0 inset-x-0 h-10 bg-gradient-to-t from-black/60 to-transparent pointer-events-none z-10" />

      <!-- Progress Bar -->
      <div v-if="progress > 0" class="absolute bottom-0 inset-x-0 h-px group-hover:h-[2px] transition-all duration-300 z-20 bg-white/15">
        <div class="h-full bg-primary transition-[width] duration-500 ease-out" :style="{ width: `${progress * 100}%` }" />
      </div>

      <div v-if="video.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/70 px-1.5 text-2xs font-medium text-white tabular-nums shadow-sm backdrop-blur-sm transition-opacity group-hover:opacity-0">
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
            <span v-if="video.site" class="shrink-0 px-1 py-px rounded bg-accent/50 text-2xs font-bold text-muted-foreground uppercase tracking-wider">
              {{ video.site }}
            </span>
          </div>

          <div class="flex items-center gap-2 text-xs text-muted-foreground/70 font-medium">
            <span>{{ formatDate(video.played_at) }}</span>
            <span v-if="progress > 0" class="inline-flex items-center gap-1 rounded-full bg-muted/70 px-2 py-0.5 text-muted-foreground">
              <span class="h-1.5 w-1.5 rounded-full bg-primary" />
              已观看 {{ (progress * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <button
      class="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-md bg-background/90 text-muted-foreground opacity-0 shadow-sm transition-colors group-hover:opacity-100 hover:bg-destructive hover:text-destructive-foreground"
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
