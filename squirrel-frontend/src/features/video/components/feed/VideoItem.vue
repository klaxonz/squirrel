<template>
  <article
    class="video-item group"
    :class="layout === 'list' ? 'video-item--list' : 'video-item--grid'"
    role="button"
    tabindex="0"
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
        v-if="hasActiveFlags"
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
        class="video-item__duration"
        :class="{ 'video-item__duration--with-progress': progressRatio > 0 }"
      >
        {{ formatDuration(video.duration) }}
      </span>

      <div class="video-item__scrim" />

      <div
        v-if="progressRatio > 0"
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
            @click.stop="goToSubscription(displayAvatars[0].id)"
          />
        </div>

        <div class="video-item__meta-main">
          <div class="video-item__meta-line">
            <span class="video-item__source-name" @click.stop="goToSubscription(primarySubscriptionId)">
              {{ displayNames }}
            </span>
            <span v-if="video.site" class="video-item__site">{{ video.site }}</span>
          </div>
          <div class="video-item__meta-line video-item__meta-line--secondary">
            <span>{{ displayDateText }}</span>
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
            :aria-pressed="isRead"
            @click="toggleReadStatus(!isRead)"
          >
            <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-3.5" />
          </button>
          <button
            type="button"
            class="video-item__quick-btn"
            :class="{ 'is-on': isLater === 1 }"
            :title="isLater === 1 ? '取消稍后再看' : '稍后再看'"
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
            :title="isLiked === 1 ? '取消喜欢' : '喜欢'"
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
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
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

const hasActiveFlags = computed(
  () => isRead.value || isLater.value === 1 || isLiked.value === 1,
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

/* ── Thumbnail: media first, no action toolbar (media-craft) ───────────── */
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
  font-size: 0.875rem;
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
  gap: 0.125rem;
}

.video-item__meta-line {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.video-item__meta-line--secondary {
  color: hsl(var(--muted-foreground) / 0.88);
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
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.25rem;
  background: hsl(var(--accent) / 0.5);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 700;
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
