<template>
  <article
    class="video-item group"
    :class="layout === 'list' ? 'flex-row gap-4' : 'flex-col gap-2.5'"
    role="button"
    tabindex="0"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <div :class="[
      'video-item__thumb',
      layout === 'list' ? 'video-item__thumb--list' : 'video-item__thumb--grid'
    ]">
      <VideoThumbnail
        :src="thumbnailSrc"
        :alt="video.title"
        fit="responsive"
        interactive
        :blur="shouldBlurThumbnail"
      />

      <div class="app-overlay-actions app-overlay-actions--top-right">
        <div class="app-overlay-actions__bar">
          <Button
            variant="ghost"
            size="mini-icon"
            class="app-overlay-action"
            title="标记已读"
            @click.stop="toggleReadStatus(!isRead)"
          >
            <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-[15px]" />
          </Button>
          <Button
            variant="ghost"
            size="mini-icon"
            class="app-overlay-action"
            title="稍后再看"
            @click.stop="toggleLater"
          >
            <AppIcon :name="isLater === 1 ? 'watchLaterActive' : 'watchLater'" class="size-[15px]" />
          </Button>
          <Button
            variant="ghost"
            size="mini-icon"
            class="app-overlay-action"
            :class="{ 'is-active': isLiked === 1 }"
            title="喜欢"
            @click.stop="toggleLikeVideo"
          >
            <AppIcon name="heart" class="size-[15px]" :class="{ 'fill-current': isLiked === 1 }" />
          </Button>
        </div>
      </div>

      <span v-if="video.duration && showDuration" class="video-item__duration">
        {{ formatDuration(video.duration) }}
      </span>

      <div class="video-item__scrim" />

      <div v-if="progressRatio > 0" class="video-item__progress">
        <div class="h-full bg-primary transition-[width] duration-500 ease-out" :style="{ width: `${progressRatio * 100}%` }" />
      </div>
    </div>

    <!-- Info Container -->
    <div :class="[
      'flex flex-col gap-1 px-0.5',
      layout === 'list' ? 'flex-1 py-1 min-w-0' : ''
    ]">
      <h3 :class="[
        'video-item__title',
        layout === 'list' ? 'video-item__title--list' : 'video-item__title--grid'
      ]">
        {{ video.title }}
      </h3>

      <div class="flex items-start gap-3 min-w-0">
        <div v-if="showAvatar && displayAvatars.length" class="shrink-0 mt-0.5">
          <SubscriptionAvatar
            :src="displayAvatars[0].avatar"
            :name="displayAvatars[0].name"
            size="lg"
            @click.stop="goToSubscription(displayAvatars[0].id)"
          />
        </div>

        <div class="flex-1 min-w-0 flex flex-col gap-0.5">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground/80 font-medium">
            <span class="video-item__source-name" @click.stop="goToSubscription(primarySubscriptionId)">
              {{ displayNames }}
            </span>
            <span v-if="video.site" class="video-item__site">{{ video.site }}</span>
          </div>
          <div class="flex items-center gap-1 text-xs text-muted-foreground/70 font-medium">
            <span>{{ displayDateText }}</span>
            <span v-if="layout === 'list' && video.duration" class="ml-2 font-mono bg-muted px-1 rounded">{{ formatDuration(video.duration) }}</span>
          </div>
        </div>
      </div>

      <div v-if="layout === 'list' && video.description" class="hidden md:block mt-1.5 text-xs text-muted-foreground/70 line-clamp-2">
        {{ video.description }}
      </div>
    </div>

    <Teleport to="body">
      <ContextMenu
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :video="video"
        :is-liked="isLiked"
        @close="showMenu = false"
        @toggleReadStatus="toggleReadStatus"
        @toggleLike="toggleLikeVideo"
      />
    </Teleport>
  </article>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import ContextMenu from './ContextMenu.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { useSystemConfig } from '@/shared/composables/useSystemConfig'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import type { VideoListItem } from '@/features/video/types/video'

const props = withDefaults(defineProps<{
  video: VideoListItem
  showAvatar?: boolean
  sortBy?: string
  layout?: 'grid' | 'list'
  showDuration?: boolean
}>(), {
  layout: 'grid',
  showDuration: true,
})

const emit = defineEmits(['goToSubscription', 'openModal'])

const { config: systemConfig } = useSystemConfig()
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })

// ponytail: read/like/later interaction state. The list endpoint does not
// return these flags, so they are kept as local optimistic UI state here
// rather than mutated on the props object (which would violate one-way flow
// and previously wrote to nonexistent fields).
const isRead = ref(false)
const isLiked = ref<number | null>(null)
const isLater = ref<number | null>(null)

const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const isNsfwVideo = computed(() => props.video.subscriptions?.some((s) => s.is_nsfw))
const shouldBlurThumbnail = computed(() => Boolean(systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value))

const progressRatio = computed(() => {
  const d = Number(props.video?.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video?.last_position || 0) / d) : 0
})

const displayDateText = computed(() => {
  const t = props.sortBy === 'created_at' ? (props.video.created_at || props.video.uploaded_at) : (props.video.uploaded_at || props.video.created_at)
  return t ? formatDate(t) : ''
})

const displayAvatars = computed(() => {
  const subs = props.video.subscriptions || []
  const actors = props.video.actors || []
  return (subs.length ? subs : actors).slice(0, 1)
})

const displayNames = computed(() => {
  const names = (props.video.subscriptions || props.video.actors || []).map((a) => a.name)
  return names.length ? names.join(' / ') : '未知'
})

const primarySubscriptionId = computed(() => props.video.subscriptions?.[0]?.id || props.video.actors?.[0]?.id)

const closeMenuOnExternalClose = () => { showMenu.value = false }

const showContextMenu = async (event: MouseEvent) => {
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))
  await nextTick()
  menuPosition.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

const handleClick = () => emit('openModal', props.video)
const goToSubscription = (id: number | string | null | undefined) => id && emit('goToSubscription', id)

const toggleReadStatus = async (markRead: boolean) => {
  if (markRead) {
    const pos = Number(props.video.duration || 0)
    await sendReport(props.video.id, pos, { force: true })
    isRead.value = true
  } else {
    await clearHistory([props.video.id])
    isRead.value = false
  }
  showMenu.value = false
}

const toggleLikeVideo = async () => {
  try {
    if (isLiked.value === 1) {
      await deleteInteraction(props.video.id)
      isLiked.value = null
    } else {
      await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
      isLiked.value = 1
    }
  } catch {
    // silent — toggle failure leaves the prior like state
  }
  showMenu.value = false
}

const toggleLater = async () => {
  try {
    if (isLater.value === 1) {
      await deleteInteraction(props.video.id)
      isLater.value = null
    } else {
      await toggleLike(props.video.id, INTERACTION_TYPE.LATER)
      isLater.value = 1
    }
  } catch {
    // silent — toggle failure leaves the prior later state
  }
}

onMounted(() => document.addEventListener('closeAllContextMenus', closeMenuOnExternalClose))
onUnmounted(() => document.removeEventListener('closeAllContextMenus', closeMenuOnExternalClose))
</script>

<style scoped>
.video-item {
  display: flex;
  cursor: pointer;
  border-radius: var(--radius-lg);
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default);
}

.video-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.4);
}

.video-item__thumb {
  position: relative;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: var(--radius-xl);
  background: hsl(var(--muted));
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease;
}

.video-item:hover .video-item__thumb,
.video-item:focus-visible .video-item__thumb {
  border-color: hsl(var(--primary) / 0.32);
}

.video-item__thumb--list {
  aspect-ratio: 16 / 9;
  width: 12rem;
  flex: 0 0 auto;
}

@media (min-width: 768px) {
  .video-item__thumb--list {
    width: 16rem;
  }
}

.video-item__thumb--grid {
  aspect-ratio: 16 / 9;
  width: 100%;
}

.video-item__duration {
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

.video-item:hover .video-item__duration {
  opacity: 0;
}

.video-item__scrim {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  height: 2.5rem;
  pointer-events: none;
  background: linear-gradient(to top, hsl(0 0% 0% / 0.6), transparent);
}

.video-item__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 20;
  height: 1px;
  background: hsl(0 0% 100% / 0.16);
}

.video-item__source-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.16s ease;
}

.video-item__source-name:hover {
  color: hsl(var(--foreground));
}

.video-item__site {
  flex: 0 0 auto;
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.25rem;
  background: hsl(var(--accent) / 0.5);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 700;
}

.video-item__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground) / 0.9);
  font-weight: 600;
  line-height: 1.3;
  transition: color var(--duration-fast) var(--ease-default);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-item__title--grid {
  font-size: 0.875rem;
}

.video-item__title--list {
  margin-bottom: 0.125rem;
  font-size: 1rem;
  -webkit-line-clamp: 3;
}

.video-item:hover .video-item__title {
  color: hsl(var(--primary));
}

@media (prefers-reduced-motion: reduce) {
  .video-item,
  .video-item__thumb,
  .video-item__duration,
  .video-item__source-name {
    transition: none;
  }
}
</style>
