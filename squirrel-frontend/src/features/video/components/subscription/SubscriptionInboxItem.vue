<template>
  <article
    class="subscription-inbox-item"
    :class="{ 'subscription-inbox-item--read': isRead }"
  >
    <Button
      unstyled
      type="button"
      class="subscription-inbox-item__thumbnail"
      :aria-label="`播放 ${video.title}`"
      @click="openVideo"
    >
      <VideoThumbnail
        :src="video.thumbnail"
        :alt="video.title"
        fit="cover"
        interactive
      />
      <span v-if="video.duration" class="subscription-inbox-item__duration">
        {{ formatDuration(video.duration) }}
      </span>
    </Button>

    <div class="subscription-inbox-item__copy">
      <Button
        unstyled
        type="button"
        class="subscription-inbox-item__title"
        @click="openVideo"
      >
        {{ video.title }}
      </Button>
      <div class="subscription-inbox-item__meta">
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
        variant="ghost"
        size="icon-sm"
        :loading="readBusy"
        :title="isRead ? '标记未读' : '标记已读'"
        :aria-label="isRead ? '标记未读' : '标记已读'"
        :aria-pressed="isRead"
        @click="toggleRead"
      >
        <AppIcon
          v-if="!readBusy"
          :name="isRead ? 'statusSuccess' : 'check'"
          class="h-4 w-4"
        />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        title="播放视频"
        aria-label="播放视频"
        @click="openVideo"
      >
        <AppIcon name="chevronRight" class="h-4 w-4" />
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
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import type { VideoListItem } from '@/features/video/types/video'

const props = defineProps<{
  video: VideoListItem
}>()

const emit = defineEmits<{
  open: [video: VideoListItem]
  'read-change': [payload: { videoId: number; isRead: boolean }]
}>()

const toast = useToast()
const { clearHistory, sendReport } = useVideoHistory()
const readBusy = ref(false)
const isRead = ref(props.video.last_position > 0)

const displayDate = computed(() => (
  formatDate(props.video.uploaded_at || props.video.created_at)
))

watch(() => props.video.last_position, (value) => {
  isRead.value = value > 0
})

const setReadState = async (nextValue: boolean) => {
  if (readBusy.value || isRead.value === nextValue) return true
  readBusy.value = true
  try {
    if (nextValue) {
      await sendReport(
        props.video.id,
        Math.max(1, Number(props.video.duration || 1)),
        { force: true },
      )
    } else {
      await clearHistory([props.video.id])
    }
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

const openVideo = () => {
  if (!isRead.value) void setReadState(true)
  emit('open', props.video)
}
</script>

<style scoped>
.subscription-inbox-item {
  display: grid;
  min-width: 0;
  grid-template-columns: 9rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-4);
  padding: 0.625rem 0;
  border-top: 1px solid var(--app-hairline);
}

.subscription-inbox-item--read {
  opacity: 0.72;
}

.subscription-inbox-item__thumbnail {
  position: relative;
  overflow: hidden;
  width: 9rem;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-lg);
  background: hsl(0 0% 0% / 0.55);
  cursor: pointer;
}

.subscription-inbox-item__thumbnail:focus-visible,
.subscription-inbox-item__title:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.42);
}

.subscription-inbox-item__duration {
  position: absolute;
  right: 0.375rem;
  bottom: 0.375rem;
  border-radius: var(--radius-sm);
  background: hsl(0 0% 0% / 0.72);
  padding: 0.125rem 0.3rem;
  color: hsl(0 0% 100% / 0.94);
  font-family: var(--font-mono);
  font-size: 0.625rem;
  line-height: 1;
}

.subscription-inbox-item__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.45rem;
}

.subscription-inbox-item__title {
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.4;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.subscription-inbox-item__title:hover {
  color: hsl(var(--primary));
}

.subscription-inbox-item__meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: hsl(var(--muted-foreground) / 0.74);
  font-size: 0.6875rem;
  font-weight: 500;
}

.subscription-inbox-item__read-state {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.subscription-inbox-item__actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-default);
}

.subscription-inbox-item:hover .subscription-inbox-item__actions,
.subscription-inbox-item:focus-within .subscription-inbox-item__actions {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .subscription-inbox-item__actions {
    opacity: 1;
    transition: none;
  }
}
</style>
