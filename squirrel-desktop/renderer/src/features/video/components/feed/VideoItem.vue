<template>
  <article
    class="video-item group"
    :class="[
      layout === 'list' ? 'video-item--card' : 'video-item--grid',
      `video-item--appearance-${appearance}`,
    ]"
    role="button"
    tabindex="0"
    :aria-label="`播放：${video.title}`"
    @contextmenu.prevent="showContextMenu"
    @pointerenter="prefetchPlayback"
    @pointerdown.left="prefetchPlayback"
    @click="handleOpen"
    @keydown.enter.prevent="handleOpen"
    @keydown.space.prevent="handleOpen"
  >
    <!-- Reddit card: community meta on top -->
    <header v-if="layout === 'list'" class="video-item__top">
      <div class="video-item__community">
        <SubscriptionAvatar
          v-if="showAvatar && displayAvatars.length"
          class="video-item__avatar"
          :src="displayAvatars[0].avatar"
          :name="displayAvatars[0].name"
          size="sm"
          @click.stop="goToProfile(displayAvatars[0])"
        />
        <button
          type="button"
          class="video-item__source-name"
          @click.stop="goToProfile(primaryProfile)"
        >
          {{ displayNames }}
        </button>
        <span v-if="displayDateText" class="video-item__date">{{ displayDateText }}</span>
        <span v-if="video.site" class="video-item__site">{{ video.site }}</span>
      </div>
      <div class="video-item__top-actions" @click.stop>
        <button
          type="button"
          class="video-item__join"
          :class="{ 'is-on': isLater === 1 }"
          :title="isLater === 1 ? '取消稍后看' : '稍后看'"
          @click="toggleLater"
        >
          {{ isLater === 1 ? '已加' : '加入' }}
        </button>
      </div>
    </header>

    <h3
      class="video-item__title"
      :class="layout === 'list' ? 'video-item__title--card' : 'video-item__title--grid'"
    >
      {{ video.title }}
    </h3>

    <div
      class="video-item__thumb"
      :class="layout === 'list' ? 'video-item__thumb--card' : 'video-item__thumb--grid'"
    >
      <VideoThumbnail
        :src="thumbnailSrc"
        :alt="video.title"
        fit="cover"
        interactive
        :blur="shouldBlurThumbnail"
      />

      <span
        v-if="video.duration && showDuration"
        class="video-item__duration app-mono"
        :class="{ 'video-item__duration--with-progress': progressRatio > 0 }"
      >
        {{ formatDuration(video.duration) }}
      </span>

      <div v-if="layout !== 'list'" class="video-item__scrim" />

      <div
        v-if="showThumbnailProgress"
        class="video-item__progress"
        role="progressbar"
        :aria-valuenow="Math.round(progressRatio * 100)"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`已观看 ${Math.round(progressRatio * 100)}%`"
      >
        <div
          class="video-item__progress-fill"
          :style="{ width: `${progressRatio * 100}%` }"
        />
      </div>
    </div>

    <!-- Grid keeps compact meta under thumb -->
    <div v-if="layout !== 'list'" class="video-item__body">
      <div class="video-item__meta">
        <div v-if="showAvatar && displayAvatars.length" class="video-item__avatar">
          <SubscriptionAvatar
            :src="displayAvatars[0].avatar"
            :name="displayAvatars[0].name"
            size="md"
            @click.stop="goToProfile(displayAvatars[0])"
          />
        </div>
        <div class="video-item__meta-main">
          <div class="video-item__meta-line">
            <span class="video-item__source-name" @click.stop="goToProfile(primaryProfile)">
              {{ displayNames }}
            </span>
            <span v-if="displayDateText" class="video-item__date">{{ displayDateText }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Reddit-style bottom action bar on cards -->
    <footer v-if="layout === 'list'" class="video-item__bar" @click.stop>
      <button
        type="button"
        class="video-item__bar-btn"
        :class="{ 'is-on': isLiked === 1 }"
        :title="isLiked === 1 ? '取消喜欢' : '喜欢'"
        :aria-pressed="isLiked === 1"
        @click="toggleLikeVideo"
      >
        <AppIcon name="heart" class="size-4" :class="{ 'fill-current': isLiked === 1 }" />
        <span>{{ isLiked === 1 ? '已喜欢' : '喜欢' }}</span>
      </button>
      <button
        type="button"
        class="video-item__bar-btn"
        :class="{ 'is-on': isRead }"
        :title="isRead ? '标记未读' : '标记已读'"
        :aria-pressed="isRead"
        @click="toggleReadStatus(!isRead)"
      >
        <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-4" />
        <span>{{ isRead ? '已读' : '标已读' }}</span>
      </button>
      <button
        type="button"
        class="video-item__bar-btn"
        :class="{ 'is-on': isLater === 1 }"
        :title="isLater === 1 ? '取消稍后看' : '稍后看'"
        :aria-pressed="isLater === 1"
        @click="toggleLater"
      >
        <AppIcon :name="isLater === 1 ? 'watchLaterActive' : 'watchLater'" class="size-4" />
        <span>稍后看</span>
      </button>
    </footer>

    <Teleport to="body">
      <ContextMenu
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :video="video"
        :is-liked="isLiked"
        :is-later="isLater"
        :is-read="isRead"
        @close="showMenu = false"
        @toggle-read-status="toggleReadStatus"
        @toggle-like="toggleLikeVideo"
        @toggle-later="toggleLater"
      />
    </Teleport>
  </article>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import ContextMenu from './ContextMenu.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { updateVideoReadState } from '@/shared/api'
import { useSystemConfig } from '@/shared/composables/useSystemConfig'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import {
  pickPrimaryProfile,
  profileDisplayNames,
} from '@/features/video/composables/useProfileNavigation'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'

const props = withDefaults(defineProps<{
  video: VideoListItem
  showAvatar?: boolean
  sortBy?: string
  layout?: 'grid' | 'list'
  showDuration?: boolean
  thumbnailProgress?: boolean
  appearance?: 'default' | 'workbench'
}>(), {
  layout: 'grid',
  showDuration: true,
  thumbnailProgress: true,
  appearance: 'default',
})

const emit = defineEmits<{
  goToProfile: [profile: VideoProfile]
  /** @deprecated prefer goToProfile */
  goToSubscription: [id: number | string]
  openModal: [video: VideoListItem]
}>()

const { config: systemConfig } = useSystemConfig()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()
const toast = useToast()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })

const isRead = ref(false)
const isLiked = ref<number | null>(null)
const isLater = ref<number | null>(null)

function hydrateFromVideo(video: VideoListItem) {
  isRead.value = video.is_read ?? Number(video.last_position || 0) > 0
  const type = video.interaction_type
  isLiked.value = type === INTERACTION_TYPE.LIKE ? 1 : null
  isLater.value = type === INTERACTION_TYPE.LATER ? 1 : null
}

hydrateFromVideo(props.video)

watch(
  () => [props.video.id, props.video.is_read, props.video.interaction_type, props.video.last_position] as const,
  () => hydrateFromVideo(props.video),
)

const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const isNsfwVideo = computed(() => props.video.subscriptions?.some((s) => s.is_nsfw))
const shouldBlurThumbnail = computed(() => Boolean(systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value))

const progressRatio = computed(() => {
  const d = Number(props.video?.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video?.last_position || 0) / d) : 0
})
const showThumbnailProgress = computed(() => props.thumbnailProgress && progressRatio.value > 0)

const displayDateText = computed(() => {
  const t = props.sortBy === 'created_at'
    ? (props.video.created_at || props.video.uploaded_at)
    : (props.video.uploaded_at || props.video.created_at)
  return t ? formatDate(t) : ''
})

const displayAvatars = computed(() => {
  const primary = pickPrimaryProfile(props.video)
  return primary ? [primary] : []
})

const displayNames = computed(() => profileDisplayNames(props.video, '未知'))

const primaryProfile = computed(() => pickPrimaryProfile(props.video))

const closeMenuOnExternalClose = () => { showMenu.value = false }

const showContextMenu = async (event: MouseEvent) => {
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))
  await nextTick()
  menuPosition.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

const handleOpen = () => emit('openModal', props.video)

const prefetchPlayback = () => {
  void prefetchDesktopPlaybackSource(props.video)
}

const goToProfile = (profile: VideoProfile | null | undefined) => {
  if (!profile) return
  let source = profile.profile_source
  if (!source) {
    const id = profile.id
    const inSubs = (props.video.subscriptions || []).some((s) => s.id === id && id != null)
    const inActors = (props.video.actors || []).some((a) => a.id === id && id != null)
    if (inSubs) source = 'subscription'
    else if (inActors) source = 'creator'
  }
  const resolved: VideoProfile = source ? { ...profile, profile_source: source } : profile
  emit('goToProfile', resolved)
  if (resolved.profile_source === 'subscription' && resolved.id != null && resolved.id !== '') {
    emit('goToSubscription', resolved.id)
  }
}

const toggleReadStatus = async (markRead: boolean) => {
  const previous = isRead.value
  isRead.value = markRead
  try {
    await updateVideoReadState(props.video.id, markRead)
  } catch (err) {
    isRead.value = previous
    toast.error(errorMessage(err, markRead ? '标记已读失败' : '标记未读失败'))
  }
  showMenu.value = false
}

const setExclusiveInteraction = async (next: 'like' | 'later' | null) => {
  const prevLiked = isLiked.value
  const prevLater = isLater.value

  if (next === 'like') {
    isLiked.value = 1
    isLater.value = null
  } else if (next === 'later') {
    isLater.value = 1
    isLiked.value = null
  } else {
    isLiked.value = null
    isLater.value = null
  }

  try {
    if (next === 'like') {
      await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
    } else if (next === 'later') {
      await toggleLike(props.video.id, INTERACTION_TYPE.LATER)
    } else {
      await deleteInteraction(props.video.id)
    }
  } catch (err) {
    isLiked.value = prevLiked
    isLater.value = prevLater
    toast.error(errorMessage(err, '更新互动状态失败'))
  }
}

const toggleLikeVideo = async () => {
  await setExclusiveInteraction(isLiked.value === 1 ? null : 'like')
  showMenu.value = false
}

const toggleLater = async () => {
  await setExclusiveInteraction(isLater.value === 1 ? null : 'later')
  showMenu.value = false
}

onMounted(() => document.addEventListener('closeAllContextMenus', closeMenuOnExternalClose))
onUnmounted(() => document.removeEventListener('closeAllContextMenus', closeMenuOnExternalClose))
</script>

<style scoped>
.video-item {
  display: flex;
  cursor: pointer;
  border: 0;
  background: transparent;
  padding: 0;
  outline: none;
  transition: background-color var(--duration-fast) var(--ease-default);
}

/* Reddit card post: white surface, full-width media */
.video-item--card {
  flex-direction: column;
  gap: 0;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
}

.video-item--card:hover {
  border-color: hsl(var(--foreground) / 0.18);
  background: hsl(var(--card));
}

.video-item--grid {
  flex-direction: column;
  gap: 0.5rem;
  border-radius: var(--radius-md);
}

.video-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.4);
}

.video-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.875rem 0.25rem;
}

.video-item__community {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.video-item__top-actions {
  flex: 0 0 auto;
}

.video-item__join {
  height: 1.75rem;
  border: 0;
  border-radius: 999px;
  padding: 0 0.75rem;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}

.video-item__join.is-on {
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
}

.video-item__join:hover {
  filter: brightness(1.05);
}

.video-item__title {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-weight: 700;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-item__title--card {
  padding: 0.25rem 0.875rem 0.625rem;
  font-size: 1.125rem;
  letter-spacing: -0.015em;
  -webkit-line-clamp: 3;
}

.video-item__title--grid {
  min-height: calc(2 * 0.875rem * 1.35);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
}

.video-item__thumb {
  position: relative;
  overflow: hidden;
  border: 0;
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.video-item__thumb--card {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 0;
}

.video-item__thumb--grid {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-sm);
}

.video-item--card:hover .video-item__thumb--card {
  filter: brightness(0.98);
}

.video-item__duration {
  position: absolute;
  right: 0.5rem;
  bottom: 0.5rem;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: var(--radius-sm);
  background: var(--app-media-badge-bg);
  color: hsl(var(--app-media-on-image));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.video-item__duration--with-progress {
  bottom: 0.65rem;
}

.video-item__scrim {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  height: 2.75rem;
  pointer-events: none;
  background: linear-gradient(to top, var(--app-media-scrim-mid), transparent);
}

.video-item__progress {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 20;
  height: 3px;
  overflow: hidden;
  background: var(--app-media-progress-track);
}

.video-item__progress-fill {
  height: 100%;
  background: hsl(var(--primary));
}

.video-item__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0 0.125rem 0.25rem;
}

.video-item__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
}

.video-item__avatar {
  flex: 0 0 auto;
}

.video-item__meta-main {
  min-width: 0;
  flex: 1 1 auto;
}

.video-item__meta-line {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.video-item__source-name {
  overflow: hidden;
  border: 0;
  padding: 0;
  background: transparent;
  color: hsl(var(--foreground));
  font: inherit;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.video-item__source-name:hover {
  text-decoration: underline;
}

.video-item__date,
.video-item__site {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--muted-foreground));
}

.video-item__date::before,
.video-item__site::before {
  content: '·';
  margin-right: 0.3rem;
  color: hsl(var(--muted-foreground) / 0.5);
}

.video-item__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem 0.5rem;
}

.video-item__bar-btn {
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  border-radius: 999px;
  padding: 0 0.625rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}

.video-item__bar-btn:hover {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground));
}

.video-item__bar-btn.is-on {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.video-item--appearance-workbench.video-item--card {
  border-radius: var(--radius-lg);
}

@media (prefers-reduced-motion: reduce) {
  .video-item,
  .video-item__progress-fill,
  .video-item__source-name {
    transition: none;
  }
}
</style>
