<template>
  <div
    class="video-terminal-item"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <div class="video-viewer-frame">
      <img
        v-if="thumbnailSrc && !showThumbnailFallback"
        :src="thumbnailSrc"
        loading="lazy"
        decoding="async"
        fetchpriority="low"
        referrerpolicy="no-referrer"
        class="video-terminal-image"
        :class="{
          'blur-thumbnail': shouldBlurThumbnail,
          'image-loaded': imageLoaded,
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

      <div class="video-duration-badge">{{ formatDuration(video.duration) }}</div>

      <!-- 进度条：1px 极细线 -->
      <div
        v-if="progressRatio > 0"
        class="tech-progress-bar"
      >
        <div
          class="tech-progress-fill"
          :style="{ width: `${(progressRatio * 100).toFixed(1)}%` }"
        ></div>
      </div>
    </div>

    <div class="video-terminal-info">
      <h5 class="video-terminal-title">{{ video.title }}</h5>
      <div class="video-terminal-meta">
        <div class="meta-left">
          <div v-if="displayAvatars.length" class="meta-avatar-frame">
            <SubscriptionAvatar
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="avatar.avatar"
              :name="avatar.name"
              size="xs"
              class="meta-avatar"
              @click.stop="goToSubscription(avatar.id)"
            />
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
/* ═══════════════════════════════════════════════════════════════════════
   Video Card - YouTube-inspired with tech aesthetic
   Based on: UI_UX_DESIGN_STANDARDS.md
   ═══════════════════════════════════════════════════════════════════════ */

.video-terminal-item {
  position: relative;
  cursor: pointer;
  padding: 0.75rem;
  border-radius: var(--radius-xl);
  transition:
    background-color var(--duration-fast) var(--ease-default),
    transform var(--duration-normal) var(--ease-default);
}

.video-terminal-item:hover {
  background: hsl(var(--foreground) / 0.04);
}

.video-viewer-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: hsl(var(--secondary));
  border-radius: var(--radius-lg);
  border: 1px solid hsl(var(--border) / 0.6);
  transition:
    border-color var(--duration-normal) var(--ease-default),
    box-shadow var(--duration-normal) var(--ease-default),
    transform var(--duration-normal) var(--ease-default);
}

.video-terminal-item:hover .video-viewer-frame {
  border-color: hsl(var(--primary) / 0.5);
  box-shadow:
    0 8px 24px -8px hsl(var(--primary) / 0.25),
    inset 0 0 12px hsl(var(--primary) / 0.05);
  transform: scale(1.01);
}

.video-terminal-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: contrast(1.0) brightness(1.0);
  opacity: 0;
  transition:
    opacity var(--duration-slow) var(--ease-default),
    transform var(--duration-normal) var(--ease-default),
    filter var(--duration-normal) var(--ease-default);
}

.video-terminal-image.image-loaded {
  opacity: 1;
}

.video-terminal-item:hover .video-terminal-image.image-loaded {
  filter: contrast(1.05) brightness(1.08);
  transform: scale(1.04);
}

.video-duration-badge {
  position: absolute;
  right: var(--space-2);
  bottom: var(--space-2);
  z-index: 6;
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: 500;
  color: #fff;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  padding: 2px var(--space-1);
  line-height: 1.2;
  pointer-events: none;
}

.tech-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.15);
  z-index: 5;
}

.tech-progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  box-shadow: 0 0 8px hsl(var(--primary) / 0.6);
  transition: width var(--duration-fast) var(--ease-default);
}

.video-terminal-info {
  margin-top: var(--space-3);
  z-index: 1;
  position: relative;
}

.video-terminal-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  line-height: 1.4;
  height: 2.8em;
  color: hsl(var(--foreground));
  margin-bottom: var(--space-2);
  letter-spacing: 0.01em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-terminal-item:hover .video-terminal-title {
  color: hsl(var(--primary));
}

.video-terminal-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  color: hsl(var(--muted-foreground));
  letter-spacing: 0.05em;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  flex: 1;
}

.meta-right {
  flex-shrink: 0;
}

.meta-avatar-frame {
  display: flex;
  align-items: center;
  background: hsl(var(--secondary));
  border: 1px solid hsl(var(--border) / 0.5);
  padding: 1px;
  border-radius: var(--radius-sm);
}

.meta-avatar {
  width: 14px;
  height: 14px;
  border-radius: var(--radius-sm);
}

.meta-avatar:deep(.avatar-image),
.meta-avatar:deep(.avatar-placeholder) {
  border-radius: var(--radius-sm);
}

.meta-avatar:deep(.avatar-image) {
  filter: grayscale(0.5);
  transition: filter var(--duration-fast) var(--ease-default);
}

.meta-channel {
  font-weight: 500;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-terminal-item:hover .meta-avatar:deep(.avatar-image) {
  filter: grayscale(0);
}

.meta-channel:hover {
  color: hsl(var(--foreground));
}

.video-terminal-fallback {
  position: absolute;
  inset: 0;
  background: hsl(var(--muted) / 0.5);
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
  gap: var(--space-2);
  z-index: 1;
}

.fallback-status {
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  color: hsl(var(--primary));
  letter-spacing: 0.2em;
  font-weight: 700;
  opacity: 0.6;
}

.fallback-id {
  font-family: var(--font-mono);
  font-size: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.4);
  letter-spacing: 0.1em;
}

/* ── Responsive ── */
@media (max-width: 640px) {
  .video-terminal-item {
    padding: 0.5rem;
  }

  .video-terminal-title {
    font-size: var(--font-size-xs);
    -webkit-line-clamp: 2;
  }

  .video-terminal-meta {
    font-size: 0.55rem;
  }
}
</style>
