<template>
  <div
    class="video-card"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <div class="video-card__thumbnail">
      <img
        v-if="thumbnailSrc && !showThumbnailFallback"
        :src="thumbnailSrc"
        loading="lazy"
        decoding="async"
        fetchpriority="low"
        referrerpolicy="no-referrer"
        class="video-card__image"
        :class="{
          'video-card__image--blur': shouldBlurThumbnail,
          'video-card__image--loaded': imageLoaded,
        }"
        :alt="video.title"
        @load="handleImageLoad"
        @error="handleThumbnailError"
      >

      <div v-else class="video-card__fallback">
        <div class="video-card__fallback-inner">
          <span class="video-card__fallback-text">无封面</span>
        </div>
      </div>

      <span class="video-card__duration">{{ formatDuration(video.duration) }}</span>

      <div
        v-if="progressRatio > 0"
        class="video-card__progress"
      >
        <div
          class="video-card__progress-fill"
          :style="{ width: `${(progressRatio * 100).toFixed(1)}%` }"
        ></div>
      </div>
    </div>

    <div class="video-card__info">
      <h5 class="video-card__title">{{ video.title }}</h5>
      <div class="video-card__meta">
        <div class="video-card__meta-left">
          <div v-if="displayAvatars.length" class="video-card__avatars">
            <SubscriptionAvatar
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="avatar.avatar"
              :name="avatar.name"
              size="xs"
              class="video-card__avatar"
              @click.stop="goToSubscription(avatar.id)"
            />
          </div>
          <span class="video-card__channel" @click.stop="goToSubscription(primarySubscriptionId)">
            {{ displayNames }}
          </span>
        </div>
        <span class="video-card__date">{{ displayDateText }}</span>
      </div>
    </div>

    <Teleport to="body">
      <ContextMenu
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :video="video"
        @close="closeContextMenu"
        @toggleReadStatus="toggleReadStatus"
        @copyVideoLink="copyVideoLink"
        @toggleLike="toggleLikeVideo"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, toRef, watch } from 'vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import ContextMenu from './ContextMenu.vue'
import { useThumbnailRegistry } from './useThumbnailRegistry'
import useOptionsMenu from '@/composables/useOptionsMenu'
import useVideoHistory from '@/composables/useVideoHistory'
import useVideoInteraction from '@/composables/useVideoInteraction'
import { useSystemConfig } from '@/composables/useSystemConfig'
import { formatVideoCardId } from '@/utils/videoCard'
import { formatDate, formatDuration } from '@/utils/dateFormat'
import { Logger } from '@/utils/logger'

const props = defineProps({
  video: {
    type: Object,
    required: true,
  },
  showAvatar: {
    type: Boolean,
    default: true,
  },
  sortBy: {
    type: String,
    default: 'publish_date',
  },
})

const emit = defineEmits([
  'goToSubscription',
  'openModal',
])

const { config: systemConfig } = useSystemConfig()
const { copyVideoLink } = useOptionsMenu(toRef(props, 'video'))
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const {
  imageLoaded,
  showFallback: showThumbnailFallback,
  handleLoad: handleImageLoad,
  handleError: handleThumbnailError,
} = useThumbnailRegistry(thumbnailSrc)
const isNsfwVideo = computed(() => props.video.subscriptions?.some((subscription) => subscription.is_nsfw) || false)
const shouldBlurThumbnail = computed(() => systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value)
const videoCardId = computed(() => formatVideoCardId(props.video?.id))
const progressRatio = computed(() => {
  const duration = Number(props.video?.duration || 0)
  if (!duration || duration <= 0) {
    return 0
  }

  const position = Number(props.video?.last_position || 0)
  const normalized = position / duration
  return Math.max(0, Math.min(1, normalized))
})

const displayDateText = computed(() => {
  const video = props.video
  const timestamp = props.sortBy === 'created_at'
    ? (video.created_at || video.uploaded_at)
    : (video.uploaded_at || video.created_at)
  return timestamp ? formatDate(timestamp) : ''
})

const subscriptions = computed(() => props.video.subscriptions || [])
const actors = computed(() => props.video.actors || [])

const displayAvatars = computed(() => {
  const subs = subscriptions.value
  let avatars = subs.map((subscription) => ({
    id: subscription.id,
    name: subscription.name,
    avatar: subscription.avatar,
  }))
  if (!avatars.length) {
    avatars = actors.value.map((actor) => ({
      id: actor.id,
      name: actor.name,
      avatar: actor.avatar,
    }))
  }
  return avatars.slice(0, 3)
})

const displayNames = computed(() => {
  const names = displayAvatars.value.map((avatar) => avatar.name)
  if (!names.length) return '未知'
  return names.join(' / ')
})

const primarySubscriptionId = computed(() => {
  return subscriptions.value[0]?.id ?? displayAvatars.value[0]?.id
})

const closeContextMenu = () => {
  showMenu.value = false
}

const handleScroll = () => {
  if (showMenu.value) closeContextMenu()
}

const showContextMenu = async (event) => {
  event.preventDefault()
  event.stopPropagation()
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))
  await nextTick()
  menuPosition.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

const handleClick = () => {
  emit('openModal', props.video)
}

const goToSubscription = (subscriptionId) => {
  if (!subscriptionId) return
  emit('goToSubscription', subscriptionId)
}

const toggleReadStatus = async (isRead) => {
  try {
    if (isRead) {
      const position = Number(props.video.duration || props.video.last_position || 0)
      await sendReport(props.video.id, position, { force: true })
      props.video.is_read = true
      props.video.last_position = position
    } else {
      await clearHistory([props.video.id])
      props.video.is_read = false
      props.video.last_position = 0
    }
    closeContextMenu()
  } catch (error) {
    Logger.error('Failed to update read status', error)
  }
}

const toggleLikeVideo = async () => {
  try {
    if (props.video.is_liked === 1 || props.video.is_liked === 0) {
      const { error } = await deleteInteraction(props.video.id)
      if (!error) props.video.is_liked = null
    } else {
      const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
      if (!error) props.video.is_liked = 1
    }
    closeContextMenu()
  } catch (error) {
    Logger.error('Failed to toggle like state', error)
  }
}

watch(showMenu, (isOpen) => {
  if (isOpen) {
    nextTick(() => {
      document.addEventListener('click', closeContextMenu, { once: true })
      window.addEventListener('scroll', handleScroll, { passive: true, capture: true, once: true })
    })
  }
})

onMounted(() => {
  document.addEventListener('closeAllContextMenus', closeContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('closeAllContextMenus', closeContextMenu)
  window.removeEventListener('scroll', handleScroll, true)
})
</script>

<style scoped>
.video-card {
  cursor: pointer;
  border-radius: var(--radius-xl);
  transition:
    background-color var(--duration-fast) var(--ease-default);
}

.video-card:hover {
  background: hsl(var(--foreground) / 0.03);
}

.video-card__thumbnail {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: hsl(var(--secondary));
  border-radius: var(--radius-xl);
  transition:
    box-shadow var(--duration-normal) var(--ease-default),
    transform var(--duration-normal) var(--ease-default);
}

.video-card:hover .video-card__thumbnail {
  box-shadow: 0 4px 16px hsl(var(--primary) / 0.15);
  transform: scale(1.02);
}

.video-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition:
    opacity var(--duration-slow) var(--ease-default),
    transform var(--duration-normal) var(--ease-default),
    filter var(--duration-normal) var(--ease-default);
}

.video-card__image--loaded {
  opacity: 1;
}

.video-card:hover .video-card__image--loaded {
  filter: brightness(1.05);
}

.video-card__image--blur {
  filter: blur(20px);
}

.video-card__duration {
  position: absolute;
  right: 0.5rem;
  bottom: 0.5rem;
  z-index: 2;
  padding: 1px 0.375rem;
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 500;
  color: #fff;
  background: rgba(0, 0, 0, 0.8);
  border-radius: var(--radius-sm);
  line-height: 1.4;
  pointer-events: none;
}

.video-card__progress {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.2);
  z-index: 2;
}

.video-card__progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  transition: width var(--duration-fast) var(--ease-default);
}

.video-card__info {
  margin-top: 0.75rem;
}

.video-card__title {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.4;
  height: 2.8em;
  color: hsl(var(--foreground));
  margin: 0 0 0.375rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-card:hover .video-card__title {
  color: hsl(var(--primary));
}

.video-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.video-card__meta-left {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  min-width: 0;
  flex: 1;
}

.video-card__avatars {
  display: flex;
  align-items: center;
  gap: 2px;
}

.video-card__avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
}

.video-card__avatar:deep(.avatar-image),
.video-card__avatar:deep(.avatar-placeholder) {
  border-radius: 50%;
}

.video-card__channel {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-card__channel:hover {
  color: hsl(var(--foreground));
}

.video-card__fallback {
  position: absolute;
  inset: 0;
  background: hsl(var(--muted));
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-card__fallback-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.video-card__fallback-text {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

@media (max-width: 640px) {
  .video-card__title {
    font-size: 0.8125rem;
  }

  .video-card__meta {
    font-size: 0.6875rem;
  }
}
</style>
