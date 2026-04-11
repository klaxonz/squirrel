<template>
  <div
    class="history-item"
    @click="$emit('open', video)"
  >
    <!-- Thumbnail Section -->
    <div class="thumbnail-wrapper">
      <div class="thumbnail-container">
        <img
          v-if="video.thumbnail && !showDefaultThumbnail"
          :src="video.thumbnail"
          referrerpolicy="no-referrer"
          class="thumbnail-image"
          :class="{ 'image-loaded': imageLoaded }"
          :alt="video.title"
          @load="imageLoaded = true"
          @error="handleThumbnailError"
        />

        <!-- Terminal Fallback -->
        <div v-else class="video-terminal-fallback">
          <div class="fallback-noise"></div>
          <div class="fallback-content">
            <span class="fallback-status">信号丢失</span>
            <span class="fallback-id">ID: {{ videoCardId }}</span>
          </div>
        </div>

        <!-- Duration Badge -->
        <div class="duration-badge">{{ formatDuration(video.duration) }}</div>

        <!-- Progress Bar -->
        <div
          v-if="video.progress > 0"
          class="progress-bar"
        >
          <div
            class="progress-fill"
            :style="{ width: `${video.progress * 100}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Info Section -->
    <div class="info-container">
      <h4 class="video-title line-clamp-2">{{ video.title }}</h4>

      <div class="meta-row">
        <div class="meta-left">
          <div v-if="displayAvatars.length" class="avatar-stack">
            <SubscriptionAvatar
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="avatar.avatar"
              :name="avatar.name"
              size="xs"
              class="history-item__avatar"
            />
          </div>

          <span v-if="displayChannel" class="channel-name">{{ displayChannel }}</span>
        </div>

        <div class="meta-right">
          <span v-if="video.progress > 0" class="progress-text">已看 {{ (video.progress * 100).toFixed(0) }}%</span>
          <span v-else class="progress-text">未观看</span>
          <span class="separator">·</span>
          <span class="watch-time">{{ formatLastWatchTime(video.played_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Actions Section -->
    <div class="actions-container" :class="{ 'is-always-visible': isMobile }">
      <button
        class="delete-btn"
        :title="isMobile ? '移除' : '从历史记录中移除'"
        @click.stop="handleDelete"
      >
        <TrashIcon class="h-4 w-4" />
      </button>
    </div>

    <!-- Delete Confirmation Dialog -->
    <Dialog :open="showDeleteConfirm" @update:open="showDeleteConfirm = $event">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>移除历史记录</DialogTitle>
          <DialogDescription>
            确定要移除这条播放记录吗？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button variant="secondary" size="sm" @click="showDeleteConfirm = false">取消</Button>
          <Button variant="destructive" size="sm" @click="confirmDelete">确认移除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { TrashIcon } from '@heroicons/vue/24/outline'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { formatDuration } from '@/utils/dateFormat'
import { formatVideoCardId } from '@/utils/videoCard'

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['open', 'delete'])

const showDefaultThumbnail = ref(false)
const imageLoaded = ref(false)
const showDeleteConfirm = ref(false)
const isMobile = ref(false)

const videoCardId = computed(() => formatVideoCardId(props.video?.id))

const handleThumbnailError = () => {
  imageLoaded.value = false
  showDefaultThumbnail.value = true
}

const handleDelete = () => {
  showDeleteConfirm.value = true
}

const confirmDelete = () => {
  emit('delete', props.video.history_id ?? props.video.id)
  showDeleteConfirm.value = false
}

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

const displayChannel = computed(() => {
  if (props.video.subscriptions && props.video.subscriptions.length > 0) {
    return props.video.subscriptions.map(s => s.name).join(' / ')
  }
  return ''
})

const formatLastWatchTime = (timestamp) => {
  if (!timestamp) return ''
  const raw = typeof timestamp === 'string' ? timestamp : String(timestamp)
  const datePart = raw.includes('T') ? raw.split('T')[0] : raw.split(' ')[0]
  const date = new Date(datePart)
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)

  if (date.getTime() === now.getTime()) {
    return '今天'
  } else if (date.getTime() === yesterday.getTime()) {
    return '昨天'
  } else {
    return `${date.getMonth() + 1}/${date.getDate()}`
  }
}

const checkMobile = () => {
  isMobile.value = window.innerWidth < 640
}

watch(
  () => props.video?.thumbnail,
  () => {
    imageLoaded.value = false
    showDefaultThumbnail.value = false
  }
)

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.history-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.5rem 0;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: hsl(var(--secondary) / 0.08);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Thumbnail */
.thumbnail-wrapper {
  position: relative;
  flex-shrink: 0;
}

.thumbnail-container {
  position: relative;
  width: 11rem;
  aspect-ratio: 16/9;
  background: hsl(var(--secondary) / 0.3);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

@media (max-width: 640px) {
  .thumbnail-container {
    width: 8rem;
  }
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.5s ease, transform 0.3s ease;
}

.thumbnail-image.image-loaded {
  opacity: 1;
}

.history-item:hover .thumbnail-image.image-loaded {
  transform: scale(1.04);
}

.duration-badge {
  position: absolute;
  right: 0.3rem;
  bottom: 0.3rem;
  z-index: 4;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: #fff;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  padding: 1px 5px;
}

/* Progress Bar - 放在封面内 */
.progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 0;
  z-index: 1;
}

.progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  box-shadow: 0 0 6px hsl(var(--primary) / 0.8);
  border-radius: 0;
}

/* Info Container */
.info-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding-right: 0.5rem;
}

.video-title {
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.4;
  color: hsl(var(--foreground));
  transition: color 0.2s ease;
}

.history-item:hover .video-title {
  color: hsl(var(--primary));
}

.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground));
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex: 1;
}

.avatar-stack {
  display: flex;
  align-items: center;
}

.history-item__avatar {
  width: 1rem;
  height: 1rem;
  border-radius: 2px;
  margin-right: -0.25rem;
  border: 1px solid hsl(var(--background));
}

.channel-name {
  font-weight: 500;
  color: hsl(var(--foreground) / 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta-right {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.progress-text {
  color: hsl(var(--primary) / 0.8);
  font-weight: 500;
}

.separator {
  opacity: 0.4;
}

.watch-time {
  opacity: 0.7;
}

/* Actions */
.actions-container {
  flex-shrink: 0;
  align-self: flex-start;
  opacity: 0;
  transition: opacity 0.2s ease;
  display: flex;
  align-items: center;
  padding: 0 0.25rem;
}

.history-item:hover .actions-container {
  opacity: 1;
}

.actions-container.is-always-visible {
  opacity: 1;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: hsl(var(--muted-foreground) / 0.6);
  transition: all 0.15s ease;
}

.delete-btn:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

/* Terminal Fallback */
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
  gap: 0.4rem;
  z-index: 1;
}

.fallback-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: #ff4d00;
  letter-spacing: 0.25rem;
  font-weight: 800;
  opacity: 0.6;
}

.fallback-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.45rem;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.1em;
}

/* Responsive */
@media (max-width: 640px) {
  .info-container {
    padding-right: 0;
  }

  .meta-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .meta-right {
    font-size: 0.6rem;
  }
}
</style>
