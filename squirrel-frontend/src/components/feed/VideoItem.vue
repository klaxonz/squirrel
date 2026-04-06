<template>
  <div
    class="video-terminal-item"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <div class="video-viewer-frame">
      <img
        v-if="video.thumbnail && !showDefaultThumbnail"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="video-terminal-image"
        :class="{ 
          'blur-thumbnail': shouldBlurThumbnail,
          'image-loaded': imageLoaded 
        }"
        :alt="video.title"
        @load="handleImageLoad"
        @error="handleThumbnailError"
      >

      <!-- 电影感“无信号”占位图 -->
      <div v-else class="video-terminal-fallback">
        <div class="fallback-noise"></div>
        <div class="fallback-content">
          <span class="fallback-status">信号丢失</span>
          <span class="fallback-id">ID: {{ videoCardId }}</span>
        </div>
      </div>

      <div class="scanline"></div>
      <div class="video-status-overlay">
        <div class="flex justify-between items-start w-full">
          <div class="tech-tag">[信号锁定]</div>
          <div v-if="isLikedVideo" class="fav-dot"></div>
        </div>
        <div class="flex justify-between items-end w-full">
          <div class="tech-tag">ID: {{ videoCardId }}</div>
        </div>
      </div>

      <div class="video-duration-badge">{{ formatDuration(video.duration) }}</div>

      <!-- 进度条：1px 极细线 -->
      <div
        v-if="showProgress && progress > 0"
        class="tech-progress-bar"
      >
        <div
          class="tech-progress-fill"
          :style="{ width: `${(progress * 100).toFixed(1)}%` }"
        ></div>
      </div>
    </div>

    <div class="video-terminal-info">
      <h5 class="video-terminal-title">{{ video.title }}</h5>
      <div class="video-terminal-meta">
        <div class="meta-left">
          <div v-if="displayAvatars.length" class="meta-avatar-frame">
            <img
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="getAvatarSrc(avatar.avatar, `video-avatar-${video.id}-${index}`)"
              class="meta-avatar"
              referrerpolicy="no-referrer"
              :alt="avatar.name"
              @error="(event) => handleAvatarError(event, `video-avatar-${video.id}-${index}`)"
              @click.stop="goToSubscription(avatar.id)"
            >
          </div>
          <span class="meta-channel" @click.stop="goToSubscription(primarySubscriptionId)">
            {{ displayNames }}
          </span>
        </div>
        <div class="meta-right">
          <span class="meta-date">{{ displayDateText }}</span>
        </div>
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
import { Badge } from '@/components/ui/badge'
import ContextMenu from './ContextMenu.vue'
import useOptionsMenu from '@/composables/useOptionsMenu'
import useVideoHistory from '@/composables/useVideoHistory'
import useVideoInteraction from '@/composables/useVideoInteraction'
import { useImageFallback } from '@/composables/useImageFallback'
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
  showProgress: {
    type: Boolean,
    default: false,
  },
  progress: {
    type: Number,
    default: 0,
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
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const { copyVideoLink } = useOptionsMenu(toRef(props, 'video'))
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const showActors = ref(false)
const showDefaultThumbnail = ref(false)
const imageLoaded = ref(false)

const isNsfwVideo = computed(() => props.video.subscriptions?.some((subscription) => subscription.is_nsfw) || false)
const shouldBlurThumbnail = computed(() => systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value)
const isLikedVideo = computed(() => props.video.is_liked === 1)
const videoCardId = computed(() => formatVideoCardId(props.video?.id))
const videoBgIndex = computed(() => formatVideoCardId(props.video?.id, { length: 2, placeholder: '--' }))

const displayDateText = computed(() => {
  const timestamp = props.sortBy === 'created_at'
    ? (props.video.created_at || props.video.uploaded_at)
    : (props.video.uploaded_at || props.video.created_at)

  return timestamp ? formatDate(timestamp) : ''
})

const displayAvatars = computed(() => {
  let avatars = props.video.subscriptions?.map((subscription) => ({
    id: subscription.id,
    name: subscription.name,
    avatar: subscription.avatar,
  })) || []

  if (!avatars.length && props.video.actors) {
    avatars = props.video.actors.map((actor) => ({
      id: actor.id,
      name: actor.name,
      avatar: actor.avatar,
    }))
  }

  return avatars.slice(0, 3)
})

const displayNames = computed(() => {
  const names = displayAvatars.value.map((avatar) => avatar.name)

  if (!names.length) {
    return '未知'
  }

  return names.join(' / ')
})

const primarySubscriptionId = computed(() => {
  return props.video.subscriptions?.[0]?.id ?? displayAvatars.value[0]?.id
})

const closeContextMenu = () => {
  showMenu.value = false
}

const handleScroll = () => {
  if (showMenu.value) {
    closeContextMenu()
  }
}

const showContextMenu = async (event) => {
  event.preventDefault()
  event.stopPropagation()
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))

  await nextTick()

  menuPosition.value = {
    x: event.clientX,
    y: event.clientY,
  }
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
      if (!error) {
        props.video.is_liked = null
      }
    } else {
      const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
      if (!error) {
        props.video.is_liked = 1
      }
    }

    closeContextMenu()
  } catch (error) {
    Logger.error('Failed to toggle like state', error)
  }
}

const handleThumbnailError = () => {
  showDefaultThumbnail.value = true
}

const handleImageLoad = () => {
  imageLoaded.value = true
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
.video-terminal-item {
  position: relative;
  cursor: pointer;
  padding: 1rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  animation: item-appear 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes item-appear {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.video-viewer-frame {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: #000;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.video-terminal-item:hover .video-viewer-frame {
  border-color: rgba(255, 77, 0, 0.4);
  box-shadow: 
    0 0 30px rgba(255, 77, 0, 0.15),
    inset 0 0 15px rgba(255, 77, 0, 0.05);
}

.video-terminal-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: contrast(1.05) brightness(0.9);
  opacity: 0;
  transition: opacity 0.6s ease, transform 0.4s ease, filter 0.4s ease;
}

.video-terminal-image.image-loaded {
  opacity: 1;
}

.video-terminal-item:hover .video-terminal-image.image-loaded {
  filter: contrast(1.1) brightness(1.1);
  transform: scale(1.02);
}

.scanline {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
  z-index: 3;
  opacity: 0;
  pointer-events: none;
}

.video-terminal-item:hover .scanline {
  animation: scan 2s linear infinite;
  opacity: 1;
}

@keyframes scan {
  0% { top: 0; }
  100% { top: 100%; }
}

.video-status-overlay {
  position: absolute;
  inset: 0;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  z-index: 4;
  background: linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 30%, transparent 70%, rgba(0,0,0,0.6) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.video-terminal-item:hover .video-status-overlay {
  opacity: 1;
}

.tech-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: #ff4d00;
  letter-spacing: 0.1em;
  opacity: 0.8;
}

.fav-dot {
  width: 6px;
  height: 6px;
  background: #ff4d00;
  border-radius: 50%;
  box-shadow: 0 0 10px #ff4d00;
}

.video-duration-badge {
  position: absolute;
  right: 0.35rem;
  bottom: 0.35rem;
  z-index: 6;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #fff;
  background: rgba(0, 0, 0, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  padding: 2px 6px;
  line-height: 1.2;
  pointer-events: none;
}

.tech-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
  z-index: 5;
}

.tech-progress-fill {
  height: 100%;
  background: #ff4d00;
  box-shadow: 0 0 8px #ff4d00;
}

.video-terminal-info {
  margin-top: 0.75rem;
  z-index: 1;
  position: relative;
}

.video-terminal-title {
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.4;
  height: 2.8em;
  color: #fff;
  margin-bottom: 0.4rem;
  letter-spacing: 0.01em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.video-terminal-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
  flex: 1;
}

.meta-right {
  flex-shrink: 0;
}

.meta-avatar-frame {
  display: flex;
  align-items: center;
  background: #000;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 1px;
  border-radius: 2px;
}

.meta-avatar {
  width: 14px;
  height: 14px;
  object-fit: cover;
  filter: grayscale(0.5);
  transition: all 0.3s;
  border-radius: 1px;
}

.video-terminal-item:hover .meta-avatar {
  filter: grayscale(0);
}

.meta-channel:hover {
  color: #fff;
}

.video-terminal-fallback {
  position: absolute;
  inset: 0;
  background: #0a0a0a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.fallback-noise {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
  opacity: 0.05;
}

.fallback-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  z-index: 1;
}

.fallback-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #ff4d00;
  letter-spacing: 0.3em;
  font-weight: 800;
  opacity: 0.6;
}

.fallback-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.1em;
}
</style>
