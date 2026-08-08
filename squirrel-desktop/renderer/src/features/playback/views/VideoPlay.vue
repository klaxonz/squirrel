<template>
  <div ref="videoPageRef" class="video-play-page" :class="{ 'is-widescreen': isWidescreen }">
    <div
      class="video-play-layout"
      :class="{ 'is-widescreen': isWidescreen }"
    >
      <div
        class="video-player-stage"
        :class="{ 'is-widescreen': isWidescreen }"
      >
        <div
          ref="videoPlayerHostRef"
          class="video-player-host"
        />
      </div>

      <div class="video-play-alerts">
        <div
          v-if="metadataError"
          class="video-play-alert video-play-alert--error"
          role="alert"
        >
          <div>
            <strong>视频信息加载失败</strong>
            <span>{{ metadataError }}</span>
          </div>
          <Button type="button" text severity="secondary" size="sm" :disabled="loadingMetadata" @click="retryMetadata">
            {{ loadingMetadata ? '重试中' : '重试' }}
          </Button>
        </div>

        <div
          v-if="persistenceStatus !== 'idle'"
          class="video-play-alert"
          :class="{ 'video-play-alert--error': persistenceStatus === 'failed' }"
          :role="persistenceStatus === 'failed' ? 'alert' : 'status'"
          :aria-live="persistenceStatus === 'failed' ? 'assertive' : 'polite'"
        >
          <div>
            <strong>{{ persistenceStatus === 'saving' ? '正在保存远端视频' : '远端视频保存失败' }}</strong>
            <span>{{ persistenceStatus === 'saving' ? '保存完成后即可同步互动与播放记录。' : persistenceError }}</span>
          </div>
          <Button
            v-if="persistenceStatus === 'failed'"
            type="button"
            text
            severity="secondary"
            size="sm"
            @click="ensureLocalVideo(video)"
          >
            重试
          </Button>
        </div>
      </div>

      <div class="video-play-main" :class="{ 'is-widescreen': isWidescreen }">
        <div v-if="video" class="video-detail">
          <div class="video-detail__title-block">
            <h1 class="app-h2">
              {{ video.title }}
            </h1>
            <div v-if="videoPublishedText || video.site" class="video-detail__meta">
              <span v-if="videoPublishedText">{{ videoPublishedText }}</span>
              <span
                v-if="videoPublishedText && video.site"
                class="video-detail__dot"
                aria-hidden="true"
              >·</span>
              <span v-if="video.site" class="video-detail__site">{{ video.site }}</span>
            </div>
          </div>

          <!-- 操作行：like/dislike 成组（Reddit vote pill），later/share 同排，more 靠右 -->
          <div class="video-detail__actions">
            <div class="video-detail__action-group">
              <button
                v-for="action in primaryVisibleActions"
                :key="action.key"
                type="button"
                class="video-detail__action-button"
                :class="{ 'is-active': action.active }"
                :aria-pressed="action.active"
                :aria-busy="isInteractionUpdating || undefined"
                :aria-label="action.label || action.key"
                :disabled="isInteractionUpdating"
                @click="handleVideoAction(action)"
              >
                <AppIcon :name="action.icon" class="video-detail__action-icon" :stroke-width="action.active ? 2.5 : 2" />
                <span v-if="action.label" class="video-detail__action-label">{{ action.label }}</span>
              </button>

              <button
                type="button"
                class="video-detail__action-button"
                title="分享链接"
                aria-label="分享链接"
                @click="handleShare"
              >
                <AppIcon name="share" class="video-detail__action-icon" />
                <span class="video-detail__action-label">分享</span>
              </button>
            </div>

            <div class="video-detail__more" ref="moreMenuRef">
              <button
                type="button"
                class="video-detail__action-button video-detail__action-button--more"
                :aria-expanded="moreMenuOpen"
                aria-haspopup="menu"
                aria-label="更多操作"
                @click.stop="moreMenuOpen = !moreMenuOpen"
              >
                <AppIcon name="more" class="video-detail__action-icon" />
                <span class="video-detail__action-label">更多</span>
              </button>
              <Transition name="fade">
                <AppFloatingList
                  v-if="moreMenuOpen"
                  class="video-detail__menu"
                  max-height="16rem"
                >
                  <AppListOption
                    v-for="action in videoOverflowActions.filter(a => a.key !== 'source')"
                    :key="action.key"
                    role="menuitem"
                    @click.stop="handleVideoAction(action); moreMenuOpen = false"
                  >
                    <AppIcon :name="action.icon" class="w-4 h-4 text-muted-foreground" />
                    {{ action.label }}
                  </AppListOption>
                  <a
                    v-if="video.url"
                    :href="video.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="video-detail__menu-link"
                    @click.stop="moreMenuOpen = false"
                  >
                    <AppIcon name="externalLink" class="w-4 h-4 text-muted-foreground" />
                    原视频
                  </a>
                </AppFloatingList>
              </Transition>
            </div>
          </div>

          <div class="video-detail__bar">
            <div class="video-detail__channel-actions">
              <button
                v-if="primarySubscription"
                type="button"
                class="video-detail__channel"
                @click="openProfile(primarySubscription)"
              >
                <SubscriptionAvatar :src="primarySubscription.avatar" :name="primarySubscription.name || ''" size="xl" />
                <span class="video-detail__channel-copy">
                  <span>{{ primarySubscription.name }}</span>
                  <small>{{ primarySubscription.total_videos || 0 }} 项视频</small>
                </span>
              </button>
              <Button
                v-if="primarySubscriptionUrl"
                type="button"

                size="sm"
                class="video-detail__subscribe-button"
                :class="{ 'is-subscribed': isSubscriptionChecked && isSubscribed }"
                :disabled="isCheckingSubscription || isSubscribing"
                @click="handleSubscribe"
              >
                {{ subscriptionButtonText }}
              </Button>
            </div>

            <div
              v-if="subscriptionStatusError || subscriptionToggleError"
              class="video-detail__subscription-error"
              role="alert"
            >
              <span>{{ subscriptionToggleError || subscriptionStatusError }}</span>
              <Button
                v-if="subscriptionStatusError"
                type="button"
                text
                severity="secondary"
                size="sm"
                :disabled="isCheckingSubscription"
                @click="refreshSubscriptionStatus"
              >
                {{ isCheckingSubscription ? '重试中' : '重试' }}
              </Button>
            </div>
          </div>

            <div v-if="displayedVideoActors.length" class="video-detail__actors">
              <div class="video-detail__actor-list no-scrollbar">
                <Button
                  v-for="actor in displayedVideoActors"
                  :key="actor.url || actor.name"
                  type="button"
                  severity="secondary"
                  size="sm"
                  class="video-detail__actor"
                  @click="openProfile(actor)"
                >
                  <SubscriptionAvatar :src="actor.avatar" :name="actor.name || ''" size="xs" />
                  <span class="truncate max-w-[120px]">{{ actor.name }}</span>
                </Button>
              </div>
            </div>

            <div v-if="videoDescription" class="video-detail__description">
              <div
                ref="descriptionTextRef"
                class="relative overflow-hidden"
                :class="{ 'max-h-[4.8em]': !descriptionExpanded }"
              >
                <p class="text-sm leading-relaxed text-foreground/75 whitespace-pre-wrap">
                  {{ videoDescription }}
                </p>
              </div>
              <Button
                v-if="hasLongDescription"
                type="button"
                text severity="secondary"
                size="sm"
                class="video-detail__description-toggle"
                :aria-expanded="descriptionExpanded"
                @click="descriptionExpanded = !descriptionExpanded"
              >
                {{ descriptionExpanded ? '收起' : '展开' }}
                <AppIcon :name="descriptionExpanded ? 'chevronUp' : 'chevronDown'" class="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>

          <div v-else class="video-detail__skeleton">
            <div class="space-y-2">
              <AppSkeleton width="75%" height="1.75rem" rounded="var(--radius-lg)" shimmer />
              <AppSkeleton width="9rem" height="1rem" rounded="var(--radius)" shimmer />
            </div>
            <div class="flex items-center gap-4">
              <AppSkeleton width="3rem" height="3rem" rounded="9999px" shimmer />
              <div class="space-y-2 flex-1">
                <AppSkeleton width="7rem" height="1rem" rounded="var(--radius)" shimmer />
                <AppSkeleton width="4rem" height="0.75rem" rounded="var(--radius)" shimmer />
              </div>
              <AppSkeleton width="4rem" height="1.75rem" rounded="9999px" shimmer />
            </div>
            <div class="flex gap-2">
              <AppSkeleton width="4rem" height="2rem" rounded="9999px" shimmer />
              <AppSkeleton width="5rem" height="2rem" rounded="9999px" shimmer />
              <AppSkeleton width="3.5rem" height="2rem" rounded="9999px" shimmer />
            </div>
            <AppSkeleton height="5rem" rounded="var(--radius-xl)" shimmer />
          </div>
        </div>

      <div
        class="video-play-aside"
        :class="{ 'is-widescreen': isWidescreen }"
      >
        <section v-if="activePlaylist && currentIndex >= 0" class="video-play-queue" aria-labelledby="video-play-queue-title">
          <div class="video-play-aside__header">
            <div>
              <span class="video-play-queue__eyebrow">播放列表</span>
              <h2 id="video-play-queue-title">{{ activePlaylist.name }}</h2>
            </div>
            <span class="video-play-aside__count app-mono">
              {{ currentIndex + 1 }} / {{ activePlaylistItems.length }}
            </span>
          </div>
          <div class="video-play-queue__items custom-scrollbar">
            <button
              v-for="(item, index) in activePlaylistItems"
              :key="item.id"
              type="button"
              class="video-play-queue__item"
              :class="{ 'is-current': index === currentIndex }"
              :aria-current="index === currentIndex ? 'true' : undefined"
              @click="handlePlaylistSelect(index)"
            >
              <span class="video-play-queue__index app-mono">{{ index + 1 }}</span>
              <span class="video-play-queue__title">{{ item.video?.title || `视频 ${item.video_id}` }}</span>
              <AppIcon v-if="index === currentIndex" name="play" class="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </section>

        <div class="video-play-aside__header">
          <h2>相关视频</h2>
          <span v-if="relatedVideos.length" class="video-play-aside__count app-mono">
            {{ relatedVideos.length }} 项
          </span>
        </div>

        <div class="video-play-aside__content">
          <div v-if="loadingRelated" class="space-y-3">
            <div v-for="n in 4" :key="n" class="flex gap-3">
              <AppSkeleton width="8.25rem" height="4.64rem" rounded="var(--radius-md)" class="shrink-0" shimmer />
              <div class="flex-1 space-y-1.5 py-0.5">
                <AppSkeleton width="100%" height="0.875rem" rounded="var(--radius)" shimmer />
                <AppSkeleton width="75%" height="0.875rem" rounded="var(--radius)" shimmer />
                <AppSkeleton width="4rem" height="0.75rem" rounded="var(--radius)" shimmer />
              </div>
            </div>
          </div>
          <div v-else-if="relatedVideos.length" class="video-related-list">
            <button
              v-for="related in relatedVideos"
              :key="related.id"
              type="button"
              class="video-related-item"
              :disabled="related.id == null"
              :aria-label="`播放 ${related.title}`"
              @click="related.id != null && goToVideo(related.id, related)"
            >
              <div class="video-related-item__thumb">
                <VideoThumbnail v-if="related.thumbnail" :src="(related.thumbnail as string)" fit="cover" />
                <span v-if="related.duration" class="video-related-item__duration">{{ formatDuration(related.duration as number) }}</span>
              </div>
              <div class="video-related-item__copy">
                <h4>{{ related.title }}</h4>
                <div class="video-related-item__meta">
                  <p>{{ related.subscriptions?.[0]?.name || related.site || '' }}</p>
                  <span v-if="(related.subscriptions?.[0]?.name || related.site) && related.uploaded_at" aria-hidden="true">·</span>
                  <small>{{ formatDate(related.uploaded_at) }}</small>
                </div>
              </div>
            </button>
          </div>
          <AppEmptyState v-else class="py-16" variant="plain" icon="film" title="暂无相关视频" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import usePlaybackOrchestrator from '../composables/usePlaybackOrchestrator'
import usePlaybackReporting from '../composables/usePlaybackReporting'
import useVideoActionBar from '@/features/video/composables/useVideoActionBar'
import useVideoClipMarkers from '@/features/video/composables/useVideoClipMarkers'
import useVideoPlaybackShell from '../composables/useVideoPlaybackShell'
import { useVideoDescriptionOverflow } from '../composables/useVideoDescriptionOverflow'
import { useVideoSubscription } from '../composables/useVideoSubscription'
import { useVideoShareMenu } from '../composables/useVideoShareMenu'
import useVideoPageNavigation from '@/features/video/composables/useVideoPageNavigation'
import { useProfileNavigation } from '@/features/video/composables/useProfileNavigation'
import { consumeVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { useGlobalVideoPlayer } from '@/features/playback/composables/useGlobalVideoPlayer'
import { storeToRefs } from 'pinia'
import { useThemeStore } from '@/shared/stores/theme'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { Button } from '@/shared/ui/button'
import { LocalStorageAdapter } from '@/features/playback/components/video-player/core'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useToast } from '@/shared/components/toast/useToast'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { usePlaylist } from '@/features/video/composables/usePlaylist'
import { saveRemoteVideo } from '@/shared/api'
import type { VideoPageVideo } from '@/features/playback/types/videoPlayback'
import type { PlaylistEntry } from '@/features/playback/types/playerSession'

const route = useRoute()
const router = useRouter()
const { openProfile } = useProfileNavigation(router)
// ponytail: useThemeStore replaces the deleted useAppTheme composable (the two
// had diverged — only useAppTheme wired the matchMedia listener). storeToRefs
// keeps the computed ref reactive when passed into useVideoPlaybackShell.
const { effectiveTheme } = storeToRefs(useThemeStore())
const playerAdapter = new LocalStorageAdapter()
const {
  seekGlobalVideoPlayer,
  playGlobalVideoPlayer,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  publishGlobalVideoPlayerWiring,
  session,
} = useGlobalVideoPlayer()

// ADR-0002 PR2 — usePlaybackOrchestrator now returns read-only
// projections of PlaybackSession.facts (no local refs, no hydratePlaybackState).
// The initial seed is no longer passed here; the shell hands it to
// session.beginNewVideo(id, seed) at mount. `video` is a computed projection —
// mutations go through session.update({ video }). The other projections
// (playbackSource / subtitleTracks /
// startTime) were only ever forwarded into the shell's watcher; with the
// watcher gone, VideoPlay no longer reads them, so they're not destructured.
const {
  video,
  relatedVideos,
  loadingRelated,
  loadingMetadata,
  metadataError,
  loadAndPlayById,
  retryMetadata,
} = usePlaybackOrchestrator()

const { sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()
const {
  activePlaylist,
  activePlaylistItems,
  currentIndex,
  hasPrev,
  hasNext,
  goToPrev,
  goToNext,
  setCurrentVideo,
  playItem,
} = usePlaylist()

const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate, flushPendingReport } = usePlaybackReporting(video, sendReport)

const {
  goToVideo,
  hasPrevVideo,
  hasNextVideo,
  handleAutoplayNext,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handlePlayRandom: playRandomVideo,
} = useVideoPageNavigation({
  route, router, video, relatedVideos,
  goToPrev,
  goToNext,
  onVideoEnded,
})

// A queue remains active only while the routed video belongs to it. This
// prevents a playlist opened earlier in the app session from leaking into an
// unrelated direct/related/random playback route.
watch(() => route.params.videoId, (videoId) => {
  setCurrentVideo(videoId == null ? null : String(videoId))
}, { immediate: true })

const playbackPlaylistEntries = computed<PlaylistEntry[]>(() => {
  if (currentIndex.value < 0) return []
  return activePlaylistItems.value.map((item) => ({
    id: String(item.id),
    title: item.video?.title || `视频 ${item.video_id}`,
    thumbnail: item.video?.thumbnail,
    source: null,
    videoId: item.video?.id ?? item.video_id,
    duration: item.video?.duration,
  }))
})
const hasPrevPlayback = computed(() => hasPrev.value || hasPrevVideo.value)
const hasNextPlayback = computed(() => hasNext.value || hasNextVideo.value)

const handlePlaylistSelect = async (index: number) => {
  const item = activePlaylistItems.value[index]
  const selectedVideo = item ? playItem(item) : null
  if (selectedVideo?.id != null) {
    await goToVideo(selectedVideo.id, selectedVideo)
  }
}

const toast = useToast()
const remoteSaveByUrl = new Map<string, Promise<VideoPageVideo | null>>()
const persistenceStatus = ref<'idle' | 'saving' | 'failed'>('idle')
const persistenceError = ref<string | null>(null)

const ensureLocalVideo = async (targetVideo: VideoPageVideo | null): Promise<VideoPageVideo | null> => {
  if (!targetVideo || targetVideo.source !== 'remote') return targetVideo

  const url = String(targetVideo.url || '').trim()
  if (!url) {
    persistenceStatus.value = 'failed'
    persistenceError.value = '无法保存远端视频：缺少视频地址'
    toast.error(persistenceError.value)
    return null
  }

  persistenceStatus.value = 'saving'
  persistenceError.value = null
  let savePromise = remoteSaveByUrl.get(url)
  if (!savePromise) {
    savePromise = saveRemoteVideo({
      site: targetVideo.site || undefined,
      url,
      title: targetVideo.title || url,
      thumbnail: targetVideo.thumbnail || undefined,
      duration: targetVideo.duration ?? undefined,
      publish_date: targetVideo.publish_date || targetVideo.uploaded_at || undefined,
      uploaded_at: targetVideo.uploaded_at || targetVideo.publish_date || undefined,
      description: targetVideo.description || undefined,
      subscriptions: Array.isArray(targetVideo.subscriptions) ? targetVideo.subscriptions : [],
      actors: Array.isArray(targetVideo.actors) ? targetVideo.actors : [],
    }).then((data) => {
      if (!data?.id) throw new Error('服务器未返回已保存的视频')
      return data
    }).catch((error) => {
      remoteSaveByUrl.delete(url)
      throw error
    })
    remoteSaveByUrl.set(url, savePromise)
  }

  let savedVideo: VideoPageVideo | null
  try {
    savedVideo = await savePromise
  } catch (error) {
    persistenceStatus.value = 'failed'
    persistenceError.value = errorMessage(error, '远端视频保存失败，请重试')
    toast.error(persistenceError.value)
    return null
  }
  if (!savedVideo?.id) return null
  persistenceStatus.value = 'idle'

  const currentVideo = video.value
  if (currentVideo && String(currentVideo.url || '') === url) {
    // ADR-0002 PR2 — `video` is a read-only projection of
    // session.facts.video, so the remote→local id rewrite routes through
    // session.update instead of mutating the ref in place.
    const nextVideo: VideoPageVideo = {
      ...currentVideo,
      id: String(savedVideo.id),
      interaction_type: savedVideo.interaction_type ?? currentVideo.interaction_type ?? undefined,
      last_position: savedVideo.last_position ?? currentVideo.last_position,
      clip_markers: savedVideo.clip_markers ?? currentVideo.clip_markers,
      source: 'local',
      site: currentVideo.site || savedVideo.site,
      url,
    }
    session.update({ video: nextVideo })
    if (String(route.params.videoId || '') !== String(savedVideo.id)) {
      await router.replace({ name: 'VideoPlay', params: { videoId: savedVideo.id } })
    }
  }

  return video.value || savedVideo
}

watch(() => {
  const currentVideo = video.value
  if (currentVideo?.source !== 'remote') return ''
  return String(currentVideo.url || '').trim()
}, async (url) => {
  if (!url) return
  await ensureLocalVideo(video.value)
}, { immediate: true })
// ponytail: "more" dropdown open/close + click-outside lifecycle + share
// action live in useVideoShareMenu. The document click listener + clipboard
// fallback are owned there rather than alongside playback wiring.
const { moreMenuOpen, moreMenuRef, handleShare } = useVideoShareMenu({
  videoId: computed(() => route.params.videoId as string | number | null | undefined),
})


const { videoActions, videoOverflowActions, isInteractionUpdating, handleVideoAction } = useVideoActionBar({
  video,
  interactionTypeLike: INTERACTION_TYPE.LIKE,
  interactionTypeDislike: INTERACTION_TYPE.DISLIKE,
  interactionTypeLater: INTERACTION_TYPE.LATER,
  toggleLike: (id, type) => toggleLike(id, Number(type)),
  deleteInteraction,
  ensureLocalVideo,
  commitInteractionType: (targetVideo, interactionType) => {
    const currentVideo = video.value
    if (!currentVideo) return

    const sameVideo = String(currentVideo.id) === String(targetVideo.id)
      || (!!currentVideo.url && currentVideo.url === targetVideo.url)
    if (!sameVideo) return

    session.update({
      video: {
        ...currentVideo,
        interaction_type: interactionType ?? undefined,
      },
    })
  },
  onInteractionError: (error) => {
    toast.error(errorMessage(error, '更新互动状态失败'))
  },
  handlePlayRandom: async () => {
    const navigated = await playRandomVideo()
    if (!navigated) toast.error('随机播放失败，请稍后重试')
  },
})

const { handlePlaybackTimeUpdate, handleClipMarkerSeek, handleClipMarkersUpdated } = useVideoClipMarkers({
  video,
  session,
  seekToTime: async (t: number) => {
    if (await seekGlobalVideoPlayer(t)) await playGlobalVideoPlayer()
    focusGlobalVideoPlayer()
  }
})

const handleVideoTimeUpdate = (currentTime: number) => {
  onVideoTimeUpdate(currentTime)
  handlePlaybackTimeUpdate(currentTime)
}

const videoPublishedText = computed(() => {
  const d = video.value?.publish_date || video.value?.uploaded_at
  return d ? formatDate(d) : ''
})

const videoDescription = computed(() => String(video.value?.description || '').trim())
const isRemoteVideo = computed(() => video.value?.source === 'remote')
const videoActors = computed(() => {
  const actors = video.value?.actors
  if (!Array.isArray(actors)) return []
  return actors
    .filter((actor) => String(actor?.name || '').trim())
    .map((actor) => ({
      ...actor,
      name: String(actor.name || '').trim(),
      url: String(actor.url || '').trim(),
      avatar: String(actor.avatar || '').trim(),
    }))
})
const primaryVisibleActions = computed(() => {
  const keys = isRemoteVideo.value ? ['later', 'like', 'dislike'] : ['like', 'dislike']
  return videoActions.value.filter((action) => keys.includes(action.key))
})

// ponytail: description expand/collapse + ResizeObserver overflow detection
// lives in useVideoDescriptionOverflow. The measurement lifecycle + the two
// reset watchers (video id / description text) are owned there.
const {
  descriptionTextRef,
  descriptionExpanded,
  hasLongDescription,
} = useVideoDescriptionOverflow({
  videoId: computed(() => video.value?.id),
  description: videoDescription,
})

// ponytail: subscription status + toggle live in useVideoSubscription.
// primarySubscription / primarySubscriptionUrl are returned because the view
// also renders the avatar and de-duplicates the actor list against the primary.
const {
  primarySubscription,
  primarySubscriptionUrl,
  isCheckingSubscription,
  isSubscribing,
  isSubscriptionChecked,
  isSubscribed,
  subscriptionStatusError,
  subscriptionToggleError,
  subscriptionButtonText,
  refreshSubscriptionStatus,
  handleSubscribe,
} = useVideoSubscription({ video })

const displayedVideoActors = computed(() => {
  const primary = primarySubscription.value
  const primaryUrl = String(primary?.url || '').trim().toLowerCase()
  const primaryId = primary?.id != null ? String(primary.id).trim() : ''
  const primaryName = String(primary?.name || '').trim().toLowerCase()

  return videoActors.value.filter((actor) => {
    const actorUrl = String(actor?.url || '').trim().toLowerCase()
    if (primaryUrl && actorUrl && actorUrl === primaryUrl) return false

    const actorId = actor?.id != null ? String(actor.id).trim() : ''
    if (primaryId && actorId && actorId === primaryId) return false

    const actorName = String(actor?.name || '').trim().toLowerCase()
    return !(primaryName && actorName && actorName === primaryName)
  })
})

const {
  videoPlayerHostRef,
  isWidescreen,
} = useVideoPlaybackShell({
  route,
  effectiveTheme,
  consumePlaybackSeed: (id: unknown) => consumeVideoPlaybackSeed(String(id || '')),
  loadAndPlayById,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  publishWiring: (handlers) => publishGlobalVideoPlayerWiring(handlers, playerAdapter),
  flushPendingReport,
  onVideoPlay,
  onVideoPause,
  handleAutoplayNext,
  handlePlaybackTimeUpdate: handleVideoTimeUpdate,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handlePlayerRetry: () => {
    const videoId = video.value?.id ?? String(route.params.videoId || '')
    if (videoId) void loadAndPlayById(videoId, video.value, { forceRefresh: true })
  },
  handleAuthRequired: () => {
    // 登录态失效：跳到站点管理页完成登录/授权，回来后手动重试播放。
    void router.push({ name: 'SiteRuntimes' })
  },
  handleClipMarkerSeek,
  handleClipMarkersUpdated,
  handlePlaylistSelect,
  hasPrev: hasPrevPlayback,
  hasNext: hasNextPlayback,
  playlistEntries: playbackPlaylistEntries,
  playlistIndex: currentIndex,
})

</script>

<style scoped>
.video-play-page {
  min-height: 100%;
  /* Content bearing surface — matches the workspace card so the player
     page owns its surface explicitly (transparent would work today, but
     an explicit card keeps the page self-contained if the workspace
     background ever changes). */
  background: hsl(var(--card));
}

/* ===== 布局 =====
   默认（<1080px）单列堆叠；桌面 ≥1080px 两栏：
   播放器全宽 + [详情 | 右侧栏]。
   本页独有放宽：96rem（家页/列表仍用 --app-content-media-max）。 */
.video-play-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: var(--space-5) var(--space-6);
  width: 100%;
  max-width: min(100%, 96rem);
  margin-inline: auto;
  padding: var(--space-5) var(--app-content-media-gutter) var(--space-8);
  transition:
    max-width var(--duration-base) var(--ease-out),
    padding var(--duration-base) var(--ease-out);
}

/* 宽屏语义：去掉 max-width，播放器与页面内容贴边（edge-to-edge） */
.video-play-layout.is-widescreen {
  max-width: none;
  padding-top: var(--space-4);
}

.video-player-stage {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: black;
  box-shadow: 0 0 0 1px hsl(var(--border) / 0.32);
  /* 视口适配：16:9 全宽在矮窗口/宽屏下会超出视口（底部控制条被遮挡）。
     按剩余视口高度约束宽度，保证播放器完整可见；高窗口时 100% 优先（贴边）。 */
  width: min(100%, calc((100vh - var(--app-player-chrome, 7rem)) * 16 / 9));
  margin-inline: auto;
}

/* 音乐播放时底部音乐条占用 4.5rem，追加到视口余量 */
.app-layout__scroll--music-player .video-player-stage {
  --app-player-chrome: 11.5rem;
}

.video-player-host {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
}

.video-play-alerts {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.video-play-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.3);
}

.video-play-alert > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.125rem;
}

.video-play-alert strong,
.video-play-alert span {
  font-size: var(--app-text-secondary-size);
}

.video-play-alert span {
  color: hsl(var(--muted-foreground));
}

.video-play-alert--error {
  border-color: hsl(var(--destructive) / 0.28);
  background: hsl(var(--destructive) / 0.06);
}

.video-play-alert--error strong,
.video-play-alert--error span {
  color: hsl(var(--destructive));
}

/* ===== 操作行（Reddit vote pill）=====
   标题下方横排：like/dislike 成组，later/share 同排，more 靠右。
   独立 pill 按钮（无共享容器），选中态 primary 12% 底 + primary 图标/文字。 */
.video-detail__actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding-block: var(--space-1);
}

.video-detail__action-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.video-detail__action-button {
  display: inline-flex;
  height: 2rem;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
  padding-inline: 0.625rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
  outline: none;
  white-space: nowrap;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.video-detail__action-button:hover {
  background: hsl(var(--muted) / 0.62);
  color: hsl(var(--foreground));
}

.video-detail__action-button.is-active {
  background: hsl(var(--primary) / 0.12);
  color: hsl(var(--primary));
}

.video-detail__action-button:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.52);
}

.video-detail__action-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.video-detail__action-icon {
  width: 1.125rem;
  height: 1.125rem;
  flex: 0 0 auto;
}

.video-detail__more {
  position: relative;
  margin-left: auto;
}

.video-detail__menu {
  right: 0;
  left: auto;
  width: 11rem;
}

.video-detail__menu-link {
  display: flex;
  min-height: 2.25rem;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0.25rem 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-detail__menu-link:hover,
.video-detail__menu-link:focus-visible {
  background: var(--app-row-hover-bg);
  color: hsl(var(--foreground));
  outline: none;
}

.video-play-main {
  min-width: 0;
}

.video-detail,
.video-detail__skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.video-detail__title-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-bottom: var(--space-1);
}

.video-detail__title-block h1 {
  max-width: 64rem;
  margin: 0;
  color: hsl(var(--foreground));
  font-size: clamp(1.125rem, 1.4vw, 1.375rem);
  line-height: 1.35;
  letter-spacing: -0.01em;
}

.video-detail__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: var(--app-text-secondary-size);
  font-weight: 500;
}

.video-detail__dot {
  color: hsl(var(--muted-foreground) / 0.55);
}

.video-detail__site {
  display: inline-flex;
  align-items: center;
  color: hsl(var(--muted-foreground));
  font-size: inherit;
}

.video-detail__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding-block: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--app-hairline);
}

.video-detail__channel-actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-4);
}

.video-detail__channel {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
  margin: -0.25rem;
  padding: 0.25rem;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  outline: none;
}

.video-detail__channel:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.video-detail__channel-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.125rem;
}

.video-detail__channel-copy span {
  color: hsl(var(--foreground));
  overflow: hidden;
  font-size: var(--app-text-body-size);
  font-weight: 650;
  line-height: 1.25;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-detail__channel:hover .video-detail__channel-copy span {
  color: hsl(var(--primary));
}

.video-detail__channel-copy small {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
  font-weight: 500;
}

.video-detail__subscribe-button {
  min-width: 4.25rem;
  height: 2rem;
  padding-inline: var(--space-3);
  border: 1px solid transparent;
  border-radius: 999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.video-detail__subscribe-button:hover {
  background: hsl(var(--primary) / 0.9);
}

.video-detail__subscribe-button.is-subscribed {
  border-color: hsl(var(--border) / 0.42);
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
}

.video-detail__subscribe-button.is-subscribed:hover {
  background: hsl(var(--secondary) / 0.82);
}

.video-detail__subscribe-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.video-detail__subscription-error {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  color: hsl(var(--destructive));
  font-size: var(--app-text-secondary-size);
}

.video-detail__subscription-error > span {
  min-width: 0;
}

.video-detail__actors {
  margin-top: calc(var(--space-1) * -1);
}

.video-detail__actor-list {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding-bottom: var(--space-1);
}

.video-detail__actor {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: var(--space-2);
  height: 2rem;
  padding-inline: var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.32);
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.75rem;
  font-weight: 650;
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.video-detail__actor:hover {
  background: hsl(var(--muted) / 0.72);
  color: hsl(var(--foreground));
}

/* 简介正文区：透明底（Reddit 正文区不承载 card 表面），仅顶部 hairline 分隔 */
.video-detail__description {
  padding: var(--space-3) 0 0;
  border-top: 1px solid var(--app-hairline);
  background: transparent;
}

.video-detail__description p {
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.8125rem;
  line-height: 1.8;
}

.video-detail__description-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.5rem;
  padding: 0.125rem 0.25rem;
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.875rem;
  font-weight: 650;
  outline: none;
  transition: color 0.16s ease;
}

.video-detail__description-toggle:hover,
.video-detail__description-toggle:focus-visible {
  color: hsl(var(--foreground));
}

.video-play-aside {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-3);
}

.video-play-queue {
  overflow: hidden;
  border: 1px solid var(--app-hairline);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.14);
}

.video-play-queue .video-play-aside__header {
  padding-inline: var(--space-3);
}

.video-play-queue__eyebrow {
  display: block;
  margin-bottom: 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-badge-size);
  font-weight: 600;
}

.video-play-queue__items {
  max-height: 14rem;
  overflow-y: auto;
}

.video-play-queue__item {
  display: grid;
  width: 100%;
  grid-template-columns: 1.5rem minmax(0, 1fr) 1rem;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.5rem;
  padding: var(--space-2) var(--space-3);
  border: 0;
  border-top: 1px solid var(--app-hairline);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.video-play-queue__item:hover,
.video-play-queue__item:focus-visible {
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--foreground));
  outline: none;
}

.video-play-queue__item.is-current {
  background: hsl(var(--primary) / 0.09);
  color: hsl(var(--primary));
}

/* Reddit queue: the row gets a quiet primary tint; the title stays
   foreground while the index + play indicator carry the accent. */
.video-play-queue__item.is-current .video-play-queue__title {
  color: hsl(var(--foreground));
}

.video-play-queue__index {
  font-size: var(--app-text-badge-size);
  text-align: center;
}

.video-play-queue__title {
  overflow: hidden;
  font-size: var(--app-text-secondary-size);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-play-aside__header {
  display: flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 1px solid var(--app-hairline);
}

.video-play-aside__header h2 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: var(--app-text-body-size);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.video-play-aside__count {
  color: hsl(var(--muted-foreground) / 0.66);
  font-size: var(--app-text-badge-size);
}

.video-play-aside__content {
  min-height: 20rem;
}

.video-related-list {
  display: flex;
  flex-direction: column;
}

.video-related-item {
  display: grid;
  width: calc(100% + var(--space-4));
  grid-template-columns: 8.25rem minmax(0, 1fr);
  align-items: center;
  gap: var(--space-3);
  margin-inline: calc(var(--space-2) * -1);
  padding: var(--space-2);
  border: 0;
  border-top: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  outline: none;
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}

.video-related-item + .video-related-item {
  border-top-color: var(--app-hairline);
}

.video-related-item:hover,
.video-related-item:focus-visible {
  background: hsl(var(--muted) / 0.34);
}

.video-related-item__thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  flex: 0 0 auto;
  overflow: hidden;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.video-related-item__duration {
  position: absolute;
  right: 0.25rem;
  bottom: 0.25rem;
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: var(--radius-sm);
  background: var(--app-media-badge-bg);
  color: hsl(var(--app-media-on-image));
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

.video-related-item__copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--space-1);
}

.video-related-item__copy h4 {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground) / 0.9);
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  transition: color 0.16s ease;
}

.video-related-item:hover .video-related-item__copy h4 {
  color: hsl(var(--foreground));
}

.video-related-item__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-1);
  color: hsl(var(--muted-foreground) / 0.62);
  font-size: 0.6875rem;
}

.video-related-item__meta p,
.video-related-item__meta small {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-related-item__meta p {
  color: hsl(var(--muted-foreground) / 0.76);
  font-size: inherit;
  font-weight: 500;
}

.video-related-item__meta small {
  flex: 0 0 auto;
  color: inherit;
  font-size: inherit;
  font-weight: 500;
}

/* ===== 桌面两栏（≥1080px）===== */
@media (min-width: 1080px) {
  .video-play-layout {
    grid-template-columns: minmax(0, 1fr) minmax(19rem, 22rem);
  }

  .video-play-layout.is-widescreen {
    grid-template-columns: minmax(0, 1fr) minmax(20rem, 24rem);
  }

  .video-player-stage {
    grid-column: 1 / -1;
    grid-row: 1;
  }

  .video-play-alerts {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .video-play-main {
    grid-column: 1;
    grid-row: 3;
  }

  .video-play-aside {
    position: sticky;
    top: var(--space-4);
    grid-column: 2;
    grid-row: 3;
  }
}

/* 相关视频双列（720–1079） */
@media (max-width: 1079px) and (min-width: 720px) {
  .video-related-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: var(--space-6);
  }
}

@media (max-width: 719px) {
  .video-play-layout {
    gap: var(--space-5);
    padding: var(--space-3) var(--space-4) var(--space-7);
  }

  /* 操作行：不换行不挤压，超宽横向滚动（隐藏滚动条） */
  .video-detail__actions {
    overflow-x: auto;
    scrollbar-width: none;
  }

  .video-detail__actions::-webkit-scrollbar {
    display: none;
  }

  .video-detail__bar {
    align-items: flex-start;
  }

  .video-detail__channel-actions {
    width: 100%;
    justify-content: space-between;
  }

  .video-related-item {
    grid-template-columns: 7.5rem minmax(0, 1fr);
  }
}

@media (max-width: 479px) {
  .video-detail__action-label {
    display: none;
  }

  .video-detail__action-button {
    width: 2.125rem;
    padding-inline: 0;
    justify-content: center;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .video-play-layout,
  .video-player-stage,
  .video-detail__channel-copy span,
  .video-detail__subscribe-button,
  .video-detail__action-button,
  .video-detail__menu-link,
  .video-detail__description-toggle,
  .video-related-item,
  .video-related-item__copy h4,
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
