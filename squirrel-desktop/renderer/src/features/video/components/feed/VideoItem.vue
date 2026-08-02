<template>
  <article
    class="video-item group"
    :class="[
      layout === 'list'
        ? (appearance === 'workbench' ? 'video-item--row' : 'video-item--card')
        : 'video-item--grid',
      `video-item--appearance-${appearance}`,
    ]"
    @contextmenu.prevent="showContextMenu"
    @pointerenter="prefetchPlayback"
    @pointerdown.left="prefetchPlayback"
  >
    <VideoItemWorkbenchLayout
      v-if="layout === 'list' && appearance === 'workbench'"
      :video="video"
      :thumbnail="thumbnailPresentation"
      :profile="profilePresentation"
      :actions="actionPresentation"
      @activate="handleOpen"
      @open-profile="goToProfile"
      @toggle-like="toggleLikeVideo"
      @toggle-read="toggleReadStatus"
      @toggle-later="toggleLater"
    />
    <VideoItemFeedLayout
      v-else-if="layout === 'list'"
      :video="video"
      :thumbnail="thumbnailPresentation"
      :profile="profilePresentation"
      :actions="actionPresentation"
      @activate="handleOpen"
      @open-profile="goToProfile"
      @toggle-like="toggleLikeVideo"
      @toggle-read="toggleReadStatus"
      @toggle-later="toggleLater"
    />
    <VideoItemGridLayout
      v-else
      :video="video"
      :thumbnail="thumbnailPresentation"
      :profile="profilePresentation"
      @activate="handleOpen"
      @open-profile="goToProfile"
    />

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
import ContextMenu from './ContextMenu.vue'
import VideoItemFeedLayout from './VideoItemFeedLayout.vue'
import VideoItemGridLayout from './VideoItemGridLayout.vue'
import VideoItemWorkbenchLayout from './VideoItemWorkbenchLayout.vue'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { updateVideoReadState } from '@/shared/api'
import { useSystemConfig } from '@/shared/composables/useSystemConfig'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { formatDate } from '@/shared/lib/dateFormat'
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
  showAvatar: false,
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

const displayDateText = computed(() => {
  const t = props.sortBy === 'created_at'
    ? (props.video.created_at || props.video.uploaded_at)
    : (props.video.uploaded_at || props.video.created_at)
  return t ? formatDate(t) : ''
})

const displayNames = computed(() => profileDisplayNames(props.video, '未知'))

const primaryProfile = computed(() => pickPrimaryProfile(props.video))

const thumbnailPresentation = computed(() => ({
  src: thumbnailSrc.value,
  title: props.video.title,
  duration: props.showDuration ? props.video.duration : null,
  progressRatio: progressRatio.value,
  showProgress: props.thumbnailProgress,
  blur: shouldBlurThumbnail.value,
}))

const profilePresentation = computed(() => ({
  profile: primaryProfile.value,
  names: displayNames.value,
  dateText: displayDateText.value,
  site: props.video.site,
  showAvatar: props.showAvatar,
}))

const actionPresentation = computed(() => ({
  isLiked: isLiked.value === 1,
  isRead: isRead.value,
  isLater: isLater.value === 1,
}))

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

<style>
.video-item {
  position: relative;
  display: flex;
  border: 0;
  background: transparent;
  padding: 0;
  outline: none;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.video-item__playback-control {
  position: absolute;
  z-index: 1;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  padding: 0;
  background: transparent;
  color: transparent;
  cursor: pointer;
}

.video-item__playback-control:hover {
  background: transparent;
  filter: none;
}

.video-item__playback-control:focus-visible {
  outline: 2px solid hsl(var(--ring) / 0.7);
  outline-offset: 2px;
  box-shadow: none;
}

.video-item__playback-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.video-item__presentation {
  pointer-events: none;
}

.video-item__controls {
  position: relative;
  z-index: 2;
}

.video-item__row-thumbnail {
  display: flex;
  flex: 0 0 clamp(11rem, 16vw, 16rem);
}

/* Reddit card post: white surface, full-width media, hairline border. */
.video-item--card {
  position: relative;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.9);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-item--card:hover {
  border-color: hsl(var(--foreground) / 0.16);
  background: hsl(var(--card));
}

.video-item--card:focus-visible {
  border-color: hsl(var(--ring) / 0.55);
}

.video-item--grid {
  flex-direction: column;
  gap: 0.55rem;
  border-radius: var(--radius-md);
}

.video-item--grid:hover .video-item__thumb--grid {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.1);
}

.video-item--grid:hover .video-item__title--grid {
  color: hsl(var(--foreground));
}

/* Workbench list: thumb left + body right. Compact enough for delivery density. */
.video-item--row {
  flex-direction: row;
  align-items: stretch;
  gap: 0.9rem;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.9);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  padding: 0.7rem;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-item--row:hover {
  border-color: hsl(var(--foreground) / 0.16);
  background: hsl(var(--card));
}

.video-item__thumb--row {
  position: relative;
  width: clamp(11rem, 16vw, 16rem);
  flex: 0 0 clamp(11rem, 16vw, 16rem);
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.video-item__row-body {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  justify-content: center;
  gap: 0.25rem;
}

.video-item__top--row {
  padding: 0;
}

.video-item__title--row {
  padding: 0;
  font-size: 0.9375rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  -webkit-line-clamp: 2;
}

.video-item__bar--row {
  margin-top: 0.125rem;
  padding: 0;
}

.video-item:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.4);
}

.video-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.875rem 0.95rem 0.3rem;
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
  --sq-button-height: 1.75rem;
  height: 1.75rem;
  border: 0;
  border-radius: 999px;
  padding: 0 0.8rem;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition:
    filter var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.video-item__join.is-on {
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
  box-shadow: inset 0 0 0 1px hsl(var(--border));
}

.video-item__join:hover {
  filter: brightness(1.06);
}

.video-item__join.is-on:hover {
  background: hsl(var(--accent));
  filter: none;
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
  padding: 0.2rem 0.95rem 0.7rem;
  font-size: 1.125rem;
  letter-spacing: -0.02em;
  line-height: 1.28;
  text-wrap: pretty;
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

.video-item--card:hover .video-item__thumb--card {
  filter: brightness(0.985);
}

.video-item--card .video-item__thumb--card img {
  transition: transform var(--duration-slow) var(--ease-out);
}

.video-item--card:hover .video-item__thumb--card :deep(img) {
  transform: scale(1.015);
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

.video-item__profile-action {
  --sq-button-height: auto;
  min-width: 0;
  gap: 0.375rem;
  border-radius: var(--radius-sm);
  padding: 0;
  color: inherit;
  font: inherit;
  filter: none;
}

.video-item__profile-action:hover {
  background: transparent;
  color: inherit;
  filter: none;
}

.video-item__profile-action--grid {
  gap: 0.5rem;
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
  gap: 0.2rem;
  padding: 0.35rem 0.45rem 0.55rem;
  border-top: 1px solid hsl(var(--border) / 0.55);
  background: hsl(var(--card));
}

.video-item__bar-btn {
  --sq-button-height: 2rem;
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: 0.375rem;
  border: 0;
  border-radius: 999px;
  padding: 0 0.75rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-item__bar-btn:hover {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground));
}

.video-item__bar-btn.is-on {
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground));
}

.video-item__bar-btn.is-on[title*='喜欢'],
.video-item__bar-btn.is-on:has(.fill-current) {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.08);
}

.video-item--appearance-workbench.video-item--card {
  border-radius: var(--radius-lg);
}

@media (prefers-reduced-motion: reduce) {
  .video-item,
  .video-item__progress-fill,
  .video-item__source-name,
  .video-item--card,
  .video-item--card .video-item__thumb--card img {
    transition: none;
  }

  .video-item--card:hover .video-item__thumb--card :deep(img) {
    transform: none;
  }
}
</style>
