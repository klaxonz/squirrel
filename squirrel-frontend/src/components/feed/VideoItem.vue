<template>
  <div
    class="video-terminal-item"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <!-- 背景大数字索引 -->
    <div class="video-bg-index">{{ videoBgIndex }}</div>

    <div class="video-viewer-frame group">
      <!-- 四角取景框线 -->
      <div class="corner-mark top-left"></div>
      <div class="corner-mark top-right"></div>
      <div class="corner-mark bottom-left"></div>
      <div class="corner-mark bottom-right"></div>

      <img
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="video-terminal-image"
        :class="{ 'blur-thumbnail': shouldBlurThumbnail }"
        :alt="video.title"
        @error="handleThumbnailError"
      >

      <!-- 动态扫描线（仅悬停显示） -->
      <div class="scanline"></div>

      <div class="video-status-overlay">
        <div class="status-top">
          <span class="tech-tag">REC // {{ videoCardId }}</span>
          <div v-if="isLikedVideo" class="fav-dot"></div>
        </div>
        <div class="status-bottom">
          <span class="tech-time">{{ formatDuration(video.duration) }}</span>
        </div>
      </div>

      <!-- 进度条改到顶部，极细 -->
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
    return 'UNKNOWN'
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
  padding: 1.5rem;
  transition: all 0.5s cubic-bezier(0.19, 1, 0.22, 1);
}

.video-bg-index {
  position: absolute;
  top: 0;
  left: 0;
  font-size: 6rem;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.03);
  font-family: 'Courier New', Courier, monospace;
  line-height: 1;
  pointer-events: none;
  z-index: 0;
}

.video-viewer-frame {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: #000;
  z-index: 1;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* 取景框线 */
.corner-mark {
  position: absolute;
  width: 10px;
  height: 10px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  z-index: 2;
  transition: all 0.3s ease;
}

.top-left { top: 10px; left: 10px; border-right: none; border-bottom: none; }
.top-right { top: 10px; right: 10px; border-left: none; border-bottom: none; }
.bottom-left { bottom: 10px; left: 10px; border-right: none; border-top: none; }
.bottom-right { bottom: 10px; right: 10px; border-left: none; border-top: none; }

.video-terminal-item:hover .corner-mark {
  border-color: #ff4d00;
  width: 15px;
  height: 15px;
}

.video-terminal-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: all 0.6s cubic-bezier(0.19, 1, 0.22, 1);
}

.video-terminal-item:hover .video-terminal-image {
  transform: scale(1.05);
}

/* 扫描线动画 */
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
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  z-index: 4;
  background: linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 30%, transparent 70%, rgba(0,0,0,0.6) 100%);
  opacity: 0.8;
}

.tech-tag {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  color: #fff;
  letter-spacing: 0.2em;
}

.fav-dot {
  width: 6px;
  height: 6px;
  background: #ff4d00;
  border-radius: 50%;
  box-shadow: 0 0 10px #ff4d00;
}

.tech-time {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
  color: #fff;
  background: rgba(0,0,0,0.5);
  padding: 2px 5px;
}

.tech-progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  z-index: 5;
}

.tech-progress-fill {
  height: 100%;
  background: #ff4d00;
  box-shadow: 0 0 5px #ff4d00;
}

.video-terminal-info {
  margin-top: 1rem;
  z-index: 1;
  position: relative;
}

.video-terminal-title {
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.4;
  height: 2.8em; /* 固定两行高度 */
  color: #fff;
  margin-bottom: 0.5rem;
  letter-spacing: 0.02em;
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
  font-family: 'Courier New', Courier, monospace;
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
}

.meta-avatar {
  width: 14px;
  height: 14px;
  object-fit: cover;
  filter: grayscale(0.5);
  transition: all 0.3s;
}

.video-terminal-item:hover .meta-avatar {
  filter: grayscale(0);
}

.meta-channel:hover {
  color: #fff;
}

.meta-divider {
  opacity: 0.2;
}

.blur-thumbnail {
  filter: blur(25px) grayscale(1);
}
</style>
