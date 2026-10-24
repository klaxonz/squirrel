<template>
  <article
    class="subscription-inbox-item"
    :class="{ 'subscription-inbox-item--read': isRead }"
  >
    <button
      type="button"
      class="subscription-inbox-item__thumbnail"
      :aria-label="`播放 ${video.title}`"
      @click="openVideo"
    >
      <MediaFrame
        class="subscription-inbox-item__frame"
        :duration="video.duration ? formatDuration(video.duration) : ''"
        compact
      >
        <VideoThumbnail
          :src="video.thumbnail"
          :alt="video.title"
          fit="cover"
          interactive
        />
      </MediaFrame>
    </button>

    <div class="subscription-inbox-item__copy">
      <button
        type="button"
        class="subscription-inbox-item__title"
        @click="openVideo"
      >
        {{ video.title }}
      </button>
      <div class="subscription-inbox-item__meta">
        <button
          v-if="subscriptionId != null"
          type="button"
          class="subscription-inbox-item__channel"
          @click="openChannel"
        >
          <SubscriptionAvatar
            :src="channelAvatar"
            :name="channelName"
            size="xs"
          />
          <span>{{ channelName }}</span>
        </button>
        <span v-else class="subscription-inbox-item__channel">
          <SubscriptionAvatar
            :src="channelAvatar"
            :name="channelName"
            size="xs"
          />
          <span>{{ channelName }}</span>
        </span>
        <span class="subscription-inbox-item__meta-separator" aria-hidden="true">·</span>
        <span>{{ displayDate }}</span>
        <span v-if="isRead" class="subscription-inbox-item__read-state">
          <AppIcon name="check" class="h-3 w-3" />
          已读
        </span>
      </div>
    </div>

    <div class="subscription-inbox-item__actions">
      <Button
        type="button"
        variant="secondary"
        size="sm"
        icon-only
        class="subscription-inbox-item__read-action"
        :loading="readBusy"
        :title="isRead ? '标记未读' : '标记已读'"
        :aria-label="isRead ? '标记未读' : '标记已读'"
        :aria-pressed="isRead"
        @click="toggleRead"
      >
        <AppIcon
          v-if="!readBusy"
          :name="isRead ? 'circle' : 'check'"
          class="h-3.5 w-3.5"
        />
      </Button>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import MediaFrame from '@/shared/components/layout/MediaFrame.vue'
import { updateVideoReadState } from '@/shared/api'
import type { VideoListItem } from '@/features/video/types/video'

const props = defineProps<{
  video: VideoListItem
  channelName: string
  channelAvatar: string | null
  subscriptionId: string | number | null
}>()

const emit = defineEmits<{
  open: [video: VideoListItem]
  'open-channel': [subscriptionId: string | number]
  'read-change': [payload: { videoId: number; isRead: boolean }]
}>()

const toast = useToast()
const readBusy = ref(false)
const isRead = ref(props.video.is_read ?? props.video.last_position > 0)

const displayDate = computed(() => (
  formatDate(props.video.uploaded_at || props.video.created_at)
))

watch(
  () => [props.video.is_read, props.video.last_position] as const,
  ([readState, position]) => {
    isRead.value = readState ?? position > 0
  },
)

const setReadState = async (nextValue: boolean) => {
  if (readBusy.value || isRead.value === nextValue) return true
  readBusy.value = true
  try {
    await updateVideoReadState(props.video.id, nextValue)
    isRead.value = nextValue
    emit('read-change', { videoId: props.video.id, isRead: nextValue })
    return true
  } catch (error) {
    toast.error(errorMessage(error, nextValue ? '标记已读失败' : '标记未读失败'))
    return false
  } finally {
    readBusy.value = false
  }
}

const toggleRead = () => {
  void setReadState(!isRead.value)
}

const openChannel = () => {
  if (props.subscriptionId != null) emit('open-channel', props.subscriptionId)
}

const openVideo = () => {
  if (!isRead.value) void setReadState(true)
  emit('open', props.video)
}
</script>

<style scoped>
.subscription-inbox-item {
  display: grid;
  min-width: 0;
  min-height: 7.25rem;
  grid-template-columns: 11rem minmax(0, 1fr) 2rem;
  align-items: center;
  gap: var(--space-5);
  padding: 0.875rem 0.9rem;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.subscription-inbox-item:hover,
.subscription-inbox-item:focus-within {
  background: hsl(var(--foreground) / 0.03);
}

.subscription-inbox-item__thumbnail {
  position: relative;
  display: block;
  width: 11rem;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.subscription-inbox-item__frame {
  width: 100%;
}

.subscription-inbox-item__thumbnail:focus-visible,
.subscription-inbox-item__title:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.8);
}

.subscription-inbox-item__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-2);
}

.subscription-inbox-item__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: var(--app-text-lg);
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: -0.01em;
  text-align: left;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  cursor: pointer;
}

.subscription-inbox-item--read .subscription-inbox-item__thumbnail {
  opacity: 0.82;
}

.subscription-inbox-item--read .subscription-inbox-item__title {
  color: hsl(var(--muted-foreground));
  font-weight: 500;
}

.subscription-inbox-item--read .subscription-inbox-item__meta {
  opacity: 0.86;
}

.subscription-inbox-item__title:hover {
  /* Title stays foreground; primary is for CTA/play only. */
  color: hsl(var(--foreground));
}

.subscription-inbox-item__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 500;
}

.subscription-inbox-item__channel {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
}

.subscription-inbox-item__channel > span {
  overflow: hidden;
  max-width: 16rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

button.subscription-inbox-item__channel {
  cursor: pointer;
}

button.subscription-inbox-item__channel:hover,
button.subscription-inbox-item__channel:focus-visible {
  color: hsl(var(--foreground) / 0.86);
  outline: none;
}

.subscription-inbox-item__meta-separator {
  color: hsl(var(--muted-foreground) / 0.42);
}

.subscription-inbox-item__read-state {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.subscription-inbox-item__actions {
  display: flex;
  align-items: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--duration-fast) var(--ease-default);
}

.subscription-inbox-item:hover .subscription-inbox-item__actions,
.subscription-inbox-item:focus-within .subscription-inbox-item__actions {
  opacity: 1;
  pointer-events: auto;
}

.subscription-inbox-item__read-action {
  width: 1.875rem;
  height: 1.875rem;
  color: hsl(var(--muted-foreground) / 0.82);
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .subscription-inbox-item__actions {
    opacity: 1;
    pointer-events: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .subscription-inbox-item__actions {
    transition: none;
  }
}

@media (max-width: 640px) {
  .subscription-inbox-item {
    grid-template-columns: 7rem minmax(0, 1fr);
    gap: var(--space-3);
  }

  .subscription-inbox-item__thumbnail {
    width: 7rem;
  }

  .subscription-inbox-item__actions {
    display: none;
  }
}
</style>
