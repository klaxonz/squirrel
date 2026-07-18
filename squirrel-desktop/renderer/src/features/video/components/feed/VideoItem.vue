<template>
  <article
    class="video-item group"
    :class="layout === 'list' ? 'video-item--list' : 'video-item--grid'"
    role="button"
    tabindex="0"
    :aria-label="`打开：${video.title}`"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
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

      <!-- Active flags only — quiet, non-toolbar chrome. Full toggles live in meta. -->
      <div
        v-if="showThumbnailFlags"
        class="video-item__flags"
        aria-hidden="true"
      >
        <span v-if="isRead" class="video-item__flag" title="已读">
          <AppIcon name="check" class="size-3" />
        </span>
        <span v-if="isLater === 1" class="video-item__flag" title="稍后看">
          <AppIcon name="watchLaterActive" class="size-3" />
        </span>
        <span v-if="isLiked === 1" class="video-item__flag" title="喜欢">
          <AppIcon name="heart" class="size-3 fill-current" />
        </span>
      </div>

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
            size="lg"
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
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
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
  thumbnailStatus?: 'full' | 'progress-only' | 'none'
}>(), {
  layout: 'grid',
  showDuration: true,
  thumbnailStatus: 'full',
})

const emit = defineEmits<{
  goToProfile: [profile: VideoProfile]
  /** @deprecated prefer goToProfile */
  goToSubscription: [id: number | string]
  openModal: [video: VideoListItem]
}>()

const { config: systemConfig } = useSystemConfig()
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()
const toast = useToast()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })

/**
 * Local optimistic engagement state, seeded from list fields:
 * - is_read: history row exists
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

const hasActiveFlags = computed(
  () => isRead.value || isLater.value === 1 || isLiked.value === 1,
)
const showThumbnailFlags = computed(() => props.thumbnailStatus === 'full' && hasActiveFlags.value)

const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const isNsfwVideo = computed(() => props.video.subscriptions?.some((s) => s.is_nsfw))
const shouldBlurThumbnail = computed(() => Boolean(systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value))

const progressRatio = computed(() => {
  const d = Number(props.video?.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video?.last_position || 0) / d) : 0
})
const showThumbnailProgress = computed(() => props.thumbnailStatus !== 'none' && progressRatio.value > 0)

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

const handleClick = () => emit('openModal', props.video)
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
    if (markRead) {
      const pos = Number(props.video.duration || 0)
      await sendReport(props.video.id, pos, { force: true })
    } else {
      await clearHistory([props.video.id])
    }
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
  border-radius: var(--radius-lg);
  outline: none;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-item--grid {
  flex-direction: column;
  gap: 0.625rem;
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
  box-shadow: var(--shadow-card-hover);
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

/* Quiet status chips — only when a flag is on; never three equal toolbar buttons */
.video-item__flags {
  position: absolute;
  top: 0.375rem;
  left: 0.375rem;
  z-index: var(--z-content);
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.15rem 0.3rem;
  border-radius: 999px;
  background: var(--app-media-flag-bg);
  color: hsl(var(--app-media-on-image) / 0.94);
  pointer-events: none;
}

.video-item__flag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
  padding-inline: 0.125rem;
}

.video-item__body--list {
  padding-block: 0.25rem;
}

.video-item__title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-weight: 600;
  line-height: 1.3;
  transition: color var(--duration-fast) var(--ease-default);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-item__title--grid {
  font-size: 0.9375rem;
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
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 0.625rem;
}

.video-item__avatar {
  flex: 0 0 auto;
  margin-top: 0.125rem;
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

/* Quick ops: meta-row ghost icons — media stays clean */
.video-item__quick {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.125rem;
  margin-top: 0.0625rem;
  margin-inline-start: auto;
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
  opacity: 0;
  pointer-events: none;
  transition:
    opacity var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-item:hover .video-item__quick-btn,
.video-item:focus-within .video-item__quick-btn,
.video-item__quick-btn.is-on {
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
  opacity: 1;
  pointer-events: auto;
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

@media (min-width: 768px) {
  .video-item__description {
    display: -webkit-box;
  }
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .video-item__quick-btn {
    opacity: 1;
    pointer-events: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .video-item,
  .video-item__thumb,
  .video-item__progress-fill,
  .video-item__quick-btn,
  .video-item__source-name,
  .video-item__title {
    transition: none;
  }
}
</style>
