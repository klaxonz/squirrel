<template>
  <article
    class="video-item group"
    :class="[
      layout === 'list' ? 'video-item--list' : 'video-item--grid',
      `video-item--appearance-${appearance}`,
    ]"
    role="button"
    tabindex="0"
    :aria-label="`播放：${video.title}`"
    @contextmenu.prevent="showContextMenu"
    @click="handleOpen"
    @keydown.enter.prevent="handleOpen"
    @keydown.space.prevent="handleOpen"
  >
    <div
      class="video-item__thumb"
      :class="layout === 'list' ? 'video-item__thumb--list' : 'video-item__thumb--grid'"
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

      <div class="video-item__scrim" />

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

    <div class="video-item__body" :class="{ 'video-item__body--list': layout === 'list' }">
      <h3
        class="video-item__title"
        :class="layout === 'list' ? 'video-item__title--list' : 'video-item__title--grid'"
      >
        {{ video.title }}
      </h3>

      <div class="video-item__meta">
        <div v-if="showAvatar && displayAvatars.length" class="video-item__avatar">
          <SubscriptionAvatar
            :src="displayAvatars[0].avatar"
            :name="displayAvatars[0].name"
            :size="layout === 'list' ? 'lg' : 'md'"
            @click.stop="goToProfile(displayAvatars[0])"
          />
        </div>

        <div class="video-item__meta-main">
          <!-- One scannable meta line — source · date (site demoted / list-only). -->
          <div class="video-item__meta-line">
            <span class="video-item__source-name" @click.stop="goToProfile(primaryProfile)">
              {{ displayNames }}
            </span>
            <span v-if="displayDateText" class="video-item__date">{{ displayDateText }}</span>
            <span
              v-if="layout === 'list' && video.site"
              class="video-item__site"
            >{{ video.site }}</span>
            <span
              v-if="layout === 'list' && video.duration"
              class="video-item__list-duration app-mono"
            >
              {{ formatDuration(video.duration) }}
            </span>
          </div>
        </div>

        <!-- Secondary ops: ghost icon toggles in meta, not on the poster. -->
        <div
          class="video-item__quick"
          role="group"
          aria-label="视频快捷操作"
          @click.stop
        >
          <button
            type="button"
            class="video-item__quick-btn"
            :class="{ 'is-on': isRead }"
            :title="isRead ? '标记未读' : '标记已读'"
            :aria-label="isRead ? '标记未读' : '标记已读'"
            :aria-pressed="isRead"
            @click="toggleReadStatus(!isRead)"
          >
            <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-3.5" />
          </button>
          <button
            type="button"
            class="video-item__quick-btn"
            :class="{ 'is-on': isLater === 1 }"
            :title="isLater === 1 ? '取消稍后看' : '稍后看（会替换喜欢）'"
            :aria-label="isLater === 1 ? '取消稍后看' : '稍后看'"
            :aria-pressed="isLater === 1"
            @click="toggleLater"
          >
            <AppIcon
              :name="isLater === 1 ? 'watchLaterActive' : 'watchLater'"
              class="size-3.5"
            />
          </button>
          <button
            type="button"
            class="video-item__quick-btn"
            :class="{ 'is-on': isLiked === 1 }"
            :title="isLiked === 1 ? '取消喜欢' : '喜欢（会替换稍后看）'"
            :aria-label="isLiked === 1 ? '取消喜欢' : '喜欢'"
            :aria-pressed="isLiked === 1"
            @click="toggleLikeVideo"
          >
            <AppIcon
              name="heart"
              class="size-3.5"
              :class="{ 'fill-current': isLiked === 1 }"
            />
          </button>
        </div>
      </div>

      <div
        v-if="layout === 'list' && video.description"
        class="video-item__description"
      >
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

/**
 * Local optimistic engagement state, seeded from list fields:
 * - is_read: explicit inbox state, independent from playback progress
 * - interaction_type: exclusive 1=like / 2=dislike / 3=later
 *
 * Like and later share one backend row — setting one replaces the other.
 */
const isRead = ref(false)
const isLiked = ref<number | null>(null)
const isLater = ref<number | null>(null)

function hydrateFromVideo(video: VideoListItem) {
  // Prefer explicit is_read; fall back to last_position for older payloads.
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
const goToProfile = (profile: VideoProfile | null | undefined) => {
  if (!profile) return
  // Fill profile_source when list payload omitted it, so navigation never
  // mistakes a creator id for a subscription id.
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

/**
 * Exclusive engagement toggle. Backend stores one interaction_type per
 * user/video, so enabling like clears later (and vice versa).
 */
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
  border-radius: var(--radius-lg);
  background: transparent;
  padding: 0;
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default);
}

.video-item:hover {
  background: transparent;
}

.video-item--grid {
  flex-direction: column;
  gap: 0.5rem;
}

.video-item--list {
  flex-direction: row;
  gap: var(--space-4);
}

.video-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.4);
}

/* Thumbnail: media first, no action toolbar. */
.video-item__thumb {
  position: relative;
  overflow: hidden;
  border: 0;
  border-radius: var(--app-card-radius);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
  transition:
    box-shadow var(--duration-base) var(--ease-default),
    transform var(--duration-base) var(--ease-default);
}

.video-item:hover .video-item__thumb,
.video-item:focus-visible .video-item__thumb {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.16);
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
  border-radius: var(--radius-sm);
  background: var(--app-media-badge-bg);
  color: hsl(var(--app-media-on-image));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  letter-spacing: 0.01em;
}

.video-item__duration--with-progress {
  bottom: 0.55rem;
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
  transition: width var(--duration-slow) var(--ease-out);
}

/* ── Body / meta ────────────────────────────────────────────────────────── */
.video-item__body {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0 0.125rem 0.25rem;
}

.video-item__body--list {
  padding-block: 0.25rem;
}


.video-item__title {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-weight: 600;
  line-height: 1.3;
  transition: color var(--duration-fast) var(--ease-default);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-item__title--grid {
  min-height: calc(2 * 0.875rem * 1.35);
  font-size: 0.875rem;
  line-height: 1.35;
}

.video-item__title--list {
  margin-bottom: 0.125rem;
  font-size: 1rem;
  -webkit-line-clamp: 2;
}

.video-item:hover .video-item__title {
  color: hsl(var(--foreground));
}

.video-item__meta {
  position: relative;
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
}

.video-item__avatar {
  flex: 0 0 auto;
}

.video-item__meta-main {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0;
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

.video-item__date {
  flex: 0 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--muted-foreground) / 0.88);
}

.video-item__date::before {
  content: '·';
  margin-right: 0.3rem;
  color: hsl(var(--muted-foreground) / 0.45);
}

.video-item__source-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-item__source-name:hover {
  color: hsl(var(--foreground));
}

.video-item__site {
  flex: 0 0 auto;
  max-width: 5.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 500;
}

.video-item__site::before {
  content: '·';
  margin-right: 0.3rem;
  color: hsl(var(--muted-foreground) / 0.45);
}

.video-item__list-duration {
  margin-left: 0.5rem;
  padding: 0 0.25rem;
  border-radius: 0.25rem;
  background: hsl(var(--muted));
}

/* Quick ops overlay secondary metadata on demand instead of permanently
   shrinking the source/date line. Active state is already visible on-image. */
.video-item__quick {
  position: absolute;
  top: 50%;
  right: 0;
  z-index: var(--z-content);
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  padding-left: 0.75rem;
  background: linear-gradient(to right, hsl(var(--background) / 0), hsl(var(--background)) 32%);
  opacity: 0;
  pointer-events: none;
  transform: translateY(-50%);
  transition: opacity var(--duration-fast) var(--ease-default);
}

.video-item__quick-btn {
  display: inline-flex;
  width: 1.5rem;
  height: 1.5rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.55);
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-item:hover .video-item__quick,
.video-item:focus-within .video-item__quick {
  opacity: 1;
  pointer-events: auto;
}

.video-item__quick-btn:hover {
  background: hsl(var(--foreground) / 0.06);
  color: var(--app-selection-fg);
}

.video-item__quick-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.45);
}

.video-item__quick-btn.is-on {
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
}

.video-item__quick-btn.is-on:hover {
  background: var(--app-selection-bg-hover);
}

.video-item__description {
  display: none;
  margin-top: 0.375rem;
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.75rem;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-item--appearance-workbench {
  padding: 0;
}

.video-item--appearance-workbench:hover {
  background: transparent;
}

.video-item--appearance-workbench .video-item__thumb {
  border-radius: var(--radius-md);
  box-shadow: none;
}

.video-item--appearance-workbench:hover .video-item__thumb,
.video-item--appearance-workbench:focus-visible .video-item__thumb {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.16);
}

.video-item--appearance-workbench .video-item__scrim {
  display: none;
}

.video-item--appearance-workbench .video-item__body {
  padding: 0 0.125rem 0.25rem;
}

.video-item--appearance-workbench .video-item__title {
  font-weight: 620;
  letter-spacing: -0.012em;
}

@media (min-width: 768px) {
  .video-item__description {
    display: -webkit-box;
  }
}

@media (hover: none) {
  .video-item__quick {
    position: static;
    padding-left: 0;
    background: transparent;
    opacity: 1;
    pointer-events: auto;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .video-item,
  .video-item__thumb,
  .video-item__progress-fill,
  .video-item__quick,
  .video-item__quick-btn,
  .video-item__source-name,
  .video-item__title {
    transition: none;
  }
}
</style>
